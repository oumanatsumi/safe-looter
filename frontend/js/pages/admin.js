/* ── Admin Panel ── */

let adminToken = '';

const CFG_KEYS = [
  'cooldown_min', 'cooldown_max',
  'rate_blue', 'rate_purple', 'rate_gold', 'rate_red',
  'menggong_duration',
  'menggong_rate_purple', 'menggong_rate_gold', 'menggong_rate_red',
];

function initAdmin() {
  document.getElementById('adminBtn').addEventListener('click', () => {
    showTokenModal();
  });

  // Token modal
  const tokenInput = document.getElementById('adminTokenInput');
  tokenInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doAdminAuth();
  });
  document.getElementById('adminTokenSubmit').addEventListener('click', doAdminAuth);
  document.getElementById('adminTokenCancel').addEventListener('click', hideTokenModal);

  // Settings modal
  document.getElementById('adminSettingsSave').addEventListener('click', saveSettings);
  document.getElementById('adminSettingsClose').addEventListener('click', hideSettingsModal);

  // Close modals on overlay click
  document.getElementById('adminTokenModal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) hideTokenModal();
  });
  document.getElementById('adminSettingsModal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) hideSettingsModal();
  });
}

// ── Token Modal ──

function showTokenModal() {
  document.getElementById('adminTokenInput').value = '';
  document.getElementById('adminTokenError').classList.add('hidden');
  document.getElementById('adminTokenModal').classList.remove('hidden');
  document.getElementById('adminTokenInput').focus();
}

function hideTokenModal() {
  document.getElementById('adminTokenModal').classList.add('hidden');
}

async function doAdminAuth() {
  const token = document.getElementById('adminTokenInput').value.trim();
  if (!token) return;

  try {
    const data = await API.adminAuth(token);
    if (data.ok) {
      adminToken = token;
      hideTokenModal();
      await loadSettings();
      showSettingsModal();
    } else {
      document.getElementById('adminTokenError').textContent = data.message || '验证失败';
      document.getElementById('adminTokenError').classList.remove('hidden');
    }
  } catch (e) {
    document.getElementById('adminTokenError').textContent = '网络错误';
    document.getElementById('adminTokenError').classList.remove('hidden');
  }
}

// ── Settings Modal ──

function showSettingsModal() {
  document.getElementById('adminSettingsModal').classList.remove('hidden');
}

function hideSettingsModal() {
  document.getElementById('adminSettingsModal').classList.add('hidden');
}

async function loadSettings() {
  try {
    const data = await API.adminGetConfig(adminToken);
    if (!data.ok) {
      showToast('加载配置失败', true);
      return;
    }
    const cfg = data.config;
    for (const key of CFG_KEYS) {
      const el = document.getElementById('cfg_' + key);
      if (el) el.value = cfg[key] || '';
    }
  } catch (e) {
    showToast('加载配置失败', true);
  }
}

async function saveSettings() {
  const updates = {};
  for (const key of CFG_KEYS) {
    const el = document.getElementById('cfg_' + key);
    if (!el) continue;
    const val = el.value.trim();
    if (val === '') {
      showMsg('请填写所有字段', 'error');
      return;
    }
    updates[key] = val;
  }

  try {
    const data = await API.adminSaveConfig(adminToken, updates);
    const cls = data.ok ? 'success' : 'error';
    showMsg(data.message, cls);
  } catch (e) {
    showMsg('保存失败', 'error');
  }
}

function showMsg(msg, cls) {
  const el = document.getElementById('adminSettingsMsg');
  el.textContent = msg;
  el.className = 'modal-msg ' + cls;
  el.classList.remove('hidden');
}
