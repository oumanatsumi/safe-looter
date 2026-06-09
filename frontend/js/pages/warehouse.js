/* ── Warehouse Page ── */

let refreshInterval = null;

function initWarehouse() {
  document.getElementById('btnUpgrade').addEventListener('click', doUpgrade);
  document.getElementById('btnMenggong').addEventListener('click', doMenggong);
  document.getElementById('btnAutoToggle').addEventListener('click', toggleAuto);
}

async function loadWarehouse() {
  const uid = App.getUserId();
  try {
    const data = await API.economy(uid);
    if (!data.ok) return;

    document.getElementById('whValue').textContent = fmt(data.warehouse_value);
    document.getElementById('whLevel').textContent = data.teqin_level + ' 级';
    document.getElementById('whGrid').textContent = `${data.grid_size}x${data.grid_size}`;

    // Menggong status
    const mgDiv = document.getElementById('menggongStatus');
    if (data.menggong_active && data.menggong_remaining > 0) {
      const mins = Math.floor(data.menggong_remaining / 60);
      const secs = data.menggong_remaining % 60;
      mgDiv.innerHTML = `<span style="color:#ff9800">&#x1F525; 猛攻中 — 剩余 ${mins}分${secs}秒</span>`;
    } else {
      mgDiv.innerHTML = '<span>状态: 未激活</span>';
    }

    // Auto touchi status
    const autoDiv = document.getElementById('autoStatus');
    const autoBtn = document.getElementById('btnAutoToggle');
    if (data.auto_touchi_active) {
      const elapsed = Math.floor(Date.now() / 1000) - (data.auto_touchi_start_time || 0);
      const mins = Math.floor(elapsed / 60);
      autoDiv.innerHTML = `<span style="color:#4fc3f7">&#x1F916; 运行中 — 已 ${mins} 分钟 | 红 ${data.auto_touchi_red_count || 0} 个</span>`;
      autoBtn.textContent = '关闭自动偷吃';
      autoBtn.className = 'btn-auto';
      autoBtn.style.background = '#c62828';
    } else {
      autoDiv.innerHTML = '<span>状态: 未开启</span>';
      autoBtn.textContent = '开启自动偷吃';
      autoBtn.className = 'btn-auto';
      autoBtn.style.background = '#00838f';
    }
  } catch (e) {
    showToast('加载仓库数据失败', true);
  }
}

async function doUpgrade() {
  const uid = App.getUserId();
  const data = await API.upgrade(uid);
  showToast(data.message, !data.ok);
  if (data.ok) loadWarehouse();
}

async function doMenggong() {
  const uid = App.getUserId();
  const data = await API.menggong(uid);
  showToast(data.message, !data.ok);
  if (data.ok) loadWarehouse();
}

async function toggleAuto() {
  const uid = App.getUserId();
  const eco = await API.economy(uid);
  let data;
  if (eco.auto_touchi_active) {
    data = await API.autoStop(uid);
  } else {
    data = await API.autoStart(uid);
  }
  showToast(data.message, !data.ok);
  if (data.ok) loadWarehouse();
}

// Auto-refresh warehouse every 30s for menggong/auto timers
function startWarehouseRefresh() {
  if (refreshInterval) clearInterval(refreshInterval);
  refreshInterval = setInterval(loadWarehouse, 30000);
}
