/* ============================================================
   Settings — 设置页
   职责：LLM 配置 / 天气配置 / 语言 / 主题 / 用户偏好
   依赖：API, MODES, I18N, App
   ============================================================ */

const Settings = (() => {
  const $ = (id) => document.getElementById(id);
  let configCache = null;
  let prefsCache = null;

  function init() {
    $('setLanguage').addEventListener('click', openLanguage);
    $('setTheme').addEventListener('click', openTheme);
    $('setDefaultMode').addEventListener('click', openDefaultMode);
    $('setValues').addEventListener('click', openValues);
    $('setAIConfig').addEventListener('click', () => openLLM());
    $('setWeatherConfig').addEventListener('click', () => openWeather());
    $('setTTS').addEventListener('click', openTTS);
    $('setAbout').addEventListener('click', openAbout);
    loadConfig();
  }

  async function loadConfig() {
    try {
      configCache = await API.getConfig();
      refreshConfigValues();
    } catch (e) { /* 忽略 */ }
  }

  function refreshConfigValues() {
    const cfg = configCache;
    if (!cfg) return;
    if ($('aiConfigValue')) {
      const has = cfg.hasLlm;
      const model = cfg.llm && cfg.llm.model ? cfg.llm.model : '';
      $('aiConfigValue').textContent = has ? (model || '✓') : 'API Key';
    }
    if ($('weatherConfigValue')) {
      const has = cfg.hasWeather;
      const city = cfg.weather && cfg.weather.city ? cfg.weather.city : '';
      $('weatherConfigValue').textContent = has
        ? (city ? city + ' · ' + I18N.t('settings.weather.realtime') : I18N.t('settings.weather.realtime'))
        : I18N.t('settings.weather.simulated');
    }
  }

  /** 刷新右侧显示值（语言/主题/模式等） */
  function refreshValues() {
    const prefs = App.prefs || {};
    if ($('languageValue')) {
      const lk = 'lang.' + (prefs.language || 'zh-CN');
      $('languageValue').textContent = I18N.t(lk);
    }
    if ($('themeValue')) {
      const tk = prefs.theme ? 'settings.theme.' + prefs.theme : 'settings.theme.auto';
      $('themeValue').textContent = I18N.t(tk);
    }
    if ($('defaultModeValue')) {
      const m = MODES.get(prefs.default_mode || prefs.defaultMode || 'auto') || MODES.get('auto');
      $('defaultModeValue').textContent = I18N.t(m.nameKey);
    }
    if ($('valuesValue')) {
      const v = prefs.values;
      if (v) {
        $('valuesValue').textContent = [v.efficiency, v.risk, v.growth, v.relationship].filter(x => x != null).join(' / ');
      }
    }
    // TTS 状态：显示当前音色名
    if ($('ttsValue')) {
      const voiceUri = prefs.tts_voice_uri || 'zh-CN-XiaoxiaoNeural';
      $('ttsValue').textContent = voiceUri;  // 先显示 id，等音色列表加载完再替换为中文名
      Voice.getEdgeVoices().then(vs => {
        const v = vs.find(x => x.id === voiceUri);
        if (v && $('ttsValue')) {
          $('ttsValue').textContent = v.name + (prefs.auto_speak === false ? ' ·' : '');
        }
      }).catch(() => {});
    }
  }

  /* ---------- 语言 ---------- */
  function openLanguage() {
    const list = document.createElement('div');
    list.className = 'lang-list';
    const langs = [
      { id: 'zh-CN', key: 'lang.zh-CN' },
      { id: 'yue', key: 'lang.yue' },
      { id: 'en', key: 'lang.en' },
      { id: 'fr', key: 'lang.fr' },
      { id: 'ja', key: 'lang.ja' },
      { id: 'es', key: 'lang.es' }
    ];
    const current = I18N.getLang();
    langs.forEach(l => {
      const opt = document.createElement('button');
      opt.type = 'button';
      opt.className = 'lang-opt' + (l.id === current ? ' active' : '');
      opt.innerHTML = '<span>' + I18N.t(l.key) + '</span><svg class="check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" aria-hidden="true"><path d="M5 12l5 5 9-11"/></svg>';
      opt.addEventListener('click', async () => {
        I18N.setLang(l.id);
        App.prefs.language = l.id;
        try { await API.savePreferences({ language: l.id }); } catch (e) {}
        App.applyPrefs(App.prefs);
        I18N.apply();
        refreshValues();
        App.closeModal();
        App.toast(I18N.t('settings.saved'));
      });
      list.appendChild(opt);
    });
    App.openModal(list, { title: I18N.t('settings.language') });
  }

  /* ---------- 主题 ---------- */
  function openTheme() {
    const row = document.createElement('div');
    row.className = 'choice-row';
    const opts = [
      { id: 'light', key: 'settings.theme.light', icon: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M19 5l-1.5 1.5M6.5 17.5L5 19"/>' },
      { id: 'dark', key: 'settings.theme.dark', icon: '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>' },
      { id: 'auto', key: 'settings.theme.auto', icon: '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="M3 12h18"/>' }
    ];
    const current = (App.prefs && App.prefs.theme) || 'auto';
    opts.forEach(o => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'choice-opt' + (o.id === current ? ' active' : '');
      b.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">' + o.icon + '</svg><span></span>';
      b.querySelector('span').textContent = I18N.t(o.key);
      b.addEventListener('click', async () => {
        try {
          const saved = await API.savePreferences({ theme: o.id });
          Object.assign(App.prefs, saved || { theme: o.id });
        } catch (e) {
          App.prefs.theme = o.id;
        }
        App.applyTheme(o.id);
        refreshValues();
        App.closeModal();
        App.toast(I18N.t('settings.saved'));
      });
      row.appendChild(b);
    });
    App.openModal(row, { title: I18N.t('settings.theme') });
  }

  /* ---------- 默认模式 ---------- */
  function openDefaultMode() {
    const grid = document.createElement('div');
    grid.className = 'mode-pick-grid';
    const current = (App.prefs && (App.prefs.default_mode || App.prefs.defaultMode)) || 'auto';
    MODES.list().forEach(m => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'mode-pick' + (m.id === current ? ' active' : '');
      b.innerHTML = MODES.sealSVG(m.id, { size: 26, rounded: 5 }) + '<span></span>';
      b.querySelector('span').textContent = I18N.t(m.nameKey);
      b.addEventListener('click', async () => {
        App.prefs.default_mode = m.id;
        Chat.setMode(m.id);
        try { await API.savePreferences({ default_mode: m.id }); } catch (e) {}
        refreshValues();
        App.closeModal();
        App.toast(I18N.t('settings.saved'));
      });
      grid.appendChild(b);
    });
    App.openModal(grid, { title: I18N.t('settings.defaultMode') });
  }

  /* ---------- 价值观权重 ---------- */
  function openValues() {
    const wrap = document.createElement('div');
    const v = (App.prefs && App.prefs.values) || { efficiency: 50, risk: 50, growth: 50, relationship: 50 };
    const items = [
      { id: 'efficiency', key: 'settings.values.efficiency' },
      { id: 'risk', key: 'settings.values.risk' },
      { id: 'growth', key: 'settings.values.growth' },
      { id: 'relationship', key: 'settings.values.relationship' }
    ];
    items.forEach(it => {
      const s = document.createElement('div');
      s.className = 'value-slider';
      const val = v[it.id] != null ? v[it.id] : 50;
      s.innerHTML = '<div class="vs-head"><span class="vs-name">' + I18N.t(it.key) + '</span><span class="vs-val">' + val + '</span></div>';
      const input = document.createElement('input');
      input.type = 'range';
      input.min = '0'; input.max = '100'; input.value = String(val);
      input.setAttribute('aria-label', I18N.t(it.key));
      input.addEventListener('input', () => {
        s.querySelector('.vs-val').textContent = input.value;
      });
      s.appendChild(input);
      wrap.appendChild(s);
    });
    const saveBtn = document.createElement('button');
    saveBtn.className = 'btn btn-block';
    saveBtn.style.marginTop = '8px';
    saveBtn.textContent = I18N.t('settings.save');
    saveBtn.addEventListener('click', async () => {
      const inputs = wrap.querySelectorAll('input[type="range"]');
      const newV = {};
      items.forEach((it, i) => { newV[it.id] = parseInt(inputs[i].value, 10); });
      App.prefs.values = newV;
      try { await API.savePreferences({ values: newV }); } catch (e) {}
      refreshValues();
      App.closeModal();
      App.toast(I18N.t('settings.saved'));
    });
    wrap.appendChild(saveBtn);
    App.openModal(wrap, { title: I18N.t('settings.values') });
  }

  /* ---------- LLM 配置 ---------- */
  async function openLLM() {
    if (!configCache) {
      try { configCache = await API.getConfig(); } catch (e) { configCache = {}; }
    }
    const cfg = (configCache && configCache.llm) || {};
    const keyPh = cfg.hasKey ? '***已配置***（留空则不修改）' : 'sk-...';
    const wrap = document.createElement('div');
    wrap.innerHTML =
      fieldHTML('llm_apiKey', I18N.t('settings.llm.apiKey'), '', 'password', keyPh) +
      fieldHTML('llm_model', I18N.t('settings.llm.model'), cfg.model || '', 'text', 'gpt-4o-mini') +
      fieldHTML('llm_baseUrl', I18N.t('settings.llm.baseUrl'), cfg.baseUrl || '', 'text', 'https://api.openai.com/v1');
    const save = document.createElement('button');
    save.className = 'btn btn-block';
    save.style.marginTop = '4px';
    save.textContent = I18N.t('settings.save');
    save.addEventListener('click', async () => {
      const apiKeyVal = wrap.querySelector('#llm_apiKey').value.trim();
      const modelVal = wrap.querySelector('#llm_model').value.trim();
      const baseUrlVal = wrap.querySelector('#llm_baseUrl').value.trim();
      const payload = {};
      if (apiKeyVal) payload.llm_api_key = apiKeyVal;
      if (modelVal) payload.llm_model = modelVal;
      if (baseUrlVal) payload.llm_base_url = baseUrlVal;
      try {
        const updated = await API.saveConfig(payload);
        configCache = updated;
        App.closeModal();
        App.toast(I18N.t('settings.saved'));
        refreshConfigValues();
        if (updated && updated.hasLlm) App.hideKeyBanner();
      } catch (e) {
        App.toast(I18N.t('common.error'));
      }
    });
    wrap.appendChild(save);
    App.openModal(wrap, { title: I18N.t('settings.llm') });
  }

  /* ---------- 天气配置（高德开放平台） ---------- */
  async function openWeather() {
    if (!configCache) {
      try { configCache = await API.getConfig(); } catch (e) { configCache = {}; }
    }
    const cfg = (configCache && configCache.weather) || {};
    const wrap = document.createElement('div');

    const tip = document.createElement('div');
    tip.className = 'weather-tip';
    tip.textContent = I18N.t('settings.weather.tip');
    wrap.appendChild(tip);

    wrap.appendChild(document.createElement('div')).innerHTML =
      fieldHTML('w_city', I18N.t('settings.weather.city'), cfg.city || '', 'text', '北京');
    const save = document.createElement('button');
    save.className = 'btn btn-block';
    save.style.marginTop = '4px';
    save.textContent = I18N.t('settings.save');
    save.addEventListener('click', async () => {
      const cityVal = wrap.querySelector('#w_city').value.trim();
      const payload = {};
      if (cityVal) payload.weather_city = cityVal;
      try {
        const updated = await API.saveConfig(payload);
        configCache = updated;
        refreshConfigValues();
        App.closeModal();
        App.toast(I18N.t('settings.saved'));
      } catch (e) {
        App.toast(I18N.t('common.error'));
      }
    });
    wrap.appendChild(save);
    App.openModal(wrap, { title: I18N.t('settings.weather') });
  }

  function fieldHTML(id, label, value, type, ph) {
    return '<div class="field"><label for="' + id + '">' + Brief.esc(label) + '</label><input id="' + id + '" type="' + type + '" value="' + Brief.esc(value) + '" placeholder="' + Brief.esc(ph) + '" autocomplete="off"/></div>';
  }

  /* ---------- 关于 ---------- */
  function openAbout() {
    const wrap = document.createElement('div');
    wrap.className = 'about-wrap';

    // 顶部 logo + 标题 + 版本
    const head = document.createElement('div');
    head.className = 'about-head';
    head.innerHTML =
      '<div class="about-logo" aria-hidden="true"><svg viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M5,7 C14,2 8,14 18,22 C14,28 18,33 20,35" stroke="rgba(244,245,239,0.35)" stroke-width="1.5" stroke-linecap="round" fill="none"/><path d="M10,5 C2,12 20,16 10,24 C6,30 14,33 20,35" stroke="rgba(244,245,239,0.45)" stroke-width="1.5" stroke-linecap="round" fill="none"/><path d="M16,6 C8,10 28,18 12,26 C10,30 16,33 20,35" stroke="rgba(244,245,239,0.55)" stroke-width="1.6" stroke-linecap="round" fill="none"/><path d="M24,6 C32,10 12,18 28,26 C30,30 24,33 20,35" stroke="rgba(244,245,239,0.55)" stroke-width="1.6" stroke-linecap="round" fill="none"/><path d="M30,5 C38,12 20,16 30,24 C34,30 26,33 20,35" stroke="rgba(244,245,239,0.45)" stroke-width="1.5" stroke-linecap="round" fill="none"/><path d="M35,7 C26,2 32,14 22,22 C26,28 22,33 20,35" stroke="rgba(244,245,239,0.35)" stroke-width="1.5" stroke-linecap="round" fill="none"/><path d="M20,5 C20,14 20,24 20,35" stroke="rgba(244,245,239,0.95)" stroke-width="2" stroke-linecap="round" fill="none"/><circle cx="20" cy="35" r="1.5" fill="rgba(244,245,239,0.95)"/></svg></div>' +
      '<div class="about-title">' + Brief.esc(I18N.t('app.title')) + '</div>' +
      '<div class="about-sub">' + Brief.esc(I18N.t('app.subtitle')) + '</div>' +
      '<div class="about-ver">v0.8.4 · MIT</div>';
    wrap.appendChild(head);

    // 5 段内容
    const sections = [
      { key: 'about.why',      textKey: 'about.why.text' },
      { key: 'about.features', textKey: 'about.features.text' },
      { key: 'about.disclaimer', textKey: 'about.disclaimer.text' },
      { key: 'about.license',  textKey: 'about.license.text' },
      { key: 'about.credits',  textKey: 'about.credits.text' },
    ];
    sections.forEach(s => {
      const sec = document.createElement('section');
      sec.className = 'about-section';
      const h = document.createElement('h3');
      h.textContent = I18N.t(s.key);
      const p = document.createElement('p');
      p.textContent = I18N.t(s.textKey);
      sec.appendChild(h);
      sec.appendChild(p);
      wrap.appendChild(sec);
    });

    App.openModal(wrap, { title: I18N.t('settings.about') });
  }

  /* ---------- 语音朗读（TTS） ---------- */
  async function openTTS() {
    const prefs = App.prefs || {};
    const wrap = document.createElement('div');
    wrap.className = 'tts-wrap';

    // 自动朗读开关
    const autoRow = document.createElement('div');
    autoRow.className = 'tts-row tts-toggle-row';
    autoRow.innerHTML =
      '<div class="tts-row-label">' + Brief.esc(I18N.t('settings.tts.autoSpeak')) + '</div>' +
      '<label class="switch"><input type="checkbox" id="tts_auto"' + (prefs.auto_speak !== false ? ' checked' : '') + '><span class="slider" aria-hidden="true"></span></label>';
    wrap.appendChild(autoRow);

    // 语速
    const rateRow = document.createElement('div');
    rateRow.className = 'tts-row';
    const rateVal = prefs.tts_rate != null ? prefs.tts_rate : 0.95;
    rateRow.innerHTML =
      '<div class="tts-row-label">' + Brief.esc(I18N.t('settings.tts.rate')) + ' <span class="tts-num" id="tts_rate_val">' + rateVal.toFixed(2) + '</span></div>';
    const rateInput = document.createElement('input');
    rateInput.type = 'range'; rateInput.min = '0.5'; rateInput.max = '1.5'; rateInput.step = '0.05';
    rateInput.value = String(rateVal);
    rateInput.setAttribute('aria-label', I18N.t('settings.tts.rate'));
    rateInput.addEventListener('input', () => {
      $('tts_rate_val').textContent = parseFloat(rateInput.value).toFixed(2);
    });
    rateRow.appendChild(rateInput);
    wrap.appendChild(rateRow);

    // 音调
    const pitchRow = document.createElement('div');
    pitchRow.className = 'tts-row';
    const pitchVal = prefs.tts_pitch != null ? prefs.tts_pitch : 1.05;
    pitchRow.innerHTML =
      '<div class="tts-row-label">' + Brief.esc(I18N.t('settings.tts.pitch')) + ' <span class="tts-num" id="tts_pitch_val">' + pitchVal.toFixed(2) + '</span></div>';
    const pitchInput = document.createElement('input');
    pitchInput.type = 'range'; pitchInput.min = '0.5'; pitchInput.max = '1.5'; pitchInput.step = '0.05';
    pitchInput.value = String(pitchVal);
    pitchInput.setAttribute('aria-label', I18N.t('settings.tts.pitch'));
    pitchInput.addEventListener('input', () => {
      $('tts_pitch_val').textContent = parseFloat(pitchInput.value).toFixed(2);
    });
    pitchRow.appendChild(pitchInput);
    wrap.appendChild(pitchRow);

    // 发音人（edge 神经音色）
    const voiceRow = document.createElement('div');
    voiceRow.className = 'tts-row tts-voice-row';
    voiceRow.innerHTML = '<div class="tts-row-label">' + Brief.esc(I18N.t('settings.tts.voice')) + '</div>';
    const voiceSelect = document.createElement('select');
    voiceSelect.className = 'tts-voice-select';
    const voicePh = document.createElement('option');
    voicePh.value = '';
    voicePh.textContent = '…';
    voicePh.disabled = true;
    voicePh.selected = true;
    voiceSelect.appendChild(voicePh);
    voiceRow.appendChild(voiceSelect);
    wrap.appendChild(voiceRow);

    const currentUri = prefs.tts_voice_uri || 'zh-CN-XiaoxiaoNeural';
    const curLang = I18N.getLocale();

    const btnRow = document.createElement('div');
    btnRow.className = 'tts-btn-row';
    const testBtn = document.createElement('button');
    testBtn.type = 'button';
    testBtn.className = 'btn btn-ghost';
    testBtn.textContent = I18N.t('settings.tts.test');
    testBtn.disabled = true;
    testBtn.addEventListener('click', () => {
      const sample = {
        'zh-CN': '这是一个决策辅助工具，帮你把纠结拆成可判断的证据和下一步。',
        'yue': '呢個係一個決策輔助工具，幫你將糾結拆成可判斷嘅證據。',
        'en': 'This is a decision aid that breaks your dilemma into judgeable evidence and next steps.',
        'fr': 'Voici un outil d\'aide à la décision qui décompose votre dilemme en preuves.',
        'ja': 'これは決断補助ツールで、迷いを判断できる証拠と次の一手に分解します。',
        'es': 'Esta herramienta descompone tu dilema en pruebas y próximos pasos.',
      }[curLang] || 'This is a decision aid.';
      Voice.speak(sample, { voice: voiceSelect.value, rate: parseFloat(rateInput.value), pitch: parseFloat(pitchInput.value) });
    });
    const saveBtn = document.createElement('button');
    saveBtn.type = 'button';
    saveBtn.className = 'btn';
    saveBtn.textContent = I18N.t('settings.save');
    saveBtn.addEventListener('click', async () => {
      const payload = {
        auto_speak: $('tts_auto').checked,
        tts_rate: parseFloat(rateInput.value),
        tts_pitch: parseFloat(pitchInput.value),
        tts_voice_uri: voiceSelect.value || 'zh-CN-XiaoxiaoNeural',
      };
      Object.assign(App.prefs, payload);
      Voice.resetEdgeAvailability();
      try {
        await API.savePreferences(payload);
        if ($('ttsValue')) {
          const selOpt = voiceSelect.options[voiceSelect.selectedIndex];
          const name = selOpt ? selOpt.textContent.split(' — ')[0] : payload.tts_voice_uri;
          $('ttsValue').textContent = name + (payload.auto_speak === false ? ' ·' : '');
        }
        refreshValues();
        App.closeModal();
        App.toast(I18N.t('settings.saved'));
      } catch (e) {
        App.toast(I18N.t('common.error'));
      }
    });
    btnRow.appendChild(testBtn);
    btnRow.appendChild(saveBtn);
    wrap.appendChild(btnRow);

    App.openModal(wrap, { title: I18N.t('settings.tts') });

    (async function fillVoices() {
      try {
        const TIMEOUT_MS = 8000;
        const allVoices = await Promise.race([
          Voice.getEdgeVoices(),
          new Promise((_, rej) => setTimeout(() => rej(new Error('tts-timeout')), TIMEOUT_MS))
        ]);
        const groups = {};
        allVoices.forEach(v => {
          const g = groups[v.lang] || (groups[v.lang] = []);
          g.push(v);
        });
        const orderedLangs = [curLang, 'zh-CN', 'yue', 'en', 'ja', 'fr', 'es'].filter((l, i, arr) => arr.indexOf(l) === i);
        const langLabel = { 'zh-CN': '中文', 'yue': '粵語', 'en': 'English', 'ja': '日本語', 'fr': 'Français', 'es': 'Español' };
        voiceSelect.innerHTML = '';
        orderedLangs.forEach(lg => {
          const list = groups[lg];
          if (!list || !list.length) return;
          const grp = document.createElement('optgroup');
          grp.label = langLabel[lg] || lg;
          list.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v.id;
            opt.textContent = v.name + (v.gender === 'F' ? ' ♀' : v.gender === 'M' ? ' ♂' : '') + ' — ' + v.desc;
            if (v.id === currentUri) opt.selected = true;
            grp.appendChild(opt);
          });
          voiceSelect.appendChild(grp);
        });
        if (!voiceSelect.value && currentUri) {
          const opt = document.createElement('option');
          opt.value = currentUri;
          opt.textContent = currentUri;
          opt.selected = true;
          voiceSelect.insertBefore(opt, voiceSelect.firstChild);
        }
        testBtn.disabled = false;
      } catch (e) {
        voiceSelect.innerHTML = '';
        const opt = document.createElement('option');
        opt.value = 'zh-CN-XiaoxiaoNeural';
        opt.textContent = '晓晓 (默认)';
        opt.selected = true;
        voiceSelect.appendChild(opt);
        testBtn.disabled = false;
      }
    })();
  }

  return { init, refreshValues };
})();
