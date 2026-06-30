/* ============================================================
   Stats — 决策统计
   职责：4 指标卡 / 模式分布柱状图 / 7 天趋势
   依赖：API, MODES, I18N, App
   ============================================================ */

const Stats = (() => {
  const $ = (id) => document.getElementById(id);
  let loaded = false;

  function init() {}

  async function load(force = false) {
    if (loaded && !force) return;
    const scroll = $('statsScroll');
    try {
      const data = await API.getStats();
      render(data || {});
      loaded = true;
    } catch (e) {
      scroll.innerHTML = '<div class="stats-empty">' + I18N.t('common.error') + '</div>';
    }
  }

  function render(data) {
    const scroll = $('statsScroll');
    scroll.innerHTML = '';

    const total = data.totalDecisions || 0;
    const modeDist = data.modeDistribution || {};
    if (total === 0 && !data.weekTrend) {
      scroll.innerHTML = '<div class="stats-empty">' + I18N.t('stats.empty') + '</div>';
      return;
    }

    // 4 指标卡
    const grid = document.createElement('div');
    grid.className = 'stats-grid';
    grid.appendChild(statCard('total', total, I18N.t('stats.total'), ''));
    grid.appendChild(statCard('executed', pct(data.executedRate), I18N.t('stats.executedRate'), '%'));
    grid.appendChild(statCard('regret', pct(data.regretRate), I18N.t('stats.regretRate'), '%'));
    grid.appendChild(statCard('confidence', Math.round(data.avgConfidence || 0), I18N.t('stats.avgConfidence'), '%'));
    scroll.appendChild(grid);

    // 模式分布
    if (modeDist && Object.keys(modeDist).length) {
      const chart = document.createElement('div');
      chart.className = 'chart';
      const h = document.createElement('h3');
      h.textContent = I18N.t('stats.modeDist');
      chart.appendChild(h);
      const bars = document.createElement('div');
      bars.className = 'mode-bars';
      const max = Math.max(1, ...Object.values(modeDist));
      MODES.list().forEach(m => {
        const count = modeDist[m.id] || 0;
        const row = document.createElement('div');
        row.className = 'mode-bar';
        row.setAttribute('data-mode', m.id);
        const label = document.createElement('span');
        label.className = 'mb-label';
        label.innerHTML = MODES.sealSVG(m.id, { size: 16, rounded: 3 }) + '<span></span>';
        label.querySelector('span').textContent = I18N.t(m.nameKey);
        const track = document.createElement('span');
        track.className = 'mb-track';
        const fill = document.createElement('span');
        fill.className = 'mb-fill';
        fill.style.width = (count / max * 100) + '%';
        track.appendChild(fill);
        const val = document.createElement('span');
        val.className = 'mb-value';
        val.textContent = String(count);
        row.appendChild(label);
        row.appendChild(track);
        row.appendChild(val);
        bars.appendChild(row);
      });
      chart.appendChild(bars);
      scroll.appendChild(chart);
    }

    // 7 天趋势
    if (data.weekTrend) {
      const chart = document.createElement('div');
      chart.className = 'chart';
      const h = document.createElement('h3');
      h.textContent = I18N.t('stats.weekTrend');
      chart.appendChild(h);
      const tc = document.createElement('div');
      tc.className = 'trend-chart';
      const trend = data.weekTrend; // [{date, count}]
      const max = Math.max(1, ...trend.map(t => t.count || 0));
      const today = new Date();
      trend.forEach((t, i) => {
        const col = document.createElement('div');
        col.className = 'trend-bar';
        const isToday = i === trend.length - 1;
        if (isToday) col.classList.add('today');
        const inner = document.createElement('div');
        inner.className = 'tb-col';
        inner.style.height = ((t.count || 0) / max * 100) + '%';
        const cnt = document.createElement('span');
        cnt.className = 'tb-count';
        cnt.textContent = String(t.count || 0);
        inner.appendChild(cnt);
        const lbl = document.createElement('span');
        lbl.className = 'tb-label';
        lbl.textContent = dayLabel(t.date, i, trend.length);
        col.appendChild(inner);
        col.appendChild(lbl);
        tc.appendChild(col);
      });
      chart.appendChild(tc);
      scroll.appendChild(chart);
    }
  }

  function statCard(accent, value, label, unit) {
    const c = document.createElement('div');
    c.className = 'stat';
    c.setAttribute('data-accent', accent);
    const b = document.createElement('b');
    b.innerHTML = Brief.esc(value) + (unit ? '<span class="unit">' + unit + '</span>' : '');
    const s = document.createElement('span');
    s.textContent = label;
    c.appendChild(b);
    c.appendChild(s);
    return c;
  }

  function pct(v) {
    if (v == null) return 0;
    return Math.round(v * 100);
  }

  function dayLabel(dateStr, i, len) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d)) return '';
    const labels = ['日', '一', '二', '三', '四', '五', '六'];
    return labels[d.getDay()] || '';
  }

  return { init, load };
})();
