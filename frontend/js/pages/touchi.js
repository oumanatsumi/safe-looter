/* ── Touchi Page ── */

let touchiCooldown = 0;
let countdownInterval = null;
let revealTimeout = null;

function initTouchi() {
  const btn = document.getElementById('touchiBtn');
  btn.addEventListener('click', () => {
    if (touchiCooldown > 0) return;
    doTouchi();
  });
}

async function doTouchi() {
  const uid = App.getUserId();
  const btn = document.getElementById('touchiBtn');
  const btnText = btn.querySelector('.btn-text');
  const resultArea = document.getElementById('resultArea');

  btn.disabled = true;
  resultArea.classList.add('hidden');
  if (revealTimeout) clearTimeout(revealTimeout);

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

    // Show GIF
    const gif = document.getElementById('resultGif');
    gif.src = data.image_url;

    // Prepare items HTML (hidden initially)
    document.getElementById('resultValue').textContent = fmt(data.total_value);

    const profitEl = document.getElementById('resultProfit');
    if (data.total_profit > 0) {
      profitEl.textContent = `本次收益: +${fmt(data.total_profit)} 哈夫币`;
      profitEl.classList.remove('hidden');
    } else {
      profitEl.classList.add('hidden');
    }

    const itemsDiv = document.getElementById('resultItems');
    itemsDiv.innerHTML = data.items.map(it => `
      <div class="result-item level-${it.level}">
        <img src="${it.image_url}" alt="${it.name}" loading="lazy">
        <span class="item-name">${it.name}</span>
        <span class="item-value" style="color:${levelColor(it.level)}">${fmt(it.value)}</span>
      </div>
    `).join('');
    // Hide items during GIF first playthrough
    itemsDiv.classList.add('hidden');
    document.getElementById('resultValue').parentElement.querySelector('.result-profit')?.classList?.add('hidden');

    // Reveal items after GIF finishes first loop
    const gifDuration = data.gif_duration_ms || 6000;
    revealTimeout = setTimeout(() => {
      itemsDiv.classList.remove('hidden');
    }, gifDuration);

    // Show result area immediately (GIF visible, items hidden)
    resultArea.classList.remove('hidden');

    // Refresh header economy
    App.refreshHeader();
  } catch (e) {
    clearInterval(dotsInterval);
    if (btnText) btnText.textContent = '偷 吃';
    showToast('网络错误，请重试', true);
    btn.disabled = false;
  }
}

function startCooldown(seconds) {
  touchiCooldown = seconds;
  const btn = document.getElementById('touchiBtn');
  const overlay = document.getElementById('cooldownOverlay');
  const circle = document.getElementById('cooldownCircle');
  const timer = document.getElementById('cooldownTimer');
  const total = seconds;

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
      return;
    }
    touchiCooldown--;
  }

  clearInterval(countdownInterval);
  countdownInterval = setInterval(tick, 1000);
  tick();
}
