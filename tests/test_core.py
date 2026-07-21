import importlib.util
import asyncio
import base64
import io
import json
import os
import pathlib
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from PIL import Image


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

    def test_bundled_demo_media_is_local_and_kind_scoped(self):
        image = commercial_main.bundled_demo_media("image")
        video = commercial_main.bundled_demo_media("video")

        self.assertTrue(image.is_file())
        self.assertTrue(video.is_file())
        self.assertEqual(image.name, "yunzhi-generated-character.png")
        self.assertEqual(video.name, "yunzhi-seedance-story.mp4")
        with self.assertRaisesRegex(commercial_main.AppError, "不支持的演示媒体类型"):
            commercial_main.bundled_demo_media("audio")

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
        self.assertNotIn("provider", task["options"])
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
        self.assertNotIn("fps", video_payload)
        self.assertTrue(video_payload["fixed_camera"])

    def test_lingjing_video_payload_uses_structured_content(self):
        reference = "data:image/png;base64,AAAA"

        payload = commercial_main.build_video_payload(
            "slow camera push-in",
            {
                "provider": "灵境API",
                "model": "doubao-seedance-2-0-260128",
                "mode": "image_to_video",
                "duration": 15,
                "aspect_ratio": "16:9",
                "resolution": "1080p",
                "output_fps": 60,
                "generate_audio": False,
            },
            reference_images=[reference],
        )

        self.assertEqual(payload["model"], "doubao-seedance-2-0-260128")
        self.assertEqual(payload["prompt"], "slow camera push-in")
        self.assertEqual(payload["content"][0], {"type": "text", "text": "slow camera push-in"})
        self.assertEqual(
            payload["content"][1],
            {
                "type": "image_url",
                "image_url": {"url": reference},
                "role": "first_frame",
            },
        )
        self.assertEqual(payload["ratio"], "16:9")
        self.assertEqual(payload["duration"], 15)
        self.assertEqual(payload["resolution"], "1080p")
        self.assertFalse(payload["generate_audio"])
        self.assertNotIn("mode", payload)
        self.assertNotIn("aspect_ratio", payload)
        self.assertNotIn("framespersecond", payload)

    def test_lingjing_video_payload_uses_explicit_roles_and_resolves_strong_alias(self):
        payload = commercial_main.build_video_payload(
            "让 @图片1 中的画面跟随 @主体1\n保持人物一致",
            {
                "provider": "灵境API",
                "model": "doubao-seedance-2-0-260128",
                "mode": "image_to_video",
                "strong_reference_alias": "主体",
            },
            reference_images={
                "reference_image": "data:image/png;base64,SUBJECT",
                "first_frame": "data:image/png;base64,FIRST",
            },
        )

        self.assertEqual(payload["prompt"], "让 @图片1 中的画面跟随 @图片2 保持人物一致")
        self.assertEqual(payload["content"][0]["text"], payload["prompt"])
        self.assertEqual(
            [(item["role"], item["image_url"]["url"]) for item in payload["content"][1:]],
            [
                ("reference_image", "data:image/png;base64,FIRST"),
                ("reference_image", "data:image/png;base64,SUBJECT"),
            ],
        )

    def test_lingjing_first_last_frames_use_frame_roles_without_reference_media(self):
        payload = commercial_main.build_video_payload(
            "transition",
            {
                "provider": "灵境API",
                "model": "doubao-seedance-2-0-260128",
                "mode": "image_to_video",
                "first_last_frame": True,
            },
            reference_images={
                "first_frame": "data:image/png;base64,FIRST",
                "last_frame": "data:image/png;base64,LAST",
            },
        )

        self.assertEqual(
            [item["role"] for item in payload["content"][1:]],
            ["first_frame", "last_frame"],
        )

    def test_lingjing_rejects_mixed_strong_reference_and_frame_roles(self):
        with self.assertRaisesRegex(commercial_main.AppError, "不能与首尾帧模式同时使用"):
            commercial_main.build_video_payload(
                "animate",
                {
                    "provider": "灵境API",
                    "model": "doubao-seedance-2-0-260128",
                    "mode": "image_to_video",
                    "first_last_frame": True,
                    "strong_reference_alias": "主体",
                },
                reference_images={
                    "first_frame": "data:image/png;base64,FIRST",
                    "reference_image": "data:image/png;base64,SUBJECT",
                    "last_frame": "data:image/png;base64,LAST",
                },
            )

    def test_strong_alias_is_removed_without_an_actual_strong_reference(self):
        payload = commercial_main.build_video_payload(
            "让 @主体1 向镜头走来",
            {
                "provider": "灵境API",
                "model": "doubao-seedance-2-0-260128",
                "mode": "image_to_video",
                "strong_reference_alias": "主体",
            },
            reference_images={"first_frame": "data:image/png;base64,FIRST"},
        )

        self.assertEqual(payload["prompt"], "让 向镜头走来")

    def test_video_output_fps_is_applied_locally_after_download(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("video-fps@example.com", "password1", "secret")

        task = {
            "id": "video_fps_task",
            "user_id": user["id"],
            "kind": "video",
            "prompt": "animate",
            "canvas_id": "",
            "node_id": "video_node",
            "options": {"output_fps": 60},
        }
        calls = []

        async def fake_stream(_url, _kind, temporary, _user_id):
            temporary.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_bytes(b"\x00\x00\x00\x18ftypisomsource")
            return ".mp4", temporary.stat().st_size

        async def fake_interpolate(source, target, target_fps):
            calls.append((source, target, target_fps))
            target.write_bytes(source.read_bytes() + b"-interpolated")

        with patch.object(commercial_main, "stream_generated_media_to_path", new=fake_stream), patch.object(
            commercial_main,
            "interpolate_video_file",
            new=fake_interpolate,
        ):
            result = asyncio.run(
                commercial_main.persist_generated_assets(
                    task,
                    {"video_url": "https://cdn.example/source.mp4"},
                )
            )

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][2], 60)
        self.assertEqual(result["frame_interpolation"]["target_fps"], 60)
        with commercial_main.db() as conn:
            row = conn.execute(
                "SELECT path FROM assets WHERE user_id = ? AND id = ?",
                (user["id"], "task_video_fps_task_0"),
            ).fetchone()
        self.assertTrue(pathlib.Path(row["path"]).read_bytes().endswith(b"-interpolated"))

    def test_video_reference_assets_are_owner_scoped_and_encoded(self):
        with EnvPatch(INVITE_CODE="secret"):
            owner = commercial_main.register_user("owner@example.com", "password1", "secret")
            stranger = commercial_main.register_user("stranger@example.com", "password1", "secret")

        owner_path = pathlib.Path(commercial_main.user_storage_path(owner["id"])) / "reference.png"
        Image.new("RGB", (64, 48), (20, 120, 180)).save(owner_path)
        with commercial_main.db() as conn:
            conn.execute(
                "INSERT INTO assets (id, user_id, name, kind, path, url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("owner_image", owner["id"], "reference.png", "image", str(owner_path), "/api/assets/owner_image", 1),
            )

        references = commercial_main.resolve_video_reference_images(owner["id"], ["owner_image"])

        self.assertEqual(len(references), 1)
        self.assertTrue(references[0].startswith("data:image/jpeg;base64,"))
        self.assertTrue(base64.b64decode(references[0].split(",", 1)[1]).startswith(b"\xff\xd8"))
        with self.assertRaisesRegex(commercial_main.AppError, "素材不存在"):
            commercial_main.resolve_video_reference_images(stranger["id"], ["owner_image"])

    def test_video_reference_assets_are_resolved_by_explicit_role(self):
        with EnvPatch(INVITE_CODE="secret"):
            owner = commercial_main.register_user("roles@example.com", "password1", "secret")

        asset_ids = ["first_asset", "subject_asset", "last_asset"]
        colors = [(230, 20, 20), (20, 230, 20), (20, 20, 230)]
        with commercial_main.db() as conn:
            for index, asset_id in enumerate(asset_ids):
                path = pathlib.Path(commercial_main.user_storage_path(owner["id"])) / f"{asset_id}.png"
                Image.new("RGB", (48, 48), colors[index]).save(path)
                conn.execute(
                    "INSERT INTO assets (id, user_id, name, kind, path, url, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (asset_id, owner["id"], path.name, "image", str(path), f"/api/assets/{asset_id}", index + 1),
                )

        roles = commercial_main.resolve_video_reference_image_roles(
            owner["id"],
            {
                "first_frame_asset_id": "first_asset",
                "strong_reference_asset_id": "subject_asset",
                "last_frame_asset_id": "last_asset",
            },
        )

        self.assertEqual(set(roles), {"first_frame", "reference_image", "last_frame"})
        self.assertEqual(len(set(roles.values())), 3)
        self.assertTrue(all(value.startswith("data:image/jpeg;base64,") for value in roles.values()))

    def test_video_reference_image_is_resized_and_bounded_for_inline_provider_payload(self):
        source = pathlib.Path(self.tmp.name) / "large-reference.png"
        Image.new("RGBA", (2400, 1600), (16, 160, 150, 180)).save(source)

        data_url = commercial_main.encode_video_reference_image(source)
        encoded = base64.b64decode(data_url.split(",", 1)[1])
        with Image.open(io.BytesIO(encoded)) as image:
            self.assertLessEqual(max(image.size), commercial_main.VIDEO_REFERENCE_INLINE_MAX_SIDE)
            self.assertEqual(image.mode, "RGB")
        self.assertLessEqual(len(encoded), commercial_main.VIDEO_REFERENCE_INLINE_MAX_BYTES)

    def test_video_reference_image_rejects_unsafe_source_dimensions_before_decode(self):
        cases = [
            ("too-many-pixels.png", (6001, 4000), "尺寸过大", 413),
            ("too-wide.png", (1001, 400), "宽高比", 400),
            ("too-tall.png", (400, 1001), "宽高比", 400),
        ]
        for filename, size, message, status_code in cases:
            with self.subTest(filename=filename):
                source = pathlib.Path(self.tmp.name) / filename
                Image.new("1", size, 1).save(source)
                with self.assertRaisesRegex(commercial_main.AppError, message) as context:
                    commercial_main.encode_video_reference_image(source)
                self.assertEqual(context.exception.status_code, status_code)

    def test_video_reference_image_rechecks_dimensions_after_exif_transpose(self):
        source = pathlib.Path(self.tmp.name) / "valid-reference.png"
        Image.new("RGB", (800, 600), (16, 160, 150)).save(source)
        unsafe_transposed = Image.new("1", (6001, 4000), 1)

        with patch.object(commercial_main.ImageOps, "exif_transpose", return_value=unsafe_transposed):
            with self.assertRaisesRegex(commercial_main.AppError, "尺寸过大") as context:
                commercial_main.encode_video_reference_image(source)

        self.assertEqual(context.exception.status_code, 413)

    def test_video_task_persists_explicit_reference_roles_and_legacy_ids(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("video-options@example.com", "password1", "secret")

        task = commercial_main.create_task(
            user["id"],
            "video",
            "animate",
            cost=0,
            options={
                "reference_asset_ids": ["legacy_one", "legacy_two"],
                "first_frame_asset_id": "image_one",
                "strong_reference_asset_id": "image_two",
                "last_frame_asset_id": "image_three",
                "strong_reference_alias": "@主体1",
                "reference_images": ["data:image/png;base64,must-not-be-stored"],
            },
        )

        self.assertEqual(
            task["options"]["reference_asset_ids"],
            ["image_one", "image_two", "image_three"],
        )
        self.assertEqual(task["options"]["first_frame_asset_id"], "image_one")
        self.assertEqual(task["options"]["strong_reference_asset_id"], "image_two")
        self.assertEqual(task["options"]["last_frame_asset_id"], "image_three")
        self.assertEqual(task["options"]["strong_reference_alias"], "主体")
        self.assertNotIn("reference_images", task["options"])

    def test_legacy_video_reference_ids_map_to_strong_or_last_frame(self):
        strong = commercial_main.normalize_task_options(
            "video",
            {"reference_asset_ids": ["first", "second"]},
        )
        first_last = commercial_main.normalize_task_options(
            "video",
            {"reference_asset_ids": ["first", "second"], "first_last_frame": True},
        )

        self.assertEqual(strong["first_frame_asset_id"], "first")
        self.assertEqual(strong["strong_reference_asset_id"], "second")
        self.assertEqual(strong["last_frame_asset_id"], "")
        self.assertEqual(first_last["first_frame_asset_id"], "first")
        self.assertEqual(first_last["strong_reference_asset_id"], "")
        self.assertEqual(first_last["last_frame_asset_id"], "second")

    def test_lingjing_legacy_seedance_model_uses_configured_model(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"video_url": "https://cdn.example/result.mp4"}

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, url, headers, json):
                captured.update(url=url, headers=headers, payload=json)
                return FakeResponse()

        with EnvPatch(
            VIDEO_API_KEY="fake-key",
            VIDEO_GENERATION_URL="https://video.example/v1/video/generations",
            VIDEO_MODEL="cdance2.0-0611",
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            asyncio.run(
                commercial_main.call_video(
                    "animate",
                    {"provider": "灵境API", "model": "seedance-2.0"},
                )
            )

        self.assertEqual(captured["payload"]["model"], "cdance2.0-0611")

    def test_lingjing_call_video_injects_both_reference_tokens_into_upstream_contract(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"video_url": "https://cdn.example/result.mp4"}

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, url, headers, json):
                captured.update(url=url, headers=headers, payload=json)
                return FakeResponse()

        with EnvPatch(
            VIDEO_API_KEY="fake-key",
            VIDEO_GENERATION_URL="https://video.example/v1/video/generations",
            VIDEO_MODEL="doubao-seedance-2-0-260128",
            VOLCANO_VIDEO_API_KEY=None,
            VOLCANO_VIDEO_GENERATION_URL=None,
            VOLCANO_VIDEO_MODEL=None,
            CUSTOM_VIDEO_API_KEY=None,
            CUSTOM_VIDEO_GENERATION_URL=None,
            CUSTOM_VIDEO_MODEL=None,
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            asyncio.run(
                commercial_main.call_video(
                    "人物缓慢转身",
                    {
                        "model": "doubao-seedance-2-0-260128",
                        "mode": "image_to_video",
                        "strong_reference_alias": "主体",
                    },
                    reference_images={
                        "first_frame": "data:image/png;base64,FIRST",
                        "reference_image": "data:image/png;base64,SUBJECT",
                    },
                )
            )

        self.assertIn("@图片1", captured["payload"]["prompt"])
        self.assertIn("@图片2", captured["payload"]["prompt"])
        self.assertIn("人物缓慢转身", captured["payload"]["prompt"])
        self.assertEqual(
            [item.get("role") for item in captured["payload"]["content"][1:]],
            ["reference_image", "reference_image"],
        )

    def test_non_supporting_video_provider_rejects_images_before_network_call(self):
        with EnvPatch(
            VIDEO_API_KEY=None,
            VIDEO_GENERATION_URL=None,
            VIDEO_MODEL=None,
            VOLCANO_VIDEO_API_KEY=None,
            VOLCANO_VIDEO_GENERATION_URL=None,
            VOLCANO_VIDEO_MODEL=None,
            CUSTOM_VIDEO_API_KEY="custom-key",
            CUSTOM_VIDEO_GENERATION_URL="https://custom.example/video/generations",
            CUSTOM_VIDEO_MODEL="custom-video",
        ):
            with self.assertRaisesRegex(commercial_main.AppError, "不支持图生视频") as context:
                asyncio.run(
                    commercial_main.call_video(
                        "animate",
                        {"model": "custom-video", "mode": "image_to_video"},
                        reference_images={"first_frame": "data:image/png;base64,FIRST"},
                    )
                )

        self.assertEqual(context.exception.status_code, 400)

    def test_doubao_seedance_model_exposes_real_reference_capabilities(self):
        capability = commercial_main.video_model_capability(
            {
                "provider": "灵境API",
                "model": "doubao-seedance-2-0-260128",
            }
        )

        self.assertEqual(
            capability,
            {
                "image_to_video": True,
                "strong_reference": True,
                "first_last_frame": True,
                "max_images": 2,
            },
        )

    def test_fictional_seedance_model_exposes_no_reference_capabilities(self):
        capability = commercial_main.video_model_capability(
            {
                "provider": "灵境API",
                "model": "not-a-real-seedance-model",
            }
        )

        self.assertEqual(
            capability,
            {
                "image_to_video": False,
                "strong_reference": False,
                "first_last_frame": False,
                "max_images": 0,
            },
        )

    def test_lingjing_legacy_config_falls_back_and_default_provider_uses_lingjing_contract(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"video_url": "https://cdn.example/result.mp4"}

        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, url, headers, json):
                captured.update(url=url, headers=headers, payload=json)
                return FakeResponse()

        with EnvPatch(
            VIDEO_API_KEY="fake-key",
            VIDEO_GENERATION_URL="https://video.example/v1/video/generations",
            VIDEO_MODEL="seedance-2.0",
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            asyncio.run(commercial_main.call_video("animate", {"model": "seedance-2.0"}))

        self.assertEqual(captured["payload"]["model"], "cdance2.0-0611")
        self.assertEqual(captured["payload"]["content"], [{"type": "text", "text": "animate"}])

    def test_video_submission_surfaces_upstream_error_detail(self):
        class FakeClient:
            def __init__(self, *_args, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, url, headers, json):
                return commercial_main.httpx.Response(
                    403,
                    request=commercial_main.httpx.Request("POST", url),
                    json={"detail": "无模型权限"},
                )

        with EnvPatch(
            VIDEO_API_KEY="fake-key",
            VIDEO_GENERATION_URL="https://video.example/v1/video/generations",
            VIDEO_MODEL="cdance2.0-0611",
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            with self.assertRaisesRegex(RuntimeError, "无模型权限"):
                asyncio.run(commercial_main.call_video("animate", {"provider": "灵境API"}))

    def test_guohe_deployment_llm_uses_dual_auth_and_omits_model(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "OK"}}]}

        class FakeClient:
            def __init__(self, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, _exc_type, _exc, _tb):
                return None

            async def post(self, url, headers, json):
                captured.update(url=url, headers=headers, payload=json)
                return FakeResponse()

        endpoint = (
            "https://llm.guohe-sh.com/api/openai/deployments/gpt-5.5/"
            "chat/completions?api-version=2025-04-01-preview"
        )
        with EnvPatch(
            LLM_API_KEY="secret",
            LLM_CHAT_URL=endpoint,
            LLM_MODEL="gpt-5.5",
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            result = asyncio.run(commercial_main.call_llm("只回复 OK"))

        self.assertEqual(result["text"], "OK")
        self.assertEqual(captured["url"], endpoint)
        self.assertEqual(captured["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(captured["headers"].get("api-key"), "secret")
        self.assertNotIn("model", captured["payload"])

    def test_guohe_deployment_image_uses_dual_auth(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": [{"url": "https://example.com/result.png"}]}

        class FakeClient:
            def __init__(self, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, _exc_type, _exc, _tb):
                return None

            async def post(self, url, headers, json):
                captured.update(url=url, headers=headers, payload=json)
                return FakeResponse()

        endpoint = (
            "https://llm.guohe-sh.com/api/openai/deployments/gpt-image-2/"
            "images/generations?api-version=2025-04-01-preview"
        )
        with EnvPatch(
            IMAGE_API_KEY="secret",
            IMAGE_GENERATION_URL=endpoint,
            IMAGE_MODEL="gpt-image-2",
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            asyncio.run(commercial_main.call_image("make an image"))

        self.assertEqual(captured["url"], endpoint)
        self.assertEqual(captured["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(captured["headers"].get("api-key"), "secret")
        self.assertNotIn("model", captured["payload"])

    def test_standard_openai_llm_does_not_send_api_key_header(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "OK"}}]}

        class FakeClient:
            def __init__(self, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, _exc_type, _exc, _tb):
                return None

            async def post(self, url, headers, json):
                captured.update(url=url, headers=headers, payload=json)
                return FakeResponse()

        with EnvPatch(
            LLM_API_KEY="secret",
            LLM_CHAT_URL="https://api.openai.com/v1/chat/completions",
            LLM_MODEL="gpt-4o-mini",
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            asyncio.run(commercial_main.call_llm("hello"))

        self.assertNotIn("api-key", captured["headers"])
        self.assertEqual(captured["payload"]["model"], "gpt-4o-mini")

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

    def test_selected_model_routes_without_trusting_client_provider(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": []}

        class FakeClient:
            def __init__(self, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, _exc_type, _exc, _tb):
                return None

            async def post(self, url, headers, json):
                captured.update(url=url, headers=headers, payload=json)
                return FakeResponse()

        with EnvPatch(
            IMAGE_API_KEY="default-key",
            IMAGE_GENERATION_URL="https://default.example/images",
            IMAGE_MODEL="default-image",
            OPENAI_IMAGE_API_KEY=None,
            OPENAI_IMAGE_GENERATION_URL=None,
            OPENAI_IMAGE_MODEL=None,
            CUSTOM_IMAGE_API_KEY="custom-key",
            CUSTOM_IMAGE_GENERATION_URL="https://custom.example/images",
            CUSTOM_IMAGE_MODEL="custom-image",
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            asyncio.run(
                commercial_main.call_image(
                    "make an image",
                    {"provider": "国禾API", "model": "custom-image"},
                )
            )
            self.assertEqual(captured["url"], "https://custom.example/images")
            self.assertEqual(captured["payload"]["model"], "custom-image")

            asyncio.run(commercial_main.call_image("make another image", {"model": "stale-client-image"}))

        self.assertEqual(captured["url"], "https://default.example/images")
        self.assertEqual(captured["payload"]["model"], "default-image")

    def test_video_routing_prefers_public_runtime_model_over_legacy_alias(self):
        with EnvPatch(
            VIDEO_API_KEY="lingjing-key",
            VIDEO_GENERATION_URL="https://lingjing.example/video",
            VIDEO_MODEL="seedance-2.0",
            VOLCANO_VIDEO_API_KEY="volcano-key",
            VOLCANO_VIDEO_GENERATION_URL="https://volcano.example/video",
            VOLCANO_VIDEO_MODEL="seedance-2.0",
            CUSTOM_VIDEO_API_KEY=None,
            CUSTOM_VIDEO_GENERATION_URL=None,
            CUSTOM_VIDEO_MODEL=None,
        ):
            public_seedance = commercial_main.resolve_generation_provider_config("video", "seedance-2.0")
            public_cdance = commercial_main.resolve_generation_provider_config("video", "cdance2.0-0611")

        self.assertEqual(public_seedance["provider"], "火山引擎")
        self.assertEqual(public_cdance["provider"], "灵境API")

    def test_provider_without_model_is_not_publicly_usable(self):
        with EnvPatch(
            IMAGE_API_KEY="image-key",
            IMAGE_GENERATION_URL="https://images.example/generations",
            IMAGE_MODEL=None,
            OPENAI_IMAGE_API_KEY=None,
            OPENAI_IMAGE_GENERATION_URL=None,
            OPENAI_IMAGE_MODEL=None,
            CUSTOM_IMAGE_API_KEY=None,
            CUSTOM_IMAGE_GENERATION_URL=None,
            CUSTOM_IMAGE_MODEL=None,
        ):
            capabilities = commercial_main.generation_capabilities()
            with self.assertRaisesRegex(RuntimeError, "可用的图片生成模型"):
                commercial_main.resolve_generation_provider_config("image")

        self.assertFalse(capabilities["image"]["configured"])
        self.assertEqual(capabilities["image"]["models"], [])

    def test_admin_provider_override_is_encrypted_persistent_and_used_at_runtime(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": []}

        class FakeClient:
            def __init__(self, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, _exc_type, _exc, _tb):
                return None

            async def post(self, url, headers, json):
                captured.update(url=url, headers=headers, payload=json)
                return FakeResponse()

        secret = "database-provider-secret"
        provider_name = "自定义"
        with EnvPatch(
            APP_ENV="development",
            CANVAS_PRODUCTION="0",
            SESSION_SECRET="development-session-secret",
            CONFIG_ENCRYPTION_KEY="stable-test-config-key",
            IMAGE_API_KEY=None,
            IMAGE_GENERATION_URL=None,
            IMAGE_MODEL=None,
            OPENAI_IMAGE_API_KEY=None,
            OPENAI_IMAGE_GENERATION_URL=None,
            OPENAI_IMAGE_MODEL=None,
            CUSTOM_IMAGE_API_KEY="environment-fallback-key",
            CUSTOM_IMAGE_GENERATION_URL="https://environment.example/images",
            CUSTOM_IMAGE_MODEL="environment-image",
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            before = commercial_main.resolve_provider_config("image", provider_name)
            saved = commercial_main.update_provider_config(
                "image",
                provider_name,
                commercial_main.ProviderConfigPayload(
                    api_key=secret,
                    url="https://database.example/images",
                    model="database-image",
                ),
            )
            commercial_main.init_db()
            after = commercial_main.resolve_provider_config("image", provider_name)
            asyncio.run(
                commercial_main.call_image(
                    "make an image",
                    {"provider": "国禾API", "model": "stale-client-image"},
                )
            )
            with commercial_main.db() as conn:
                raw_value = conn.execute(
                    "SELECT value_json FROM app_settings WHERE key = ?",
                    (commercial_main.provider_setting_key("image", provider_name),),
                ).fetchone()["value_json"]
            commercial_main.update_provider_config(
                "image",
                provider_name,
                commercial_main.ProviderConfigPayload(api_key="", model="database-image-v2"),
            )
            preserved_key = commercial_main.resolve_provider_config("image", provider_name)["api_key"]
            commercial_main.update_provider_config(
                "image",
                provider_name,
                commercial_main.ProviderConfigPayload(clear_api_key=True),
            )
            cleared_key = commercial_main.resolve_provider_config("image", provider_name)["api_key"]

        self.assertEqual(before["api_key"], "environment-fallback-key")
        self.assertEqual(before["source"], "env")
        self.assertNotIn(secret, raw_value)
        self.assertNotIn(secret, str(saved))
        self.assertEqual(after["api_key"], secret)
        self.assertEqual(after["url"], "https://database.example/images")
        self.assertEqual(after["model"], "database-image")
        self.assertEqual(after["models"], ["database-image"])
        self.assertEqual(after["source"], "admin")
        self.assertEqual(captured["url"], "https://database.example/images")
        self.assertEqual(captured["headers"]["Authorization"], f"Bearer {secret}")
        self.assertEqual(captured["payload"]["model"], "database-image")
        self.assertEqual(preserved_key, secret)
        self.assertEqual(cleared_key, "")

    def test_admin_provider_multi_models_route_selected_model_and_empty_list_disables(self):
        captured = {}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"data": []}

        class FakeClient:
            def __init__(self, **_kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, _exc_type, _exc, _tb):
                return None

            async def post(self, url, headers, json):
                captured.update(url=url, headers=headers, payload=json)
                return FakeResponse()

        with EnvPatch(
            APP_ENV="development",
            CANVAS_PRODUCTION="0",
            CONFIG_ENCRYPTION_KEY="stable-test-config-key",
            IMAGE_API_KEY=None,
            IMAGE_GENERATION_URL=None,
            IMAGE_MODEL=None,
            OPENAI_IMAGE_API_KEY=None,
            OPENAI_IMAGE_GENERATION_URL=None,
            OPENAI_IMAGE_MODEL=None,
            CUSTOM_IMAGE_API_KEY=None,
            CUSTOM_IMAGE_GENERATION_URL=None,
            CUSTOM_IMAGE_MODEL=None,
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            saved = commercial_main.update_provider_config(
                "image",
                "自定义",
                commercial_main.ProviderConfigPayload(
                    api_key="multi-model-secret",
                    url="https://multi.example/v1/images/generations",
                    model="image-a",
                    models=[" image-a ", "image-b", "image-a", ""],
                ),
            )
            selected = commercial_main.resolve_generation_provider_config("image", "image-b")
            capabilities = commercial_main.generation_capabilities()
            asyncio.run(commercial_main.call_image("make an image", {"model": "image-b"}))
            with commercial_main.db() as conn:
                stored = json.loads(
                    conn.execute(
                        "SELECT value_json FROM app_settings WHERE key = ?",
                        (commercial_main.provider_setting_key("image", "自定义"),),
                    ).fetchone()["value_json"]
                )
            with self.assertRaisesRegex(commercial_main.AppError, "默认模型"):
                commercial_main.update_provider_config(
                    "image",
                    "自定义",
                    commercial_main.ProviderConfigPayload(model="image-c", models=["image-a", "image-b"]),
                )
            with self.assertRaisesRegex(commercial_main.AppError, "最多保存 100"):
                commercial_main.update_provider_config(
                    "image",
                    "自定义",
                    commercial_main.ProviderConfigPayload(
                        model="image-0",
                        models=[f"image-{index}" for index in range(101)],
                    ),
                )
            disabled = commercial_main.update_provider_config(
                "image",
                "自定义",
                commercial_main.ProviderConfigPayload(model="", models=[]),
            )

        self.assertEqual(saved["model"], "image-a")
        self.assertEqual(saved["models"], ["image-a", "image-b"])
        self.assertEqual(stored["model"], "image-a")
        self.assertEqual(stored["models"], ["image-a", "image-b"])
        self.assertEqual(selected["model"], "image-b")
        self.assertEqual(capabilities["image"]["models"], ["image-a", "image-b"])
        self.assertEqual(captured["payload"]["model"], "image-b")
        self.assertEqual(disabled["models"], [])
        self.assertEqual(disabled["model"], "")
        self.assertFalse(disabled["configured"])

    def test_development_provider_encryption_can_fall_back_to_session_secret(self):
        with EnvPatch(
            APP_ENV="development",
            CANVAS_PRODUCTION="0",
            CONFIG_ENCRYPTION_KEY=None,
            SESSION_SECRET="development-session-secret",
        ):
            encrypted = commercial_main.encrypt_provider_secret("development-provider-key")
            decrypted = commercial_main.decrypt_provider_secret(encrypted)

        self.assertNotIn("development-provider-key", encrypted)
        self.assertEqual(decrypted, "development-provider-key")

    def test_provider_urls_reject_credentials_fragments_localhost_and_private_ips(self):
        unsafe_urls = [
            "ftp://api.example.test/generations",
            "https://user:password@api.example.test/generations",
            "https://api.example.test/generations#secret",
            "http://localhost:8080/generations",
            "http://localhost.:8080/generations",
            "http://127.0.0.1/generations",
            "http://10.0.0.1/generations",
            "http://192.168.1.10/generations",
            "http://169.254.169.254/latest/meta-data",
            "http://[::1]/generations",
        ]
        for url in unsafe_urls:
            with self.subTest(url=url):
                with self.assertRaises(commercial_main.AppError):
                    commercial_main.validate_provider_url(url)

        self.assertEqual(
            commercial_main.validate_provider_url("https://api.example.test/v1/generations?api-version=1"),
            "https://api.example.test/v1/generations?api-version=1",
        )
        with self.assertRaisesRegex(commercial_main.AppError, "task_id"):
            commercial_main.validate_provider_url(
                "https://video.example.test/tasks/status",
                require_task_id=True,
            )

    def test_provider_models_url_derives_standard_endpoints_and_deployment_model(self):
        self.assertEqual(
            commercial_main.provider_models_url(
                {
                    "kind": "llm",
                    "base_url": "https://api.example.test/v1",
                    "url": "https://api.example.test/v1/chat/completions",
                }
            ),
            "https://api.example.test/v1/models",
        )
        self.assertEqual(
            commercial_main.provider_models_url(
                {
                    "kind": "llm",
                    "base_url": "https://wrong.example/v1",
                    "url": "https://api.example.test/v1/chat/completions",
                }
            ),
            "https://api.example.test/v1/models",
        )
        self.assertEqual(
            commercial_main.provider_models_url(
                {
                    "kind": "image",
                    "url": "https://api.example.test/v1/images/generations?api-version=1",
                }
            ),
            "https://api.example.test/v1/models?api-version=1",
        )
        self.assertEqual(
            commercial_main.provider_deployment_model(
                {
                    "kind": "image",
                    "url": "https://api.example.test/openai/deployments/gpt-image-2/images/generations",
                }
            ),
            "gpt-image-2",
        )

    def test_provider_models_url_rejects_dns_resolving_to_private_network(self):
        private_result = [
            (commercial_main.socket.AF_INET, commercial_main.socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))
        ]
        with patch.object(commercial_main.socket, "getaddrinfo", return_value=private_result):
            with self.assertRaisesRegex(commercial_main.AppError, "内网"):
                asyncio.run(commercial_main.validate_provider_models_url("https://models.example.test/v1/models"))

    def test_provider_models_url_reports_unresolvable_hostname(self):
        with patch.object(
            commercial_main.socket,
            "getaddrinfo",
            side_effect=commercial_main.socket.gaierror(-2, "Name or service not known"),
        ):
            with self.assertRaisesRegex(
                commercial_main.AppError,
                r"服务器无法解析域名 models\.example\.test.*手动添加模型 ID",
            ):
                asyncio.run(commercial_main.validate_provider_models_url("https://models.example.test/v1/models"))

    def test_provider_models_url_reports_dns_timeout(self):
        with patch.object(commercial_main.socket, "getaddrinfo", side_effect=TimeoutError("timed out")):
            with self.assertRaisesRegex(commercial_main.AppError, "服务器解析域名 models.example.test 超时"):
                asyncio.run(commercial_main.validate_provider_models_url("https://models.example.test/v1/models"))

    def test_fetch_video_models_uses_saved_secret_and_filters_nonvideo_ids(self):
        captured = {}
        body = json.dumps(
            {
                "data": [
                    {"id": "DeepSeek-V3.2"},
                    {"id": "DeepSeek-V4-Pro"},
                    {"id": "DeepSeek-V4-Flash"},
                    {"id": "Kimi-K2.5"},
                    {"id": "glm-5.2"},
                    {"id": "Doubao-Seed-2.0-Pro"},
                    {"id": "GLM-5.0"},
                    {"id": "glm-5.1"},
                    {"id": "minimax-m3"},
                    {"id": "qwen3.5-397b-a17b"},
                    {"id": "qwen3.5-122b-a10b"},
                    {"id": "qwen3.5-35b-a3b"},
                    {"id": "cdance2.0-fast-0611"},
                    {"id": "cdance2.0-0611"},
                ]
            }
        ).encode("utf-8")

        class FakeResponse:
            status_code = 200
            headers = {"content-type": "application/json", "content-length": str(len(body))}

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def aiter_bytes(self):
                yield body

        class FakeClient:
            def __init__(self, *_args, **kwargs):
                captured["client"] = kwargs

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            def stream(self, method, url, headers):
                captured.update(method=method, url=url, headers=headers)
                return FakeResponse()

        secret = "server-side-model-secret"
        with EnvPatch(
            VIDEO_API_KEY=secret,
            VIDEO_GENERATION_URL="https://models.example.test/v1/video/generations",
            VIDEO_MODEL="cdance2.0-0611",
        ), patch.object(commercial_main, "validate_provider_models_url", return_value=None), patch.object(
            commercial_main.httpx,
            "AsyncClient",
            FakeClient,
        ):
            result = asyncio.run(commercial_main.fetch_provider_models("video", "灵境API"))

        self.assertEqual(result["models"], ["cdance2.0-fast-0611", "cdance2.0-0611"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["discovered_count"], 14)
        self.assertEqual(result["filtered_out"], 12)
        self.assertIn("已隐藏 12 个非视频模型", result["message"])
        self.assertEqual(captured["method"], "GET")
        self.assertEqual(captured["url"], "https://models.example.test/v1/models")
        self.assertEqual(captured["headers"]["Authorization"], f"Bearer {secret}")
        self.assertFalse(captured["client"]["follow_redirects"])
        self.assertFalse(captured["client"]["trust_env"])
        self.assertNotIn(secret, json.dumps(result, ensure_ascii=False))

    def test_model_discovery_prefers_metadata_and_excludes_unknown_media_models(self):
        payload = {
            "data": [
                {"id": "declared-video", "task_type": "image_to_video"},
                {"id": "declared-image", "task_type": "text_to_image"},
                {"id": "unknown-media"},
            ]
        }

        video, video_truncated, discovered, video_filtered = commercial_main.parse_provider_models(
            payload,
            kind="video",
            provider="自定义",
        )
        image, image_truncated, _, image_filtered = commercial_main.parse_provider_models(
            payload,
            kind="image",
            provider="自定义",
        )

        self.assertEqual(video, ["declared-video"])
        self.assertEqual(image, ["declared-image"])
        self.assertFalse(video_truncated)
        self.assertFalse(image_truncated)
        self.assertEqual(discovered, 3)
        self.assertEqual(video_filtered, 2)
        self.assertEqual(image_filtered, 2)

    def test_model_discovery_classifies_output_not_multimodal_input(self):
        payload = {
            "data": [
                {
                    "id": "multimodal-chat",
                    "modalities": {"input": ["text", "image", "video"], "output": ["text"]},
                },
                {
                    "id": "frame-animator",
                    "modalities": {"input": ["image"], "output": ["video"]},
                },
                {
                    "id": "vision-chat",
                    "capabilities": {"input": ["image", "video"], "output": ["text"]},
                },
            ]
        }

        video, *_ = commercial_main.parse_provider_models(payload, kind="video", provider="自定义")
        image, *_ = commercial_main.parse_provider_models(payload, kind="image", provider="自定义")
        llm, *_ = commercial_main.parse_provider_models(payload, kind="llm", provider="自定义")

        self.assertEqual(video, ["frame-animator"])
        self.assertEqual(image, [])
        self.assertEqual(llm, ["multimodal-chat", "vision-chat"])

    def test_production_refuses_to_save_provider_key_without_config_encryption_key(self):
        with EnvPatch(
            APP_ENV="production",
            CANVAS_PRODUCTION="1",
            SESSION_SECRET="s" * 48,
            CONFIG_ENCRYPTION_KEY=None,
        ):
            with self.assertRaisesRegex(commercial_main.AppError, "CONFIG_ENCRYPTION_KEY"):
                commercial_main.update_provider_config(
                    "llm",
                    "自定义",
                    commercial_main.ProviderConfigPayload(api_key="must-not-be-stored"),
                )

        with commercial_main.db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM app_settings").fetchone()[0]
        self.assertEqual(count, 0)

        with EnvPatch(
            APP_ENV="production",
            CANVAS_PRODUCTION="1",
            SESSION_SECRET="s" * 48,
            CONFIG_ENCRYPTION_KEY="too-short",
        ):
            with self.assertRaisesRegex(commercial_main.AppError, "至少 32 位"):
                commercial_main.update_provider_config(
                    "llm",
                    "自定义",
                    commercial_main.ProviderConfigPayload(api_key="must-not-be-stored"),
                )

    def test_generation_capabilities_do_not_expose_secrets(self):
        with EnvPatch(
            LLM_API_KEY=None,
            IMAGE_API_KEY="image-secret",
            IMAGE_GENERATION_URL="https://example.com/images",
            IMAGE_MODEL="image-model-a",
            OPENAI_IMAGE_API_KEY=None,
            OPENAI_IMAGE_GENERATION_URL=None,
            OPENAI_IMAGE_MODEL=None,
            CUSTOM_IMAGE_API_KEY="custom-image-secret",
            CUSTOM_IMAGE_GENERATION_URL="https://custom.example.com/images",
            CUSTOM_IMAGE_MODEL="image-model-b",
            VIDEO_API_KEY=None,
            VIDEO_GENERATION_URL=None,
        ):
            capabilities = commercial_main.generation_capabilities()

        self.assertFalse(capabilities["llm"]["configured"])
        self.assertTrue(capabilities["image"]["configured"])
        self.assertFalse(capabilities["video"]["configured"])
        self.assertEqual(capabilities["image"]["models"], ["image-model-a", "image-model-b"])
        self.assertNotIn("providers", capabilities["image"])
        self.assertNotIn("image-secret", str(capabilities))
        for provider_name in ("国禾API", "OpenAI兼容", "自定义"):
            self.assertNotIn(provider_name, str(capabilities))

    def test_async_video_submission_polls_until_media_is_available(self):
        poll_count = {"value": 0}

        class FakeResponse:
            def __init__(self, data):
                self.data = data

            def raise_for_status(self):
                return None

            def json(self):
                return self.data

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, *_args, **_kwargs):
                return FakeResponse(
                    {
                        "task_id": "video-123",
                        "status": "queued",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": "https://cdn.example/input.png"},
                            }
                        ],
                    }
                )

            async def get(self, *_args, **_kwargs):
                poll_count["value"] += 1
                if poll_count["value"] == 1:
                    return FakeResponse(
                        {
                            "id": "video-123",
                            "status": "running",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": "https://cdn.example/input.png"},
                                }
                            ],
                        }
                    )
                return FakeResponse(
                    {
                        "id": "video-123",
                        "status": "succeeded",
                        "content": {"video_url": "https://cdn.example/final.mp4"},
                    }
                )

        with EnvPatch(
            VIDEO_API_KEY="video-key",
            VIDEO_GENERATION_URL="https://video.example/tasks",
            VIDEO_MODEL="video-test-model",
            VIDEO_STATUS_URL_TEMPLATE="https://video.example/tasks/{task_id}",
            VIDEO_POLL_INTERVAL_SECONDS="0",
            VIDEO_POLL_TIMEOUT_SECONDS="5",
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            result = asyncio.run(commercial_main.call_video("prompt", {"provider": "灵境API"}, "request-1"))

        self.assertEqual(result["task_id"], "video-123")
        self.assertEqual(poll_count["value"], 2)
        self.assertEqual(result["video_url"], "https://cdn.example/final.mp4")
        self.assertEqual(result["raw"]["content"]["video_url"], "https://cdn.example/final.mp4")

    def test_async_video_failure_surfaces_nested_reason_and_task_id(self):
        class FakeResponse:
            status_code = 200

            def raise_for_status(self):
                return None

            def json(self):
                return self.data

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def post(self, *_args, **_kwargs):
                response = FakeResponse()
                response.data = {"id": "video-failed-123", "status": "queued"}
                return response

            async def get(self, *_args, **_kwargs):
                response = FakeResponse()
                response.data = {
                    "id": "video-failed-123",
                    "status": "failed",
                    "data": {"result": {"failure_reason": "reference image payload rejected"}},
                }
                return response

        with EnvPatch(
            VIDEO_API_KEY="video-key",
            VIDEO_GENERATION_URL="https://video.example/tasks",
            VIDEO_MODEL="video-test-model",
            VIDEO_STATUS_URL_TEMPLATE="https://video.example/tasks/{task_id}",
            VIDEO_POLL_INTERVAL_SECONDS="0",
            VIDEO_POLL_TIMEOUT_SECONDS="5",
        ), patch.object(commercial_main.httpx, "AsyncClient", FakeClient):
            with self.assertRaisesRegex(
                RuntimeError,
                "reference image payload rejected.*video-failed-123",
            ):
                asyncio.run(commercial_main.call_video("prompt", {"provider": "灵境API"}, "request-1"))

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
            VIDEO_MODEL="video-test-model",
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
        project = commercial_main.create_project(user["id"], "Project")
        canvas = commercial_main.create_canvas(user["id"], project["id"], "Canvas")

        task = commercial_main.create_task(
            user["id"],
            "image",
            "character sheet",
            cost=0,
            canvas_id=canvas["id"],
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

    def test_canvas_creation_revalidates_project_after_waiting_for_delete(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("canvas-create-race@example.com", "password1", "secret")
        project = commercial_main.create_project(user["id"], "Project")
        blocker = commercial_main.connect()
        blocker.execute("BEGIN IMMEDIATE")
        blocker.execute("UPDATE projects SET deleted_at = 1 WHERE id = ?", (project["id"],))
        outcome = {}
        started = threading.Event()

        def create_after_delete():
            started.set()
            try:
                outcome["canvas"] = commercial_main.create_canvas(user["id"], project["id"], "Late canvas")
            except Exception as error:
                outcome["error"] = error

        worker = threading.Thread(target=create_after_delete)
        worker.start()
        self.assertTrue(started.wait(1))
        time.sleep(0.05)
        blocker.commit()
        blocker.close()
        worker.join(2)

        self.assertFalse(worker.is_alive())
        self.assertIsInstance(outcome.get("error"), commercial_main.AppError)
        self.assertEqual(outcome["error"].status_code, 404)
        with commercial_main.db() as conn:
            count = conn.execute("SELECT COUNT(*) AS count FROM canvases WHERE project_id = ?", (project["id"],)).fetchone()["count"]
        self.assertEqual(count, 0)

    def test_canvas_creation_returns_the_inserted_row_without_a_second_lookup(self):
        with EnvPatch(INVITE_CODE="secret"):
            user = commercial_main.register_user("canvas-create-return@example.com", "password1", "secret")
        project = commercial_main.create_project(user["id"], "Project")

        with patch.object(commercial_main, "get_canvas", side_effect=AssertionError("post-commit lookup")):
            canvas = commercial_main.create_canvas(user["id"], project["id"], "Canvas")

        self.assertEqual(canvas["project_id"], project["id"])
        self.assertEqual(canvas["name"], "Canvas")
        self.assertEqual(canvas["revision"], 1)
        self.assertEqual(canvas["state"]["nodes"], [])

    def test_task_creation_revalidates_canvas_before_charging_after_delete(self):
        with EnvPatch(INVITE_CODE="secret", DEFAULT_CREDITS="10"):
            user = commercial_main.register_user("task-create-race@example.com", "password1", "secret")
        project = commercial_main.create_project(user["id"], "Project")
        canvas = commercial_main.create_canvas(user["id"], project["id"], "Canvas")
        blocker = commercial_main.connect()
        blocker.execute("BEGIN IMMEDIATE")
        blocker.execute("DELETE FROM canvases WHERE id = ?", (canvas["id"],))
        outcome = {}
        started = threading.Event()

        def create_after_delete():
            started.set()
            try:
                outcome["task"] = commercial_main.create_task(
                    user["id"], "image", "Late task", cost=3, canvas_id=canvas["id"], node_id="node_1"
                )
            except Exception as error:
                outcome["error"] = error

        worker = threading.Thread(target=create_after_delete)
        worker.start()
        self.assertTrue(started.wait(1))
        time.sleep(0.05)
        blocker.commit()
        blocker.close()
        worker.join(2)

        self.assertFalse(worker.is_alive())
        self.assertIsInstance(outcome.get("error"), commercial_main.AppError)
        self.assertEqual(outcome["error"].status_code, 404)
        self.assertEqual(commercial_main.credit_balance(user["id"]), 10)

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
        project = commercial_main.create_project(user["id"], "Project")
        canvas = commercial_main.create_canvas(user["id"], project["id"], "Canvas")

        task = commercial_main.create_task(
            user["id"],
            "image",
            "prompt",
            cost=0,
            canvas_id=canvas["id"],
            node_id="node_1",
        )
        loaded = commercial_main.get_task(user["id"], task["id"])

        self.assertEqual(loaded["canvas_id"], canvas["id"])
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
        project = commercial_main.create_project(user["id"], "Project")
        canvas = commercial_main.create_canvas(user["id"], project["id"], "Canvas")

        task = commercial_main.create_task(
            user["id"],
            "image",
            "prompt",
            cost=0,
            canvas_id=canvas["id"],
            node_id="node_1",
        )
        commercial_main.complete_task(task["id"], {"items": [{"url": "https://example.com/result.png"}]})

        assets = commercial_main.list_assets(user["id"])

        self.assertEqual(assets[0]["url"], "https://example.com/result.png")
        self.assertEqual(assets[0]["source"], "task")
        self.assertEqual(assets[0]["task_id"], task["id"])
        self.assertEqual(assets[0]["canvas_id"], canvas["id"])
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
