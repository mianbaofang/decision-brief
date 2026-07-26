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
    if (o.title) meta.appendChild(el('div', 'brief-title', o.title));
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
    if (o.verdict) {
      const verdict = el('div', 'verdict');
      const verdictLeft = el('div');
      verdictLeft.appendChild(el('div', 'verdict-label', I18N.t('brief.verdict')));
      verdictLeft.appendChild(el('div', 'verdict-main', o.verdict));
      verdict.appendChild(verdictLeft);
      verdict.appendChild(confidenceRing(o.percent || 0));
      body.appendChild(verdict);
    }

    // 保留 / 放下 双栏
    if (o.keep || o.drop) {
      const cols = el('div', 'brief-columns' + (!o.keep || !o.drop ? ' is-single' : ''));
      if (o.keep) {
        const keepSec = el('section', 'mini-section');
        keepSec.appendChild(el('h3', '', I18N.t('brief.keep')));
        keepSec.appendChild(el('p', '', o.keep));
        cols.appendChild(keepSec);
      }
      if (o.drop) {
        const dropSec = el('section', 'mini-section');
        dropSec.appendChild(el('h3', '', I18N.t('brief.drop')));
        dropSec.appendChild(el('p', '', o.drop));
        cols.appendChild(dropSec);
      }
      body.appendChild(cols);
    }

    // 模式专属附加内容
    const extra = renderExtra(o);
    if (extra) body.appendChild(extra);

    // 下一步
    if (o.next) {
      const next = el('div', 'next-step');
      next.innerHTML = '<strong>' + esc(I18N.t('brief.next')) + '</strong>' + esc(o.next);
      body.appendChild(next);
    }

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

  const SVG_NS = 'http://www.w3.org/2000/svg';
  let randomSvgSerial = 0;

  function randomSvgNode(name, className, attrs = {}) {
    const node = document.createElementNS(SVG_NS, name);
    if (className) node.setAttribute('class', className);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    return node;
  }

  function randomHash(value) {
    let hash = 2166136261;
    const text = String(value || '');
    for (let i = 0; i < text.length; i++) {
      hash ^= text.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return hash >>> 0;
  }

  function randomSvg(className, label, viewBox = '0 0 220 220') {
    const svg = randomSvgNode('svg', 'random-form-svg ' + className, { viewBox, role: 'img', focusable: 'false' });
    svg.setAttribute('aria-label', label);
    return svg;
  }

  function buildPointerForm(chosenIdx, label) {
    const svg = randomSvg('random-pointer-svg', label, '0 0 200 200');
    const cx = 100, cy = 100;
    svg.appendChild(randomSvgNode('circle', 'random-draw-wash', { cx, cy, r: 88 }));
    svg.appendChild(randomSvgNode('circle', 'random-draw-track', { cx, cy, r: 78 }));
    svg.appendChild(randomSvgNode('circle', 'random-draw-sweep', { cx, cy, r: 84 }));
    for (let k = 0; k < 6; k++) {
      const angle = (k * 60 - 90) * Math.PI / 180;
      const x1 = cx + 69 * Math.cos(angle), y1 = cy + 69 * Math.sin(angle);
      const x2 = cx + 78 * Math.cos(angle), y2 = cy + 78 * Math.sin(angle);
      const nx = cx + 84 * Math.cos(angle), ny = cy + 84 * Math.sin(angle);
      svg.appendChild(randomSvgNode('line', 'random-draw-tick', { x1, y1, x2, y2 }));
      svg.appendChild(randomSvgNode('circle', 'random-draw-node' + (k === chosenIdx ? ' is-picked' : ''), { cx: nx, cy: ny, r: 9 }));
      const text = randomSvgNode('text', 'random-draw-number' + (k === chosenIdx ? ' is-picked' : ''), { x: nx, y: ny + 3.5, 'text-anchor': 'middle' });
      text.textContent = String(k + 1);
      svg.appendChild(text);
    }
    const needle = randomSvgNode('g', 'random-draw-needle');
    needle.style.setProperty('--draw-angle', (chosenIdx * 60) + 'deg');
    needle.appendChild(randomSvgNode('line', 'random-draw-needle-line', { x1: cx, y1: cy, x2: cx, y2: 27 }));
    needle.appendChild(randomSvgNode('circle', 'random-draw-needle-tip', { cx, cy: 27, r: 3.5 }));
    svg.appendChild(needle);
    svg.appendChild(randomSvgNode('circle', 'random-draw-center', { cx, cy, r: 9 }));
    return svg;
  }

  function buildSticksForm(chosenIdx, label) {
    const svg = randomSvg('random-sticks-svg', label, '0 0 240 220');
    const xs = [74, 94, 114, 134, 154, 174];
    svg.appendChild(randomSvgNode('ellipse', 'random-stick-shadow', { cx: 124, cy: 207, rx: 72, ry: 8 }));
    svg.appendChild(randomSvgNode('ellipse', 'random-stick-rim-back', { cx: 124, cy: 122, rx: 84, ry: 17 }));
    xs.forEach((x, k) => {
      const stick = randomSvgNode('line', 'random-stick random-stick--' + (k + 1) + (k === chosenIdx ? ' is-picked' : ''), { x1: x, y1: 38 + (k % 3) * 6, x2: x, y2: 158 });
      stick.style.setProperty('--stick-delay', (k * 35) + 'ms');
      svg.appendChild(stick);
      if (k === chosenIdx) {
        svg.appendChild(randomSvgNode('circle', 'random-stick-mark', { cx: x, cy: 42 + (k % 3) * 6, r: 13 }));
        const no = randomSvgNode('text', 'random-stick-number', { x, y: 46 + (k % 3) * 6, 'text-anchor': 'middle' });
        no.textContent = String(k + 1);
        svg.appendChild(no);
      }
    });
    svg.appendChild(randomSvgNode('path', 'random-stick-cup', { d: 'M40 122 Q124 148 208 122 L188 204 Q124 216 60 204 Z' }));
    svg.appendChild(randomSvgNode('path', 'random-stick-cup-band', { d: 'M48 146 Q124 164 200 146 L196 162 Q124 180 52 162 Z' }));
    svg.appendChild(randomSvgNode('circle', 'random-stick-cup-seal', { cx: 124, cy: 176, r: 16 }));
    const seal = randomSvgNode('text', 'random-stick-cup-char', { x: 124, y: 181, 'text-anchor': 'middle' });
    seal.textContent = '签';
    svg.appendChild(seal);
    svg.appendChild(randomSvgNode('path', 'random-stick-rim-front', { d: 'M40 122 Q124 148 208 122' }));
    return svg;
  }

  function buildDiceForm(chosenIdx, label) {
    const stage = el('div', 'random-form-svg random-dice-canvas-stage');
    stage.setAttribute('role', 'img');
    stage.setAttribute('aria-label', label);
    stage.dataset.result = String(chosenIdx + 1);

    const shadow = el('span', 'random-dice-shadow');
    shadow.setAttribute('aria-hidden', 'true');
    const canvas = document.createElement('canvas');
    canvas.className = 'random-dice-canvas';
    canvas.width = 440;
    canvas.height = 440;
    canvas.setAttribute('aria-hidden', 'true');
    stage.appendChild(shadow);
    stage.appendChild(canvas);
    return stage;
  }

  function randomCssColor(node, name, fallback) {
    const value = getComputedStyle(node).getPropertyValue(name).trim();
    return value || fallback;
  }

  function startZdogDice(stage, chosenIdx) {
    if (!window.Zdog) return;
    const canvas = stage.querySelector('.random-dice-canvas');
    if (!canvas || canvas.dataset.ready === 'true') return;
    canvas.dataset.ready = 'true';

    const TAU = Zdog.TAU;
    const faceColors = [
      randomCssColor(stage, '--random-card-1', '#5d9f94'),
      randomCssColor(stage, '--random-die-top', '#eaf2ed'),
      randomCssColor(stage, '--random-card-2', '#799cc1'),
      randomCssColor(stage, '--random-card-5', '#bf9557'),
      randomCssColor(stage, '--random-card-3', '#b67486'),
      randomCssColor(stage, '--random-card-4', '#9b82b3')
    ];
    const lightPip = '#f8faf7';
    const darkPip = '#173128';
    const patterns = [
      [[0, 0]],
      [[-1, -1], [1, 1]],
      [[-1, -1], [0, 0], [1, 1]],
      [[-1, -1], [1, -1], [-1, 1], [1, 1]],
      [[-1, -1], [1, -1], [0, 0], [-1, 1], [1, 1]],
      [[-1, -1], [1, -1], [-1, 0], [1, 0], [-1, 1], [1, 1]]
    ];
    const illo = new Zdog.Illustration({
      element: canvas,
      zoom: 4.15,
      rotate: { x: -TAU * 35 / 360, y: TAU * 32 / 360 }
    });
    const die = new Zdog.Anchor({ addTo: illo });
    new Zdog.Box({
      addTo: die,
      width: 56,
      height: 56,
      depth: 56,
      stroke: false,
      color: faceColors[0],
      frontFace: faceColors[0],
      rearFace: faceColors[5],
      rightFace: faceColors[2],
      leftFace: faceColors[3],
      topFace: faceColors[1],
      bottomFace: faceColors[4]
    });
    const faces = [
      { value: 1, translate: { z: 30 } },
      { value: 6, translate: { z: -30 }, rotate: { y: TAU / 2 } },
      { value: 3, translate: { x: 30 }, rotate: { y: TAU / 4 } },
      { value: 4, translate: { x: -30 }, rotate: { y: -TAU / 4 } },
      { value: 2, translate: { y: -30 }, rotate: { x: -TAU / 4 } },
      { value: 5, translate: { y: 30 }, rotate: { x: TAU / 4 } }
    ];
    const faceData = [];

    faces.forEach(faceSpec => {
      const value = faceSpec.value;
      const face = new Zdog.Anchor({
        addTo: die,
        translate: faceSpec.translate,
        rotate: faceSpec.rotate || {}
      });
      const color = faceColors[value - 1];
      const plate = new Zdog.RoundedRect({
        addTo: face,
        width: 53,
        height: 53,
        cornerRadius: 10,
        stroke: 7,
        fill: true,
        color
      });
      const pips = patterns[value - 1].map(([x, y]) => (
        new Zdog.Anchor({
          addTo: face,
          translate: { x: x * 10.5, y: y * 10.5, z: 4.2 },
        })
      ));
      faceData.push({
        plate,
        pips,
        color: value === 2 || value === 4 ? darkPip : lightPip
      });
    });

    const renderFrame = () => {
      illo.updateRenderGraph();
      const ctx = canvas.getContext('2d');
      const visibleFaces = faceData.slice()
        .sort((a, b) => b.plate.renderOrigin.z - a.plate.renderOrigin.z)
        .slice(0, 3);
      ctx.save();
      ctx.translate(canvas.width / 2, canvas.height / 2);
      ctx.scale(illo.zoom, illo.zoom);
      visibleFaces.forEach(face => {
        ctx.fillStyle = face.color;
        face.pips.forEach(pip => {
          ctx.beginPath();
          ctx.arc(pip.renderOrigin.x, pip.renderOrigin.y, 3.7, 0, TAU);
          ctx.fill();
        });
      });
      ctx.restore();
    };

    const finalRotations = [
      { x: TAU / 4, y: 0, z: 0 },
      { x: 0, y: 0, z: 0 },
      { x: 0, y: 0, z: -TAU / 4 },
      { x: 0, y: 0, z: TAU / 4 },
      { x: TAU / 2, y: 0, z: 0 },
      { x: -TAU / 4, y: 0, z: 0 }
    ];
    const end = finalRotations[chosenIdx] || finalRotations[0];
    const start = {
      x: end.x - TAU * 2.25,
      y: end.y + TAU * 2.75,
      z: end.z - TAU * 1.5
    };
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reducedMotion) {
      Object.assign(die.rotate, end);
      renderFrame();
      return;
    }

    const duration = 1500;
    const startedAt = performance.now();
    const animate = now => {
      const progress = Math.min(1, (now - startedAt) / duration);
      const eased = 1 - Math.pow(1 - progress, 4);
      die.rotate.x = Zdog.lerp(start.x, end.x, eased);
      die.rotate.y = Zdog.lerp(start.y, end.y, eased);
      die.rotate.z = Zdog.lerp(start.z, end.z, eased);
      renderFrame();
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }

  function buildCardsForm(chosenIdx, label) {
    const svg = randomSvg('random-cards-svg', label, '0 0 260 220');
    const positions = [
      [42, 62, -16], [61, 56, -9], [80, 53, -3],
      [99, 53, 3], [118, 56, 9], [137, 62, 16]
    ];
    const order = [0, 1, 2, 3, 4, 5].filter(k => k !== chosenIdx).concat(chosenIdx);
    order.forEach(k => {
      const [x, y, angle] = positions[k];
      const card = randomSvgNode('g', 'random-card-form random-card--' + (k + 1) + (k === chosenIdx ? ' is-picked' : ''));
      card.style.setProperty('--card-x', x + 'px');
      card.style.setProperty('--card-y', y + 'px');
      card.style.setProperty('--card-angle', angle + 'deg');

      const back = randomSvgNode('g', 'random-card-back');
      back.appendChild(randomSvgNode('rect', 'random-card-back-face', { width: 74, height: 112, rx: 8 }));
      back.appendChild(randomSvgNode('path', 'random-card-back-frame', { d: 'M9 10H65V102H9Z' }));
      back.appendChild(randomSvgNode('path', 'random-card-back-weave random-card-back-weave--a', { d: 'M14 32L60 80M14 50L54 92M20 20L60 62' }));
      back.appendChild(randomSvgNode('path', 'random-card-back-weave random-card-back-weave--b', { d: 'M60 32L14 80M60 50L20 92M54 20L14 62' }));
      back.appendChild(randomSvgNode('circle', 'random-card-back-seal', { cx: 37, cy: 56, r: 15 }));
      card.appendChild(back);

      const front = randomSvgNode('g', 'random-card-front');
      front.appendChild(randomSvgNode('rect', 'random-card-face', { width: 74, height: 112, rx: 8 }));
      front.appendChild(randomSvgNode('path', 'random-card-pattern', { d: 'M12 20H62M12 28H62M12 84H62M12 92H62' }));
      front.appendChild(randomSvgNode('circle', 'random-card-seal', { cx: 37, cy: 56, r: 17 }));
      const no = randomSvgNode('text', 'random-card-number', { x: 37, y: 65, 'text-anchor': 'middle' });
      no.textContent = String(k + 1);
      front.appendChild(no);
      card.appendChild(front);
      svg.appendChild(card);
    });
    return svg;
  }

  function buildTicketsForm(options, chosenIdx, label) {
    const svg = randomSvg('random-tickets-svg', label, '0 0 240 220');
    const clipId = 'random-ticket-clip-' + (++randomSvgSerial);
    const defs = randomSvgNode('defs');
    const clip = randomSvgNode('clipPath', '', { id: clipId });
    clip.appendChild(randomSvgNode('rect', '', { x: 20, y: 34, width: 200, height: 132, rx: 8 }));
    defs.appendChild(clip);
    svg.appendChild(defs);
    svg.appendChild(randomSvgNode('rect', 'random-ticket-window', { x: 20, y: 34, width: 200, height: 132, rx: 8 }));
    svg.appendChild(randomSvgNode('line', 'random-ticket-line', { x1: 20, y1: 102, x2: 220, y2: 102 }));
    const clipped = randomSvgNode('g', '', { 'clip-path': 'url(#' + clipId + ')' });
    const strip = randomSvgNode('g', 'random-ticket-strip');
    strip.style.setProperty('--ticket-stop', (74 - chosenIdx * 42) + 'px');
    options.forEach((option, k) => {
      const y = 10 + k * 42;
      const ticket = randomSvgNode('g', 'random-ticket-row random-ticket--' + (k + 1) + (k === chosenIdx ? ' is-picked' : ''));
      ticket.appendChild(randomSvgNode('rect', 'random-ticket', { x: 34, y, width: 172, height: 32, rx: 4 }));
      ticket.appendChild(randomSvgNode('rect', 'random-ticket-accent', { x: 34, y, width: 7, height: 32, rx: 4 }));
      const text = randomSvgNode('text', 'random-ticket-text', { x: 47, y: y + 21 });
      text.textContent = String(k + 1).padStart(2, '0') + '  ' + String(option).slice(0, 7);
      ticket.appendChild(text);
      strip.appendChild(ticket);
    });
    clipped.appendChild(strip);
    svg.appendChild(clipped);
    return svg;
  }

  function buildInkForm(chosenIdx, label) {
    const svg = randomSvg('random-ink-svg', label, '0 0 240 220');
    const ends = [[35, 42], [120, 24], [205, 42], [208, 170], [120, 194], [32, 172]];
    const paths = [
      'M120 110 Q78 72 35 42', 'M120 110 Q120 64 120 24', 'M120 110 Q164 72 205 42',
      'M120 110 Q164 142 208 170', 'M120 110 Q120 154 120 194', 'M120 110 Q74 145 32 172'
    ];
    paths.forEach((d, k) => svg.appendChild(randomSvgNode('path', 'random-ink-branch' + (k === chosenIdx ? ' is-picked' : ''), { d, pathLength: 1 })));
    svg.appendChild(randomSvgNode('circle', 'random-ink-center', { cx: 120, cy: 110, r: 7 }));
    ends.forEach(([x, y], k) => {
      svg.appendChild(randomSvgNode('circle', 'random-ink-end' + (k === chosenIdx ? ' is-picked' : ''), { cx: x, cy: y, r: 12 }));
      const no = randomSvgNode('text', 'random-ink-number' + (k === chosenIdx ? ' is-picked' : ''), { x, y: y + 3.5, 'text-anchor': 'middle' });
      no.textContent = String(k + 1);
      svg.appendChild(no);
    });
    return svg;
  }

  /* ---- 天意：同一结果固定一种形式，不同决策随机换样式 ---- */
  function renderRandomExtra(o) {
    const options = Array.isArray(o.options) ? o.options.slice(0, 6) : [];
    const fallback = ['再想想', '换个角度', '问朋友', '睡一觉', '抛硬币', '跟着心走'];
    let i = 0;
    while (options.length < 6) options.push(fallback[i++ % fallback.length]);

    const seed = o.randomSeed || options.join('|');
    const fallbackIdx = randomHash(seed + '|choice') % options.length;
    const chosen = options.includes(o.wheelResult) ? o.wheelResult : options[fallbackIdx];
    const resolvedIdx = options.indexOf(chosen);
    const chosenIdx = resolvedIdx >= 0 ? resolvedIdx : fallbackIdx;
    const variants = ['pointer', 'sticks', 'dice', 'cards', 'tickets', 'ink'];
    const variant = variants[randomHash(seed + '|style') % variants.length];
    const label = I18N.t('random.result') + '：' + chosen;
    const builders = {
      pointer: () => buildPointerForm(chosenIdx, label),
      sticks: () => buildSticksForm(chosenIdx, label),
      dice: () => buildDiceForm(chosenIdx, label),
      cards: () => buildCardsForm(chosenIdx, label),
      tickets: () => buildTicketsForm(options, chosenIdx, label),
      ink: () => buildInkForm(chosenIdx, label)
    };

    const wrap = el('div', 'random-draw random-draw--' + variant);
    const stage = el('div', 'random-draw-stage');
    const visual = el('div', 'random-visual-wrap');
    const formVisual = builders[variant]();
    visual.appendChild(formVisual);
    stage.appendChild(visual);

    const optionList = el('div', 'random-draw-options');
    options.forEach((option, k) => {
      const item = el('div', 'random-draw-option' + (k === chosenIdx ? ' is-picked' : ''));
      item.appendChild(el('span', 'random-draw-option-no', String(k + 1)));
      item.appendChild(el('span', 'random-draw-option-text', option));
      optionList.appendChild(item);
    });
    stage.appendChild(optionList);
    wrap.appendChild(stage);

    const result = el('div', 'random-draw-result');
    result.textContent = I18N.t('random.result') + '：「' + chosen + '」';
    wrap.appendChild(result);
    requestAnimationFrame(() => requestAnimationFrame(() => {
      formVisual.classList.add('is-drawing');
      if (variant === 'dice') startZdogDice(formVisual, chosenIdx);
    }));
    return wrap;
  }

  /* ---- 自然：信号卡 + 诗意解读 ---- */
  function renderNatureExtra(o) {
    const n = o.nature || o;
    const card = el('div', 'nature-card');
    const considerations = [];
    addNatureItem(considerations, I18N.t('nature.alerts'), n.alarms || n.alerts || n.warnings);
    addNatureItem(considerations, I18N.t('nature.trend'), n.weatherTrend || n.trend);
    addNatureItem(considerations, I18N.t('nature.living'), n.life_indices || n.livingAdvice || n.tips);
    addNatureItem(considerations, I18N.t('nature.air'), n.airDetail || n.air_detail || n.airQuality || n.air);
    addNatureItem(considerations, I18N.t('nature.timeSeason'), [n.time, n.season, n.moonPhase].filter(Boolean).join(' · '));
    if (considerations.length) card.appendChild(renderNatureList(I18N.t('nature.considered'), considerations, 'nature-considerations'));

    const evidence = [];
    addNatureItem(evidence, I18N.t('nature.location'), n.city);
    addNatureItem(evidence, I18N.t('nature.weather'), n.weather);
    addNatureItem(evidence, I18N.t('nature.temperature'), n.temperature !== '' && n.temperature != null ? n.temperature + '℃' : '');
    addNatureItem(evidence, I18N.t('nature.wind'), n.wind);
    addNatureItem(evidence, I18N.t('nature.humidity'), n.humidity ? n.humidity + (String(n.humidity).includes('%') ? '' : '%') : '');
    addNatureItem(evidence, I18N.t('nature.sun'), n.sun);
    addNatureItem(evidence, I18N.t('nature.moon'), n.moonPhase);
    addNatureItem(evidence, I18N.t('nature.updated'), n.updateTime);
    if (evidence.length) {
      const title = I18N.t('nature.data') + ' · ' + I18N.t(n.isReal ? 'nature.realtime' : 'nature.degraded');
      card.appendChild(renderNatureList(title, evidence, 'nature-evidence'));
    }

    const weights = n.signals && Array.isArray(n.signals.weights) ? n.signals.weights.slice(0, 10) : [];
    if (weights.length) {
      const section = el('section', 'nature-section nature-weights');
      section.appendChild(el('h4', '', I18N.t('nature.weights')));
      weights.forEach(item => {
        const weight = Math.max(0, Math.min(100, Number(item.weight) || 0));
        if (!item.name || !weight) return;
        const row = el('div', 'nature-weight-row');
        row.appendChild(el('span', 'nature-weight-name', String(item.name)));
        const track = el('span', 'nature-weight-track');
        const bar = el('span', 'nature-weight-bar');
        bar.style.width = weight + '%';
        track.appendChild(bar);
        row.appendChild(track);
        row.appendChild(el('span', 'nature-weight-value', weight + '%'));
        section.appendChild(row);
      });
      card.appendChild(section);
    }

    const forecast = Array.isArray(n.forecast_1h) && n.forecast_1h.length ? n.forecast_1h : n.forecast_24h;
    if (Array.isArray(forecast) && forecast.length) {
      const section = el('section', 'nature-section nature-forecast');
      section.appendChild(el('h4', '', I18N.t('nature.forecast')));
      forecast.slice(0, 3).forEach(item => {
        if (!item || typeof item !== 'object') return;
        const info = item.infos || item.info || {};
        const value = [item.hour || item.time || item.forecast_time, item.weather || info.weather || item.text || info.text,
          item.temperature || info.temperature || item.temp || info.temp].filter(v => v !== '' && v != null).join(' · ');
        if (value) section.appendChild(el('div', 'nature-forecast-item', value));
      });
      card.appendChild(section);
    }

    if (n.poem) {
      const poem = el('div', 'nature-poem');
      poem.textContent = n.poem;
      card.appendChild(poem);
    }
    if (n.source) card.appendChild(el('div', 'nature-source', I18N.t('nature.source', { source: n.source }) + (n.isReal ? '' : I18N.t('nature.fallback'))));
    if (!card.childNodes.length) return null;
    return card;
  }

  function addNatureItem(items, label, value) {
    const text = natureText(value);
    if (text) items.push({ label, value: text });
  }

  function natureText(value) {
    if (Array.isArray(value)) return value.map(natureText).filter(Boolean).slice(0, 2).join('；');
    if (value && typeof value === 'object') {
      const candidates = [value.name, value.level, value.desc, value.title, value.text, value.description, value.value]
        .concat(Array.isArray(value.ids) ? value.ids : []);
      return candidates.map(natureText).filter(Boolean).slice(0, 3).join('；');
    }
    return String(value || '').trim();
  }

  function renderNatureList(title, items, className) {
    const section = el('section', 'nature-section ' + className);
    section.appendChild(el('h4', '', title));
    const grid = el('div', 'nature-data-grid');
    items.forEach(item => {
      const row = el('div', 'nature-data-item');
      row.appendChild(el('span', 'nature-data-label', item.label));
      row.appendChild(el('span', 'nature-data-value', item.value));
      grid.appendChild(row);
    });
    section.appendChild(grid);
    return section;
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
        window.dispatchEvent(new CustomEvent('bjj:dialogue-complete', { detail: { question: o.question || '', answer: opt } }));
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
      randomSeed: resp.decisionId || result.randomSeed || result.wheelResult || brief.summary || '',
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
      nature: result,
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
      randomSeed: d.id || result.randomSeed || result.wheelResult || d.question || '',
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
      nature: result,
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
