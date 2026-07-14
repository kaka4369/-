import importlib.util
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_bundle", ROOT / "scripts" / "build_release_bundle.py")


class ReleaseReadinessTest(unittest.TestCase):
    def test_release_manifest_and_builder_exist(self):
        self.assertTrue((ROOT / "release_manifest.json").exists())
        self.assertTrue((ROOT / "scripts" / "build_release_bundle.py").exists())
        self.assertTrue((ROOT / "docs" / "PRODUCTION_RUNBOOK.md").exists())

    def test_release_bundle_uses_allowlist_and_excludes_runtime_state(self):
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            bundle_dir = pathlib.Path(tmp) / "bundle"
            copied = module.build_bundle(ROOT, bundle_dir)
            copied_paths = {path.as_posix() for path in copied}

            for required in ["main.py", "static/app.css", "static/auth.html", "Dockerfile", "README.md"]:
                self.assertIn(required, copied_paths)
                self.assertTrue((bundle_dir / required).exists())

            for forbidden in [".env", "data", "storage", "output", "__pycache__", "server-commercial.out.log"]:
                self.assertFalse((bundle_dir / forbidden).exists(), forbidden)


if __name__ == "__main__":
    unittest.main()
