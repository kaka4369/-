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

            for required in [
                "main.py",
                "static/app.css",
                "static/auth.html",
                "static/brand/yunzhi-avatar.png",
                "static/brand/yunzhi-ip.png",
                "static/demo/yunzhi-generated-character.png",
                "static/demo/yunzhi-seedance-story.mp4",
                "static/vendor/phosphor/phosphor.css",
                "static/vendor/phosphor/Phosphor.woff2",
                "Dockerfile",
                "README.md",
            ]:
                self.assertIn(required, copied_paths)
                self.assertTrue((bundle_dir / required).exists())

            for forbidden in [".env", "data", "storage", "output", "__pycache__", "server-commercial.out.log"]:
                self.assertFalse((bundle_dir / forbidden).exists(), forbidden)

    def test_container_uses_dynamic_port_and_standard_library_healthcheck(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("${PORT:-3020}", dockerfile)
        self.assertNotIn('["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3020"]', dockerfile)
        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn("urllib.request", dockerfile)
        self.assertIn("/readyz", dockerfile)
        self.assertNotIn("curl ", dockerfile)


if __name__ == "__main__":
    unittest.main()
