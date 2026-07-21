import importlib.util
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image


ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("commercial_api_main", ROOT / "main.py")
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


class CommercialApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        commercial_main.configure_paths(
            data_dir=os.path.join(self.tmp.name, "data"),
            storage_dir=os.path.join(self.tmp.name, "storage"),
        )
        commercial_main.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_health_endpoints_are_public_and_minimal(self):
        with EnvPatch(TASK_WORKER_ENABLED="0"):
            with TestClient(commercial_main.app) as client:
                alive = client.get("/healthz")
                ready = client.get("/readyz")

        self.assertEqual(alive.status_code, 200)
        self.assertEqual(alive.json(), {"status": "ok"})
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json(), {"status": "ok"})

    def test_readyz_failure_is_generic_and_does_not_leak_details(self):
        with EnvPatch(TASK_WORKER_ENABLED="0"):
            with TestClient(commercial_main.app) as client:
                with patch.object(
                    commercial_main,
                    "runtime_ready",
                    side_effect=RuntimeError("secret database path and credentials"),
                ):
                    response = client.get("/readyz")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"status": "unavailable"})
        self.assertNotIn("secret", response.text)
        self.assertNotIn("database", response.text)

    def test_runtime_ready_checks_database_and_writable_directories(self):
        self.assertTrue(commercial_main.runtime_ready())

        commercial_main.DB_PATH.write_bytes(b"not a sqlite database")
        self.assertFalse(commercial_main.runtime_ready())

        blocked_data = pathlib.Path(self.tmp.name) / "blocked-data"
        blocked_data.write_text("not a directory", encoding="utf-8")
        commercial_main.configure_paths(
            data_dir=str(blocked_data),
            storage_dir=os.path.join(self.tmp.name, "other-storage"),
        )

        self.assertFalse(commercial_main.runtime_ready())

    def test_register_canvas_save_and_admin_recharge(self):
        with EnvPatch(INVITE_CODE="secret", DEFAULT_CREDITS="12", AUTO_ADMIN_FIRST_USER="1"):
            with TestClient(commercial_main.app) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "owner@example.com", "password": "password1", "invite_code": "secret"},
                )
                self.assertEqual(registered.status_code, 200)
                self.assertTrue(registered.json()["user"]["is_admin"])

                project = client.post("/api/projects", json={"name": "Launch"}).json()["project"]
                canvas = client.post(f"/api/projects/{project['id']}/canvases", json={"name": "Board"}).json()["canvas"]

                saved = client.put(
                    f"/api/canvases/{canvas['id']}",
                    json={"name": "Board", "state": {"nodes": [{"id": "n1", "type": "text"}], "edges": []}},
                )
                self.assertEqual(saved.status_code, 200)
                self.assertEqual(saved.json()["canvas"]["state"]["nodes"][0]["id"], "n1")

                users = client.get("/api/admin/users").json()["users"]
                balance = client.post(
                    f"/api/admin/users/{users[0]['id']}/credits",
                    json={"delta": 8, "reason": "manual test"},
                )
                self.assertEqual(balance.status_code, 200)
                self.assertEqual(balance.json()["balance"], 20)

    def test_admin_users_requires_login(self):
        with EnvPatch(TASK_WORKER_ENABLED="0"):
            with TestClient(commercial_main.app) as client:
                response = client.get("/api/admin/users")

        self.assertEqual(response.status_code, 401)

    def test_admin_users_rejects_non_admin_users(self):
        with EnvPatch(INVITE_CODE="secret", AUTO_ADMIN_FIRST_USER="1", TASK_WORKER_ENABLED="0"):
            with TestClient(commercial_main.app) as client:
                client.post(
                    "/api/auth/register",
                    json={"email": "admin@example.com", "password": "password1", "invite_code": "secret"},
                )
                client.post("/api/auth/logout")
                member = client.post(
                    "/api/auth/register",
                    json={"email": "member@example.com", "password": "password1", "invite_code": "secret"},
                )

                response = client.get("/api/admin/users")

        self.assertFalse(member.json()["user"]["is_admin"])
        self.assertEqual(response.status_code, 403)

    def test_admin_provider_configs_are_persistent_masked_and_hot_loaded(self):
        secret = "provider-secret-must-never-be-returned"
        with EnvPatch(
            INVITE_CODE="secret",
            AUTO_ADMIN_FIRST_USER="1",
            TASK_WORKER_ENABLED="0",
            APP_ENV="development",
            CANVAS_PRODUCTION="0",
            CONFIG_ENCRYPTION_KEY="test-config-encryption-key",
            CUSTOM_IMAGE_API_KEY=None,
            CUSTOM_IMAGE_GENERATION_URL=None,
            CUSTOM_IMAGE_MODEL=None,
        ):
            with TestClient(commercial_main.app) as client:
                client.post(
                    "/api/auth/register",
                    json={"email": "admin@example.com", "password": "password1", "invite_code": "secret"},
                )

                initial = client.get("/api/admin/providers")
                saved = client.put(
                    "/api/admin/providers/image/%E8%87%AA%E5%AE%9A%E4%B9%89",
                    json={
                        "api_key": secret,
                        "url": "https://images.example.test/v1/generations",
                        "model": "custom-image-v1",
                    },
                )
                listed = client.get("/api/admin/providers")
                preserved = client.put(
                    "/api/admin/providers/image/%E8%87%AA%E5%AE%9A%E4%B9%89",
                    json={"api_key": "", "model": "custom-image-v2"},
                )
                capabilities = client.get("/api/capabilities")

                effective = commercial_main.resolve_provider_config("image", "自定义")
                with commercial_main.db() as conn:
                    stored = conn.execute(
                        "SELECT value_json FROM app_settings WHERE key = ?",
                        (commercial_main.provider_setting_key("image", "自定义"),),
                    ).fetchone()["value_json"]

                cleared = client.put(
                    "/api/admin/providers/image/%E8%87%AA%E5%AE%9A%E4%B9%89",
                    json={"clear_api_key": True},
                )

        self.assertEqual(initial.status_code, 200)
        self.assertEqual(len(initial.json()["providers"]), 9)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(preserved.status_code, 200)
        self.assertEqual(capabilities.status_code, 200)
        for response in (saved, listed, preserved, cleared):
            self.assertNotIn(secret, response.text)
        self.assertNotIn(secret, stored)
        self.assertEqual(saved.json()["provider"]["source"], "admin")
        self.assertTrue(saved.json()["provider"]["has_api_key"])
        self.assertEqual(saved.json()["provider"]["key_preview"], f"••••{secret[-4:]}")
        self.assertTrue(saved.json()["provider"]["configured"])
        self.assertEqual(effective["api_key"], secret)
        self.assertEqual(effective["model"], "custom-image-v2")
        self.assertIn("custom-image-v2", capabilities.json()["generation"]["image"]["models"])
        self.assertFalse(cleared.json()["provider"]["has_api_key"])
        self.assertEqual(cleared.json()["provider"]["key_preview"], "")
        self.assertFalse(cleared.json()["provider"]["configured"])

    def test_admin_multi_models_are_visible_to_all_members_and_validate_default(self):
        secret = "multi-provider-secret"
        with EnvPatch(
            INVITE_CODE="secret",
            AUTO_ADMIN_FIRST_USER="1",
            TASK_WORKER_ENABLED="0",
            APP_ENV="development",
            CANVAS_PRODUCTION="0",
            CONFIG_ENCRYPTION_KEY="test-config-encryption-key",
            IMAGE_API_KEY=None,
            IMAGE_GENERATION_URL=None,
            IMAGE_MODEL=None,
            OPENAI_IMAGE_API_KEY=None,
            OPENAI_IMAGE_GENERATION_URL=None,
            OPENAI_IMAGE_MODEL=None,
            CUSTOM_IMAGE_API_KEY=None,
            CUSTOM_IMAGE_GENERATION_URL=None,
            CUSTOM_IMAGE_MODEL=None,
        ):
            with TestClient(commercial_main.app) as client:
                client.post(
                    "/api/auth/register",
                    json={"email": "admin@example.com", "password": "password1", "invite_code": "secret"},
                )
                saved = client.put(
                    "/api/admin/providers/image/%E8%87%AA%E5%AE%9A%E4%B9%89",
                    json={
                        "api_key": secret,
                        "url": "https://images.example.test/v1/generations",
                        "model": "image-model-b",
                        "models": ["image-model-a", "image-model-b", "image-model-a", ""],
                    },
                )
                invalid_default = client.put(
                    "/api/admin/providers/image/%E8%87%AA%E5%AE%9A%E4%B9%89",
                    json={"model": "image-model-c", "models": ["image-model-a", "image-model-b"]},
                )
                listed = client.get("/api/admin/providers")
                client.post("/api/auth/logout")
                member = client.post(
                    "/api/auth/register",
                    json={"email": "member@example.com", "password": "password1", "invite_code": "secret"},
                )
                capabilities = client.get("/api/capabilities")

        provider = next(
            item
            for item in listed.json()["providers"]
            if item["kind"] == "image" and item["provider"] == "自定义"
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["provider"]["model"], "image-model-b")
        self.assertEqual(saved.json()["provider"]["models"], ["image-model-a", "image-model-b"])
        self.assertEqual(invalid_default.status_code, 400)
        self.assertEqual(provider["model"], "image-model-b")
        self.assertEqual(provider["models"], ["image-model-a", "image-model-b"])
        self.assertNotIn(secret, listed.text)
        self.assertEqual(member.status_code, 200)
        self.assertFalse(member.json()["user"]["is_admin"])
        self.assertEqual(capabilities.status_code, 200)
        self.assertEqual(capabilities.json()["generation"]["image"]["models"], ["image-model-b", "image-model-a"])

    def test_member_capabilities_expose_models_without_provider_details(self):
        with EnvPatch(
            INVITE_CODE="secret",
            AUTO_ADMIN_FIRST_USER="0",
            TASK_WORKER_ENABLED="0",
            VIDEO_API_KEY="video-key",
            VIDEO_GENERATION_URL="https://video.example.test/generations",
            VIDEO_MODEL="doubao-seedance-2-0-260128",
            VOLCANO_VIDEO_API_KEY="volcano-key",
            VOLCANO_VIDEO_GENERATION_URL="https://volcano.example.test/generations",
            VOLCANO_VIDEO_MODEL="not-a-real-seedance-model",
            CUSTOM_VIDEO_API_KEY=None,
            CUSTOM_VIDEO_GENERATION_URL=None,
            CUSTOM_VIDEO_MODEL=None,
        ):
            with TestClient(commercial_main.app) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "member@example.com", "password": "password1", "invite_code": "secret"},
                )
                response = client.get("/api/capabilities")

        self.assertEqual(registered.status_code, 200)
        self.assertEqual(response.status_code, 200)
        generation = response.json()["generation"]
        self.assertEqual(set(generation["video"]), {"configured", "models", "model_capabilities"})
        self.assertEqual(
            generation["video"]["models"],
            ["doubao-seedance-2-0-260128", "not-a-real-seedance-model"],
        )
        self.assertEqual(
            generation["video"]["model_capabilities"]["doubao-seedance-2-0-260128"],
            {
                "image_to_video": True,
                "strong_reference": True,
                "first_last_frame": True,
                "max_images": 2,
            },
        )
        self.assertEqual(
            generation["video"]["model_capabilities"]["not-a-real-seedance-model"],
            {
                "image_to_video": False,
                "strong_reference": False,
                "first_last_frame": False,
                "max_images": 0,
            },
        )
        self.assertNotIn("providers", str(generation))
        for provider_name in ("灵境API", "火山引擎", "自定义"):
            self.assertNotIn(provider_name, str(generation))

    def test_video_task_rejects_unsupported_image_reference_before_charging(self):
        with EnvPatch(
            INVITE_CODE="secret",
            DEFAULT_CREDITS="100",
            AUTO_ADMIN_FIRST_USER="0",
            TASK_WORKER_ENABLED="0",
            VIDEO_API_KEY=None,
            VIDEO_GENERATION_URL=None,
            VIDEO_MODEL=None,
            VOLCANO_VIDEO_API_KEY=None,
            VOLCANO_VIDEO_GENERATION_URL=None,
            VOLCANO_VIDEO_MODEL=None,
            CUSTOM_VIDEO_API_KEY="custom-key",
            CUSTOM_VIDEO_GENERATION_URL="https://custom.example.test/video/generations",
            CUSTOM_VIDEO_MODEL="custom-video",
        ):
            with TestClient(commercial_main.app) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "member@example.com", "password": "password1", "invite_code": "secret"},
                )
                response = client.post(
                    "/api/tasks",
                    json={
                        "kind": "video",
                        "prompt": "animate",
                        "options": {
                            "model": "custom-video",
                            "mode": "image_to_video",
                            "first_frame_asset_id": "missing-image",
                        },
                    },
                )
                balance = client.get("/api/me").json()["user"]["credits"]

        self.assertEqual(registered.status_code, 200)
        self.assertEqual(response.status_code, 400)
        self.assertIn("不支持图生视频", response.json()["detail"])
        self.assertEqual(balance, 100)

    def test_video_task_rejects_mixed_strong_reference_and_first_last_frames(self):
        with EnvPatch(
            INVITE_CODE="secret",
            DEFAULT_CREDITS="100",
            AUTO_ADMIN_FIRST_USER="0",
            TASK_WORKER_ENABLED="0",
            VIDEO_API_KEY="video-key",
            VIDEO_GENERATION_URL="https://video.example.test/generations",
            VIDEO_MODEL="doubao-seedance-2-0-260128",
            VOLCANO_VIDEO_API_KEY=None,
            VOLCANO_VIDEO_GENERATION_URL=None,
            VOLCANO_VIDEO_MODEL=None,
            CUSTOM_VIDEO_API_KEY=None,
            CUSTOM_VIDEO_GENERATION_URL=None,
            CUSTOM_VIDEO_MODEL=None,
        ):
            with TestClient(commercial_main.app) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "member@example.com", "password": "password1", "invite_code": "secret"},
                )
                response = client.post(
                    "/api/tasks",
                    json={
                        "kind": "video",
                        "prompt": "animate @主体1",
                        "options": {
                            "model": "doubao-seedance-2-0-260128",
                            "mode": "image_to_video",
                            "first_last_frame": True,
                            "first_frame_asset_id": "first-image",
                            "strong_reference_asset_id": "subject-image",
                            "last_frame_asset_id": "last-image",
                            "strong_reference_alias": "主体",
                        },
                    },
                )
                balance = client.get("/api/me").json()["user"]["credits"]

        self.assertEqual(registered.status_code, 200)
        self.assertEqual(response.status_code, 400)
        self.assertIn("不能与首尾帧模式同时使用", response.json()["detail"])
        self.assertEqual(balance, 100)

    def test_video_task_accepts_owned_strong_reference_and_persists_explicit_roles(self):
        with EnvPatch(
            INVITE_CODE="secret",
            DEFAULT_CREDITS="100",
            AUTO_ADMIN_FIRST_USER="0",
            TASK_WORKER_ENABLED="0",
            VIDEO_API_KEY="video-key",
            VIDEO_GENERATION_URL="https://video.example.test/generations",
            VIDEO_MODEL="doubao-seedance-2-0-260128",
            VOLCANO_VIDEO_API_KEY=None,
            VOLCANO_VIDEO_GENERATION_URL=None,
            VOLCANO_VIDEO_MODEL=None,
            CUSTOM_VIDEO_API_KEY=None,
            CUSTOM_VIDEO_GENERATION_URL=None,
            CUSTOM_VIDEO_MODEL=None,
        ):
            with TestClient(commercial_main.app) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "member@example.com", "password": "password1", "invite_code": "secret"},
                )
                user_id = registered.json()["user"]["id"]
                with commercial_main.db() as conn:
                    for index, asset_id in enumerate(("first-image", "subject-image")):
                        path = pathlib.Path(commercial_main.user_storage_path(user_id)) / f"{asset_id}.png"
                        Image.new("RGB", (64, 48), (20 + index * 80, 120, 180)).save(path)
                        conn.execute(
                            "INSERT INTO assets (id, user_id, name, kind, path, url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (asset_id, user_id, path.name, "image", str(path), f"/api/assets/{asset_id}", index + 1),
                        )
                response = client.post(
                    "/api/tasks",
                    json={
                        "kind": "video",
                        "prompt": "@图片1 跟随 @主体1",
                        "options": {
                            "model": "doubao-seedance-2-0-260128",
                            "mode": "image_to_video",
                            "first_frame_asset_id": "first-image",
                            "strong_reference_asset_id": "subject-image",
                            "strong_reference_alias": "主体",
                        },
                    },
                )

        self.assertEqual(response.status_code, 200)
        task = response.json()["task"]
        self.assertEqual(task["options"]["first_frame_asset_id"], "first-image")
        self.assertEqual(task["options"]["strong_reference_asset_id"], "subject-image")
        self.assertEqual(task["options"]["strong_reference_alias"], "主体")
        self.assertEqual(response.json()["balance"], 60)

    def test_admin_provider_routes_reject_members_main_host_and_unsafe_urls(self):
        with EnvPatch(
            ADMIN_HOST="admin.canvas.example",
            INVITE_CODE="secret",
            AUTO_ADMIN_FIRST_USER="1",
            TASK_WORKER_ENABLED="0",
            APP_ENV="development",
            CANVAS_PRODUCTION="0",
            CONFIG_ENCRYPTION_KEY="test-config-encryption-key",
        ):
            with TestClient(commercial_main.app, base_url="https://canvas.example") as main_client:
                admin = main_client.post(
                    "/api/auth/register",
                    json={"email": "admin@example.com", "password": "password1", "invite_code": "secret"},
                ).json()["user"]
                main_client.post("/api/auth/logout")
                member = main_client.post(
                    "/api/auth/register",
                    json={"email": "member@example.com", "password": "password1", "invite_code": "secret"},
                ).json()["user"]
                main_host = main_client.get("/api/admin/providers")
                main_host_models = main_client.post(
                    "/api/admin/providers/image/%E8%87%AA%E5%AE%9A%E4%B9%89/models"
                )

            with TestClient(commercial_main.app, base_url="https://admin.canvas.example") as admin_client:
                signed_out = admin_client.get("/api/admin/providers")
                signed_out_models = admin_client.post(
                    "/api/admin/providers/image/%E8%87%AA%E5%AE%9A%E4%B9%89/models"
                )
                member_login = admin_client.post(
                    "/api/auth/login",
                    json={"email": member["email"], "password": "password1"},
                )
                admin_client.post(
                    "/api/auth/login",
                    json={"email": admin["email"], "password": "password1"},
                )
                deployment = admin_client.put(
                    "/api/admin/providers/image/%E8%87%AA%E5%AE%9A%E4%B9%89",
                    json={
                        "url": "https://images.example.test/openai/deployments/gpt-image-2/images/generations",
                        "model": "",
                    },
                )
                deployment_models = admin_client.post(
                    "/api/admin/providers/image/%E8%87%AA%E5%AE%9A%E4%B9%89/models"
                )
                unsafe = admin_client.put(
                    "/api/admin/providers/video/%E8%87%AA%E5%AE%9A%E4%B9%89",
                    json={
                        "api_key": "should-not-be-saved",
                        "url": "http://169.254.169.254/latest/meta-data",
                        "status_url_template": "https://video.example.test/tasks/{task_id}",
                    },
                )
                missing_task_id = admin_client.put(
                    "/api/admin/providers/video/%E8%87%AA%E5%AE%9A%E4%B9%89",
                    json={"status_url_template": "https://video.example.test/tasks/status"},
                )
                invalid_slot = admin_client.put(
                    "/api/admin/providers/audio/custom",
                    json={"url": "https://audio.example.test/generations"},
                )

        self.assertEqual(main_host.status_code, 404)
        self.assertEqual(main_host_models.status_code, 404)
        self.assertEqual(signed_out.status_code, 401)
        self.assertEqual(signed_out_models.status_code, 401)
        self.assertEqual(member_login.status_code, 403)
        self.assertEqual(unsafe.status_code, 400)
        self.assertEqual(missing_task_id.status_code, 400)
        self.assertEqual(invalid_slot.status_code, 400)
        self.assertEqual(deployment.status_code, 200)
        self.assertEqual(deployment_models.status_code, 200)
        self.assertEqual(deployment_models.json()["models"], ["gpt-image-2"])
        self.assertFalse(deployment_models.json()["complete"])
        self.assertNotIn("should-not-be-saved", unsafe.text)

    def test_admin_portal_uses_independent_host_and_rejects_members(self):
        with EnvPatch(
            ADMIN_HOST="admin.canvas.example",
            INVITE_CODE="secret",
            AUTO_ADMIN_FIRST_USER="1",
            TASK_WORKER_ENABLED="0",
        ):
            with TestClient(commercial_main.app, base_url="https://canvas.example") as main_client:
                admin = main_client.post(
                    "/api/auth/register",
                    json={"email": "admin@example.com", "password": "password1", "invite_code": "secret"},
                ).json()["user"]
                main_client.post("/api/auth/logout")
                member = main_client.post(
                    "/api/auth/register",
                    json={"email": "member@example.com", "password": "password1", "invite_code": "secret"},
                ).json()["user"]
                main_client.post("/api/auth/logout")

                main_admin_page = main_client.get("/admin", follow_redirects=False)
                main_client.post(
                    "/api/auth/login",
                    json={"email": admin["email"], "password": "password1"},
                )
                account = main_client.get("/api/me").json()
                main_admin_api = main_client.get("/api/admin/users")

            with TestClient(commercial_main.app, base_url="https://admin.canvas.example") as admin_client:
                signed_out_page = admin_client.get("/admin", follow_redirects=False)
                register_page = admin_client.get("/register", follow_redirects=False)
                register_api = admin_client.post(
                    "/api/auth/register",
                    json={"email": "blocked@example.com", "password": "password1", "invite_code": "secret"},
                )
                member_login = admin_client.post(
                    "/api/auth/login",
                    json={"email": member["email"], "password": "password1"},
                )
                admin_login = admin_client.post(
                    "/api/auth/login",
                    json={"email": admin["email"], "password": "password1"},
                )
                admin_page = admin_client.get("/admin")
                admin_users = admin_client.get("/api/admin/users")

        self.assertEqual(main_admin_page.status_code, 404)
        self.assertEqual(main_admin_api.status_code, 404)
        self.assertEqual(account["admin_url"], "https://admin.canvas.example/admin")
        self.assertEqual(signed_out_page.status_code, 303)
        self.assertEqual(signed_out_page.headers["location"], "/login")
        self.assertEqual(register_page.status_code, 303)
        self.assertEqual(register_page.headers["location"], "/login")
        self.assertEqual(register_api.status_code, 404)
        self.assertEqual(member_login.status_code, 403)
        self.assertNotIn("set-cookie", member_login.headers)
        self.assertEqual(admin_login.status_code, 200)
        self.assertEqual(admin_page.status_code, 200)
        self.assertEqual(admin_users.status_code, 200)
        self.assertEqual({user["email"] for user in admin_users.json()["users"]}, {admin["email"], member["email"]})

    def test_admin_users_aggregates_task_usage_per_user(self):
        with EnvPatch(
            INVITE_CODE="secret",
            DEFAULT_CREDITS="100",
            AUTO_ADMIN_FIRST_USER="1",
            TASK_WORKER_ENABLED="0",
        ):
            with TestClient(commercial_main.app) as client:
                admin = client.post(
                    "/api/auth/register",
                    json={"email": "admin@example.com", "password": "password1", "invite_code": "secret"},
                ).json()["user"]
                client.post("/api/auth/logout")
                first_user = client.post(
                    "/api/auth/register",
                    json={"email": "first@example.com", "password": "password1", "invite_code": "secret"},
                ).json()["user"]
                client.post("/api/auth/logout")
                second_user = client.post(
                    "/api/auth/register",
                    json={"email": "second@example.com", "password": "password1", "invite_code": "secret"},
                ).json()["user"]
                client.post("/api/auth/logout")

                task_rows = [
                    ("first-llm-success", first_user["id"], "llm", 3, "succeeded", 0, 1000),
                    ("first-image-success", first_user["id"], "image", 5, "succeeded", 0, 2000),
                    ("first-video-refund", first_user["id"], "video", 7, "failed", 1, 3000),
                    ("first-image-queued", first_user["id"], "image", 11, "queued", 0, 4000),
                    ("first-video-running", first_user["id"], "video", 13, "running", 0, 5000),
                    ("first-llm-failed", first_user["id"], "llm", 17, "failed", 0, 6000),
                    ("second-video-success", second_user["id"], "video", 23, "succeeded", 0, 7000),
                    ("second-image-refund", second_user["id"], "image", 29, "failed", 1, 8000),
                ]
                with commercial_main.db() as conn:
                    conn.executemany(
                        "INSERT INTO tasks (id, user_id, kind, prompt, cost, status, refunded, created_at, updated_at) "
                        "VALUES (?, ?, ?, 'test', ?, ?, ?, ?, ?)",
                        [row + (row[-1],) for row in task_rows],
                    )

                client.post(
                    "/api/auth/login",
                    json={"email": "admin@example.com", "password": "password1"},
                )
                before_recharge_response = client.get("/api/admin/users")
                before_recharge = {
                    item["email"]: item for item in before_recharge_response.json()["users"]
                }
                recharged = client.post(
                    f"/api/admin/users/{first_user['id']}/credits",
                    json={"delta": 40, "reason": "manual recharge"},
                )
                response = client.get("/api/admin/users")

        self.assertEqual(before_recharge_response.status_code, 200)
        self.assertEqual(recharged.status_code, 200)
        self.assertEqual(recharged.json()["balance"], 140)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("password_hash", response.text)

        users = {item["email"]: item for item in response.json()["users"]}
        self.assertEqual(set(users), {"admin@example.com", "first@example.com", "second@example.com"})
        self.assertEqual(
            {key: users["first@example.com"][key] for key in (
                "task_count",
                "succeeded_count",
                "failed_count",
                "active_count",
                "consumed_credits",
                "pending_credits",
                "refunded_credits",
                "llm_credits",
                "image_credits",
                "video_credits",
                "last_task_at",
            )},
            {
                "task_count": 6,
                "succeeded_count": 2,
                "failed_count": 2,
                "active_count": 2,
                "consumed_credits": 8,
                "pending_credits": 24,
                "refunded_credits": 7,
                "llm_credits": 3,
                "image_credits": 5,
                "video_credits": 0,
                "last_task_at": 6000,
            },
        )
        self.assertEqual(users["first@example.com"]["credits"], 140)
        self.assertEqual(users["second@example.com"]["task_count"], 2)
        self.assertEqual(users["second@example.com"]["succeeded_count"], 1)
        self.assertEqual(users["second@example.com"]["failed_count"], 1)
        self.assertEqual(users["second@example.com"]["active_count"], 0)
        self.assertEqual(users["second@example.com"]["consumed_credits"], 23)
        self.assertEqual(users["second@example.com"]["pending_credits"], 0)
        self.assertEqual(users["second@example.com"]["refunded_credits"], 29)
        self.assertEqual(users["second@example.com"]["llm_credits"], 0)
        self.assertEqual(users["second@example.com"]["image_credits"], 0)
        self.assertEqual(users["second@example.com"]["video_credits"], 23)
        self.assertEqual(users["second@example.com"]["last_task_at"], 8000)
        self.assertEqual(users["admin@example.com"]["task_count"], 0)
        self.assertEqual(users["admin@example.com"]["consumed_credits"], 0)
        self.assertIsNone(users["admin@example.com"]["last_task_at"])
        for field in (
            "task_count",
            "succeeded_count",
            "failed_count",
            "active_count",
            "consumed_credits",
            "pending_credits",
            "refunded_credits",
            "llm_credits",
            "image_credits",
            "video_credits",
            "last_task_at",
        ):
            self.assertEqual(before_recharge["first@example.com"][field], users["first@example.com"][field])

    def test_delete_canvas_removes_workspace_but_preserves_uploaded_assets(self):
        with EnvPatch(INVITE_CODE="secret"):
            with TestClient(commercial_main.app) as client:
                client.post(
                    "/api/auth/register",
                    json={"email": "delete-canvas@example.com", "password": "password1", "invite_code": "secret"},
                )
                project = client.post("/api/projects", json={"name": "Campaign"}).json()["project"]
                canvas = client.post(
                    f"/api/projects/{project['id']}/canvases",
                    json={"name": "Storyboard"},
                ).json()["canvas"]
                uploaded = client.post(
                    f"/api/uploads?project_id={project['id']}&canvas_id={canvas['id']}",
                    files={"file": ("reference.png", b"\x89PNG\r\n\x1a\nasset", "image/png")},
                ).json()["asset"]

                deleted = client.delete(f"/api/canvases/{canvas['id']}")

                self.assertEqual(deleted.status_code, 200)
                self.assertEqual(deleted.json(), {"ok": True})
                self.assertEqual(client.get(f"/api/canvases/{canvas['id']}").status_code, 404)
                self.assertEqual(
                    client.get(f"/api/projects/{project['id']}/canvases").json()["canvases"],
                    [],
                )
                assets = {item["id"]: item for item in client.get("/api/assets").json()["assets"]}
                self.assertIn(uploaded["id"], assets)
                self.assertEqual(assets[uploaded["id"]]["project_id"], project["id"])
                self.assertEqual(assets[uploaded["id"]]["canvas_id"], "")

    def test_upload_rejects_a_canvas_that_was_already_deleted(self):
        with EnvPatch(INVITE_CODE="secret"):
            with TestClient(commercial_main.app) as client:
                client.post(
                    "/api/auth/register",
                    json={"email": "deleted-upload@example.com", "password": "password1", "invite_code": "secret"},
                )
                project = client.post("/api/projects", json={"name": "Campaign"}).json()["project"]
                canvas = client.post(
                    f"/api/projects/{project['id']}/canvases",
                    json={"name": "Storyboard"},
                ).json()["canvas"]
                self.assertEqual(client.delete(f"/api/canvases/{canvas['id']}").status_code, 200)

                uploaded = client.post(
                    f"/api/uploads?project_id={project['id']}&canvas_id={canvas['id']}",
                    files={"file": ("reference.png", b"\x89PNG\r\n\x1a\nasset", "image/png")},
                )

                self.assertEqual(uploaded.status_code, 404)
                self.assertEqual(client.get("/api/assets").json()["assets"], [])

    def test_delete_project_removes_its_canvases_but_preserves_uploaded_assets(self):
        with EnvPatch(INVITE_CODE="secret"):
            with TestClient(commercial_main.app) as client:
                client.post(
                    "/api/auth/register",
                    json={"email": "delete-project@example.com", "password": "password1", "invite_code": "secret"},
                )
                project = client.post("/api/projects", json={"name": "Launch"}).json()["project"]
                first = client.post(
                    f"/api/projects/{project['id']}/canvases",
                    json={"name": "Board A"},
                ).json()["canvas"]
                second = client.post(
                    f"/api/projects/{project['id']}/canvases",
                    json={"name": "Board B"},
                ).json()["canvas"]
                uploaded = client.post(
                    f"/api/uploads?project_id={project['id']}&canvas_id={first['id']}",
                    files={"file": ("reference.png", b"\x89PNG\r\n\x1a\nasset", "image/png")},
                ).json()["asset"]

                deleted = client.delete(f"/api/projects/{project['id']}")

                self.assertEqual(deleted.status_code, 200)
                self.assertEqual(deleted.json(), {"ok": True, "deleted_canvas_count": 2})
                self.assertEqual(client.get("/api/projects").json()["projects"], [])
                self.assertEqual(client.get(f"/api/canvases/{first['id']}").status_code, 404)
                self.assertEqual(client.get(f"/api/canvases/{second['id']}").status_code, 404)
                assets = {item["id"]: item for item in client.get("/api/assets").json()["assets"]}
                self.assertIn(uploaded["id"], assets)
                self.assertEqual(assets[uploaded["id"]]["project_id"], "")
                self.assertEqual(assets[uploaded["id"]]["canvas_id"], "")

    def test_project_and_canvas_delete_are_scoped_to_the_signed_in_user(self):
        with EnvPatch(INVITE_CODE="secret"):
            with TestClient(commercial_main.app) as client:
                client.post(
                    "/api/auth/register",
                    json={"email": "owner-delete@example.com", "password": "password1", "invite_code": "secret"},
                )
                project = client.post("/api/projects", json={"name": "Private"}).json()["project"]
                canvas = client.post(
                    f"/api/projects/{project['id']}/canvases",
                    json={"name": "Private Board"},
                ).json()["canvas"]
                client.post("/api/auth/logout")
                client.post(
                    "/api/auth/register",
                    json={"email": "other-delete@example.com", "password": "password1", "invite_code": "secret"},
                )

                self.assertEqual(client.delete(f"/api/canvases/{canvas['id']}").status_code, 404)
                self.assertEqual(client.delete(f"/api/projects/{project['id']}").status_code, 404)

                client.post("/api/auth/logout")
                client.post(
                    "/api/auth/login",
                    json={"email": "owner-delete@example.com", "password": "password1"},
                )
                self.assertEqual(client.get(f"/api/canvases/{canvas['id']}").status_code, 200)
                project_ids = {item["id"] for item in client.get("/api/projects").json()["projects"]}
                self.assertIn(project["id"], project_ids)

    def test_project_and_canvas_delete_wait_for_active_generation_tasks(self):
        with EnvPatch(INVITE_CODE="secret"):
            with TestClient(commercial_main.app) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "active-delete@example.com", "password": "password1", "invite_code": "secret"},
                ).json()["user"]
                project = client.post("/api/projects", json={"name": "Active"}).json()["project"]
                canvas = client.post(
                    f"/api/projects/{project['id']}/canvases",
                    json={"name": "Rendering"},
                ).json()["canvas"]
                timestamp = commercial_main.now_ms()
                with commercial_main.db() as conn:
                    conn.execute(
                        "INSERT INTO tasks (id, user_id, kind, prompt, status, canvas_id, lease_until, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, 'running', ?, ?, ?, ?)",
                        ("active-delete-task", registered["id"], "image", "render", canvas["id"], timestamp + 60000, timestamp, timestamp),
                    )

                canvas_delete = client.delete(f"/api/canvases/{canvas['id']}")
                project_delete = client.delete(f"/api/projects/{project['id']}")

                self.assertEqual(canvas_delete.status_code, 409)
                self.assertIn("任务", canvas_delete.json()["detail"])
                self.assertEqual(project_delete.status_code, 409)
                self.assertIn("任务", project_delete.json()["detail"])

    def test_upload_rejects_non_media_and_accepts_image(self):
        with EnvPatch(INVITE_CODE="secret"):
            with TestClient(commercial_main.app) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "media@example.com", "password": "password1", "invite_code": "secret"},
                )
                self.assertEqual(registered.status_code, 200)

                project = client.post("/api/projects", json={"name": "Assets"}).json()["project"]
                canvas = client.post(f"/api/projects/{project['id']}/canvases", json={"name": "Board"}).json()["canvas"]

                rejected = client.post(
                    f"/api/uploads?project_id={project['id']}&canvas_id={canvas['id']}",
                    files={"file": ("note.txt", b"hello", "text/plain")},
                )
                self.assertEqual(rejected.status_code, 415)

                uploaded = client.post(
                    f"/api/uploads?project_id={project['id']}&canvas_id={canvas['id']}",
                    files={"file": ("reference.png", b"\x89PNG\r\n\x1a\n", "image/png")},
                )
                self.assertEqual(uploaded.status_code, 200)
                self.assertEqual(uploaded.json()["asset"]["kind"], "image")

    def test_upload_rejects_spoofed_image_content(self):
        with EnvPatch(INVITE_CODE="secret"):
            with TestClient(commercial_main.app) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "spoof@example.com", "password": "password1", "invite_code": "secret"},
                )
                self.assertEqual(registered.status_code, 200)

                spoofed = client.post(
                    "/api/uploads",
                    files={"file": ("fake.png", b"not really a png", "image/png")},
                )
                self.assertEqual(spoofed.status_code, 415)

    def test_uploaded_asset_opens_inline_in_browser(self):
        with EnvPatch(INVITE_CODE="secret"):
            with TestClient(commercial_main.app) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "inline@example.com", "password": "password1", "invite_code": "secret"},
                )
                self.assertEqual(registered.status_code, 200)

                uploaded = client.post(
                    "/api/uploads",
                    files={"file": ("reference.png", b"\x89PNG\r\n\x1a\nasset", "image/png")},
                )
                self.assertEqual(uploaded.status_code, 200)

                opened = client.get(uploaded.json()["asset"]["url"])
                self.assertEqual(opened.status_code, 200)
                self.assertEqual(opened.headers["content-type"], "image/png")
                self.assertTrue(opened.headers["content-disposition"].lower().startswith("inline;"))

                downloaded = client.get(f'{uploaded.json()["asset"]["url"]}?download=1')
                self.assertEqual(downloaded.status_code, 200)
                self.assertEqual(downloaded.headers["content-type"], "image/png")
                self.assertTrue(downloaded.headers["content-disposition"].lower().startswith("attachment;"))

    def test_generated_asset_download_name_keeps_media_extension(self):
        with EnvPatch(INVITE_CODE="secret"):
            with TestClient(commercial_main.app) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "generated-download@example.com", "password": "password1", "invite_code": "secret"},
                )
                user_id = registered.json()["user"]["id"]
                path = pathlib.Path(commercial_main.user_storage_path(user_id)) / "generated.mp4"
                path.write_bytes(b"\x00\x00\x00\x18ftypisom")
                with commercial_main.db() as conn:
                    conn.execute(
                        "INSERT INTO assets (id, user_id, name, kind, path, url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        ("generated-video", user_id, "视频生成结果", "video", str(path), "/api/assets/generated-video", 1),
                    )

                downloaded = client.get("/api/assets/generated-video?download=1")

        self.assertEqual(downloaded.status_code, 200)
        disposition = downloaded.headers["content-disposition"].lower()
        self.assertTrue(disposition.startswith("attachment;"))
        self.assertIn(".mp4", disposition)

    def test_security_headers_are_set_on_html_responses(self):
        with TestClient(commercial_main.app) as client:
            res = client.get("/login")

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["x-content-type-options"], "nosniff")
        self.assertEqual(res.headers["x-frame-options"], "DENY")
        self.assertIn("default-src 'self'", res.headers["content-security-policy"])

    def test_favicon_route_is_available(self):
        with TestClient(commercial_main.app) as client:
            res = client.get("/favicon.ico")

        self.assertEqual(res.status_code, 200)
        self.assertIn("image/", res.headers["content-type"])
        self.assertGreater(len(res.content), 100)

    def test_login_rate_limits_repeated_failures(self):
        with EnvPatch(INVITE_CODE="secret", AUTH_RATE_LIMIT_MAX="2", AUTH_RATE_LIMIT_WINDOW_SECONDS="60"):
            with TestClient(commercial_main.app) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "limited@example.com", "password": "password1", "invite_code": "secret"},
                )
                self.assertEqual(registered.status_code, 200)
                client.post("/api/auth/logout")

                for _index in range(2):
                    failed = client.post(
                        "/api/auth/login",
                        json={"email": "limited@example.com", "password": "wrong-password"},
                    )
                    self.assertEqual(failed.status_code, 401)

                limited = client.post(
                    "/api/auth/login",
                    json={"email": "limited@example.com", "password": "wrong-password"},
                )
                self.assertEqual(limited.status_code, 429)

    def test_account_storage_asset_delete_and_password_change_flow(self):
        with EnvPatch(INVITE_CODE="secret", MAX_USER_STORAGE_MB="1"):
            with TestClient(commercial_main.app) as client:
                registered = client.post(
                    "/api/auth/register",
                    json={"email": "account@example.com", "password": "password1", "invite_code": "secret"},
                )
                self.assertEqual(registered.status_code, 200)

                uploaded = client.post(
                    "/api/uploads",
                    files={"file": ("reference.png", b"\x89PNG\r\n\x1a\nasset", "image/png")},
                )
                self.assertEqual(uploaded.status_code, 200)
                asset_id = uploaded.json()["asset"]["id"]

                account = client.get("/api/me").json()
                self.assertGreater(account["storage"]["used_bytes"], 0)
                asset = client.get("/api/assets").json()["assets"][0]
                self.assertNotIn("path", asset)

                deleted = client.delete(f"/api/assets/{asset_id}")
                self.assertEqual(deleted.status_code, 200)
                self.assertEqual(deleted.json()["storage"]["used_bytes"], 0)

                changed = client.post(
                    "/api/account/password",
                    json={"current_password": "password1", "new_password": "new-password2"},
                )
                self.assertEqual(changed.status_code, 200)
                client.post("/api/auth/logout")
                self.assertEqual(
                    client.post(
                        "/api/auth/login",
                        json={"email": "account@example.com", "password": "password1"},
                    ).status_code,
                    401,
                )
                self.assertEqual(
                    client.post(
                        "/api/auth/login",
                        json={"email": "account@example.com", "password": "new-password2"},
                    ).status_code,
                    200,
                )


if __name__ == "__main__":
    unittest.main()
