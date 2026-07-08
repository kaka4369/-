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


if __name__ == "__main__":
    unittest.main()
