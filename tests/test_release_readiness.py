import importlib.util
import json
import pathlib
import tempfile
import unittest

from PIL import Image


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
                "static/brand/yunzhi-avatar.webp",
                "static/brand/yunzhi-ip.png",
                "static/brand/yunzhi-ip.webp",
                "static/demo/yunzhi-generated-character.png",
                "static/demo/yunzhi-seedance-story.mp4",
                "static/ecommerce/scenes/outdoor-scenes-contact-sheet.png",
                "static/ecommerce/scenes/white-studio-example.png",
                "static/vendor/phosphor/phosphor.css",
                "static/vendor/phosphor/Phosphor.woff2",
                "Dockerfile",
                "README.md",
            ]:
                self.assertIn(required, copied_paths)
                self.assertTrue((bundle_dir / required).exists())

            for forbidden in [".env", "data", "storage", "output", "__pycache__", "server-commercial.out.log"]:
                self.assertFalse((bundle_dir / forbidden).exists(), forbidden)

            catalog = json.loads(
                (ROOT / "static" / "ecommerce" / "models" / "manifest.json").read_text(encoding="utf-8")
            )
            for model in catalog["models"]:
                relative_image = model["image"].removeprefix("/")
                self.assertIn(relative_image, copied_paths)
                self.assertTrue((bundle_dir / relative_image).exists())

    def test_brand_webp_assets_are_valid_and_materially_smaller(self):
        brand_dir = ROOT / "static" / "brand"
        cases = [
            ("yunzhi-avatar", (256, 256)),
            ("yunzhi-ip", (1448, 1086)),
        ]
        for stem, expected_size in cases:
            with self.subTest(asset=stem):
                png_path = brand_dir / f"{stem}.png"
                webp_path = brand_dir / f"{stem}.webp"
                self.assertTrue(png_path.exists())
                self.assertTrue(webp_path.exists())
                self.assertLess(webp_path.stat().st_size, png_path.stat().st_size * 0.1)
                with Image.open(webp_path) as image:
                    self.assertEqual("WEBP", image.format)
                    self.assertEqual(expected_size, image.size)
                    self.assertEqual(("R", "G", "B"), image.getbands())

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
