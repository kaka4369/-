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
    directorPrompt: '粘贴剧本、项目设定、产品卖点或角色世界观。导演台会拆出角色、场景、物品、情节线、分镜和视频任务。',
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
    runNode: '运行',
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
    director: '导演台',
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
  const THEME_STORAGE_KEY = 'canvas-saas-theme';

  function readSavedTheme() {
    try {
      return localStorage.getItem(THEME_STORAGE_KEY) === 'dark' ? 'dark' : 'light';
    } catch (error) {
      return 'light';
    }
  }

  function writeSavedTheme(theme) {
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch (error) {
      // Ignore storage failures; theme still works for the current page.
    }
  }

  const els = {
    appShell: document.querySelector('.app-shell'),
    accountBackBtn: document.getElementById('accountBackBtn'),
    accountBtn: document.getElementById('accountBtn'),
    accountEmail: document.getElementById('accountEmail'),
    accountLine: document.getElementById('accountLine'),
    accountModal: document.getElementById('accountModal'),
    accountPage: document.getElementById('accountPage'),
    accountPageAdminLink: document.getElementById('accountPageAdminLink'),
    accountPageCredits: document.getElementById('accountPageCredits'),
    accountPageEmail: document.getElementById('accountPageEmail'),
    accountPageLogoutBtn: document.getElementById('accountPageLogoutBtn'),
    accountPageRole: document.getElementById('accountPageRole'),
    accountStorageBar: document.getElementById('accountStorageBar'),
    accountStorageLimit: document.getElementById('accountStorageLimit'),
    accountStorageUsed: document.getElementById('accountStorageUsed'),
    addMenu: document.getElementById('addMenu'),
    adminLink: document.getElementById('adminLink'),
    assetAllCount: document.getElementById('assetAllCount'),
    assetBackBtn: document.getElementById('assetBackBtn'),
    assetBtn: document.getElementById('assetBtn'),
    assetDrawer: document.getElementById('assetDrawer'),
    assetDrawerCloseBtn: document.getElementById('assetDrawerCloseBtn'),
    assetDrawerCount: document.getElementById('assetDrawerCount'),
    assetDrawerGrid: document.getElementById('assetDrawerGrid'),
    assetDrawerSearch: document.getElementById('assetDrawerSearch'),
    assetDrawerUploadBtn: document.getElementById('assetDrawerUploadBtn'),
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
    canvasCreateCancelBtn: document.getElementById('canvasCreateCancelBtn'),
    canvasCreateCloseBtn: document.getElementById('canvasCreateCloseBtn'),
    canvasCreateForm: document.getElementById('canvasCreateForm'),
    canvasCreateModal: document.getElementById('canvasCreateModal'),
    canvasList: document.getElementById('canvasList'),
    canvasNameInput: document.getElementById('canvasNameInput'),
    confirmPasswordInput: document.getElementById('confirmPasswordInput'),
    currentPasswordInput: document.getElementById('currentPasswordInput'),
    canvasTitle: document.getElementById('canvasTitle'),
    clearLogBtn: document.getElementById('clearLogBtn'),
    closeAccount: document.getElementById('closeAccount'),
    copyWorkflowBtn: document.getElementById('copyWorkflowBtn'),
    creditText: document.getElementById('creditText'),
    directorRecipeBtn: document.getElementById('directorRecipeBtn'),
    edgeLayer: document.getElementById('edgeLayer'),
    emptyHint: document.getElementById('emptyHint'),
    exportWorkflowBtn: document.getElementById('exportWorkflowBtn'),
    fileInput: document.getElementById('fileInput'),
    groupBtn: document.getElementById('groupBtn'),
    logBtn: document.getElementById('logBtn'),
    logList: document.getElementById('logList'),
    logsBackBtn: document.getElementById('logsBackBtn'),
    logsPage: document.getElementById('logsPage'),
    logsPageClearBtn: document.getElementById('logsPageClearBtn'),
    logsPageList: document.getElementById('logsPageList'),
    logoutBtn: document.getElementById('logoutBtn'),
    minimap: document.getElementById('minimap'),
    minimapContent: document.getElementById('minimapContent'),
    minimapView: document.getElementById('minimapView'),
    minimapViewport: document.getElementById('minimapViewport'),
    minimapZoom: document.getElementById('minimapZoom'),
    mediaPreviewImage: document.getElementById('mediaPreviewImage'),
    mediaPreviewModal: document.getElementById('mediaPreviewModal'),
    modalCredits: document.getElementById('modalCredits'),
    modalRole: document.getElementById('modalRole'),
    newCanvasBtn: document.getElementById('newCanvasBtn'),
    newProjectBtn: document.getElementById('newProjectBtn'),
    nodeInspector: document.getElementById('nodeInspector'),
    nodeLayer: document.getElementById('nodeLayer'),
    newPasswordInput: document.getElementById('newPasswordInput'),
    passwordChangeForm: document.getElementById('passwordChangeForm'),
    canvasCurrentName: document.getElementById('canvasCurrentName'),
    projectCurrentName: document.getElementById('projectCurrentName'),
    projectList: document.getElementById('projectList'),
    refreshAssetBtn: document.getElementById('refreshAssetBtn'),
    runBtn: document.getElementById('runBtn'),
    runChainBtn: document.getElementById('runChainBtn'),
    saveBtn: document.getElementById('saveBtn'),
    saveWorkflowTemplateBtn: document.getElementById('saveWorkflowTemplateBtn'),
    saveState: document.getElementById('saveState'),
    selectionBox: document.getElementById('selectionBox'),
    taskList: document.getElementById('taskList'),
    themeToggleBtn: document.getElementById('themeToggleBtn'),
    toolbar: document.querySelector('.toolbar'),
    toastRegion: document.getElementById('toastRegion'),
    uploadBtn: document.getElementById('uploadBtn'),
    viewportPan: document.getElementById('viewportPan'),
    workflowTemplateList: document.getElementById('workflowTemplateList'),
    workflowSummary: document.getElementById('workflowSummary'),
    world: document.getElementById('world'),
    worldScale: document.getElementById('worldScale'),
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
  let selectedEdgeId = '';
  let draftEdge = null;
  let edgeRaf = 0;
  let minimapRaf = 0;
  let progressTimer = null;
  let minimapRevealTimer = null;
  let minimapLayout = null;
  let assetCache = [];
  let assetFilter = 'all';
  let workflowTemplates = [];
  let selectedAssetId = '';
  let currentView = 'canvas';
  let generationCapabilities = {};
  let activeEdgeCleanup = null;
  let addMenuWorldPoint = null;
  let pendingEdgeConnection = null;
  let dirty = false;
  let dirtyVersion = 0;
  let savingInFlight = null;
  const nodeRunsInFlight = new Set();
  let chainRunInFlight = false;
  let spaceDown = false;
  let activeDrag = null;
  let panMomentumRaf = 0;
  let activeViewAnimation = null;
  let activeGroupRenameId = '';
  let suppressNextMediaPreviewClick = false;

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

  function providerOptionHtml(kind, options, selected) {
    const providers = generationCapabilities?.[kind]?.providers || {};
    return options.map((item) => {
      const known = Object.prototype.hasOwnProperty.call(providers, item);
      const disabled = known && !providers[item]?.configured;
      const suffix = disabled ? '（未配置）' : '';
      return `<option value="${escapeHtml(item)}"${item === selected ? ' selected' : ''}${disabled ? ' disabled' : ''}>${escapeHtml(item + suffix)}</option>`;
    }).join('');
  }

  function applyGenerationCapabilities() {
    ['llm', 'image', 'video'].forEach((kind) => {
      const configured = !!generationCapabilities?.[kind]?.configured;
      document.querySelectorAll(`[data-add="${kind}"], [data-dock-add="${kind}"]`).forEach((button) => {
        const message = `${typeNames[kind]}服务尚未配置，可先添加和编辑，运行前需配置`;
        button.disabled = false;
        button.setAttribute('data-capability-disabled', 'false');
        button.setAttribute('data-capability-configured', configured ? 'true' : 'false');
        if (configured) button.removeAttribute('aria-describedby');
        else button.setAttribute('aria-describedby', 'capabilitySetupHint');
        button.title = configured ? '' : message;
      });
    });
  }

  async function loadGenerationCapabilities() {
    const data = await api('/api/capabilities');
    generationCapabilities = data.generation || {};
    applyGenerationCapabilities();
    return generationCapabilities;
  }

  function nodeCapability(node) {
    const kind = node?.type === 'director' ? 'llm' : node?.type;
    if (!['llm', 'image', 'video'].includes(kind)) return { configured: true };
    const provider = node?.type === 'llm' || node?.type === 'director' ? node.llmProvider : node.apiProvider;
    const providerState = generationCapabilities?.[kind]?.providers?.[provider];
    return providerState || generationCapabilities?.[kind] || { configured: false };
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
    if (!res.ok) {
      const error = new Error(data.detail || data.message || labels.failed);
      error.status = res.status;
      throw error;
    }
    return data;
  }

  function showError(error) {
    const message = error?.message || String(error || '未知错误');
    addLog({ level: 'error', title: '请求失败', detail: message });
    showToast(message, 'error');
  }

  function showToast(message, tone = 'info') {
    if (!els.toastRegion) return;
    const toast = document.createElement('div');
    toast.className = `toast-message ${tone}`;
    toast.setAttribute('role', tone === 'error' ? 'alert' : 'status');
    toast.textContent = String(message || labels.failed);
    els.toastRegion.appendChild(toast);
    window.setTimeout(() => {
      toast.remove();
    }, 4200);
  }
  function setDirty(value = true) {
    if (value) dirtyVersion += 1;
    dirty = !!value;
    els.saveState.textContent = value ? labels.unsaved : labels.saved;
  }

  function defaultSize(type) {
    if (type === 'group') return { w: 540, h: 340 };
    if (type === 'director') return { w: 760, h: 620 };
    if (type === 'llm') return { w: 390, h: 340 };
    if (type === 'image') return { w: 520, h: 780 };
    if (type === 'video') return { w: 520, h: 780 };
    if (type === 'output') return { w: 340, h: 270 };
    if (type === 'loop') return { w: 340, h: 300 };
    return { w: 460, h: 380 };
  }

  function minSize(type) {
    if (type === 'group') return { w: 180, h: 120 };
    if (type === 'director') return { w: 560, h: 420 };
    if (type === 'image') return { w: 360, h: 460 };
    if (type === 'video') return { w: 360, h: 430 };
    return { w: 240, h: 180 };
  }

  function defaultPrompt(type) {
    if (type === 'director') return labels.directorPrompt;
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
    if (type === 'director') {
      return {
        llmProvider: nodePresets.llmProviders[0],
        model: nodePresets.llmModels[0],
        aspectRatio: '9:16',
        activeTab: 'overview',
        directorResult: null,
        outputText: ''
      };
    }
    return {};
  }

  function normalizeNode(raw) {
    const source = raw && typeof raw === 'object' ? raw : {};
    const type = source.type || 'prompt';
    const size = defaultSize(type);
    const minimum = minSize(type);
    const defaults = defaultsForType(type);
    const node = {
      ...defaults,
      ...source,
      id: source.id || uid(type),
      type,
      title: source.title || typeNames[type] || 'Node',
      x: safeNumber(source.x, 0),
      y: safeNumber(source.y, 0),
      w: clamp(safeNumber(source.w, size.w), minimum.w, 1400),
      h: clamp(safeNumber(source.h, size.h), minimum.h, 1400),
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
    if (type === 'director') {
      node.llmProvider = node.llmProvider || nodePresets.llmProviders[0];
      node.model = node.model || nodePresets.llmModels[0];
      node.aspectRatio = node.aspectRatio || '9:16';
      node.activeTab = node.activeTab || 'overview';
      node.directorResult = normalizeDirectorResult(source.directorResult || node.directorResult);
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
    selectedEdgeId = '';
    renderSelection();
  }

  function toggleSelect(id) {
    selectedEdgeId = '';
    if (selectedIds.has(id)) selectedIds.delete(id);
    else selectedIds.add(id);
    renderSelection();
  }

  function selectMany(ids) {
    selectedIds = new Set(ids);
    selectedEdgeId = '';
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

  function updateCanvasSpotlight(event) {
    const point = clientToCanvas(event.clientX, event.clientY);
    els.canvasArea.style.setProperty('--spotlight-x', `${point.x}px`);
    els.canvasArea.style.setProperty('--spotlight-y', `${point.y}px`);
    els.canvasArea.classList.add('pointer-lit');
  }

  function clearCanvasSpotlight() {
    els.canvasArea.classList.remove('pointer-lit');
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

  function canvasGridSize(scale) {
    let size = 28 * Math.max(scale, MIN_ZOOM);
    while (size > 84) size /= 2;
    return clamp(size, 10, 84);
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
    const gridSize = canvasGridSize(scale);
    els.viewportPan.style.transform = `translate3d(${x}px, ${y}px, 0)`;
    els.worldScale.style.zoom = String(scale);
    els.world.style.transform = 'none';
    els.canvasArea.style.setProperty('--grid-size', `${gridSize}px`);
    els.canvasArea.style.setProperty('--grid-x', `${x % gridSize}px`);
    els.canvasArea.style.setProperty('--grid-y', `${y % gridSize}px`);
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

  function applyTheme(theme, options = {}) {
    const normalized = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.dataset.theme = normalized;
    document.documentElement.style.colorScheme = normalized === 'dark' ? 'dark' : 'light';
    if (els.themeToggleBtn) {
      const dark = normalized === 'dark';
      const label = els.themeToggleBtn.querySelector('span');
      const icon = els.themeToggleBtn.querySelector('i.ph');
      if (label) label.textContent = dark ? '白天' : '黑夜';
      if (icon) {
        icon.classList.toggle('ph-sun', dark);
        icon.classList.toggle('ph-moon', !dark);
      }
      els.themeToggleBtn.setAttribute('aria-pressed', dark ? 'true' : 'false');
      els.themeToggleBtn.setAttribute('aria-label', dark ? '切换到白天模式' : '切换到黑夜模式');
      els.themeToggleBtn.title = dark ? '切换到白天模式' : '切换到黑夜模式';
    }
    if (options.persist) writeSavedTheme(normalized);
  }

  function toggleTheme() {
    const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
    applyTheme(next, { persist: true });
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
    if (els.accountPageEmail) els.accountPageEmail.textContent = user.email || labels.account;
    if (els.accountPageCredits) els.accountPageCredits.textContent = user.credits || 0;
    if (els.accountPageRole) els.accountPageRole.textContent = user.is_admin ? labels.admin : labels.user;
    if (els.accountPageAdminLink) els.accountPageAdminLink.classList.toggle('hidden', !user.is_admin);
  }

  function formatStorageBytes(value) {
    const bytes = Math.max(0, Number(value) || 0);
    if (bytes < 1024) return `${Math.round(bytes)} B`;
    const units = ['KB', 'MB', 'GB', 'TB'];
    let amount = bytes / 1024;
    let unit = units[0];
    for (let index = 1; index < units.length && amount >= 1024; index += 1) {
      amount /= 1024;
      unit = units[index];
    }
    return `${amount >= 10 ? amount.toFixed(1) : amount.toFixed(2)} ${unit}`;
  }

  function updateStorageSummary(storage) {
    if (!storage) return;
    if (els.accountStorageUsed) els.accountStorageUsed.textContent = formatStorageBytes(storage.used_bytes);
    if (els.accountStorageLimit) els.accountStorageLimit.textContent = formatStorageBytes(storage.limit_bytes);
    if (els.accountStorageBar) els.accountStorageBar.style.width = `${Math.max(0, Math.min(100, Number(storage.percent) || 0))}%`;
  }

  async function loadMe() {
    const data = await api('/api/me');
    if (!data.user) {
      location.href = '/login';
      return null;
    }
    updateAccount(data.user);
    updateStorageSummary(data.storage);
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
    cancelPanMomentum();
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
    cancelPanMomentum();
    if (currentCanvas && currentCanvas.id !== canvasId) await saveCurrentCanvasIfDirty();
    const data = await api(`/api/canvases/${canvasId}`);
    cancelPanMomentum();
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
    await loadWorkflowTemplates();
  }

  function renderProjects() {
    if (els.projectCurrentName) {
      els.projectCurrentName.textContent = currentProject?.name || labels.noProject;
    }
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
    if (els.canvasCurrentName) {
      els.canvasCurrentName.textContent = currentCanvas?.name || labels.noCanvas;
    }
    els.canvasList.innerHTML = canvases.length ? '' : `<div class="muted">${labels.noCanvas}</div>`;
    canvases.forEach((canvas) => {
      const button = document.createElement('button');
      button.className = `nav-item${currentCanvas && currentCanvas.id === canvas.id ? ' active' : ''}`;
      button.innerHTML = `<span>${escapeHtml(canvas.name)}</span><small>${labels.canvas}</small>`;
      button.addEventListener('click', () => selectCanvas(canvas.id).catch(showError));
      els.canvasList.appendChild(button);
    });
  }

  function nextNodePlacement(size) {
    const center = centerWorldPoint();
    const origin = {
      x: center.x - size.w / 2,
      y: center.y - size.h / 2
    };
    const scale = Math.max(state.viewport.scale || 1, MIN_ZOOM);
    const gap = 20 / scale;
    const horizontalStep = size.w + gap;
    const verticalStep = size.h + gap;
    const offsets = [[0, 0]];
    for (let ring = 1; ring <= 4; ring += 1) {
      offsets.push(
        [0, ring], [ring, 0], [0, -ring], [-ring, 0],
        [ring, ring], [-ring, ring], [ring, -ring], [-ring, -ring]
      );
    }
    for (const [offsetX, offsetY] of offsets) {
      const candidate = {
        x: origin.x + offsetX * horizontalStep,
        y: origin.y + offsetY * verticalStep
      };
      const occupied = state.nodes.some((node) => (
        candidate.x < node.x + node.w + gap
        && candidate.x + size.w + gap > node.x
        && candidate.y < node.y + node.h + gap
        && candidate.y + size.h + gap > node.y
      ));
      if (!occupied) return candidate;
    }
    return { x: origin.x, y: origin.y + verticalStep * 5 };
  }

  function fitNewNodeInCanvas(node) {
    if (!node) return;
    const rect = els.canvasArea.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const dock = els.canvasArea.querySelector('.canvas-create-dock');
    const dockHeight = dock?.getBoundingClientRect().height || 0;
    const padding = 24;
    const usableWidth = Math.max(120, rect.width - padding);
    const usableHeight = Math.max(180, rect.height - dockHeight - padding * 2);
    const fitScale = Math.min(1, usableWidth / node.w, usableHeight / node.h);
    const currentScale = state.viewport.scale || 1;
    const targetScale = clamp(Math.min(currentScale, fitScale), MIN_ZOOM, MAX_ZOOM);
    if (targetScale < currentScale - 0.001) state.viewport.scale = targetScale;
    const visibleCenterY = Math.max(padding, (rect.height - dockHeight) / 2);
    const appliedScale = state.viewport.scale || targetScale;
    state.viewport.x = rect.width / 2 - (node.x + node.w / 2) * appliedScale;
    state.viewport.y = visibleCenterY - (node.y + node.h / 2) * appliedScale;
    applyViewport();
  }

  function addNode(type, patch = {}) {
    const size = defaultSize(type);
    const hasExplicitPosition = Number.isFinite(patch.x) && Number.isFinite(patch.y);
    const position = nextNodePlacement(size);
    if (hasExplicitPosition) {
      position.x = patch.x;
      position.y = patch.y;
    }
    const node = normalizeNode({
      id: uid(type),
      type,
      x: position.x,
      y: position.y,
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
    if (!hasExplicitPosition) fitNewNodeInCanvas(node);
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
    if (compact) return `<img class="node-media compact" src="${safe}" alt="asset" loading="lazy" draggable="false" />`;
    return `
      <button class="node-media-preview" type="button" data-preview-media="${safe}" aria-label="查看完整图片" draggable="false">
        <img class="node-media" src="${safe}" alt="asset" loading="lazy" draggable="false" />
      </button>
    `;
  }

  function renderNodes() {
    els.nodeLayer.innerHTML = '';
    const groups = state.nodes.filter((node) => node.type === 'group');
    const regular = state.nodes.filter((node) => node.type !== 'group');
    groups.forEach(renderGroupNode);
    regular.forEach(renderRegularNode);
    requestAnimationFrame(() => {
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

  function renameGroup(node) {
    if (!node || node.type !== 'group') return;
    activeGroupRenameId = node.id;
    renderNodes();
    renderInspector();
    window.setTimeout(() => {
      const element = nodeElement(node.id);
      const input = element?.querySelector('[data-group-rename-input]');
      input?.focus();
      input?.select();
    }, 0);
  }

  function commitGroupRename(node, value) {
    if (!node || node.type !== 'group' || activeGroupRenameId !== node.id) return;
    activeGroupRenameId = '';
    const cleanName = String(value || '').trim().slice(0, 80);
    if (cleanName && cleanName !== node.title) {
      node.title = cleanName;
      addLog({ level: 'info', title: '分组已重命名', detail: node.title });
      setDirty();
    }
    renderNodes();
    renderInspector();
    renderWorkflowSummary();
  }

  function cancelGroupRename(node) {
    if (!node || node.type !== 'group' || activeGroupRenameId !== node.id) return;
    activeGroupRenameId = '';
    renderNodes();
    renderInspector();
  }

  function renderGroupNode(node) {
    const element = document.createElement('section');
    element.className = `group-node${selectedIds.has(node.id) ? ' selected' : ''}`;
    element.dataset.nodeId = node.id;
    element.style.setProperty('--x', `${node.x}px`);
    element.style.setProperty('--y', `${node.y}px`);
    element.style.setProperty('--w', `${node.w}px`);
    element.style.setProperty('--h', `${node.h}px`);
    const renaming = activeGroupRenameId === node.id;
    element.innerHTML = `
      <div class="group-label">
        ${renaming
          ? `<input class="group-rename-input" data-group-rename-input value="${escapeHtml(node.title || typeNames.group)}" maxlength="80" aria-label="分组名称" />`
          : `<div class="group-title">${escapeHtml(node.title || typeNames.group)}</div>
             <button class="group-rename" type="button" data-group-action="rename" title="重命名分组" aria-label="重命名分组">改名</button>`}
      </div>
      <div class="group-count">${groupChildren(node).length} 个节点</div>
      <div class="group-resize" title="调整分组大小"></div>
    `;
    const groupTitle = element.querySelector('.group-title');
    if (groupTitle) {
      groupTitle.addEventListener('pointerdown', (event) => startNodeDrag(event, node, true));
      element.querySelector('.group-title').addEventListener('dblclick', (event) => {
        event.preventDefault();
        event.stopPropagation();
        renameGroup(node);
      });
    }
    const renameButton = element.querySelector('[data-group-action="rename"]');
    if (renameButton) {
      renameButton.addEventListener('pointerdown', (event) => event.stopPropagation());
      renameButton.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        renameGroup(node);
      });
    }
    const renameInput = element.querySelector('[data-group-rename-input]');
    if (renameInput) {
      renameInput.addEventListener('pointerdown', (event) => event.stopPropagation());
      renameInput.addEventListener('keydown', (event) => {
        event.stopPropagation();
        if (event.key === 'Enter') {
          event.preventDefault();
          commitGroupRename(node, renameInput.value);
        }
        if (event.key === 'Escape') {
          event.preventDefault();
          cancelGroupRename(node);
        }
      });
      renameInput.addEventListener('blur', () => commitGroupRename(node, renameInput.value));
    }
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
          <span class="node-type-icon" aria-hidden="true"></span>
          <div class="node-title-meta">
            <div class="node-type">${escapeHtml(typeNames[node.type] || node.type)}</div>
            <div class="node-title">${escapeHtml(node.title)}</div>
          </div>
        </div>
        <div class="node-tools">
          <button class="node-tool node-tool-run" data-node-action="run" title="${escapeHtml(labels.runNode)}">${escapeHtml(labels.runNode)}</button>
        </div>
      </div>
      <div class="node-body">${nodeBodyHtml(node)}</div>
      <button class="node-resize" type="button" title="调整大小" aria-label="调整大小"></button>
    `;

    element.addEventListener('pointerdown', (event) => {
      if (event.target.closest('input,textarea,button,select,video,.node-port,.node-media')) {
        if (selectedIds.size !== 1 || !selectedIds.has(node.id)) selectOnly(node.id);
        return;
      }
      event.stopPropagation();
      if (event.shiftKey) toggleSelect(node.id);
      else if (!selectedIds.has(node.id)) selectOnly(node.id);
    });
    element.addEventListener('focusin', () => {
      if (selectedIds.size !== 1 || !selectedIds.has(node.id)) selectOnly(node.id);
    });
    element.querySelector('.node-head').addEventListener('pointerdown', (event) => startNodeDrag(event, node, false));
    element.querySelector('.node-resize').addEventListener('pointerdown', (event) => startNodeResize(event, node));
    element.querySelector('.node-port.output').addEventListener('pointerdown', (event) => startEdgeDrag(event, node));
    element.querySelector('.node-port.input').addEventListener('pointerup', (event) => finishEdgeDrag(event, node));
    if (node.type === 'image') {
      element.querySelector('.node-media-preview')?.addEventListener('pointerdown', (event) => {
        startNodeDrag(event, node, false, {
          allowInteractive: true,
          previewUrl: event.currentTarget.dataset.previewMedia || ''
        });
      });
    }
    bindNodeControls(element, node);
    els.nodeLayer.appendChild(element);
  }

  function nodeBodyHtml(node) {
    if (node.type === 'prompt') return promptNodeHtml(node);
    if (node.type === 'loop') return loopNodeHtml(node);
    if (node.type === 'llm') return llmNodeHtml(node);
    if (node.type === 'image') return imageNodeHtml(node);
    if (node.type === 'video') return videoNodeHtml(node);
    if (node.type === 'director') return directorNodeHtml(node);
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

  function stageKindLabel(kind) {
    if (kind === 'image') return '图像资产';
    if (kind === 'video') return '视频镜头';
    return '文本内容';
  }

  function nodeParamSummary(node, kind) {
    if (kind === 'image') {
      return `${node.ratio || '1:1'} · ${node.imageSize || '自适应'} · ${node.count || 1} 张`;
    }
    if (kind === 'video') {
      const fps = Number(node.outputFps || 0);
      return `${node.aspectRatio || '16:9'} · ${node.resolution || 'Auto'} · ${node.duration || 5}s${fps ? ` · ${fps}fps` : ''}`;
    }
    const length = String(node.prompt || node.resultText || '').length;
    return `${length || 0} 字 · 可接入下游`;
  }

  function nodeFlowMetaHtml(node, kind) {
    const inCount = upstreamNodes(node.id).length;
    const outCount = downstreamNodes(node.id).length;
    return `
      <div class="stage-flow-meta">
        <span>${escapeHtml(stageKindLabel(kind))}</span>
        <strong>${escapeHtml(nodeParamSummary(node, kind))}</strong>
        <em>IN ${inCount} / OUT ${outCount}</em>
      </div>
    `;
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
    if (node.status === 'succeeded') return '';
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
        ${nodeFlowMetaHtml(node, kind)}
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
        <select data-field="llmProvider">${providerOptionHtml('llm', nodePresets.llmProviders, node.llmProvider)}</select>
        <select data-field="model">${optionHtml(nodePresets.llmModels, node.model)}</select>
      </div>
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
          <select data-field="apiProvider">${providerOptionHtml('image', nodePresets.imageProviders, node.apiProvider)}</select>
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
          <select data-field="apiProvider">${providerOptionHtml('video', nodePresets.videoProviders, node.apiProvider)}</select>
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

  function directorCounts(result) {
    const data = result || {};
    return {
      characters: Array.isArray(data.characters) ? data.characters.length : 0,
      scenes: Array.isArray(data.scenes) ? data.scenes.length : 0,
      props: Array.isArray(data.props) ? data.props.length : 0,
      shots: Array.isArray(data.shots) ? data.shots.length : 0,
      videoSegments: Array.isArray(data.videoSegments) ? data.videoSegments.length : 0
    };
  }

  function directorTabLabel(tab) {
    return {
      overview: '总览',
      characters: '角色',
      scenes: '场景',
      props: '物品',
      shots: '分镜',
      videoSegments: '视频'
    }[tab] || tab;
  }

  function directorSummaryText(result) {
    if (!result) return '';
    const counts = directorCounts(result);
    return [
      result.title ? `项目：${result.title}` : '',
      result.logline ? `一句话：${result.logline}` : '',
      `角色 ${counts.characters} / 场景 ${counts.scenes} / 物品 ${counts.props} / 分镜 ${counts.shots} / 视频任务 ${counts.videoSegments}`
    ].filter(Boolean).join('\n');
  }

  function directorResultListHtml(result, tab) {
    if (!result) {
      return '<div class="node-empty director-empty">还没有拆解结果。先粘贴剧本或项目设定，再点击“导演拆解”。</div>';
    }
    if (tab === 'overview') {
      return `
        <div class="director-overview-card">
          <strong>${escapeHtml(result.title || '未命名项目')}</strong>
          <p>${escapeHtml(result.logline || '暂无一句话定位')}</p>
          <p>${escapeHtml(result.styleGuide || '暂无统一风格约束')}</p>
        </div>
      `;
    }
    const list = Array.isArray(result[tab]) ? result[tab] : [];
    if (!list.length) return `<div class="node-empty director-empty">${escapeHtml(directorTabLabel(tab))}暂无内容。</div>`;
    return list.slice(0, 16).map((item, index) => {
      const title = item.name || item.title || item.id || `${directorTabLabel(tab)} ${index + 1}`;
      const desc = item.description || item.role || item.prompt || item.action || '';
      const meta = [item.id, item.priority, item.duration ? `${item.duration}s` : '', item.location, item.time].filter(Boolean).join(' · ');
      return `
        <article class="director-result-card">
          <div><strong>${escapeHtml(title)}</strong><span>${escapeHtml(meta)}</span></div>
          <p>${escapeHtml(desc)}</p>
        </article>
      `;
    }).join('');
  }

  function directorNodeHtml(node) {
    const result = node.directorResult || null;
    const counts = directorCounts(result);
    const activeTab = node.activeTab || 'overview';
    const tabs = ['overview', 'characters', 'scenes', 'props', 'shots', 'videoSegments'];
    return `
      <section class="director-console">
        <div class="field-grid three">
          <select data-field="llmProvider">${providerOptionHtml('llm', nodePresets.llmProviders, node.llmProvider)}</select>
          <select data-field="model">${optionHtml(nodePresets.llmModels, node.model)}</select>
          <select data-field="aspectRatio">${optionHtml(nodePresets.ratios, node.aspectRatio)}</select>
        </div>
        <textarea class="node-textarea director-input" spellcheck="false" data-field="prompt" placeholder="${escapeHtml(labels.directorPrompt)}">${escapeHtml(node.prompt)}</textarea>
        <div class="director-actions">
          <button class="node-action" type="button" data-director-action="extract">导演拆解</button>
          <button class="node-action primary" type="button" data-director-action="build">加入画布</button>
          <span class="node-status ${escapeHtml(node.status || '')}">${escapeHtml(node.status || 'idle')}</span>
        </div>
        <div class="director-counts">
          <span>角色 ${counts.characters}</span>
          <span>场景 ${counts.scenes}</span>
          <span>物品 ${counts.props}</span>
          <span>分镜 ${counts.shots}</span>
          <span>视频 ${counts.videoSegments}</span>
        </div>
        <div class="director-tabs">
          ${tabs.map((tab) => `<button type="button" data-director-tab="${escapeHtml(tab)}" class="${activeTab === tab ? 'active' : ''}">${escapeHtml(directorTabLabel(tab))}</button>`).join('')}
        </div>
        <div class="director-results">${directorResultListHtml(result, activeTab)}</div>
      </section>
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
    element.querySelectorAll('[data-director-tab]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        node.activeTab = button.dataset.directorTab || 'overview';
        renderAll();
        setDirty();
      });
    });
    element.querySelectorAll('[data-director-action]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        selectOnly(node.id);
        if (button.dataset.directorAction === 'extract') runNode(node).catch(showError);
        if (button.dataset.directorAction === 'build') buildDirectorBlueprintNodes(node);
      });
    });
    element.querySelectorAll('[data-node-action="run"]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        selectOnly(node.id);
        runNode(node).catch(showError);
      });
    });
    element.querySelector('[data-node-action="delete"]')?.addEventListener('click', (event) => {
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

  function startNodeDrag(event, node, includeGroupChildren, options = {}) {
    if (event.button !== 0) return;
    if (activeDrag) return;
    if (!options.allowInteractive && event.target.closest('input,textarea,button,select,video,.node-port')) return;
    event.preventDefault();
    event.stopPropagation();
    if (event.shiftKey) toggleSelect(node.id);
    else if (!selectedIds.has(node.id)) selectOnly(node.id);

    const movedNodes = new Map();
    selectedNodes().forEach((item) => movedNodes.set(item.id, item));
    if (includeGroupChildren) groupChildren(node).forEach((item) => movedNodes.set(item.id, item));
    if (!beginPointerAction(event, {
      kind: 'node',
      start: clientToWorld(event.clientX, event.clientY),
      clientStart: { x: event.clientX, y: event.clientY },
      moved: false,
      previewUrl: options.previewUrl || '',
      origins: [...movedNodes.values()].map((item) => ({ id: item.id, x: item.x, y: item.y }))
    })) return;
  }

  function startGroupResize(event, node) {
    if (event.button !== 0) return;
    if (activeDrag) return;
    event.preventDefault();
    event.stopPropagation();
    selectOnly(node.id);
    if (!beginPointerAction(event, {
      kind: 'resize-group',
      start: clientToWorld(event.clientX, event.clientY),
      id: node.id,
      w: node.w,
      h: node.h
    })) return;
  }

  function startNodeResize(event, node) {
    if (event.button !== 0) return;
    if (activeDrag) return;
    event.preventDefault();
    event.stopPropagation();
    selectOnly(node.id);
    if (!beginPointerAction(event, {
      kind: 'resize-node',
      start: clientToWorld(event.clientX, event.clientY),
      id: node.id,
      w: node.w,
      h: node.h
    })) return;
  }

  function prefersReducedMotion() {
    return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;
  }

  function cancelPanMomentum() {
    if (!panMomentumRaf) return;
    cancelAnimationFrame(panMomentumRaf);
    panMomentumRaf = 0;
  }

  function startPanMomentum(samples) {
    cancelPanMomentum();
    if (prefersReducedMotion() || !Array.isArray(samples) || samples.length < 2) return;
    const last = samples[samples.length - 1];
    const first = samples.find((sample) => last.timeStamp - sample.timeStamp <= 120) || samples[0];
    const elapsed = Math.max(1, last.timeStamp - first.timeStamp);
    let velocityX = clamp((last.x - first.x) / elapsed, -2.4, 2.4);
    let velocityY = clamp((last.y - first.y) / elapsed, -2.4, 2.4);
    if (Math.hypot(velocityX, velocityY) < 0.08) return;
    const momentumState = state;
    let previousTime = performance.now();
    const step = (time) => {
      if (state !== momentumState) {
        panMomentumRaf = 0;
        return;
      }
      const delta = Math.min(32, Math.max(1, time - previousTime));
      previousTime = time;
      const decay = Math.pow(0.9, delta / 16.67);
      velocityX *= decay;
      velocityY *= decay;
      state.viewport.x += velocityX * delta;
      state.viewport.y += velocityY * delta;
      applyViewport();
      revealMinimap();
      if (Math.hypot(velocityX, velocityY) < 0.015) {
        panMomentumRaf = 0;
        revealMinimap();
        return;
      }
      panMomentumRaf = requestAnimationFrame(step);
    };
    panMomentumRaf = requestAnimationFrame(step);
  }

  function beginPointerAction(event, drag) {
    cancelPanMomentum();
    if (activeDrag) return false;
    activeDrag = {
      ...drag,
      pointerId: event.pointerId,
      pointerTarget: event.currentTarget || els.canvasArea
    };
    try { activeDrag.pointerTarget?.setPointerCapture?.(event.pointerId); } catch (_error) {}
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', endPointerAction);
    window.addEventListener('pointercancel', endPointerAction);
    return true;
  }

  function startPan(event) {
    if (activeDrag) return;
    event.preventDefault();
    if (!beginPointerAction(event, {
      kind: 'pan',
      start: { x: event.clientX, y: event.clientY },
      viewport: { ...state.viewport },
      samples: [{ x: event.clientX, y: event.clientY, timeStamp: event.timeStamp }]
    })) return;
  }

  function startCanvasMiddlePanCapture(event) {
    if (event.button !== 1) return;
    if (event.target.closest('.toolbar,.canvas-minimap,.add-menu,.canvas-create-dock')) return;
    event.stopPropagation();
    hideAddMenu();
    els.canvasArea.focus();
    startPan(event);
  }

  function startMarquee(event) {
    if (activeDrag) return;
    const point = clientToCanvas(event.clientX, event.clientY);
    if (!beginPointerAction(event, { kind: 'marquee', start: point, current: point })) return;
    els.selectionBox.classList.remove('hidden');
    paintMarquee();
  }

  function onPointerMove(event) {
    if (!activeDrag) return;
    if (event.pointerId !== activeDrag.pointerId) return;
    if (activeDrag.kind === 'pan') {
      activeDrag.samples.push({ x: event.clientX, y: event.clientY, timeStamp: event.timeStamp });
      activeDrag.samples = activeDrag.samples.filter((sample) => event.timeStamp - sample.timeStamp <= 120);
      activeDrag.samples = activeDrag.samples.slice(-6);
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
      const clientDx = Math.abs(event.clientX - activeDrag.clientStart.x);
      const clientDy = Math.abs(event.clientY - activeDrag.clientStart.y);
      if (clientDx + clientDy > 4) activeDrag.moved = true;
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
      const min = minSize(node.type);
      node.w = Math.max(min.w, activeDrag.w + point.x - activeDrag.start.x);
      node.h = Math.max(min.h, activeDrag.h + point.y - activeDrag.start.y);
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

  function endPointerAction(event) {
    if (!activeDrag) return;
    if (event?.pointerId != null && event.pointerId !== activeDrag.pointerId) return;
    const finished = activeDrag;
    const cancelled = event?.type === 'pointercancel';
    if (finished.kind === 'pan' && event?.clientX != null) {
      finished.samples.push({ x: event.clientX, y: event.clientY, timeStamp: event.timeStamp });
      finished.samples = finished.samples.slice(-6);
    }
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', endPointerAction);
    window.removeEventListener('pointercancel', endPointerAction);
    try { finished.pointerTarget?.releasePointerCapture?.(finished.pointerId); } catch (_error) {}
    activeDrag = null;
    if (finished.kind === 'marquee' && !cancelled) {
      const rect = marqueeWorldRect(finished);
      const ids = state.nodes
        .filter((node) => rectsIntersect(nodeRect(node), rect))
        .map((node) => node.id);
      selectMany(ids);
    }
    if (finished.kind === 'marquee') els.selectionBox.classList.add('hidden');
    if (!cancelled && finished.kind === 'node' && finished.previewUrl) {
      suppressNextMediaPreviewClick = true;
      if (!finished.moved) openMediaPreview(finished.previewUrl);
    }
    if (!cancelled && finished.kind === 'pan') startPanMomentum(finished.samples);
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
      const dropTarget = document.elementFromPoint(upEvent.clientX, upEvent.clientY);
      const target = dropTarget?.closest?.('[data-node-id]');
      const port = dropTarget?.closest?.('.node-port.input');
      if (target && port) {
        addEdge(source.id, target.dataset.nodeId);
      } else {
        pendingEdgeConnection = { source: source.id };
        showConnectionAddMenu(upEvent.clientX, upEvent.clientY);
      }
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

  function selectEdge(edgeId) {
    selectedIds.clear();
    selectedEdgeId = edgeId || '';
    renderSelection();
  }

  function deleteEdge(edgeId) {
    const edge = state.edges.find((item) => item.id === edgeId);
    if (!edge) return;
    state.edges = state.edges.filter((item) => item.id !== edgeId);
    if (selectedEdgeId === edgeId) selectedEdgeId = '';
    const source = nodeById(edge.source);
    const target = nodeById(edge.target);
    addLog({ level: 'info', title: '已删除连线', detail: `${source?.title || edge.source} -> ${target?.title || edge.target}` });
    renderEdges();
    renderInspector();
    renderWorkflowSummary();
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

  function edgeDeletePoint(start, end) {
    return {
      x: (start.x + end.x) / 2,
      y: (start.y + end.y) / 2
    };
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
      const start = portPoint(source, 'output');
      const end = portPoint(target, 'input');
      const group = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      group.setAttribute('class', `edge-group${selectedEdgeId === edge.id ? ' selected' : ''}`);
      group.setAttribute('data-edge-id', edge.id);
      const pathData = edgePath(start, end);
      const selectThisEdge = (event) => {
        event.preventDefault();
        event.stopPropagation();
        selectEdge(edge.id);
      };
      const hitPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      hitPath.setAttribute('class', 'edge-hit-path');
      hitPath.setAttribute('d', pathData);
      hitPath.addEventListener('pointerdown', selectThisEdge);
      group.appendChild(hitPath);
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('class', 'edge-path');
      path.setAttribute('d', pathData);
      path.addEventListener('pointerdown', selectThisEdge);
      group.appendChild(path);
      const point = edgeDeletePoint(start, end);
      const deleteGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      deleteGroup.setAttribute('class', 'edge-delete-control');
      deleteGroup.setAttribute('transform', `translate(${point.x}, ${point.y})`);
      deleteGroup.setAttribute('role', 'button');
      deleteGroup.setAttribute('tabindex', '0');
      deleteGroup.setAttribute('aria-label', '断开连线');
      const hit = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      hit.setAttribute('class', 'edge-delete-hit');
      hit.setAttribute('r', '12');
      const glyph = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      glyph.setAttribute('class', 'edge-delete-glyph');
      glyph.setAttribute('text-anchor', 'middle');
      glyph.setAttribute('dominant-baseline', 'central');
      glyph.textContent = '×';
      const removeEdge = (event) => {
        event.preventDefault();
        event.stopPropagation();
        deleteEdge(edge.id);
      };
      deleteGroup.addEventListener('pointerdown', (event) => {
        event.preventDefault();
        event.stopPropagation();
      });
      deleteGroup.addEventListener('click', removeEdge);
      deleteGroup.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') removeEdge(event);
      });
      deleteGroup.appendChild(hit);
      deleteGroup.appendChild(glyph);
      group.appendChild(deleteGroup);
      els.edgeLayer.appendChild(group);
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
    cancelPanMomentum();
    if (!currentCanvas) return;
    const requestedCanvasId = currentCanvas.id;
    let savedCanvas = currentCanvas;
    do {
      if (savingInFlight) {
        savedCanvas = await savingInFlight;
        continue;
      }
      const canvasAtStart = currentCanvas;
      if (!canvasAtStart || canvasAtStart.id !== requestedCanvasId) break;
      const versionAtStart = dirtyVersion;
      const savePromise = (async () => {
        els.saveState.textContent = labels.saving;
        let data;
        try {
          data = await api(`/api/canvases/${canvasAtStart.id}`, {
            method: 'PUT',
            body: JSON.stringify({ name: canvasAtStart.name, state, revision: canvasAtStart.revision })
          });
        } catch (error) {
          els.saveState.textContent = labels.unsaved;
          if (error?.status === 409) {
            showToast('画布已在其他页面更新，当前修改没有被覆盖。请刷新后重新确认。', 'warning');
          }
          throw error;
        }
        if (!currentCanvas || currentCanvas.id !== canvasAtStart.id) return data.canvas;
        currentCanvas = data.canvas;
        if (dirtyVersion === versionAtStart) setDirty(false);
        else {
          dirty = true;
          els.saveState.textContent = labels.unsaved;
        }
        renderCanvases();
        return currentCanvas;
      })();
      savingInFlight = savePromise;
      try {
        savedCanvas = await savePromise;
      } finally {
        if (savingInFlight === savePromise) savingInFlight = null;
      }
    } while (dirty && currentCanvas?.id === requestedCanvasId);
    if (!options.silent && currentCanvas?.id === requestedCanvasId && !dirty) {
      showToast('画布已保存', 'success');
    }
    return savedCanvas;
  }

  async function saveCurrentCanvasIfDirty() {
    cancelPanMomentum();
    while (dirty && currentCanvas) {
      await saveCanvas({ silent: true });
    }
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
    return [upstream, `# Prompt\n${own}`].filter(Boolean).join('\n\n');
  }

  function taskOptions(node) {
    if (node.type === 'image') {
      return {
        provider: node.apiProvider || '',
        model: node.model || '',
        ratio: node.ratio || '1:1',
        image_size: node.imageSize || '自适应',
        image_scale: Number(node.imageScale || 1),
        count: Number(node.count || 1)
      };
    }
    if (node.type === 'video') {
      return {
        provider: node.apiProvider || '',
        model: node.model || '',
        mode: node.videoMode || 'text_to_video',
        duration: Number(node.duration || 5),
        aspect_ratio: node.aspectRatio || '16:9',
        resolution: node.resolution || 'Auto',
        output_fps: Number(node.outputFps || 0),
        enhance_prompt: !!node.enhancePrompt,
        fixed_camera: !!node.cameraFixed,
        generate_audio: !!node.generateAudio,
        first_last_frame: !!node.firstLastFrame
      };
    }
    if (node.type === 'llm') {
      return {
        provider: node.llmProvider || '',
        model: node.model || '',
        system_prompt: node.systemPrompt || ''
      };
    }
    return {};
  }

  function directorSystemPrompt() {
    return `你是专业影视导演台和 AI 资产制片助手。你的任务是把用户给出的剧本、项目设定、产品卖点或世界观拆成可以直接进入画布生产的结构化蓝图。

只输出 JSON，不要 Markdown，不要解释。JSON 必须包含：
{
  "title": "项目名称",
  "logline": "一句话定位",
  "styleGuide": "统一视觉风格、画幅、镜头和连续性约束",
  "characters": [
    {"id":"CHR_001","name":"角色名","role":"角色功能","description":"外形、服装、性格、连续性约束","priority":"P0","prompt":"人物资产图提示词"}
  ],
  "scenes": [
    {"id":"SCN_001","name":"场景名","location":"地点","time":"时间","description":"空间、光线、色调、陈设、可复用机位","prompt":"场景资产图提示词"}
  ],
  "props": [
    {"id":"PRP_001","name":"物品名","description":"材质、颜色、尺寸、使用方式、连续性约束","prompt":"物品资产图提示词"}
  ],
  "shots": [
    {"id":"SHT_001","title":"分镜标题","duration":4,"description":"主体、动作、景别、机位、运镜、光线、转场","referenceAssetIds":["CHR_001","SCN_001"],"prompt":"分镜关键帧提示词"}
  ],
  "videoSegments": [
    {"id":"VID_001","title":"视频任务标题","duration":5,"aspectRatio":"9:16","description":"视频镜头内容","referenceAssetIds":["CHR_001","SCN_001","SHT_001"],"prompt":"视频生成提示词"}
  ]
}

拆解原则：
1. 角色、场景、物品必须分开，不能混成一个总提示词。
2. 每个资产必须能单独生图或单独生视频。
3. prompt 字段用中文为主，可以保留必要英文摄影和清晰度关键词。
4. 人物资产优先使用真人三视图/半身特写/全身 A-pose 结构；场景和物品使用资产板结构；视频任务要引用对应资产 id。`;
  }

  function directorUserPrompt(node, source) {
    return [
      directorSystemPrompt(),
      `# 目标画幅\n${node.aspectRatio || '9:16'}`,
      '# 用户内容',
      source
    ].join('\n\n');
  }

  function parseDirectorJson(value) {
    if (value && typeof value === 'object') return value;
    let text = String(value || '').trim();
    text = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/i, '').trim();
    const first = text.indexOf('{');
    const last = text.lastIndexOf('}');
    if (first >= 0 && last > first) text = text.slice(first, last + 1);
    text = text.replace(/,\s*([}\]])/g, '$1');
    return JSON.parse(text);
  }

  function directorArray(source, keys) {
    for (const key of keys) {
      if (Array.isArray(source?.[key])) return source[key];
    }
    return [];
  }

  function normalizeDirectorItem(item, index, prefix) {
    const source = item && typeof item === 'object' ? item : { description: String(item || '') };
    const id = String(source.id || source.code || `${prefix}_${String(index + 1).padStart(3, '0')}`).trim();
    const name = String(source.name || source.title || id).trim();
    const description = String(source.description || source.summary || source.role || source.action || source.prompt || '').trim();
    return {
      ...source,
      id,
      name,
      title: String(source.title || name).trim(),
      description,
      prompt: String(source.prompt || description || name).trim(),
      referenceAssetIds: Array.isArray(source.referenceAssetIds)
        ? source.referenceAssetIds.map((value) => String(value).trim()).filter(Boolean)
        : []
    };
  }

  function normalizeDirectorResult(raw) {
    if (!raw || typeof raw !== 'object') return null;
    return {
      title: String(raw.title || raw.project || raw.name || '导演台拆解结果').trim(),
      logline: String(raw.logline || raw.summary || raw.positioning || '').trim(),
      styleGuide: String(raw.styleGuide || raw.visualStyle || raw.style || '').trim(),
      characters: directorArray(raw, ['characters', 'roles', 'people']).map((item, index) => normalizeDirectorItem(item, index, 'CHR')),
      scenes: directorArray(raw, ['scenes', 'locations', 'sets']).map((item, index) => normalizeDirectorItem(item, index, 'SCN')),
      props: directorArray(raw, ['props', 'items', 'objects']).map((item, index) => normalizeDirectorItem(item, index, 'PRP')),
      shots: directorArray(raw, ['shots', 'storyboards', 'frames']).map((item, index) => normalizeDirectorItem(item, index, 'SHT')),
      videoSegments: directorArray(raw, ['videoSegments', 'videos', 'segments']).map((item, index) => normalizeDirectorItem(item, index, 'VID'))
    };
  }

  function directorTaskText(task) {
    const result = task?.result || {};
    if (typeof result.text === 'string') return result.text;
    if (typeof result.raw === 'string') return result.raw;
    return JSON.stringify(result.raw || result, null, 2);
  }

  async function runDirectorNode(node) {
    if (!nodeCapability(node).configured) {
      showToast('LLM 服务尚未配置，导演台暂不可运行。', 'warning');
      return false;
    }
    const source = [upstreamContext(node), node.prompt].filter(Boolean).join('\n\n').trim();
    if (!source) {
      showToast('请先输入剧本、项目设定或连接上游节点。', 'warning');
      return false;
    }
    node.status = 'queued';
    node.progress = 6;
    node.progressStartedAt = Date.now();
    node.resultText = '';
    addLog({ level: 'info', title: '导演台开始拆解', detail: node.title });
    renderAll();
    const data = await api('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({
        kind: 'llm',
        prompt: directorUserPrompt(node, source),
        canvas_id: currentCanvas?.id || '',
        node_id: node.id,
        options: taskOptions({ ...node, type: 'llm', systemPrompt: directorSystemPrompt() })
      })
    });
    updateAccount({ ...me, credits: data.balance });
    node.taskId = data.task.id;
    node.status = data.task.status;
    renderAll();
    setDirty();
    pollDirectorTask(data.task.id, node.id).catch((error) => markTaskPollingFailed(node.id, data.task.id, error));
    await loadTasks().catch(showError);
    return true;
  }

  async function pollDirectorTask(taskId, nodeId) {
    for (let i = 0; i < 160; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, i < 4 ? 900 : 1600));
      const data = await api(`/api/tasks/${taskId}`);
      updateAccount({ ...me, credits: data.balance });
      const node = nodeById(nodeId);
      if (node?.taskId && node.taskId !== taskId) return;
      if (node) {
        node.taskId = data.task.id;
        node.status = data.task.status;
        node.progress = generationProgress(node);
        if (data.task.status === 'failed') {
          node.resultText = data.task.error || '导演台拆解失败';
          addLog({ level: 'error', title: '导演台拆解失败', detail: node.resultText });
        }
        if (data.task.status === 'succeeded') {
          const rawText = directorTaskText(data.task);
          try {
            const parsed = parseDirectorJson(rawText);
            node.directorResult = normalizeDirectorResult(parsed);
            node.resultText = directorSummaryText(node.directorResult);
            node.progress = 100;
            addLog({ level: 'success', title: '导演台拆解完成', detail: node.resultText });
          } catch (error) {
            node.status = 'failed';
            node.resultText = `导演台返回不是有效 JSON，请重试或缩短输入。\n${String(rawText || '').slice(0, 800)}`;
            addLog({ level: 'error', title: '导演台解析失败', detail: error.message || String(error) });
          }
        }
        renderAll();
        setDirty();
      }
      if (['succeeded', 'failed'].includes(data.task.status)) {
        await loadTasks();
        return;
      }
    }
    markTaskPollingFailed(nodeId, taskId, new Error('导演台查询超时，请稍后重试。'));
  }

  function directorItemPrompt(kind, item, result) {
    const style = result?.styleGuide ? `\n统一风格：${result.styleGuide}` : '';
    if (kind === 'character') {
      return `生成${item.name}的真人形象三视图，白底图。左侧展示精细真人半身特写肖像，面部特征、骨骼结构、神态表情、发型及头部配饰必须严格一致，呈现自然皮肤纹理、毛孔和发丝细节。右侧展示完全相同角色的全身真人照片，标准 A-pose 站姿，按正视图、侧视图、背面图排列。身体比例、服装设计、布料层次、鞋子和配饰必须严格遵循，所有材质真实。\n角色说明：${item.description || item.prompt}${style}\n负面：避免脸不一致、服装变化、多余肢体、手部畸形、塑料皮肤、过度美颜、文字乱码。`;
    }
    if (kind === 'scene') {
      return `生成${item.name}的场景资产图，16:9 横版，完整展示空间结构、主视角、反向视角、关键陈设、动线、光线色调和可复用机位。不要加入无关人物。\n场景说明：${item.description || item.prompt}${style}\n负面：避免空间结构混乱、比例错误、随机文字、水印、低清晰度。`;
    }
    if (kind === 'prop') {
      return `生成${item.name}的物品道具资产图，白底或浅灰底，展示正面、侧面、背面、细节特写和真实材质质感。保持尺寸比例、结构、颜色、磨损和使用痕迹一致。\n物品说明：${item.description || item.prompt}${style}\n负面：避免结构不一致、重复物体、文字乱码、低质伪影。`;
    }
    if (kind === 'shot') {
      return `生成分镜关键帧：${item.title || item.name}。画面需要明确主体、动作、景别、机位、运镜意图、光线、情绪和转场。\n分镜说明：${item.description || item.prompt}${style}`;
    }
    return `${item.title || item.name}\n${item.description || ''}\n${item.prompt || ''}${style}`.trim();
  }

  function buildDirectorBlueprintNodes(sourceNode) {
    const result = sourceNode.directorResult;
    if (!result) {
      showToast('请先运行导演台拆解，得到结构化结果后再加入画布。', 'warning');
      return;
    }
    if (currentView !== 'canvas') showCanvasPage();
    const oldIds = new Set(state.nodes.filter((node) => node.directorSourceId === sourceNode.id).map((node) => node.id));
    if (oldIds.size) {
      state.nodes = state.nodes.filter((node) => !oldIds.has(node.id));
      state.edges = state.edges.filter((edge) => !oldIds.has(edge.source) && !oldIds.has(edge.target));
    }

    const baseX = sourceNode.x + sourceNode.w + 180;
    const baseY = sourceNode.y - 40;
    const created = [];
    const links = [];
    const assetOutputs = new Map();
    const characterItems = result.characters.slice(0, 8);
    const sceneItems = result.scenes.slice(0, 6);
    const propItems = result.props.slice(0, 8);
    const shotItems = result.shots.slice(0, 10);
    const videoItems = result.videoSegments.slice(0, 8);
    const characterY = baseY;
    const characterHeight = Math.max(700, characterItems.length * 360 + 100);
    const sceneY = characterY + characterHeight + 90;
    const sceneHeight = Math.max(620, sceneItems.length * 340 + 100);
    const propY = sceneY + sceneHeight + 90;
    const propHeight = Math.max(620, propItems.length * 320 + 100);
    const shotY = baseY;
    const shotHeight = Math.max(980, shotItems.length * 250 + 100);
    const videoY = shotY + shotHeight + 90;
    const videoHeight = Math.max(780, videoItems.length * 310 + 100);
    const groupSpecs = [
      ['人物资产区', baseX - 40, characterY - 40, 1460, characterHeight],
      ['场景资产区', baseX - 40, sceneY - 40, 1460, sceneHeight],
      ['物品资产区', baseX - 40, propY - 40, 1460, propHeight],
      ['分镜区', baseX + 1320, shotY - 40, 1580, shotHeight],
      ['视频任务区', baseX + 1320, videoY - 40, 1580, videoHeight]
    ];

    const makeNode = (type, patch) => {
      const size = defaultSize(type);
      const node = normalizeNode({
        id: uid(type),
        type,
        w: size.w,
        h: size.h,
        directorSourceId: sourceNode.id,
        ...patch
      });
      created.push(node);
      return node;
    };
    const link = (source, target) => links.push({ id: uid('edge'), source: source.id, target: target.id });
    const makeAssetChain = (item, kind, x, y, ratio) => {
      const prompt = makeNode('prompt', {
        title: `${kind === 'character' ? '角色' : kind === 'scene' ? '场景' : '物品'} | ${item.name}`,
        x,
        y,
        w: 360,
        h: 300,
        prompt: directorItemPrompt(kind, item, result)
      });
      const image = makeNode('image', {
        title: `生图 | ${item.name}`,
        x: x + 430,
        y,
        w: 520,
        h: 620,
        ratio,
        imageSize: '2K',
        prompt: directorItemPrompt(kind, item, result)
      });
      const output = makeNode('output', {
        title: `输出 | ${item.name}`,
        x: x + 1010,
        y,
        w: 360,
        h: 260,
        prompt: `${item.name}资产输出`
      });
      link(prompt, image);
      link(image, output);
      assetOutputs.set(item.id, output);
      assetOutputs.set(item.name, output);
    };

    characterItems.forEach((item, index) => makeAssetChain(item, 'character', baseX, characterY + index * 360, '9:16'));
    sceneItems.forEach((item, index) => makeAssetChain(item, 'scene', baseX, sceneY + index * 340, '16:9'));
    propItems.forEach((item, index) => makeAssetChain(item, 'prop', baseX, propY + index * 320, '1:1'));

    shotItems.forEach((item, index) => {
      const rowY = shotY + index * 250;
      const prompt = makeNode('prompt', {
        title: `分镜 | ${item.title || item.name}`,
        x: baseX + 1360,
        y: rowY,
        w: 410,
        h: 250,
        prompt: directorItemPrompt('shot', item, result)
      });
      const image = makeNode('image', {
        title: `关键帧 | ${item.title || item.name}`,
        x: baseX + 1830,
        y: rowY,
        w: 520,
        h: 560,
        ratio: sourceNode.aspectRatio || '9:16',
        imageSize: '2K',
        prompt: directorItemPrompt('shot', item, result)
      });
      const output = makeNode('output', {
        title: `分镜输出 | ${item.title || item.name}`,
        x: baseX + 2400,
        y: rowY,
        w: 360,
        h: 250,
        prompt: `${item.title || item.name}关键帧输出`
      });
      link(prompt, image);
      link(image, output);
      (item.referenceAssetIds || []).forEach((id) => {
        const ref = assetOutputs.get(id);
        if (ref) link(ref, image);
      });
      assetOutputs.set(item.id, output);
      assetOutputs.set(item.name, output);
    });

    videoItems.forEach((item, index) => {
      const rowY = videoY + index * 310;
      const prompt = makeNode('prompt', {
        title: `视频提示词 | ${item.title || item.name}`,
        x: baseX + 1360,
        y: rowY,
        w: 410,
        h: 270,
        prompt: directorItemPrompt('video', item, result)
      });
      const video = makeNode('video', {
        title: `视频生成 | ${item.title || item.name}`,
        x: baseX + 1830,
        y: rowY,
        w: 560,
        h: 540,
        aspectRatio: item.aspectRatio || sourceNode.aspectRatio || '9:16',
        resolution: '1080p',
        duration: item.duration || 5,
        prompt: directorItemPrompt('video', item, result)
      });
      const output = makeNode('output', {
        title: `视频输出 | ${item.title || item.name}`,
        x: baseX + 2450,
        y: rowY,
        w: 360,
        h: 260,
        prompt: `${item.title || item.name}视频输出`
      });
      link(prompt, video);
      (item.referenceAssetIds || []).forEach((id) => {
        const ref = assetOutputs.get(id);
        if (ref) link(ref, video);
      });
      link(video, output);
    });

    const groups = groupSpecs.map(([title, x, y, w, h]) => normalizeNode({ id: uid('group'), type: 'group', title, x, y, w, h, prompt: '', directorSourceId: sourceNode.id }));
    state.nodes.push(...groups, ...created);
    state.edges.push(...links);
    selectMany(created.map((node) => node.id));
    addLog({ level: 'success', title: '导演台蓝图已加入画布', detail: `${created.length} 个节点 / ${links.length} 条连线` });
    renderAll();
    setDirty();
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

  function taskNodeSnapshot(node) {
    return JSON.stringify({
      status: node.status || '',
      taskId: node.taskId || '',
      progress: Number(node.progress || 0),
      resultText: node.resultText || '',
      resultUrl: node.resultUrl || '',
      resultKind: node.resultKind || '',
      directorResult: node.type === 'director' ? (node.directorResult || null) : null
    });
  }

  function applyTaskToNode(node, task) {
    applyTaskResult(node, task);
    if (node.type !== 'director' || task.status !== 'succeeded') return;
    const rawText = directorTaskText(task);
    try {
      node.directorResult = normalizeDirectorResult(parseDirectorJson(rawText));
      node.resultText = directorSummaryText(node.directorResult);
      node.progress = 100;
    } catch (error) {
      node.status = 'failed';
      node.resultText = `导演台返回不是有效 JSON，请重试或缩短输入。\n${String(rawText || '').slice(0, 800)}`;
    }
  }

  async function reconcileTasksToNodes(tasks) {
    if (!currentCanvas || !Array.isArray(tasks) || !tasks.length) return false;
    let changed = false;
    const reconciledNodeIds = new Set();
    tasks.forEach((task) => {
      if (task.canvas_id && task.canvas_id !== currentCanvas.id) return;
      const node = (task.node_id && nodeById(task.node_id)) || state.nodes.find((item) => item.taskId === task.id);
      if (!node) return;
      if (node.taskId && node.taskId !== task.id) return;
      if (reconciledNodeIds.has(node.id)) return;
      reconciledNodeIds.add(node.id);
      const before = taskNodeSnapshot(node);
      applyTaskToNode(node, task);
      if (taskNodeSnapshot(node) !== before) changed = true;
    });
    if (!changed) return false;
    renderAll();
    setDirty();
    await saveCurrentCanvasIfDirty();
    return true;
  }

  function isLocalRunnable(node) {
    return ['prompt', 'loop', 'output'].includes(node.type);
  }

  function isRemoteRunnable(node) {
    return ['llm', 'image', 'video', 'director'].includes(node.type);
  }

  async function runSelectedNode() {
    const node = selectedNodes()[0];
    if (!node || node.type === 'group') {
      showToast(labels.selectRunnable, 'warning');
      return false;
    }
    return runNode(node);
  }

  async function runNode(node) {
    if (!node || node.type === 'group') {
      showToast(labels.selectRunnable, 'warning');
      return false;
    }
    if (nodeRunsInFlight.has(node.id) || ['queued', 'running'].includes(node.status)) {
      showToast('该节点正在运行，请等待当前任务完成。', 'warning');
      return false;
    }
    const capability = nodeCapability(node);
    if (!capability.configured) {
      const kind = node.type === 'director' ? 'LLM' : typeNames[node.type];
      showToast(`${kind}服务尚未配置，请先在服务器环境变量中配置对应供应商。`, 'warning');
      return false;
    }
    if (!isLocalRunnable(node) && !isRemoteRunnable(node)) {
      showToast(labels.selectRunnable, 'warning');
      return false;
    }
    nodeRunsInFlight.add(node.id);
    try {
      if (isLocalRunnable(node)) {
        runLocalNode(node);
        return true;
      }
      if (node.type === 'director') return await runDirectorNode(node);
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
          node_id: node.id,
          options: taskOptions(node)
        })
      });
      updateAccount({ ...me, credits: data.balance });
      applyTaskResult(node, data.task);
      renderAll();
      setDirty();
      pollTask(data.task.id, node.id).catch((error) => markTaskPollingFailed(node.id, data.task.id, error));
      await loadTasks().catch(showError);
      return true;
    } catch (error) {
      node.status = 'failed';
      node.progress = 0;
      node.resultText = error?.message || labels.failed;
      addLog({ level: 'error', title: '节点启动失败', detail: `${typeNames[node.type]} -> ${node.title}` });
      renderAll();
      setDirty();
      throw error;
    } finally {
      nodeRunsInFlight.delete(node.id);
    }
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

  function markTaskPollingFailed(nodeId, taskId, error) {
    const node = nodeById(nodeId);
    if (!node || (node.taskId && node.taskId !== taskId)) return;
    node.status = 'failed';
    node.progress = 0;
    node.resultText = error?.message || labels.failed;
    addLog({ level: 'error', title: '任务查询失败', detail: `${typeNames[node.type]} -> ${node.title}` });
    renderAll();
    setDirty();
    showToast(node.resultText, 'error');
  }

  async function pollTask(taskId, nodeId) {
    for (let i = 0; i < 160; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, i < 4 ? 900 : 1600));
      const data = await api(`/api/tasks/${taskId}`);
      updateAccount({ ...me, credits: data.balance });
      const node = nodeById(nodeId);
      if (node?.taskId && node.taskId !== taskId) return;
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
    markTaskPollingFailed(nodeId, taskId, new Error('任务查询超时，请稍后重试。'));
  }

  async function runChain() {
    if (chainRunInFlight) {
      showToast('当前链路正在运行，请等待完成。', 'warning');
      return false;
    }
    chainRunInFlight = true;
    try {
      const roots = selectedNodes().filter((node) => node.type !== 'group');
      if (!roots.length) return await runSelectedNode();
      const order = collectRunOrder(roots);
      addLog({ level: 'info', title: '链路开始运行', detail: `${order.length} 个节点` });
      for (const node of order) {
        if (node.type === 'group') continue;
        const started = await runNode(node);
        if (!started) {
          addLog({ level: 'error', title: '链路已停止', detail: `${node.title} 未启动` });
          return false;
        }
        if (isRemoteRunnable(node)) {
          const status = await waitForNodeDone(node.id);
          if (status !== 'succeeded') {
            addLog({ level: 'error', title: '链路已停止', detail: `${node.title} / ${status}` });
            return false;
          }
        } else if (node.status !== 'succeeded') {
          addLog({ level: 'error', title: '链路已停止', detail: `${node.title} / ${node.status || labels.failed}` });
          return false;
        }
      }
      addLog({ level: 'success', title: '链路运行完成', detail: `${order.length} 个节点` });
      return true;
    } finally {
      chainRunInFlight = false;
    }
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
      if (!node) return 'missing';
      if (['succeeded', 'failed'].includes(node.status)) return node.status;
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    return 'timeout';
  }

  function taskTargetFor(task) {
    if (task.project_id || task.canvas_id || task.node_id) {
      return {
        projectId: task.project_id || '',
        canvasId: task.canvas_id || '',
        nodeId: task.node_id || ''
      };
    }
    const node = state.nodes.find((item) => item.taskId === task.id);
    return node ? {
      projectId: currentProject?.id || '',
      canvasId: currentCanvas?.id || '',
      nodeId: node.id
    } : null;
  }

  async function resolveTaskTarget(task) {
    const local = taskTargetFor(task);
    if (local && (local.projectId || !local.canvasId || local.canvasId === currentCanvas?.id)) return local;
    if (!task.id) return local;
    const data = await api(`/api/tasks/${task.id}/target`);
    if (!data.target) return local;
    return {
      projectId: data.target.project_id || '',
      canvasId: data.target.canvas_id || '',
      nodeId: data.target.node_id || ''
    };
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
    if (target.projectId && (!currentProject || currentProject.id !== target.projectId)) {
      await selectProject(target.projectId);
    }
    if (target.canvasId && (!currentCanvas || currentCanvas.id !== target.canvasId)) {
      await selectCanvas(target.canvasId);
    }
    await reconcileTasksToNodes([task]);
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
    await reconcileTasksToNodes(tasks);
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

  function filteredAssets(assets, keyword = String(els.assetSearchInput?.value || '').trim().toLowerCase()) {
    const search = String(keyword || '').trim().toLowerCase();
    return assets.filter((asset) => {
      const kindOk = assetFilter === 'all'
        || (assetFilter === 'image' && asset.kind === 'image')
        || (assetFilter === 'video' && asset.kind === 'video')
        || (assetFilter === 'upload' && asset.source === 'upload')
        || (assetFilter === 'task' && asset.source === 'task');
      if (!kindOk) return false;
      if (!search) return true;
      return [asset.title, asset.kind, asset.source, asset.task_id, asset.node_id]
        .some((value) => String(value || '').toLowerCase().includes(search));
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
    els.assetList.querySelector('[data-open-assets]')?.addEventListener('click', () => showAssetPage().catch(showError));
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
        ${String(asset.url || '').startsWith('/api/assets/') ? '<button class="small-button danger" type="button" data-preview-delete>删除素材</button>' : ''}
      </div>
    `;
    els.assetPreview.querySelector('[data-preview-focus]')?.addEventListener('click', () => {
      focusTask({
        id: asset.task_id || '',
        project_id: asset.project_id || '',
        canvas_id: asset.canvas_id || '',
        node_id: asset.node_id || ''
      }).catch(showError);
    });
    const deleteButton = els.assetPreview.querySelector('[data-preview-delete]');
    deleteButton?.addEventListener('click', async () => {
      if (deleteButton.dataset.confirmed !== 'true') {
        deleteButton.dataset.confirmed = 'true';
        deleteButton.textContent = '再次点击确认';
        window.setTimeout(() => {
          if (!deleteButton.isConnected) return;
          deleteButton.dataset.confirmed = 'false';
          deleteButton.textContent = '删除素材';
        }, 3000);
        return;
      }
      deleteButton.disabled = true;
      try {
        const data = await api(`/api/assets/${encodeURIComponent(asset.id)}`, { method: 'DELETE' });
        let canvasChanged = false;
        state.nodes.forEach((node) => {
          if (node.resultUrl === asset.url) {
            node.resultUrl = '';
            node.status = '';
            canvasChanged = true;
          }
          if (node.assetUrl === asset.url) {
            node.assetUrl = '';
            node.assetName = '';
            canvasChanged = true;
          }
        });
        if (canvasChanged) setDirty();
        selectedAssetId = '';
        updateStorageSummary(data.storage);
        await loadAssets();
        showToast('素材已删除', 'success');
      } catch (error) {
        deleteButton.disabled = false;
        showError(error);
      }
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

  function focusAsset(asset) {
    if (!asset) return;
    if (asset.node_id || asset.task_id) {
      hideAssetDrawer();
      focusTask({
        id: asset.task_id || '',
        project_id: asset.project_id || '',
        canvas_id: asset.canvas_id || '',
        node_id: asset.node_id || ''
      }).catch(showError);
      return;
    }
    if (asset.url && asset.kind === 'image') openMediaPreview(asset.url);
    else if (asset.url) window.open(asset.url, '_blank', 'noreferrer');
  }

  function renderAssetDrawer() {
    if (!els.assetDrawerGrid) return;
    const assets = currentAssetItems();
    const keyword = String(els.assetDrawerSearch?.value || '').trim().toLowerCase();
    const visible = filteredAssets(assets, keyword);
    els.assetDrawerCount.textContent = `${visible.length} / ${assets.length} 个素材`;
    document.querySelectorAll('[data-asset-tab]').forEach((button) => {
      button.classList.toggle('active', button.dataset.assetTab === assetFilter);
    });
    const uploadCard = `
      <button class="drawer-upload-card" type="button" data-upload-from-drawer>
        <strong>上传素材</strong>
        <small>保存到当前画布</small>
      </button>
    `;
    if (!visible.length) {
      els.assetDrawerGrid.innerHTML = `
        ${uploadCard}
        <div class="drawer-empty">${assets.length ? '当前筛选下暂无素材' : labels.noAssets}</div>
      `;
      els.assetDrawerGrid.querySelector('[data-upload-from-drawer]')?.addEventListener('click', () => els.fileInput.click());
      return;
    }
    els.assetDrawerGrid.innerHTML = `
      ${uploadCard}
      ${visible.map((asset) => {
        const id = asset.id || asset.url;
        return `
          <button class="drawer-asset-card" type="button" data-drawer-asset-id="${escapeHtml(id)}" title="${escapeHtml(asset.title || '素材')}">
            <span class="drawer-asset-thumb">
              ${asset.kind === 'video'
                ? `<video src="${escapeHtml(asset.url)}" muted></video>`
                : `<img src="${escapeHtml(asset.url)}" alt="" draggable="false">`}
            </span>
            <strong>${escapeHtml(asset.title || '素材')}</strong>
            <small>${escapeHtml(assetSourceLabel(asset))}</small>
          </button>
        `;
      }).join('')}
    `;
    els.assetDrawerGrid.querySelector('[data-upload-from-drawer]')?.addEventListener('click', () => els.fileInput.click());
    els.assetDrawerGrid.querySelectorAll('[data-drawer-asset-id]').forEach((button) => {
      button.addEventListener('click', () => {
        const asset = visible.find((item) => (item.id || item.url) === button.dataset.drawerAssetId);
        focusAsset(asset);
      });
    });
  }

  function renderAssets() {
    const assets = currentAssetItems();
    renderAssetSidebarSummary(assets);
    renderAssetPage();
    renderAssetDrawer();
  }

  function hideAssetDrawer() {
    els.assetDrawer?.classList.add('hidden');
    els.assetBtn?.classList.remove('active');
  }

  function navigateTo(path, options = {}) {
    if (window.location.pathname === path) return;
    const method = options.replace ? 'replaceState' : 'pushState';
    window.history[method]({}, '', path);
  }

  function setTopNavigationActive(view) {
    els.assetBtn?.classList.toggle('active', view === 'assets');
    els.logBtn?.classList.toggle('active', view === 'logs');
    els.accountBtn?.classList.toggle('active', view === 'account');
  }

  function hideSubpages() {
    els.assetPage?.classList.add('hidden');
    els.accountPage?.classList.add('hidden');
    els.logsPage?.classList.add('hidden');
  }

  function setSubpageMode(enabled) {
    els.appShell?.classList.toggle('subpage-open', enabled);
  }

  function cancelViewAnimation(nextTarget = null) {
    if (!activeViewAnimation) return null;
    const target = activeViewAnimation.effect?.target || null;
    const presentation = target && target === nextTarget
      ? { target, opacity: getComputedStyle(target).opacity, transform: getComputedStyle(target).transform }
      : null;
    activeViewAnimation.cancel();
    activeViewAnimation = null;
    return presentation;
  }

  function animateView(target, direction = 'forward') {
    if (!target || target.classList.contains('hidden') || typeof target.animate !== 'function') return;
    const interrupted = cancelViewAnimation(target);
    const computed = getComputedStyle(target);
    const reduced = prefersReducedMotion();
    const offset = direction === 'back' ? -8 : 8;
    const startOpacity = interrupted ? Number.parseFloat(interrupted.opacity) || 0 : 0;
    const startTransform = interrupted?.transform && interrupted.transform !== 'none'
      ? interrupted.transform
      : `translateY(${offset}px) scale(0.992)`;
    const keyframes = reduced
      ? [{ opacity: startOpacity }, { opacity: 1 }]
      : [
          { opacity: startOpacity, transform: startTransform },
          { opacity: 1, transform: computed.transform === 'none' ? 'translateY(0) scale(1)' : computed.transform }
        ];
    const animation = target.animate(keyframes, {
      duration: reduced ? 120 : 220,
      easing: 'cubic-bezier(0.22, 1, 0.36, 1)',
      fill: 'both'
    });
    activeViewAnimation = animation;
    animation.finished.then(() => {
      if (activeViewAnimation !== animation) return;
      animation.cancel();
      activeViewAnimation = null;
    }).catch(() => {});
  }

  function showCanvasPage(options = {}) {
    cancelPanMomentum();
    if (currentView === 'canvas' && !els.canvasArea.classList.contains('hidden')) return;
    currentView = 'canvas';
    setSubpageMode(false);
    hideSubpages();
    els.canvasArea?.classList.remove('hidden');
    animateView(els.canvasArea, 'back');
    if (!els.assetDrawer || els.assetDrawer.classList.contains('hidden')) setTopNavigationActive('canvas');
    els.canvasTitle.textContent = currentCanvas?.name || labels.canvas;
    if (options.push !== false) navigateTo('/');
    applyViewport();
    renderEdges();
    scheduleMinimapRender();
  }

  async function showAssetDrawer() {
    if (currentView === 'assets') showCanvasPage();
    await loadAssets();
    els.assetDrawer?.classList.remove('hidden');
    els.assetBtn?.classList.add('active');
    renderAssetDrawer();
  }

  async function showAssetPage(options = {}) {
    cancelPanMomentum();
    if (currentView === 'assets' && !els.assetPage.classList.contains('hidden')) return;
    currentView = 'assets';
    hideAssetDrawer();
    setSubpageMode(true);
    els.canvasArea?.classList.add('hidden');
    els.accountPage?.classList.add('hidden');
    els.logsPage?.classList.add('hidden');
    els.assetPage.classList.remove('hidden');
    animateView(els.assetPage, 'forward');
    setTopNavigationActive('assets');
    els.canvasTitle.textContent = '素材库管理';
    if (options.push !== false) navigateTo('/assets');
    els.assetPage.setAttribute('aria-busy', 'true');
    try {
      await loadAssets();
      renderAssetPage();
    } finally {
      els.assetPage.setAttribute('aria-busy', 'false');
    }
  }

  function toggleAssetPage() {
    if (currentView === 'assets') showCanvasPage();
    else showAssetPage().catch(showError);
  }

  function renderAccountPage() {
    updateAccount(me);
  }

  function showAccountPage(options = {}) {
    cancelPanMomentum();
    if (currentView === 'account' && !els.accountPage.classList.contains('hidden')) return;
    currentView = 'account';
    hideAssetDrawer();
    setSubpageMode(true);
    els.canvasArea?.classList.add('hidden');
    els.assetPage?.classList.add('hidden');
    els.logsPage?.classList.add('hidden');
    els.accountPage?.classList.remove('hidden');
    animateView(els.accountPage, 'forward');
    setTopNavigationActive('account');
    els.canvasTitle.textContent = '用户中心';
    if (options.push !== false) navigateTo('/account');
    renderAccountPage();
  }

  async function submitPasswordChange(event) {
    event.preventDefault();
    const currentPassword = els.currentPasswordInput?.value || '';
    const newPassword = els.newPasswordInput?.value || '';
    const confirmation = els.confirmPasswordInput?.value || '';
    if (newPassword.length < 6) {
      showToast('新密码至少 6 位', 'warning');
      return;
    }
    if (newPassword !== confirmation) {
      showToast('两次输入的新密码不一致', 'warning');
      return;
    }
    const submitButton = els.passwordChangeForm?.querySelector('button[type="submit"]');
    if (submitButton) submitButton.disabled = true;
    try {
      await api('/api/account/password', {
        method: 'POST',
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
      });
      els.passwordChangeForm?.reset();
      showToast('密码已更新', 'success');
    } catch (error) {
      showError(error);
    } finally {
      if (submitButton) submitButton.disabled = false;
    }
  }

  function showLogsPage(options = {}) {
    cancelPanMomentum();
    if (currentView === 'logs' && !els.logsPage.classList.contains('hidden')) return;
    currentView = 'logs';
    hideAssetDrawer();
    setSubpageMode(true);
    els.canvasArea?.classList.add('hidden');
    els.assetPage?.classList.add('hidden');
    els.accountPage?.classList.add('hidden');
    els.logsPage?.classList.remove('hidden');
    animateView(els.logsPage, 'forward');
    setTopNavigationActive('logs');
    els.canvasTitle.textContent = '运行日志';
    if (options.push !== false) navigateTo('/logs');
    renderLogsPage();
  }

  function applyRouteFromLocation() {
    if (window.location.pathname === '/assets') {
      showAssetPage({ push: false }).catch(showError);
      return;
    }
    if (window.location.pathname === '/account') {
      showAccountPage({ push: false });
      return;
    }
    if (window.location.pathname === '/logs') {
      showLogsPage({ push: false });
      return;
    }
    showCanvasPage({ push: false });
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
      renderLogsPage();
      return;
    }
    els.logList.innerHTML = logs.slice().reverse().map((log) => `
      <div class="log-item ${escapeHtml(log.level)}">
        <strong>${escapeHtml(log.title)}<span>${escapeHtml(log.at)}</span></strong>
        <p>${escapeHtml(log.detail)}</p>
      </div>
    `).join('');
    renderLogsPage();
  }

  function renderLogsPage() {
    if (!els.logsPageList) return;
    const logs = state.logs || [];
    if (!logs.length) {
      els.logsPageList.innerHTML = `<div class="subpage-empty">${labels.noLogs}</div>`;
      return;
    }
    els.logsPageList.innerHTML = logs.slice().reverse().map((log) => `
      <article class="logs-page-item ${escapeHtml(log.level)}">
        <div>
          <strong>${escapeHtml(log.title)}</strong>
          <span>${escapeHtml(log.detail)}</span>
        </div>
        <time>${escapeHtml(log.at)}</time>
      </article>
    `).join('');
  }

  function workflowPayload(selectedOnly = true) {
    const selected = new Set(selectedIds);
    if (selectedOnly && selected.size) {
      state.nodes
        .filter((node) => node.type === 'group' && selected.has(node.id))
        .forEach((group) => groupChildren(group).forEach((node) => selected.add(node.id)));
    }
    const nodes = selectedOnly && selected.size
      ? state.nodes.filter((node) => selected.has(node.id))
      : state.nodes.filter((node) => node.type !== 'group');
    const ids = new Set(nodes.map((node) => node.id));
    const assets = currentAssetItems()
      .filter((asset) => ids.has(asset.node_id || '') || ids.has(asset.id || ''))
      .map((asset) => ({
        id: asset.id || '',
        title: asset.title || '',
        kind: asset.kind || '',
        url: asset.url || '',
        source: asset.source || '',
        node_id: asset.node_id || '',
        task_id: asset.task_id || ''
      }));
    return {
      version: 1,
      name: currentCanvas?.name || labels.canvas,
      exported_at: new Date().toISOString(),
      nodes,
      edges: state.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target)),
      assets
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

  async function loadWorkflowTemplates() {
    if (!els.workflowTemplateList) return;
    const data = await api('/api/workflows');
    workflowTemplates = data.workflows || [];
    renderWorkflowTemplates();
  }

  function renderWorkflowTemplates() {
    if (!els.workflowTemplateList) return;
    if (!workflowTemplates.length) {
      els.workflowTemplateList.innerHTML = '<div class="workflow-empty">暂无保存的模板。选中一组节点后点击“保存模板”。</div>';
      return;
    }
    els.workflowTemplateList.innerHTML = workflowTemplates.map((item) => `
      <div class="workflow-template-item">
        <div>
          <strong>${escapeHtml(item.name || '工作流模板')}</strong>
          <span>${safeNumber(item.node_count, 0)} 节点 / ${safeNumber(item.edge_count, 0)} 连线</span>
        </div>
        <div class="workflow-template-actions">
          <button type="button" data-workflow-insert="${escapeHtml(item.id)}">加入</button>
          <button type="button" data-workflow-delete="${escapeHtml(item.id)}">删除</button>
        </div>
      </div>
    `).join('');
    els.workflowTemplateList.querySelectorAll('[data-workflow-insert]').forEach((button) => {
      button.addEventListener('click', () => insertWorkflowTemplate(button.dataset.workflowInsert).catch(showError));
    });
    els.workflowTemplateList.querySelectorAll('[data-workflow-delete]').forEach((button) => {
      button.addEventListener('click', () => deleteWorkflowTemplate(button.dataset.workflowDelete).catch(showError));
    });
  }

  async function saveWorkflowTemplate() {
    const payload = workflowPayload(true);
    if (!payload.nodes.length) {
      showToast('请先选中要保存为模板的节点。', 'warning');
      return;
    }
    const suggestedName = `${currentCanvas?.name || '工作流'} - ${payload.nodes.length} 节点`;
    const name = window.prompt('模板名称', suggestedName);
    if (!name) return;
    const data = await api('/api/workflows', {
      method: 'POST',
      body: JSON.stringify({ name, payload })
    });
    const workflow = data.workflow;
    workflowTemplates = [workflow, ...workflowTemplates.filter((item) => item.id !== workflow.id)];
    renderWorkflowTemplates();
    addLog({ level: 'success', title: '工作流模板已保存', detail: `${workflow.name} / ${workflow.node_count} 节点` });
  }

  async function deleteWorkflowTemplate(id) {
    if (!id) return;
    if (!window.confirm('删除这个工作流模板？')) return;
    await api(`/api/workflows/${encodeURIComponent(id)}`, { method: 'DELETE' });
    workflowTemplates = workflowTemplates.filter((item) => item.id !== id);
    renderWorkflowTemplates();
    addLog({ level: 'info', title: '工作流模板已删除', detail: id });
  }

  async function insertWorkflowTemplate(id) {
    if (!id) return;
    const data = await api(`/api/workflows/${encodeURIComponent(id)}`);
    insertWorkflowPayload(data.workflow?.payload || {}, data.workflow?.name || '工作流模板');
  }

  function insertWorkflowPayload(payload, name = '工作流模板') {
    const sourceNodes = Array.isArray(payload.nodes) ? payload.nodes.map(normalizeNode) : [];
    if (!sourceNodes.length) {
      showToast('模板里没有可加入的节点。', 'warning');
      return;
    }
    const bounds = {
      left: Math.min(...sourceNodes.map((node) => node.x)),
      top: Math.min(...sourceNodes.map((node) => node.y)),
      right: Math.max(...sourceNodes.map((node) => node.x + node.w)),
      bottom: Math.max(...sourceNodes.map((node) => node.y + node.h))
    };
    const center = centerWorldPoint();
    const offsetX = center.x - (bounds.left + bounds.right) / 2;
    const offsetY = center.y - (bounds.top + bounds.bottom) / 2;
    const idMap = new Map();
    const clonedNodes = sourceNodes.map((node) => {
      const clone = normalizeNode({
        ...node,
        id: uid(node.type),
        x: Math.round(node.x + offsetX),
        y: Math.round(node.y + offsetY),
        taskId: '',
        progress: 0,
        progressStartedAt: 0
      });
      if (!clone.resultUrl) clone.status = '';
      idMap.set(node.id, clone.id);
      return clone;
    });
    clonedNodes.forEach((node) => {
      if (node.type === 'group' && Array.isArray(node.children)) {
        node.children = node.children.map((id) => idMap.get(id)).filter(Boolean);
      }
    });
    const clonedEdges = (Array.isArray(payload.edges) ? payload.edges : [])
      .filter((edge) => idMap.has(edge.source) && idMap.has(edge.target))
      .map((edge) => ({ id: uid('edge'), source: idMap.get(edge.source), target: idMap.get(edge.target) }));
    state.nodes.push(...clonedNodes);
    state.edges.push(...clonedEdges);
    selectMany(clonedNodes.map((node) => node.id));
    if (currentView !== 'canvas') showCanvasPage();
    addLog({ level: 'success', title: '已加入工作流模板', detail: `${name} / ${clonedNodes.length} 节点` });
    renderAll();
    setDirty();
  }

  function addDirectorRecipe() {
    if (currentView !== 'canvas') showCanvasPage();
    const center = centerWorldPoint();
    const baseX = Math.round(center.x - 760);
    const baseY = Math.round(center.y - 340);
    const created = [];
    const links = [];
    const makeNode = (type, patch) => {
      const size = defaultSize(type);
      const node = normalizeNode({
        id: uid(type),
        type,
        w: size.w,
        h: size.h,
        title: typeNames[type] || type,
        prompt: defaultPrompt(type),
        ...patch
      });
      created.push(node);
      return node;
    };

    const script = makeNode('prompt', {
      title: '剧本 / 创意输入',
      x: baseX,
      y: baseY,
      w: 420,
      h: 360,
      prompt: '粘贴剧本、产品卖点、角色设定、参考素材说明或短剧梗概。'
    });
    const character = makeNode('llm', {
      title: '角色拆解',
      x: baseX + 500,
      y: baseY - 40,
      w: 400,
      h: 300,
      prompt: '从上游内容拆出每个角色。每个角色必须单独输出：姓名、身份、年龄感、五官、发型、服装、关键道具、性格、连续性注意事项。'
    });
    const scene = makeNode('llm', {
      title: '场景拆解',
      x: baseX + 500,
      y: baseY + 300,
      w: 400,
      h: 300,
      prompt: '从上游内容拆出每个场地。每个场地必须单独输出：地点名称、时间、空间结构、光线、色调、关键陈设、可复用镜头角度。'
    });
    const prop = makeNode('llm', {
      title: '物品拆解',
      x: baseX + 500,
      y: baseY + 640,
      w: 400,
      h: 280,
      prompt: '从上游内容拆出关键物品和道具。每个物品必须单独输出：名称、材质、颜色、尺寸感、使用方式、连续性约束。'
    });
    const storyboard = makeNode('llm', {
      title: '分镜规划',
      x: baseX + 980,
      y: baseY + 160,
      w: 430,
      h: 360,
      prompt: '根据角色、场景和物品拆解，输出可执行分镜。每个分镜单独包含：镜号、时长、画幅、主体、动作、景别、机位、运镜、光线、转场、需要引用的角色/场景/物品。'
    });
    const characterImage = makeNode('image', {
      title: '人物资产生成',
      x: baseX + 1480,
      y: baseY - 140,
      ratio: '9:16',
      imageSize: '2K',
      prompt: '为每个角色分别生成中文真人三视图资产板：白底，左侧精细半身肖像，右侧同一角色全身 A-pose 正视图、侧视图、背面图。面部骨骼、发型、服装、材质和配饰必须严格一致。'
    });
    const sceneImage = makeNode('image', {
      title: '场景资产生成',
      x: baseX + 1480,
      y: baseY + 520,
      ratio: '16:9',
      imageSize: '2K',
      prompt: '为每个场地分别生成中文场景资产板：16:9，完整空间参考，展示主视角、反向视角、关键陈设、光线色调和可拍摄机位，不要混入人物。'
    });
    const propImage = makeNode('image', {
      title: '物品资产生成',
      x: baseX + 1480,
      y: baseY + 1180,
      ratio: '16:9',
      imageSize: '2K',
      prompt: '为每个关键物品分别生成中文道具资产板：白底或浅灰底，展示正面、侧面、背面、细节特写和材质质感，保持比例和结构一致。'
    });
    const video = makeNode('video', {
      title: '分镜视频生成',
      x: baseX + 2040,
      y: baseY + 200,
      aspectRatio: '9:16',
      resolution: '1080p',
      duration: 5,
      prompt: '按分镜逐条生成视频。每条视频必须引用对应角色资产、场景资产和物品资产，保持人物身份、服装、空间、镜头运动和情绪连续。'
    });
    const output = makeNode('output', {
      title: '成片输出',
      x: baseX + 2640,
      y: baseY + 240,
      prompt: '收集分镜视频结果，用于最终交付、预览或文案说明。'
    });

    [
      [script, character],
      [script, scene],
      [script, prop],
      [character, storyboard],
      [scene, storyboard],
      [prop, storyboard],
      [character, characterImage],
      [scene, sceneImage],
      [prop, propImage],
      [storyboard, video],
      [characterImage, video],
      [sceneImage, video],
      [propImage, video],
      [video, output]
    ].forEach(([source, target]) => links.push({ id: uid('edge'), source: source.id, target: target.id }));

    const groupSpecs = [
      ['导演台拆解区', baseX - 36, baseY - 90, 1460, 1050],
      ['人物资产区', baseX + 1440, baseY - 190, 560, 640],
      ['场景资产区', baseX + 1440, baseY + 470, 560, 640],
      ['物品资产区', baseX + 1440, baseY + 1130, 560, 640],
      ['视频任务区', baseX + 2000, baseY + 150, 520, 560],
      ['输出区', baseX + 2600, baseY + 190, 440, 400]
    ].map(([title, x, y, w, h]) => normalizeNode({ id: uid('group'), type: 'group', title, x, y, w, h, prompt: '' }));

    state.nodes.push(...groupSpecs, ...created);
    state.edges.push(...links);
    selectMany(created.map((node) => node.id));
    addLog({ level: 'success', title: '导演台配方已加入', detail: `${created.length} 个节点 / ${links.length} 条连线` });
    renderAll();
    setDirty();
  }

  function addDirectorNode(point = null) {
    if (currentView !== 'canvas') showCanvasPage();
    const center = point || centerWorldPoint();
    const node = addNode('director', {
      x: Math.round(center.x - 380),
      y: Math.round(center.y - 310),
      title: '导演台',
      prompt: defaultPrompt('director')
    });
    addLog({ level: 'info', title: '导演台已加入', detail: '输入剧本或项目设定后运行拆解' });
    return node;
  }

  function addDirectorRecipe() {
    return addDirectorNode();
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

  function openMediaPreview(url) {
    if (!url) return;
    els.mediaPreviewImage.src = url;
    els.mediaPreviewModal.classList.remove('hidden');
  }

  function closeMediaPreview() {
    els.mediaPreviewModal.classList.add('hidden');
    els.mediaPreviewImage.removeAttribute('src');
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
    pendingEdgeConnection = null;
    els.addMenu.classList.remove('connection-menu');
    els.addMenu.classList.add('hidden');
  }

  function positionAddMenu(clientX, clientY) {
    const canvasPoint = clientToCanvas(clientX, clientY);
    addMenuWorldPoint = clientToWorld(clientX, clientY);
    const left = clamp(canvasPoint.x, 12, Math.max(12, els.canvasArea.clientWidth - 202));
    const top = clamp(canvasPoint.y, 12, Math.max(12, els.canvasArea.clientHeight - 250));
    els.addMenu.style.left = `${left}px`;
    els.addMenu.style.top = `${top}px`;
  }

  function showAddMenu(event) {
    if (event.target.closest('.node,.group-node,.toolbar,.canvas-minimap,.add-menu,.canvas-create-dock')) return;
    event.preventDefault();
    pendingEdgeConnection = null;
    els.addMenu.classList.remove('connection-menu');
    positionAddMenu(event.clientX, event.clientY);
    els.addMenu.classList.remove('hidden');
  }

  function showConnectionAddMenu(clientX, clientY) {
    const source = pendingEdgeConnection?.source ? nodeById(pendingEdgeConnection.source) : null;
    if (!source) {
      pendingEdgeConnection = null;
      return;
    }
    positionAddMenu(clientX, clientY);
    els.addMenu.classList.add('connection-menu');
    els.addMenu.classList.remove('hidden');
  }

  function addNodeFromMenu(type) {
    const point = addMenuWorldPoint || centerWorldPoint();
    const pendingConnection = pendingEdgeConnection;
    const node = addNode(type, { x: point.x, y: point.y });
    if (pendingConnection?.source) {
      addEdge(pendingConnection.source, node.id);
      renderAll();
    }
    hideAddMenu();
  }

  function zoomAtCanvasPoint(canvasX, canvasY, nextScale) {
    cancelPanMomentum();
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
    cancelPanMomentum();
    const rect = els.canvasArea.getBoundingClientRect();
    zoomAtCanvasPoint(rect.width / 2, rect.height / 2, state.viewport.scale * factor);
  }

  function centerViewportOnWorld(worldX, worldY) {
    cancelPanMomentum();
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
      cancelPanMomentum();
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

  function shouldPreserveNodeWheel(target) {
    const element = target instanceof Element ? target : target?.parentElement;
    return !!element?.closest('.node-console,.node-stage-copy,.node-result-text,.director-results,input,textarea,select,video,a[href],[contenteditable="true"]');
  }

  function handleWheel(event) {
    if (shouldPreserveNodeWheel(event.target)) return;
    event.preventDefault();
    hideAddMenu();
    cancelPanMomentum();
    const point = clientToCanvas(event.clientX, event.clientY);
    zoomAtCanvasPoint(point.x, point.y, state.viewport.scale * Math.exp(-event.deltaY * 0.0012));
  }

  function showCreateCanvasModal() {
    if (!currentProject) return;
    els.canvasNameInput.value = labels.canvasName;
    els.canvasCreateModal.classList.remove('hidden');
    window.setTimeout(() => {
      els.canvasNameInput.focus();
      els.canvasNameInput.select();
    }, 0);
  }

  function hideCreateCanvasModal() {
    els.canvasCreateModal.classList.add('hidden');
  }

  async function createCanvasWithName(name) {
    if (!currentProject) return;
    name = String(name || '').trim();
    if (!name) return;
    await saveCurrentCanvasIfDirty();
    const data = await api(`/api/projects/${currentProject.id}/canvases`, { method: 'POST', body: JSON.stringify({ name }) });
    canvases.unshift(data.canvas);
    hideAssetDrawer();
    hideCreateCanvasModal();
    await selectCanvas(data.canvas.id);
  }

  function bindEvents() {
    els.toolbar.querySelectorAll('button').forEach((button) => {
      if (!button.title) button.title = button.textContent.trim();
    });
    els.toolbar.querySelectorAll('[data-add]').forEach((button) => {
      button.addEventListener('click', () => {
        if (currentView !== 'canvas') showCanvasPage();
        addNode(button.dataset.add);
      });
    });
    document.querySelectorAll('[data-dock-add]').forEach((button) => {
      button.addEventListener('click', () => {
        if (currentView !== 'canvas') showCanvasPage();
        addNode(button.dataset.dockAdd);
      });
    });
    document.querySelectorAll('[data-dock-action]').forEach((button) => {
      button.addEventListener('click', () => {
        const action = button.dataset.dockAction;
        if (action === 'upload') els.fileInput.click();
        if (action === 'assets') showAssetPage().catch(showError);
      });
    });
    els.addMenu.querySelectorAll('[data-add-menu]').forEach((button) => {
      button.addEventListener('click', (event) => {
        event.stopPropagation();
        addNodeFromMenu(button.dataset.addMenu);
      });
    });
    els.groupBtn.addEventListener('click', groupSelected);
    els.directorRecipeBtn.addEventListener('click', addDirectorNode);
    els.runBtn.addEventListener('click', () => runSelectedNode().catch(showError));
    els.runChainBtn.addEventListener('click', () => runChain().catch(showError));
    els.saveBtn.addEventListener('click', () => saveCanvas().catch(showError));
    els.assetBtn.addEventListener('click', () => showAssetPage().catch(showError));
    els.themeToggleBtn?.addEventListener('click', toggleTheme);
    els.assetDrawerCloseBtn?.addEventListener('click', hideAssetDrawer);
    els.assetDrawerUploadBtn?.addEventListener('click', () => els.fileInput.click());
    els.assetDrawerSearch?.addEventListener('input', renderAssetDrawer);
    els.logBtn.addEventListener('click', showLogsPage);
    els.refreshAssetBtn.addEventListener('click', () => loadAssets().catch(showError));
    els.assetPageRefreshBtn.addEventListener('click', () => loadAssets().catch(showError));
    els.assetBackBtn.addEventListener('click', showCanvasPage);
    els.accountBackBtn?.addEventListener('click', showCanvasPage);
    els.logsBackBtn?.addEventListener('click', showCanvasPage);
    els.assetSearchInput.addEventListener('input', renderAssetPage);
    document.querySelectorAll('[data-asset-tab]').forEach((button) => {
      button.addEventListener('click', () => {
        assetFilter = button.dataset.assetTab || 'all';
        renderAssets();
      });
    });
    els.clearLogBtn.addEventListener('click', () => {
      state.logs = [];
      renderLogs();
      setDirty();
    });
    els.logsPageClearBtn?.addEventListener('click', () => {
      state.logs = [];
      renderLogs();
      setDirty();
    });
    els.exportWorkflowBtn.addEventListener('click', exportWorkflow);
    els.saveWorkflowTemplateBtn.addEventListener('click', () => saveWorkflowTemplate().catch(showError));
    els.copyWorkflowBtn.addEventListener('click', () => copyWorkflowSummary().catch(showError));
    els.backToOriginBtn.addEventListener('click', () => {
      cancelPanMomentum();
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
    els.nodeLayer.addEventListener('click', (event) => {
      const trigger = event.target.closest('[data-preview-media]');
      if (!trigger) return;
      event.preventDefault();
      event.stopPropagation();
      if (suppressNextMediaPreviewClick) {
        suppressNextMediaPreviewClick = false;
        return;
      }
      openMediaPreview(trigger.dataset.previewMedia || '');
    });
    els.mediaPreviewModal.querySelectorAll('[data-preview-close]').forEach((button) => {
      button.addEventListener('click', closeMediaPreview);
    });
    els.mediaPreviewModal.addEventListener('click', (event) => {
      if (event.target === els.mediaPreviewModal) closeMediaPreview();
    });
    els.canvasCreateCancelBtn.addEventListener('click', hideCreateCanvasModal);
    els.canvasCreateCloseBtn.addEventListener('click', hideCreateCanvasModal);
    els.canvasCreateModal.addEventListener('click', (event) => {
      if (event.target === els.canvasCreateModal) hideCreateCanvasModal();
    });
    els.canvasCreateForm.addEventListener('submit', (event) => {
      event.preventDefault();
      createCanvasWithName(els.canvasNameInput.value).catch(showError);
    });
    els.uploadBtn.addEventListener('click', () => els.fileInput.click());
    els.fileInput.addEventListener('change', () => {
      const file = els.fileInput.files && els.fileInput.files[0];
      els.fileInput.value = '';
      uploadFile(file).catch(showError);
    });
    els.canvasArea.addEventListener('wheel', (event) => {
      handleWheel(event);
    }, { passive: false });
    els.canvasArea.addEventListener('pointermove', updateCanvasSpotlight);
    els.canvasArea.addEventListener('pointerleave', clearCanvasSpotlight);
    els.canvasArea.addEventListener('dblclick', showAddMenu);
    els.canvasArea.addEventListener('pointerdown', cancelPanMomentum, true);
    els.canvasArea.addEventListener('pointerdown', startCanvasMiddlePanCapture, true);
    els.canvasArea.addEventListener('pointerdown', (event) => {
      if (event.target.closest('.node,.group-node,.toolbar,.canvas-minimap,.add-menu,.canvas-create-dock')) return;
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
      showCreateCanvasModal();
    });
    els.accountBtn.addEventListener('click', showAccountPage);
    els.closeAccount?.addEventListener('click', () => els.accountModal.classList.add('hidden'));
    const logout = async () => {
      await api('/api/auth/logout', { method: 'POST', body: JSON.stringify({}) });
      location.href = '/login';
    };
    els.logoutBtn?.addEventListener('click', logout);
    els.accountPageLogoutBtn?.addEventListener('click', logout);
    els.passwordChangeForm?.addEventListener('submit', submitPasswordChange);
    window.addEventListener('popstate', applyRouteFromLocation);
    window.addEventListener('keydown', (event) => {
      const editing = event.target instanceof Element
        && !!event.target.closest('input,textarea,select,button,a[href],[contenteditable="true"]');
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        saveCanvas().catch(showError);
        return;
      }
      if (event.code === 'Space' && !editing) {
        spaceDown = true;
        event.preventDefault();
      }
      if (event.key === 'Escape') {
        hideAddMenu();
        hideAssetDrawer();
        closeMediaPreview();
        hideCreateCanvasModal();
      }
      if (editing) return;
      if ((event.key === 'Delete' || event.key === 'Backspace') && selectedEdgeId) {
        event.preventDefault();
        deleteEdge(selectedEdgeId);
      } else if ((event.key === 'Delete' || event.key === 'Backspace') && selectedIds.size) {
        event.preventDefault();
        deleteSelected();
      }
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'g') {
        event.preventDefault();
        groupSelected();
      }
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        runChain().catch(showError);
      }
    });
    window.addEventListener('keyup', (event) => {
      if (event.code === 'Space') spaceDown = false;
    });
    window.addEventListener('blur', () => {
      spaceDown = false;
      endPointerAction({ type: 'pointercancel' });
      cancelPanMomentum();
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
    applyTheme(readSavedTheme());
    applyViewport();
    try {
      const user = await loadMe();
      if (!user) return;
      await loadGenerationCapabilities();
      await loadProjects();
      applyRouteFromLocation();
    } catch (error) {
      showError(error);
    }
  }

  init();
})();
