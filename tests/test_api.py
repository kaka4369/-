import importlib.util
import os
import pathlib
import tempfile
import unittest

from fastapi.testclient import TestClient


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
