/* ============================================================
   Chat — 首页聊天逻辑
   职责：模式选择 / 发送问题 / 调用 API / 渲染简报卡
   依赖：API, Brief, MODES, I18N, App（toast）
   ============================================================ */

const Chat = (() => {
  let currentMode = 'auto';
  let busy = false;
  let lastQuestion = '';
  let pendingImage = null; // data URL

  const $ = (id) => document.getElementById(id);

  function clearImage() {
    pendingImage = null;
    const imageInput = $('imageInput');
    const imagePreview = $('imagePreview');
    const imagePreviewImg = $('imagePreviewImg');
    if (imageInput) imageInput.value = '';
    if (imagePreview) imagePreview.hidden = true;
    if (imagePreviewImg) imagePreviewImg.src = '';
  }

  function init() {
    // 模式选择
    document.querySelectorAll('#modeSelector .mode-card').forEach(card => {
      card.addEventListener('click', () => {
        if (busy) return;
        setMode(card.getAttribute('data-mode'));
      });
    });

    // 快捷示例
    document.querySelectorAll('#quickExamples .quick-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        if (busy) return;
        $('inputText').value = chip.textContent;
        send();
      });
    });

    // 发送
    $('sendBtn').addEventListener('click', send);
    const ta = $('inputText');
    ta.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });
    ta.addEventListener('input', () => autoGrow(ta));

    // 语音输入
    const micBtn = $('micBtn');
    if (micBtn) {
      micBtn.addEventListener('click', () => Voice.toggleStt(ta));
      if (!Voice.sttSupported()) micBtn.style.display = 'none';
    }

    // 图片选择
    const imageBtn = $('imageBtn');
    const imageInput = $('imageInput');
    const imagePreview = $('imagePreview');
    const imagePreviewImg = $('imagePreviewImg');
    const imageRemove = $('imageRemove');
    if (imageBtn && imageInput) {
      imageBtn.addEventListener('click', () => imageInput.click());
      imageInput.addEventListener('change', (e) => {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        if (!file.type.startsWith('image/')) {
          App.toast(I18N.t('common.error'));
          return;
        }
        if (file.size > 5 * 1024 * 1024) {
          App.toast('图片不能超过 5MB');
          imageInput.value = '';
          return;
        }
        const reader = new FileReader();
        reader.onload = (ev) => {
          pendingImage = ev.target.result;
          imagePreviewImg.src = pendingImage;
          imagePreview.hidden = false;
        };
        reader.readAsDataURL(file);
      });
      if (imageRemove) {
        imageRemove.addEventListener('click', clearImage);
      }
    }

    // 新对话
    $('newChatBtn').addEventListener('click', () => {
      if (busy) return;
      reset();
    });

    // 风水追问 / 对话完成事件
    window.addEventListener('bjj:resubmit', (e) => {
      ta.value = lastQuestion + ' ' + e.detail;
      send();
    });
    window.addEventListener('bjj:dialogue-complete', () => {
      // 对话完成后保存当前决策
      if (App.currentDecision) {
        API.updateDecision(App.currentDecision.id, { dialogueDone: true }).catch(() => {});
      }
    });
  }

  function setMode(modeId) {
    if (!MODES.get(modeId)) return;
    currentMode = modeId;
    document.querySelectorAll('#modeSelector .mode-card').forEach(c => {
      const active = c.getAttribute('data-mode') === modeId;
      c.classList.toggle('active', active);
      c.setAttribute('aria-checked', active ? 'true' : 'false');
    });
    if (navigator.vibrate) navigator.vibrate(10);
  }

  function getMode() { return currentMode; }

  function autoGrow(ta) {
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 180) + 'px';
  }

  async function send() {
    if (busy) return;
    const text = $('inputText').value.trim();
    if (!text && !pendingImage) return;
    busy = true;
    lastQuestion = text || '(图片)';
    const imgToSend = pendingImage;
    $('sendBtn').disabled = true;
    $('inputText').value = '';
    autoGrow($('inputText'));
    clearImage();

    // 渲染用户消息（含图片）
    appendMessage('user', text || '', imgToSend);
    // 思考占位
    const thinking = appendThinking();

    try {
      const extra = {};
      if (imgToSend) extra.image = imgToSend;
      const resp = await API.chat(text || '请分析这张图片并给出建议', currentMode, extra);
      thinking.remove();
      // auto 模式识别提示
      const recognizedMode = resp.autoRecognized && resp.autoRecognized.mode;
      if (currentMode === 'auto' && recognizedMode && recognizedMode !== 'auto') {
        const m = MODES.get(recognizedMode);
        if (m) appendAutoHint(I18N.t('auto.recognized', { mode: I18N.t(m.nameKey) }));
      }
      // 渲染简报卡
      const card = Brief.fromResponse(resp);
      // 在卡顶部加朗读按钮
      if (Voice.ttsSupported() && resp.reply) {
        const speakBtn = Voice.makeSpeakButton(resp.reply);
        speakBtn.classList.add('brief-action-btn');
        card.insertBefore(speakBtn, card.firstChild);
      }
      appendCard(card);

      // 后端已自动落库，记录 decisionId 供后续标记 executed/regret
      if (resp.decisionId) {
        App.currentDecision = { id: resp.decisionId, mode: resp.mode };
      }

      // 自动朗读（偏好控制）
      if (Voice.ttsSupported() && resp.reply && App.prefs && App.prefs.auto_speak) {
        Voice.speak(resp.reply);
      }
    } catch (e) {
      thinking.remove();
      if (e && e.status === 402) {
        App.showKeyBanner && App.showKeyBanner();
        App.toast(I18N.t('api.keyRequired'));
      } else {
        appendError(e);
      }
    } finally {
      busy = false;
      $('sendBtn').disabled = false;
    }
  }

  function appendMessage(role, text, imageSrc) {
    const wrap = document.createElement('div');
    wrap.className = 'message ' + role;
    const bubble = document.createElement('div');
    bubble.className = 'bubble ' + role;
    if (imageSrc) {
      const img = document.createElement('img');
      img.src = imageSrc;
      img.className = 'bubble-image';
      img.alt = '';
      bubble.appendChild(img);
    }
    if (text) {
      const textNode = document.createElement('div');
      textNode.className = 'bubble-text';
      textNode.textContent = text;
      bubble.appendChild(textNode);
    }
    wrap.appendChild(bubble);
    getContainer().appendChild(wrap);
    scrollBottom();
  }

  function appendThinking() {
    const wrap = document.createElement('div');
    wrap.className = 'message ai';
    const t = document.createElement('div');
    t.className = 'thinking';
    t.innerHTML = '<span>' + I18N.t('common.thinking') + '</span><span class="loading-dots"><span></span><span></span><span></span></span>';
    wrap.appendChild(t);
    getContainer().appendChild(wrap);
    scrollBottom();
    return wrap;
  }

  function appendCard(node) {
    const wrap = document.createElement('div');
    wrap.className = 'message ai';
    wrap.appendChild(node);
    getContainer().appendChild(wrap);
    scrollBottom();
  }

  function appendAutoHint(text) {
    const wrap = document.createElement('div');
    wrap.className = 'auto-hint';
    wrap.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/><circle cx="12" cy="12" r="4"/></svg><span></span>';
    wrap.querySelector('span').textContent = text;
    getContainer().appendChild(wrap);
    scrollBottom();
  }

  function appendError(e) {
    const wrap = document.createElement('div');
    wrap.className = 'message ai';
    const t = document.createElement('div');
    t.className = 'thinking';
    t.style.color = 'var(--cinnabar)';
    const msg = (e && e.status === 'network') ? I18N.t('common.networkError') : I18N.t('common.error');
    t.textContent = msg;
    wrap.appendChild(t);
    getContainer().appendChild(wrap);
    scrollBottom();
    App.toast(msg);
  }

  function getContainer() {
    return $('chatContainer');
  }

  function scrollBottom() {
    const sc = $('chatScroll');
    requestAnimationFrame(() => { sc.scrollTop = sc.scrollHeight; });
  }

  function reset() {
    getContainer().innerHTML = '';
    App.currentDecision = null;
    setMode('auto');
  }

  return { init, setMode, getMode, reset };
})();
