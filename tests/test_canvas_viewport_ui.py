from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CanvasViewportUiTests(unittest.TestCase):
    def test_spatial_workbench_shell_matches_reference(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        phosphor_css_path = ROOT / "static" / "vendor" / "phosphor" / "phosphor.css"
        phosphor_font_path = ROOT / "static" / "vendor" / "phosphor" / "Phosphor.woff2"

        self.assertRegex(html, r'<aside class="[^"]*\bapp-sidebar\b')
        self.assertRegex(html, r'<main class="[^"]*\bapp-main\b')
        self.assertIn('class="sidebar-nav"', html)
        self.assertIn('class="topbar-context"', html)
        self.assertIn('class="topbar compact-topbar"', html)
        self.assertIn('class="canvas-create-dock"', html)

        sidebar_start = html.index('class="app-sidebar')
        sidebar_end = html.index('class="app-main')
        sidebar_html = html[sidebar_start:sidebar_end]
        for element_id in [
            "backToOriginBtn",
            "projectCurrentName",
            "newProjectBtn",
            "projectList",
            "canvasCurrentName",
            "newCanvasBtn",
            "canvasList",
            "assetBtn",
            "logBtn",
            "themeToggleBtn",
            "accountBtn",
        ]:
            self.assertIn(f'id="{element_id}"', sidebar_html)

        topbar_start = html.index('class="topbar compact-topbar"')
        topbar_end = html.index("</header>", topbar_start)
        topbar_html = html[topbar_start:topbar_end]
        for element_id in ["canvasTitle", "saveState", "creditText", "runBtn", "saveBtn"]:
            self.assertIn(f'id="{element_id}"', topbar_html)

        self.assertIn('/static/vendor/phosphor/phosphor.css', html)
        self.assertRegex(html, r'<i class="ph ph-[^"]+"')
        self.assertTrue(phosphor_css_path.is_file())
        self.assertTrue(phosphor_font_path.is_file())
        phosphor_css = phosphor_css_path.read_text(encoding="utf-8")
        self.assertIn("@font-face", phosphor_css)
        self.assertIn("Phosphor.woff2", phosphor_css)
        self.assertIn(".ph", phosphor_css)

    def test_saved_theme_bootstraps_before_css_on_every_html_page(self):
        for page in ["index.html", "auth.html", "admin.html"]:
            with self.subTest(page=page):
                html = (ROOT / "static" / page).read_text(encoding="utf-8")
                theme_storage_read = "localStorage.getItem('canvas-saas-theme')"
                self.assertIn(theme_storage_read, html)
                theme_bootstrap = html.index(theme_storage_read)
                first_stylesheet = html.index('rel="stylesheet"')
                self.assertLess(theme_bootstrap, first_stylesheet)
                self.assertIn("document.documentElement.dataset.theme", html[:first_stylesheet])

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

    def test_canvas_background_is_hover_lit_and_zoom_clamped(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("--spotlight-x", css)
        self.assertIn(".canvas-area.pointer-lit::before", css)
        self.assertIn("function updateCanvasSpotlight", js)
        self.assertIn("function clearCanvasSpotlight", js)
        self.assertIn("pointer-lit", js)
        self.assertIn("function canvasGridSize", js)
        self.assertIn("let size = 28 * Math.max(scale, MIN_ZOOM)", js)
        self.assertIn("while (size > 84) size /= 2", js)
        self.assertIn("return clamp(size, 10, 84)", js)
        self.assertIn("setProperty('--grid-size'", js)
        self.assertIn("var(--grid-size", css)
        self.assertIn("var(--grid-x", css)
        self.assertNotIn("setProperty('--major-grid-size'", js)
        self.assertNotIn("setProperty('--major-grid-x'", js)
        self.assertNotIn("28 * scale", js)
        self.assertNotIn("style.backgroundSize", js)

    def test_canvas_has_polished_visual_layer(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertIn("Canvas polish layer", css)
        self.assertIn(".canvas-area", css)
        self.assertIn(".node.selected", css)
        self.assertIn(".node-port.hot", css)
        self.assertIn(".edge-group:hover .edge-path", css)
        self.assertIn(".canvas-minimap", css)
        self.assertIn(".add-menu", css)

    def test_secondary_pages_keep_shared_sidebar_and_hide_canvas_only_tools(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]

        self.assertIn('class="app-sidebar"', html)
        self.assertIn(".app-shell.subpage-open .app-sidebar", final_css)
        self.assertIn(".app-shell.subpage-open .toolbar", final_css)
        self.assertIn(".app-shell.subpage-open .canvas-area", final_css)
        self.assertRegex(
            final_css,
            r"\.app-shell\s*\{[^}]*grid-template-columns:\s*var\(--sidebar-width\)\s+minmax\(0,\s*1fr\)",
        )
        self.assertRegex(final_css, r"\.inspector\s*\{[^}]*display:\s*none")

    def test_night_mode_setting_is_available_and_persisted(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        css_version = re.search(r'app\.css\?v=([^"\']+)', html)
        js_version = re.search(r'app\.js\?v=([^"\']+)', html)
        self.assertIsNotNone(css_version)
        self.assertIsNotNone(js_version)
        self.assertEqual(css_version.group(1), js_version.group(1))
        self.assertIn("canvas-saas-theme", html)
        self.assertIn('id="themeToggleBtn"', html)
        self.assertIn("黑夜", html)
        self.assertIn("THEME_STORAGE_KEY", js)
        self.assertIn("function applyTheme", js)
        self.assertIn("function toggleTheme", js)
        self.assertIn("els.themeToggleBtn?.addEventListener('click', toggleTheme)", js)
        self.assertIn('[data-theme="dark"]', css)
        self.assertIn("Dark theme", css)

    def test_canvas_exposes_visual_creation_dock_and_node_icons(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertIn("canvas-create-dock", html)
        self.assertIn('data-dock-add="prompt"', html)
        self.assertIn('data-dock-add="image"', html)
        self.assertIn('data-dock-action="assets"', html)
        self.assertIn("document.querySelectorAll('[data-dock-add]')", js)
        self.assertIn("document.querySelectorAll('[data-dock-action]')", js)
        self.assertIn("node-type-icon", js)
        self.assertIn(".canvas-create-dock", css)
        self.assertIn(".dock-icon", css)
        self.assertIn(".node-type-icon", css)
        self.assertIn(".toolbar button::before", css)
        self.assertIn(".stage-icon", css)

    def test_canvas_dock_is_excluded_from_canvas_pointer_selection_capture(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        pointerdown = js[js.index("els.canvasArea.addEventListener('pointerdown', (event) => {"):]
        pointerdown = pointerdown[:pointerdown.index("els.canvasArea.addEventListener('dragover'")]
        middle_pan = js[js.index("function startCanvasMiddlePanCapture(event) {"):]
        middle_pan = middle_pan[:middle_pan.index("function startMarquee(event) {")]
        add_menu = js[js.index("function showAddMenu(event) {"):]
        add_menu = add_menu[:add_menu.index("function showConnectionAddMenu")]

        self.assertIn(".canvas-create-dock", pointerdown)
        self.assertLess(pointerdown.index(".canvas-create-dock"), pointerdown.index("startMarquee(event)"))
        self.assertIn(".canvas-create-dock", middle_pan)
        self.assertIn(".canvas-create-dock", add_menu)

    def test_dock_created_nodes_center_and_avoid_overlap(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        add_node = js[js.index("function addNode(type, patch = {}) {"):]
        add_node = add_node[:add_node.index("function renderAll() {")]
        self.assertIn("function nextNodePlacement(size)", js)
        placement = js[js.index("function nextNodePlacement(size)"):js.index("function addNode(type, patch = {})")]

        self.assertIn("const size = defaultSize(type)", add_node)
        self.assertIn("const position = nextNodePlacement(size)", add_node)
        self.assertIn("x: position.x", add_node)
        self.assertIn("y: position.y", add_node)
        self.assertIn("const center = centerWorldPoint()", placement)
        self.assertIn("state.nodes.some(", placement)
        self.assertIn("state.viewport.scale", placement)
        self.assertIn("const gap = 20 / scale", placement)
        self.assertIn("const horizontalStep = size.w + gap", placement)
        self.assertIn("const verticalStep = size.h + gap", placement)
        self.assertIn("candidate.x + size.w + gap > node.x", placement)
        self.assertIn("candidate.y + size.h + gap > node.y", placement)
        self.assertNotIn("placedCount", add_node)
        self.assertLess(add_node.index("const position = nextNodePlacement(size)"), add_node.index("state.nodes.push(node)"))

    def test_regular_nodes_expose_resize_handle(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('class="node-resize"', js)
        self.assertIn("function startNodeResize", js)
        self.assertIn("startNodeResize(event, node)", js)
        self.assertIn("activeDrag.kind === 'resize-node'", js)
        self.assertIn(".node-resize", css)

    def test_group_nodes_can_be_renamed_from_group_label(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function renameGroup", js)
        self.assertIn('data-group-action="rename"', js)
        self.assertIn("element.querySelector('.group-title').addEventListener('dblclick'", js)
        self.assertIn("renameGroup(node)", js)
        self.assertIn(".group-label", css)
        self.assertIn(".group-rename", css)

    def test_group_rename_is_inline_not_browser_prompt(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn("window.prompt('分组名称'", js)
        self.assertIn("let activeGroupRenameId", js)
        self.assertIn("function commitGroupRename", js)
        self.assertIn("function cancelGroupRename", js)
        self.assertIn('data-group-rename-input', js)
        self.assertIn("event.key === 'Enter'", js)
        self.assertIn("event.key === 'Escape'", js)
        self.assertIn(".group-rename-input", css)

    def test_edges_expose_visible_delete_action(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("let selectedEdgeId", js)
        self.assertIn("function selectEdge", js)
        self.assertIn("function deleteEdge", js)
        self.assertIn("edge-group", js)
        self.assertIn("edge-delete-control", js)
        self.assertIn("edge-delete-hit", js)
        self.assertIn("glyph.textContent = '×'", js)
        self.assertIn("deleteEdge(selectedEdgeId)", js)
        self.assertIn("event.key === 'Delete' || event.key === 'Backspace'", js)
        self.assertIn(".edge-group:hover .edge-path", css)
        self.assertIn(".edge-group.selected .edge-path", css)
        self.assertIn(".edge-delete-control", css)
        self.assertIn(".edge-delete-hit", css)
        self.assertIn("opacity: 0", css)
        self.assertIn("pointer-events: stroke", css)
        self.assertIn("fill: var(--danger)", css)
        self.assertNotIn("node-tool-delete", js)

    def test_edge_delete_control_uses_svg_hit_area_not_foreign_object(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertNotIn("'foreignObject'", js)
        self.assertIn("edge-hit-path", js)
        self.assertIn("edge-delete-control", js)
        self.assertIn("edge-delete-hit", js)
        self.assertIn("deleteGroup.addEventListener('pointerdown'", js)
        self.assertIn("deleteGroup.addEventListener('click'", js)
        self.assertIn(".edge-hit-path", css)
        self.assertIn("stroke-width: 24", css)
        self.assertIn("stroke: transparent", css)
        self.assertIn(".edge-delete-hit", css)

    def test_canvas_layers_do_not_block_edge_hover(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertRegex(css, r"\.edge-layer\s*\{[^}]*pointer-events:\s*auto")
        self.assertRegex(css, r"\.node-layer\s*\{[^}]*pointer-events:\s*none")
        self.assertRegex(css, r"\.node,\s*\n\.group-node\s*\{[^}]*pointer-events:\s*auto")

    def test_rendering_does_not_autoshrink_node_height(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function minSize", js)
        self.assertIn("if (type === 'image') return { w: 360, h: 460 }", js)
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

    def test_middle_mouse_pan_works_over_nodes(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function startCanvasMiddlePanCapture", js)
        self.assertIn("if (event.button !== 1) return", js)
        self.assertIn("event.target.closest('.toolbar,.canvas-minimap,.add-menu,.canvas-create-dock')", js)
        self.assertIn("startPan(event)", js)
        self.assertIn("event.stopPropagation()", js)
        self.assertIn("els.canvasArea.addEventListener('pointerdown', startCanvasMiddlePanCapture, true)", js)

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

    def test_asset_button_opens_top_asset_page_without_side_rail(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertNotIn('id="railAssetBtn"', html)
        self.assertNotIn(".quick-rail", css)
        self.assertIn('id="assetDrawer"', html)
        self.assertIn('id="assetDrawerGrid"', html)
        self.assertIn(".asset-drawer", css)
        self.assertIn("#assetPanel", css)
        self.assertIn("display: none", css)
        self.assertIn("function toggleAssetPage", js)
        self.assertIn("function showAssetPage", js)
        self.assertIn("function showAssetDrawer", js)
        self.assertIn("function renderAssetDrawer", js)
        self.assertIn("hideAssetDrawer", js)
        self.assertIn("els.assetBtn.addEventListener('click', () => showAssetPage().catch(showError))", js)
        self.assertIn("navigateTo('/assets')", js)
        self.assertNotIn('id="workflowBtn"', html)
        self.assertNotIn("workflowBtn", js)

    def test_secondary_pages_are_route_addressable(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        main = (ROOT / "main.py").read_text(encoding="utf-8")

        self.assertIn('id="assetPage"', html)
        self.assertIn('id="accountPage"', html)
        self.assertIn('id="logsPage"', html)
        self.assertIn('id="accountBackBtn"', html)
        self.assertIn('id="logsBackBtn"', html)
        self.assertIn('id="logsPageList"', html)

        self.assertIn("function navigateTo", js)
        self.assertIn("function showAccountPage", js)
        self.assertIn("function showLogsPage", js)
        self.assertIn("function applyRouteFromLocation", js)
        self.assertIn("window.addEventListener('popstate', applyRouteFromLocation)", js)
        self.assertIn("els.logBtn.addEventListener('click', showLogsPage)", js)
        self.assertIn("els.accountBtn.addEventListener('click', showAccountPage)", js)

        self.assertIn(".app-shell.subpage-open", css)
        self.assertIn(".subpage-head", css)
        self.assertIn(".account-page-grid", css)
        self.assertIn(".logs-page-list", css)

        self.assertIn('@app.get("/assets")', main)
        self.assertIn('@app.get("/account")', main)
        self.assertIn('@app.get("/logs")', main)

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

    def test_full_image_preview_shrinks_to_media_without_a_white_frame(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        card_blocks = re.findall(r"^\.media-preview-card\s*\{([^}]*)\}", css, re.M | re.S)
        image_blocks = re.findall(r"^\.media-preview-card img\s*\{([^}]*)\}", css, re.M | re.S)

        self.assertTrue(card_blocks)
        self.assertTrue(image_blocks)
        for declaration in [
            "width: fit-content;",
            "height: fit-content;",
            "max-width: calc(100vw - 56px);",
            "max-height: calc(100dvh - 56px);",
            "border: 0;",
            "background: transparent;",
            "box-shadow: none;",
            "padding: 0;",
        ]:
            self.assertIn(declaration, card_blocks[-1])
        for declaration in [
            "min-width: 0;",
            "min-height: 0;",
            "max-width: calc(100vw - 56px);",
            "max-height: calc(100dvh - 56px);",
        ]:
            self.assertIn(declaration, image_blocks[-1])
        self.assertRegex(image_blocks[-1], r"box-shadow:\s*0 24px 80px rgba\(0, 0, 0, 0\.38\);")

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
        self.assertIn("image_size: node.imageSize", js)
        self.assertIn("image_scale: Number(node.imageScale", js)
        self.assertIn("options: taskOptions(node)", js)
        self.assertNotIn("imageQuality", js)
        self.assertNotIn("image_quality", js)
        self.assertNotIn("data-field=\"imageQuality\"", js)
        self.assertNotIn("画质", js)
        self.assertIn(".image-option-grid", css)
        self.assertIn(".image-scale-group", css)

    def test_generation_tools_reflect_backend_capabilities(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        capability_apply = js[js.index("function applyGenerationCapabilities() {"):]
        capability_apply = capability_apply[:capability_apply.index("async function loadGenerationCapabilities() {")]

        self.assertIn("async function loadGenerationCapabilities", js)
        self.assertIn("function applyGenerationCapabilities", js)
        self.assertIn("/api/capabilities", js)
        self.assertIn("data-capability-disabled", js)
        self.assertIn("button.disabled = false", capability_apply)
        self.assertIn("data-capability-configured", capability_apply)
        self.assertIn("可先添加和编辑，运行前需配置", capability_apply)
        self.assertNotIn("button.disabled = !configured", capability_apply)
        self.assertIn("if (!capability.configured)", js)

    def test_compact_topbar_and_account_actions_remain_visible(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("@media (max-width: 1200px)", css)
        self.assertIn(".account-page-grid .subpage-card:first-child strong", css)
        self.assertRegex(css, r"\.account-actions-card\s+\.danger-button\s*\{[^}]*color:\s*#fff")
        self.assertRegex(css, r"@media \(max-width: 1200px\)[\s\S]*\.toolbar button\s*\{[^}]*font-size:\s*0")
        self.assertIn("button.title = button.textContent.trim()", js)

    def test_canvas_saves_with_optimistic_revision(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        save = js[
            js.index("async function saveCanvas(options = {})") :
            js.index("async function saveCurrentCanvasIfDirty()")
        ]
        self.assertIn("const canvasAtStart = currentCanvas", save)
        self.assertIn("revision: canvasAtStart.revision", save)
        self.assertLess(
            save.index("const canvasAtStart = currentCanvas"),
            save.index("await api("),
        )
        self.assertIn("画布已在其他页面更新", js)

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

    def test_remote_nodes_send_structured_options_and_reconcile_finished_tasks(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function taskOptions(node)", js)
        self.assertIn("options: taskOptions(node)", js)
        self.assertIn("async function reconcileTasksToNodes(tasks)", js)
        self.assertIn("await reconcileTasksToNodes(tasks)", js)
        self.assertIn("applyTaskResult(node, task)", js)
        self.assertIn("const reconciledNodeIds = new Set()", js)
        self.assertIn("if (node.taskId && node.taskId !== task.id) return", js)

    def test_sidebar_workspace_minimap_and_assets_are_canvas_friendly(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertIn('class="app-sidebar"', html)
        self.assertIn('class="sidebar-nav"', html)
        self.assertIn(".workspace-cluster", css)
        self.assertIn(".workspace-menu", css)
        self.assertIn('id="projectCurrentName"', html)
        self.assertIn('id="canvasCurrentName"', html)

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

    def test_toolbar_has_compact_overflow_treatment(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertIn(".toolbar-shell", css)
        self.assertIn(".toolbar-shell::before", css)
        self.assertIn(".toolbar-shell::after", css)
        self.assertIn("scroll-snap-type: x proximity", css)
        self.assertIn("scroll-snap-align: start", css)
        self.assertIn("max-width: clamp(420px, 52vw, 900px)", css)

    def test_toasts_replace_browser_alerts(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        admin_html = (ROOT / "static" / "admin.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        admin_js = (ROOT / "static" / "admin.js").read_text(encoding="utf-8")

        self.assertIn('id="toastRegion"', html)
        self.assertIn('id="adminToastRegion"', admin_html)
        self.assertIn(".toast-region", css)
        self.assertIn(".toast-message", css)
        self.assertIn("function showToast", app_js)
        self.assertIn("showToast(message, 'error')", app_js)
        self.assertIn("function showAdminToast", admin_js)
        self.assertNotIn("window.alert", app_js)
        self.assertNotIn("window.alert", admin_js)

    def test_auth_pages_have_commercial_styling(self):
        html = (ROOT / "static" / "auth.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertIn('class="auth-shell"', html)
        self.assertIn('class="auth-panel"', html)
        self.assertNotIn('placeholder="canvasv1"', html)
        for selector in [
            ".auth-body",
            ".auth-shell",
            ".auth-panel",
            ".field-input",
            ".field-label",
            ".error-line",
            ".text-link",
        ]:
            self.assertIn(selector, css)
        self.assertIn("min-height: 100vh", css)
        self.assertIn("backdrop-filter", css)

    def test_dark_secondary_pages_use_shared_dark_material_tokens(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]

        self.assertRegex(
            final_css,
            r'\[data-theme="dark"\]\s*\{[^}]*--app-bg:\s*#0c131d;[^}]*--canvas-bg:\s*#0d141e;',
        )
        self.assertRegex(
            final_css,
            r'\[data-theme="dark"\]\s+\.asset-page,\s*\n\[data-theme="dark"\]\s+\.subpage\s*\{[^}]*background-color:\s*var\(--canvas-bg\)',
        )
        self.assertIn('[data-theme="dark"] .sidebar-actions > button.active', final_css)

    def test_workflow_templates_and_director_recipe_are_exposed(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertIn('id="directorRecipeBtn"', html)
        self.assertIn('id="saveWorkflowTemplateBtn"', html)
        self.assertIn('id="workflowTemplateList"', html)

        self.assertIn("function addDirectorRecipe", js)
        self.assertIn("function saveWorkflowTemplate", js)
        self.assertIn("function insertWorkflowTemplate", js)
        self.assertIn("function insertWorkflowPayload", js)
        self.assertIn("function loadWorkflowTemplates", js)
        self.assertIn("/api/workflows", js)
        self.assertIn("els.directorRecipeBtn.addEventListener", js)
        self.assertIn("els.saveWorkflowTemplateBtn.addEventListener", js)

        self.assertIn(".workflow-template-list", css)
        self.assertIn(".workflow-template-item", css)

    def test_director_desk_uses_structured_blueprint_logic(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("director: '导演台'", js)
        self.assertIn("if (type === 'director') return { w: 760, h: 620 }", js)
        self.assertIn("function addDirectorNode", js)
        self.assertIn("function directorSystemPrompt", js)
        self.assertIn("function parseDirectorJson", js)
        self.assertIn("function normalizeDirectorResult", js)
        self.assertIn("function buildDirectorBlueprintNodes", js)
        self.assertIn("function directorItemPrompt", js)
        self.assertIn("function directorNodeHtml", js)
        self.assertIn("data-director-action=\"extract\"", js)
        self.assertIn("data-director-action=\"build\"", js)
        self.assertIn("characters", js)
        self.assertIn("scenes", js)
        self.assertIn("props", js)
        self.assertIn("shots", js)
        self.assertIn("videoSegments", js)
        self.assertIn("['人物资产区'", js)
        self.assertIn("['场景资产区'", js)
        self.assertIn("['物品资产区'", js)
        self.assertIn("['分镜区'", js)
        self.assertIn("['视频任务区'", js)
        self.assertIn("addDirectorNode()", js)
        self.assertIn("els.directorRecipeBtn.addEventListener('click', addDirectorNode)", js)

    def test_account_storage_password_and_asset_delete_controls_are_exposed(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        main = (ROOT / "main.py").read_text(encoding="utf-8")

        self.assertIn('id="accountStorageUsed"', html)
        self.assertIn('id="accountStorageLimit"', html)
        self.assertIn('id="passwordChangeForm"', html)
        self.assertIn('id="currentPasswordInput"', html)
        self.assertIn('id="newPasswordInput"', html)
        self.assertIn('id="confirmPasswordInput"', html)
        self.assertIn("function updateStorageSummary", js)
        self.assertIn("method: 'DELETE'", js)
        self.assertIn("'/api/account/password'", js)
        self.assertIn('@app.delete("/api/assets/{asset_id}")', main)
        self.assertIn('@app.post("/api/account/password")', main)

    def test_approved_apple_glass_design_system_covers_every_surface(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        auth = (ROOT / "static" / "auth.html").read_text(encoding="utf-8")
        admin = (ROOT / "static" / "admin.html").read_text(encoding="utf-8")

        for token in [
            "--glass-surface",
            "--glass-surface-strong",
            "--glass-border",
            "--glass-highlight",
            "--system-blue",
            "--ease-out",
        ]:
            self.assertIn(token, css)
        for selector in [
            ".topbar",
            ".canvas-create-dock",
            ".node",
            ".canvas-minimap",
            ".asset-page",
            ".logs-page",
            ".account-page",
            ".auth-panel",
            ".admin-shell",
        ]:
            self.assertIn(selector, css)
        self.assertIn("var(--grid-size", css)
        self.assertIn("var(--grid-x", css)
        self.assertIn("var(--grid-y", css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)
        self.assertIn('class="auth-body"', auth)
        self.assertIn('class="admin-shell"', admin)

    def test_final_spatial_material_layer_defines_light_and_dark_reference_tokens(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        marker = "/* Approved bright silver glass system, 2026-07-10. */"
        self.assertIn(marker, css)
        final_css = css.split(marker, 1)[1]

        light_tokens = {
            "--app-bg": "#f4f5fa",
            "--canvas-bg": "#f2f4f9",
            "--glass-surface": "rgba(255, 255, 255, 0.76)",
            "--glass-surface-strong": "rgba(255, 255, 255, 0.88)",
            "--glass-border": "rgba(119, 136, 158, 0.22)",
            "--ink": "#151b26",
            "--muted": "#737b88",
            "--sidebar-width": "167px",
            "--topbar-height": "66px",
        }
        root_block = re.search(r":root\s*\{(?P<body>[^}]*)\}", final_css, re.S)
        self.assertIsNotNone(root_block)
        for token, value in light_tokens.items():
            self.assertIn(f"{token}: {value};", root_block.group("body"))

        dark_block = re.search(r'\[data-theme="dark"\]\s*\{(?P<body>[^}]*)\}', final_css, re.S)
        self.assertIsNotNone(dark_block)
        for token, value in {
            "--app-bg": "#0c131d",
            "--canvas-bg": "#0d141e",
            "--glass-surface": "rgba(24, 32, 43, 0.82)",
            "--glass-surface-strong": "rgba(24, 32, 43, 0.9)",
            "--glass-border": "rgba(164, 181, 204, 0.22)",
            "--ink": "#f4f7fb",
            "--muted": "#9fa9b6",
        }.items():
            self.assertIn(f"{token}: {value};", dark_block.group("body"))

    def test_final_spatial_material_layer_drives_every_route_and_overlay(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]

        for selector in [
            ".app-shell",
            ".app-main",
            ".canvas-area",
            ".asset-page",
            ".subpage",
            ".auth-body",
            ".auth-panel",
            ".admin-shell",
            ".add-menu",
            ".asset-drawer",
            ".modal-card",
            ".toast-message",
        ]:
            self.assertIn(selector, final_css)

        self.assertGreaterEqual(final_css.count("var(--app-bg)"), 5)
        self.assertGreaterEqual(final_css.count("var(--canvas-bg)"), 3)
        self.assertGreaterEqual(final_css.count("var(--glass-surface)"), 12)
        self.assertGreaterEqual(final_css.count("var(--glass-border)"), 12)
        self.assertGreaterEqual(final_css.count("color: var(--ink)"), 6)
        self.assertGreaterEqual(final_css.count("color: var(--muted)"), 6)

    def test_final_spatial_material_layer_matches_reference_geometry(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]

        self.assertRegex(
            final_css,
            r"\.app-shell\s*\{[^}]*grid-template-columns:\s*var\(--sidebar-width\)\s+minmax\(0,\s*1fr\)",
        )
        self.assertRegex(final_css, r"\.app-sidebar\s*\{[^}]*width:\s*var\(--sidebar-width\)")
        self.assertRegex(final_css, r"\.app-main\s*\{[^}]*grid-template-rows:\s*var\(--topbar-height\)\s+minmax\(0,\s*1fr\)")
        self.assertRegex(
            final_css,
            r"\.canvas-create-dock\s*\{[^}]*left:\s*50%;[^}]*bottom:\s*34px;[^}]*grid-template-columns:\s*repeat\(6,\s*minmax\(64px,\s*1fr\)\);[^}]*transform:\s*translateX\(-50%\)",
        )
        dock_block = re.search(r"\.canvas-create-dock\s*\{(?P<body>[^}]*)\}", final_css, re.S)
        self.assertIsNotNone(dock_block)
        self.assertIn("min-height: 108px;", dock_block.group("body"))
        self.assertRegex(final_css, r"\.zoom-chip\s*\{[^}]*left:\s*28px;[^}]*bottom:\s*28px")
        self.assertRegex(final_css, r"\.canvas-minimap\s*\{[^}]*right:\s*18px;[^}]*bottom:\s*18px;[^}]*opacity:\s*1")
        minimap_block = re.search(r"\.canvas-minimap\s*\{(?P<body>[^}]*)\}", final_css, re.S)
        self.assertIsNotNone(minimap_block)
        self.assertIn("background: var(--glass-surface-strong);", minimap_block.group("body"))
        self.assertIn("backdrop-filter: none;", minimap_block.group("body"))
        self.assertIn("-webkit-backdrop-filter: none;", minimap_block.group("body"))
        zoom_blocks = re.findall(r"\.zoom-chip\s*\{([^}]*)\}", final_css, re.S)
        self.assertTrue(any("left: 28px;" in block and "opacity: 0;" in block for block in zoom_blocks))
        self.assertIn("@media (max-width: 1100px)", final_css)
        self.assertIn("--sidebar-width: 116px", final_css)

    def test_creation_dock_is_unframed_with_blue_gray_controls(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        dock_blocks = re.findall(r"^\.canvas-create-dock\s*\{([^}]*)\}", css, re.M | re.S)
        button_blocks = re.findall(r"^\.canvas-create-dock button\s*\{([^}]*)\}", css, re.M | re.S)
        dark_dock_blocks = re.findall(
            r'^\[data-theme="dark"\] \.canvas-create-dock\s*\{([^}]*)\}',
            css,
            re.M | re.S,
        )
        dark_button_blocks = re.findall(
            r'^\[data-theme="dark"\] \.canvas-create-dock button\s*\{([^}]*)\}',
            css,
            re.M | re.S,
        )

        self.assertTrue(dock_blocks)
        self.assertTrue(button_blocks)
        self.assertTrue(dark_dock_blocks)
        self.assertTrue(dark_button_blocks)
        for declaration in [
            "border: 0;",
            "background: transparent;",
            "box-shadow: none;",
            "backdrop-filter: none;",
            "pointer-events: none;",
        ]:
            self.assertIn(declaration, dock_blocks[-1])
        self.assertIn("pointer-events: auto;", button_blocks[-1])
        self.assertIn("--dock-label: #344154;", dock_blocks[-1])
        self.assertIn("--dock-icon: #5c6b80;", dock_blocks[-1])
        self.assertIn("--dock-label: #e3eaf4;", dark_dock_blocks[-1])
        self.assertIn("--dock-icon: #b8c5d6;", dark_dock_blocks[-1])
        self.assertIn("color: var(--dock-label);", dark_button_blocks[-1])
        self.assertRegex(
            css,
            r"\.canvas-create-dock button:(?:hover|focus-visible)[^{]*\{[^}]*color:\s*var\(--system-blue\);",
        )
        self.assertRegex(
            css,
            r"\.canvas-create-dock button:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--system-blue\);",
        )
        self.assertRegex(
            css,
            r'\[data-theme="dark"\] \.canvas-create-dock button:hover,[^{]*\{[^}]*background:\s*var\(--dock-hover-bg\);',
        )

    def test_reference_brand_stacks_without_clipping_on_desktop(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]
        brand_block = re.search(r"\.sidebar-brand\s*\{(?P<body>[^}]*)\}", final_css, re.S)

        self.assertIsNotNone(brand_block)
        for declaration in [
            "display: flex;",
            "flex-direction: column;",
            "align-items: flex-start;",
        ]:
            self.assertIn(declaration, brand_block.group("body"))
        self.assertRegex(final_css, r"\.sidebar-brand\s+strong\s*\{[^}]*white-space:\s*nowrap")

        compact_css = final_css[final_css.index("@media (max-width: 1100px)"):]
        self.assertRegex(
            compact_css,
            r"\.sidebar-brand\s*>\s*span:last-child,[^{]*\{[^}]*display:\s*none;",
        )

    def test_topbar_keeps_one_visible_primary_run_action_with_official_play_icon(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        phosphor_css = (ROOT / "static" / "vendor" / "phosphor" / "phosphor.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]

        self.assertRegex(
            html,
            r'<button id="runChainBtn"[^>]*>\s*<i class="ph ph-play"[^>]*></i>\s*<span>&#36816;&#34892;</span>\s*</button>',
        )
        self.assertIn('.ph.ph-play::before { content: "\\e3d0"; }', phosphor_css)
        self.assertRegex(
            final_css,
            r"#runBtn,\s*\n#saveBtn\s*\{[^}]*display:\s*none;",
        )
        self.assertRegex(
            final_css,
            r"#runChainBtn\s*\{[^}]*border-color:\s*var\(--system-blue\);[^}]*background:",
        )
        self.assertIn("els.runBtn.addEventListener('click'", (ROOT / "static" / "app.js").read_text(encoding="utf-8"))
        self.assertIn("els.saveBtn.addEventListener('click'", (ROOT / "static" / "app.js").read_text(encoding="utf-8"))

    def test_all_entrypoints_use_the_qa_cache_version(self):
        for page in ["index.html", "auth.html", "admin.html"]:
            with self.subTest(page=page):
                html = (ROOT / "static" / page).read_text(encoding="utf-8")
                self.assertIn("/static/app.css?v=20260714-interaction-fix3", html)
        index_html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn("/static/app.js?v=20260714-interaction-fix3", index_html)

    def test_final_layer_disables_legacy_sidebar_character_icons(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]

        self.assertRegex(
            final_css,
            r"#assetBtn::before,\s*\n#logBtn::before,\s*\n#themeToggleBtn::before\s*\{[^}]*content:\s*none;[^}]*display:\s*none;",
        )

    def test_final_dark_layer_reclaims_legacy_high_specificity_surfaces(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]

        expected = {
            ".asset-tabs": [
                "border-color: var(--glass-border);",
                "background: var(--glass-surface);",
                "color: var(--ink);",
            ],
            ".logs-page-item": [
                "border-color: var(--glass-border);",
                "background: transparent;",
                "color: var(--ink);",
            ],
            ".empty-hint": [
                "border-color: transparent;",
                "background: transparent;",
                "color: var(--ink);",
            ],
            ".asset-upload-tile": [
                "border-color: var(--glass-border);",
                "background: var(--glass-surface);",
                "color: var(--muted);",
            ],
            ".minimap-actions button": [
                "border-color: var(--glass-border);",
                "background: transparent;",
                "color: var(--ink);",
            ],
            ".canvas-minimap": [
                "border-color: var(--glass-border);",
                "background: var(--glass-surface-strong);",
                "box-shadow: var(--glass-highlight), var(--glass-shadow);",
            ],
            ".minimap-view": [
                "border-color: var(--glass-border);",
                "background-color: var(--canvas-bg);",
            ],
        }
        for selector, declarations in expected.items():
            with self.subTest(selector=selector):
                block = re.search(
                    rf'\[data-theme="dark"\]\s+{re.escape(selector)}\s*\{{(?P<body>[^}}]*)\}}',
                    final_css,
                    re.S,
                )
                self.assertIsNotNone(block)
                for declaration in declarations:
                    self.assertIn(declaration, block.group("body"))

    def test_modal_scrim_stays_crisp_while_modal_card_keeps_glass_blur(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]

        modal_block = re.search(r"\.modal\s*\{(?P<body>[^}]*)\}", final_css, re.S)
        self.assertIsNotNone(modal_block)
        self.assertIn("background: var(--scrim);", modal_block.group("body"))
        self.assertIn("backdrop-filter: none;", modal_block.group("body"))
        self.assertIn("-webkit-backdrop-filter: none;", modal_block.group("body"))
        self.assertRegex(
            final_css,
            r"\.modal-card,\s*\n\.canvas-create-card\s*\{[^}]*backdrop-filter:\s*blur\(24px\)",
        )

    def test_new_media_nodes_open_with_complete_controls(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]

        self.assertIn("if (type === 'image') return { w: 520, h: 780 }", js)
        self.assertIn("if (type === 'video') return { w: 520, h: 780 }", js)
        self.assertIn("if (type === 'output') return { w: 340, h: 270 }", js)
        self.assertIn("if (type === 'image') return { w: 360, h: 460 }", js)
        self.assertIn("grid-template-columns: repeat(auto-fit, minmax(104px, 1fr));", final_css)
        self.assertIn("flex-wrap: wrap;", final_css)
        self.assertIn("justify-content: flex-start;", final_css)

    def test_canvas_zoom_uses_layout_scaling_instead_of_raster_transform_scaling(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="viewportPan"', html)
        self.assertIn('id="worldScale"', html)
        self.assertIn("viewportPan: document.getElementById('viewportPan')", js)
        self.assertIn("worldScale: document.getElementById('worldScale')", js)
        self.assertIn("els.viewportPan.style.transform = `translate3d(${x}px, ${y}px, 0)`", js)
        self.assertIn("els.worldScale.style.zoom = String(scale)", js)
        self.assertNotIn("scale(${scale})", js)
        self.assertRegex(css, r"\.viewport-pan\s*\{[^}]*will-change:\s*transform")
        self.assertRegex(css, r"\.world-scale\s*\{[^}]*width:\s*0")
        self.assertRegex(css, r"\.world\s*\{[^}]*will-change:\s*auto")

    def test_dark_theme_covers_director_controls_and_node_surfaces(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertRegex(css, r'\[data-theme="dark"\]\s+\.director-actions\s+\.primary\s*\{[^}]*background:\s*var\(--system-blue\)[^}]*color:\s*#fff')
        self.assertRegex(css, r'\[data-theme="dark"\]\s+\.director-counts\s+span,[\s\S]*\[data-theme="dark"\]\s+\.director-tabs\s+button\s*\{[^}]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.06\)[^}]*color:\s*var\(--muted\)')
        self.assertRegex(css, r'\[data-theme="dark"\]\s+\.director-tabs\s+button\.active\s*\{[^}]*background:\s*var\(--system-blue\)[^}]*color:\s*#fff')
        self.assertRegex(css, r'\[data-theme="dark"\]\s+\.stage-icon,[\s\S]*\[data-theme="dark"\]\s+\.node-head\s*\{[^}]*background:\s*rgba\(255,\s*255,\s*255,\s*0\.04\)')

    def test_final_motion_layer_has_immediate_press_feedback_without_node_transform_transition(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]

        root_block = re.search(r":root\s*\{(?P<body>[^}]*)\}", final_css, re.S)
        self.assertIsNotNone(root_block)
        self.assertIn("--press-scale: 0.97;", root_block.group("body"))
        self.assertIn("--motion-press: 90ms;", root_block.group("body"))
        self.assertRegex(
            final_css,
            r"button:not\(:disabled\):not\(\.edge-delete-control\):active,[\s\S]*\[role=\"button\"\]:not\(\[aria-disabled=\"true\"\]\):not\(\.edge-delete-control\):active\s*\{[^}]*transform:\s*scale\(var\(--press-scale\)\);[^}]*transition-duration:\s*var\(--motion-press\);[^}]*transition-delay:\s*0ms;",
        )
        node_block = re.search(r"\.node\s*\{(?P<body>[^}]*)\}", final_css, re.S)
        self.assertIsNotNone(node_block)
        node_transition = re.search(r"transition:\s*(?P<value>[^;]+);", node_block.group("body"))
        self.assertIsNotNone(node_transition)
        self.assertNotIn("transform", node_transition.group("value"))
        self.assertRegex(final_css, r"\.canvas-create-dock\s*\{[^}]*transform:\s*translateX\(-50%\)")

    def test_apply_theme_preserves_phosphor_icon_and_maps_official_sun_glyph(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        phosphor = (ROOT / "static" / "vendor" / "phosphor" / "phosphor.css").read_text(encoding="utf-8")
        apply_theme = js[js.index("function applyTheme"):js.index("function toggleTheme")]

        self.assertIn("els.themeToggleBtn.querySelector('span')", apply_theme)
        self.assertIn("els.themeToggleBtn.querySelector('i.ph')", apply_theme)
        self.assertIn("classList.toggle('ph-sun', dark)", apply_theme)
        self.assertIn("classList.toggle('ph-moon', !dark)", apply_theme)
        self.assertNotIn("themeToggleBtn.textContent", apply_theme)
        self.assertRegex(phosphor, r'\.ph\.ph-sun::before\s*\{\s*content:\s*"\\e472";\s*\}')

    def test_shared_pointer_action_captures_cancels_and_releases_the_active_pointer(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function beginPointerAction(event, drag)", js)
        self.assertIn("pointerId: event.pointerId", js)
        self.assertIn("pointerTarget: event.currentTarget", js)
        self.assertIn("setPointerCapture?.(event.pointerId)", js)
        self.assertIn("window.addEventListener('pointercancel', endPointerAction)", js)
        self.assertIn("releasePointerCapture?.(finished.pointerId)", js)
        self.assertIn("event?.type === 'pointercancel'", js)
        self.assertIn("event.pointerId !== activeDrag.pointerId", js)
        self.assertGreaterEqual(js.count("beginPointerAction(event,"), 5)

    def test_pan_momentum_uses_recent_velocity_and_is_interruptible_and_reduced_motion_safe(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("let panMomentumRaf = 0", js)
        self.assertIn("function cancelPanMomentum()", js)
        self.assertIn("function startPanMomentum(samples)", js)
        self.assertIn("requestAnimationFrame(step)", js)
        self.assertIn("cancelAnimationFrame(panMomentumRaf)", js)
        self.assertIn("prefersReducedMotion()", js)
        self.assertIn("timeStamp: event.timeStamp", js)
        self.assertIn("activeDrag.samples = activeDrag.samples.slice(-6)", js)
        self.assertIn("if (!cancelled && finished.kind === 'pan') startPanMomentum(finished.samples)", js)
        self.assertIn("els.canvasArea.addEventListener('pointerdown', cancelPanMomentum, true)", js)
        handle_wheel = js[js.index("function handleWheel"):js.index("function showCreateCanvasModal")]
        self.assertLess(handle_wheel.index("cancelPanMomentum()"), handle_wheel.index("zoomAtCanvasPoint"))

    def test_asset_page_materializes_and_sets_busy_before_loading(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        block = js[js.index("async function showAssetPage"):js.index("function toggleAssetPage")]

        self.assertIn("els.assetPage.setAttribute('aria-busy', 'true')", block)
        self.assertIn("els.assetPage.setAttribute('aria-busy', 'false')", block)
        shell_index = block.index("els.assetPage.classList.remove('hidden')")
        busy_index = block.index("els.assetPage.setAttribute('aria-busy', 'true')")
        await_index = block.index("await loadAssets()")
        self.assertLess(shell_index, await_index)
        self.assertLess(busy_index, await_index)
        self.assertIn("finally", block)
        self.assertGreater(block.index("els.assetPage.setAttribute('aria-busy', 'false')"), await_index)

    def test_view_materialization_is_single_cancelable_symmetric_and_reduced_motion_safe(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("let activeViewAnimation = null", js)
        self.assertIn("function cancelViewAnimation(", js)
        self.assertIn("function animateView(target, direction = 'forward')", js)
        self.assertIn("activeViewAnimation.cancel()", js)
        self.assertIn("getComputedStyle(target)", js)
        self.assertIn("target.animate(keyframes", js)
        self.assertIn("direction === 'back' ? -8 : 8", js)
        self.assertIn("const keyframes = reduced", js)
        self.assertIn("[{ opacity: startOpacity }, { opacity: 1 }]", js)
        self.assertIn("animateView(els.canvasArea, 'back')", js)
        self.assertGreaterEqual(js.count("animateView("), 5)
        asset_block = js[js.index("async function showAssetPage"):js.index("function toggleAssetPage")]
        self.assertLess(asset_block.index("classList.remove('hidden')"), asset_block.index("animateView(els.assetPage"))

    def test_accessibility_motion_transparency_contrast_and_cache_contract(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]

        reduced = final_css[final_css.index("@media (prefers-reduced-motion: reduce)"):]
        self.assertNotIn("0.01ms", reduced)
        self.assertRegex(reduced, r"transition-duration:\s*120ms\s*!important")
        self.assertIn("transition-property: color, background-color, border-color, box-shadow, opacity !important;", reduced)
        self.assertIn("@media (prefers-reduced-transparency: reduce)", final_css)
        self.assertIn("backdrop-filter: none !important", final_css)
        self.assertIn("@media (prefers-contrast: more)", final_css)
        self.assertIn("outline: 3px solid var(--system-blue)", final_css)

        version = "20260714-interaction-fix3"
        index_html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f'/static/app.css?v={version}', index_html)
        self.assertIn(f'/static/app.js?v={version}', index_html)
        for name in ["auth.html", "admin.html"]:
            page = (ROOT / "static" / name).read_text(encoding="utf-8")
            self.assertIn(f'/static/app.css?v={version}', page)

    def test_pan_momentum_cannot_mutate_replaced_or_saved_canvas_state(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        momentum = js[js.index("function startPanMomentum"):js.index("function beginPointerAction")]
        self.assertIn("const momentumState = state", momentum)
        self.assertRegex(momentum, r"const step = \(time\) => \{\s*if \(state !== momentumState\) \{\s*panMomentumRaf = 0;\s*return;")

        boundaries = [
            ("async function selectProject", "async function selectCanvas"),
            ("async function saveCanvas", "async function saveCurrentCanvasIfDirty"),
            ("async function saveCurrentCanvasIfDirty", "function upstreamNodes"),
            ("async function showAssetPage", "function toggleAssetPage"),
            ("function showAccountPage", "async function submitPasswordChange"),
            ("function showLogsPage", "function applyRouteFromLocation"),
            ("function zoomBy", "function centerViewportOnWorld"),
            ("function centerViewportOnWorld", "function worldPointFromMinimap"),
            ("function bindMinimapEvents", "function handleWheel"),
        ]
        for start, end in boundaries:
            with self.subTest(boundary=start):
                block = js[js.index(start):js.index(end)]
                self.assertIn("cancelPanMomentum()", block)

        select_canvas = js[js.index("async function selectCanvas"):js.index("function renderProjects")]
        load_index = select_canvas.index("const data = await api")
        replace_index = select_canvas.index("state = normalizeState")
        cancel_before_replace = select_canvas.rindex("cancelPanMomentum()", 0, replace_index)
        self.assertGreater(cancel_before_replace, load_index)

        back_origin = js[js.index("els.backToOriginBtn.addEventListener('click'"):js.index("els.zoomOutBtn.addEventListener")]
        self.assertLess(back_origin.index("cancelPanMomentum()"), back_origin.index("state.viewport ="))

    def test_shared_pointer_starts_reject_secondary_pointer_before_side_effects(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        ranges = [
            ("function startNodeDrag", "function startGroupResize", "toggleSelect"),
            ("function startGroupResize", "function startNodeResize", "selectOnly"),
            ("function startNodeResize", "function prefersReducedMotion", "selectOnly"),
            ("function startPan(event)", "function startCanvasMiddlePanCapture", "beginPointerAction"),
            ("function startMarquee", "function onPointerMove", "selectionBox.classList.remove"),
        ]
        for start, end, first_side_effect in ranges:
            with self.subTest(start=start):
                block = js[js.index(start):js.index(end)]
                self.assertIn("if (activeDrag) return;", block)
                self.assertLess(block.index("if (activeDrag) return;"), block.index(first_side_effect))
                self.assertIn("if (!beginPointerAction(event, {", block)
        marquee = js[js.index("function startMarquee"):js.index("function onPointerMove")]
        self.assertRegex(marquee, r"if \(!beginPointerAction\(event, \{[^}]+\}\)\) return;[\s\S]*selectionBox\.classList\.remove")

    def test_view_animation_owns_cancellation_and_repeated_visible_routes_are_noops(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        animate = js[js.index("function animateView"):js.index("function showCanvasPage")]
        self.assertIn("cancelViewAnimation(target)", animate)

        route_contracts = [
            ("function showCanvasPage", "async function showAssetDrawer", "currentView === 'canvas'", "els.canvasArea"),
            ("async function showAssetPage", "function toggleAssetPage", "currentView === 'assets'", "els.assetPage"),
            ("function showAccountPage", "async function submitPasswordChange", "currentView === 'account'", "els.accountPage"),
            ("function showLogsPage", "function applyRouteFromLocation", "currentView === 'logs'", "els.logsPage"),
        ]
        for start, end, current_check, visible_target in route_contracts:
            with self.subTest(route=start):
                block = js[js.index(start):js.index(end)]
                self.assertNotIn("cancelViewAnimation();", block)
                self.assertIn(current_check, block)
                self.assertIn(f"!{visible_target}.classList.contains('hidden')", block)
                self.assertLess(block.index(current_check), block.index("animateView("))

        assets = js[js.index("async function showAssetPage"):js.index("function toggleAssetPage")]
        self.assertIn("currentView === 'assets'", assets)
        self.assertLess(assets.index("currentView === 'assets'"), assets.index("await loadAssets()"))
        self.assertIn("finally", assets)
        self.assertIn("setAttribute('aria-busy', 'false')", assets)

    def test_press_feedback_preserves_svg_edge_transform_and_canvas_cannot_scroll(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]

        self.assertRegex(
            final_css,
            r'\[role="button"\]:not\(\[aria-disabled="true"\]\):not\(\.edge-delete-control\):active',
        )
        edge_press = re.search(r"\.edge-delete-control:active\s*\{(?P<body>[^}]*)\}", final_css, re.S)
        self.assertIsNotNone(edge_press)
        self.assertIn("opacity:", edge_press.group("body"))
        self.assertNotIn("transform", edge_press.group("body"))
        self.assertRegex(final_css, r"\.edge-delete-control:active\s+\.edge-delete-hit\s*\{[^}]*stroke:\s*var\(--danger\)")

        canvas = re.search(r"\.canvas-area\s*\{(?P<body>[^}]*)\}", final_css, re.S)
        self.assertIsNotNone(canvas)
        self.assertIn("overflow: hidden;", canvas.group("body"))
        self.assertIn("overflow: clip;", canvas.group("body"))
        self.assertLess(canvas.group("body").index("overflow: hidden;"), canvas.group("body").index("overflow: clip;"))

    def test_theme_crossfade_uses_one_non_spatial_motion_contract(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]
        root_block = re.search(r":root\s*\{(?P<body>[^}]*)\}", final_css, re.S)
        self.assertIsNotNone(root_block)
        self.assertIn("--motion-theme: 220ms;", root_block.group("body"))
        for selector in [
            "body,",
            ".app-sidebar,",
            ".topbar,",
            ".canvas-area,",
            ".node,",
            ".asset-page,",
            ".subpage,",
            ".auth-body,",
            ".auth-panel,",
            ".admin-shell,",
            ".modal-card,",
            ".toast-message",
        ]:
            self.assertIn(selector, final_css)
        self.assertRegex(
            final_css,
            r"body,[\s\S]*\.toast-message\s*\{[^}]*transition-property:\s*color, background-color, border-color;[^}]*transition-duration:\s*var\(--motion-theme\);",
        )

    def test_reduced_transparency_and_contrast_make_nested_surfaces_opaque(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]
        transparency = final_css[final_css.index("@media (prefers-reduced-transparency: reduce)"):final_css.index("@media (prefers-contrast: more)")]

        for token in ["--control-bg:", "--control-hover:", "--surface-muted:"]:
            self.assertGreaterEqual(transparency.count(token), 2)
        for selector in [".stage-status,", ".stage-flow-meta,", ".minimap-actions,", ".asset-tabs,", ".logs-page-list"]:
            self.assertIn(selector, transparency)
        self.assertIn("backdrop-filter: none !important", transparency)

        contrast = final_css[final_css.index("@media (prefers-contrast: more)"):]
        for token in ["--sidebar-bg:", "--topbar-bg:", "--glass-surface:", "--glass-surface-strong:", "--control-bg:"]:
            self.assertGreaterEqual(contrast.count(token), 2)

    def test_narrow_default_nodes_fit_without_changing_explicit_coordinates(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function fitNewNodeInCanvas(node)", js)
        fit_node = js[js.index("function fitNewNodeInCanvas(node)"):js.index("function addNode(type, patch = {})")]
        add_node = js[js.index("function addNode(type, patch = {})"):js.index("function renderAll() {")]

        self.assertIn("els.canvasArea.getBoundingClientRect()", fit_node)
        self.assertIn(".canvas-create-dock", fit_node)
        self.assertIn("state.viewport.scale", fit_node)
        self.assertIn("applyViewport()", fit_node)
        self.assertIn("if (targetScale < currentScale - 0.001)", fit_node)
        self.assertNotIn("if (targetScale >= currentScale - 0.001) return", fit_node)
        self.assertIn("const hasExplicitPosition", add_node)
        self.assertIn("if (!hasExplicitPosition) fitNewNodeInCanvas(node)", add_node)

    def test_default_created_nodes_recenter_at_all_viewport_widths(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        fit_node = js[js.index("function fitNewNodeInCanvas(node)"):js.index("function addNode(type, patch = {})")]

        self.assertNotIn("rect.width >= 700", fit_node)
        self.assertIn("state.viewport.x = rect.width / 2", fit_node)
        self.assertIn("state.viewport.y = visibleCenterY", fit_node)

    def test_node_scroll_surfaces_take_wheel_before_canvas_zoom(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function shouldPreserveNodeWheel(target)", js)
        helper = js[js.index("function shouldPreserveNodeWheel(target)"):js.index("function handleWheel(event)")]
        handle_wheel = js[js.index("function handleWheel(event)"):js.index("function showCreateCanvasModal")]

        for selector in [".node-console", ".node-stage-copy", "textarea", "select", "video"]:
            self.assertIn(selector, helper)
        self.assertIn("if (shouldPreserveNodeWheel(event.target)) return", handle_wheel)
        self.assertLess(
            handle_wheel.index("if (shouldPreserveNodeWheel(event.target)) return"),
            handle_wheel.index("event.preventDefault()"),
        )

    def test_focused_node_controls_activate_their_run_target(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        render_node = js[js.index("function renderRegularNode(node)"):js.index("function nodeBodyHtml(node)")]

        self.assertIn("element.addEventListener('focusin'", render_node)
        focus_handler = render_node[render_node.index("element.addEventListener('focusin'"):]
        self.assertIn("selectedIds.size !== 1", focus_handler)
        self.assertIn("selectOnly(node.id)", focus_handler)

    def test_save_completion_preserves_newer_edits(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("let dirtyVersion = 0", js)
        set_dirty = js[js.index("function setDirty(value = true)"):js.index("function defaultSize(type)")]
        save = js[js.index("async function saveCanvas(options = {})"):js.index("async function saveCurrentCanvasIfDirty()")]

        self.assertIn("if (value) dirtyVersion += 1", set_dirty)
        self.assertIn("const versionAtStart = dirtyVersion", save)
        self.assertIn("if (dirtyVersion === versionAtStart) setDirty(false)", save)
        self.assertLess(save.index("const versionAtStart = dirtyVersion"), save.index("await api("))
        self.assertGreater(save.index("if (dirtyVersion === versionAtStart) setDirty(false)"), save.index("await api("))

    def test_manual_and_automatic_saves_share_one_inflight_request(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        save = js[js.index("async function saveCanvas(options = {})"):js.index("async function saveCurrentCanvasIfDirty()")]
        autosave = js[js.index("async function saveCurrentCanvasIfDirty()"):js.index("function upstreamNodes")]

        self.assertIn("const requestedCanvasId = currentCanvas.id", save)
        self.assertIn("if (savingInFlight)", save)
        self.assertIn("await savingInFlight", save)
        self.assertIn("const savePromise =", save)
        self.assertIn("savingInFlight = savePromise", save)
        self.assertIn("savingInFlight = null", save)
        self.assertIn("while (dirty && currentCanvas?.id === requestedCanvasId)", save)
        self.assertIn("while (dirty && currentCanvas)", autosave)
        self.assertIn("await saveCanvas({ silent: true })", autosave)
        self.assertNotIn("savingInFlight = saveCanvas", autosave)

    def test_run_node_and_chain_reject_duplicate_or_unstarted_work(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn("const nodeRunsInFlight = new Set()", js)
        self.assertIn("let chainRunInFlight = false", js)
        run_node = js[js.index("async function runNode(node)"):js.index("function runLocalNode(node)")]
        run_chain = js[js.index("async function runChain()"):js.index("function collectRunOrder")]
        wait_done = js[js.index("async function waitForNodeDone(nodeId)"):js.index("function taskTargetFor")]

        self.assertIn("nodeRunsInFlight.has(node.id)", run_node)
        self.assertIn("['queued', 'running'].includes(node.status)", run_node)
        self.assertIn("nodeRunsInFlight.add(node.id)", run_node)
        self.assertIn("nodeRunsInFlight.delete(node.id)", run_node)
        self.assertIn("return false", run_node)
        self.assertIn("return true", run_node)
        self.assertLess(run_node.index("nodeRunsInFlight.add(node.id)"), run_node.index("await api('/api/tasks'"))
        self.assertGreater(run_node.index("nodeRunsInFlight.delete(node.id)"), run_node.index("await api('/api/tasks'"))

        self.assertIn("if (chainRunInFlight)", run_chain)
        self.assertIn("const started = await runNode(node)", run_chain)
        self.assertIn("if (!started)", run_chain)
        self.assertIn("const status = await waitForNodeDone(node.id)", run_chain)
        self.assertIn("status !== 'succeeded'", run_chain)
        self.assertIn("return 'timeout'", wait_done)

    def test_task_poll_timeouts_mark_nodes_failed_for_retry(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        director_poll = js[js.index("async function pollDirectorTask(taskId, nodeId)"):js.index("function directorItemPrompt")]
        task_poll = js[js.index("async function pollTask(taskId, nodeId)"):js.index("async function runChain()")]

        self.assertIn("markTaskPollingFailed(nodeId, taskId", director_poll)
        self.assertIn("导演台查询超时", director_poll)
        self.assertIn("markTaskPollingFailed(nodeId, taskId", task_poll)
        self.assertIn("任务查询超时", task_poll)

    def test_keyboard_shortcuts_preserve_buttons_and_release_canvas_gestures_on_blur(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        keydown = js[js.index("window.addEventListener('keydown'"):js.index("window.addEventListener('keyup'")]
        bindings = js[js.index("function bindEvents()"):js.index("async function init()")]

        self.assertIn("button,a[href],[contenteditable=\"true\"]", keydown)
        self.assertLess(keydown.index("event.key.toLowerCase() === 's'"), keydown.index("if (editing) return"))
        self.assertIn("window.addEventListener('blur'", bindings)
        blur_handler = bindings[bindings.index("window.addEventListener('blur'"):]
        self.assertIn("spaceDown = false", blur_handler)
        self.assertIn("endPointerAction({ type: 'pointercancel' })", blur_handler)

    def test_narrow_dock_keeps_all_six_actions_reachable(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]
        dock = html[html.index('class="canvas-create-dock"'):html.index('id="addMenu"')]
        narrow = final_css[final_css.index("@media (max-width: 760px)"):final_css.index("@media (prefers-reduced-motion: reduce)")]

        self.assertEqual(len(re.findall(r"data-dock-(?:add|action)=", dock)), 6)
        self.assertRegex(narrow, r"\.canvas-create-dock\s*\{[^}]*grid-template-columns:\s*repeat\(3,")
        self.assertRegex(narrow, r"\.canvas-create-dock\s+button\s*\{[^}]*min-height:\s*56px")

    def test_collapsed_sidebar_actions_keep_accessible_names(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        for element_id in ["assetBtn", "logBtn", "themeToggleBtn", "accountBtn"]:
            self.assertRegex(html, rf'<button[^>]*id="{element_id}"[^>]*aria-label="[^"]+"')
        apply_theme = js[js.index("function applyTheme(theme, options = {})"):js.index("function toggleTheme()")]
        self.assertIn("themeToggleBtn.setAttribute('aria-label'", apply_theme)

    def test_tablet_asset_preview_actions_remain_reachable(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]
        tablet = final_css[final_css.index("@media (max-width: 1200px)"):final_css.index("@media (max-width: 1100px)")]

        preview = re.search(r"\.asset-preview\s*\{(?P<body>[^}]*)\}", tablet, re.S)
        self.assertIsNotNone(preview)
        self.assertIn("display: block", preview.group("body"))
        self.assertIn("grid-column: 1 / -1", preview.group("body"))
        self.assertNotIn("display: none", preview.group("body"))

    def test_unconfigured_generation_tools_remain_actionable_with_status_hint(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="capabilitySetupHint"', html)
        self.assertIn("aria-describedby", js)
        self.assertRegex(
            css,
            r'\[data-capability-configured="false"\][^{]*\{[^}]*opacity:\s*1;[^}]*filter:\s*none;',
        )
        self.assertRegex(css, r'\[data-capability-configured="false"\]::after[^{]*\{[^}]*background:\s*#ff9f0a;')

    def test_cross_project_targets_switch_project_before_canvas(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        target_for = js[js.index("function taskTargetFor(task)"):js.index("async function resolveTaskTarget(task)")]
        resolve = js[js.index("async function resolveTaskTarget(task)"):js.index("function inspectTask(task)")]
        focus = js[js.index("async function focusTask(task)"):js.index("async function loadTasks()")]
        preview = js[js.index("function renderAssetPreview(asset)"):js.index("function selectAsset(assetId)")]
        focus_asset = js[js.index("function focusAsset(asset)"):js.index("function renderAssetDrawer()")]

        self.assertIn("projectId: task.project_id || ''", target_for)
        for field in ["project_id", "canvas_id", "node_id"]:
            self.assertIn(field, resolve)
        self.assertIn("if (target.projectId", focus)
        self.assertIn("await selectProject(target.projectId)", focus)
        self.assertLess(focus.index("await selectProject(target.projectId)"), focus.index("await selectCanvas(target.canvasId)"))
        self.assertIn("project_id: asset.project_id || ''", preview)
        self.assertIn("project_id: asset.project_id || ''", focus_asset)

if __name__ == "__main__":
    unittest.main()
