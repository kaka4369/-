from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CanvasViewportUiTests(unittest.TestCase):
    def test_canvas_exposes_minimap_and_zoom_controls(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="minimap"', html)
        self.assertIn('id="minimapViewport"', html)
        self.assertIn('id="zoomOutBtn"', html)
        self.assertIn('id="zoomResetBtn"', html)
        self.assertIn('id="zoomInBtn"', html)

        self.assertIn(".canvas-minimap", css)
        self.assertIn(".minimap-viewport", css)

        self.assertIn("function renderMinimap", js)
        self.assertIn("function zoomAtCanvasPoint", js)
        self.assertIn("bindMinimapEvents", js)
        self.assertIn("const MIN_ZOOM = 0.02", js)
        self.assertIn("const MAX_ZOOM = 8", js)

    def test_regular_nodes_expose_resize_handle(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('class="node-resize"', js)
        self.assertIn("function startNodeResize", js)
        self.assertIn("startNodeResize(event, node)", js)
        self.assertIn("activeDrag.kind === 'resize-node'", js)
        self.assertIn(".node-resize", css)

    def test_canvas_double_click_opens_add_menu(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="addMenu"', html)
        self.assertIn('data-add-menu="prompt"', html)
        self.assertIn('data-add-menu="image"', html)
        self.assertIn(".add-menu", css)
        self.assertIn("function showAddMenu", js)
        self.assertIn("function hideAddMenu", js)
        self.assertIn("addNode(type, { x:", js)
        self.assertIn("els.canvasArea.addEventListener('dblclick'", js)

    def test_connection_drag_to_empty_canvas_opens_add_menu_and_auto_links(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("let pendingEdgeConnection = null", js)
        self.assertIn("function showConnectionAddMenu", js)
        self.assertIn("pendingEdgeConnection = { source: source.id }", js)
        self.assertIn("showConnectionAddMenu(upEvent.clientX, upEvent.clientY)", js)
        self.assertIn("const pendingConnection = pendingEdgeConnection", js)
        self.assertIn("addEdge(pendingConnection.source, node.id)", js)
        self.assertIn(".add-menu.connection-menu", css)

    def test_text_image_video_nodes_use_console_layout(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function nodeStageHtml", js)
        self.assertIn("function consoleRunButtonHtml", js)
        self.assertIn("node-console", js)
        self.assertIn("node-toolbar-row", js)
        self.assertIn("node-bottom-bar", js)
        self.assertIn("console-run-button", js)
        self.assertIn("data-tool-action", js)

        self.assertIn(".node-stage", css)
        self.assertIn(".node-console", css)
        self.assertIn(".node-toolbar-row", css)
        self.assertIn(".node-bottom-bar", css)
        self.assertIn(".console-run-button", css)

    def test_generation_progress_and_responsive_node_body(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function generationProgress", js)
        self.assertIn("function stageProgressHtml", js)
        self.assertIn("function renderProgressIndicators", js)
        self.assertIn("data-progress-node", js)
        self.assertIn("progressStartedAt", js)

        self.assertIn(".stage-progress", css)
        self.assertIn(".stage-progress-fill", css)
        self.assertIn(".stage-progress-label", css)
        self.assertRegex(css, r"\.node-body\s*\{[^}]*display:\s*flex")
        self.assertIn("flex-direction: column", css)
        self.assertIn("flex: 1 1", css)

    def test_asset_button_toggles_back_to_canvas(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function toggleAssetPage", js)
        self.assertIn("if (currentView === 'assets')", js)
        self.assertIn("showCanvasPage();", js)
        self.assertIn("els.assetBtn.addEventListener('click', toggleAssetPage)", js)

    def test_image_result_preview_is_visually_balanced(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertIn(".node-image .node-stage-image", css)
        self.assertIn("flex: 0 0 min(42%, 320px)", css)
        self.assertIn("max-height: 320px", css)
        self.assertIn(".node-image .node-console", css)
        self.assertIn("max-height: none", css)

    def test_generated_images_are_contained_and_click_to_preview(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="mediaPreviewModal"', html)
        self.assertIn('id="mediaPreviewImage"', html)
        self.assertIn("mediaPreviewModal: document.getElementById('mediaPreviewModal')", js)
        self.assertIn("data-preview-media", js)
        self.assertIn("function openMediaPreview", js)
        self.assertIn("function closeMediaPreview", js)
        self.assertIn("data-preview-close", js)

        self.assertIn(".node-media-preview", css)
        self.assertIn("cursor: zoom-in", css)
        self.assertIn(".node-stage .node-media-preview .node-media", css)
        self.assertIn("width: auto", css)
        self.assertIn("height: auto", css)
        self.assertIn(".media-preview-modal", css)

    def test_image_nodes_expose_ratio_size_and_scale_controls_without_quality(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        for ratio in ["2:3", "3:2", "4:5", "5:4", "9:16", "16:9"]:
            self.assertIn(f"'{ratio}'", js)
        for image_size in ["自适应", "1K", "2K", "4K"]:
            self.assertIn(f"'{image_size}'", js)

        self.assertIn("imageSize", js)
        self.assertIn("imageScale", js)
        self.assertIn("data-field=\"imageSize\"", js)
        self.assertIn("data-chip-field=\"${escapeHtml(field)}\"", js)
        self.assertIn("'imageScale'", js)
        self.assertIn("image_size=${node.imageSize}", js)
        self.assertIn("image_scale=${node.imageScale", js)
        self.assertNotIn("imageQuality", js)
        self.assertNotIn("image_quality", js)
        self.assertNotIn("data-field=\"imageQuality\"", js)
        self.assertNotIn("画质", js)
        self.assertIn(".image-option-grid", css)
        self.assertIn(".image-scale-group", css)

    def test_canvas_switch_autosaves_and_tasks_can_focus_nodes(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertIn("let dirty = false", js)
        self.assertIn("async function saveCurrentCanvasIfDirty", js)
        self.assertIn("await saveCurrentCanvasIfDirty()", js)
        self.assertIn("addEventListener('beforeunload'", js)

        self.assertIn("function taskTargetFor", js)
        self.assertIn("function focusTask", js)
        self.assertIn("data-task-id", js)
        self.assertIn("button.addEventListener('click', () => focusTask(task)", js)
        self.assertIn(".task-item.is-clickable", css)

    def test_sidebar_minimap_and_assets_are_canvas_friendly(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertIn(".sidebar::after", css)
        self.assertIn(".sidebar:hover", css)
        self.assertIn("transform: translateX(calc(-100% + 18px))", css)

        self.assertIn("function revealMinimap", js)
        self.assertIn("minimap-active", js)
        self.assertIn(".canvas-area.minimap-active .canvas-minimap", css)
        self.assertIn("pointer-events: none", css)

        self.assertIn("async function loadAssets", js)
        self.assertIn("asset.task_id", js)
        self.assertIn("/api/assets", js)
        self.assertIn("function inspectTask", js)
        self.assertIn("/target", js)

        self.assertIn('id="assetPage"', html)
        self.assertIn('id="assetGrid"', html)
        self.assertIn('id="assetPreview"', html)
        self.assertIn('data-asset-tab="image"', html)
        self.assertIn("function showAssetPage", js)
        self.assertIn("function showCanvasPage", js)
        self.assertIn("function renderAssetPage", js)
        self.assertIn("function renderAssetSidebarSummary", js)
        self.assertIn(".asset-page", css)
        self.assertIn(".asset-grid", css)
        self.assertIn(".asset-preview", css)

if __name__ == "__main__":
    unittest.main()
