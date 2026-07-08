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

    def test_edges_expose_visible_delete_action(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("let selectedEdgeId", js)
        self.assertIn("function selectEdge", js)
        self.assertIn("function deleteEdge", js)
        self.assertIn("edge-delete-button", js)
        self.assertIn("deleteEdge(selectedEdgeId)", js)
        self.assertIn("event.key === 'Delete' || event.key === 'Backspace'", js)
        self.assertIn(".edge-path.selected", css)
        self.assertIn(".edge-delete-button", css)
        self.assertIn("pointer-events: stroke", css)
        self.assertIn("color: var(--danger)", css)
        self.assertNotIn("node-tool-delete", js)

    def test_rendering_does_not_autoshrink_node_height(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function minSize", js)
        self.assertIn("if (type === 'image') return { w: 380, h: 560 }", js)
        self.assertIn("h: clamp(safeNumber(source.h, size.h), minimum.h, 1400)", js)
        self.assertIn("const min = minSize(node.type)", js)
        self.assertNotIn("node.h = Math.max(180, element.offsetHeight)", js)

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

    def test_llm_node_hides_system_prompt_editor(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("if (type === 'llm') return { w: 390, h: 340 }", js)
        self.assertIn("function llmNodeHtml", js)
        self.assertIn("systemPrompt: '你是可靠的 AI 创作助手", js)
        self.assertNotIn("system-text", js)
        self.assertNotIn('data-field="systemPrompt"', js)
        self.assertNotIn("<span>System</span>", js)

    def test_generation_progress_and_responsive_node_body(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function generationProgress", js)
        self.assertIn("function stageProgressHtml", js)
        self.assertIn("function renderProgressIndicators", js)
        self.assertIn("data-progress-node", js)
        self.assertIn("progressStartedAt", js)
        self.assertIn("if (node.status === 'succeeded') return ''", js)

        self.assertIn(".stage-progress", css)
        self.assertIn(".stage-progress-fill", css)
        self.assertIn(".stage-progress-label", css)
        self.assertRegex(css, r"\.node-body\s*\{[^}]*display:\s*flex")
        self.assertIn("flex-direction: column", css)
        self.assertIn("flex: 1 1", css)

    def test_asset_button_opens_left_asset_drawer(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="railAssetBtn"', html)
        self.assertIn('id="assetDrawer"', html)
        self.assertIn('id="assetDrawerGrid"', html)
        self.assertIn(".quick-rail", css)
        self.assertIn(".asset-drawer", css)
        self.assertIn("#assetPanel", css)
        self.assertIn("display: none", css)
        self.assertIn("function toggleAssetPage", js)
        self.assertIn("function showAssetDrawer", js)
        self.assertIn("function renderAssetDrawer", js)
        self.assertIn("hideAssetDrawer", js)
        self.assertIn("els.railAssetBtn?.addEventListener('click', toggleAssetPage)", js)
        self.assertIn("els.assetBtn.addEventListener('click', toggleAssetPage)", js)
        self.assertNotIn('id="workflowBtn"', html)
        self.assertNotIn("workflowBtn", js)

    def test_new_canvas_uses_in_page_modal_not_left_rail_prompt(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn('id="leftNewCanvasBtn"', html)
        self.assertIn('id="canvasCreateModal"', html)
        self.assertIn('id="canvasCreateForm"', html)
        self.assertIn('id="canvasNameInput"', html)
        self.assertIn(".canvas-create-card", css)
        self.assertIn(".modal-field", css)
        self.assertIn("function showCreateCanvasModal", js)
        self.assertIn("async function createCanvasWithName", js)
        self.assertIn("els.newCanvasBtn.addEventListener('click'", js)
        self.assertIn("showCreateCanvasModal()", js)
        self.assertIn("createCanvasWithName(els.canvasNameInput.value)", js)
        self.assertNotIn("window.prompt('新画布名称'", js)
        self.assertNotIn("leftNewCanvasBtn", js)

    def test_image_result_preview_is_visually_balanced(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertIn(".node-image .node-stage-image", css)
        self.assertIn("aspect-ratio: 4 / 3", css)
        self.assertIn("flex: 0 0 auto", css)
        self.assertIn("width: min(100%, 560px)", css)
        self.assertIn("max-height: none", css)
        self.assertIn("align-self: center", css)
        self.assertIn("border: 0", css)
        self.assertIn("background: transparent", css)
        self.assertIn("box-shadow: none", css)
        self.assertIn(".node-image .node-console", css)
        self.assertIn("max-height: none", css)

    def test_image_node_uses_separate_preview_and_control_panels(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertIn(".node-image {", css)
        self.assertIn("background: transparent", css)
        self.assertIn(".node-image .node-head", css)
        self.assertIn("width: max-content", css)
        self.assertIn(".node-image .node-body", css)
        self.assertIn("overflow: visible", css)
        self.assertIn(".node-image.selected .node-stage-image", css)
        self.assertIn(".node-image.selected .node-console", css)

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
        self.assertIn(".node-image .node-media-preview", css)
        self.assertIn("background: #edf2f8", css)
        self.assertIn("width: auto", css)
        self.assertIn("height: auto", css)
        self.assertIn(".media-preview-modal", css)

    def test_image_preview_drags_node_instead_of_native_image(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('draggable="false"', js)
        self.assertIn("allowInteractive: true", js)
        self.assertIn("previewUrl: event.currentTarget.dataset.previewMedia || ''", js)
        self.assertIn("suppressNextMediaPreviewClick", js)
        self.assertIn("if (!finished.moved) openMediaPreview(finished.previewUrl)", js)
        self.assertIn("-webkit-user-drag: none", css)
        self.assertIn("cursor: grab", css)
        self.assertIn("cursor: grabbing", css)

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
        self.assertIn("function renderAssetDrawer", js)
        self.assertIn("function renderAssetSidebarSummary", js)
        self.assertIn('id="assetDrawer"', html)
        self.assertIn('id="assetDrawerGrid"', html)
        self.assertNotIn('id="leftNewCanvasBtn"', html)
        self.assertIn(".asset-page", css)
        self.assertIn(".asset-drawer-grid", css)
        self.assertIn(".asset-grid", css)
        self.assertIn(".asset-preview", css)

if __name__ == "__main__":
    unittest.main()
