/* ============================================================
   Voice — 语音输入（STT）+ 语音输出（TTS，浏览器原生 SpeechSynthesis）
   职责：
     - STT：点击麦克风按钮启动/停止识别，结果写入 textarea
     - TTS：朗读决策简报的 reply（自动 + 手动喇叭按钮）
     - 设置页：发音人/语速/音调/试听
   依赖：I18N, App（prefs / toast）
   说明：
     - STT 用 Web Speech API SpeechRecognition（Chrome/Edge 支持）
     - TTS 用浏览器原生 SpeechSynthesis（Windows 默认调用微软 SAPI，免费）
   ============================================================ */

const Voice = (() => {
  const $ = (id) => document.getElementById(id);

  /* ---------- STT ---------- */
  let recognition = null;
  let recognizing = false;
  let sttTarget = null; // 当前识别结果写入的 textarea

  function sttSupported() {
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  }

  // 把 i18n 语言代码转 BCP-47（SpeechRecognition 接受的）
  function bcp47(lang) {
    switch (lang) {
      case 'zh-CN': return 'zh-CN';
      case 'yue':   return 'zh-HK';   // 粤语 fallback 到香港普通话识别
      case 'en':    return 'en-US';
      case 'fr':    return 'fr-FR';
      case 'ja':    return 'ja-JP';
      case 'es':    return 'es-ES';
      default:      return 'zh-CN';
    }
  }

  function ensureRecognition() {
    if (recognition) return recognition;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return null;
    recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = bcp47(I18N.getLocale());
    recognition.onresult = (e) => {
      if (!sttTarget) return;
      let final = '';
      let interim = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) final += r[0].transcript;
        else interim += r[0].transcript;
      }
      if (final) sttTarget.value = (sttTarget.value ? sttTarget.value + ' ' : '') + final.trim();
      else if (interim) sttTarget.dataset.interim = interim;
    };
    recognition.onerror = (e) => {
      recognizing = false;
      setMicState(false);
      if (e.error === 'not-allowed') App.toast(I18N.t('chat.mic.notSupported'));
      else if (e.error !== 'aborted' && e.error !== 'no-speech') App.toast(I18N.t('chat.mic.notSupported'));
    };
    recognition.onend = () => {
      recognizing = false;
      setMicState(false);
      if (sttTarget && sttTarget.dataset.interim) {
        delete sttTarget.dataset.interim;
      }
    };
    return recognition;
  }

  function setMicState(on) {
    const btn = $('micBtn');
    if (!btn) return;
    btn.classList.toggle('listening', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    btn.setAttribute('aria-label', I18N.t(on ? 'chat.mic.listening' : 'chat.mic'));
  }

  function toggleStt(textareaEl) {
    if (!sttSupported()) {
      App.toast(I18N.t('chat.mic.notSupported'));
      return;
    }
    if (recognizing) {
      try { recognition.stop(); } catch (_) {}
      recognizing = false;
      setMicState(false);
      return;
    }
    sttTarget = textareaEl;
    const r = ensureRecognition();
    if (!r) {
      App.toast(I18N.t('chat.mic.notSupported'));
      return;
    }
    r.lang = bcp47(I18N.getLocale());
    try {
      r.start();
      recognizing = true;
      setMicState(true);
    } catch (_) {
      recognizing = false;
      setMicState(false);
    }
  }

  /* ---------- TTS ----------
   * 双通道：优先 edge-tts（后端 /api/tts/speak 返回 MP3），失败降级到浏览器 SpeechSynthesis。
   * edge 支持更自然的神经音色（晓晓/云希等），离线/网络异常时仍可朗读。
   */

  let edgeUnavailable = false;  // 一次失败后标记，避免反复请求
  let edgeAudio = null;         // 当前 Audio 元素（edge 通道）

  function browserTtsSupported() {
    return !!window.speechSynthesis && typeof window.speechSynthesis.speak === 'function';
  }

  function ttsSupported() {
    return true;  // edge 或 browser 总有一个能用（edge 通过后端）
  }

  function edgeTtsUrl(text, opts = {}) {
    const prefs = App.prefs || {};
    const params = new URLSearchParams();
    params.set('text', text);
    const voice = opts.voice || prefs.tts_voice_uri || 'zh-CN-XiaoxiaoNeural';
    params.set('voice', voice);
    const rate = (opts.rate != null ? opts.rate : prefs.tts_rate) || 0.95;
    const pitch = (opts.pitch != null ? opts.pitch : prefs.tts_pitch) || 1.05;
    params.set('rate', String(rate));
    params.set('pitch', String(pitch));
    return '/api/tts/speak?' + params.toString();
  }

  function stop() {
    // 停 edge
    if (edgeAudio) {
      try { edgeAudio.pause(); edgeAudio.src = ''; } catch (_) {}
      edgeAudio = null;
    }
    // 停浏览器
    if (browserTtsSupported()) {
      try { window.speechSynthesis.cancel(); } catch (_) {}
    }
  }

  function isSpeaking() {
    if (edgeAudio && !edgeAudio.paused && !edgeAudio.ended) return true;
    if (browserTtsSupported() && window.speechSynthesis.speaking) return true;
    return false;
  }

  function _speakBrowser(text, opts = {}) {
    if (!browserTtsSupported()) return;
    try { window.speechSynthesis.cancel(); } catch (_) {}
    const u = new SpeechSynthesisUtterance(text);
    const prefs = App.prefs || {};
    u.rate = typeof prefs.tts_rate === 'number' ? prefs.tts_rate : 0.95;
    u.pitch = typeof prefs.tts_pitch === 'number' ? prefs.tts_pitch : 1.05;
    u.lang = bcp47(prefs.language || 'zh-CN');
    // 不指定 voice，用系统默认（edge 通道才是音色主力）
    if (opts.onend) u.onend = opts.onend;
    if (opts.onstart) u.onstart = opts.onstart;
    if (opts.onerror) u.onerror = opts.onerror;
    window.speechSynthesis.speak(u);
  }

  // 用 edge-tts 播放，返回 Promise 以支持失败降级
  function _speakEdge(text, opts = {}) {
    return new Promise((resolve, reject) => {
      if (edgeUnavailable) return reject(new Error('edge unavailable'));
      stop();
      const audio = new Audio();
      audio.src = edgeTtsUrl(text, opts);
      audio.preload = 'auto';
      let settled = false;
      const done = (err) => {
        if (settled) return;
        settled = true;
        if (err) reject(err);
        else resolve();
      };
      audio.addEventListener('canplaythrough', () => {
        try { audio.play().catch(done); } catch (e) { done(e); }
      }, { once: true });
      audio.addEventListener('play', () => {
        if (opts.onstart) opts.onstart();
      }, { once: true });
      audio.addEventListener('ended', () => {
        edgeAudio = null;
        if (opts.onend) opts.onend();
        done();
      }, { once: true });
      audio.addEventListener('error', (e) => {
        edgeAudio = null;
        // 网络/后端异常：标记 edge 不可用，后续降级浏览器
        edgeUnavailable = true;
        done(e.error || new Error('edge tts error'));
      }, { once: true });
      edgeAudio = audio;
      audio.load();
      // 5 秒没 canplaythrough 视为失败
      setTimeout(() => {
        if (!settled && (audio.readyState < 2)) {
          try { audio.pause(); } catch (_) {}
          edgeUnavailable = true;
          done(new Error('edge tts timeout'));
        }
      }, 5000);
    });
  }

  async function speak(text, opts = {}) {
    if (!text) return;
    try {
      await _speakEdge(text, opts);
    } catch (e) {
      // edge 失败降级浏览器
      _speakBrowser(text, opts);
    }
  }

  // 手动朗读按钮（插入到简报卡顶部）
  function makeSpeakButton(text) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'icon-button speak-button';
    btn.setAttribute('aria-label', I18N.t('chat.speak'));
    btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M15.54 8.46a5 5 0 0 1 0 7.07"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14"/></svg>';
    let speaking = false;
    const onStart = () => {
      speaking = true;
      btn.classList.add('speaking');
      btn.setAttribute('aria-label', I18N.t('chat.speak.stop'));
    };
    const onEnd = () => {
      speaking = false;
      btn.classList.remove('speaking');
      btn.setAttribute('aria-label', I18N.t('chat.speak'));
    };
    btn.addEventListener('click', () => {
      if (speaking) {
        stop();
        onEnd();
      } else {
        speak(text, { onstart: onStart, onend: onEnd });
      }
    });
    return btn;
  }

  // 音色列表：首次从后端拉取，缓存
  let voicesCache = null;
  async function getEdgeVoices(lang) {
    if (voicesCache) return voicesCache;
    try {
      const url = lang ? `/api/tts/voices?lang=${encodeURIComponent(lang)}` : '/api/tts/voices';
      const resp = await fetch(url);
      const data = await resp.json();
      voicesCache = data.voices || [];
    } catch (e) {
      voicesCache = [];
    }
    return voicesCache;
  }

  function resetEdgeAvailability() {
    edgeUnavailable = false;
  }

  return {
    sttSupported,
    ttsSupported,
    toggleStt,
    speak,
    stop,
    isSpeaking,
    makeSpeakButton,
    getEdgeVoices,
    resetEdgeAvailability,
    edgeTtsUrl,
  };
})();
