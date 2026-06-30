/* ============================================================
   Archive — 决策档案
   职责：列表 / 详情 / 删除 / executed/regret 标记 / 分页
   依赖：API, Brief, MODES, I18N, App
   ============================================================ */

const Archive = (() => {
  const $ = (id) => document.getElementById(id);
  let page = 1;
  const pageSize = 15;
  let total = 0;
  let loaded = false;

  function init() {
    $('archiveList').addEventListener('click', onListClick);
    $('detailBack').addEventListener('click', closeDetail);
    $('detailBody').addEventListener('click', onDetailClick);
  }

  async function load(force = false) {
    if (loaded && !force) return;
    try {
      const data = await API.getArchive(page, pageSize);
      total = (data && data.total) || 0;
      renderList((data && data.list) || []);
      loaded = true;
    } catch (e) {
      renderError();
    }
  }

  function renderList(items) {
    const list = $('archiveList');
    list.innerHTML = '';
    if (!items.length) {
      list.appendChild(renderEmpty());
      return;
    }
    items.forEach(d => list.appendChild(renderCard(d)));
    // 分页器
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    if (totalPages > 1) list.appendChild(renderPager(totalPages));
  }

  function renderEmpty() {
    const empty = document.createElement('div');
    empty.className = 'archive-empty';
    empty.innerHTML = '<div class="emoji"><svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M5 4h14v16H5z"/><path d="M8 8h8M8 12h8M8 16h5"/></svg></div>';
    const t = document.createElement('div');
    t.className = 'empty-title';
    t.textContent = I18N.t('archive.empty');
    const h = document.createElement('div');
    h.className = 'empty-hint';
    h.textContent = I18N.t('archive.empty.hint');
    empty.appendChild(t);
    empty.appendChild(h);
    return empty;
  }

  function renderCard(d) {
    const card = document.createElement('article');
    card.className = 'archive-card';
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');
    card.setAttribute('data-id', d.id);

    const header = document.createElement('div');
    header.className = 'ac-header';
    const q = document.createElement('div');
    q.className = 'ac-q';
    q.textContent = d.question;
    header.appendChild(q);

    // 模式 pill
    const m = MODES.get(d.mode) || MODES.get('auto');
    const pill = document.createElement('span');
    pill.className = 'pill';
    pill.setAttribute('data-mode', d.mode);
    pill.innerHTML = MODES.sealSVG(d.mode, { size: 12, rounded: 2 }) + '<span></span>';
    pill.querySelector('span').textContent = I18N.t(m.nameKey);
    header.appendChild(pill);
    card.appendChild(header);

    // 摘要判断
    const verdict = (d.brief && d.brief.summary) || (d.result && (d.result.conclusion || d.result.signal || d.result.suggestion));
    if (verdict) {
      const v = document.createElement('div');
      v.className = 'ac-verdict';
      v.textContent = verdict;
      card.appendChild(v);
    }

    // 标记
    if (d.executed || d.regret) {
      const row = document.createElement('div');
      row.className = 'mark-row';
      if (d.executed) row.appendChild(mark('executed', I18N.t('archive.executed')));
      if (d.regret) row.appendChild(mark('regret', I18N.t('archive.regret')));
      card.appendChild(row);
    }

    // 元信息
    const meta = document.createElement('div');
    meta.className = 'archive-meta';
    const time = document.createElement('span');
    time.textContent = formatTime(d.createdAt);
    meta.appendChild(time);
    const conf = document.createElement('span');
    conf.className = 'ac-confidence';
    const pct = (d.brief && d.brief.confidence) || 0;
    conf.appendChild(Brief.miniRing(pct));
    conf.appendChild(document.createTextNode(pct + '%'));
    meta.appendChild(conf);
    card.appendChild(meta);

    return card;
  }

  function mark(type, label) {
    const m = document.createElement('span');
    m.className = 'mark ' + type;
    const icon = type === 'executed'
      ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="M5 12l5 5 9-11"/></svg>'
      : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M12 8v5M12 17h.01"/><circle cx="12" cy="12" r="9"/></svg>';
    m.innerHTML = icon + '<span></span>';
    m.querySelector('span').textContent = label;
    return m;
  }

  function renderPager(totalPages) {
    const p = document.createElement('div');
    p.className = 'archive-pager';
    const prev = document.createElement('button');
    prev.textContent = '‹';
    prev.disabled = page <= 1;
    prev.addEventListener('click', async () => { if (page > 1) { page--; await load(true); } });
    const info = document.createElement('span');
    info.textContent = I18N.t('archive.page', { n: page + '/' + totalPages });
    const next = document.createElement('button');
    next.textContent = '›';
    next.disabled = page >= totalPages;
    next.addEventListener('click', async () => { if (page < totalPages) { page++; await load(true); } });
    p.appendChild(prev);
    p.appendChild(info);
    p.appendChild(next);
    return p;
  }

  function renderError() {
    const list = $('archiveList');
    list.innerHTML = '';
    const e = document.createElement('div');
    e.className = 'archive-empty';
    e.textContent = I18N.t('common.error');
    list.appendChild(e);
  }

  async function onListClick(e) {
    const card = e.target.closest('.archive-card');
    if (!card) return;
    const id = card.getAttribute('data-id');
    await openDetail(id);
  }

  async function openDetail(id) {
    const body = $('detailBody');
    body.innerHTML = '<div class="thinking"><span>' + I18N.t('common.loading') + '</span><span class="loading-dots"><span></span><span></span><span></span></span></div>';
    $('detailView').classList.add('show');
    try {
      const d = await API.getDecision(id);
      App.currentDecision = d;
      renderDetail(d);
    } catch (err) {
      body.innerHTML = '<div class="archive-empty">' + I18N.t('common.error') + '</div>';
    }
  }

  function renderDetail(d) {
    const body = $('detailBody');
    body.innerHTML = '';
    body.setAttribute('data-id', d.id);

    const q = document.createElement('div');
    q.className = 'detail-question';
    q.textContent = d.question;
    body.appendChild(q);

    const time = document.createElement('div');
    time.className = 'detail-time';
    time.textContent = formatTime(d.createdAt);
    body.appendChild(time);

    // 简报卡
    if (d.brief || d.result) {
      body.appendChild(Brief.fromStored(d));
    }

    // 操作区
    const actions = document.createElement('div');
    actions.className = 'detail-actions';
    const execBtn = document.createElement('button');
    execBtn.className = 'btn btn-toggle' + (d.executed ? ' on executed' : '');
    execBtn.setAttribute('data-action', 'executed');
    execBtn.textContent = I18N.t('archive.executed');
    const regretBtn = document.createElement('button');
    regretBtn.className = 'btn btn-toggle' + (d.regret ? ' on regret' : '');
    regretBtn.setAttribute('data-action', 'regret');
    regretBtn.textContent = I18N.t('archive.regret');
    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn-danger detail-delete';
    delBtn.setAttribute('data-action', 'delete');
    delBtn.textContent = I18N.t('archive.delete');
    actions.appendChild(execBtn);
    actions.appendChild(regretBtn);
    actions.appendChild(delBtn);
    body.appendChild(actions);
  }

  async function onDetailClick(e) {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    const action = btn.getAttribute('data-action');
    const id = $('detailBody').getAttribute('data-id');
    if (action === 'delete') {
      const ok = await App.confirm(I18N.t('archive.deleteConfirm'));
      if (!ok) return;
      try {
        await API.deleteDecision(id);
        App.toast(I18N.t('archive.delete'));
        closeDetail();
        load(true);
        App.loadSidebarRecent();
      } catch (err) {
        App.toast(I18N.t('common.error'));
      }
      return;
    }
    // executed / regret 切换
    const d = App.currentDecision;
    if (!d) return;
    const next = !d[action];
    try {
      const patch = {}; patch[action] = next;
      await API.updateDecision(id, patch);
      d[action] = next;
      btn.classList.toggle('on', next);
      if (action === 'executed') btn.classList.toggle('executed', next);
      if (action === 'regret') btn.classList.toggle('regret', next);
      load(true);
      App.loadSidebarRecent();
    } catch (err) {
      App.toast(I18N.t('common.error'));
    }
  }

  function closeDetail() {
    $('detailView').classList.remove('show');
    App.currentDecision = null;
  }

  function formatTime(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    const now = new Date();
    const diff = (now - d) / 1000;
    if (diff < 60) return '刚刚';
    if (diff < 3600) return Math.floor(diff / 60) + ' min';
    if (diff < 86400) return Math.floor(diff / 3600) + ' h';
    const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, '0'), day = String(d.getDate()).padStart(2, '0');
    return y + '-' + m + '-' + day;
  }

  return { init, load };
})();
