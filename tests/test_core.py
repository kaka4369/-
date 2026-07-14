import importlib.util
import asyncio
import base64
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch


ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("commercial_main", ROOT / "main.py")
commercial_main = importlib.util.module_from_spec(spec)


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


class CommercialCoreTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec.loader.exec_module(commercial_main)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        commercial_main.configure_paths(
            data_dir=os.path.join(self.tmp.name, "data"),
            storage_dir=os.path.join(self.tmp.name, "storage"),
        )
        commercial_main.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_register_requires_invite_code_and_creates_user_storage(self):
        with EnvPatch(INVITE_CODE="secret", DEFAULT_CREDITS="25"):
            with self.assertRaises(commercial_main.AppError):
                commercial_main.register_user("a@example.com", "password1", "wrong")
            user = commercial_main.register_user("a@example.com", "password1", "secret")

        self.assertEqual(user["email"], "a@example.com")
        self.assertEqual(commercial_main.credit_balance(user["id"]), 25)
        self.assertTrue(os.path.isdir(commercial_main.user_storage_path(user["id"])))

    def test_production_requires_configured_session_secret(self):
        with EnvPatch(APP_ENV="production", SESSION_SECRET=None, INVITE_CODE=None):
            with self.assertRaises(commercial_main.AppError):
                commercial_main.session_secret()

        with EnvPatch(APP_ENV="production", SESSION_SECRET="strong-secret-for-production"):
            self.assertEqual(commercial_main.session_secret(), "strong-secret-for-production")

    def test_production_rejects_unsafe_registration_config(self):
        unsafe_configs = [
            {
                "APP_ENV": "production",
                "SESSION_SECRET": "x" * 48,
                "INVITE_CODE": "canvasv1",
                "COOKIE_SECURE": "1",
                "AUTO_ADMIN_FIRST_USER": "0",
            },
            {
                "APP_ENV": "production",
                "SESSION_SECRET": "x" * 48,
                "INVITE_CODE": "private-invite-code",
                "COOKIE_SECURE": "0",
                "AUTO_ADMIN_FIRST_USER": "0",
            },
            {
                "APP_ENV": "production",
                "SESSION_SECRET": "x" * 48,
                "INVITE_CODE": "private-invite-code",
                "COOKIE_SECURE": "1",
                "AUTO_ADMIN_FIRST_USER": "1",
            },
        ]
        for index, env in enumerate(unsafe_configs):
            with self.subTest(index=index), EnvPatch(**env):
                with self.assertRaises(commercial_main.AppError):
                    commercial_main.register_user(f"unsafe-{index}@example.com", "password1", env["INVITE_CODE"])

    def test_create_admin_user_works_with_safe_production_config(self):
        with EnvPatch(
            APP_ENV="production",
            SESSION_SECRET="x" * 48,
            INVITE_CODE="private-invite-code",
            COOKIE_SECURE="1",
            AUTO_ADMIN_FIRST_USER="0",
            DEFAULT_CREDITS="0",
        ):
            admin = commercial_main.create_admin_user("owner@example.com", "password1")

        self.assertTrue(admin["is_admin"])
        self.assertEqual(admin["email"], "owner@example.com")
        self.assertEqual(admin["credits"], 0)

    def test_recover_interrupted_tasks_requeues_without_refunding(self):
        with EnvPatch(INVITE_CODE="secret", DEFAULT_CREDITS="10"):
            user = commercial_main.register_user("recover@example.com", "password1", "secret")

        task = commercial_main.create_task(user["id"], "image", "prompt", cost=3)
        self.assertEqual(commercial_main.credit_balance(user["id"]), 7)
        with commercial_main.db() as conn:
            conn.execute("UPDATE tasks SET status = 'running', refunded = 0 WHERE id = ?", (task["id"],))

        commercial_main.init_db()

        loaded = commercial_main.get_task(user["id"], task["id"])
        self.assertEqual(loaded["status"], "queued")
        self.assertEqual(loaded["refunded"], False)
        self.assertEqual(commercial_main.credit_balance(user["id"]), 7)

        commercial_main.init_db()
        self.assertEqual(commercial_main.credit_balance(user["id"]), 7)

    def test_task_options_are_normalized_and_persisted(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("options@example.com", "password1", "secret")

        task = commercial_main.create_task(
            user["id"],
            "image",
            "prompt",
            cost=0,
            options={
                "provider": "Guohe API",
                "model": "gpt-image-2",
                "ratio": "4:3",
                "image_size": "2K",
                "image_scale": 2,
                "count": 2,
                "api_key": "must-not-be-stored",
            },
        )

        self.assertEqual(task["options"]["model"], "gpt-image-2")
        self.assertEqual(task["options"]["ratio"], "4:3")
        self.assertEqual(task["options"]["image_size"], "2K")
        self.assertEqual(task["options"]["count"], 2)
        self.assertNotIn("api_key", task["options"])

    def test_provider_payload_builders_apply_structured_options(self):
        image_payload = commercial_main.build_image_payload(
            "make an image",
            {
                "model": "gpt-image-2",
                "ratio": "4:3",
                "image_size": "2K",
                "count": 2,
            },
            "https://example.com/v1/images/generations",
        )
        video_payload = commercial_main.build_video_payload(
            "make a video",
            {
                "model": "seedance-2.0-1080",
                "mode": "image_to_video",
                "duration": 8,
                "aspect_ratio": "9:16",
                "resolution": "1080p",
                "output_fps": 30,
                "fixed_camera": True,
            },
        )

        self.assertEqual(image_payload["model"], "gpt-image-2")
        self.assertEqual(image_payload["size"], "2048x1536")
        self.assertEqual(image_payload["n"], 2)
        self.assertEqual(video_payload["model"], "seedance-2.0-1080")
        self.assertEqual(video_payload["duration"], 8)
        self.assertEqual(video_payload["aspect_ratio"], "9:16")
        self.assertEqual(video_payload["resolution"], "1080p")
        self.assertEqual(video_payload["fps"], 30)
        self.assertTrue(video_payload["fixed_camera"])

    def test_provider_config_routes_named_and_default_providers(self):
        with EnvPatch(
            IMAGE_API_KEY="default-key",
            IMAGE_GENERATION_URL="https://default.example/images",
            IMAGE_MODEL="default-image",
            CUSTOM_IMAGE_API_KEY="custom-key",
            CUSTOM_IMAGE_GENERATION_URL="https://custom.example/images",
            CUSTOM_IMAGE_MODEL="custom-image",
        ):
            default = commercial_main.resolve_provider_config("image", "国禾API")
            custom = commercial_main.resolve_provider_config("image", "自定义")

        self.assertEqual(default["api_key"], "default-key")
        self.assertEqual(default["url"], "https://default.example/images")
        self.assertEqual(custom["api_key"], "custom-key")
        self.assertEqual(custom["url"], "https://custom.example/images")
        self.assertEqual(custom["model"], "custom-image")

    def test_generation_capabilities_do_not_expose_secrets(self):
        with EnvPatch(
            LLM_API_KEY=None,
            IMAGE_API_KEY="image-secret",
            IMAGE_GENERATION_URL="https://example.com/images",
            VIDEO_API_KEY=None,
            VIDEO_GENERATION_URL=None,
        ):
            capabilities = commercial_main.generation_capabilities()

        self.assertFalse(capabilities["llm"]["configured"])
        self.assertTrue(capabilities["image"]["configured"])
        self.assertFalse(capabilities["video"]["configured"])
        self.assertNotIn("image-secret", str(capabilities))

    def test_async_video_submission_polls_until_media_is_available(self):
        class FakeResponse:
            def __init__(self, data):
                self.data = data

            def raise_for_status(self):
                return None

            def json(self):
                return self.data

        class FakeClient:
            def __init__(self, *args, **kwargs):
                self.polls = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, *_args, **_kwargs):
                return FakeResponse({"task_id": "video-123", "status": "queued"})

            async def get(self, *_args, **_kwargs):
                self.polls += 1
                if self.polls == 1:
                    return FakeResponse({"id": "video-123", "status": "running"})
                return FakeResponse({"id": "video-123", "status": "succeeded", "video_url": "https://cdn.example/final.mp4"})

        with EnvPatch(
            VIDEO_API_KEY="video-key",
            VIDEO_GENERATION_URL="https://video.example/tasks",
            VIDEO_STATUS_URL_TEMPLATE="https://video.example/tasks/{task_id}",
            VIDEO_POLL_INTERVAL_SECONDS="0",
            VIDEO_POLL_TIMEOUT_SECONDS="5",
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            result = asyncio.run(commercial_main.call_video("prompt", {"provider": "灵境API"}, "request-1"))

        self.assertEqual(result["task_id"], "video-123")
        self.assertEqual(result["raw"]["video_url"], "https://cdn.example/final.mp4")

    def test_async_video_submission_requires_status_endpoint(self):
        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"task_id": "video-123", "status": "queued"}

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, *_args, **_kwargs):
                return FakeResponse()

        with EnvPatch(
            VIDEO_API_KEY="video-key",
            VIDEO_GENERATION_URL="https://video.example/tasks",
            VIDEO_STATUS_URL_TEMPLATE=None,
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            with self.assertRaisesRegex(RuntimeError, "状态查询地址"):
                asyncio.run(commercial_main.call_video("prompt", {"provider": "灵境API"}, "request-1"))

    def test_expired_tasks_stop_after_maximum_attempts(self):
        with EnvPatch(INVITE_CODE="secret", DEFAULT_CREDITS="10", TASK_MAX_ATTEMPTS="2"):
            user = commercial_main.register_user("max-attempts@example.com", "password1", "secret")
            task = commercial_main.create_task(user["id"], "image", "prompt", cost=3)
            with commercial_main.db() as conn:
                conn.execute(
                    "UPDATE tasks SET status = 'running', attempt_count = 2, lease_until = 1 WHERE id = ?",
                    (task["id"],),
                )
            commercial_main.recover_expired_tasks()

        loaded = commercial_main.get_task(user["id"], task["id"])
        self.assertEqual(loaded["status"], "failed")
        self.assertEqual(commercial_main.credit_balance(user["id"]), 10)

    def test_queue_claim_and_expired_lease_recovery_preserve_charge(self):
        with EnvPatch(INVITE_CODE="secret", DEFAULT_CREDITS="10"):
            user = commercial_main.register_user("queue@example.com", "password1", "secret")

        task = commercial_main.create_task(user["id"], "image", "prompt", cost=3)
        claimed = commercial_main.claim_next_task("worker-test", lease_ms=1000)

        self.assertEqual(claimed["id"], task["id"])
        self.assertEqual(claimed["status"], "running")
        self.assertEqual(claimed["attempt_count"], 1)
        with commercial_main.db() as conn:
            conn.execute("UPDATE tasks SET lease_until = 1 WHERE id = ?", (task["id"],))
        self.assertEqual(commercial_main.requeue_expired_tasks(), 1)
        loaded = commercial_main.get_task(user["id"], task["id"])
        self.assertEqual(loaded["status"], "queued")
        self.assertEqual(commercial_main.credit_balance(user["id"]), 7)

    def test_generated_data_uri_is_persisted_in_user_outputs(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("persist@example.com", "password1", "secret")

        task = commercial_main.create_task(
            user["id"],
            "image",
            "character sheet",
            cost=0,
            canvas_id="canvas_1",
            node_id="node_1",
        )
        png = b"\x89PNG\r\n\x1a\n" + b"generated-image"
        result = {"items": [{"url": f"data:image/png;base64,{base64.b64encode(png).decode('ascii')}"}]}

        persisted = asyncio.run(commercial_main.persist_generated_assets(task, result))
        commercial_main.complete_task(task["id"], persisted)
        loaded = commercial_main.get_task(user["id"], task["id"])
        assets = commercial_main.list_assets(user["id"])

        self.assertTrue(loaded["result"]["items"][0]["url"].startswith("/api/assets/"))
        self.assertEqual(assets[0]["source"], "task")
        self.assertEqual(assets[0]["task_id"], task["id"])
        self.assertTrue(pathlib.Path(assets[0]["path"]).is_file())
        self.assertIn(str(pathlib.Path("users") / user["id"] / "outputs"), assets[0]["path"])

    def test_generated_assets_use_streaming_writer_instead_of_buffering_reader(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("stream@example.com", "password1", "secret")
        task = commercial_main.create_task(user["id"], "image", "stream image", cost=0)
        png = b"\x89PNG\r\n\x1a\n" + b"streamed-image"

        async def fake_stream(_url, _kind, temporary, _user_id):
            temporary.write_bytes(png)
            return ".png", len(png)

        with patch.object(commercial_main, "stream_generated_media_to_path", side_effect=fake_stream), patch.object(
            commercial_main,
            "read_generated_media",
            side_effect=AssertionError("buffering reader must not be used"),
        ):
            persisted = asyncio.run(
                commercial_main.persist_generated_assets(task, {"items": [{"url": "https://example.com/image.png"}]})
            )

        asset = commercial_main.list_assets(user["id"])[0]
        self.assertEqual(persisted["items"][0]["url"], asset["url"])
        self.assertEqual(pathlib.Path(asset["path"]).read_bytes(), png)

    def test_generated_media_download_rejects_private_network_urls(self):
        with self.assertRaisesRegex(RuntimeError, "不允许保存内网地址"):
            asyncio.run(commercial_main.read_generated_media("http://127.0.0.1:3020/static/app.js", "image"))

    def test_generated_asset_batch_does_not_leave_partial_files(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("atomic-assets@example.com", "password1", "secret")
        task = commercial_main.create_task(user["id"], "image", "two images", cost=0)
        png = b"\x89PNG\r\n\x1a\n" + b"first"
        result = {
            "items": [
                {"url": f"data:image/png;base64,{base64.b64encode(png).decode('ascii')}"},
                {"url": "data:image/png;base64,not-valid-base64"},
            ]
        }

        with self.assertRaisesRegex(RuntimeError, "Base64"):
            asyncio.run(commercial_main.persist_generated_assets(task, result))

        self.assertEqual(commercial_main.list_assets(user["id"]), [])
        output_dir = pathlib.Path(commercial_main.user_storage_path(user["id"])) / "outputs"
        self.assertEqual(list(output_dir.iterdir()), [])

    def test_dockerignore_excludes_runtime_secrets_and_user_data(self):
        dockerignore = ROOT / ".dockerignore"
        self.assertTrue(dockerignore.exists())
        text = dockerignore.read_text(encoding="utf-8")
        for pattern in [".env", "data/", "storage/", "output/", "*.log", "*.png", "__pycache__/"]:
            self.assertIn(pattern, text)

        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertNotIn("COPY . .", dockerfile)

    def test_credits_charge_and_refund_once(self):
        with EnvPatch(INVITE_CODE="secret", DEFAULT_CREDITS="10"):
            user = commercial_main.register_user("b@example.com", "password1", "secret")

        task = commercial_main.create_task(user["id"], "llm", "hello", cost=3)
        self.assertEqual(commercial_main.credit_balance(user["id"]), 7)

        commercial_main.fail_task(task["id"], "upstream error")
        commercial_main.fail_task(task["id"], "upstream error")

        loaded = commercial_main.get_task(user["id"], task["id"])
        self.assertEqual(loaded["status"], "failed")
        self.assertEqual(commercial_main.credit_balance(user["id"]), 10)

    def test_canvas_and_tasks_are_user_scoped(self):
        with EnvPatch(INVITE_CODE="secret"):
            alice = commercial_main.register_user("alice@example.com", "password1", "secret")
            bob = commercial_main.register_user("bob@example.com", "password1", "secret")

        project = commercial_main.create_project(alice["id"], "Campaign")
        canvas = commercial_main.create_canvas(alice["id"], project["id"], "Board")
        task = commercial_main.create_task(alice["id"], "image", "prompt", cost=1)

        self.assertEqual(commercial_main.get_canvas(alice["id"], canvas["id"])["name"], "Board")
        self.assertIsNone(commercial_main.get_canvas(bob["id"], canvas["id"]))
        self.assertEqual(commercial_main.get_task(alice["id"], task["id"])["kind"], "image")
        self.assertIsNone(commercial_main.get_task(bob["id"], task["id"]))

    def test_canvas_save_rejects_stale_revision(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("revision@example.com", "password1", "secret")
        project = commercial_main.create_project(user["id"], "Project")
        canvas = commercial_main.create_canvas(user["id"], project["id"], "Canvas")

        saved = commercial_main.save_canvas_state(
            user["id"],
            canvas["id"],
            {"nodes": [{"id": "one"}]},
            expected_revision=canvas["revision"],
        )

        self.assertEqual(saved["revision"], canvas["revision"] + 1)
        with self.assertRaisesRegex(commercial_main.AppError, "其他页面") as caught:
            commercial_main.save_canvas_state(
                user["id"],
                canvas["id"],
                {"nodes": [{"id": "stale"}]},
                expected_revision=canvas["revision"],
            )
        self.assertEqual(caught.exception.status_code, 409)

    def test_user_storage_quota_counts_existing_files(self):
        with EnvPatch(INVITE_CODE="secret", MAX_USER_STORAGE_MB="1"):
            user = commercial_main.register_user("quota@example.com", "password1", "secret")
            uploads = pathlib.Path(commercial_main.user_storage_path(user["id"])) / "uploads"
            (uploads / "existing.bin").write_bytes(b"x" * (1024 * 1024 - 16))
            with self.assertRaisesRegex(commercial_main.AppError, "存储空间"):
                commercial_main.ensure_user_storage_capacity(user["id"], 32)

    def test_storage_summary_reports_used_limit_and_percentage(self):
        with EnvPatch(INVITE_CODE="secret", MAX_USER_STORAGE_MB="1"):
            user = commercial_main.register_user("usage@example.com", "password1", "secret")
            uploads = pathlib.Path(commercial_main.user_storage_path(user["id"])) / "uploads"
            (uploads / "sample.bin").write_bytes(b"x" * 1024)
            summary = commercial_main.user_storage_summary(user["id"])

        self.assertEqual(summary["used_bytes"], 1024)
        self.assertEqual(summary["limit_bytes"], 1024 * 1024)
        self.assertAlmostEqual(summary["percent"], 0.1, places=1)

    def test_asset_delete_is_owner_scoped_and_removes_local_file(self):
        with EnvPatch(INVITE_CODE="secret"):
            alice = commercial_main.register_user("asset-owner@example.com", "password1", "secret")
            bob = commercial_main.register_user("asset-other@example.com", "password1", "secret")
        target = pathlib.Path(commercial_main.user_storage_path(alice["id"])) / "uploads" / "owned.png"
        target.write_bytes(b"\x89PNG\r\n\x1a\nowned")
        with commercial_main.db() as conn:
            conn.execute(
                "INSERT INTO assets (id, user_id, name, kind, path, url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("owned_asset", alice["id"], "owned.png", "image", str(target), "/api/assets/owned_asset", 1),
            )

        self.assertFalse(commercial_main.delete_asset(bob["id"], "owned_asset"))
        self.assertTrue(target.exists())
        self.assertTrue(commercial_main.delete_asset(alice["id"], "owned_asset"))
        self.assertFalse(target.exists())
        self.assertEqual(commercial_main.list_assets(alice["id"]), [])

    def test_change_password_rejects_wrong_current_and_invalidates_old_password(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("password@example.com", "password1", "secret")

        with self.assertRaisesRegex(commercial_main.AppError, "当前密码"):
            commercial_main.change_password(user["id"], "wrong-password", "new-password2")

        commercial_main.change_password(user["id"], "password1", "new-password2")
        with self.assertRaises(commercial_main.AppError):
            commercial_main.authenticate_user("password@example.com", "password1")
        self.assertEqual(
            commercial_main.authenticate_user("password@example.com", "new-password2")["id"],
            user["id"],
        )

    def test_task_keeps_canvas_and_node_metadata_for_navigation(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("meta@example.com", "password1", "secret")

        task = commercial_main.create_task(
            user["id"],
            "image",
            "prompt",
            cost=0,
            canvas_id="canvas_1",
            node_id="node_1",
        )
        loaded = commercial_main.get_task(user["id"], task["id"])

        self.assertEqual(loaded["canvas_id"], "canvas_1")
        self.assertEqual(loaded["node_id"], "node_1")

    def test_task_target_can_be_recovered_from_saved_canvas_state(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("target@example.com", "password1", "secret")

        project = commercial_main.create_project(user["id"], "Project")
        canvas = commercial_main.create_canvas(user["id"], project["id"], "Canvas")
        task = commercial_main.create_task(user["id"], "image", "prompt", cost=0)
        commercial_main.save_canvas_state(
            user["id"],
            canvas["id"],
            {
                "nodes": [{"id": "node_1", "type": "image", "taskId": task["id"]}],
                "edges": [],
                "viewport": {"x": 0, "y": 0, "scale": 1},
            },
        )

        self.assertEqual(
            commercial_main.find_task_target(user["id"], task["id"]),
            {"project_id": project["id"], "canvas_id": canvas["id"], "node_id": "node_1"},
        )

    def test_task_target_with_canvas_metadata_includes_owning_project(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("direct-target@example.com", "password1", "secret")

        project = commercial_main.create_project(user["id"], "Project")
        canvas = commercial_main.create_canvas(user["id"], project["id"], "Canvas")
        task = commercial_main.create_task(
            user["id"],
            "image",
            "prompt",
            cost=0,
            canvas_id=canvas["id"],
            node_id="node_2",
        )

        self.assertEqual(
            commercial_main.find_task_target(user["id"], task["id"]),
            {"project_id": project["id"], "canvas_id": canvas["id"], "node_id": "node_2"},
        )

    def test_asset_library_includes_generated_task_media(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("assets@example.com", "password1", "secret")

        task = commercial_main.create_task(
            user["id"],
            "image",
            "prompt",
            cost=0,
            canvas_id="canvas_1",
            node_id="node_1",
        )
        commercial_main.complete_task(task["id"], {"items": [{"url": "https://example.com/result.png"}]})

        assets = commercial_main.list_assets(user["id"])

        self.assertEqual(assets[0]["url"], "https://example.com/result.png")
        self.assertEqual(assets[0]["source"], "task")
        self.assertEqual(assets[0]["task_id"], task["id"])
        self.assertEqual(assets[0]["canvas_id"], "canvas_1")
        self.assertEqual(assets[0]["node_id"], "node_1")

    def test_workflow_templates_are_user_scoped_and_reusable(self):
        with EnvPatch(INVITE_CODE="secret"):
            alice = commercial_main.register_user("workflow-a@example.com", "password1", "secret")
            bob = commercial_main.register_user("workflow-b@example.com", "password1", "secret")

        payload = {
            "version": 1,
            "nodes": [
                {"id": "prompt_1", "type": "prompt", "title": "提示词", "prompt": "卖点说明"},
                {"id": "image_1", "type": "image", "title": "生图", "prompt": "商品主图"},
            ],
            "edges": [{"id": "edge_1", "source": "prompt_1", "target": "image_1"}],
        }
        workflow = commercial_main.create_workflow_template(alice["id"], "商品图模板", payload)

        self.assertEqual(workflow["name"], "商品图模板")
        self.assertEqual(workflow["node_count"], 2)
        self.assertEqual(workflow["edge_count"], 1)
        self.assertEqual(commercial_main.list_workflow_templates(alice["id"])[0]["id"], workflow["id"])
        self.assertEqual(commercial_main.get_workflow_template(alice["id"], workflow["id"])["payload"]["nodes"][0]["id"], "prompt_1")
        self.assertIsNone(commercial_main.get_workflow_template(bob["id"], workflow["id"]))
        self.assertTrue(commercial_main.delete_workflow_template(alice["id"], workflow["id"]))
        self.assertEqual(commercial_main.list_workflow_templates(alice["id"]), [])


if __name__ == "__main__":
    unittest.main()
