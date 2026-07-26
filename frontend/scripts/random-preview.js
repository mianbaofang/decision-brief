(() => {
  const OPTIONS = ['现在就做', '明天再定', '先问朋友', '换个方案', '暂时放下', '凭直觉选'];
  const EFFECTS = [
    { variant: 'pointer', title: '指针盘', note: '转动后落在第 1 项', seed: 'preview-10', picked: 0 },
    { variant: 'sticks', title: '签筒', note: '晃两次后弹出第 2 签', seed: 'preview-6', picked: 1 },
    { variant: 'dice', title: '立体骰子', note: '翻滚后显示 3 点', seed: 'preview-1', picked: 2 },
    { variant: 'cards', title: '六张抽卡', note: '洗牌后翻开第 4 张', seed: 'preview-0', picked: 3 },
    { variant: 'tickets', title: '纸条机', note: '滚动后停在第 5 项', seed: 'preview-3', picked: 4 },
    { variant: 'ink', title: '墨迹择路', note: '六条路亮起第 6 条', seed: 'preview-13', picked: 5 }
  ];

  function renderEffect(effect, mount) {
    mount.replaceChildren(Brief.renderBrief({
      tone: 'random',
      modeName: '天意',
      percent: 100,
      title: effect.title,
      options: OPTIONS,
      wheelResult: OPTIONS[effect.picked],
      randomSeed: effect.seed
    }));
  }

  function createEffect(effect) {
    const section = document.createElement('section');
    section.className = 'preview-effect';
    section.dataset.variant = effect.variant;

    const bar = document.createElement('div');
    bar.className = 'preview-effect-bar';

    const title = document.createElement('div');
    title.className = 'preview-effect-title';
    title.innerHTML = '<h2></h2><span></span>';
    title.querySelector('h2').textContent = effect.title;
    title.querySelector('span').textContent = effect.note;

    const replay = document.createElement('button');
    replay.type = 'button';
    replay.className = 'preview-replay';
    replay.textContent = '↻';
    replay.title = '重新播放';
    replay.setAttribute('aria-label', '重新播放' + effect.title);

    const mount = document.createElement('div');
    mount.className = 'preview-mount';
    mount.dataset.previewVariant = effect.variant;

    replay.addEventListener('click', () => renderEffect(effect, mount));
    bar.append(title, replay);
    section.append(bar, mount);
    renderEffect(effect, mount);
    return section;
  }

  document.querySelectorAll('.preview-skin').forEach(button => {
    button.addEventListener('click', () => {
      document.documentElement.dataset.skin = button.dataset.skin;
      document.querySelectorAll('.preview-skin').forEach(item => {
        item.classList.toggle('is-active', item === button);
      });
    });
  });

  const grid = document.getElementById('previewGrid');
  EFFECTS.forEach(effect => grid.appendChild(createEffect(effect)));
})();
