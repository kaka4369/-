import importlib.util
import os
import pathlib
import tempfile
import unittest


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
            {"canvas_id": canvas["id"], "node_id": "node_1"},
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


if __name__ == "__main__":
    unittest.main()
