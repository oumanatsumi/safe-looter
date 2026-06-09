/* ── Collection Page ── */

async function loadCollection() {
  const uid = App.getUserId();
  const grid = document.getElementById('collectionGrid');
  const progress = document.getElementById('collProgress');

  try {
    const data = await API.collection(uid);
    if (!data.ok) {
      grid.innerHTML = '<p style="text-align:center;color:#888;padding:40px;">暂无收集</p>';
      progress.textContent = '';
      return;
    }

    progress.textContent = `(金 ${data.gold_count} / 红 ${data.red_count} — 共 ${data.total_count})`;

    if (data.items.length === 0) {
      grid.innerHTML = '<p style="text-align:center;color:#888;padding:40px;">还没有收集到金/红物品，快去偷吃吧！</p>';
      return;
    }

    grid.innerHTML = data.items.map(it => `
      <div class="collection-item level-${it.level}">
        <img src="${it.image_url}" alt="${it.name}" loading="lazy">
        <span class="item-name">${it.name}</span>
        <span class="item-value" style="color:${levelColor(it.level)}">${fmt(it.value)}</span>
      </div>
    `).join('');
  } catch (e) {
    grid.innerHTML = '<p style="text-align:center;color:#c62828;padding:40px;">加载失败</p>';
  }
}

function initCollection() {
  // Loaded on page switch via app.js
}
