import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EcommerceStudioUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        cls.js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

    def test_ecommerce_is_a_sidebar_workflow_and_dock_keeps_five_creation_tools(self):
        dock = self.html[
            self.html.index('class="canvas-create-dock"') : self.html.index('id="addMenu"')
        ]
        self.assertEqual(len(re.findall(r'data-dock-(?:add|action)=', dock)), 5)
        self.assertNotIn('data-dock-action="ecommerce"', dock)
        self.assertNotIn('data-dock-action="assets"', dock)
        sidebar = self.html[self.html.index('class="sidebar-actions"') : self.html.index('</nav>')]
        self.assertIn('id="ecommerceBtn"', sidebar)
        self.assertIn('data-dock-action="ecommerce"', sidebar)
        self.assertLess(sidebar.index('id="ecommerceBtn"'), sidebar.index('id="assetBtn"'))
        self.assertIn('aria-expanded="false"', sidebar)
        self.assertIn("openEcommerceStudio().catch(showError)", self.js)

    def test_workbench_exposes_button_first_model_environment_and_tuning_controls(self):
        for value in ("domestic", "international", "custom"):
            self.assertIn(f'data-ecommerce-model-group="{value}"', self.html)
        for value in ("white", "outdoor"):
            self.assertIn(f'data-ecommerce-environment="{value}"', self.html)
        for value in ("3:4", "4:5", "2:3", "9:16", "1:1", "4:3", "3:2", "16:9"):
            self.assertIn(f'data-ecommerce-ratio="{value}"', self.html)
        for value in ("full", "half", "detail", "back"):
            self.assertIn(f'data-ecommerce-shot="{value}"', self.html)
        for value in (
            "auto",
            "front",
            "three-quarter",
            "side",
            "back",
            "weight-shift",
            "walking",
            "arms-open",
            "turn-look",
        ):
            self.assertIn(f'data-ecommerce-pose="{value}"', self.html)
        self.assertIn('role="radiogroup"', self.html)
        self.assertIn('aria-pressed="true"', self.html)

    def test_common_ratios_and_pose_cards_are_compact_visual_and_accessible(self):
        tune = self.html[
            self.html.index('class="ecommerce-tune-grid"') : self.html.index('id="ecommerceTuneSummary"')
        ]
        self.assertEqual(tune.count('data-ecommerce-ratio='), 8)
        self.assertEqual(tune.count('data-ecommerce-pose='), 9)
        self.assertEqual(tune.count('class="ecommerce-ratio-mark'), 8)
        self.assertEqual(tune.count('<svg viewBox="0 0 44 56" aria-hidden="true">'), 9)
        self.assertIn('role="group" aria-label="画面比例，选择一个常用构图比例"', tune)
        self.assertIn('role="group" aria-label="模特动作姿势，选择一个动作"', tune)
        self.assertIn('aria-label="四分之三侧转姿势"', tune)
        self.assertIn('aria-label="转身回望姿势"', tune)
        self.assertIn('.ecommerce-ratio-grid', self.css)
        self.assertIn('.ecommerce-pose-grid', self.css)
        self.assertIn('[data-theme="dark"] .ecommerce-ratio-grid button', self.css)
        self.assertIn('[data-theme="dark"] .ecommerce-pose-grid button', self.css)
        self.assertIn('@media (max-width: 620px)', self.css)

    def test_each_model_group_exposes_five_women_and_five_men(self):
        self.assertEqual(self.html.count('5 女 · 5 男'), 2)
        self.assertIn('data-ecommerce-model-gender="${gender}"', self.js)
        self.assertIn("const gender = model.gender === 'male' ? 'male' : 'female'", self.js)
        self.assertIn('class="ecommerce-model-gender"', self.js)

    def test_workbench_uses_catalog_and_batch_contract(self):
        self.assertIn("api('/api/ecommerce/catalog')", self.js)
        self.assertIn("api('/api/ecommerce/batches'", self.js)
        self.assertIn("api(`/api/ecommerce/batches/${encodeURIComponent(batchId)}`)", self.js)
        for key in (
            "client_request_id",
            "product_asset_id",
            "model_preset_id",
            "custom_model_prompt",
            "environment",
            "scene_preset_id",
            "custom_scene_prompt",
            "shot",
            "pose",
            "ratio",
            "image_size",
        ):
            self.assertIn(key, self.js)

    def test_model_images_open_a_dedicated_large_preview_without_selecting(self):
        self.assertIn('id="ecommerceImagePreviewModal"', self.html)
        self.assertIn('data-ecommerce-model-preview=', self.js)
        self.assertIn('data-ecommerce-model-id=', self.js)
        self.assertIn('function openEcommerceImagePreview(model, trigger = null, options = {})', self.js)
        self.assertIn('function closeEcommerceImagePreview()', self.js)
        self.assertIn("ecommercePreviewReturnFocus", self.js)
        self.assertIn("event.key === 'Escape' && !event.isComposing", self.js)
        preview_open = self.js[self.js.index("function openEcommerceImagePreview"):self.js.index("function closeEcommerceImagePreview")]
        self.assertNotIn("modelPresetId =", preview_open)

    def test_white_studio_shows_a_real_clickable_example_without_changing_model(self):
        self.assertIn('id="ecommerceWhitePanel"', self.html)
        self.assertIn('id="ecommerceWhiteExampleBtn"', self.html)
        self.assertIn('/static/ecommerce/scenes/white-studio-example.png', self.html)
        self.assertIn('id="ecommerceImagePreviewKicker"', self.html)
        self.assertIn("els.ecommerceWhiteExampleBtn?.addEventListener('click'", self.js)
        self.assertIn("selectable: false", self.js)
        self.assertIn("kicker: '白底案例'", self.js)
        self.assertIn("els.ecommerceWhitePanel?.classList.toggle('hidden', outdoor)", self.js)
        self.assertIn('.ecommerce-white-example-card', self.css)

    def test_outdoor_scenes_render_real_image_previews(self):
        self.assertIn("outdoor-scenes-contact-sheet.png", self.css)
        for index in range(6):
            self.assertIn(f"ecommerce-scene-preview-{index}", self.css)
        self.assertIn("scene.preview_index", self.js)
        self.assertIn("ecommerce-scene-thumb", self.js)

    def test_upload_uses_a_native_file_control_and_visible_busy_state(self):
        upload_markup = self.html[
            self.html.index('id="ecommerceUploadBtn"'):self.html.index('id="ecommerceStyleGrid"')
        ]
        self.assertIn('id="ecommerceFileInput"', upload_markup)
        self.assertIn('id="ecommerceUploadLabel"', upload_markup)
        self.assertIn("uploadEcommerceStyles(files).catch(showError)", self.js)
        self.assertIn("els.ecommerceFileInput.disabled = uploadDisabled", self.js)
        self.assertIn("setAttribute('aria-busy'", self.js)
        self.assertNotIn("ecommerceFileInput.click()", self.js)

    def test_workbench_is_full_screen_and_only_reads_this_shooting_session(self):
        self.assertIn('独立工作区 · AI 电商拍摄', self.html)
        self.assertIn('不读取画布或素材库历史内容', self.html)
        self.assertIn('aria-label="本次上传款式多选"', self.html)
        self.assertIn('sessionStyleIds: new Set()', self.js)
        self.assertIn('sessionAssets: new Map()', self.js)
        self.assertIn('function ecommerceSessionImageAssets()', self.js)
        styles_render = self.js[
            self.js.index('function renderEcommerceStyles()'):self.js.index('function renderEcommerceModels()')
        ]
        self.assertIn('const assets = ecommerceSessionImageAssets()', styles_render)
        self.assertNotIn('ecommerceImageAssets()', styles_render)
        open_studio = self.js[
            self.js.index('async function openEcommerceStudio()'):self.js.index('function closeEcommerceStudio()')
        ]
        self.assertNotIn('primeEcommerceStylesFromCanvas', open_studio)
        self.assertNotIn('loadAssets()', open_studio)
        self.assertNotIn('function primeEcommerceStylesFromCanvas()', self.js)
        self.assertIn('width: 100vw;', self.css)
        self.assertIn('height: 100dvh;', self.css)
        self.assertIn('.ecommerce-session-badge', self.css)

    def test_session_reset_is_frontend_only_and_preserves_catalog_cache(self):
        reset = self.js[
            self.js.index('function resetEcommerceStudioSession'):self.js.index('function ensureEcommerceDefaults')
        ]
        self.assertIn('const catalog = ecommerceStudio.catalog', reset)
        self.assertIn('ecommerceStudio = createEcommerceStudioState()', reset)
        self.assertIn('ecommerceStudio.catalog = catalog', reset)
        self.assertNotIn('api(', reset)
        self.assertNotIn('saveCanvas', reset)
        self.assertNotIn('delete', reset.lower())
        self.assertIn('ecommerceStudio.sessionAssets.set(assetId, data.asset)', self.js)
        self.assertIn('ecommerceStudio.sessionStyleIds.add(assetId)', self.js)

    def test_tuning_controls_update_state_feedback_and_request_payload(self):
        for field, dataset in (("ratio", "ecommerceRatio"), ("shot", "ecommerceShot"), ("pose", "ecommercePose")):
            self.assertIn(f"ecommerceStudio.{field} = button.dataset.{dataset}", self.js)
            self.assertIn(f"setPressedGroup('[data-ecommerce-{field}]'", self.js)
        self.assertIn("renderEcommerceTuneSummary()", self.js)
        self.assertIn('id="ecommerceTuneSummary"', self.html)
        request_body = self.js[self.js.index("function ecommerceBatchRequest"):self.js.index("async function insertEcommerceResults")]
        for field in ("shot", "pose", "ratio"):
            self.assertIn(field, request_body)
        for value in ("three-quarter", "weight-shift", "arms-open", "turn-look"):
            self.assertIn(f"{value}:" if "-" not in value else f"'{value}':", self.js)

    def test_batch_is_capped_costed_and_protected_from_duplicate_submit(self):
        self.assertIn("selectedStyleIds.size >= 20", self.js)
        self.assertIn("slice(0, available)", self.js)
        self.assertIn("ecommerceStudio.submitting", self.js)
        self.assertIn("count * ecommerceImageCost()", self.js)
        self.assertIn("Number(me?.credits || 0) < cost", self.js)
        self.assertIn("先试拍 1 款", self.html)

    def test_results_keep_polling_and_support_canvas_edit_and_download(self):
        self.assertIn("scheduleEcommercePoll", self.js)
        self.assertIn("insertEcommerceResults", self.js)
        self.assertIn("openMediaPreview(button.dataset.ecommerceEdit", self.js)
        self.assertIn("downloadMedia(button.dataset.ecommerceDownload", self.js)
        self.assertIn('data-ecommerce-result-preview=', self.js)
        self.assertIn("kicker: '拍摄结果'", self.js)
        self.assertIn('returnTaskId: taskId', self.js)
        result_preview = self.js[
            self.js.index("querySelectorAll('[data-ecommerce-result-preview]')"):self.js.index("querySelectorAll('[data-ecommerce-edit]')")
        ]
        self.assertIn('openEcommerceImagePreview', result_preview)
        self.assertIn('selectable: false', result_preview)
        self.assertIn("ecommerceStudio.insertedTaskIds.has(taskId)", self.js)
        self.assertIn("await saveCanvas({ silent: true })", self.js)

    def test_submit_returns_to_canvas_and_background_status_is_recoverable(self):
        submit = self.js[
            self.js.index('async function submitEcommerceBatch'):self.js.index('function resetEcommerceBatch')
        ]
        self.assertIn('closeEcommerceStudio();', submit)
        self.assertIn('已转入后台拍摄', submit)
        self.assertLess(submit.index('closeEcommerceStudio();'), submit.index('scheduleEcommercePoll(700)'))
        self.assertIn('id="ecommerceTaskBadge"', self.html)
        self.assertIn('const ecommerceBackgroundBatches = new Map()', self.js)
        self.assertIn("api('/api/ecommerce/batches?active_only=true&limit=20')", self.js)
        self.assertIn('recoverEcommerceBackgroundBatches(currentCanvas.id)', self.js)
        self.assertIn("document.addEventListener('visibilitychange'", self.js)

    def test_background_results_are_scoped_and_persistently_deduplicated(self):
        insert = self.js[
            self.js.index('async function insertEcommerceResults'):self.js.index('async function applyEcommerceBatchPayload')
        ]
        self.assertIn("String(currentCanvas?.id || '') !== targetCanvasId", insert)
        self.assertIn("state.nodes.find((node) => String(node.taskId || '') === taskId)", insert)
        self.assertIn('ecommerceStudio.insertedTaskIds.add(taskId)', insert)
        self.assertIn('await saveCanvas({ silent: true })', insert)

    def test_multiple_upload_accessibility_dark_theme_and_reduced_motion(self):
        self.assertIn('id="ecommerceFileInput" type="file" accept="image/*" multiple', self.html)
        self.assertIn('aria-modal="true"', self.html)
        self.assertIn("ecommerceStudioModal.querySelectorAll('button:not(:disabled)", self.js)
        self.assertIn('[data-theme="dark"] .ecommerce-studio-card', self.css)
        self.assertIn('@media (prefers-reduced-motion: reduce)', self.css)
        self.assertIn('.ecommerce-studio-card { animation: none; }', self.css)


if __name__ == "__main__":
    unittest.main()
