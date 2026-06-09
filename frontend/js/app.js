/* ── Application controller ── */

const App = {
  userId: 'default',

  init() {
    // Load saved user ID
    const saved = localStorage.getItem('touchi_user_id');
    if (saved) {
      this.userId = saved;
      document.getElementById('userIdInput').value = saved;
    }

    // Save ID button
    document.getElementById('saveIdBtn').addEventListener('click', () => {
      const val = document.getElementById('userIdInput').value.trim();
      if (!val) return;
      this.userId = val;
      localStorage.setItem('touchi_user_id', val);
      showToast('干员ID已保存');
      this.refreshAll();
    });

    // Enter key on ID input
    document.getElementById('userIdInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        document.getElementById('saveIdBtn').click();
      }
    });

    // Nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const pageId = btn.dataset.page;
        this.switchPage(pageId);
      });
    });

    // Init page modules
    initTouchi();
    initCollection();
    initWarehouse();
    initAdmin();

    // Load initial data
    this.switchPage('pageTouchi');
    this.refreshHeader();
  },

  getUserId() {
    return this.userId;
  },

  switchPage(pageId) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    document.getElementById(pageId).classList.add('active');
    document.querySelector(`[data-page="${pageId}"]`).classList.add('active');

    // Load page-specific data
    if (pageId === 'pageCollection') loadCollection();
    if (pageId === 'pageWarehouse') {
      loadWarehouse();
      startWarehouseRefresh();
    } else {
      if (refreshInterval) clearInterval(refreshInterval);
    }
  },

  async refreshHeader() {
    try {
      const data = await API.economy(this.userId);
      if (!data.ok) return;
      document.getElementById('headerValue').textContent = fmt(data.warehouse_value);

      const mgBadge = document.getElementById('headerMenggong');
      mgBadge.style.display = data.menggong_active ? 'inline' : 'none';

      const autoBadge = document.getElementById('headerAuto');
      autoBadge.style.display = data.auto_touchi_active ? 'inline' : 'none';
    } catch (e) {
      // Silently ignore
    }
  },

  refreshAll() {
    this.refreshHeader();
    const activePage = document.querySelector('.page.active');
    if (activePage) {
      if (activePage.id === 'pageCollection') loadCollection();
      if (activePage.id === 'pageWarehouse') loadWarehouse();
    }
  },
};

document.addEventListener('DOMContentLoaded', () => App.init());
