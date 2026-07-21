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

    def test_dark_canvas_spotlight_is_cool_subtle_and_normally_blended(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        marker = "/* Calmer dark canvas spotlight, approved 2026-07-15. */"

        self.assertIn(marker, css)
        spotlight_css = css.split(marker, 1)[1]
        self.assertRegex(
            spotlight_css,
            r'\[data-theme="dark"\] \.canvas-area::before\s*\{[^}]*radial-gradient\(\s*circle 160px[^}]*rgba\(78,\s*140,\s*196,\s*0\.065\)[^}]*mix-blend-mode:\s*normal;',
        )
        self.assertRegex(
            spotlight_css,
            r'\[data-theme="dark"\] \.canvas-area\.pointer-lit::before\s*\{[^}]*opacity:\s*0\.62;',
        )
        self.assertNotIn("rgba(242, 201, 76", spotlight_css)
        self.assertNotIn("rgba(78, 122, 86", spotlight_css)

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

    def test_keyboard_canvas_controls_have_visible_operable_paths(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        group_template = js[js.index("function renderGroupNode"):js.index("function renderRegularNode")]
        regular_node_template = js[js.index("function renderRegularNode"):js.index("function nodeBodyHtml")]

        self.assertIn('<button class="node-port input" type="button"', regular_node_template)
        self.assertIn('<button class="node-port output" type="button"', regular_node_template)
        self.assertIn('aria-label="输入端口"', regular_node_template)
        self.assertIn('aria-label="输出端口"', regular_node_template)
        self.assertIn('<button class="group-resize" type="button"', group_template)
        self.assertIn('aria-label="调整分组大小"', group_template)
        self.assertIn("function handlePortKeydown", js)
        self.assertIn("function resizeNodeFromKeyboard", js)

        port_keyboard_start = js.index("function handlePortKeydown")
        port_keyboard = js[port_keyboard_start:js.index("\n  function ", port_keyboard_start)]
        resize_keyboard_start = js.index("function resizeNodeFromKeyboard")
        resize_keyboard = js[resize_keyboard_start:js.index("\n  function ", resize_keyboard_start)]
        self.assertIn("event.key === 'Escape'", port_keyboard)
        self.assertIn("event.key === 'Enter' || event.key === ' '", port_keyboard)
        self.assertIn("pendingEdgeConnection = { source: node.id }", port_keyboard)
        self.assertIn("addEdge(pendingEdgeConnection.source, node.id)", port_keyboard)
        self.assertIn("hideAddMenu()", port_keyboard)
        self.assertIn("event.preventDefault()", port_keyboard)
        self.assertIn("event.stopPropagation()", port_keyboard)
        self.assertIn("const step = event.shiftKey ? 32 : 8", resize_keyboard)
        self.assertIn("const min = isGroup ? { w: 180, h: 120 } : minSize(node.type)", resize_keyboard)
        self.assertIn("if (event.key === 'ArrowRight') node.w += step", resize_keyboard)
        self.assertIn("if (event.key === 'ArrowLeft') node.w = Math.max(min.w, node.w - step)", resize_keyboard)
        self.assertIn("if (event.key === 'ArrowDown') node.h += step", resize_keyboard)
        self.assertIn("if (event.key === 'ArrowUp') node.h = Math.max(min.h, node.h - step)", resize_keyboard)
        self.assertIn("event.preventDefault()", resize_keyboard)
        self.assertIn("event.stopPropagation()", resize_keyboard)
        self.assertIn("selectOnly(node.id)", resize_keyboard)
        self.assertIn("applyNodePosition(node)", resize_keyboard)
        self.assertIn("scheduleEdges()", resize_keyboard)
        self.assertIn("scheduleMinimapRender()", resize_keyboard)
        self.assertIn("setDirty()", resize_keyboard)

        self.assertIn("element.querySelector('.group-resize').addEventListener('pointerdown', (event) => startGroupResize(event, node))", group_template)
        self.assertIn("element.querySelector('.node-resize').addEventListener('pointerdown', (event) => startNodeResize(event, node))", regular_node_template)
        self.assertIn("element.querySelector('.node-port.output').addEventListener('pointerdown', (event) => startEdgeDrag(event, node))", regular_node_template)
        self.assertIn("element.querySelector('.node-port.input').addEventListener('pointerup', (event) => finishEdgeDrag(event, node))", regular_node_template)
        self.assertIn("element.querySelector('.group-resize').addEventListener('keydown', (event) => resizeNodeFromKeyboard(event, node, true))", group_template)
        self.assertIn("element.querySelector('.node-resize').addEventListener('keydown', (event) => resizeNodeFromKeyboard(event, node))", regular_node_template)
        self.assertIn("element.querySelector('.node-port.output').addEventListener('keydown', (event) => handlePortKeydown(event, node, 'output'))", regular_node_template)
        self.assertIn("element.querySelector('.node-port.input').addEventListener('keydown', (event) => handlePortKeydown(event, node, 'input'))", regular_node_template)

        self.assertRegex(css, r"\.edge-delete-control:focus-visible[^{]*\{[^}]*opacity:\s*1")
        self.assertIn(".node-port:focus-visible", css)
        self.assertIn(".node-resize:focus-visible", css)
        self.assertIn(".group-resize:focus-visible", css)

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
        self.assertIn("function nodeRunButtonHtml", js)
        self.assertIn("node-console", js)
        self.assertIn("node-toolbar-row", js)
        self.assertIn("node-workbench-footer", js)
        self.assertIn("node-workbench-run", js)
        self.assertIn("data-tool-action", js)

        self.assertIn(".node-stage", css)
        self.assertIn(".node-console", css)
        self.assertIn(".node-toolbar-row", css)
        self.assertIn(".node-workbench-footer", css)
        self.assertIn(".node-workbench-run", css)

    def test_llm_node_hides_system_prompt_editor(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("if (type === 'llm') return { w: 460, h: 500 }", js)
        self.assertIn("if (type === 'llm') return { w: 360, h: 480 }", js)
        self.assertIn("function llmNodeHtml", js)
        self.assertIn("systemPrompt: '你是可靠的 AI 创作助手", js)
        self.assertNotIn("system-text", js)
        self.assertNotIn('data-field="systemPrompt"', js)
        self.assertNotIn("<span>System</span>", js)

    def test_llm_node_uses_adaptive_workbench(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        llm = js[js.index("function llmNodeHtml(node)"):js.index("function imageNodeHtml(node)")]

        for token in [
            'node-workbench llm-workbench',
            'node-workbench-main',
            'llm-settings',
            'llm-context',
            'llm-instruction',
            'llm-output',
            '<span>模型</span>',
            "modelSelectHtml('llm', node.model)",
            '<span>指令</span>',
            '<span>生成结果</span>',
            "footerHtml(node, '运行 LLM')",
        ]:
            self.assertIn(token, llm)
        self.assertNotIn("服务商", llm)
        self.assertNotIn("llmProvider", llm)

    def test_llm_result_has_one_click_copy_action(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        llm = js[js.index("function llmNodeHtml(node)"):js.index("function imageNodeHtml(node)")]
        binding = js[js.index("function bindNodeControls"):js.index("function nodeRect")]
        copy_helper = js

        self.assertIn('data-node-action="copy-result"', llm)
        self.assertIn('aria-label="复制生成结果"', llm)
        self.assertIn("node.resultText?.trim() ? '' : 'disabled'", llm)
        self.assertIn("[data-node-action=\"copy-result\"]", binding)
        self.assertIn("copyNodeResult(button, node).catch(showError)", binding)
        self.assertIn("await copyText(node.resultText)", copy_helper)
        self.assertIn("catch (clipboardError)", copy_helper)
        self.assertIn("const copied = document.execCommand('copy')", copy_helper)
        self.assertIn("if (!copied) throw new Error", copy_helper)
        self.assertIn("window.clearTimeout(button.copyResetTimer)", copy_helper)
        self.assertIn("button.copyResetTimer = window.setTimeout", copy_helper)
        self.assertIn("showToast('生成结果已复制', 'success')", copy_helper)
        self.assertIn(".llm-copy-button", css)
        self.assertIn(".llm-copy-button.copied", css)

    def test_llm_result_is_editable_and_can_be_cleared(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        phosphor_css = (ROOT / "static" / "vendor" / "phosphor" / "phosphor.css").read_text(encoding="utf-8")
        llm = js[js.index("function llmNodeHtml(node)"):js.index("function imageNodeHtml(node)")]
        binding = js[js.index("function bindNodeControls"):js.index("function nodeRect")]

        self.assertIn('data-field="resultText"', llm)
        self.assertIn('aria-label="生成结果，可编辑"', llm)
        self.assertIn('data-node-action="clear-result"', llm)
        self.assertIn('aria-label="清空生成结果"', llm)
        self.assertIn('class="ph ph-eraser"', llm)
        self.assertIn("field === 'resultText'", binding)
        self.assertIn('[data-node-action="clear-result"]', binding)
        self.assertIn("node.resultText = ''", binding)
        self.assertIn("showToast('生成结果已清空', 'success')", binding)
        self.assertIn(".llm-output-editor", css)
        self.assertIn(".llm-clear-button", css)
        self.assertIn(".ph.ph-eraser::before", phosphor_css)

    def test_node_workbench_prevents_dead_space_and_horizontal_overflow(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        marker = "/* Unified adaptive node workbench, approved 2026-07-15. */"
        self.assertIn(marker, css)
        workbench = css[css.index(marker):]

        for token in [
            ".node-workbench {",
            "grid-template-rows: minmax(0, 1fr) auto;",
            ".node-workbench-main {",
            "overflow-x: hidden;",
            ".llm-workbench .node-workbench-main {",
            ".input-preview-item > div {",
            "overflow-wrap: anywhere;",
            ".node-workbench textarea,",
            "max-width: 100%;",
        ]:
            self.assertIn(token, workbench)

    def test_dark_node_workbench_keeps_primary_action_blue(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        marker = "/* Unified adaptive node workbench, approved 2026-07-15. */"
        workbench = css[css.index(marker):]

        self.assertRegex(
            workbench,
            r'\[data-theme="dark"\] \.node-workbench-run\s*\{[^}]*'
            r'border-color:\s*var\(--system-blue\);[^}]*'
            r'background:\s*var\(--system-blue\);[^}]*color:\s*#fff;',
        )

    def test_dark_node_workbench_preserves_semantic_status_colors(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        marker = "/* Unified adaptive node workbench, approved 2026-07-15. */"
        workbench = css[css.index(marker):]

        for state, color in [
            ("running", "--warning"),
            ("queued", "--warning"),
            ("succeeded", "--success"),
            ("failed", "--danger"),
        ]:
            self.assertRegex(
                workbench,
                rf'\[data-theme="dark"\] \.node-workbench-status\.{state}\s*'
                rf'\{{[^}}]*color:\s*var\({color}\);',
            )

    def test_workbench_minimum_heights_fit_internal_tracks(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        for token in [
            "if (type === 'prompt') return { w: 340, h: 360 }",
            "if (type === 'loop') return { w: 340, h: 360 }",
            "if (type === 'llm') return { w: 360, h: 480 }",
            "if (type === 'video') return { w: 360, h: 460 }",
            "if (type === 'output') return { w: 320, h: 360 }",
        ]:
            self.assertIn(token, js)

    def test_creative_nodes_share_the_adaptive_workbench(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        render = js[js.index("function renderRegularNode(node)"):js.index("function nodeBodyHtml(node)")]
        self.assertNotIn("node-tool-run", render)
        self.assertIn("aria-busy", render)

        names = ["prompt", "loop", "llm", "image", "video", "output"]
        starts = [js.index(f"function {name}NodeHtml(node)") for name in names]
        ends = starts[1:] + [js.index("function directorCounts")]
        for name, start, end in zip(names, starts, ends):
            block = js[start:end]
            self.assertIn("node-workbench", block, name)
            self.assertIn("node-workbench-main", block, name)
            self.assertEqual(block.count("footerHtml(node"), 1, name)

        director = js[js.index("function directorNodeHtml(node)"):js.index("function toolActionText")]
        self.assertIn("node-workbench director-workbench", director)
        self.assertIn("nodeStatusHtml(node", director)

    def test_adaptive_workbench_preserves_generation_controls(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        image = js[js.index("function imageNodeHtml(node)"):js.index("function videoNodeHtml(node)")]
        video = js[js.index("function videoNodeHtml(node)"):js.index("function outputNodeHtml(node)")]

        for token in [
            "toolButtonHtml('uploadReference', '上传')",
            "toolButtonHtml('addReference', '参考')",
            "modelSelectHtml('image', node.model)",
            'data-field="ratio"',
            'data-field="imageSize"',
            'data-field="count"',
            "'imageScale'",
        ]:
            self.assertIn(token, image)

        for token in [
            "'videoMode'",
            "toolButtonHtml('markShot', '添加镜头说明')",
            "toolButtonHtml('effectPrompt', '添加特效描述')",
            "toolButtonHtml('characterRef', '添加角色约束')",
            "toolButtonHtml('addReference', '添加参考约束')",
            "modelSelectHtml('video', node.model)",
            'data-field="aspectRatio"',
            'data-field="resolution"',
            'data-field="duration"',
            "'outputFps'",
        ]:
            self.assertIn(token, video)

        for block in (image, video):
            self.assertNotIn("服务商", block)
            self.assertNotIn('data-field="apiProvider"', block)

    def test_node_status_is_localized_and_announced(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        status = js[js.index("function nodeStatusText(node, fallback)"):js.index("function stageKindLabel")]
        self.assertIn("function nodeStatusHtml(node", js)
        self.assertIn("function nodeRunButtonHtml", js)
        status_html = js[js.index("function nodeStatusHtml(node"):js.index("function nodeRunButtonHtml")]
        run_html = js[js.index("function nodeRunButtonHtml"):js.index("function toolButtonHtml")]
        footer = js[js.index("function footerHtml(node"):js.index("function promptNodeHtml")]

        for token in ["运行中", "失败", "完成"]:
            self.assertIn(token, status)
        self.assertIn("nodeStatusText(node, '待运行')", status_html)
        self.assertIn('role="status"', status_html)
        self.assertIn('aria-live="polite"', status_html)
        self.assertIn('aria-label="${escapeHtml(label)}"', run_html)
        self.assertIn("node.demo && node.status === 'succeeded'", run_html)
        self.assertNotIn("node.status || 'idle'", footer)

    def test_presentation_demo_is_disabled_for_real_generation(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        normalize = js[js.index("function normalizeNode(raw)"):js.index("function normalizeState(raw)")]
        reconcile = js[js.index("async function reconcileTasksToNodes"):js.index("function isLocalRunnable")]
        run_node = js[js.index("async function runNode(node)"):js.index("function runLocalNode(node)")]

        self.assertIn("const PRESENTATION_DEMO_MODE = false;", js)
        self.assertIn("const isDemoGeneration = PRESENTATION_DEMO_MODE && ['image', 'video'].includes(type);", normalize)
        self.assertIn("node.demo = false;", normalize)
        self.assertNotIn("isUploadedMedia", normalize)
        self.assertIn("PRESENTATION_DEMO_MODE && node.demo && ['image', 'video'].includes(node.type)", reconcile)
        self.assertIn("PRESENTATION_DEMO_MODE && node.demo && ['image', 'video'].includes(node.type)", run_node)

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
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn(".node-image .node-stage-image", css)
        image_stage = css[
            css.index(".node-image .node-stage-image {") :
            css.index(".node-image .node-media-preview")
        ]
        self.assertIn("aspect-ratio: auto", image_stage)
        self.assertNotIn("aspect-ratio: 4 / 3", image_stage)
        self.assertIn("flex: 0 0 auto", css)
        self.assertIn("width: 100%", css)
        self.assertIn("max-width: none", css)
        self.assertIn("max-height: none", css)
        self.assertIn("justify-self: stretch", css)
        self.assertIn("object-position: center", css)
        self.assertNotIn("width: min(100%, 560px)", css)
        preview_image = css[
            css.index(".node-stage .node-media-preview .node-media") :
            css.index(".node-image .node-stage-image")
        ]
        self.assertIn("width: 100%", preview_image)
        self.assertIn("height: 100%", preview_image)
        self.assertIn("min-width: 0", preview_image)
        self.assertIn("min-height: 0", preview_image)
        image_stage_content = css[
            css.index(".node-image .node-stage-content {") :
            css.index(".node-image .node-console")
        ]
        self.assertIn("position: absolute", image_stage_content)
        self.assertIn("inset: 0", image_stage_content)
        self.assertIn("overflow: hidden", image_stage_content)
        self.assertIn("function nodeMediaAspectRatio(node)", js)
        self.assertIn("--media-aspect:${nodeMediaAspectRatio(node)}", js)
        self.assertIn(".node-image .node-media-shell.image", css)
        image_shell = css[
            css.index(".node-image .node-media-shell.image") :
            css.index(".node-media-shell .node-media-preview")
        ]
        self.assertIn("width: auto", image_shell)
        self.assertIn("max-width: 100%", image_shell)
        self.assertIn("height: 100%", image_shell)
        self.assertIn("max-height: 100%", image_shell)
        self.assertIn("aspect-ratio: var(--media-aspect", image_shell)
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

    def test_generated_images_open_the_editor_on_double_click(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="mediaPreviewModal"', html)
        self.assertIn('id="mediaPreviewImage"', html)
        self.assertIn('id="mediaEditorCanvas"', html)
        self.assertIn('data-editor-ratio="original"', html)
        self.assertIn("mediaPreviewModal: document.getElementById('mediaPreviewModal')", js)
        self.assertIn("data-preview-media", js)
        self.assertIn("data-preview-node-id", js)
        self.assertIn("els.nodeLayer.addEventListener('dblclick'", js)
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

    def test_generated_media_download_is_icon_only(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        icon_css = (ROOT / "static" / "vendor" / "phosphor" / "phosphor.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        media = js[js.index("function mediaDownloadButtonHtml"):js.index("function renderNodes()")]

        self.assertIn("node-media-shell", media)
        self.assertIn("data-download-media", media)
        self.assertIn("ph-download-simple", media)
        self.assertIn("function mediaDownloadUrl", js)
        self.assertIn("function downloadMedia", js)
        self.assertIn("download=1", js)
        controls = js[js.index("function bindNodeControls"):js.index("function nodeRect")]
        self.assertIn("data-download-media", controls)
        self.assertIn(".ph.ph-download-simple:before", icon_css)

        blocks = re.findall(r"^\.node-media-download\s*\{([^}]*)\}", css, re.M | re.S)
        self.assertTrue(blocks)
        for declaration in [
            "border: 0;",
            "background: transparent;",
            "box-shadow: none;",
            "backdrop-filter: none;",
            "color: #fff;",
        ]:
            self.assertIn(declaration, blocks[-1])
        self.assertIn(".node-media-shell.video .node-media-download", css)

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
        self.assertNotIn("previewUrl: event.currentTarget.dataset.previewMedia || ''", js)
        self.assertNotIn("suppressNextMediaPreviewClick", js)
        self.assertNotIn("if (!finished.moved) openMediaPreview(finished.previewUrl)", js)
        self.assertIn("data-edit-media", js)
        self.assertIn("data-edit-node-id", js)
        self.assertIn("-webkit-user-drag: none", css)
        self.assertIn("cursor: grab", css)
        self.assertIn("cursor: grabbing", css)

    def test_image_editor_supports_brush_history_and_non_destructive_save(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        for tool in ["move", "brush", "eraser"]:
            self.assertIn(f'data-editor-tool="{tool}"', html)
        for control in [
            'id="mediaEditorBrushColor"',
            'id="mediaEditorBrushSize"',
            'id="mediaEditorUndoBtn"',
            'id="mediaEditorRedoBtn"',
            'id="mediaEditorDiscardDialog"',
        ]:
            self.assertIn(control, html)
        self.assertIn("function drawMediaEditorScene", js)
        self.assertIn("globalCompositeOperation = stroke.erase ? 'destination-out' : 'source-over'", js)
        self.assertIn("function commitMediaEditorHistory", js)
        self.assertIn("history.length > 30", js)
        self.assertIn("mediaEditor.history.splice(1, mediaEditor.history.length - 30)", js)
        self.assertIn("mediaEditor.saving || !mediaEditorHasChanges()", js)
        self.assertIn("button.setAttribute('aria-pressed', String(active))", js)
        self.assertIn("id=\"mediaEditorStageHint\"", html)
        self.assertIn("brush: '在图片上拖动绘制'", js)
        self.assertIn("await uploadEditedImage(blob, node)", js)
        self.assertIn("node.resultOverride = true", js)
        self.assertIn("if (node.resultOverride && task.status === 'succeeded') return", js)
        self.assertIn("delete node.resultOverride", js)
        self.assertIn(".media-preview-card.media-editor-card", css)
        self.assertIn("#mediaEditorCanvas[data-tool=\"brush\"]", css)
        self.assertNotIn("var(--blue)", css)
        self.assertRegex(
            css,
            r"\.media-editor-discard-actions\s+\.danger-button\s*\{[^}]*background:\s*#d70015;[^}]*color:\s*#fff;",
        )
        self.assertRegex(
            css,
            r"\.media-editor-discard-actions\s+\.danger-button:hover,[\s\S]*?\.media-editor-discard-actions\s+\.danger-button:focus-visible\s*\{[^}]*background:\s*#b80016;[^}]*color:\s*#fff;",
        )

        icon_css = (ROOT / "static" / "vendor" / "phosphor" / "phosphor.css").read_text(encoding="utf-8")
        for icon in ["arrow-counter-clockwise", "arrow-clockwise", "hand", "paint-brush", "eraser", "check"]:
            self.assertIn(f".ph.ph-{icon}::before", icon_css)

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
        self.assertIn("generationCapabilities?.[kind]?.models", js)
        node_capability = js[js.index("function nodeCapability(node)"):js.index("function chipHtml")]
        self.assertNotIn("providers", node_capability)

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

    def test_video_prompt_excludes_connected_media_nodes_and_stock_guidance(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        task_prompt = js[
            js.index("function taskPrompt(node)") :
            js.index("function taskOptions(node)")
        ]

        self.assertRegex(
            js,
            r"function upstreamTextContext\(node\)[\s\S]*?filter\(\(item\) => !nodeMediaUrl\(item\)\)",
        )
        self.assertIn(
            "node.type === 'video' ? upstreamTextContext(node) : upstreamContext(node)",
            task_prompt,
        )
        self.assertIn("const own = authoredNodePrompt(node)", task_prompt)

    def test_video_modes_follow_upstream_image_availability(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn("function upstreamImageReferences(node)", js)
        self.assertIn("function upstreamImageAssetIds(node)", js)
        references = js[
            js.index("function upstreamImageReferences(node)") :
            js.index("function taskPrompt(node)")
        ]
        video = js[
            js.index("function videoNodeHtml(node)") :
            js.index("function outputNodeHtml(node)")
        ]
        options = js[
            js.index("function taskOptions(node)") :
            js.index("function directorSystemPrompt()")
        ]
        delete_edge = js[
            js.index("function deleteEdge(edgeId)") :
            js.index("function portPoint(node, side)")
        ]

        self.assertIn("upstreamNodes(node.id)", references)
        self.assertIn("nodeMediaUrl(item)", references)
        self.assertIn("mediaKindForUrl(url, item.resultKind) === 'image'", references)
        self.assertIn("const referenceKey = assetId || url", references)
        self.assertIn("!url || !isImage", references)
        self.assertIn(".filter(Boolean)", references)
        self.assertIn("const referenceImages = upstreamImageReferences(node)", video)
        self.assertIn("disabled: !references.capability.imageToVideo || !hasReferenceImage", video)
        self.assertIn("disabled: true", video)
        self.assertIn("disabled: !references.capability.firstLastFrame || !hasFramePair", video)
        self.assertIn("reference_asset_ids: referenceAssetIds", options)
        self.assertIn("const imageToVideo = references.imageToVideo", options)
        self.assertIn("first_last_frame: firstLastFrame", options)
        self.assertIn("renderAll()", delete_edge)

    def test_video_first_last_frame_slots_are_explicit(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        video = js[
            js.index("function videoFrameSlotsHtml") :
            js.index("function outputNodeHtml(node)")
        ]

        self.assertIn("首帧", video)
        self.assertIn("尾帧", video)
        self.assertIn("画面参考", video)
        self.assertIn("强参考", video)
        self.assertIn("等待连接图片", video)
        self.assertIn("待连接第二张图片", video)
        self.assertIn("title: '暂未支持'", video)
        self.assertIn("videoFrameSlotsHtml(node, references)", video)
        self.assertIn(".video-frame-slots", css)
        self.assertIn(".video-frame-slot", css)
        self.assertIn(".video-frame-slot img", css)
        frame_slot = css[css.rindex(".video-frame-slot {") : css.rindex(".video-frame-slot > span")]
        frame_image = css[css.rindex(".video-frame-slot img") : css.rindex(".video-frame-empty")]
        self.assertIn("height: 112px", frame_slot)
        self.assertIn("object-fit: contain", frame_image)
        self.assertIn("object-position: center", frame_image)
        self.assertIn("min-width: 0", frame_image)
        self.assertIn("min-height: 0", frame_image)
        self.assertIn("max-width: 100%", frame_image)
        self.assertIn("max-height: 100%", frame_image)

    def test_video_strong_reference_is_capability_gated_and_submitted_as_real_assets(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        capability = js[
            js.index("function videoModelCapabilities(nodeOrModel)") :
            js.index("function strongReferenceRole(type)")
        ]
        video = js[
            js.index("function imageAssetReference(asset)") :
            js.index("function outputNodeHtml(node)")
        ]
        controls = js[
            js.index("function insertTokenAtPrompt(textarea, token)") :
            js.index("function nodeRect(node)")
        ]
        options = js[
            js.index("function taskOptions(node)") :
            js.index("function directorSystemPrompt()")
        ]

        self.assertIn("video.model_capabilities?.[model]", capability)
        for field in ["image_to_video", "strong_reference", "first_last_frame", "max_images"]:
            self.assertIn(field, capability)
        self.assertNotIn("cdance", capability.lower())

        for token in [
            "firstFrameAssetId",
            "strongReferenceAssetId",
            "lastFrameAssetId",
            "strongReferenceEnabled",
            "strongReferenceAlias",
            "@\u4e3b\u4f531",
            "@\u573a\u666f1",
            "@\u9053\u51771",
            "@\u98ce\u683c1",
        ]:
            self.assertIn(token, js)

        self.assertIn("data-strong-reference-action=\"toggle\"", video)
        self.assertIn("data-strong-reference-action=\"choose\"", video)
        self.assertIn("data-strong-reference-type", video)
        self.assertIn("data-strong-reference-token", video)
        self.assertIn("secondReference && !references.strongReferenceEnabled", video)
        self.assertIn("'强参考（待启用）'", video)
        self.assertIn("references.strongReferenceEnabled ? '\u753b\u9762\u53c2\u8003' : '\u9996\u5e27'", video)
        self.assertIn("node.firstLastFrame = false", video)
        self.assertIn("node.strongReferenceEnabled = true", video)

        self.assertIn("textarea.setRangeText", controls)
        self.assertIn("textarea.selectionStart", controls)
        self.assertIn("textarea.dispatchEvent(new Event('input'", controls)
        self.assertNotIn("contenteditable", controls.lower())
        self.assertIn("assetDrawerSelection = { kind: 'strong_reference', nodeId: node.id }", controls)

        for field in [
            "first_frame_asset_id: firstFrameAssetId",
            "strong_reference_asset_id: strongReferenceAssetId",
            "last_frame_asset_id: lastFrameAssetId",
            "strong_reference_alias: strongReferenceAlias",
            "reference_asset_ids: referenceAssetIds",
        ]:
            self.assertIn(field, options)
        self.assertIn("function videoReferenceValidationMessage(node)", options)
        self.assertIn("if (referenceError)", js)

        for selector in [
            ".strong-reference-panel",
            ".strong-reference-switch",
            ".strong-reference-role",
            ".strong-reference-token",
            ".drawer-selection-hint",
            ".asset-drawer.selection-mode",
        ]:
            self.assertIn(selector, css)
        self.assertIn("@media (prefers-reduced-motion: reduce)", css)

    def test_model_picker_uses_backend_configured_models_only(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        task_options = js[js.index("function taskOptions(node)"):js.index("function directorSystemPrompt()")]
        director = js[js.index("function directorNodeHtml(node)"):js.index("function toolActionText")]

        self.assertIn("function configuredModels(kind)", js)
        self.assertIn("generationCapabilities?.[kind]?.models", js)
        self.assertIn("function effectiveModel(kind, current)", js)
        self.assertIn("function modelSelectHtml(kind, current)", js)
        self.assertIn("后台暂未配置模型", js)
        self.assertIn("model: effectiveModel('video', node.model)", task_options)
        self.assertIn("modelSelectHtml('llm', node.model)", director)
        self.assertNotIn("服务商", director)
        self.assertNotIn("llmProvider", director)
        self.assertNotIn("provider:", task_options)
        self.assertNotIn("videoModelOptions", js)
        self.assertNotIn("configuredProviderModel", js)

    def test_video_run_rejects_an_empty_prompt_before_creating_a_task(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        run_node = js[
            js.index("async function runNode(node)") :
            js.index("function runLocalNode(node)")
        ]

        self.assertIn("node.type === 'video' && !taskPrompt(node).trim()", run_node)
        self.assertIn("请填写视频提示词，或连接有文本结果的节点。", run_node)

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

    def test_workspace_menus_explain_hierarchy_and_expose_safe_delete_actions(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        self.assertIn("项目空间", html)
        self.assertIn("当前画布", html)
        self.assertIn("项目用于组织多个画布", html)
        self.assertIn("画布是项目内的节点工作区", html)
        self.assertIn("projectListHint", js)
        self.assertIn("canvasListHint", js)
        self.assertIn("个画布", js)

        self.assertIn("data-project-delete", js)
        self.assertIn("data-canvas-delete", js)
        self.assertIn('class="nav-delete-icon"', js)
        self.assertNotIn('class="ph ph-trash"', js)
        self.assertIn("async function deleteProject", js)
        self.assertIn("async function deleteCanvas", js)
        self.assertIn("async function waitForCanvasSaveToSettle", js)
        self.assertIn("while (currentCanvas?.id === canvasId && savingInFlight)", js)
        self.assertIn("const deleteRequestsInFlight = new Set()", js)
        self.assertIn("deleteButton.disabled = deleteRequestsInFlight.has", js)
        self.assertIn("els.newCanvasBtn.disabled = !currentProject || deleteRequestsInFlight.has", js)
        self.assertIn("const projectDeleting = currentProject && deleteRequestsInFlight.has", js)
        self.assertIn("button.setAttribute('aria-current', 'true')", js)
        self.assertIn("state = blankState()", js)
        self.assertIn("window.confirm", js)
        self.assertIn("/api/projects/${project.id}", js)
        self.assertIn("/api/canvases/${canvas.id}", js)
        project_delete = js[js.index("async function deleteProject"):js.index("async function deleteCanvas")]
        canvas_delete = js[js.index("async function deleteCanvas"):js.index("function renderProjects")]
        select_project = js[js.index("async function selectProject"):js.index("async function selectCanvas")]
        create_canvas = js[js.index("async function createCanvasWithName"):js.index("function bindEvents")]
        self.assertIn("await waitForCanvasSaveToSettle(currentCanvas.id)", project_delete)
        self.assertIn("await waitForCanvasSaveToSettle(canvas.id)", canvas_delete)
        self.assertIn("currentProject.canvas_count = canvases.length", select_project)
        self.assertIn("currentProject.canvas_count = canvases.length", canvas_delete)
        self.assertIn("currentProject.canvas_count = 1", canvas_delete)
        self.assertIn("currentProject.canvas_count = canvases.length", create_canvas)

        self.assertIn(".nav-item-row", css)
        self.assertIn(".nav-list-caption", css)
        self.assertIn(".nav-item-delete", css)
        self.assertIn(".nav-item-delete:hover", css)
        self.assertIn("[data-theme=\"dark\"] .nav-item-delete", css)
        self.assertIn("width: 44px", css)
        self.assertIn("height: 44px", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr) 44px", css)
        self.assertIn(".nav-item-delete:disabled", css)
        self.assertNotIn(".app-sidebar .workspace-menu:first-child", css)

    def test_canvas_assets_keep_persisted_identity_and_node_provenance(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        block = js[js.index("function currentAssetItems()"):js.index("function assetSourceLabel(asset)")]

        self.assertIn("const persisted = assetCache.find((asset) => asset.url === url)", block)
        self.assertIn("id: persisted?.id || node.id", block)
        self.assertIn("source: persisted?.source || 'node'", block)
        self.assertIn("node_id: persisted?.node_id || node.id", block)

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

    def test_logout_saves_before_invalidating_session(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        block = js[js.index("const logout = async () => {"):js.index("els.passwordChangeForm?.addEventListener")]

        self.assertIn("await saveCurrentCanvasIfDirty()", block)
        self.assertLess(block.index("await saveCurrentCanvasIfDirty()"), block.index("await api('/api/auth/logout'"))
        self.assertIn("els.logoutBtn?.addEventListener('click', () => logout().catch(showError))", block)
        self.assertIn("els.accountPageLogoutBtn?.addEventListener('click', () => logout().catch(showError))", block)

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

    def test_admin_usage_dashboard_has_independent_portal_controls(self):
        admin = (ROOT / "static" / "admin.html").read_text(encoding="utf-8")
        admin_js = (ROOT / "static" / "admin.js").read_text(encoding="utf-8")
        app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        auth = (ROOT / "static" / "auth.html").read_text(encoding="utf-8")

        for element_id in [
            "summaryUsers",
            "summaryConsumed",
            "summaryPending",
            "summaryBalance",
            "adminUserSearch",
            "adminUserSort",
            "adminLogout",
        ]:
            self.assertIn(f'id="{element_id}"', admin)
        for field in [
            "consumed_credits",
            "pending_credits",
            "refunded_credits",
            "llm_credits",
            "image_credits",
            "video_credits",
            "last_task_at",
        ]:
            self.assertIn(field, admin_js)
        self.assertIn("/api/admin/users", admin_js)
        self.assertIn("/api/auth/logout", admin_js)
        self.assertIn("rootHost.startsWith('canvas.')", admin_js)
        self.assertIn("data.admin_url", app_js)
        self.assertIn("const isAdminPortal", auth)
        self.assertIn("isAdminPortal ? '/admin' : '/'", auth)

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

    def test_creation_dock_floats_in_the_top_chrome_without_a_full_width_bar(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        marker = "/* Floating top creation controls, approved 2026-07-14. */"

        topbar_start = html.index('class="topbar compact-topbar"')
        topbar_end = html.index("</header>", topbar_start)
        topbar_html = html[topbar_start:topbar_end]
        self.assertEqual(html.count('class="canvas-create-dock"'), 1)
        self.assertIn('class="canvas-create-dock"', topbar_html)

        self.assertIn(marker, css)
        floating_css = css.split(marker, 1)[1]
        self.assertRegex(
            floating_css,
            r"\.app-main\s*\{[^}]*grid-template-rows:\s*minmax\(0,\s*1fr\)",
        )
        self.assertRegex(
            floating_css,
            r"\.topbar\s*\{[^}]*position:\s*absolute;[^}]*grid-template-columns:\s*minmax\(160px,\s*1fr\)\s+minmax\(384px,\s*496px\)\s+max-content;[^}]*border:\s*0;[^}]*background:\s*transparent;[^}]*box-shadow:\s*none;[^}]*pointer-events:\s*none;",
        )
        self.assertRegex(floating_css, r"\.toolbar-shell\s*\{[^}]*display:\s*flex")
        self.assertRegex(
            floating_css,
            r"\.canvas-create-dock\s*\{[^}]*position:\s*static;[^}]*width:\s*100%;[^}]*min-height:\s*58px;[^}]*grid-template-columns:\s*repeat\(6,\s*minmax\(56px,\s*1fr\)\);[^}]*transform:\s*none;",
        )
        dock_block = re.search(r"\.canvas-create-dock\s*\{(?P<body>[^}]*)\}", floating_css, re.S)
        self.assertIsNotNone(dock_block)
        self.assertNotIn("bottom:", dock_block.group("body"))

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
            "align-items: center;",
            "text-align: center;",
        ]:
            self.assertIn(declaration, brand_block.group("body"))
        self.assertRegex(final_css, r"\.sidebar-brand\s+strong\s*\{[^}]*white-space:\s*nowrap")
        self.assertRegex(final_css, r"\.brand-avatar\s*\{[^}]*inset:\s*0;[^}]*object-fit:\s*cover;")

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
            r"#runBtn\s*\{[^}]*display:\s*none;",
        )
        self.assertNotRegex(final_css, r"#runBtn,\s*\n#saveBtn\s*\{[^}]*display:\s*none;")
        self.assertRegex(
            final_css,
            r"#runChainBtn\s*\{[^}]*border-color:\s*var\(--system-blue\);[^}]*background:",
        )
        self.assertIn("els.runBtn.addEventListener('click'", (ROOT / "static" / "app.js").read_text(encoding="utf-8"))
        self.assertIn("els.saveBtn.addEventListener('click'", (ROOT / "static" / "app.js").read_text(encoding="utf-8"))
        self.assertIn("document.addEventListener('visibilitychange'", (ROOT / "static" / "app.js").read_text(encoding="utf-8"))

    def test_all_entrypoints_use_the_qa_cache_version(self):
        version = "20260721-editor-discard2"
        for page in ["index.html", "auth.html", "admin.html"]:
            with self.subTest(page=page):
                html = (ROOT / "static" / page).read_text(encoding="utf-8")
                self.assertIn(f"/static/vendor/phosphor/phosphor.css?v={version}", html)
                self.assertIn(f"/static/app.css?v={version}", html)
        index_html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f"/static/app.js?v={version}", index_html)

    def test_yunzhi_brand_name_and_ip_are_consistent_across_entrypoints(self):
        pages = {
            page: (ROOT / "static" / page).read_text(encoding="utf-8")
            for page in ["index.html", "auth.html", "admin.html"]
        }
        for page, html in pages.items():
            with self.subTest(page=page):
                self.assertIn("云芝画布", html)
                self.assertNotIn("云知画布", html)

        self.assertIn('/static/brand/yunzhi-ip.png', pages["auth.html"])
        for page in ["index.html", "auth.html", "admin.html"]:
            self.assertIn('/static/brand/yunzhi-avatar.png', pages[page])
        self.assertIn('class="empty-hint-avatar brand-avatar-shell"', pages["index.html"])
        self.assertIn("云芝陪你开始创作", pages["index.html"])

    def test_admin_provider_settings_are_scoped_masked_and_responsive(self):
        html = (ROOT / "static" / "admin.html").read_text(encoding="utf-8")
        js = (ROOT / "static" / "admin.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")

        for token in [
            'data-admin-view="providers"',
            'id="adminProviderView"',
            'data-provider-kind="llm"',
            'data-provider-kind="image"',
            'data-provider-kind="video"',
            'id="adminProviderForm"',
            'id="adminProviderKey" type="password"',
            'id="adminProviderModelsFetch"',
            'id="adminProviderModelPicker"',
            'id="adminProviderModelAdd"',
            'id="adminProviderModelSummary"',
            'id="adminProviderModelList"',
            'id="adminProviderModelSelectAll"',
            'id="adminProviderModelClear"',
            'id="adminProviderModelDefault"',
            'id="adminProviderModelsStatus"',
            'id="adminProviderStatusUrl"',
            'id="adminProviderModel" type="text" spellcheck="false" maxlength="120"',
            'id="adminProviderSaveLabel"',
        ]:
            self.assertIn(token, html)

        self.assertIn("api('/api/admin/providers')", js)
        self.assertIn("if (key) payload.api_key = key", js)
        self.assertIn("JSON.stringify({ clear_api_key: true })", js)
        self.assertIn("/models`, {", js)
        self.assertIn("checkbox.type = 'checkbox'", js)
        self.assertIn("function mergeProviderModels(models)", js)
        self.assertIn("models,\n      model: models.includes(providerDefaultModel)", js)
        self.assertIn("providerModelListEl.addEventListener('change'", js)
        self.assertIn("providerModelSelectAllEl.addEventListener('click'", js)
        self.assertIn("providerModelClearEl.addEventListener('click'", js)
        self.assertIn("providerModelDefaultEl.addEventListener('change'", js)
        self.assertIn("providerModelCandidates.forEach((model) => providerSelectedModels.add(model))", js)
        self.assertIn("已对所有用户生效", js)
        self.assertIn("拉取${providerKindMeta[selectedProviderKind]?.fetchLabel", js)
        self.assertIn("if (providerConnectionDirty)", js)
        self.assertIn("当前表单有未保存内容，请先保存配置再拉取。", js)
        self.assertIn("providerKeyEl.value = ''", js)
        self.assertNotIn('select id="adminProviderModelSelect"', html)
        self.assertNotIn('multiple', html[html.index('id="adminProviderModelPicker"'):html.index('id="adminProviderStatusUrlField"')])
        self.assertNotIn("localStorage.setItem('admin-provider", js)
        self.assertRegex(css, r"\.admin-provider-workspace\s*\{[^}]*grid-template-columns:\s*260px minmax\(0, 1fr\)")
        self.assertIn(".admin-provider-list {", css)
        self.assertIn(".admin-model-control {", css)
        self.assertIn(".admin-model-picker {", css)
        self.assertIn(".admin-model-list {", css)
        self.assertIn("max-height: 264px", css)
        self.assertIn(".admin-model-option {", css)
        self.assertIn("min-height: 44px", css)
        self.assertIn(".admin-default-model {", css)
        self.assertIn("@media (max-width: 680px)", css)

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
        self.assertIn("if (type === 'output') return { w: 400, h: 360 }", js)
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
        floating_css = final_css.split("/* Floating top creation controls, approved 2026-07-14. */", 1)[1]
        self.assertRegex(floating_css, r"\.canvas-create-dock\s*\{[^}]*transform:\s*none;")

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

        version = "20260721-editor-discard2"
        index_html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f'/static/vendor/phosphor/phosphor.css?v={version}', index_html)
        self.assertIn(f'/static/app.css?v={version}', index_html)
        self.assertIn(f'/static/app.js?v={version}', index_html)
        for name in ["auth.html", "admin.html"]:
            page = (ROOT / "static" / name).read_text(encoding="utf-8")
            self.assertIn(f'/static/vendor/phosphor/phosphor.css?v={version}', page)
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
        self.assertNotIn(".canvas-create-dock", fit_node)
        self.assertIn("const usableHeight = Math.max(180, rect.height - padding * 2)", fit_node)
        self.assertIn("const visibleCenterY = Math.max(padding, rect.height / 2)", fit_node)
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
        self.assertIn("await ensureTaskPolling(node.taskId, node.id)", wait_done)
        self.assertNotIn("return 'timeout'", wait_done)

    def test_task_polling_keeps_backend_as_the_only_terminal_source(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        task_poll = js[js.index("async function pollTask(taskId, nodeId"):js.index("async function runChain()")]
        ensure_poll = js[js.index("function ensureTaskPolling(taskId, nodeId"):js.index("async function pollTask(taskId, nodeId")]
        reconcile = js[js.index("async function reconcileTasksToNodes(tasks)"):js.index("function isLocalRunnable")]
        director_run = js[js.index("async function runDirectorNode(node)"):js.index("function directorItemPrompt")]

        self.assertNotIn("for (let i = 0; i < 160", task_poll)
        self.assertNotIn("markTaskPollingFailed", task_poll)
        self.assertNotIn("任务查询超时", task_poll)
        self.assertIn("['succeeded', 'failed'].includes(data.task.status)", task_poll)
        self.assertIn("pollAttempt", task_poll)
        self.assertIn("pollRetryDelay", task_poll)
        self.assertNotIn("node.status = 'failed'", task_poll)
        self.assertIn("MAX_TASK_POLL_FAILURES", task_poll)
        self.assertIn("isRetryableTaskPollError", task_poll)
        self.assertIn("return pauseTaskSync", task_poll)

        self.assertIn("const taskPollsInFlight = new Map()", js)
        self.assertIn("taskPollsInFlight.get(taskId)", ensure_poll)
        self.assertIn("taskPollsInFlight.set(taskId, polling)", ensure_poll)
        self.assertIn("taskPollsInFlight.delete(taskId)", ensure_poll)
        self.assertIn("canvasId = currentCanvas?.id || ''", ensure_poll)
        self.assertIn("ensureTaskPolling(task.id, node.id)", reconcile)
        self.assertNotIn("await ensureTaskPolling(task.id, node.id)", reconcile)
        self.assertNotIn("node.type !== 'director'", reconcile)
        self.assertIn("ensureTaskPolling(data.task.id, node.id)", director_run)
        self.assertNotIn("async function pollDirectorTask", js)
        self.assertNotIn("function markTaskPollingFailed", js)

    def test_task_polling_is_scoped_to_canvas_and_exact_task(self):
        js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
        task_poll = js[js.index("async function pollTask(taskId, nodeId"):js.index("async function runChain()")]
        self.assertIn("currentCanvas?.id !== canvasId", task_poll)
        self.assertIn("nodeBeforePoll.taskId !== taskId", task_poll)
        self.assertIn("node.taskId !== taskId", task_poll)
        self.assertNotIn("nodeBeforePoll.taskId &&", task_poll)
        self.assertNotIn("node.taskId &&", task_poll)

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

    def test_tablet_canvas_chrome_uses_separate_safe_areas(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        self.assertRegex(
            css,
            r"@media \(min-width: 761px\) and \(max-width: 1000px\)[\s\S]*?"
            r"\.canvas-minimap\s*\{[^}]*top:\s*18px;[^}]*bottom:\s*auto",
        )
        self.assertRegex(
            css,
            r"@media \(min-width: 761px\) and \(max-width: 1000px\)[\s\S]*?"
            r"\.minimap-actions\s*\{[^}]*bottom:\s*154px",
        )

    def test_dark_theme_preview_selection_and_danger_overrides_win_final_cascade(self):
        css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
        final_css = css.split("/* Approved bright silver glass system, 2026-07-10. */", 1)[1]
        generic_controls = re.search(
            r'\[data-theme="dark"\] \.asset-card,[\s\S]*?'
            r'\[data-theme="dark"\] \.small-button,[\s\S]*?\{[^}]*\}',
            final_css,
        )
        self.assertIsNotNone(generic_controls)

        expected_rules = {
            '[data-theme="dark"] .media-preview-card .icon-close': [
                "border-color: var(--glass-border);",
                "background: var(--glass-surface-strong);",
                "color: var(--ink);",
            ],
            '[data-theme="dark"] .asset-card.active': [
                "border-color: var(--system-blue);",
                "background: var(--accent-soft);",
            ],
            '[data-theme="dark"] .small-button.danger': [
                "color: var(--danger);",
                "border-color: color-mix(in srgb, var(--danger) 48%, var(--glass-border));",
                "background: color-mix(in srgb, var(--danger) 12%, var(--control-bg));",
            ],
        }
        ordered_overrides = {
            '[data-theme="dark"] .asset-card.active',
            '[data-theme="dark"] .small-button.danger',
        }

        for selector, declarations in expected_rules.items():
            with self.subTest(selector=selector):
                rule = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>[^}}]*)\}}", final_css)
                self.assertIsNotNone(rule, f"missing final dark override: {selector}")
                for declaration in declarations:
                    self.assertIn(declaration, rule.group("body"))
                if selector in ordered_overrides:
                    self.assertGreater(rule.start(), generic_controls.end())

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
