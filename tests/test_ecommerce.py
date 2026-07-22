import asyncio
import importlib.util
import json
import os
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("commercial_ecommerce_main", ROOT / "main.py")
commercial_main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(commercial_main)


class EnvPatch:
    def __init__(self, **values):
        self.values = values
        self.previous = {}

    def __enter__(self):
        for key, value in self.values.items():
            self.previous[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def __exit__(self, _exc_type, _exc, _tb):
        for key, value in self.previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class EcommerceCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        commercial_main.configure_paths(
            data_dir=os.path.join(self.tmp.name, "data"),
            storage_dir=os.path.join(self.tmp.name, "storage"),
        )
        commercial_main.init_db()
        with EnvPatch(INVITE_CODE="secret", DEFAULT_CREDITS="100"):
            self.user = commercial_main.register_user("shop@example.com", "password1", "secret")
        self.product_asset_id = self._make_asset(self.user["id"], "product.png")

    def tearDown(self):
        self.tmp.cleanup()

    def _make_asset(self, user_id, name, kind="image"):
        asset_id = uuid.uuid4().hex
        folder = pathlib.Path(commercial_main.user_storage_path(user_id)) / "uploads"
        target = folder / f"{asset_id}.png"
        Image.new("RGB", (80, 100), "white").save(target)
        with commercial_main.db() as conn:
            conn.execute(
                "INSERT INTO assets (id, user_id, name, kind, path, url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (asset_id, user_id, name, kind, str(target), f"/api/assets/{asset_id}", commercial_main.now_ms()),
            )
        return asset_id

    def _item(self, **overrides):
        item = {
            "product_asset_id": self.product_asset_id,
            "model_preset_id": "domestic-01",
            "environment": "white",
            "shot": "full",
            "ratio": "3:4",
            "image_size": "2K",
        }
        item.update(overrides)
        return item

    def test_catalog_has_exactly_twenty_safe_model_presets(self):
        catalog = commercial_main.public_ecommerce_catalog()
        self.assertEqual(len(catalog["models"]), 20)
        self.assertEqual(len({model["id"] for model in catalog["models"]}), 20)
        self.assertEqual(
            {
                (group, gender): sum(
                    model["group"] == group and model["gender"] == gender
                    for model in catalog["models"]
                )
                for group in ("domestic", "international")
                for gender in ("female", "male")
            },
            {
                ("domestic", "female"): 5,
                ("domestic", "male"): 5,
                ("international", "female"): 5,
                ("international", "male"): 5,
            },
        )
        self.assertEqual(len(catalog["scenes"]), 6)
        self.assertEqual(
            [ratio["id"] for ratio in catalog["ratios"]],
            ["3:4", "1:1", "4:5", "2:3", "9:16", "4:3", "3:2", "16:9"],
        )
        self.assertEqual(
            [pose["id"] for pose in catalog["poses"]],
            [
                "auto",
                "front",
                "three-quarter",
                "side",
                "back",
                "weight-shift",
                "walking",
                "arms-open",
                "turn-look",
            ],
        )
        self.assertTrue(all(ratio["description"] for ratio in catalog["ratios"]))
        self.assertTrue(all(pose["name"] and pose["description"] for pose in catalog["poses"]))
        self.assertNotIn("_path", json.dumps(catalog, ensure_ascii=False))
        self.assertTrue(catalog["models"][0]["image_url"].startswith("/static/ecommerce/models/"))
        self.assertNotIn("image", catalog["models"][0])
        self.assertEqual({scene["preview_index"] for scene in catalog["scenes"]}, set(range(6)))
        for scene in catalog["scenes"]:
            self.assertEqual(scene["preview_image"], "/static/ecommerce/scenes/outdoor-scenes-contact-sheet.png")
            self.assertTrue((ROOT / scene["preview_image"].lstrip("/")).is_file())

    def test_catalog_rejects_unbalanced_gender_distribution(self):
        payload = json.loads(commercial_main.ECOMMERCE_MODEL_MANIFEST.read_text(encoding="utf-8"))
        payload["models"][0]["gender"] = "male"
        bad_manifest = pathlib.Path(self.tmp.name) / "bad-model-manifest.json"
        bad_manifest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        with patch.object(commercial_main, "ECOMMERCE_MODEL_MANIFEST", bad_manifest), self.assertRaisesRegex(
            commercial_main.AppError, "性别分布不完整"
        ):
            commercial_main.load_ecommerce_catalog()

    def test_prompt_is_gender_neutral_and_custom_male_prompt_has_no_conflict(self):
        catalog = commercial_main.load_ecommerce_catalog()
        preset_prompt = commercial_main.ecommerce_prompt(
            self._item(model_preset_id="domestic-06"), catalog
        )
        custom_prompt = commercial_main.ecommerce_prompt(
            self._item(
                model_preset_id="",
                custom_model_prompt="成年男性模特，短发，体型挺拔，沉稳商务气质",
            ),
            catalog,
        )

        for prompt in (preset_prompt, custom_prompt):
            self.assertNotIn("女装", prompt)
            self.assertNotIn("女性", prompt)
            self.assertIn("服装模特摄影图", prompt)
        self.assertIn("成年男性模特", custom_prompt)
        self.assertIn("性别与人物特征严格遵循人物设定", custom_prompt)

    def test_white_background_prompt_has_strict_neutral_white_contract(self):
        prompt = commercial_main.ecommerce_prompt(
            self._item(environment="white", pose="front"),
            commercial_main.load_ecommerce_catalog(),
        )

        for required in (
            "sRGB #FFFFFF",
            "R=255、G=255、B=255",
            "5500K",
            "四角与主体周围亮度一致",
            "禁止暖白、米白、奶油色、灰白、淡黄",
            "禁止渐变",
            "彩色投影",
            "黄光污染",
            "中性灰接触阴影",
            "白底附加禁令",
        ):
            self.assertIn(required, prompt)

        batch, _created = commercial_main.create_ecommerce_batch(
            self.user["id"], "request-white-contract", [self._item(environment="white")]
        )
        with commercial_main.db() as conn:
            row = conn.execute(
                "SELECT options_json FROM tasks WHERE batch_id = ? LIMIT 1", (batch["id"],)
            ).fetchone()
        options = json.loads(row["options_json"])
        self.assertEqual(
            options["ecommerce"]["background_contract"],
            commercial_main.ECOMMERCE_WHITE_BACKGROUND_CONTRACT,
        )

    def test_white_background_quality_gate_accepts_neutral_white_and_rejects_warm_or_gray(self):
        folder = pathlib.Path(self.tmp.name) / "quality"
        folder.mkdir()

        white_path = folder / "white.png"
        white_image = Image.new("RGB", (240, 320), "white")
        white_image.paste((30, 35, 40), (80, 40, 160, 300))
        white_image.save(white_path)
        white_report = commercial_main.inspect_ecommerce_white_background(white_path)
        self.assertTrue(white_report["passed"])
        self.assertGreaterEqual(white_report["neutral_white_coverage"], 0.9)

        warm_path = folder / "warm.png"
        Image.new("RGB", (240, 320), (255, 248, 222)).save(warm_path)
        warm_report = commercial_main.inspect_ecommerce_white_background(warm_path)
        self.assertFalse(warm_report["passed"])
        self.assertGreater(warm_report["mean_yellow_bias"], 7)

        gray_path = folder / "gray.png"
        Image.new("RGB", (240, 320), (228, 228, 228)).save(gray_path)
        gray_report = commercial_main.inspect_ecommerce_white_background(gray_path)
        self.assertFalse(gray_report["passed"])
        self.assertLess(gray_report["mean_luminance"], 244)

        warm_edge_path = folder / "warm-edge.png"
        warm_edge_image = Image.new("RGB", (240, 320), "white")
        warm_edge_image.paste((255, 248, 222), (0, 40, 12, 280))
        warm_edge_image.save(warm_edge_path)
        warm_edge_report = commercial_main.inspect_ecommerce_white_background(warm_edge_path)
        self.assertFalse(warm_edge_report["passed"])
        self.assertEqual(
            warm_edge_report["sample"],
            "perimeter-4-percent-plus-four-corners-8-percent",
        )

    def test_white_background_quality_failure_retries_once_before_completion(self):
        task = {
            "id": "white-task",
            "user_id": self.user["id"],
            "kind": "image",
            "prompt": "生成纯白背景电商图",
            "request_id": "white-request",
            "options": {
                "operation": "edit",
                "reference_inputs": {"product_asset_id": self.product_asset_id},
                "ecommerce": {
                    "environment": "white",
                    "background_contract": commercial_main.ECOMMERCE_WHITE_BACKGROUND_CONTRACT,
                },
            },
        }
        calls = []

        async def fake_image_edit(prompt, _options, _paths, request_id):
            calls.append((prompt, request_id))
            return {"data": [{"url": "https://example.com/result.png"}]}

        async def fake_persist(_task, result):
            if len(calls) == 1:
                raise commercial_main.EcommerceWhiteBackgroundQualityError({"passed": False})
            return {"items": [{"id": "result", "kind": "image"}], "raw": result}

        with (
            patch.object(commercial_main, "resolve_image_edit_reference_paths", return_value=[]),
            patch.object(commercial_main, "call_image_edit", new=fake_image_edit),
            patch.object(commercial_main, "persist_generated_assets", new=fake_persist),
            patch.object(commercial_main, "complete_task") as complete,
            patch.object(commercial_main, "fail_task") as fail,
        ):
            asyncio.run(commercial_main.execute_claimed_task(task, "test-worker"))

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1], "white-request")
        self.assertEqual(calls[1][1], "white-request-white-retry")
        self.assertIn("白底质量重试", calls[1][0])
        complete.assert_called_once()
        fail.assert_not_called()

    def test_catalog_ratio_and_pose_contracts_are_accepted(self):
        catalog = commercial_main.load_ecommerce_catalog()
        for ratio in catalog["ratios"]:
            normalized = commercial_main._normalize_ecommerce_item(
                self._item(ratio=ratio["id"]), catalog
            )
            self.assertEqual(normalized["ratio"], ratio["id"])

        for pose in catalog["poses"]:
            normalized = commercial_main._normalize_ecommerce_item(
                self._item(pose=pose["id"]), catalog
            )
            expected = "" if pose["id"] == "auto" else pose["id"]
            self.assertEqual(normalized["pose"], expected)

        with self.assertRaisesRegex(commercial_main.AppError, "图片比例不正确"):
            commercial_main._normalize_ecommerce_item(self._item(ratio="21:9"), catalog)

    def test_tuning_values_change_task_prompt_and_saved_options(self):
        item = self._item(
            environment="outdoor",
            scene_preset_id="paris-rooftop",
            shot="detail",
            pose="walking",
            ratio="4:5",
        )
        batch, created = commercial_main.create_ecommerce_batch(
            self.user["id"], "request-tuning", [item]
        )

        self.assertTrue(created)
        with commercial_main.db() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE batch_id = ? LIMIT 1", (batch["id"],)
            ).fetchone()
        task = commercial_main.task_from_row(row)
        self.assertEqual(task["options"]["ratio"], "4:5")
        self.assertEqual(task["options"]["ecommerce"]["shot"], "detail")
        self.assertEqual(task["options"]["ecommerce"]["pose"], "walking")
        self.assertEqual(task["options"]["ecommerce"]["scene_preset_id"], "paris-rooftop")
        self.assertIn("巴黎城市屋顶露台", task["prompt"])
        self.assertIn("服装细节近景", task["prompt"])
        self.assertIn("自然向前行走", task["prompt"])

    def test_unknown_pose_is_rejected_before_debit(self):
        with self.assertRaisesRegex(commercial_main.AppError, "模特姿势不正确"):
            commercial_main.create_ecommerce_batch(
                self.user["id"], "request-bad-pose", [self._item(pose="moonwalk")]
            )
        self.assertEqual(commercial_main.credit_balance(self.user["id"]), 100)

    def test_batch_is_atomic_debits_once_and_is_idempotent(self):
        items = [self._item(), self._item(shot="back")]
        first, created = commercial_main.create_ecommerce_batch(
            self.user["id"], "request-001", items
        )
        second, created_again = commercial_main.create_ecommerce_batch(
            self.user["id"], "request-001", items
        )

        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(first["tasks"]), 2)
        self.assertEqual(commercial_main.credit_balance(self.user["id"]), 90)
        with commercial_main.db() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM generation_batches").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 2)
            events = conn.execute(
                "SELECT COUNT(*) FROM credit_events WHERE reason LIKE '电商拍摄批次扣费%'"
            ).fetchone()[0]
        self.assertEqual(events, 1)

    def test_other_users_asset_is_rejected_without_debit_or_partial_tasks(self):
        with EnvPatch(INVITE_CODE="secret", DEFAULT_CREDITS="100"):
            owner = commercial_main.register_user("owner@example.com", "password1", "secret")
        foreign_asset_id = self._make_asset(owner["id"], "foreign.png")

        with self.assertRaisesRegex(commercial_main.AppError, "商品图片不存在"):
            commercial_main.create_ecommerce_batch(
                self.user["id"],
                "request-foreign",
                [self._item(), self._item(product_asset_id=foreign_asset_id)],
            )

        self.assertEqual(commercial_main.credit_balance(self.user["id"]), 100)
        with commercial_main.db() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM generation_batches").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)

    def test_batch_maximum_is_twenty_and_validation_happens_before_debit(self):
        with self.assertRaisesRegex(commercial_main.AppError, "1 到 20"):
            commercial_main.create_ecommerce_batch(
                self.user["id"], "request-too-many", [self._item() for _ in range(21)]
            )
        self.assertEqual(commercial_main.credit_balance(self.user["id"]), 100)

    def test_batch_aggregates_terminal_task_states(self):
        batch, _created = commercial_main.create_ecommerce_batch(
            self.user["id"], "request-status", [self._item(), self._item(shot="half")]
        )
        first_id, second_id = (task["id"] for task in batch["tasks"])
        commercial_main.complete_task(first_id, {"items": [{"url": "/api/assets/generated"}]})
        commercial_main.fail_task(second_id, "provider unavailable")

        loaded = commercial_main.get_ecommerce_batch(self.user["id"], batch["id"])
        self.assertEqual(loaded["status"], "partial")
        self.assertEqual(loaded["counts"]["succeeded"], 1)
        self.assertEqual(loaded["counts"]["failed"], 1)
        self.assertEqual(commercial_main.credit_balance(self.user["id"]), 95)

    def test_batch_list_is_user_scoped_filterable_and_recovers_product_asset(self):
        project = commercial_main.create_project(self.user["id"], "电商项目")
        first_canvas = commercial_main.create_canvas(self.user["id"], project["id"], "画布 A")
        second_canvas = commercial_main.create_canvas(self.user["id"], project["id"], "画布 B")
        first, _created = commercial_main.create_ecommerce_batch(
            self.user["id"], "list-first", [self._item()], canvas_id=first_canvas["id"]
        )
        second, _created = commercial_main.create_ecommerce_batch(
            self.user["id"], "list-second", [self._item()], canvas_id=second_canvas["id"]
        )
        commercial_main.complete_task(first["tasks"][0]["id"], {"items": [{"url": "/api/assets/generated"}]})
        with commercial_main.db() as conn:
            conn.execute("UPDATE generation_batches SET created_at = 100 WHERE id = ?", (first["id"],))
            conn.execute("UPDATE generation_batches SET created_at = 200 WHERE id = ?", (second["id"],))

        with EnvPatch(INVITE_CODE="secret", DEFAULT_CREDITS="100"):
            other = commercial_main.register_user("other-shop@example.com", "password1", "secret")
        other_asset = self._make_asset(other["id"], "other-product.png")
        commercial_main.create_ecommerce_batch(
            other["id"],
            "other-list-batch",
            [self._item(product_asset_id=other_asset)],
        )

        all_batches = commercial_main.list_ecommerce_batches(self.user["id"])
        active_batches = commercial_main.list_ecommerce_batches(self.user["id"], active_only=True)
        first_canvas_batches = commercial_main.list_ecommerce_batches(
            self.user["id"], canvas_id=first_canvas["id"]
        )

        self.assertEqual([batch["id"] for batch in all_batches], [second["id"], first["id"]])
        self.assertEqual([batch["id"] for batch in active_batches], [second["id"]])
        self.assertEqual([batch["id"] for batch in first_canvas_batches], [first["id"]])
        self.assertEqual(commercial_main.list_ecommerce_batches(self.user["id"], limit=1)[0]["id"], second["id"])
        self.assertEqual(commercial_main.list_ecommerce_batches(other["id"])[0]["id"] != second["id"], True)
        self.assertEqual(all_batches[0]["tasks"][0]["product_asset_id"], self.product_asset_id)

    def test_image_edit_uses_two_multipart_images_and_prompt(self):
        product = pathlib.Path(commercial_main.user_storage_path(self.user["id"])) / "uploads" / "product-edit.png"
        model = pathlib.Path(commercial_main.user_storage_path(self.user["id"])) / "uploads" / "model-edit.png"
        Image.new("RGB", (32, 32), "red").save(product)
        Image.new("RGB", (32, 32), "blue").save(model)
        captured = {}

        class FakeResponse:
            status_code = 200
            text = ""

            def raise_for_status(self):
                return None

            def json(self):
                return {"data": [{"b64_json": "AAAA"}], "secret": "must-not-pass-through"}

        class FakeClient:
            def __init__(self, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def post(self, url, **kwargs):
                captured["url"] = url
                captured.update(kwargs)
                return FakeResponse()

        config = {
            "provider": "custom",
            "api_key": "secret",
            "url": "https://images.example.test/v1/images/generations",
            "model": "gpt-image-2",
        }
        with patch.object(commercial_main, "resolve_generation_provider_config", return_value=config), patch.object(
            commercial_main.httpx, "AsyncClient", FakeClient
        ):
            result = asyncio.run(
                commercial_main.call_image_edit(
                    "locked product prompt",
                    {"operation": "edit", "model": "gpt-image-2", "ratio": "3:4", "image_size": "1K"},
                    [product, model],
                    "request-id",
                )
            )

        self.assertTrue(captured["url"].endswith("/v1/images/edits"))
        self.assertEqual(captured["data"]["prompt"], "locked product prompt")
        self.assertEqual(len(captured["files"]), 2)
        self.assertEqual([entry[0] for entry in captured["files"]], ["image[]", "image[]"])
        self.assertEqual(result["raw"], {"data": [{"b64_json": "AAAA"}]})
        self.assertNotIn("secret", json.dumps(result))

    def test_catalog_and_batch_api_are_authenticated_and_idempotent(self):
        project = commercial_main.create_project(self.user["id"], "API 电商项目")
        canvas = commercial_main.create_canvas(self.user["id"], project["id"], "API 画布")
        request_payload = {
            "client_request_id": "api-request-001",
            "canvas_id": canvas["id"],
            "items": [self._item()],
            "model": "gpt-image-2",
        }
        with EnvPatch(TASK_WORKER_ENABLED="0"), patch.object(commercial_main, "wake_task_worker") as wake_worker:
            with TestClient(commercial_main.app) as client:
                anonymous = client.get("/api/ecommerce/catalog")
                anonymous_batches = client.get("/api/ecommerce/batches")
                login = client.post(
                    "/api/auth/login",
                    json={"email": "shop@example.com", "password": "password1"},
                )
                catalog = client.get("/api/ecommerce/catalog")
                first = client.post("/api/ecommerce/batches", json=request_payload)
                second = client.post("/api/ecommerce/batches", json=request_payload)
                listed = client.get(
                    "/api/ecommerce/batches",
                    params={"canvas_id": canvas["id"], "active_only": "true", "limit": 1},
                )
                invalid_limit = client.get("/api/ecommerce/batches", params={"limit": 21})
                loaded = client.get(f"/api/ecommerce/batches/{first.json()['batch']['id']}")

        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(anonymous_batches.status_code, 401)
        self.assertEqual(login.status_code, 200)
        self.assertEqual(len(catalog.json()["models"]), 20)
        self.assertTrue(first.json()["created"])
        self.assertFalse(second.json()["created"])
        wake_worker.assert_called_once_with()
        self.assertEqual(first.json()["balance"], 95)
        self.assertEqual(second.json()["balance"], 95)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([batch["id"] for batch in listed.json()["batches"]], [first.json()["batch"]["id"]])
        self.assertEqual(listed.json()["batches"][0]["tasks"][0]["product_asset_id"], self.product_asset_id)
        self.assertEqual(invalid_limit.status_code, 422)
        self.assertEqual(loaded.json()["batch"]["status"], "queued")


if __name__ == "__main__":
    unittest.main()
