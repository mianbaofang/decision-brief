/* ============================================================
   Brief — 决策简报卡渲染器
   核心：信心环 conic-gradient + 6 模式结果卡
   依赖：I18N, MODES
   ============================================================ */

const Brief = (() => {

  // 安全转义
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const el = (tag, cls, content) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (content != null) e.textContent = content;
    return e;
  };

  /** 信心环 DOM：conic-gradient 按百分比动态渲染 */
  function confidenceRing(percent) {
    const p = Math.max(0, Math.min(100, percent | 0));
    const deg = Math.round((p / 100) * 360);
    const ring = el('div', 'confidence');
    ring.style.background = `conic-gradient(var(--ink) 0 ${deg}deg, rgba(25,26,22,0.12) ${deg}deg 360deg)`;
    const span = el('span', '', String(p));
    ring.appendChild(span);
    ring.setAttribute('role', 'img');
    ring.setAttribute('aria-label', I18N.t('brief.confidence') + ' ' + p + '%');
    return ring;
  }

  /** 小尺寸信心环（档案列表用） */
  function miniRing(percent) {
    const p = Math.max(0, Math.min(100, percent | 0));
    const deg = Math.round((p / 100) * 360);
    const ring = el('span', 'ring');
    ring.style.background = `conic-gradient(var(--ink) 0 ${deg}deg, rgba(25,26,22,0.12) ${deg}deg 360deg)`;
    return ring;
  }

  /**
   * 主简报卡构造器（所有模式共用）
   * @param {object} o { tone, modeName, percent, title, verdict, keep, drop, next }
   * @returns {HTMLElement} article.brief
   */
  function renderBrief(o) {
    const article = el('article', 'brief');

    // 头部：印章 + 模式名/证据强度 + 标题
    const head = el('div', 'brief-head');
    head.setAttribute('data-tone', o.tone || 'auto');
    const sealWrap = document.createElement('span');
    sealWrap.className = 'head-seal';
    sealWrap.innerHTML = MODES.sealSVG(toneToModeId(o.tone), { size: 30, rounded: 6 });
    head.appendChild(sealWrap);

    const meta = el('div', 'brief-head-meta');
    const typeBar = el('div', 'brief-type');
    const percentText = new Intl.NumberFormat(I18N.getLocale(), { style: 'percent', maximumFractionDigits: 0 }).format((o.percent || 0) / 100);
    typeBar.appendChild(el('span', '', o.modeName || ''));
    typeBar.appendChild(el('span', '', I18N.t('brief.confidence') + ' ' + percentText));
    meta.appendChild(typeBar);
    meta.appendChild(el('div', 'brief-title', o.title || ''));
    head.appendChild(meta);
    article.appendChild(head);

    // 八字信息条（风水模式，可选）
    if (o.bazi) {
      const bazi = el('div', 'brief-bazi');
      bazi.textContent = (o.baziAudit ? I18N.t('fengshui.bazi') + '（降级）：' : I18N.t('fengshui.bazi') + '：') + o.bazi;
      article.appendChild(bazi);
    }

    // 主体
    const body = el('div', 'brief-body');

    // 当前判断 + 信心环
    const verdict = el('div', 'verdict');
    const verdictLeft = el('div');
    verdictLeft.appendChild(el('div', 'verdict-label', I18N.t('brief.verdict')));
    verdictLeft.appendChild(el('div', 'verdict-main', o.verdict || ''));
    verdict.appendChild(verdictLeft);
    verdict.appendChild(confidenceRing(o.percent || 0));
    body.appendChild(verdict);

    // 保留 / 放下 双栏
    const cols = el('div', 'brief-columns');
    const keepSec = el('section', 'mini-section');
    keepSec.appendChild(el('h3', '', I18N.t('brief.keep')));
    keepSec.appendChild(el('p', '', o.keep || ''));
    cols.appendChild(keepSec);
    const dropSec = el('section', 'mini-section');
    dropSec.appendChild(el('h3', '', I18N.t('brief.drop')));
    dropSec.appendChild(el('p', '', o.drop || ''));
    cols.appendChild(dropSec);
    body.appendChild(cols);

    // 模式专属附加内容
    const extra = renderExtra(o);
    if (extra) body.appendChild(extra);

    // 下一步
    const next = el('div', 'next-step');
    next.innerHTML = '<strong>' + esc(I18N.t('brief.next')) + '</strong>' + esc(o.next || '');
    body.appendChild(next);

    article.appendChild(body);
    return article;
  }

  // tone → modeId（用于取印章）
  function toneToModeId(tone) {
    return tone || 'auto';
  }

  /** 6 模式专属附加内容 */
  function renderExtra(o) {
    switch (o.tone) {
      case 'rational': return renderRationalExtra(o);
      case 'random':   return renderRandomExtra(o);
      case 'nature':   return renderNatureExtra(o);
      case 'dialogue': return renderDialogueExtra(o);
      case 'fengshui': return renderFengshuiExtra(o);
      default: return null;
    }
  }

  /* ---- 理性：利弊清单 + 评分 ---- */
  function renderRationalExtra(o) {
    const pros = Array.isArray(o.pros) ? o.pros : [];
    const cons = Array.isArray(o.cons) ? o.cons : [];
    if (!pros.length && !cons.length && !o.score) return null;
    const wrap = el('div', 'rational-detail');
    const prosCol = el('div', 'pros-col');
    prosCol.appendChild(el('h4', '', I18N.t('rational.pros')));
    const pul = el('ul');
    (pros.length ? pros : ['—']).forEach(p => pul.appendChild(el('li', '', p)));
    prosCol.appendChild(pul);
    const consCol = el('div', 'cons-col');
    consCol.appendChild(el('h4', '', I18N.t('rational.cons')));
    const cul = el('ul');
    (cons.length ? cons : ['—']).forEach(c => cul.appendChild(el('li', '', c)));
    consCol.appendChild(cul);
    wrap.appendChild(prosCol);
    wrap.appendChild(consCol);
    if (o.score) {
      const s = o.score;
      const line = el('div', 'score-line');
      const parts = [];
      if (s.benefit != null)      parts.push('收益 ' + s.benefit);
      if (s.risk != null)         parts.push('风险 ' + s.risk);
      if (s.reversibility != null) parts.push('可逆 ' + s.reversibility);
      if (s.valueFit != null)     parts.push('契合 ' + s.valueFit);
      line.textContent = I18N.t('rational.score') + '：' + parts.join(' / ');
      wrap.appendChild(line);
    }
    return wrap;
  }

  /* ---- 天意：6 格转盘 + 动画 ---- */
  function renderRandomExtra(o) {
    const options = Array.isArray(o.options) ? o.options.slice(0, 6) : [];
    const fallback = ['再想想', '换个角度', '问朋友', '睡一觉', '抛硬币', '跟着心走'];
    let i = 0;
    while (options.length < 6) options.push(fallback[i++ % fallback.length]);
    const chosen = o.wheelResult || options[Math.floor(Math.random() * options.length)];

    const wrap = el('div');
    const wheel = el('div', 'wheel');
    const pointer = el('div', 'wheel-pointer');
    wheel.appendChild(pointer);
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('class', 'wheel-svg');
    svg.setAttribute('viewBox', '0 0 200 200');
    svg.setAttribute('aria-hidden', 'true');
    // 6 色（取模式色系，低饱和）
    const segColors = ['#317d78', '#365385', '#9b7636', '#486a55', '#69526f', '#b45a42'];
    const cx = 100, cy = 100, R = 96;
    const seg = 360 / 6;
    for (let k = 0; k < 6; k++) {
      const a0 = (k * seg - 90) * Math.PI / 180;
      const a1 = ((k + 1) * seg - 90) * Math.PI / 180;
      const x0 = cx + R * Math.cos(a0), y0 = cy + R * Math.sin(a0);
      const x1 = cx + R * Math.cos(a1), y1 = cy + R * Math.sin(a1);
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M${cx},${cy} L${x0},${y0} A${R},${R} 0 0 1 ${x1},${y1} Z`);
      path.setAttribute('fill', segColors[k]);
      path.setAttribute('stroke', 'rgba(255,255,255,0.6)');
      path.setAttribute('stroke-width', '1');
      svg.appendChild(path);
      // 文字
      const ta = ((k + 0.5) * seg - 90) * Math.PI / 180;
      const tx = cx + (R * 0.62) * Math.cos(ta);
      const ty = cy + (R * 0.62) * Math.sin(ta);
      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('x', tx); text.setAttribute('y', ty + 4);
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('font-size', '11');
      text.setAttribute('font-weight', '700');
      text.setAttribute('fill', '#fff');
      text.setAttribute('font-family', "'Songti SC',serif");
      text.textContent = options[k].slice(0, 4);
      svg.appendChild(text);
    }
    // 中心圆
    const center = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    center.setAttribute('cx', cx); center.setAttribute('cy', cy); center.setAttribute('r', 14);
    center.setAttribute('fill', 'var(--white)');
    center.setAttribute('stroke', 'var(--ink)');
    center.setAttribute('stroke-width', '1.5');
    svg.appendChild(center);
    wheel.appendChild(svg);
    wrap.appendChild(wheel);

    const result = el('div', 'wheel-result');
    result.textContent = I18N.t('random.result') + '：「' + chosen + '」';
    wrap.appendChild(result);

    // 转盘动画：定位到 chosen 的扇区中心
    const chosenIdx = Math.max(0, options.indexOf(chosen));
    const targetAngle = 360 * 5 + (360 - (chosenIdx + 0.5) * seg);
    requestAnimationFrame(() => {
      svg.style.transform = `rotate(${targetAngle}deg)`;
    });

    return wrap;
  }

  /* ---- 自然：信号卡 + 诗意解读 ---- */
  function renderNatureExtra(o) {
    const card = el('div', 'nature-card');
    const lines = [];
    if (o.weather) lines.push(I18N.t('nature.weather') + '：' + o.weather);
    if (o.city || o.temperature != null || o.wind) {
      const parts = [o.city, o.temperature != null ? o.temperature + '℃' : '', o.wind].filter(Boolean);
      if (parts.length) lines.push(parts.join(' · '));
    }
    if (o.source) lines.push(I18N.t('nature.source', { source: o.source }) + (o.isReal ? '' : I18N.t('nature.fallback')));
    if (lines.length) card.appendChild(el('div', '', lines.join('｜')));
    if (o.poem) {
      const poem = el('div', 'nature-poem');
      poem.textContent = o.poem;
      card.appendChild(poem);
    }
    if (!card.childNodes.length) return null;
    return card;
  }

  /* ---- 对话：反问 + 3 选项（交互式） ---- */
  function renderDialogueExtra(o) {
    const opts = el('div', 'dialogue-options');
    (Array.isArray(o.dialogueOptions) ? o.dialogueOptions : (o.options || [])).slice(0, 4).forEach(opt => {
      const b = el('button', 'dialogue-option', opt);
      b.type = 'button';
      b.addEventListener('click', () => {
        opts.querySelectorAll('.dialogue-option').forEach(x => { x.disabled = true; x.style.display = 'none'; });
        const rec = el('div', 'dialogue-record');
        rec.textContent = I18N.t('dialogue.recorded') + opt + '\n\n';
        const insight = el('strong', '', I18N.t('dialogue.insight'));
        rec.appendChild(insight);
        rec.appendChild(document.createTextNode(I18N.t('dialogue.insightText')));
        opts.parentElement.appendChild(rec);
        window.dispatchEvent(new CustomEvent('bjj:dialogue-complete', { detail: { answer: opt } }));
      });
      opts.appendChild(b);
    });
    return opts;
  }

  /* ---- 风水：生辰追问表单 ---- */
  function renderFengshuiExtra(o) {
    if (!o.needBirth) return null;
    const wrap = el('div', 'fengshui-ask');
    wrap.appendChild(el('div', 'fengshui-ask-title', I18N.t('fengshui.needBirth')));
    const q = el('div', 'fengshui-ask-q');
    q.textContent = o.question || I18N.t('fengshui.birthPh');
    wrap.appendChild(q);
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'fengshui-input';
    input.setAttribute('placeholder', I18N.t('fengshui.birthPh'));
    input.setAttribute('aria-label', I18N.t('fengshui.needBirth'));
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('spellcheck', 'false');
    wrap.appendChild(input);
    const btn = el('button', 'btn btn-block', I18N.t('fengshui.calc'));
    btn.style.background = 'var(--cinnabar)';
    btn.style.marginTop = '4px';
    const submit = () => {
      const v = input.value.trim();
      if (v) window.dispatchEvent(new CustomEvent('bjj:resubmit', { detail: v }));
    };
    btn.addEventListener('click', submit);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); submit(); }
    });
    wrap.appendChild(btn);
    return wrap;
  }

  /**
   * 从后端 chat 响应构造简报卡
   * 后端返回：brief={summary,confidence,perspectives,nextSteps,risks,source} + result={type,pros,cons,...}
   * 前端简报卡期望：{tone,modeName,percent,verdict,keep,drop,next, 6 模式专属字段}
   */
  function fromResponse(resp) {
    if (!resp) return renderBrief({ tone: 'auto', modeName: '', percent: 0, verdict: '', keep: '', drop: '', next: '' });
    const brief = resp.brief || {};
    const result = resp.result || {};
    const modeId = (resp.autoRecognized && resp.autoRecognized.mode) || resp.mode || 'auto';
    const m = MODES.get(modeId) || MODES.get('auto');

    // 从后端 Brief 字段映射到前端简报卡字段
    const perspectives = Array.isArray(brief.perspectives) ? brief.perspectives : [];
    const nextSteps = Array.isArray(brief.nextSteps) ? brief.nextSteps : [];
    const o = {
      tone: m.tone,
      modeName: I18N.t(m.nameKey),
      percent: brief.confidence != null ? brief.confidence : 55,
      title: brief.summary || '',
      verdict: brief.summary || result.conclusion || result.signal || result.suggestion || '',
      keep: perspectives[0] || '',
      drop: perspectives[1] || (brief.risks && brief.risks[0]) || '',
      next: nextSteps.join('；') || result.suggestion || '',
      // 6 模式专属字段从 result 取
      pros: result.pros,
      cons: result.cons,
      score: result.score,
      options: result.options,
      wheelResult: result.wheelResult,
      weather: result.weather,
      poem: result.poem,
      source: result.source || brief.source,
      isReal: result.isReal,
      city: result.city,
      temperature: result.temperature,
      wind: result.wind,
      dialogueOptions: result.options,
      needBirth: result.needBirth,
      question: result.question,
      bazi: result.bazi,
      baziAudit: result.baziAudit,
    };
    return renderBrief(o);
  }

  /**
   * 从数据库取出的 decision 构造简报卡（档案详情用）
   * decision = { id, question, mode, result, brief, createdAt, executed, regret }
   */
  function fromStored(d) {
    if (!d) return renderBrief({ tone: 'auto', modeName: '', percent: 0, verdict: '', keep: '', drop: '', next: '' });
    const brief = d.brief || {};
    const result = d.result || {};
    const m = MODES.get(d.mode) || MODES.get('auto');
    const perspectives = Array.isArray(brief.perspectives) ? brief.perspectives : [];
    const nextSteps = Array.isArray(brief.nextSteps) ? brief.nextSteps : [];
    const o = {
      tone: m.tone,
      modeName: I18N.t(m.nameKey),
      percent: brief.confidence != null ? brief.confidence : 55,
      title: brief.summary || '',
      verdict: brief.summary || result.conclusion || result.signal || result.suggestion || '',
      keep: perspectives[0] || '',
      drop: perspectives[1] || (brief.risks && brief.risks[0]) || '',
      next: nextSteps.join('；') || result.suggestion || '',
      pros: result.pros,
      cons: result.cons,
      score: result.score,
      options: result.options,
      wheelResult: result.wheelResult,
      weather: result.weather,
      poem: result.poem,
      source: result.source || brief.source,
      isReal: result.isReal,
      city: result.city,
      temperature: result.temperature,
      wind: result.wind,
      dialogueOptions: result.options,
      needBirth: result.needBirth,
      question: result.question,
      bazi: result.bazi,
      baziAudit: result.baziAudit,
    };
    return renderBrief(o);
  }

  return { renderBrief, fromResponse, fromStored, confidenceRing, miniRing, esc };
})();
