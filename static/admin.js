(() => {
  const text = {
    add: '\u5145\u503c',
    admin: '\u7ba1\u7406\u5458',
    configured: '\u5df2\u914d\u7f6e',
    credits: '\u70b9',
    failed: '\u64cd\u4f5c\u5931\u8d25',
    notConfigured: '\u672a\u914d\u7f6e',
    reason: '\u540e\u53f0\u624b\u52a8\u5145\u503c',
    user: '\u7528\u6237'
  };

  const usersEl = document.getElementById('adminUsers');
  const configEl = document.getElementById('adminConfig');
  const toastEl = document.getElementById('adminToastRegion');

  function escapeHtml(value) {
    return String(value || '').replace(/[&<>"']/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    }[char]));
  }

  async function api(path, options = {}) {
    const res = await fetch(path, {
      credentials: 'same-origin',
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

  function statusText(value) {
    return value ? text.configured : text.notConfigured;
  }

  function showAdminToast(message, tone = 'error') {
    if (!toastEl) return;
    const toast = document.createElement('div');
    toast.className = `toast-message ${tone}`;
    toast.setAttribute('role', tone === 'error' ? 'alert' : 'status');
    toast.textContent = String(message || text.failed);
    toastEl.appendChild(toast);
    window.setTimeout(() => {
      toast.remove();
    }, 4200);
  }

  async function loadConfig() {
    const data = await api('/api/admin/config');
    configEl.innerHTML = `
      <span class="pill">LLM: ${statusText(data.llm_configured)}</span>
      <span class="pill">Image: ${statusText(data.image_configured)}</span>
      <span class="pill">Video: ${statusText(data.video_configured)}</span>
      <span class="pill">Cost LLM ${data.costs.llm} / Image ${data.costs.image} / Video ${data.costs.video}</span>
    `;
  }

  async function loadUsers() {
    const data = await api('/api/admin/users');
    const users = data.users || [];
    usersEl.innerHTML = '';
    users.forEach((user) => {
      const row = document.createElement('div');
      row.className = 'admin-user';
      row.innerHTML = `
        <div><strong>${escapeHtml(user.email)}</strong><span>${escapeHtml(user.id)}</span></div>
        <strong>${user.credits || 0} ${text.credits}</strong>
        <span>${user.is_admin ? text.admin : text.user}</span>
        <input class="inline-input" type="number" step="1" value="100" />
        <button class="primary-button">${text.add}</button>
      `;
      row.querySelector('button').addEventListener('click', async () => {
        const input = row.querySelector('input');
        const delta = parseInt(input.value, 10);
        if (!Number.isFinite(delta) || delta === 0) return;
        await api(`/api/admin/users/${user.id}/credits`, {
          method: 'POST',
          body: JSON.stringify({ delta, reason: text.reason })
        });
        await loadUsers();
      });
      usersEl.appendChild(row);
    });
  }

  async function boot() {
    await loadConfig();
    await loadUsers();
  }

  boot().catch((error) => showAdminToast(error.message || text.failed, 'error'));
})();
