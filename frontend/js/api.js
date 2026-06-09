/* ── Backend API client ── */

const API = {
  async touchi(userId) {
    const r = await fetch('/api/touchi', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    return r.json();
  },

  async collection(userId) {
    const r = await fetch(`/api/collection/${encodeURIComponent(userId)}`);
    return r.json();
  },

  async economy(userId) {
    const r = await fetch(`/api/economy/${encodeURIComponent(userId)}`);
    return r.json();
  },

  async menggong(userId) {
    const r = await fetch('/api/menggong', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    return r.json();
  },

  async upgrade(userId) {
    const r = await fetch('/api/upgrade', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    return r.json();
  },

  async autoStart(userId) {
    const r = await fetch('/api/auto-touchi/start', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    return r.json();
  },

  async autoStop(userId) {
    const r = await fetch('/api/auto-touchi/stop', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId }),
    });
    return r.json();
  },

  async leaderboard() {
    const r = await fetch('/api/leaderboard');
    return r.json();
  },

  async items() {
    const r = await fetch('/api/items');
    return r.json();
  },

  async adminAuth(token) {
    const r = await fetch('/api/admin/auth', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });
    return r.json();
  },

  async adminGetConfig(token) {
    const r = await fetch(`/api/admin/config?token=${encodeURIComponent(token)}`);
    return r.json();
  },

  async adminSaveConfig(token, config) {
    const r = await fetch('/api/admin/config', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, config }),
    });
    return r.json();
  },
};
