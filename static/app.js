(() => {
  const WORLD = { width: 200000, height: 200000 };
  const MIN_ZOOM = 0.02;
  const MAX_ZOOM = 8;

  const labels = {
    account: '账号',
    admin: '后台',
    canvas: '画布',
    canvasName: '新画布',
    defaultProject: '默认项目',
    deleteConfirm: '确定删除选中的内容吗？',
    failed: '失败',
    imagePrompt: '描述要生成的画面，可以连接提示词、角色图、场景图或参考图。',
    llmPrompt: '输入要改写、拆解或生成的内容；上游节点内容会自动带入。',
    loading: '加载中',
    noAssets: '暂无资产。上传文件和生成结果会出现在这里。',
    noCanvas: '暂无画布',
    noLogs: '暂无日志',
    noProject: '暂无项目',
    noTasks: '暂无任务',
    outputPrompt: '收集上游节点结果，用于最终输出、预览或交付说明。',
    promptText: '输入提示词、脚本片段、人物设定、分镜说明或素材说明。',
    running: '运行中',
    saved: '已保存',
    saving: '保存中',
    selectRunnable: '请选择可以运行的节点',
    unsaved: '未保存',
    user: '用户',
    videoPrompt: '描述要生成的视频镜头，可以连接图片、角色、场景或分镜节点。'
  };

  const typeNames = {
    prompt: '提示词',
    loop: '循环',
    llm: 'LLM',
    image: 'API生成',
    video: '视频生成',
    output: '输出',
    group: '分组'
  };

  const nodePresets = {
    llmProviders: ['国禾API', 'OpenAI兼容', '自定义'],
    llmModels: ['gpt-5.5', 'deepseek-v4-pro', 'claude-opus-4-8', 'gemini-3.5-flash'],
    imageProviders: ['国禾API', 'OpenAI兼容', '自定义'],
    imageModels: ['gpt-image-2', 'gemini-3.1-flash-image'],
    videoProviders: ['灵境API', '火山引擎', '自定义'],
    videoModels: ['seedance-2.0', 'seedance-2.0-1080', 'seedance-2.0-vision-1080', 'veo3.1-fast'],
    ratios: ['1:1', '2:3', '3:2', '3:4', '4:3', '4:5', '5:4', '9:16', '16:9', '21:9'],
    imageSizes: ['自适应', '1K', '2K', '4K'],
    imageScales: ['1', '2', '4'],
    resolutions: ['Auto', '720p', '1080p'],
    qualities: ['auto', 'low', 'medium', 'high']
  };
  const els = {
    accountBtn: document.getElementById('accountBtn'),
    accountEmail: document.getElementById('accountEmail'),
    accountLine: document.getElementById('accountLine'),
    accountModal: document.getElementById('accountModal'),
    addMenu: document.getElementById('addMenu'),
    adminLink: document.getElementById('adminLink'),
    assetAllCount: document.getElementById('assetAllCount'),
    assetBackBtn: document.getElementById('assetBackBtn'),
    assetBtn: document.getElementById('assetBtn'),
    assetGrid: document.getElementById('assetGrid'),
    assetImageCount: document.getElementById('assetImageCount'),
    assetList: document.getElementById('assetList'),
    assetPage: document.getElementById('assetPage'),
    assetPageRefreshBtn: document.getElementById('assetPageRefreshBtn'),
    assetPageSubtitle: document.getElementById('assetPageSubtitle'),
    assetPageTitle: document.getElementById('assetPageTitle'),
    assetPreview: document.getElementById('assetPreview'),
    assetPreviewMeta: document.getElementById('assetPreviewMeta'),
    assetSearchInput: document.getElementById('assetSearchInput'),
    assetTaskCount: document.getElementById('assetTaskCount'),
    assetTotalText: document.getElementById('assetTotalText'),
    assetVideoCount: document.getElementById('assetVideoCount'),
    backToOriginBtn: document.getElementById('backToOriginBtn'),
    canvasArea: document.getElementById('canvasArea'),
    canvasList: document.getElementById('canvasList'),
    canvasTitle: document.getElementById('canvasTitle'),
    clearLogBtn: document.getElementById('clearLogBtn'),
    closeAccount: document.getElementById('closeAccount'),
    copyWorkflowBtn: document.getElementById('copyWorkflowBtn'),
    creditText: document.getElementById('creditText'),
    edgeLayer: document.getElementById('edgeLayer'),
    emptyHint: document.getElementById('emptyHint'),
    exportWorkflowBtn: document.getElementById('exportWorkflowBtn'),
    fileInput: document.getElementById('fileInput'),
    groupBtn: document.getElementById('groupBtn'),
    logBtn: document.getElementById('logBtn'),
    logList: document.getElementById('logList'),
    logoutBtn: document.getElementById('logoutBtn'),
    minimap: document.getElementById('minimap'),
    minimapContent: document.getElementById('minimapContent'),
    minimapView: document.getElementById('minimapView'),
    minimapViewport: document.getElementById('minimapViewport'),
    minimapZoom: document.getElementById('minimapZoom'),
    modalCredits: document.getElementById('modalCredits'),
    modalRole: document.getElementById('modalRole'),
    newCanvasBtn: document.getElementById('newCanvasBtn'),
    newProjectBtn: document.getElementById('newProjectBtn'),
    nodeInspector: document.getElementById('nodeInspector'),
    nodeLayer: document.getElementById('nodeLayer'),
    projectList: document.getElementById('projectList'),
    refreshAssetBtn: document.getElementById('refreshAssetBtn'),
    runBtn: document.getElementById('runBtn'),
    runChainBtn: document.getElementById('runChainBtn'),
    saveBtn: document.getElementById('saveBtn'),
    saveState: document.getElementById('saveState'),
    selectionBox: document.getElementById('selectionBox'),
    taskList: document.getElementById('taskList'),
    toolbar: document.querySelector('.toolbar'),
    uploadBtn: document.getElementById('uploadBtn'),
    workflowBtn: document.getElementById('workflowBtn'),
    workflowSummary: document.getElementById('workflowSummary'),
    world: document.getElementById('world'),
    zoomChip: document.getElementById('zoomChip'),
    zoomInBtn: document.getElementById('zoomInBtn'),
    zoomOutBtn: document.getElementById('zoomOutBtn'),
    zoomResetBtn: document.getElementById('zoomResetBtn')
  };

  let me = null;
  let projects = [];
  let canvases = [];
  let currentProject = null;
  let currentCanvas = null;
  let state = blankState();
  let selectedIds = new Set();
  let draftEdge = null;
  let edgeRaf = 0;
  let minimapRaf = 0;
  let progressTimer = null;
  let minimapRevealTimer = null;
  let minimapLayout = null;
  let assetCache = [];
  let assetFilter = 'all';
  let selectedAssetId = '';
  let currentView = 'canvas';
  let activeEdgeCleanup = null;
  let addMenuWorldPoint = null;
  let dirty = false;
  let savingInFlight = null;
  let spaceDown = false;
  let activeDrag = null;

  function blankState() {
    return {
      nodes: [],
      edges: [],
      logs: [],
      viewport: { x: 120, y: 80, scale: 1 }
    };
  }

  function uid(prefix = 'node') {
    return `${prefix}_${Math.random().toString(16).slice(2)}${Date.now().toString(16)}`;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    }[char]));
  }

  function safeNumber(value, fallback) {
    const num = Number(value);
    return Number.isFinite(num) ? num : fallback;
  }

  function optionHtml(options, selected) {
    return options.map((item) => `<option value="${escapeHtml(item)}"${item === selected ? ' selected' : ''}>${escapeHtml(item)}</option>`).join('');
  }

  function chipHtml(value, label, active, field) {
    return `<button class="chip${active ? ' active' : ''}" type="button" data-chip-field="${escapeHtml(field)}" data-chip-value="${escapeHtml(value)}">${escapeHtml(label)}</button>`;
  }

  async function api(path, options = {}) {
    const res = await fetch(path, {
      credentials: 'same-origin',
      ...options,
      headers: options.body instanceof FormData
        ? (options.headers || {})
        : { 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    if (res.status === 401 && path !== '/api/me') {
      location.href = '/login';
      throw new Error('unauthorized');
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || data.message || labels.failed);
    return data;
  }

  function showError(error) {
    const message = error?.message || String(error || '未知错误');
    addLog({ level: 'error', title: '请求失败', detail: message });
    window.alert(message);
  }
  function setDirty(value = true) {
    dirty = !!value;
    els.saveState.textContent = value ? labels.unsaved : labels.saved;
  }

  function defaultSize(type) {
    if (type === 'group') return { w: 540, h: 340 };
    if (type === 'llm') return { w: 390, h: 410 };
    if (type === 'image') return { w: 520, h: 520 };
    if (type === 'video') return { w: 560, h: 540 };
    if (type === 'output') return { w: 380, h: 300 };
    if (type === 'loop') return { w: 340, h: 300 };
    return { w: 460, h: 380 };
  }

  function defaultPrompt(type) {
    if (type === 'llm') return labels.llmPrompt;
    if (type === 'image') return labels.imagePrompt;
    if (type === 'video') return labels.videoPrompt;
    if (type === 'output') return labels.outputPrompt;
    return labels.promptText;
  }

  function defaultsForType(type) {
    if (type === 'loop') {
      return {
        prompt: '按多组镜头或素材批量循环生成。',
        loopItems: '第 1 项：第一组变量\n第 2 项：第二组变量\n第 3 项：第三组变量'
      };
    }
    if (type === 'llm') {
      return {
        llmProvider: nodePresets.llmProviders[0],
        model: nodePresets.llmModels[0],
        systemPrompt: '你是可靠的 AI 创作助手。请结合上游内容，输出清晰、可执行、适合继续生成图片或视频的结果。',
        mode: 'node',
        outputText: ''
      };
    }
    if (type === 'image') {
      return {
        apiProvider: nodePresets.imageProviders[0],
        model: nodePresets.imageModels[0],
        ratio: '1:1',
        imageSize: '自适应',
        imageScale: '1',
        count: 1
      };
    }
    if (type === 'video') {
      return {
        apiProvider: nodePresets.videoProviders[0],
        model: nodePresets.videoModels[0],
        videoMode: 'text_to_video',
        duration: 5,
        aspectRatio: '16:9',
        resolution: 'Auto',
        outputFps: 0,
        enhancePrompt: false,
        cameraFixed: false,
        generateAudio: false,
        firstLastFrame: false
      };
    }
    if (type === 'output') {
      return {
        outputItems: []
      };
    }
    return {};
  }

  function normalizeNode(raw) {
    const source = raw && typeof raw === 'object' ? raw : {};
    const type = source.type || 'prompt';
    const size = defaultSize(type);
    const defaults = defaultsForType(type);
    const node = {
      ...defaults,
      ...source,
      id: source.id || uid(type),
      type,
      title: source.title || typeNames[type] || 'Node',
      x: safeNumber(source.x, 0),
      y: safeNumber(source.y, 0),
      w: clamp(safeNumber(source.w, size.w), 180, 1400),
      h: clamp(safeNumber(source.h, size.h), 140, 1400),
      prompt: source.prompt || defaults.prompt || defaultPrompt(type),
      status: source.status || '',
      resultText: source.resultText || source.outputText || '',
      resultUrl: source.resultUrl || source.assetUrl || '',
      resultKind: source.resultKind || '',
      taskId: source.taskId || '',
      progress: clamp(safeNumber(source.progress, 0), 0, 100),
      progressStartedAt: safeNumber(source.progressStartedAt, 0)
    };
    if (type === 'group') node.children = Array.isArray(source.children) ? source.children.slice() : [];
    if (type === 'image') {
      node.imageSize = node.imageSize || '自适应';
      node.imageScale = String(node.imageScale || '1');
    }
    if (type === 'output' && !Array.isArray(node.outputItems)) node.outputItems = [];
    return node;
  }

  function normalizeState(raw) {
    const source = raw && typeof raw === 'object' ? raw : blankState();
    const viewport = source.viewport && typeof source.viewport === 'object' ? source.viewport : {};
    return {
      nodes: Array.isArray(source.nodes) ? source.nodes.map(normalizeNode) : [],
      edges: Array.isArray(source.edges)
        ? source.edges.filter((edge) => edge && edge.source && edge.target).map((edge) => ({
            id: edge.id || uid('edge'),
            source: edge.source,
            target: edge.target
          }))
        : [],
      logs: Array.isArray(source.logs) ? source.logs.slice(-80) : [],
      viewport: {
        x: Number.isFinite(viewport.x) ? viewport.x : 120,
        y: Number.isFinite(viewport.y) ? viewport.y : 80,
        scale: Number.isFinite(viewport.scale) ? clamp(viewport.scale, MIN_ZOOM, MAX_ZOOM) : 1
      }
    };
  }

  function nodeById(id) {
    return state.nodes.find((node) => node.id === id) || null;
  }

  function selectedNodes() {
    return state.nodes.filter((node) => selectedIds.has(node.id));
  }

  function selectOnly(id) {
    selectedIds = id ? new Set([id]) : new Set();
    renderSelection();
  }

  function toggleSelect(id) {
    if (selectedIds.has(id)) selectedIds.delete(id);
    else selectedIds.add(id);
    renderSelection();
  }

  function selectMany(ids) {
    selectedIds = new Set(ids);
    renderSelection();
  }

  function clientToWorld(clientX, clientY) {
    const rect = els.canvasArea.getBoundingClientRect();
    const scale = state.viewport.scale || 1;
    return {
      x: (clientX - rect.left - state.viewport.x) / scale,
      y: (clientY - rect.top - state.viewport.y) / scale
    };
  }

  function clientToCanvas(clientX, clientY) {
    const rect = els.canvasArea.getBoundingClientRect();
    return { x: clientX - rect.left, y: clientY - rect.top };
  }

  function visibleWorldRect() {
    const rect = els.canvasArea.getBoundingClientRect();
    const scale = state.viewport.scale || 1;
    return {
      x: -state.viewport.x / scale,
      y: -state.viewport.y / scale,
      w: rect.width / scale,
      h: rect.height / scale
    };
  }

  function contentBounds() {
    const view = visibleWorldRect();
    const rects = state.nodes.map((node) => ({
      x: safeNumber(node.x, 0),
      y: safeNumber(node.y, 0),
      w: Math.max(20, safeNumber(node.w, defaultSize(node.type).w)),
      h: Math.max(20, safeNumber(node.h, defaultSize(node.type).h))
    }));
    rects.push(view);
    if (!rects.length) rects.push({ x: -500, y: -300, w: 1000, h: 600 });

    let minX = Math.min(...rects.map((item) => item.x));
    let minY = Math.min(...rects.map((item) => item.y));
    let maxX = Math.max(...rects.map((item) => item.x + item.w));
    let maxY = Math.max(...rects.map((item) => item.y + item.h));
    const padding = Math.max(220, Math.min(900, Math.max(maxX - minX, maxY - minY) * 0.08));
    minX -= padding;
    minY -= padding;
    maxX += padding;
    maxY += padding;

    return {
      x: minX,
      y: minY,
      w: Math.max(1, maxX - minX),
      h: Math.max(1, maxY - minY)
    };
  }

  function zoomText(scale = state.viewport.scale) {
    return `${Math.round(scale * 100)}%`;
  }

  function syncWorldSize() {
    const width = `${WORLD.width}px`;
    const height = `${WORLD.height}px`;
    els.world.style.width = width;
    els.world.style.height = height;
    els.nodeLayer.style.width = width;
    els.nodeLayer.style.height = height;
    els.edgeLayer.setAttribute('width', String(WORLD.width));
    els.edgeLayer.setAttribute('height', String(WORLD.height));
    els.edgeLayer.setAttribute('viewBox', `0 0 ${WORLD.width} ${WORLD.height}`);
  }

  function applyViewport() {
    const { x, y, scale } = state.viewport;
    const gridSize = Math.max(7, 28 * scale);
    els.world.style.transform = `translate3d(${x}px, ${y}px, 0) scale(${scale})`;
    els.canvasArea.style.backgroundSize = `${gridSize}px ${gridSize}px, 100% 100%`;
    els.canvasArea.style.backgroundPosition = `${x % gridSize}px ${y % gridSize}px, 0 0`;
    els.zoomChip.textContent = zoomText(scale);
    els.minimapZoom.textContent = zoomText(scale);
    scheduleMinimapRender();
  }

  function scheduleMinimapRender() {
    if (minimapRaf) return;
    minimapRaf = requestAnimationFrame(() => {
      minimapRaf = 0;
      renderMinimap();
    });
  }

  function renderMinimap() {
    if (!els.minimapView || !els.minimapContent || !els.minimapViewport) return;
    const rect = els.minimapView.getBoundingClientRect();
    if (!rect.width || !rect.height) return;

    const bounds = contentBounds();
    const mapScale = Math.min(rect.width / bounds.w, rect.height / bounds.h);
    const contentW = bounds.w * mapScale;
    const contentH = bounds.h * mapScale;
    const offsetX = (rect.width - contentW) / 2;
    const offsetY = (rect.height - contentH) / 2;
    minimapLayout = { bounds, scale: mapScale, offsetX, offsetY };

    els.minimapContent.style.left = `${offsetX}px`;
    els.minimapContent.style.top = `${offsetY}px`;
    els.minimapContent.style.width = `${contentW}px`;
    els.minimapContent.style.height = `${contentH}px`;
    els.minimapContent.innerHTML = state.nodes.map((node) => {
      const typeClass = String(node.type || '').replace(/[^a-z0-9_-]/gi, '');
      const left = (safeNumber(node.x, 0) - bounds.x) * mapScale;
      const top = (safeNumber(node.y, 0) - bounds.y) * mapScale;
      const width = Math.max(3, safeNumber(node.w, defaultSize(node.type).w) * mapScale);
      const height = Math.max(3, safeNumber(node.h, defaultSize(node.type).h) * mapScale);
      return `<span class="minimap-node ${typeClass}" style="left:${left}px;top:${top}px;width:${width}px;height:${height}px"></span>`;
    }).join('');

    const view = visibleWorldRect();
    els.minimapViewport.style.left = `${offsetX + (view.x - bounds.x) * mapScale}px`;
    els.minimapViewport.style.top = `${offsetY + (view.y - bounds.y) * mapScale}px`;
    els.minimapViewport.style.width = `${Math.max(8, view.w * mapScale)}px`;
    els.minimapViewport.style.height = `${Math.max(8, view.h * mapScale)}px`;
  }

  function revealMinimap(duration = 1500) {
    if (!els.canvasArea) return;
    window.clearTimeout(minimapRevealTimer);
    els.canvasArea.classList.add('minimap-active');
    if (duration > 0) {
      minimapRevealTimer = window.setTimeout(() => els.canvasArea.classList.remove('minimap-active'), duration);
    }
  }

  function centerWorldPoint() {
    const rect = els.canvasArea.getBoundingClientRect();
    return clientToWorld(rect.left + rect.width / 2, rect.top + rect.height / 2);
  }

  function updateAccount(user = me) {
    if (!user) return;
    me = user;
    els.accountEmail.textContent = user.email || labels.account;
    els.creditText.textContent = `${user.credits || 0} 点`;
    els.accountLine.textContent = user.email || '';
    els.modalCredits.textContent = user.credits || 0;
    els.modalRole.textContent = user.is_admin ? labels.admin : labels.user;
    els.adminLink.classList.toggle('hidden', !user.is_admin);
  }

  async function loadMe() {
    const data = await api('/api/me');
    if (!data.user) {
      location.href = '/login';
      return null;
    }
    updateAccount(data.user);
    return data.user;
  }

  async function loadProjects() {
    const data = await api('/api/projects');
    projects = data.projects || [];
    if (!projects.length) {
      const created = await api('/api/projects', {
        method: 'POST',
        body: JSON.stringify({ name: labels.defaultProject })
      });
      projects = [created.project];
    }
    renderProjects();
    await selectProject(projects[0].id);
  }

  async function selectProject(projectId) {
    await saveCurrentCanvasIfDirty();
    currentProject = projects.find((item) => item.id === projectId) || projects[0] || null;
    renderProjects();
    if (!currentProject) return;
    const data = await api(`/api/projects/${currentProject.id}/canvases`);
    canvases = data.canvases || [];
    if (!canvases.length) {
      const created = await api(`/api/projects/${currentProject.id}/canvases`, {
        method: 'POST',
        body: JSON.stringify({ name: labels.canvasName })
      });
      canvases = [created.canvas];
    }
    renderCanvases();
    await selectCanvas(canvases[0].id);
  }

  async function selectCanvas(canvasId) {
    if (currentCanvas && currentCanvas.id !== canvasId) await saveCurrentCanvasIfDirty();
    const data = await api(`/api/canvases/${canvasId}`);
    currentCanvas = data.canvas;
    state = normalizeState(currentCanvas.state);
    selectedIds.clear();
    draftEdge = null;
    els.canvasTitle.textContent = currentCanvas.name || labels.canvas;
    applyViewport();
    renderCanvases();
    renderAll();
    setDirty(false);
    await loadTasks();
    await loadAssets();
  }

  function renderProjects() {
    els.projectList.innerHTML = projects.length ? '' : `<div class="muted">${labels.noProject}</div>`;
    projects.forEach((project) => {
      const button = document.createElement('button');
      button.className = `nav-item${currentProject && currentProject.id === project.id ? ' active' : ''}`;
      button.innerHTML = `<span>${escapeHtml(project.name)}</span><small>${project.canvas_count || 0}</small>`;
      button.addEventListener('click', () => selectProject(project.id).catch(showError));
      els.projectList.appendChild(button);
    });
  }

  function renderCanvases() {
    els.canvasList.innerHTML = canvases.length ? '' : `<div class="muted">${labels.noCanvas}</div>`;
    canvases.forEach((canvas) => {
      const button = document.createElement('button');
      button.className = `nav-item${currentCanvas && currentCanvas.id === canvas.id ? ' active' : ''}`;
      button.innerHTML = `<span>${escapeHtml(canvas.name)}</span><small>${labels.canvas}</small>`;
      button.addEventListener('click', () => selectCanvas(canvas.id).catch(showError));
      els.canvasList.appendChild(button);
    });
  }

  function addNode(type, patch = {}) {
    const center = centerWorldPoint();
    const size = defaultSize(type);
    const placedCount = state.nodes.filter((item) => item.type !== 'group').length;
    const col = placedCount % 2;
    const row = Math.floor(placedCount / 2);
    const node = normalizeNode({
      id: uid(type),
      type,
      x: center.x - 360 + col * 400,
      y: center.y - 165 + row * 315,
      w: size.w,
      h: size.h,
      title: typeNames[type] || 'Node',
      prompt: defaultPrompt(type),
      ...patch
    });
    state.nodes.push(node);
    selectOnly(node.id);
    addLog({ level: 'info', title: '已添加节点', detail: `${typeNames[type] || type} - ${node.title}` });
    renderAll();
    setDirty();
    return node;
  }

  function renderAll() {
    renderNodes();
    renderEdges();
    renderInspector();
    renderAssets();
    renderLogs();
    renderWorkflowSummary();
    scheduleMinimapRender();
    syncProgressTicker();
    els.emptyHint.classList.toggle('hidden', state.nodes.length > 0);
  }

  function renderSelection() {
    els.nodeLayer.querySelectorAll('[data-node-id]').forEach((element) => {
      const selected = selectedIds.has(element.dataset.nodeId);
      element.classList.toggle('selected', selected);
      element.classList.toggle('multi', selected && selectedIds.size > 1);
    });
    renderEdges();
    renderInspector();
    renderWorkflowSummary();
  }

  function mediaKindForUrl(url, fallback = '') {
    const value = String(url || '').toLowerCase();
    if (fallback) return fallback;
    if (/\.(mp4|webm|mov|m4v|mkv)(\?|$)/i.test(value)) return 'video';
    if (/\.(mp3|wav|m4a|aac|ogg|flac)(\?|$)/i.test(value)) return 'audio';
    return 'image';
  }

  function mediaHtml(node, compact = false) {
    const url = node.resultUrl || node.assetUrl || '';
    if (!url) return '';
    const safe = escapeHtml(url);
    const kind = mediaKindForUrl(url, node.resultKind);
    if (kind === 'video' || node.type === 'video') {
      return `<video class="node-media${compact ? ' compact' : ''}" src="${safe}" controls></video>`;
    }
    return `<img class="node-media${compact ? ' compact' : ''}" src="${safe}" alt="asset" loading="lazy" />`;
  }

  function renderNodes() {
    els.nodeLayer.innerHTML = '';
    const groups = state.nodes.filter((node) => node.type === 'group');
    const regular = state.nodes.filter((node) => node.type !== 'group');
    groups.forEach(renderGroupNode);
    regular.forEach(renderRegularNode);
    requestAnimationFrame(() => {
      state.nodes.forEach((node) => {
        const element = nodeElement(node.id);
        if (element && node.type !== 'group') node.h = Math.max(180, element.offsetHeight);
      });
      renderEdges();
      scheduleMinimapRender();
    });
  }

  function nodeElement(id) {
    return els.nodeLayer.querySelector(`[data-node-id="${CSS.escape(id)}"]`);
  }

  function applyNodePosition(node) {
    const element = nodeElement(node.id);
    if (!element) return;
    element.style.setProperty('--x', `${node.x}px`);
    element.style.setProperty('--y', `${node.y}px`);
    element.style.setProperty('--w', `${node.w}px`);
    element.style.setProperty('--h', `${node.h}px`);
    element.style.setProperty('--h', `${node.h}px`);
  }

  function renderGroupNode(node) {
    const element = document.createElement('section');
    element.className = `group-node${selectedIds.has(node.id) ? ' selected' : ''}`;
    element.dataset.nodeId = node.id;
    element.style.setProperty('--x', `${node.x}px`);
    element.style.setProperty('--y', `${node.y}px`);
    element.style.setProperty('--w', `${node.w}px`);
    element.style.setProperty('--h', `${node.h}px`);
    element.innerHTML = `
      <div class="group-title">${escapeHtml(node.title || typeNames.group)}</div>
      <div class="group-count">${groupChildren(node).length} 个节点</div>
      <div class="group-resize" title="调整分组大小"></div>
    `;
    element.querySelector('.group-title').addEventListener('pointerdown', (event) => startNodeDrag(event, node, true));
    element.querySelector('.group-resize').addEventListener('pointerdown', (event) => startGroupResize(event, node));
    element.addEventListener('pointerdown', (event) => {
      if (event.target.closest('.group-resize')) return;
      event.stopPropagation();
      if (event.shiftKey) toggleSelect(node.id);
      else if (!selectedIds.has(node.id)) selectOnly(node.id);
    });
    els.nodeLayer.appendChild(element);
  }

  function renderRegularNode(node) {
    const element = document.createElement('article');
    element.className = `node node-${node.type}${selectedIds.has(node.id) ? ' selected' : ''}${selectedIds.has(node.id) && selectedIds.size > 1 ? ' multi' : ''}`;
    element.dataset.nodeId = node.id;
    element.style.setProperty('--x', `${node.x}px`);
    element.style.setProperty('--y', `${node.y}px`);
    element.style.setProperty('--w', `${node.w}px`);
    element.style.setProperty('--h', `${node.h}px`);
    element.innerHTML = `
      <button class="node-port input" data-port="input" title="输入"></button>
      <button class="node-port output" data-port="output" title="输出"></button>
      <div class="node-head">
        <div class="node-title-wrap">
          <div class="node-type">${escapeHtml(typeNames[node.type] || node.type)}</div>
          <div class="node-title">${escapeHtml(node.title)}</div>
        </div>
        <div class="node-tools">
          <button data-node-action="run" title="Run">▶</button>
          <button data-node-action="delete" title="删除">×</button>
        </div>
      </div>
      <div class="node-body">${nodeBodyHtml(node)}</div>
      <button class="node-resize" type="button" title="调整大小" aria-label="调整大小"></button>
    `;

    element.addEventListener('pointerdown', (event) => {
      if (event.target.closest('input,textarea,button,select,video,.node-port,.node-media')) return;
      event.stopPropagation();
      if (event.shiftKey) toggleSelect(node.id);
      else if (!selectedIds.has(node.id)) selectOnly(node.id);
    });
    element.querySelector('.node-head').addEventListener('pointerdown', (event) => startNodeDrag(event, node, false));
    element.querySelector('.node-resize').addEventListener('pointerdown', (event) => startNodeResize(event, node));
    element.querySelector('.node-port.output').addEventListener('pointerdown', (event) => startEdgeDrag(event, node));
    element.querySelector('.node-port.input').addEventListener('pointerup', (event) => finishEdgeDrag(event, node));
    bindNodeControls(element, node);
    els.nodeLayer.appendChild(element);
  }

  function nodeBodyHtml(node) {
    if (node.type === 'prompt') return promptNodeHtml(node);
    if (node.type === 'loop') return loopNodeHtml(node);
    if (node.type === 'llm') return llmNodeHtml(node);
    if (node.type === 'image') return imageNodeHtml(node);
    if (node.type === 'video') return videoNodeHtml(node);
    if (node.type === 'output') return outputNodeHtml(node);
    return promptNodeHtml(node);
  }

  function upstreamPreviewHtml(node) {
    const upstream = upstreamNodes(node.id);
    if (!upstream.length) return '<div class="node-empty">未连接上游节点</div>';
    return upstream.map((item) => {
      const media = mediaHtml(item, true);
      const text = nodeContent(item).slice(0, 160);
      return `
        <div class="input-preview-item">
          ${media || '<div class="input-preview-icon">TXT</div>'}
          <div><strong>${escapeHtml(item.title || typeNames[item.type])}</strong><span>${escapeHtml(text || '暂无文本输出')}</span></div>
        </div>
      `;
    }).join('');
  }

  function resultHtml(node) {
    const media = mediaHtml(node);
    const text = node.resultText ? `<div class="node-result">${escapeHtml(node.resultText)}</div>` : '';
    return media || text ? `<div class="node-result-stack">${media}${text}</div>` : '';
  }

  function nodeStatusText(node, fallback) {
    if (node.status === 'queued' || node.status === 'running') return '运行中';
    if (node.status === 'failed') return '失败';
    if (node.status === 'succeeded') return '完成';
    return fallback;
  }

  function generationProgress(node) {
    if (node.status === 'succeeded') return 100;
    if (node.status === 'failed') return clamp(Math.round(node.progress || 0), 1, 99);
    if (node.status !== 'queued' && node.status !== 'running') return 0;
    const startedAt = Number(node.progressStartedAt || Date.now());
    const elapsed = Math.max(0, (Date.now() - startedAt) / 1000);
    const expectedSeconds = node.type === 'video' ? 240 : node.type === 'image' ? 150 : 60;
    const estimated = 6 + (elapsed / expectedSeconds) * 89;
    return clamp(Math.round(Math.max(node.progress || 0, estimated)), 6, 95);
  }

  function stageProgressHtml(node) {
    if (!['queued', 'running', 'succeeded', 'failed'].includes(node.status || '')) return '';
    const percent = generationProgress(node);
    return `
      <div class="stage-progress" data-progress-node="${escapeHtml(node.id)}">
        <div class="stage-progress-track">
          <div class="stage-progress-fill" style="width:${percent}%"></div>
        </div>
        <span class="stage-progress-label">${percent}%</span>
      </div>
    `;
  }

  function renderProgressIndicators() {
    document.querySelectorAll('[data-progress-node]').forEach((element) => {
      const node = nodeById(element.dataset.progressNode);
      if (!node) return;
      const percent = generationProgress(node);
      const fill = element.querySelector('.stage-progress-fill');
      const label = element.querySelector('.stage-progress-label');
      if (fill) fill.style.width = `${percent}%`;
      if (label) label.textContent = `${percent}%`;
    });
  }

  function syncProgressTicker() {
    const hasRunning = state.nodes.some((node) => ['queued', 'running'].includes(node.status || ''));
    if (hasRunning && !progressTimer) {
      progressTimer = window.setInterval(renderProgressIndicators, 1000);
    } else if (!hasRunning && progressTimer) {
      window.clearInterval(progressTimer);
      progressTimer = null;
    }
  }

  function nodeStageHtml(node, kind, emptyTitle, emptyHint) {
    const media = mediaHtml(node);
    const text = node.resultText ? `<div class="node-stage-copy">${escapeHtml(node.resultText)}</div>` : '';
    const hasResult = Boolean(media || text);
    const icon = kind === 'video' ? 'VIDEO' : kind === 'image' ? 'IMG' : 'TXT';
    return `
      <section class="node-stage node-stage-${escapeHtml(kind)}">
        <span class="stage-status ${escapeHtml(node.status || 'idle')}">${escapeHtml(nodeStatusText(node, hasResult ? '完成' : '待生成'))}</span>
        <div class="node-stage-content">
          ${hasResult ? `${media}${text}` : `
            <div class="stage-placeholder">
              <span class="stage-icon">${escapeHtml(icon)}</span>
              <strong>${escapeHtml(emptyTitle)}</strong>
              <small>${escapeHtml(emptyHint)}</small>
            </div>
          `}
        </div>
        ${stageProgressHtml(node)}
      </section>
    `;
  }

  function consoleRunButtonHtml(runLabel) {
    return `<button class="console-run-button" data-node-action="run" title="${escapeHtml(runLabel)}">↑</button>`;
  }

  function toolButtonHtml(action, label) {
    return `<button class="console-tool" type="button" data-tool-action="${escapeHtml(action)}">${escapeHtml(label)}</button>`;
  }

  function footerHtml(node, runLabel = '运行') {
    return `
      <div class="node-footer">
        <button class="node-action" data-node-action="run">${escapeHtml(runLabel)}</button>
        <span class="node-status ${escapeHtml(node.status || '')}">${escapeHtml(node.status || 'idle')}</span>
      </div>
    `;
  }

  function promptNodeHtml(node) {
    return `
      ${nodeStageHtml(node, 'text', '文本未生成', '输入内容，或连接上游节点生成文本。')}
      <section class="node-console">
        <div class="node-toolbar-row">
          ${toolButtonHtml('write', '自己编写')}
          ${toolButtonHtml('textToVideo', '文生视频')}
          ${toolButtonHtml('imagePrompt', '图片反推提示词')}
          ${toolButtonHtml('musicPrompt', '文字生音乐')}
        </div>
        <textarea class="node-textarea prompt-text console-input" spellcheck="false" data-field="prompt" placeholder="${escapeHtml(labels.promptText)}">${escapeHtml(node.prompt)}</textarea>
        <div class="node-bottom-bar">
          <span class="muted">提示词节点</span>
          ${consoleRunButtonHtml('汇总文本')}
        </div>
      </section>
    `;
  }

  function loopNodeHtml(node) {
    return `
      <label class="field-block"><span>来源提示词</span><textarea class="node-textarea" spellcheck="false" data-field="prompt">${escapeHtml(node.prompt)}</textarea></label>
      <label class="field-block"><span>循环项目</span><textarea class="node-textarea loop-items" spellcheck="false" data-field="loopItems">${escapeHtml(node.loopItems || '')}</textarea></label>
      ${resultHtml(node)}
      ${footerHtml(node, '生成循环')}
    `;
  }

  function llmNodeHtml(node) {
    return `
      <div class="field-grid two">
        <select data-field="llmProvider">${optionHtml(nodePresets.llmProviders, node.llmProvider)}</select>
        <select data-field="model">${optionHtml(nodePresets.llmModels, node.model)}</select>
      </div>
      <label class="field-block compact"><span>System</span><textarea class="node-textarea system-text" spellcheck="false" data-field="systemPrompt">${escapeHtml(node.systemPrompt || '')}</textarea></label>
      <div class="input-preview-list">${upstreamPreviewHtml(node)}</div>
      <textarea class="node-textarea prompt-text" spellcheck="false" data-field="prompt" placeholder="${escapeHtml(labels.llmPrompt)}">${escapeHtml(node.prompt)}</textarea>
      ${resultHtml(node)}
      ${footerHtml(node, '运行 LLM')}
    `;
  }

  function imageNodeHtml(node) {
    const imageScale = String(node.imageScale || '1');
    return `
      ${nodeStageHtml(node, 'image', '图片未生成', '输入提示词、上传参考图，或连接上游节点。')}
      <section class="node-console">
        <div class="node-toolbar-row">
          ${toolButtonHtml('uploadReference', '上传')}
          ${toolButtonHtml('addReference', '参考')}
          ${toolButtonHtml('stylePrompt', '风格')}
          ${toolButtonHtml('commonPrompt', '常用提示词')}
          ${toolButtonHtml('cameraPrompt', '摄影机控制')}
        </div>
        <div class="input-preview-list compact-preview">${upstreamPreviewHtml(node)}</div>
        <textarea class="node-textarea prompt-text console-input" spellcheck="false" data-field="prompt" placeholder="${escapeHtml(labels.imagePrompt)}">${escapeHtml(node.prompt)}</textarea>
        <div class="node-bottom-bar image-bottom-bar">
          <select data-field="apiProvider">${optionHtml(nodePresets.imageProviders, node.apiProvider)}</select>
          <select data-field="model">${optionHtml(nodePresets.imageModels, node.model)}</select>
          ${consoleRunButtonHtml('生成图片')}
        </div>
        <div class="image-option-grid">
          <label><span>比例</span><select data-field="ratio">${optionHtml(nodePresets.ratios, node.ratio)}</select></label>
          <label><span>尺寸</span><select data-field="imageSize">${optionHtml(nodePresets.imageSizes, node.imageSize)}</select></label>
          <label><span>张数</span><input data-field="count" type="number" min="1" max="8" value="${escapeHtml(node.count || 1)}"></label>
          <div class="image-scale-group" aria-label="倍率">
            ${nodePresets.imageScales.map((scale) => chipHtml(scale, `${scale}x`, imageScale === scale, 'imageScale')).join('')}
          </div>
        </div>
      </section>
    `;
  }

  function videoNodeHtml(node) {
    const fps = Number(node.outputFps || 0);
    return `
      ${nodeStageHtml(node, 'video', '视频未生成', '输入镜头提示词、上传素材，或连接上游节点。')}
      <section class="node-console">
        <div class="node-toolbar-row mode-row">
          ${chipHtml('text_to_video', '文生视频', node.videoMode === 'text_to_video', 'videoMode')}
          ${chipHtml('image_to_video', '图生视频', node.videoMode === 'image_to_video', 'videoMode')}
          ${chipHtml('video_to_video', '视频转视频', node.videoMode === 'video_to_video', 'videoMode')}
          ${chipHtml('firstLastFrame', '首尾帧', !!node.firstLastFrame, 'toggle')}
        </div>
        <div class="node-toolbar-row">
          ${toolButtonHtml('markShot', '标记')}
          ${toolButtonHtml('effectPrompt', '特效')}
          ${toolButtonHtml('characterRef', '角色库')}
          ${toolButtonHtml('addReference', '参考')}
        </div>
        <div class="input-preview-list compact-preview">${upstreamPreviewHtml(node)}</div>
        <textarea class="node-textarea prompt-text console-input" spellcheck="false" data-field="prompt" placeholder="${escapeHtml(labels.videoPrompt)}">${escapeHtml(node.prompt)}</textarea>
        <div class="node-bottom-bar video-bottom-bar">
          <select data-field="apiProvider">${optionHtml(nodePresets.videoProviders, node.apiProvider)}</select>
          <select data-field="model">${optionHtml(nodePresets.videoModels, node.model)}</select>
          <select data-field="aspectRatio">${optionHtml(nodePresets.ratios, node.aspectRatio)}</select>
          <select data-field="resolution">${optionHtml(nodePresets.resolutions, node.resolution)}</select>
          <input data-field="duration" type="number" min="1" max="60" value="${escapeHtml(node.duration || 5)}">
          <div class="fps-compact">
            ${chipHtml('0', '原始', fps === 0, 'outputFps')}
            ${chipHtml('30', '30fps', fps === 30, 'outputFps')}
            ${chipHtml('60', '60fps', fps === 60, 'outputFps')}
          </div>
          ${consoleRunButtonHtml('生成视频')}
        </div>
      </section>
    `;
  }

  function outputNodeHtml(node) {
    const media = mediaHtml(node);
    const text = node.resultText || node.prompt;
    return `
      <textarea class="node-textarea prompt-text" spellcheck="false" data-field="prompt" placeholder="${escapeHtml(labels.outputPrompt)}">${escapeHtml(node.prompt)}</textarea>
      <div class="output-grid">${media || '<div class="node-empty">连接上游节点，或运行输出节点。</div>'}</div>
      ${text ? `<div class="node-result">${escapeHtml(text)}</div>` : ''}
      ${footerHtml(node, '汇总输出')}
    `;
  }

  function toolActionText(action) {
    const snippets = {
      write: '请将输入内容改写成清晰、可直接用于生产的文本。',
      textToVideo: '请把这段文字转成视频生成提示词，包含主体、动作、镜头、环境、光线和运动方式。',
      imagePrompt: '请生成图片提示词，包含主体、构图、风格、光线、镜头和负面约束。',
      musicPrompt: '请生成音乐提示词，包含情绪、节奏、乐器、氛围和使用时段。',
      addReference: '参考连接的素材，保持身份、服装、场景、风格和连续性一致。',
      stylePrompt: '风格：电影感构图，角色身份一致，材质细节清晰，光线受控。',
      commonPrompt: '负面约束：避免多余肢体、手部畸形、文字乱码、服装不一致、重复人脸、低质伪影。',
      cameraPrompt: '摄影机：描述景别、镜头焦段、机位角度、运镜、焦点、景深和画面构图。',
      markShot: '镜头说明：定义主体动作、镜头运动、场景转场和关键帧意图。',
      effectPrompt: '特效：描述物理运动、粒子、天气、光影变化，以及与主体的互动。',
      characterRef: '角色参考：保持五官、发型、服装、身材比例、表情风格和连续性。'
    };
    return snippets[action] || '';
  }
  function handleToolAction(action, node) {
    if (action === 'uploadReference') {
      els.fileInput.click();
      return;
    }
    const snippet = toolActionText(action);
    if (!snippet) return;
    node.prompt = [node.prompt, snippet].filter(Boolean).join(node.prompt ? '\n' : '');
    renderAll();
    setDirty();
  }

  function bindNodeControls(element, node) {
    element.querySelectorAll('[data-field]').forEach((input) => {
      const field = input.dataset.field;
      const handler = () => {
        if (input.type === 'number') {
          node[field] = safeNumber(input.value, node[field] || 0);
        } else {
          node[field] = input.value;
        }
        setDirty();
        renderInspector();
        renderWorkflowSummary();
      };
      input.addEventListener(input.tagName === 'SELECT' ? 'change' : 'input', handler);
    });
    element.querySelectorAll('[data-chip-field]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        const field = button.dataset.chipField;
        const value = button.dataset.chipValue;
        if (field === 'toggle') node[value] = !node[value];
        else if (field === 'outputFps') node[field] = Number(value) || 0;
        else node[field] = value;
        renderAll();
        setDirty();
      });
    });
    element.querySelectorAll('[data-tool-action]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        handleToolAction(button.dataset.toolAction, node);
      });
    });
    element.querySelectorAll('[data-node-action="run"]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        selectOnly(node.id);
        runNode(node).catch(showError);
      });
    });
    element.querySelector('[data-node-action="delete"]').addEventListener('click', (event) => {
      event.stopPropagation();
      selectOnly(node.id);
      deleteSelected();
    });
  }

  function nodeRect(node) {
    return { left: node.x, top: node.y, right: node.x + node.w, bottom: node.y + node.h };
  }

  function rectsIntersect(a, b) {
    return a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
  }

  function groupChildren(group) {
    const rect = nodeRect(group);
    return state.nodes.filter((node) => {
      if (node.id === group.id || node.type === 'group') return false;
      const child = nodeRect(node);
      const centerX = child.left + node.w / 2;
      const centerY = child.top + node.h / 2;
      return centerX >= rect.left && centerX <= rect.right && centerY >= rect.top && centerY <= rect.bottom;
    });
  }

  function startNodeDrag(event, node, includeGroupChildren) {
    if (event.button !== 0 || event.target.closest('input,textarea,button,select,video,.node-port')) return;
    event.preventDefault();
    event.stopPropagation();
    if (event.shiftKey) toggleSelect(node.id);
    else if (!selectedIds.has(node.id)) selectOnly(node.id);

    const movedNodes = new Map();
    selectedNodes().forEach((item) => movedNodes.set(item.id, item));
    if (includeGroupChildren) groupChildren(node).forEach((item) => movedNodes.set(item.id, item));
    activeDrag = {
      kind: 'node',
      start: clientToWorld(event.clientX, event.clientY),
      origins: [...movedNodes.values()].map((item) => ({ id: item.id, x: item.x, y: item.y }))
    };
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', endPointerAction, { once: true });
  }

  function startGroupResize(event, node) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    selectOnly(node.id);
    activeDrag = {
      kind: 'resize-group',
      start: clientToWorld(event.clientX, event.clientY),
      id: node.id,
      w: node.w,
      h: node.h
    };
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', endPointerAction, { once: true });
  }

  function startNodeResize(event, node) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    selectOnly(node.id);
    activeDrag = {
      kind: 'resize-node',
      start: clientToWorld(event.clientX, event.clientY),
      id: node.id,
      w: node.w,
      h: node.h
    };
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', endPointerAction, { once: true });
  }

  function startPan(event) {
    event.preventDefault();
    activeDrag = {
      kind: 'pan',
      start: { x: event.clientX, y: event.clientY },
      viewport: { ...state.viewport }
    };
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', endPointerAction, { once: true });
  }

  function startMarquee(event) {
    const point = clientToCanvas(event.clientX, event.clientY);
    activeDrag = { kind: 'marquee', start: point, current: point };
    els.selectionBox.classList.remove('hidden');
    paintMarquee();
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', endPointerAction, { once: true });
  }

  function onPointerMove(event) {
    if (!activeDrag) return;
    if (activeDrag.kind === 'pan') {
      state.viewport.x = activeDrag.viewport.x + event.clientX - activeDrag.start.x;
      state.viewport.y = activeDrag.viewport.y + event.clientY - activeDrag.start.y;
      applyViewport();
      revealMinimap();
      setDirty();
      return;
    }
    if (activeDrag.kind === 'node') {
      const point = clientToWorld(event.clientX, event.clientY);
      const dx = point.x - activeDrag.start.x;
      const dy = point.y - activeDrag.start.y;
      activeDrag.origins.forEach((origin) => {
        const node = nodeById(origin.id);
        if (!node) return;
        node.x = origin.x + dx;
        node.y = origin.y + dy;
        applyNodePosition(node);
      });
      scheduleEdges();
      scheduleMinimapRender();
      return;
    }
    if (activeDrag.kind === 'resize-group') {
      const node = nodeById(activeDrag.id);
      if (!node) return;
      const point = clientToWorld(event.clientX, event.clientY);
      node.w = Math.max(180, activeDrag.w + point.x - activeDrag.start.x);
      node.h = Math.max(120, activeDrag.h + point.y - activeDrag.start.y);
      applyNodePosition(node);
      scheduleEdges();
      scheduleMinimapRender();
      return;
    }
    if (activeDrag.kind === 'resize-node') {
      const node = nodeById(activeDrag.id);
      if (!node) return;
      const point = clientToWorld(event.clientX, event.clientY);
      const min = defaultSize(node.type);
      node.w = Math.max(Math.min(240, min.w), activeDrag.w + point.x - activeDrag.start.x);
      node.h = Math.max(Math.min(180, min.h), activeDrag.h + point.y - activeDrag.start.y);
      applyNodePosition(node);
      scheduleEdges();
      scheduleMinimapRender();
      return;
    }
    if (activeDrag.kind === 'marquee') {
      activeDrag.current = clientToCanvas(event.clientX, event.clientY);
      paintMarquee();
    }
  }

  function endPointerAction() {
    if (!activeDrag) return;
    const finished = activeDrag;
    window.removeEventListener('pointermove', onPointerMove);
    activeDrag = null;
    if (finished.kind === 'marquee') {
      const rect = marqueeWorldRect(finished);
      const ids = state.nodes
        .filter((node) => rectsIntersect(nodeRect(node), rect))
        .map((node) => node.id);
      selectMany(ids);
      els.selectionBox.classList.add('hidden');
    }
    if (finished.kind !== 'marquee') {
      renderInspector();
      renderWorkflowSummary();
      setDirty();
    }
  }

  function paintMarquee() {
    if (!activeDrag || activeDrag.kind !== 'marquee') return;
    const a = activeDrag.start;
    const b = activeDrag.current;
    const left = Math.min(a.x, b.x);
    const top = Math.min(a.y, b.y);
    els.selectionBox.style.left = `${left}px`;
    els.selectionBox.style.top = `${top}px`;
    els.selectionBox.style.width = `${Math.abs(a.x - b.x)}px`;
    els.selectionBox.style.height = `${Math.abs(a.y - b.y)}px`;
  }

  function marqueeWorldRect(marquee) {
    const rect = els.canvasArea.getBoundingClientRect();
    const left = Math.min(marquee.start.x, marquee.current.x);
    const top = Math.min(marquee.start.y, marquee.current.y);
    const right = Math.max(marquee.start.x, marquee.current.x);
    const bottom = Math.max(marquee.start.y, marquee.current.y);
    const a = clientToWorld(rect.left + left, rect.top + top);
    const b = clientToWorld(rect.left + right, rect.top + bottom);
    return { left: a.x, top: a.y, right: b.x, bottom: b.y };
  }

  function startEdgeDrag(event, source) {
    if (event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    if (activeEdgeCleanup) activeEdgeCleanup();
    selectOnly(source.id);
    draftEdge = { source: source.id, point: clientToWorld(event.clientX, event.clientY) };
    renderEdges();
    const portEl = event.currentTarget;
    try { portEl?.setPointerCapture?.(event.pointerId); } catch (_error) {}
    const onMove = (moveEvent) => {
      draftEdge = { source: source.id, point: clientToWorld(moveEvent.clientX, moveEvent.clientY) };
      scheduleEdges();
    };
    const cleanup = () => {
      window.removeEventListener('pointermove', onMove);
      window.removeEventListener('pointerup', onUp);
      window.removeEventListener('pointercancel', onCancel);
      window.removeEventListener('blur', onCancel);
      try { portEl?.releasePointerCapture?.(event.pointerId); } catch (_error) {}
      activeEdgeCleanup = null;
    };
    const onUp = (upEvent) => {
      cleanup();
      const target = document.elementFromPoint(upEvent.clientX, upEvent.clientY)?.closest?.('[data-node-id]');
      const port = document.elementFromPoint(upEvent.clientX, upEvent.clientY)?.closest?.('.node-port.input');
      if (target && port) addEdge(source.id, target.dataset.nodeId);
      draftEdge = null;
      renderAll();
    };
    const onCancel = () => {
      cleanup();
      draftEdge = null;
      renderEdges();
    };
    activeEdgeCleanup = onCancel;
    window.addEventListener('pointermove', onMove);
    window.addEventListener('pointerup', onUp, { once: true });
    window.addEventListener('pointercancel', onCancel, { once: true });
    window.addEventListener('blur', onCancel, { once: true });
  }

  function finishEdgeDrag(event, target) {
    if (!draftEdge || draftEdge.source === target.id) return;
    event.preventDefault();
    event.stopPropagation();
    addEdge(draftEdge.source, target.id);
    draftEdge = null;
    renderAll();
  }

  function addEdge(source, target) {
    if (!source || !target || source === target) return;
    const sourceNode = nodeById(source);
    const targetNode = nodeById(target);
    if (!sourceNode || !targetNode || sourceNode.type === 'group' || targetNode.type === 'group') return;
    if (state.edges.some((edge) => edge.source === source && edge.target === target)) return;
    state.edges.push({ id: uid('edge'), source, target });
    addLog({ level: 'info', title: '已添加连线', detail: `${sourceNode.title} -> ${targetNode.title}` });
    setDirty();
  }
  function portPoint(node, side) {
    const element = nodeElement(node.id);
    const height = element && node.type !== 'group' ? element.offsetHeight : node.h;
    return {
      x: side === 'output' ? node.x + node.w : node.x,
      y: node.y + height / 2
    };
  }

  function edgePath(start, end) {
    const distance = Math.abs(end.x - start.x);
    const bend = Math.max(70, distance * 0.46);
    return `M ${start.x} ${start.y} C ${start.x + bend} ${start.y}, ${end.x - bend} ${end.y}, ${end.x} ${end.y}`;
  }

  function scheduleEdges() {
    if (edgeRaf) return;
    edgeRaf = requestAnimationFrame(() => {
      edgeRaf = 0;
      renderEdges();
    });
  }

  function renderEdges() {
    els.edgeLayer.innerHTML = '';
    state.edges.forEach((edge) => {
      const source = nodeById(edge.source);
      const target = nodeById(edge.target);
      if (!source || !target || source.type === 'group' || target.type === 'group') return;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('class', 'edge-path');
      path.setAttribute('d', edgePath(portPoint(source, 'output'), portPoint(target, 'input')));
      els.edgeLayer.appendChild(path);
    });
    if (draftEdge) {
      const source = nodeById(draftEdge.source);
      if (source) {
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('class', 'edge-path draft');
        path.setAttribute('d', edgePath(portPoint(source, 'output'), draftEdge.point));
        els.edgeLayer.appendChild(path);
      }
    }
  }

  function groupSelected() {
    const items = selectedNodes().filter((node) => node.type !== 'group');
    if (!items.length) return;
    const left = Math.min(...items.map((node) => node.x)) - 38;
    const top = Math.min(...items.map((node) => node.y)) - 46;
    const right = Math.max(...items.map((node) => node.x + node.w)) + 38;
    const bottom = Math.max(...items.map((node) => node.y + node.h)) + 38;
    const group = normalizeNode({
      id: uid('group'),
      type: 'group',
      title: `分组 ${state.nodes.filter((node) => node.type === 'group').length + 1}`,
      x: left,
      y: top,
      w: Math.max(220, right - left),
      h: Math.max(160, bottom - top),
      prompt: ''
    });
    state.nodes.unshift(group);
    selectOnly(group.id);
    addLog({ level: 'info', title: '已创建分组', detail: `${items.length} 个节点` });
    renderAll();
    setDirty();
  }

  function deleteSelected() {
    if (!selectedIds.size) return;
    if (!window.confirm(labels.deleteConfirm)) return;
    const ids = new Set(selectedIds);
    state.nodes = state.nodes.filter((node) => !ids.has(node.id));
    state.edges = state.edges.filter((edge) => !ids.has(edge.source) && !ids.has(edge.target));
    selectedIds.clear();
    addLog({ level: 'info', title: '已删除选中内容', detail: `${ids.size} 项` });
    renderAll();
    setDirty();
  }

  function renderInspector() {
    const items = selectedNodes();
    if (!items.length) {
      els.nodeInspector.innerHTML = '<div class="muted">选择一个节点后，可以编辑名称、提示词、状态和任务信息。</div>';
      return;
    }
    if (items.length > 1) {
      els.nodeInspector.innerHTML = `
        <div class="inspect-grid">
          <div class="pill-row"><span class="pill">已选 ${items.length} 个</span></div>
          <button id="inspectGroupBtn" class="small-button">选中内容打组</button>
          <button id="inspectRunBtn" class="small-button">运行选中链路</button>
          <button id="inspectDeleteBtn" class="danger-button">删除选中</button>
        </div>
      `;
      document.getElementById('inspectGroupBtn').addEventListener('click', groupSelected);
      document.getElementById('inspectRunBtn').addEventListener('click', () => runChain().catch(showError));
      document.getElementById('inspectDeleteBtn').addEventListener('click', deleteSelected);
      return;
    }
    const node = items[0];
    els.nodeInspector.innerHTML = `
      <div class="inspect-grid">
        <label>
          <span class="inspect-label">名称</span>
          <input id="inspectTitle" class="inspect-input" value="${escapeHtml(node.title)}" />
        </label>
        <div class="pill-row">
          <span class="pill">${escapeHtml(typeNames[node.type] || node.type)}</span>
          <span class="pill">${Math.round(node.x)}, ${Math.round(node.y)}</span>
          ${node.type === 'group' ? `<span class="pill">${groupChildren(node).length} 个节点</span>` : ''}
        </div>
        ${node.type !== 'group' ? `
          <label>
            <span class="inspect-label">提示词 / 内容</span>
            <textarea id="inspectPrompt" class="inspect-input inspect-textarea">${escapeHtml(node.prompt)}</textarea>
          </label>
        ` : ''}
        <div class="pill-row">
          <button id="inspectRunBtn" class="small-button">${node.type === 'group' ? '运行分组' : '运行节点'}</button>
          <button id="inspectDeleteBtn" class="danger-button">删除</button>
        </div>
        <div class="muted">${escapeHtml(node.taskId ? `任务 ID：${node.taskId}` : '暂未绑定任务')}</div>
      </div>
    `;
    document.getElementById('inspectTitle').addEventListener('input', (event) => {
      node.title = event.target.value;
      renderNodes();
      renderWorkflowSummary();
      setDirty();
    });
    const prompt = document.getElementById('inspectPrompt');
    if (prompt) {
      prompt.addEventListener('input', (event) => {
        node.prompt = event.target.value;
        const card = nodeElement(node.id);
        const textarea = card?.querySelector('[data-field="prompt"]');
        if (textarea && textarea.value !== node.prompt) textarea.value = node.prompt;
        renderWorkflowSummary();
        setDirty();
      });
    }
    document.getElementById('inspectRunBtn').addEventListener('click', () => runNode(node).catch(showError));
    document.getElementById('inspectDeleteBtn').addEventListener('click', deleteSelected);
  }

  async function saveCanvas(options = {}) {
    if (!currentCanvas) return;
    els.saveState.textContent = labels.saving;
    const data = await api(`/api/canvases/${currentCanvas.id}`, {
      method: 'PUT',
      body: JSON.stringify({ name: currentCanvas.name, state })
    });
    currentCanvas = data.canvas;
    if (!options.silent) addLog({ level: 'success', title: '画布已保存', detail: currentCanvas.name || labels.canvas });
    setDirty(false);
    renderCanvases();
  }

  async function saveCurrentCanvasIfDirty() {
    if (!dirty || !currentCanvas) return;
    if (savingInFlight) return savingInFlight;
    savingInFlight = saveCanvas({ silent: true }).finally(() => {
      savingInFlight = null;
    });
    return savingInFlight;
  }
  function upstreamNodes(nodeId) {
    return state.edges
      .filter((edge) => edge.target === nodeId)
      .map((edge) => nodeById(edge.source))
      .filter(Boolean);
  }

  function downstreamNodes(nodeId) {
    return state.edges
      .filter((edge) => edge.source === nodeId)
      .map((edge) => nodeById(edge.target))
      .filter(Boolean);
  }

  function nodeContent(node) {
    const pieces = [];
    if (!node) return '';
    if (node.title) pieces.push(`[${typeNames[node.type] || node.type}] ${node.title}`);
    if (node.type === 'loop' && node.loopItems) pieces.push(renderLoopText(node));
    if (node.prompt) pieces.push(node.prompt);
    if (node.resultText) pieces.push(node.resultText);
    if (node.resultUrl) pieces.push(node.resultUrl);
    if (node.assetUrl) pieces.push(node.assetUrl);
    return pieces.filter(Boolean).join('\n');
  }

  function upstreamContext(node) {
    const upstream = upstreamNodes(node.id);
    if (!upstream.length) return '';
    return upstream.map((item, index) => `# Input ${index + 1}: ${typeNames[item.type] || item.type}\n${nodeContent(item)}`).join('\n\n');
  }

  function renderLoopText(node) {
    const base = node.prompt || '';
    const lines = String(node.loopItems || '').split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (!lines.length) return base;
    return lines.map((line, index) => `#${index + 1} ${base}\n${line}`).join('\n\n');
  }

  function taskPrompt(node) {
    const upstream = upstreamContext(node);
    const own = node.prompt || defaultPrompt(node.type);
    const params = taskParams(node);
    return [upstream, `# Prompt\n${own}`, params].filter(Boolean).join('\n\n');
  }

  function taskParams(node) {
    if (node.type === 'image') {
      return `# Params\nprovider=${node.apiProvider}; model=${node.model}; ratio=${node.ratio}; image_size=${node.imageSize}; image_scale=${node.imageScale || 1}; count=${node.count || 1}`;
    }
    if (node.type === 'video') {
      return `# Params\nprovider=${node.apiProvider}; model=${node.model}; mode=${node.videoMode}; duration=${node.duration}; aspect=${node.aspectRatio}; resolution=${node.resolution}; output_fps=${node.outputFps || 0}; enhance_prompt=${!!node.enhancePrompt}; fixed_camera=${!!node.cameraFixed}; audio=${!!node.generateAudio}`;
    }
    if (node.type === 'llm') {
      return `# System\n${node.systemPrompt || ''}\n\n# Params\nprovider=${node.llmProvider}; model=${node.model}`;
    }
    return '';
  }
  function findUrl(value) {
    if (!value) return '';
    if (typeof value === 'string') return /^(https?:|data:|\/api\/assets\/)/.test(value) ? value : '';
    if (Array.isArray(value)) {
      for (const item of value) {
        const found = findUrl(item);
        if (found) return found;
      }
      return '';
    }
    if (typeof value === 'object') {
      for (const key of ['url', 'image_url', 'video_url', 'output_url', 'download_url']) {
        if (typeof value[key] === 'string') return value[key];
      }
      for (const item of Object.values(value)) {
        const found = findUrl(item);
        if (found) return found;
      }
    }
    return '';
  }

  function findBase64(value) {
    if (!value) return '';
    if (typeof value === 'object') {
      for (const key of ['b64_json', 'base64', 'image_base64']) {
        if (typeof value[key] === 'string') return value[key];
      }
      for (const item of Object.values(value)) {
        const found = findBase64(item);
        if (found) return found;
      }
    }
    return '';
  }

  function applyTaskResult(node, task) {
    node.status = task.status;
    node.taskId = task.id;
    const result = task.result || {};
    if (task.status === 'failed') {
      node.progress = generationProgress(node);
      node.resultText = task.error || labels.failed;
      return;
    }
    if (task.status !== 'succeeded') {
      node.progress = generationProgress(node);
      return;
    }
    node.progress = 100;
    if (task.kind === 'llm') {
      node.resultText = result.text || JSON.stringify(result.raw || result, null, 2);
      node.resultKind = 'text';
      return;
    }
    const url = findUrl(result);
    const b64 = findBase64(result);
    if (url) {
      node.resultUrl = url;
      node.resultKind = task.kind === 'video' ? 'video' : mediaKindForUrl(url, task.kind);
      node.resultText = '';
    } else if (b64) {
      node.resultUrl = `data:image/png;base64,${b64}`;
      node.resultKind = 'image';
      node.resultText = '';
    } else {
      node.resultText = JSON.stringify(result.raw || result, null, 2);
    }
  }

  function isLocalRunnable(node) {
    return ['prompt', 'loop', 'output'].includes(node.type);
  }

  function isRemoteRunnable(node) {
    return ['llm', 'image', 'video'].includes(node.type);
  }

  async function runSelectedNode() {
    const node = selectedNodes()[0];
    if (!node || node.type === 'group') {
      window.alert(labels.selectRunnable);
      return;
    }
    await runNode(node);
  }

  async function runNode(node) {
    if (!node || node.type === 'group') {
      window.alert(labels.selectRunnable);
      return;
    }
    if (isLocalRunnable(node)) {
      runLocalNode(node);
      return;
    }
    if (!isRemoteRunnable(node)) {
      window.alert(labels.selectRunnable);
      return;
    }
    node.status = 'queued';
    node.progress = 6;
    node.progressStartedAt = Date.now();
    node.resultText = '';
    node.resultUrl = '';
    addLog({ level: 'info', title: '节点已加入队列', detail: `${typeNames[node.type]} -> ${node.title}` });
    renderAll();
    const data = await api('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({
        kind: node.type === 'image' ? 'image' : node.type,
        prompt: taskPrompt(node),
        canvas_id: currentCanvas?.id || '',
        node_id: node.id
      })
    });
    updateAccount({ ...me, credits: data.balance });
    applyTaskResult(node, data.task);
    renderAll();
    setDirty();
    pollTask(data.task.id, node.id).catch(showError);
    await loadTasks();
  }

  function runLocalNode(node) {
    if (node.type === 'loop') {
      node.resultText = renderLoopText(node);
    } else if (node.type === 'output') {
      node.resultText = upstreamNodes(node.id).map(nodeContent).filter(Boolean).join('\n\n') || node.prompt || '';
    } else {
      node.resultText = upstreamContext(node) || node.prompt || '';
    }
    node.status = 'succeeded';
    addLog({ level: 'success', title: '本地节点已完成', detail: `${typeNames[node.type]} -> ${node.title}` });
    renderAll();
    setDirty();
  }

  async function pollTask(taskId, nodeId) {
    for (let i = 0; i < 160; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, i < 4 ? 900 : 1600));
      const data = await api(`/api/tasks/${taskId}`);
      updateAccount({ ...me, credits: data.balance });
      const node = nodeById(nodeId);
      if (node) {
        const before = node.status;
        applyTaskResult(node, data.task);
        if (before !== data.task.status && ['succeeded', 'failed'].includes(data.task.status)) {
          addLog({
            level: data.task.status === 'succeeded' ? 'success' : 'error',
            title: data.task.status === 'succeeded' ? '任务已完成' : '任务失败',
            detail: `${typeNames[node.type]} -> ${node.title}`
          });
        }
        renderAll();
        setDirty();
      }
      if (['succeeded', 'failed'].includes(data.task.status)) {
        await loadTasks();
        await loadAssets();
        return;
      }
    }
    addLog({ level: 'error', title: '任务查询超时', detail: taskId });
  }

  async function runChain() {
    const roots = selectedNodes().filter((node) => node.type !== 'group');
    if (!roots.length) {
      await runSelectedNode();
      return;
    }
    const order = collectRunOrder(roots);
    addLog({ level: 'info', title: '链路开始运行', detail: `${order.length} 个节点` });
    for (const node of order) {
      if (node.type === 'group') continue;
      await runNode(node);
      if (node.status === 'failed') break;
      if (isRemoteRunnable(node)) {
        await waitForNodeDone(node.id);
      }
    }
    addLog({ level: 'success', title: '链路运行完成', detail: `${order.length} 个节点` });
  }
  function collectRunOrder(roots) {
    const seen = new Set();
    const order = [];
    const visit = (node) => {
      if (!node || seen.has(node.id)) return;
      seen.add(node.id);
      order.push(node);
      downstreamNodes(node.id).forEach(visit);
    };
    roots.sort((a, b) => a.x - b.x || a.y - b.y).forEach(visit);
    return order.filter((node) => node.type !== 'group');
  }

  async function waitForNodeDone(nodeId) {
    for (let i = 0; i < 180; i += 1) {
      const node = nodeById(nodeId);
      if (!node || ['succeeded', 'failed'].includes(node.status)) return;
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }

  function taskTargetFor(task) {
    if (task.canvas_id || task.node_id) {
      return { canvasId: task.canvas_id || '', nodeId: task.node_id || '' };
    }
    const node = state.nodes.find((item) => item.taskId === task.id);
    return node ? { canvasId: currentCanvas?.id || '', nodeId: node.id } : null;
  }

  async function resolveTaskTarget(task) {
    const local = taskTargetFor(task);
    if (local) return local;
    if (!task.id) return null;
    const data = await api(`/api/tasks/${task.id}/target`);
    return data.target || null;
  }

  function inspectTask(task) {
    const result = task.result || {};
    const url = findUrl(result);
    const title = task.kind === 'image' ? '生图任务' : task.kind === 'video' ? '视频任务' : task.kind === 'llm' ? 'LLM 任务' : '任务';
    const statusMap = { queued: '排队中', running: '运行中', succeeded: '成功', failed: '失败' };
    const preview = url
      ? (mediaKindForUrl(url, task.kind) === 'video'
        ? `<video class="node-media" src="${escapeHtml(url)}" controls></video>`
        : `<img class="node-media" src="${escapeHtml(url)}" alt="">`)
      : '';
    els.nodeInspector.innerHTML = `
      <div class="inspect-grid">
        <div class="pill-row">
          <span class="pill">${escapeHtml(title)}</span>
          <span class="pill">${escapeHtml(statusMap[task.status] || task.status || '')}</span>
        </div>
        ${preview}
        <label>
          <span class="inspect-label">任务 ID</span>
          <input class="inspect-input" value="${escapeHtml(task.id || '')}" readonly>
        </label>
        <label>
          <span class="inspect-label">内容</span>
          <textarea class="inspect-input inspect-textarea" readonly>${escapeHtml(task.error || task.prompt || '')}</textarea>
        </label>
      </div>
    `;
    scrollPanelIntoView('inspectPanel');
  }

  async function focusTask(task) {
    const target = await resolveTaskTarget(task);
    if (!target) {
      inspectTask(task);
      addLog({ level: 'info', title: '已打开任务详情', detail: task.id || '' });
      return;
    }
    if (target.canvasId && (!currentCanvas || currentCanvas.id !== target.canvasId)) {
      await selectCanvas(target.canvasId);
    }
    const node = target.nodeId ? nodeById(target.nodeId) : state.nodes.find((item) => item.taskId === task.id);
    if (!node) {
      inspectTask(task);
      addLog({ level: 'info', title: '任务没有可定位节点', detail: task.id || '' });
      return;
    }
    if (currentView !== 'canvas') showCanvasPage();
    selectOnly(node.id);
    centerOnNode(node);
  }

  async function loadTasks() {
    const data = await api('/api/tasks');
    const tasks = data.tasks || [];
    if (!tasks.length) {
      els.taskList.innerHTML = `<div class="muted">${labels.noTasks}</div>`;
      return;
    }
    els.taskList.innerHTML = '';
    tasks.slice(0, 18).forEach((task) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('data-task-id', task.id || '');
      button.className = `task-item ${escapeHtml(task.status || '')} is-clickable`;
      const kind = task.kind === 'image' ? '生图' : task.kind === 'video' ? '视频' : task.kind === 'llm' ? 'LLM' : task.kind;
      const statusMap = { queued: '排队中', running: '运行中', succeeded: '成功', failed: '失败' };
      button.innerHTML = `<strong>${escapeHtml(kind)} / ${escapeHtml(statusMap[task.status] || task.status)}</strong><span>${escapeHtml(task.prompt || '').slice(0, 100)}</span>`;
      button.addEventListener('click', () => focusTask(task).catch(showError));
      els.taskList.appendChild(button);
    });
  }

  async function uploadFile(file) {
    if (!file || !currentCanvas || !currentProject) return;
    const body = new FormData();
    body.append('file', file);
    const url = `/api/uploads?project_id=${encodeURIComponent(currentProject.id)}&canvas_id=${encodeURIComponent(currentCanvas.id)}`;
    const data = await api(url, { method: 'POST', body });
    const isVideo = String(file.type || '').startsWith('video/');
    addNode(isVideo ? 'video' : 'image', {
      title: data.asset.name || file.name || (isVideo ? '视频素材' : '图片素材'),
      prompt: file.name || '',
      assetUrl: data.asset.url,
      resultUrl: data.asset.url,
      resultKind: isVideo ? 'video' : 'image',
      assetName: data.asset.name || file.name || ''
    });
    addLog({ level: 'success', title: '文件已上传', detail: file.name || data.asset.name });
    await loadAssets();
  }

  async function loadAssets() {
    const data = await api('/api/assets');
    assetCache = data.assets || [];
    renderAssets();
  }

  function uniqueAssets(items) {
    const seen = new Set();
    return items.filter((asset) => {
      const key = asset.url || asset.id;
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }

  function currentAssetItems() {
    const nodeAssets = state.nodes
      .filter((node) => node.assetUrl || node.resultUrl)
      .map((node) => ({
        id: node.id,
        source: 'node',
        title: node.assetName || node.title,
        url: node.resultUrl || node.assetUrl,
        kind: node.resultKind || mediaKindForUrl(node.resultUrl || node.assetUrl),
        node_id: node.id,
        canvas_id: currentCanvas?.id || '',
        task_id: node.taskId || ''
      }));
    return uniqueAssets([...nodeAssets, ...assetCache]);
  }

  function assetSourceLabel(asset) {
    if (asset.source === 'upload') return '上传素材';
    if (asset.source === 'task') return '生成结果';
    return '当前画布';
  }

  function filteredAssets(assets) {
    const keyword = String(els.assetSearchInput?.value || '').trim().toLowerCase();
    return assets.filter((asset) => {
      const kindOk = assetFilter === 'all'
        || (assetFilter === 'image' && asset.kind === 'image')
        || (assetFilter === 'video' && asset.kind === 'video')
        || (assetFilter === 'upload' && asset.source === 'upload')
        || (assetFilter === 'task' && asset.source === 'task');
      if (!kindOk) return false;
      if (!keyword) return true;
      return [asset.title, asset.kind, asset.source, asset.task_id, asset.node_id]
        .some((value) => String(value || '').toLowerCase().includes(keyword));
    });
  }

  function renderAssetSidebarSummary(assets) {
    if (!assets.length) {
      els.assetList.innerHTML = `
        <div class="asset-sidebar-empty">${labels.noAssets}</div>
        <button class="small-button" type="button" data-open-assets>进入素材库</button>
      `;
    } else {
      const imageCount = assets.filter((asset) => asset.kind === 'image').length;
      const videoCount = assets.filter((asset) => asset.kind === 'video').length;
      els.assetList.innerHTML = `
        <div class="asset-sidebar-summary">
          <strong>${assets.length}</strong>
          <span>素材总数</span>
        </div>
        <div class="asset-sidebar-stats">
          <span>图片 ${imageCount}</span>
          <span>视频 ${videoCount}</span>
        </div>
        <button class="small-button" type="button" data-open-assets>进入素材库</button>
      `;
    }
    els.assetList.querySelector('[data-open-assets]')?.addEventListener('click', () => showAssetPage());
  }

  function renderAssetPreview(asset) {
    if (!asset) {
      els.assetPreviewMeta.textContent = '选择一个素材';
      els.assetPreview.innerHTML = `
        <div class="asset-preview-empty">
          <strong>暂无可预览素材</strong>
          <span>生成或上传素材后会在这里查看详情。</span>
        </div>
      `;
      return;
    }
    els.assetPreviewMeta.textContent = assetSourceLabel(asset);
    const media = asset.kind === 'video'
      ? `<video src="${escapeHtml(asset.url)}" controls></video>`
      : `<img src="${escapeHtml(asset.url)}" alt="">`;
    els.assetPreview.innerHTML = `
      <div class="asset-preview-media">${media}</div>
      <div class="asset-preview-info">
        <strong>${escapeHtml(asset.title || '素材')}</strong>
        <span>${escapeHtml(asset.kind || 'file')} · ${escapeHtml(assetSourceLabel(asset))}</span>
      </div>
      <div class="asset-preview-actions">
        ${asset.node_id || asset.task_id ? '<button class="small-button" type="button" data-preview-focus>定位来源</button>' : ''}
        <a class="small-button" href="${escapeHtml(asset.url)}" target="_blank" rel="noreferrer">打开原图</a>
      </div>
    `;
    els.assetPreview.querySelector('[data-preview-focus]')?.addEventListener('click', () => {
      focusTask({
        id: asset.task_id || '',
        canvas_id: asset.canvas_id || '',
        node_id: asset.node_id || ''
      }).catch(showError);
    });
  }

  function selectAsset(assetId) {
    selectedAssetId = assetId || '';
    renderAssetPage();
  }

  function renderAssetPage() {
    const assets = currentAssetItems();
    const visible = filteredAssets(assets);
    const counts = {
      all: assets.length,
      image: assets.filter((asset) => asset.kind === 'image').length,
      video: assets.filter((asset) => asset.kind === 'video').length,
      task: assets.filter((asset) => asset.source === 'task').length
    };
    els.assetTotalText.textContent = `${counts.all} 个素材`;
    els.assetAllCount.textContent = counts.all;
    els.assetImageCount.textContent = counts.image;
    els.assetVideoCount.textContent = counts.video;
    els.assetTaskCount.textContent = counts.task;
    const titles = { all: '全部素材', image: '图片资产', video: '视频资产', upload: '上传素材', task: '生成结果' };
    els.assetPageTitle.textContent = titles[assetFilter] || '全部素材';
    els.assetPageSubtitle.textContent = `当前筛选 ${visible.length} 个素材`;
    document.querySelectorAll('[data-asset-tab]').forEach((button) => {
      button.classList.toggle('active', button.dataset.assetTab === assetFilter);
    });
    if (!selectedAssetId || !visible.some((asset) => (asset.id || asset.url) === selectedAssetId)) {
      selectedAssetId = visible[0] ? (visible[0].id || visible[0].url) : '';
    }
    if (!visible.length) {
      els.assetGrid.innerHTML = `
        <button class="asset-upload-tile" type="button" data-upload-from-assets>
          <strong>上传到当前分组</strong>
          <span>也可以从生成节点输出保存到素材库。</span>
        </button>
        <div class="asset-empty-wide">当前筛选下暂无素材。</div>
      `;
      els.assetGrid.querySelector('[data-upload-from-assets]')?.addEventListener('click', () => els.fileInput.click());
      renderAssetPreview(null);
      return;
    }
    els.assetGrid.innerHTML = visible.map((asset) => {
      const id = asset.id || asset.url;
      const active = id === selectedAssetId;
      return `
        <button class="asset-card${active ? ' active' : ''}" type="button" data-asset-id="${escapeHtml(id)}">
          <span class="asset-card-media">
            ${asset.kind === 'video'
              ? `<video src="${escapeHtml(asset.url)}" muted></video>`
              : `<img src="${escapeHtml(asset.url)}" alt="">`}
          </span>
          <strong>${escapeHtml(asset.title || '素材')}</strong>
          <small>${escapeHtml(assetSourceLabel(asset))}</small>
        </button>
      `;
    }).join('');
    els.assetGrid.querySelectorAll('[data-asset-id]').forEach((button) => {
      button.addEventListener('click', () => {
        selectAsset(button.dataset.assetId || '');
      });
    });
    renderAssetPreview(visible.find((asset) => (asset.id || asset.url) === selectedAssetId) || visible[0]);
  }

  function renderAssets() {
    const assets = currentAssetItems();
    renderAssetSidebarSummary(assets);
    renderAssetPage();
  }

  function showCanvasPage() {
    currentView = 'canvas';
    els.assetPage.classList.add('hidden');
    els.canvasArea.classList.remove('hidden');
    els.assetBtn.classList.remove('active');
    els.canvasTitle.textContent = currentCanvas?.name || labels.canvas;
    applyViewport();
    renderEdges();
    scheduleMinimapRender();
  }

  async function showAssetPage() {
    currentView = 'assets';
    await loadAssets();
    els.canvasArea.classList.add('hidden');
    els.assetPage.classList.remove('hidden');
    els.assetBtn.classList.add('active');
    els.canvasTitle.textContent = '素材库管理';
    renderAssetPage();
  }

  function addLog(entry) {
    if (!state.logs) state.logs = [];
    state.logs.push({
      id: uid('log'),
      at: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
      level: entry.level || 'info',
      title: entry.title || '日志',
      detail: entry.detail || ''
    });
    state.logs = state.logs.slice(-80);
    renderLogs();
  }

  function renderLogs() {
    const logs = state.logs || [];
    if (!logs.length) {
      els.logList.innerHTML = `<div class="muted">${labels.noLogs}</div>`;
      return;
    }
    els.logList.innerHTML = logs.slice().reverse().map((log) => `
      <div class="log-item ${escapeHtml(log.level)}">
        <strong>${escapeHtml(log.title)}<span>${escapeHtml(log.at)}</span></strong>
        <p>${escapeHtml(log.detail)}</p>
      </div>
    `).join('');
  }

  function workflowPayload(selectedOnly = true) {
    const selected = new Set(selectedIds);
    const nodes = selectedOnly && selected.size
      ? state.nodes.filter((node) => selected.has(node.id))
      : state.nodes.filter((node) => node.type !== 'group');
    const ids = new Set(nodes.map((node) => node.id));
    return {
      version: 1,
      name: currentCanvas?.name || labels.canvas,
      exported_at: new Date().toISOString(),
      nodes,
      edges: state.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target))
    };
  }

  function renderWorkflowSummary() {
    const payload = workflowPayload(true);
    const total = payload.nodes.length;
    const edges = payload.edges.length;
    const byType = payload.nodes.reduce((acc, node) => {
      acc[node.type] = (acc[node.type] || 0) + 1;
      return acc;
    }, {});
    els.workflowSummary.innerHTML = `
      <div class="workflow-stat"><strong>${total}</strong><span>${selectedIds.size ? '选中节点' : '画布节点'}</span></div>
      <div class="workflow-stat"><strong>${edges}</strong><span>连线</span></div>
      <div class="workflow-types">${Object.entries(byType).map(([type, count]) => `<span>${escapeHtml(typeNames[type] || type)} ${count}</span>`).join('') || '<span>暂无节点</span>'}</div>
    `;
  }

  function exportWorkflow() {
    const payload = workflowPayload(true);
    const text = JSON.stringify(payload, null, 2);
    const blob = new Blob([text], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${(payload.name || 'canvas-workflow').replace(/[\\/:*?"<>|]+/g, '-')}.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    addLog({ level: 'success', title: '工作流已导出', detail: `${payload.nodes.length} 个节点` });
  }

  async function copyWorkflowSummary() {
    const payload = workflowPayload(true);
    const summary = payload.nodes.map((node, index) => `${index + 1}. ${typeNames[node.type] || node.type} -> ${node.title}`).join('\n');
    await copyText(summary || '暂无节点');
    addLog({ level: 'success', title: '工作流摘要已复制', detail: `${payload.nodes.length} 个节点` });
  }

  async function copyText(text) {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand('copy');
    textarea.remove();
  }
  function centerOnNode(node) {
    const rect = els.canvasArea.getBoundingClientRect();
    state.viewport.x = rect.width / 2 - (node.x + node.w / 2) * state.viewport.scale;
    state.viewport.y = rect.height / 2 - (node.y + node.h / 2) * state.viewport.scale;
    applyViewport();
    renderEdges();
  }

  function scrollPanelIntoView(id) {
    document.getElementById(id)?.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }

  function hideAddMenu() {
    addMenuWorldPoint = null;
    els.addMenu.classList.add('hidden');
  }

  function showAddMenu(event) {
    if (event.target.closest('.node,.group-node,.toolbar,.canvas-minimap,.add-menu')) return;
    event.preventDefault();
    const canvasPoint = clientToCanvas(event.clientX, event.clientY);
    addMenuWorldPoint = clientToWorld(event.clientX, event.clientY);
    const left = clamp(canvasPoint.x, 12, Math.max(12, els.canvasArea.clientWidth - 202));
    const top = clamp(canvasPoint.y, 12, Math.max(12, els.canvasArea.clientHeight - 250));
    els.addMenu.style.left = `${left}px`;
    els.addMenu.style.top = `${top}px`;
    els.addMenu.classList.remove('hidden');
  }

  function addNodeFromMenu(type) {
    const point = addMenuWorldPoint || centerWorldPoint();
    addNode(type, { x: point.x, y: point.y });
    hideAddMenu();
  }

  function zoomAtCanvasPoint(canvasX, canvasY, nextScale) {
    const rect = els.canvasArea.getBoundingClientRect();
    const before = clientToWorld(rect.left + canvasX, rect.top + canvasY);
    const scale = clamp(nextScale, MIN_ZOOM, MAX_ZOOM);
    state.viewport.scale = scale;
    state.viewport.x = canvasX - before.x * scale;
    state.viewport.y = canvasY - before.y * scale;
    applyViewport();
    revealMinimap();
    setDirty();
  }

  function zoomBy(factor) {
    const rect = els.canvasArea.getBoundingClientRect();
    zoomAtCanvasPoint(rect.width / 2, rect.height / 2, state.viewport.scale * factor);
  }

  function centerViewportOnWorld(worldX, worldY) {
    const rect = els.canvasArea.getBoundingClientRect();
    state.viewport.x = rect.width / 2 - worldX * state.viewport.scale;
    state.viewport.y = rect.height / 2 - worldY * state.viewport.scale;
    applyViewport();
    revealMinimap();
    setDirty();
  }

  function worldPointFromMinimap(clientX, clientY) {
    if (!minimapLayout) renderMinimap();
    if (!minimapLayout) return null;
    const rect = els.minimapView.getBoundingClientRect();
    const { bounds, scale, offsetX, offsetY } = minimapLayout;
    return {
      x: bounds.x + (clientX - rect.left - offsetX) / scale,
      y: bounds.y + (clientY - rect.top - offsetY) / scale
    };
  }

  function bindMinimapEvents() {
    const recenter = (event) => {
      const point = worldPointFromMinimap(event.clientX, event.clientY);
      if (point) centerViewportOnWorld(point.x, point.y);
    };
    els.minimapView.addEventListener('pointerdown', (event) => {
      event.preventDefault();
      revealMinimap(0);
      els.minimapView.setPointerCapture?.(event.pointerId);
      recenter(event);
      const onMove = (moveEvent) => recenter(moveEvent);
      const onUp = () => {
        els.minimapView.releasePointerCapture?.(event.pointerId);
        window.removeEventListener('pointermove', onMove);
        revealMinimap();
      };
      window.addEventListener('pointermove', onMove);
      window.addEventListener('pointerup', onUp, { once: true });
    });
  }

  function handleWheel(event) {
    event.preventDefault();
    const point = clientToCanvas(event.clientX, event.clientY);
    zoomAtCanvasPoint(point.x, point.y, state.viewport.scale * Math.exp(-event.deltaY * 0.0012));
  }

  function bindEvents() {
    els.toolbar.querySelectorAll('[data-add]').forEach((button) => {
      button.addEventListener('click', () => {
        if (currentView !== 'canvas') showCanvasPage();
        addNode(button.dataset.add);
      });
    });
    els.addMenu.querySelectorAll('[data-add-menu]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        addNodeFromMenu(button.dataset.addMenu);
      });
    });
    els.groupBtn.addEventListener('click', groupSelected);
    els.runBtn.addEventListener('click', () => runSelectedNode().catch(showError));
    els.runChainBtn.addEventListener('click', () => runChain().catch(showError));
    els.saveBtn.addEventListener('click', () => saveCanvas().catch(showError));
    els.workflowBtn.addEventListener('click', () => scrollPanelIntoView('workflowPanel'));
    els.assetBtn.addEventListener('click', () => showAssetPage().catch(showError));
    els.logBtn.addEventListener('click', () => scrollPanelIntoView('logPanel'));
    els.refreshAssetBtn.addEventListener('click', () => loadAssets().catch(showError));
    els.assetPageRefreshBtn.addEventListener('click', () => loadAssets().catch(showError));
    els.assetBackBtn.addEventListener('click', showCanvasPage);
    els.assetSearchInput.addEventListener('input', renderAssetPage);
    document.querySelectorAll('[data-asset-tab]').forEach((button) => {
      button.addEventListener('click', () => {
        assetFilter = button.dataset.assetTab || 'all';
        renderAssetPage();
      });
    });
    els.clearLogBtn.addEventListener('click', () => {
      state.logs = [];
      renderLogs();
      setDirty();
    });
    els.exportWorkflowBtn.addEventListener('click', exportWorkflow);
    els.copyWorkflowBtn.addEventListener('click', () => copyWorkflowSummary().catch(showError));
    els.backToOriginBtn.addEventListener('click', () => {
      if (currentView !== 'canvas') {
        showCanvasPage();
        return;
      }
      state.viewport = { x: 120, y: 80, scale: 1 };
      applyViewport();
      setDirty();
    });
    els.zoomOutBtn.addEventListener('click', () => zoomBy(1 / 1.25));
    els.zoomResetBtn.addEventListener('click', () => {
      const rect = els.canvasArea.getBoundingClientRect();
      zoomAtCanvasPoint(rect.width / 2, rect.height / 2, 1);
    });
    els.zoomInBtn.addEventListener('click', () => zoomBy(1.25));
    bindMinimapEvents();
    els.minimap.addEventListener('mouseenter', () => revealMinimap(0));
    els.minimap.addEventListener('mouseleave', () => revealMinimap());
    els.zoomChip.addEventListener('mouseenter', () => revealMinimap(2200));
    els.uploadBtn.addEventListener('click', () => els.fileInput.click());
    els.fileInput.addEventListener('change', () => {
      const file = els.fileInput.files && els.fileInput.files[0];
      els.fileInput.value = '';
      uploadFile(file).catch(showError);
    });
    els.canvasArea.addEventListener('wheel', (event) => {
      hideAddMenu();
      handleWheel(event);
    }, { passive: false });
    els.canvasArea.addEventListener('dblclick', showAddMenu);
    els.canvasArea.addEventListener('pointerdown', (event) => {
      if (event.target.closest('.node,.group-node,.toolbar,.canvas-minimap,.add-menu')) return;
      hideAddMenu();
      els.canvasArea.focus();
      if (event.button === 1 || spaceDown) startPan(event);
      else if (event.button === 0) startMarquee(event);
    });
    els.canvasArea.addEventListener('dragover', (event) => event.preventDefault());
    els.canvasArea.addEventListener('drop', (event) => {
      event.preventDefault();
      const file = event.dataTransfer.files && event.dataTransfer.files[0];
      uploadFile(file).catch(showError);
    });
    els.newProjectBtn.addEventListener('click', async () => {
      const name = window.prompt('新项目名称', labels.defaultProject);
      if (!name) return;
      await saveCurrentCanvasIfDirty();
      const data = await api('/api/projects', { method: 'POST', body: JSON.stringify({ name }) });
      projects.unshift(data.project);
      await selectProject(data.project.id);
    });
    els.newCanvasBtn.addEventListener('click', async () => {
      if (!currentProject) return;
      const name = window.prompt('新画布名称', labels.canvasName);
      if (!name) return;
      await saveCurrentCanvasIfDirty();
      const data = await api(`/api/projects/${currentProject.id}/canvases`, { method: 'POST', body: JSON.stringify({ name }) });
      canvases.unshift(data.canvas);
      await selectCanvas(data.canvas.id);
    });
    els.accountBtn.addEventListener('click', () => els.accountModal.classList.remove('hidden'));
    els.closeAccount.addEventListener('click', () => els.accountModal.classList.add('hidden'));
    els.logoutBtn.addEventListener('click', async () => {
      await api('/api/auth/logout', { method: 'POST', body: JSON.stringify({}) });
      location.href = '/login';
    });
    window.addEventListener('keydown', (event) => {
      const editing = event.target && ['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName);
      if (event.code === 'Space' && !editing) {
        spaceDown = true;
        event.preventDefault();
      }
      if (event.key === 'Escape') hideAddMenu();
      if (editing) return;
      if ((event.key === 'Delete' || event.key === 'Backspace') && selectedIds.size) {
        event.preventDefault();
        deleteSelected();
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'g') {
        event.preventDefault();
        groupSelected();
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        saveCanvas().catch(showError);
      }
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        runChain().catch(showError);
      }
    });
    window.addEventListener('keyup', (event) => {
      if (event.code === 'Space') spaceDown = false;
    });
    window.addEventListener('resize', () => {
      renderEdges();
      scheduleMinimapRender();
    });
    window.addEventListener('beforeunload', (event) => {
      if (!dirty) return;
      event.preventDefault();
      event.returnValue = '';
    });
  }
  async function init() {
    syncWorldSize();
    bindEvents();
    applyViewport();
    try {
      const user = await loadMe();
      if (!user) return;
      await loadProjects();
    } catch (error) {
      showError(error);
    }
  }

  init();
})();
