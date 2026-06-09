/* ── Utility helpers ── */

/** Show a toast message */
function showToast(msg, error = false) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast ' + (error ? 'error' : '') + ' show';
  clearTimeout(el._timeout);
  el._timeout = setTimeout(() => { el.className = 'toast hidden'; }, 2500);
}

/** Simple template render */
function html(strings, ...values) {
  return String.raw({ raw: strings }, ...values);
}

/** Format large numbers */
function fmt(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 10_000) return Math.round(n / 10_000) + 'W';
  return n.toLocaleString();
}

/** Level badge color */
function levelColor(level) {
  return { blue: '#42a5f5', purple: '#9c27b0', gold: '#ffd700', red: '#e53935' }[level] || '#888';
}
