/* ============================================================
   API — 后端调用封装（同源，base URL 为空）
   端点：/api/modes /api/chat /api/decision /api/archive
        /api/stats /api/config /api/preferences
   ============================================================ */

const API = (() => {
  const BASE = '';  // 同源

  async function request(path, options = {}) {
    const opts = {
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      ...options
    };
    if (opts.body && typeof opts.body !== 'string') {
      opts.body = JSON.stringify(opts.body);
    }
    let res;
    try {
      res = await fetch(BASE + path, opts);
    } catch (e) {
      throw new ApiError('network', e.message);
    }
    if (res.status === 204) return null;
    let data = null;
    const text = await res.text();
    if (text) {
      try { data = JSON.parse(text); }
      catch (e) { data = text; }
    }
    if (!res.ok) {
      const msg = (data && (data.detail || data.message)) || res.statusText;
      throw new ApiError(res.status, msg);
    }
    return data;
  }

  class ApiError extends Error {
    constructor(status, message) {
      super(message);
      this.status = status;
      this.name = 'ApiError';
    }
  }

  return {
    ApiError,

    /** GET /api/modes — 6 模式元信息 */
    getModes() {
      return request('/api/modes');
    },

    /**
     * POST /api/chat
     * @param {string} question 决策问题
     * @param {string} mode 模式 id
     * @returns {Promise<{mode, autoRecognized?, brief, result, decisionId?}>}
     */
    chat(question, mode, extra) {
      const body = { question, mode };
      if (extra && typeof extra === 'object') Object.assign(body, extra);
      return request('/api/chat', {
        method: 'POST',
        body
      });
    },

    /** POST /api/decision — 保存决策 */
    saveDecision(decision) {
      return request('/api/decision', {
        method: 'POST',
        body: decision
      });
    },

    /** GET /api/decision/:id */
    getDecision(id) {
      return request('/api/decision/' + encodeURIComponent(id));
    },

    /** PATCH /api/decision/:id — 局部更新（executed/regret 等） */
    updateDecision(id, patches) {
      return request('/api/decision/' + encodeURIComponent(id), {
        method: 'PATCH',
        body: patches
      });
    },

    /** DELETE /api/decision/:id */
    deleteDecision(id) {
      return request('/api/decision/' + encodeURIComponent(id), {
        method: 'DELETE'
      });
    },

    /**
     * GET /api/archive?page=&pageSize=
     * @returns {Promise<{items, page, pageSize, total}>}
     */
    getArchive(page = 1, pageSize = 20) {
      const q = new URLSearchParams({ page, pageSize });
      return request('/api/archive?' + q.toString());
    },

    /** GET /api/stats */
    getStats() {
      return request('/api/stats');
    },

    /** GET /api/config — LLM + 天气配置 */
    getConfig() {
      return request('/api/config');
    },

    /** POST /api/config */
    saveConfig(config) {
      return request('/api/config', {
        method: 'POST',
        body: config
      });
    },

    /** GET /api/preferences — 用户偏好（语言/主题/默认模式/价值观） */
    getPreferences() {
      return request('/api/preferences');
    },

    /** POST /api/preferences */
    savePreferences(prefs) {
      return request('/api/preferences', {
        method: 'POST',
        body: prefs
      });
    }
  };
})();


/* ============================================================
   MODES — 6 模式注册表（印章字符 + tone + 描述 key）
   印章 SVG 生成：sealSVG(modeId) 返回 <svg> 字符串
   ============================================================ */

const MODES = (() => {
  // 单字印章符号 + 对应 tone 色 + i18n 描述 key
  const REGISTRY = [
    { id: 'auto',     char: '自', tone: 'auto',     color: 'var(--aqua)',     hex: '#317d78', nameKey: 'mode.auto',     descKey: 'mode.auto.desc' },
    { id: 'rational', char: '理', tone: 'rational', color: 'var(--lapis)',    hex: '#365385', nameKey: 'mode.rational', descKey: 'mode.rational.desc' },
    { id: 'random',   char: '随', tone: 'random',   color: 'var(--brass)',    hex: '#9b7636', nameKey: 'mode.random',   descKey: 'mode.random.desc' },
    { id: 'nature',   char: '然', tone: 'nature',   color: 'var(--moss)',     hex: '#486a55', nameKey: 'mode.nature',   descKey: 'mode.nature.desc' },
    { id: 'dialogue', char: '问', tone: 'dialogue', color: 'var(--plum)',     hex: '#69526f', nameKey: 'mode.dialogue', descKey: 'mode.dialogue.desc' },
    { id: 'fengshui', char: '局', tone: 'fengshui', color: 'var(--cinnabar)', hex: '#b45a42', nameKey: 'mode.fengshui', descKey: 'mode.fengshui.desc' }
  ];
  const BY_ID = Object.fromEntries(REGISTRY.map(m => [m.id, m]));

  /**
   * 生成印章 SVG（方形容器 + 模式色背景 + 单字白色）
   * @param {string} modeId
   * @param {object} opt { size, rounded, hollow }
   */
  function sealSVG(modeId, opt = {}) {
    const m = BY_ID[modeId];
    if (!m) return '';
    const size = opt.size || 24;
    const r = opt.rounded != null ? opt.rounded : 4;
    const fill = opt.hollow ? 'none' : m.hex;
    const stroke = opt.hollow ? m.hex : 'none';
    const textColor = opt.hollow ? m.hex : '#ffffff';
    // 印章风：略带不规则边感用圆角矩形 + 内描边
    return `<svg class="seal" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <rect x="1.5" y="1.5" width="21" height="21" rx="${r}" fill="${fill}" stroke="${stroke}" stroke-width="1.2"/>
      <rect x="3.5" y="3.5" width="17" height="17" rx="${Math.max(r - 1, 2)}" fill="none" stroke="rgba(255,255,255,0.28)" stroke-width="0.8"/>
      <text x="12" y="16.5" font-family="'Songti SC','Noto Serif SC','STSong',serif" font-size="13" font-weight="700" fill="${textColor}" text-anchor="middle" dominant-baseline="middle">${m.char}</text>
    </svg>`;
  }

  function list() { return REGISTRY.slice(); }
  function get(id) { return BY_ID[id]; }
  function toneColor(tone) {
    const m = REGISTRY.find(x => x.tone === tone);
    return m ? m.hex : '#317d78';
  }

  return { REGISTRY, BY_ID, sealSVG, list, get, toneColor };
})();
