/* ============================================================
   App — 主控制器
   职责：Tab 切换 / 路由 / 全局状态 / Toast / Modal / 主题 / 初始化
   依赖：I18N, API, Chat, Archive, Stats, Settings
   ============================================================ */

const App = (() => {
  const $ = (id) => document.getElementById(id);
  let currentTab = 'chat';
  let currentDecision = null;

  /* ---------- Toast ---------- */
  let toastTimer = null;
  function toast(msg) {
    const t = $('toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove('show'), 2200);
  }

  /* ---------- Modal ---------- */
  function openModal(contentNode, opts = {}) {
    const overlay = $('modalOverlay');
    const content = $('modalContent');
    content.innerHTML = '';
    const grip = document.createElement('div');
    grip.className = 'modal-grip';
    content.appendChild(grip);
    if (opts.title) {
      const title = document.createElement('div');
      title.className = 'modal-title';
      title.textContent = opts.title;
      content.appendChild(title);
    }
    if (contentNode) content.appendChild(contentNode);
    overlay.classList.add('show');
    overlay.setAttribute('aria-hidden', 'false');
  }
  function closeModal() {
    const overlay = $('modalOverlay');
    overlay.classList.remove('show');
    overlay.setAttribute('aria-hidden', 'true');
  }
  // 点击遮罩关闭
  function bindModal() {
    const overlay = $('modalOverlay');
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeModal();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeModal();
    });
  }

  /* ---------- 确认对话框（替代 confirm） ---------- */
  function confirm(message) {
    return new Promise((resolve) => {
      const body = document.createElement('div');
      const p = document.createElement('p');
      p.style.cssText = 'font-size:14px;line-height:1.6;color:var(--text-primary);margin-bottom:16px;text-align:center;';
      p.textContent = message;
      body.appendChild(p);
      const row = document.createElement('div');
      row.style.cssText = 'display:flex;gap:8px;';
      const cancel = document.createElement('button');
      cancel.className = 'btn btn-ghost btn-block';
      cancel.textContent = I18N.t('common.cancel');
      const ok = document.createElement('button');
      ok.className = 'btn btn-block';
      ok.textContent = I18N.t('common.confirm');
      row.appendChild(cancel);
      row.appendChild(ok);
      body.appendChild(row);
      openModal(body);
      cancel.onclick = () => { closeModal(); resolve(false); };
      ok.onclick = () => { closeModal(); resolve(true); };
    });
  }

  /* ---------- Tab 切换（桌面端：决策=主区，其他=右侧抽屉） ---------- */
  function switchTab(tab) {
    if (tab === 'chat') {
      closeDrawer();
      currentTab = 'chat';
      document.querySelectorAll('.nav-item').forEach(t => {
        const active = t.getAttribute('data-tab') === 'chat';
        t.classList.toggle('active', active);
      });
      // 面包屑
      const crumb = $('crumb');
      if (crumb) crumb.textContent = I18N.t('nav.chat') + ' / ' + I18N.t('mode.auto');
      if (navigator.vibrate) navigator.vibrate(10);
      return;
    }
    // archive / stats / settings → 打开右侧抽屉
    currentTab = tab;
    document.querySelectorAll('.nav-item').forEach(t => {
      t.classList.toggle('active', t.getAttribute('data-tab') === tab);
    });
    openDrawer(tab);
    if (navigator.vibrate) navigator.vibrate(10);
  }

  /* ---------- 右侧抽屉 ---------- */
  let drawerType = null;

  function openDrawer(type) {
    drawerType = type;
    const drawer = $('drawer');
    const overlay = $('drawerOverlay');
    const title = $('drawerTitle');
    const body = $('drawerBody');
    // 切换显示对应的 page
    body.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    const page = $('page-' + type);
    if (page) page.classList.add('active');
    const titleMap = { archive: I18N.t('nav.archive'), stats: I18N.t('nav.stats'), settings: I18N.t('nav.settings') };
    title.textContent = titleMap[type] || '';
    // 面包屑
    const crumb = $('crumb');
    if (crumb) crumb.textContent = I18N.t('nav.chat') + ' / ' + (titleMap[type] || '');
    drawer.classList.add('open');
    overlay.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
    // 懒加载内容
    if (type === 'archive') Archive.load();
    if (type === 'stats') Stats.load();
  }

  function closeDrawer() {
    const drawer = $('drawer');
    const overlay = $('drawerOverlay');
    drawer.classList.remove('open');
    overlay.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    drawerType = null;
    // 抽屉关闭后，nav 高亮回到 chat
    document.querySelectorAll('.nav-item').forEach(t => {
      t.classList.toggle('active', t.getAttribute('data-tab') === 'chat');
    });
    currentTab = 'chat';
    const crumb = $('crumb');
    if (crumb) crumb.textContent = I18N.t('nav.chat') + ' / ' + I18N.t('mode.auto');
  }

  function bindDrawer() {
    $('drawerBack').addEventListener('click', closeDrawer);
    $('drawerOverlay').addEventListener('click', closeDrawer);
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && drawerType) closeDrawer();
    });
    // 移动端菜单按钮
    const menuToggle = $('menuToggle');
    if (menuToggle) {
      menuToggle.addEventListener('click', () => {
        $('sidebar').classList.toggle('open');
      });
    }
  }

  function bindTabs() {
    document.querySelectorAll('.nav-item').forEach(t => {
      t.addEventListener('click', () => switchTab(t.getAttribute('data-tab')));
    });
  }

  /* ---------- 状态栏时间 ---------- */
  function updateStatusBarTime() {
    const node = $('statusTime');
    if (!node) return;
    const d = new Date();
    node.textContent = d.getHours() + ':' + String(d.getMinutes()).padStart(2, '0');
  }

  /* ---------- 主题 ---------- */
  function applyTheme(theme) {
    let eff = theme;
    if (theme === 'auto') {
      eff = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    document.documentElement.setAttribute('data-theme', eff);
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', eff === 'dark' ? '#1a1b17' : '#f4f5ef');
  }
  // 监听系统主题变化
  function bindSystemTheme() {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      const prefs = App.prefs || {};
      if (prefs.theme === 'auto' || !prefs.theme) applyTheme('auto');
    });
  }

  /* ---------- 语言 / 偏好应用 ---------- */
  function applyPrefs(prefs) {
    App.prefs = prefs || {};
    if (prefs.language) {
      I18N.setLang(prefs.language);
    }
    if (prefs.theme) {
      applyTheme(prefs.theme);
    } else {
      applyTheme('auto');
    }
    if (prefs.default_mode && Chat.getMode) {
      Chat.setMode(prefs.default_mode);
    }
    I18N.apply();
    // 同步设置页显示
    Settings && Settings.refreshValues && Settings.refreshValues();
  }

  /* ---------- 侧栏最近决策 ---------- */
  async function loadSidebarRecent() {
    const container = $('sidebarRecent');
    if (!container) return;
    try {
      const data = await API.getArchive(1, 6);
      const list = (data && data.list) || [];
      container.innerHTML = '';
      if (!list.length) {
        container.innerHTML = '<div style="font-size:11px;color:#999;padding:8px;">' + I18N.t('archive.empty') + '</div>';
        return;
      }
      const modeColors = { auto: '#317d78', rational: '#365385', random: '#9b7636', nature: '#486a55', dialogue: '#69526f', fengshui: '#b45a42' };
      list.forEach(d => {
        const item = document.createElement('div');
        item.className = 'recent-item';
        const dot = document.createElement('span');
        dot.className = 'recent-dot';
        dot.style.background = modeColors[d.mode] || '#317d78';
        item.appendChild(dot);
        const txt = document.createElement('span');
        txt.textContent = d.question;
        item.appendChild(txt);
        item.addEventListener('click', () => { switchTab('archive'); });
        container.appendChild(item);
      });
    } catch (e) {
      container.innerHTML = '';
    }
  }

  /* ---------- API Key 提示横幅 ---------- */
  let banner = null;
  function ensureBanner() {
    if (banner) return banner;
    const wrap = document.createElement('div');
    wrap.className = 'api-key-banner';
    wrap.innerHTML =
      '<svg class="banner-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>' +
      '<div class="banner-text">' +
        '<p class="banner-title" data-i18n="api.keyRequired"></p>' +
        '<p class="banner-hint" data-i18n="api.demoHint"></p>' +
      '</div>' +
      '<div class="banner-actions">' +
        '<button type="button" class="btn btn-ghost banner-btn-demo" data-i18n="api.tryDemo"></button>' +
        '<button type="button" class="btn banner-btn-config" data-i18n="api.configNow"></button>' +
      '</div>';
    const scrollArea = $('chatScroll');
    const ref = $('chatContainer');
    if (scrollArea && ref) scrollArea.insertBefore(wrap, ref);
    banner = wrap;
    wrap.querySelector('.banner-btn-config').addEventListener('click', () => {
      switchTab('settings');
      setTimeout(() => {
        const btn = $('setAIConfig');
        if (btn) btn.click();
      }, 250);
    });
    wrap.querySelector('.banner-btn-demo').addEventListener('click', async () => {
      try {
        const prefs = await API.savePreferences({ demo_mode: true });
        App.prefs = Object.assign({}, App.prefs, prefs);
        hideBanner();
        toast(I18N.t('api.tryDemo') + ' ✓');
      } catch (e) {
        toast(I18N.t('common.error'));
      }
    });
    return wrap;
  }
  function showBanner() {
    ensureBanner();
    banner.classList.add('show');
    I18N.apply(banner);
  }
  function hideBanner() {
    if (banner) banner.classList.remove('show');
  }

  /* ---------- 初始化 ---------- */
  async function init() {
    bindTabs();
    bindDrawer();
    bindModal();
    bindSystemTheme();

    // 模块初始化
    Chat.init();
    Archive.init();
    Stats.init();
    Settings.init();

    // 加载偏好
    try {
      const prefs = await API.getPreferences();
      applyPrefs(prefs);
    } catch (e) {
      // 偏好加载失败，用默认
      applyPrefs({});
    }
    // 检测 API Key 状态，若无 key 且未开启 demo_mode 则显示横幅
    try {
      const cfg = await API.getConfig();
      if (!cfg.hasLlm && !(App.prefs && App.prefs.demo_mode)) {
        showBanner();
      }
    } catch (e) { /* 忽略 */ }
    // 拉取模式列表（可选，用于校验）
    try { await API.getModes(); } catch (e) { /* 忽略 */ }
    // 加载最近决策到侧栏
    loadSidebarRecent();
    // 初始化面包屑
    const crumb = $('crumb');
    if (crumb) crumb.textContent = I18N.t('nav.chat') + ' / ' + I18N.t('mode.auto');
  }

  return {
    init,
    toast,
    openModal,
    closeModal,
    confirm,
    switchTab,
    openDrawer,
    closeDrawer,
    applyTheme,
    applyPrefs,
    loadSidebarRecent,
    showKeyBanner: showBanner,
    hideKeyBanner: hideBanner,
    get currentTab() { return currentTab; },
    get currentDecision() { return currentDecision; },
    set currentDecision(v) { currentDecision = v; },
    prefs: {}
  };
})();

// 启动
document.addEventListener('DOMContentLoaded', () => App.init());
