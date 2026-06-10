/* ── Touchi Page ── */

const CD_STORAGE_KEY = 'touchi_cooldown_end';
let touchiCooldown = 0;
let countdownInterval = null;
let revealTimeout = null;

function initTouchi() {
  const btn = document.getElementById('touchiBtn');
  btn.addEventListener('click', () => {
    if (touchiCooldown > 0) return;
    doTouchi();
  });

  // Restore cooldown on page load
  restoreCooldown();
}

/** Restore cooldown from backend (authoritative) + localStorage (instant) */
async function restoreCooldown() {
  const uid = App.getUserId();

  // 1. Instant: check localStorage for saved cooldown
  const savedEnd = localStorage.getItem(CD_STORAGE_KEY + '_' + uid);
  if (savedEnd) {
    const remaining = Math.ceil((parseInt(savedEnd) - Date.now()) / 1000);
    if (remaining > 0) {
      startCooldown(remaining);
    } else {
      localStorage.removeItem(CD_STORAGE_KEY + '_' + uid);
    }
  }

  // 2. Authoritative: ask backend (handles cross-device / cleared localStorage)
  try {
    const data = await API.economy(uid);
    if (data.ok && data.touchi_cooldown_remaining) {
      const backendRemaining = data.touchi_cooldown_remaining;
      if (backendRemaining > 0) {
        startCooldown(backendRemaining);
        localStorage.setItem(CD_STORAGE_KEY + '_' + uid, Date.now() + backendRemaining * 1000);
      }
    }
  } catch (e) {
    // Silently ignore — localStorage fallback is sufficient
  }
}

async function doTouchi() {
  const uid = App.getUserId();
  const btn = document.getElementById('touchiBtn');
  const btnText = btn.querySelector('.btn-text');
  const resultArea = document.getElementById('resultArea');

  btn.disabled = true;
  resultArea.classList.add('hidden');

  // Loading dots animation
  let dots = 0;
  if (btnText) btnText.textContent = '偷吃中';
  const dotsInterval = setInterval(() => {
    dots = (dots + 1) % 4;
    if (btnText) btnText.textContent = '偷吃中' + '.'.repeat(dots);
  }, 400);

  try {
    const data = await API.touchi(uid);
    clearInterval(dotsInterval);
    if (btnText) btnText.textContent = '偷 吃';

    if (!data.ok) {
      showToast(data.message, true);
      btn.disabled = false;
      return;
    }

    // Apply cooldown
    const waitTime = data.wait_time || 60;
    startCooldown(waitTime);

    // Show event message if triggered
    const eventDiv = document.getElementById('eventMessage');
    if (data.event && data.event.message) {
      eventDiv.textContent = data.event.message;
      eventDiv.classList.remove('hidden');
    } else {
      eventDiv.classList.add('hidden');
    }

    // Show result area (grid visible immediately, items hidden until animation done)
    resultArea.classList.remove('hidden');

    // Build safe grid & animate — callbacks fire after all items revealed
    buildSafeGrid(data, () => {
      // Update value info and show item list after animation completes
      document.getElementById('resultValue').textContent = fmt(data.total_value);

      const profitEl = document.getElementById('resultProfit');
      if (data.total_profit > 0) {
        profitEl.textContent = `本次收益: +${fmt(data.total_profit)} 哈夫币`;
        profitEl.classList.remove('hidden');
      } else {
        profitEl.classList.add('hidden');
      }

      // Build item cards below the grid
      const itemsDiv = document.getElementById('resultItems');
      itemsDiv.innerHTML = data.items.map(it => `
        <div class="result-item level-${it.level}">
          <img src="${it.image_url}" alt="${it.name}" loading="lazy">
          <span class="item-name">${it.name}</span>
          <span class="item-value" style="color:${levelColor(it.level)}">${fmt(it.value)}</span>
        </div>
      `).join('');
      itemsDiv.classList.remove('hidden');
    });

    // Refresh header economy
    App.refreshHeader();
  } catch (e) {
    clearInterval(dotsInterval);
    if (btnText) btnText.textContent = '偷 吃';
    showToast('网络错误，请重试', true);
    btn.disabled = false;
  }
}

/** Build the CSS grid with item slots and animate reveal sequence */
function buildSafeGrid(data, onComplete) {
  const gridEl = document.getElementById('safeGrid');
  const gridSize = data.grid_size || 2;
  const cellSize = Math.min(100, Math.floor(300 / gridSize));
  const items = data.items || [];

  // Configure grid
  gridEl.style.gridTemplateColumns = `repeat(${gridSize}, ${cellSize}px)`;
  gridEl.style.gridTemplateRows = `repeat(${gridSize}, ${cellSize}px)`;
  gridEl.style.width = (gridSize * cellSize + (gridSize - 1) * 2 + 4) + 'px';
  gridEl.style.height = (gridSize * cellSize + (gridSize - 1) * 2 + 4) + 'px';
  gridEl.style.position = 'relative';

  // Generate background cells
  gridEl.innerHTML = '';
  for (let i = 0; i < gridSize * gridSize; i++) {
    const cell = document.createElement('div');
    cell.className = 'grid-cell';
    cell.style.width = cellSize + 'px';
    cell.style.height = cellSize + 'px';
    gridEl.appendChild(cell);
  }

  // Show eating.gif during search phase
  const exprImg = document.getElementById('resultExpression');
  exprImg.src = '/resources/expressions/eating.gif';
  exprImg.style.display = '';
  exprImg.style.animation = 'none';
  exprImg.offsetHeight;
  exprImg.style.animation = 'expressionBounce 0.5s ease';

  // Hide value & item list until animation completes
  document.getElementById('resultValue').textContent = '?';
  document.getElementById('resultItems').classList.add('hidden');
  document.getElementById('resultProfit').classList.add('hidden');

  // Create item slots (absolutely positioned over cells)
  const slots = [];
  items.forEach((item, idx) => {
    const slot = document.createElement('div');
    slot.className = `item-slot searching level-${item.level}`;
    slot.style.left = (item.x * cellSize + item.x * 2 + 2) + 'px';
    slot.style.top = (item.y * cellSize + item.y * 2 + 2) + 'px';
    slot.style.width = (item.width * cellSize + (item.width - 1) * 2) + 'px';
    slot.style.height = (item.height * cellSize + (item.height - 1) * 2) + 'px';
    slot.style.zIndex = (idx + 1);

    // Preload image (hidden until reveal)
    const img = document.createElement('img');
    img.src = item.image_url;
    img.alt = item.name;
    img.style.display = 'none';
    slot.appendChild(img);

    gridEl.appendChild(slot);
    slots.push({ slot, item, img });
  });

  // Animate reveal sequence (left→right, top→bottom order from backend)
  let cumDelay = 0;
  const GAP = 150; // gap between item reveals

  slots.forEach(({ slot, item, img }) => {
    const searchDur = item.search_duration_ms || 600;

    // Reveal after search duration
    setTimeout(() => {
      slot.classList.remove('searching');
      slot.classList.add('revealed');
      img.style.display = '';
    }, cumDelay + searchDur);

    cumDelay += searchDur + GAP;
  });

  // After last item revealed: switch eating.gif → result expression, then fire callback
  const EXPR_DELAY = 400;
  const totalAnim = cumDelay + EXPR_DELAY;
  setTimeout(() => {
    // Switch to result expression
    const resultExpr = data.expression || 'cry';
    exprImg.src = `/resources/expressions/${resultExpr}.png`;
    exprImg.style.animation = 'none';
    exprImg.offsetHeight;
    exprImg.style.animation = 'expressionBounce 0.5s ease';
  }, totalAnim);

  // Fire completion callback a bit after expression switches
  setTimeout(() => {
    if (onComplete) onComplete();
  }, totalAnim + 600);
}

function startCooldown(seconds) {
  touchiCooldown = seconds;
  const btn = document.getElementById('touchiBtn');
  const overlay = document.getElementById('cooldownOverlay');
  const circle = document.getElementById('cooldownCircle');
  const timer = document.getElementById('cooldownTimer');
  const total = seconds;

  // Persist to localStorage (survives browser refresh)
  const uid = App.getUserId();
  localStorage.setItem(CD_STORAGE_KEY + '_' + uid, Date.now() + seconds * 1000);

  btn.disabled = true;
  overlay.classList.remove('hidden');
  circle.style.strokeDashoffset = '0';

  function tick() {
    const remain = touchiCooldown;
    const mins = Math.floor(remain / 60);
    const secs = remain % 60;
    timer.textContent = mins > 0 ? `${mins}:${String(secs).padStart(2, '0')}` : `${secs}s`;

    const progress = remain / total;
    circle.style.strokeDashoffset = (339.292 * (1 - progress)).toFixed(2);

    if (remain <= 0) {
      clearInterval(countdownInterval);
      overlay.classList.add('hidden');
      btn.disabled = false;
      localStorage.removeItem(CD_STORAGE_KEY + '_' + uid);
      return;
    }
    touchiCooldown--;
  }

  clearInterval(countdownInterval);
  countdownInterval = setInterval(tick, 1000);
  tick();
}
