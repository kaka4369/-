(() => {
  const text = {
    add: '调整',
    admin: '管理员',
    configured: '已配置',
    failed: '操作失败',
    member: '普通用户',
    neverUsed: '尚未使用',
    notConfigured: '未配置',
    providerCleared: '已清除 API Key',
    providerSaved: 'API 配置已保存，已对所有用户生效',
    reason: '后台手动调整',
    success: '点数已更新'
  };

  const providerKindMeta = {
    llm: {
      label: '文本模型',
      fetchLabel: '文本模型',
      icon: 'ph-brain',
      urlLabel: '完整请求地址（可选）',
      urlHint: '适用于 Azure 等需要完整部署路径的接口。',
      urlPlaceholder: 'https://api.example.com/v1/chat/completions'
    },
    image: {
      label: '生图模型',
      fetchLabel: '生图模型',
      icon: 'ph-image',
      urlLabel: '图片生成地址',
      urlHint: '填写服务商提供的完整图片生成请求地址。',
      urlPlaceholder: 'https://api.example.com/v1/images/generations'
    },
    video: {
      label: '视频模型',
      fetchLabel: '视频模型',
      icon: 'ph-video-camera',
      urlLabel: '任务提交地址',
      urlHint: '填写服务商提供的视频生成任务提交地址。',
      urlPlaceholder: 'https://api.example.com/v1/video/generations'
    }
  };

  const usersEl = document.getElementById('adminUsers');
  const emptyEl = document.getElementById('adminEmpty');
  const configEl = document.getElementById('adminConfig');
  const toastEl = document.getElementById('adminToastRegion');
  const searchEl = document.getElementById('adminUserSearch');
  const sortEl = document.getElementById('adminUserSort');
  const themeToggleEl = document.getElementById('adminThemeToggle');
  const publicAppLinkEl = document.getElementById('publicAppLink');
  const logoutEl = document.getElementById('adminLogout');
  const pageTitleEl = document.getElementById('adminPageTitle');
  const pageDescriptionEl = document.getElementById('adminPageDescription');
  const usageViewEl = document.getElementById('adminUsageView');
  const providerViewEl = document.getElementById('adminProviderView');
  const sectionTabEls = Array.from(document.querySelectorAll('[data-admin-view]'));
  const providerKindTabEls = Array.from(document.querySelectorAll('[data-provider-kind]'));
  const providerListEl = document.getElementById('adminProviderList');
  const providerFormEl = document.getElementById('adminProviderForm');
  const providerNameEl = document.getElementById('adminProviderName');
  const providerKindLabelEl = document.getElementById('adminProviderKindLabel');
  const providerStateEl = document.getElementById('adminProviderState');
  const providerKeyEl = document.getElementById('adminProviderKey');
  const providerKeyToggleEl = document.getElementById('adminProviderKeyToggle');
  const providerKeyClearEl = document.getElementById('adminProviderKeyClear');
  const providerKeyHintEl = document.getElementById('adminProviderKeyHint');
  const providerBaseUrlFieldEl = document.getElementById('adminProviderBaseUrlField');
  const providerBaseUrlEl = document.getElementById('adminProviderBaseUrl');
  const providerUrlLabelEl = document.getElementById('adminProviderUrlLabel');
  const providerUrlEl = document.getElementById('adminProviderUrl');
  const providerUrlHintEl = document.getElementById('adminProviderUrlHint');
  const providerModelEl = document.getElementById('adminProviderModel');
  const providerModelAddEl = document.getElementById('adminProviderModelAdd');
  const providerModelsFetchEl = document.getElementById('adminProviderModelsFetch');
  const providerModelPickerEl = document.getElementById('adminProviderModelPicker');
  const providerModelSummaryEl = document.getElementById('adminProviderModelSummary');
  const providerModelListEl = document.getElementById('adminProviderModelList');
  const providerModelSelectAllEl = document.getElementById('adminProviderModelSelectAll');
  const providerModelClearEl = document.getElementById('adminProviderModelClear');
  const providerModelDefaultEl = document.getElementById('adminProviderModelDefault');
  const providerModelsStatusEl = document.getElementById('adminProviderModelsStatus');
  const providerStatusUrlFieldEl = document.getElementById('adminProviderStatusUrlField');
  const providerStatusUrlEl = document.getElementById('adminProviderStatusUrl');
  const providerSourceEl = document.getElementById('adminProviderSource');
  const providerSaveEl = document.getElementById('adminProviderSave');
  const providerSaveLabelEl = document.getElementById('adminProviderSaveLabel');
  const numberFormat = new Intl.NumberFormat('zh-CN');
  const dateFormat = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
  let users = [];
  let providers = [];
  let selectedProviderKind = 'llm';
  let selectedProviderName = '';
  let providerFormDirty = false;
  let providerConnectionDirty = false;
  let providerModelsRequestId = 0;
  let providerModelCandidates = [];
  let providerSelectedModels = new Set();
  let providerDefaultModel = '';

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    }[char]));
  }

  function safeNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? number : 0;
  }

  function formatNumber(value) {
    return numberFormat.format(safeNumber(value));
  }

  function formatDate(value) {
    const timestamp = safeNumber(value);
    return timestamp > 0 ? dateFormat.format(new Date(timestamp)) : text.neverUsed;
  }

  async function api(path, options = {}) {
    const res = await fetch(path, {
      credentials: 'same-origin',
      cache: 'no-store',
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }
    });
    if (res.status === 401) {
      location.href = '/login';
      throw new Error('unauthorized');
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || text.failed);
    return data;
  }

  function showAdminToast(message, tone = 'error') {
    if (!toastEl) return;
    const toast = document.createElement('div');
    toast.className = `toast-message ${tone}`;
    toast.setAttribute('role', tone === 'error' ? 'alert' : 'status');
    toast.textContent = String(message || text.failed);
    toastEl.appendChild(toast);
    window.setTimeout(() => toast.remove(), 4200);
  }

  function applyTheme(theme, persist = false) {
    const dark = theme === 'dark';
    document.documentElement.dataset.theme = dark ? 'dark' : 'light';
    document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
    themeToggleEl?.setAttribute('aria-pressed', dark ? 'true' : 'false');
    themeToggleEl?.setAttribute('aria-label', dark ? '切换到白天模式' : '切换到黑夜模式');
    const icon = themeToggleEl?.querySelector('i');
    const label = themeToggleEl?.querySelector('span');
    icon?.classList.toggle('ph-sun', dark);
    icon?.classList.toggle('ph-moon', !dark);
    if (label) label.textContent = dark ? '白天' : '黑夜';
    if (persist) localStorage.setItem('canvas-saas-theme', dark ? 'dark' : 'light');
  }

  function configureNavigation() {
    if (location.hostname.startsWith('admin.')) {
      const rootHost = location.hostname.slice(6);
      const appHost = rootHost.startsWith('canvas.') ? rootHost : `canvas.${rootHost}`;
      publicAppLinkEl.href = `${location.protocol}//${appHost}/`;
    }
    applyTheme(document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light');
    themeToggleEl?.addEventListener('click', () => {
      applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark', true);
    });
    logoutEl?.addEventListener('click', async () => {
      logoutEl.disabled = true;
      try {
        await api('/api/auth/logout', { method: 'POST' });
      } finally {
        location.href = '/login';
      }
    });
  }

  function confirmDiscardProviderChanges() {
    return !providerFormDirty || window.confirm('当前配置尚未保存，确定放弃这些更改吗？');
  }

  function setAdminView(view, updateHistory = true) {
    const providerView = view === 'providers';
    usageViewEl.hidden = providerView;
    providerViewEl.hidden = !providerView;
    sectionTabEls.forEach((button) => {
      const active = button.dataset.adminView === (providerView ? 'providers' : 'usage');
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    pageTitleEl.textContent = providerView ? 'API 配置' : '用户用量';
    pageDescriptionEl.textContent = providerView
      ? '管理文本、生图与视频节点使用的服务商接口。'
      : '查看每位用户的点数余额、任务消耗与模型使用情况。';
    if (updateHistory) {
      history.replaceState(null, '', providerView ? `${location.pathname}#api` : location.pathname);
    }
  }

  function providersForKind(kind = selectedProviderKind) {
    return providers.filter((item) => item.kind === kind);
  }

  function selectedProvider() {
    return providers.find((item) => item.kind === selectedProviderKind && item.provider === selectedProviderName) || null;
  }

  function providerStatusLabel(provider) {
    if (!provider) return text.notConfigured;
    return provider.configured ? text.configured : text.notConfigured;
  }

  function renderProviderList() {
    const items = providersForKind();
    providerListEl.innerHTML = items.map((provider) => {
      const active = provider.provider === selectedProviderName;
      return `
        <button class="admin-provider-option ${active ? 'active' : ''}" type="button" data-provider-name="${escapeHtml(provider.provider)}" aria-pressed="${active ? 'true' : 'false'}">
          <span class="admin-provider-option-icon" aria-hidden="true"><i class="ph ${providerKindMeta[provider.kind].icon}"></i></span>
          <span>
            <strong>${escapeHtml(provider.provider)}</strong>
            <small>${provider.source === 'admin' ? '管理员配置' : '服务器环境'}</small>
          </span>
          <span class="admin-provider-option-state ${provider.configured ? 'ready' : 'missing'}" aria-label="${providerStatusLabel(provider)}"></span>
        </button>
      `;
    }).join('');

    providerListEl.querySelectorAll('[data-provider-name]').forEach((button) => {
      button.addEventListener('click', () => {
        if (button.dataset.providerName === selectedProviderName || !confirmDiscardProviderChanges()) return;
        selectedProviderName = button.dataset.providerName;
        renderProviderList();
        renderProviderForm();
      });
    });
  }

  function resetProviderKeyVisibility() {
    providerKeyEl.type = 'password';
    providerKeyToggleEl.setAttribute('aria-pressed', 'false');
    providerKeyToggleEl.setAttribute('aria-label', '显示本次输入的密钥');
    providerKeyToggleEl.querySelector('.admin-secret-eye')?.classList.remove('revealed');
  }

  function setProviderModelsStatus(message, tone = '') {
    providerModelsStatusEl.textContent = message;
    providerModelsStatusEl.className = `admin-model-status${tone ? ` ${tone}` : ''}`;
  }

  function normalizeProviderModels(values) {
    const seen = new Set();
    return (Array.isArray(values) ? values : []).map((value) => String(value || '').trim()).filter((value) => {
      if (!value || value.length > 120 || seen.has(value)) return false;
      seen.add(value);
      return true;
    });
  }

  function selectedProviderModels() {
    return providerModelCandidates.filter((model) => providerSelectedModels.has(model));
  }

  function providerFetchButtonLabel() {
    return `拉取${providerKindMeta[selectedProviderKind]?.fetchLabel || '模型'}`;
  }

  function updateProviderModelMeta() {
    const selected = selectedProviderModels();
    if (!selected.includes(providerDefaultModel)) providerDefaultModel = selected[0] || '';
    providerModelSummaryEl.textContent = `已选择 ${selected.length} 个 · 共 ${providerModelCandidates.length} 个`;
    providerModelSelectAllEl.disabled = !providerModelCandidates.length || selected.length === providerModelCandidates.length;
    providerModelClearEl.disabled = !selected.length;

    const options = selected.map((model) => {
      const option = document.createElement('option');
      option.value = model;
      option.textContent = model;
      return option;
    });
    providerModelDefaultEl.replaceChildren(...options);
    providerModelDefaultEl.disabled = !selected.length;
    providerModelDefaultEl.value = providerDefaultModel;
    providerSaveLabelEl.textContent = `保存配置（${selected.length} 个模型）`;
  }

  function renderProviderModelOptions() {
    const rows = providerModelCandidates.map((model, index) => {
      const row = document.createElement('label');
      row.className = 'admin-model-option';
      row.htmlFor = `adminProviderModelOption${index}`;

      const checkbox = document.createElement('input');
      checkbox.id = row.htmlFor;
      checkbox.type = 'checkbox';
      checkbox.dataset.model = model;
      checkbox.checked = providerSelectedModels.has(model);

      const name = document.createElement('span');
      name.textContent = model;
      name.title = model;
      row.append(checkbox, name);
      return row;
    });
    providerModelListEl.replaceChildren(...rows);
    providerModelPickerEl.hidden = !providerModelCandidates.length;
    updateProviderModelMeta();
  }

  function resetProviderModels(models = [], defaultModel = '') {
    providerModelsRequestId += 1;
    const savedModels = normalizeProviderModels([...models, defaultModel]);
    providerModelCandidates = savedModels;
    providerSelectedModels = new Set(savedModels);
    providerDefaultModel = savedModels.includes(defaultModel) ? defaultModel : (savedModels[0] || '');
    providerModelEl.value = '';
    renderProviderModelOptions();
    providerModelsFetchEl.disabled = false;
    providerModelsFetchEl.classList.remove('is-loading');
    providerModelsFetchEl.setAttribute('aria-busy', 'false');
    providerModelsFetchEl.querySelector('span').textContent = providerFetchButtonLabel();
    const label = providerKindMeta[selectedProviderKind]?.fetchLabel || '模型';
    setProviderModelsStatus(savedModels.length
      ? `已保存 ${savedModels.length} 个${label}；修改后点击“保存配置”才会对所有用户生效。`
      : `可手动添加，或从已保存的请求地址拉取${label}。`);
  }

  function mergeProviderModels(models) {
    providerModelCandidates = normalizeProviderModels([...providerModelCandidates, ...models]);
    renderProviderModelOptions();
  }

  function markProviderFormDirty() {
    providerFormDirty = true;
    providerStateEl.textContent = '未保存';
    providerStateEl.className = 'admin-provider-state changed';
  }

  function addManualProviderModel() {
    const model = providerModelEl.value.trim();
    if (!model) {
      setProviderModelsStatus('请输入要添加的模型 ID。', 'warning');
      providerModelEl.focus();
      return;
    }
    if (!providerModelCandidates.includes(model)) providerModelCandidates.push(model);
    providerSelectedModels.add(model);
    if (!providerDefaultModel) providerDefaultModel = model;
    providerModelEl.value = '';
    renderProviderModelOptions();
    markProviderFormDirty();
    setProviderModelsStatus(`已添加并选择 ${model}；保存后对所有用户生效。`, 'success');
  }

  function renderProviderForm() {
    const provider = selectedProvider();
    const meta = providerKindMeta[selectedProviderKind];
    if (!provider) {
      providerFormEl.hidden = true;
      return;
    }
    providerFormEl.hidden = false;
    providerKindLabelEl.textContent = meta.label;
    providerNameEl.textContent = provider.provider;
    providerStateEl.textContent = providerStatusLabel(provider);
    providerStateEl.className = `admin-provider-state ${provider.configured ? 'ready' : 'missing'}`;
    providerKeyEl.value = '';
    providerKeyEl.placeholder = provider.has_api_key ? '输入新 Key 可替换当前密钥' : '输入 API Key';
    providerKeyHintEl.textContent = provider.has_api_key
      ? `已保存 ${provider.key_preview || '••••••••'}；留空不会覆盖`
      : '尚未保存密钥';
    providerKeyClearEl.disabled = !provider.has_api_key;
    providerBaseUrlEl.value = provider.base_url || '';
    providerUrlEl.value = provider.url || '';
    providerStatusUrlEl.value = provider.status_url_template || '';
    providerBaseUrlFieldEl.hidden = selectedProviderKind !== 'llm';
    providerStatusUrlFieldEl.hidden = selectedProviderKind !== 'video';
    providerUrlLabelEl.textContent = meta.urlLabel;
    providerUrlHintEl.textContent = meta.urlHint;
    providerUrlEl.placeholder = meta.urlPlaceholder;
    providerSourceEl.innerHTML = provider.source === 'admin'
      ? '<i class="ph ph-notepad" aria-hidden="true"></i> 当前使用管理员配置，保存后立即生效'
      : '<i class="ph ph-gauge" aria-hidden="true"></i> 当前读取服务器环境配置，保存后转为管理员配置';
    providerFormDirty = false;
    providerConnectionDirty = false;
    resetProviderModels(Array.isArray(provider.models) ? provider.models : [], provider.model || '');
    resetProviderKeyVisibility();
  }

  function selectProviderKind(kind, force = false) {
    if (!providerKindMeta[kind] || (kind !== selectedProviderKind && !force && !confirmDiscardProviderChanges())) return;
    selectedProviderKind = kind;
    const items = providersForKind(kind);
    if (!items.some((item) => item.provider === selectedProviderName)) {
      selectedProviderName = items[0]?.provider || '';
    }
    providerKindTabEls.forEach((button) => {
      const active = button.dataset.providerKind === kind;
      button.classList.toggle('active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
    });
    renderProviderList();
    renderProviderForm();
  }

  function updateProvider(updated) {
    const index = providers.findIndex((item) => item.kind === updated.kind && item.provider === updated.provider);
    if (index >= 0) providers[index] = updated;
  }

  async function loadProviders() {
    const data = await api('/api/admin/providers');
    providers = Array.isArray(data.providers) ? data.providers : [];
    selectProviderKind(selectedProviderKind, true);
  }

  function providerPayload() {
    const models = selectedProviderModels();
    const payload = {
      url: providerUrlEl.value.trim(),
      models,
      model: models.includes(providerDefaultModel) ? providerDefaultModel : (models[0] || '')
    };
    const key = providerKeyEl.value.trim();
    if (key) payload.api_key = key;
    if (selectedProviderKind === 'llm') payload.base_url = providerBaseUrlEl.value.trim();
    if (selectedProviderKind === 'video') payload.status_url_template = providerStatusUrlEl.value.trim();
    return payload;
  }

  async function saveProviderConfig(event) {
    event.preventDefault();
    const provider = selectedProvider();
    if (!provider) return;
    const modelCount = selectedProviderModels().length;
    const modelLabel = providerKindMeta[selectedProviderKind]?.fetchLabel || '模型';
    providerSaveEl.disabled = true;
    providerFormEl.setAttribute('aria-busy', 'true');
    try {
      const data = await api(`/api/admin/providers/${encodeURIComponent(provider.kind)}/${encodeURIComponent(provider.provider)}`, {
        method: 'PUT',
        body: JSON.stringify(providerPayload())
      });
      updateProvider(data.provider);
      providerKeyEl.value = '';
      renderProviderList();
      renderProviderForm();
      await loadConfig();
      showAdminToast(`已保存 ${modelCount} 个${modelLabel}，已对所有用户生效`, 'success');
    } catch (error) {
      showAdminToast(error.message || text.failed, 'error');
    } finally {
      providerSaveEl.disabled = false;
      providerFormEl.setAttribute('aria-busy', 'false');
    }
  }

  async function fetchProviderModels() {
    const provider = selectedProvider();
    if (!provider) return;
    const modelLabel = providerKindMeta[selectedProviderKind]?.fetchLabel || '模型';
    if (providerConnectionDirty) {
      setProviderModelsStatus('当前表单有未保存内容，请先保存配置再拉取。', 'warning');
      return;
    }
    const requestId = ++providerModelsRequestId;
    providerModelsFetchEl.disabled = true;
    providerModelsFetchEl.classList.add('is-loading');
    providerModelsFetchEl.setAttribute('aria-busy', 'true');
    providerModelsFetchEl.querySelector('span').textContent = '拉取中…';
    setProviderModelsStatus('正在安全读取服务商模型列表…');
    try {
      const data = await api(`/api/admin/providers/${encodeURIComponent(provider.kind)}/${encodeURIComponent(provider.provider)}/models`, {
        method: 'POST'
      });
      if (requestId !== providerModelsRequestId) return;
      const models = normalizeProviderModels(data.models);
      mergeProviderModels(models);
      const tone = models.length && data.complete !== false ? 'success' : 'warning';
      const successMessage = `已拉取 ${models.length} 个${modelLabel}并合并到候选列表；勾选后点击“保存配置”才会对所有用户生效。`;
      setProviderModelsStatus(models.length ? successMessage : `接口未返回${modelLabel}，仍可手动添加。`, tone);
      if (models.length) providerModelListEl.querySelector('input[type="checkbox"]')?.focus();
    } catch (error) {
      if (requestId !== providerModelsRequestId) return;
      setProviderModelsStatus(error.message || text.failed, 'error');
    } finally {
      if (requestId === providerModelsRequestId) {
        providerModelsFetchEl.disabled = false;
        providerModelsFetchEl.classList.remove('is-loading');
        providerModelsFetchEl.setAttribute('aria-busy', 'false');
        providerModelsFetchEl.querySelector('span').textContent = providerFetchButtonLabel();
      }
    }
  }

  async function clearProviderKey() {
    const provider = selectedProvider();
    if (!provider?.has_api_key || !window.confirm(`确定清除“${provider.provider}”已保存的 API Key 吗？清除后该服务可能不可用。`)) return;
    providerKeyClearEl.disabled = true;
    try {
      const data = await api(`/api/admin/providers/${encodeURIComponent(provider.kind)}/${encodeURIComponent(provider.provider)}`, {
        method: 'PUT',
        body: JSON.stringify({ clear_api_key: true })
      });
      updateProvider(data.provider);
      renderProviderList();
      renderProviderForm();
      await loadConfig();
      showAdminToast(text.providerCleared, 'success');
    } catch (error) {
      providerKeyClearEl.disabled = false;
      showAdminToast(error.message || text.failed, 'error');
    }
  }

  function bindProviderControls() {
    sectionTabEls.forEach((button) => {
      button.addEventListener('click', () => setAdminView(button.dataset.adminView));
    });
    providerKindTabEls.forEach((button) => {
      button.addEventListener('click', () => selectProviderKind(button.dataset.providerKind));
    });
    providerFormEl.addEventListener('input', (event) => {
      if (event.target === providerModelEl) return;
      markProviderFormDirty();
      if (!event.target.closest('#adminProviderModelPicker')) providerConnectionDirty = true;
    });
    providerFormEl.addEventListener('submit', saveProviderConfig);
    providerModelsFetchEl.addEventListener('click', fetchProviderModels);
    providerModelAddEl.addEventListener('click', addManualProviderModel);
    providerModelEl.addEventListener('keydown', (event) => {
      if (event.key !== 'Enter') return;
      event.preventDefault();
      addManualProviderModel();
    });
    providerModelListEl.addEventListener('change', (event) => {
      const checkbox = event.target.closest('input[type="checkbox"][data-model]');
      if (!checkbox) return;
      const model = checkbox.dataset.model || '';
      if (checkbox.checked) providerSelectedModels.add(model);
      else providerSelectedModels.delete(model);
      updateProviderModelMeta();
      markProviderFormDirty();
      setProviderModelsStatus(`已选择 ${selectedProviderModels().length} 个模型；保存后对所有用户生效。`, 'success');
    });
    providerModelSelectAllEl.addEventListener('click', () => {
      providerModelCandidates.forEach((model) => providerSelectedModels.add(model));
      providerModelListEl.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => { checkbox.checked = true; });
      updateProviderModelMeta();
      markProviderFormDirty();
      setProviderModelsStatus(`已选择全部 ${providerModelCandidates.length} 个模型；保存后对所有用户生效。`, 'success');
    });
    providerModelClearEl.addEventListener('click', () => {
      providerSelectedModels.clear();
      providerModelListEl.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => { checkbox.checked = false; });
      updateProviderModelMeta();
      markProviderFormDirty();
      setProviderModelsStatus('已清空模型选择；保存后该供应商将不向用户提供模型。', 'warning');
    });
    providerModelDefaultEl.addEventListener('change', () => {
      const model = providerModelDefaultEl.value.trim();
      if (!providerSelectedModels.has(model)) return;
      providerDefaultModel = model;
      markProviderFormDirty();
      setProviderModelsStatus(`已将 ${model} 设为默认模型；保存后对所有用户生效。`, 'success');
    });
    providerKeyClearEl.addEventListener('click', clearProviderKey);
    providerKeyToggleEl.addEventListener('click', () => {
      const reveal = providerKeyEl.type === 'password';
      providerKeyEl.type = reveal ? 'text' : 'password';
      providerKeyToggleEl.setAttribute('aria-pressed', reveal ? 'true' : 'false');
      providerKeyToggleEl.setAttribute('aria-label', reveal ? '隐藏本次输入的密钥' : '显示本次输入的密钥');
      providerKeyToggleEl.querySelector('.admin-secret-eye')?.classList.toggle('revealed', reveal);
    });
    window.addEventListener('hashchange', () => setAdminView(location.hash === '#api' ? 'providers' : 'usage', false));
  }

  function statusPill(kind, label, configured, icon) {
    return `
      <button class="admin-config-pill ${configured ? 'ready' : 'missing'}" type="button" data-open-provider-kind="${kind}">
        <i class="ph ${icon}" aria-hidden="true"></i>
        ${escapeHtml(label)} · ${configured ? text.configured : text.notConfigured}
      </button>
    `;
  }

  async function loadConfig() {
    const data = await api('/api/admin/config');
    configEl.innerHTML = `
      <div class="admin-config-status">
        ${statusPill('llm', 'LLM', data.llm_configured, 'ph-brain')}
        ${statusPill('image', '生图', data.image_configured, 'ph-image')}
        ${statusPill('video', '视频', data.video_configured, 'ph-video-camera')}
      </div>
      <span class="admin-cost-note">单次点数：LLM ${formatNumber(data.costs.llm)} · 生图 ${formatNumber(data.costs.image)} · 视频 ${formatNumber(data.costs.video)}</span>
    `;
    configEl.querySelectorAll('[data-open-provider-kind]').forEach((button) => {
      button.addEventListener('click', () => {
        setAdminView('providers');
        selectProviderKind(button.dataset.openProviderKind, true);
      });
    });
  }

  function renderSummary() {
    const totals = users.reduce((result, user) => {
      result.consumed += safeNumber(user.consumed_credits);
      result.pending += safeNumber(user.pending_credits);
      result.balance += safeNumber(user.credits);
      return result;
    }, { consumed: 0, pending: 0, balance: 0 });
    document.getElementById('summaryUsers').textContent = formatNumber(users.length);
    document.getElementById('summaryConsumed').textContent = formatNumber(totals.consumed);
    document.getElementById('summaryPending').textContent = formatNumber(totals.pending);
    document.getElementById('summaryBalance').textContent = formatNumber(totals.balance);
  }

  function sortedFilteredUsers() {
    const query = String(searchEl?.value || '').trim().toLowerCase();
    const mode = sortEl?.value || 'consumed';
    const filtered = users.filter((user) => String(user.email || '').toLowerCase().includes(query));
    const sorters = {
      balance: (a, b) => safeNumber(b.credits) - safeNumber(a.credits),
      consumed: (a, b) => safeNumber(b.consumed_credits) - safeNumber(a.consumed_credits),
      created: (a, b) => safeNumber(b.created_at) - safeNumber(a.created_at),
      recent: (a, b) => safeNumber(b.last_task_at) - safeNumber(a.last_task_at)
    };
    return filtered.sort(sorters[mode] || sorters.consumed);
  }

  function usageChip(label, value, tone) {
    return `<span class="admin-usage-chip ${tone}">${escapeHtml(label)} <strong>${formatNumber(value)}</strong></span>`;
  }

  function userRowHtml(user) {
    const initial = String(user.email || '?').trim().charAt(0).toUpperCase();
    return `
      <div class="admin-user" role="row" data-user-id="${escapeHtml(user.id)}">
        <div class="admin-user-identity" role="cell" data-label="用户">
          <span class="admin-user-avatar" aria-hidden="true">${escapeHtml(initial)}</span>
          <div>
            <strong>${escapeHtml(user.email)}</strong>
            <span>${user.is_admin ? text.admin : text.member} · ${formatDate(user.created_at)} 注册</span>
          </div>
        </div>
        <div class="admin-number-cell" role="cell" data-label="余额">
          <strong>${formatNumber(user.credits)}</strong><span>点</span>
        </div>
        <div class="admin-number-cell admin-consumed-cell" role="cell" data-label="实际消耗">
          <strong>${formatNumber(user.consumed_credits)}</strong><span>点</span>
          <small>占用 ${formatNumber(user.pending_credits)} · 已退 ${formatNumber(user.refunded_credits)}</small>
        </div>
        <div class="admin-task-cell" role="cell" data-label="任务">
          <strong>${formatNumber(user.task_count)} 次</strong>
          <span>成功 ${formatNumber(user.succeeded_count)} · 失败 ${formatNumber(user.failed_count)}</span>
          ${safeNumber(user.active_count) > 0 ? `<small>${formatNumber(user.active_count)} 个处理中</small>` : ''}
        </div>
        <div class="admin-model-cell" role="cell" data-label="模型消耗">
          ${usageChip('LLM', user.llm_credits, 'blue')}
          ${usageChip('生图', user.image_credits, 'violet')}
          ${usageChip('视频', user.video_credits, 'orange')}
        </div>
        <div class="admin-date-cell" role="cell" data-label="最后使用">
          <strong>${formatDate(user.last_task_at)}</strong>
        </div>
        <div class="admin-credit-action" role="cell" data-label="点数调整">
          <input data-credit-input class="inline-input" type="number" step="1" value="100" aria-label="调整 ${escapeHtml(user.email)} 的点数" />
          <button data-credit-button class="primary-button" type="button">${text.add}</button>
        </div>
      </div>
    `;
  }

  function bindCreditActions() {
    usersEl.querySelectorAll('[data-user-id]').forEach((row) => {
      const button = row.querySelector('[data-credit-button]');
      const input = row.querySelector('[data-credit-input]');
      button?.addEventListener('click', async () => {
        const delta = parseInt(input.value, 10);
        if (!Number.isFinite(delta) || delta === 0) return;
        button.disabled = true;
        button.textContent = '处理中…';
        try {
          await api(`/api/admin/users/${row.dataset.userId}/credits`, {
            method: 'POST',
            body: JSON.stringify({ delta, reason: text.reason })
          });
          await loadUsers();
          showAdminToast(text.success, 'success');
        } catch (error) {
          showAdminToast(error.message || text.failed, 'error');
          button.disabled = false;
          button.textContent = text.add;
        }
      });
    });
  }

  function renderUsers() {
    const visibleUsers = sortedFilteredUsers();
    usersEl.innerHTML = visibleUsers.map(userRowHtml).join('');
    emptyEl.classList.toggle('hidden', visibleUsers.length > 0);
    bindCreditActions();
  }

  async function loadUsers() {
    const data = await api('/api/admin/users');
    users = Array.isArray(data.users) ? data.users : [];
    renderSummary();
    renderUsers();
  }

  async function boot() {
    configureNavigation();
    bindProviderControls();
    setAdminView(location.hash === '#api' ? 'providers' : 'usage', false);
    searchEl?.addEventListener('input', renderUsers);
    sortEl?.addEventListener('change', renderUsers);
    await Promise.all([loadConfig(), loadUsers(), loadProviders()]);
  }

  boot().catch((error) => showAdminToast(error.message || text.failed, 'error'));
})();
