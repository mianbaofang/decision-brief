# Decision Brief · 别纠结

<p align="center">
  <strong>Compress your dilemma into one sentence.</strong><br>
  Text, voice, or photo — you name the choice. We turn anxiety into evidence, risks, and a next step you can act on.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v0.8.4-blue" alt="version">
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="license">
  <img src="https://img.shields.io/badge/i18n-6%20langs-orange" alt="i18n">
  <img src="https://img.shields.io/badge/multimodal-vision-purple" alt="multimodal">
</p>

---

## In One Sentence

**Decision Brief (别纠结)** is a local-first decision-making assistant. It does not decide for you — it untangles your overthinking into verifiable evidence, visible risks, and a concrete first move.

Type (or speak, or attach a photo), pick one of six lenses (or let "Auto" choose), and get a structured decision brief in seconds. Every decision is auto-archived. Mark it executed or regretted later. Review your patterns over time.

<p align="center">
  <a href="https://mianbaofang.github.io/decision-brief/index-en.html">
    <img src="docs/images/intro-animation-preview-en.gif" alt="Decision Brief English intro animation preview" width="100%">
  </a>
</p>

<p align="center">
  <a href="README.md">中文</a>
  ·
  <a href="https://mianbaofang.github.io/decision-brief/">中文介绍动画</a>
  ·
  <a href="https://mianbaofang.github.io/decision-brief/index-en.html">English Intro</a>
</p>

## Why I Built This

The idea for Decision Brief came from tidying up a room with my daughter.

She's in sixth grade. That day we were sorting through her room together — desks, cabinets, drawers full of stuff: old notebooks, little toys, stickers, craft projects, half-used stationery, and a few things she herself couldn't decide whether to keep or not.

The hard part wasn't the cleaning. It was that every step required a choice.

Should this stay? Is that still usable? Does this have sentimental value? Do I do the desk first or the drawers? What if I throw it away and miss it later?

What looks simple to an adult isn't simple to a child. Many things have some reason to keep, and some reason to let go. She wasn't unwilling to clean — she just needed a moment to think about each small decision. Think too much, and you get tired. The room stays messy.

That moment made me realize: adults are the same. Our "rooms" are just work, life, relationships, and plans.

Many choices aren't without answers — they're just tangled together. Emotion, risk, habit, attachment, fear of regret, all squeezed into one question. Someone telling you "just pick this" doesn't necessarily help, because the person who has to live with the result is still you.

So I wanted to build a tool that helps lay choices out first.

It doesn't decide for you — "keep or toss," "do it or don't." It's more like someone sitting beside you asking a few questions: Why do you want to keep it? What happens if you don't? How big is the cost really? Is there a tiny first step you could try?

That's the original intention behind Decision Brief. I want it to solve a very specific scenario: when you're stuck on a pile of small judgments, you have a lightweight tool that helps you articulate the problem, separate the reasons, and make the next step feel less heavy.

That's why this demo isn't just a random wheel. Random works for "what should I eat for dinner" — low-stakes calls — but not for every choice. And I didn't make it into a complicated productivity system either, because when you're stuck in overthinking, you usually don't have the patience to fill out forms. One sentence should be enough to start.

The current design offers several entry points: if you want serious analysis, use Rational mode for benefits, risks, reversibility, and value alignment; if you're stuck on something small, Random gives you a nudge; if you need a different angle, Nature or Fengshui offer perspective (for reference and entertainment only); if you can't even articulate why you're stuck, Dialogue mode guides you through step-by-step questions.

The boundary I care about most: it can only assist your choice; it cannot bear the choice for you. Especially with life decisions, what really matters isn't whether the answer "looks right," but whether you've thought through why you're choosing it. If it can move someone from "I don't know what to do" to "I know what first step I can take," it has done its job.

## Quick Start

```bash
# 1. Install dependencies
pip install -e ".[dev]"      # dev mode
# or
pip install -r requirements.txt

# 2. Run the server
cd backend
python main.py
```

Open in your browser:

- Web UI: <http://localhost:8000/>
- API docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/api/health>

**Works out of the box**: without an LLM key, the server returns well-formed mock briefs so you can explore the full UI. Weather service is built-in, no sign-up needed. Drop in your own OpenAI-compatible API key (vision models like GPT-4o, Doubao-vision, or Qwen-VL unlock photo input) to enable real AI analysis.

## Six Lenses

<p align="center">
  <img src="docs/images/home-en.png" width="720" alt="Mode selector">
</p>

| Lens | Seal | When to use | What you get |
| --- | :---: | --- | --- |
| **Auto** | 自 | You aren't sure which lens fits — let the router pick | Best-fit lens, chosen from your wording |
| **Rational** | 理 | Quitting a job, buying a house, big-ticket purchases | Pros / risks / reversibility / smallest next step / confidence score |
| **Random** | 随 | Lunch, movie, which road to take — low-stakes calls | Shortlist + a randomized pick, with a little ceremony |
| **Nature** | 然 | Stuck emotionally, relationship calls, needing perspective | Time of day, weather, wind direction, natural signals |
| **Dialogue** | 问 | You already know the answer but can't admit it | 3–5 rounds of questions that help you hear yourself |
| **Fengshui** | 局 | Timing, direction, five-element balance for extra context | BaZi chart + favorable elements + daily direction |

## Screenshots

<p align="center">
  <img src="docs/images/auto-en.png" width="45%" />
  <img src="docs/images/rational-en.png" width="45%" />
  <img src="docs/images/nature-en.png" width="45%" />
  <img src="docs/images/dialogue-en.png" width="45%" />
  <img src="docs/images/fengshui-en.png" width="45%" />
  <img src="docs/images/archive-en.png" width="45%" />
  <img src="docs/images/stats-en.png" width="45%" />
  <img src="docs/images/settings-en.png" width="45%" />
</p>

## Highlights

- **🎴 Seal-style mode picker**: six single-character Chinese seal buttons (自 / 理 / 随 / 然 / 问 / 局) on a paper-textured canvas
- **⌨️🎙️🖼️ Tri-modal input**: a spacious rounded composer card that supports typing, voice dictation, and image upload (multimodal vision)
- **💬 Streaming chat**: briefs render segment by segment, with a confidence ring and highlighted keywords
- **📁 Archive**: every decision saved automatically; mark as executed / regretted; open details; delete; sidebar refreshes live
- **📊 Statistics**: execution rate, regret rate, mode distribution, and timeline review
- **🔊 TTS readout**: Edge TTS with selectable voices (free, no key required); optional auto-speak preference
- **🌦️ Built-in weather**: set your city and get real-time weather as context for the Nature lens (Amap API, key bundled)
- **🌗 Light / Dark / System themes**, saved locally and persisted across reloads
- **🌍 6 languages**: Simplified Chinese, Traditional Chinese, English, French, Japanese, Spanish
- **💾 Local-first**: persisted in SQLite (WAL mode); your data stays on your machine
- **🖥️ Responsive**: two-pane + drawer on desktop, single-pane on mobile; the composer is roomy and comfortable on every screen
- **🔌 CLI + Web dual entry**: both use the same backend and database
- **🧪 Graceful mock mode**: the full flow works without any API key for easy preview and development

## The Composer

The input area is a large rounded card in the style of modern AI chat apps:

- **Left**: image upload button (tap to pick a photo; thumbnail preview with one-tap remove; up to 5 MB)
- **Middle**: multi-line textarea (auto-grows, Shift+Enter for newline, Enter to send)
- **Right**: microphone for voice input + a teal send button

When a vision model is configured, photos are sent in the standard OpenAI multimodal format, so the model can look at your image and give advice grounded in what it sees.

## Configuring your LLM Key

On first launch, open **Settings → AI Config** and paste any OpenAI-compatible key (OpenAI, MiniMax, DeepSeek, Moonshot, local Ollama, Doubao, etc.). Without a key the server returns mock data so you can try everything.

Environment variables (highest priority):

```bash
export CHOICE_LLM_API_KEY=sk-xxx
export CHOICE_LLM_MODEL=gpt-4o-mini          # swap to gpt-4o / qwen-vl for images
export CHOICE_LLM_BASE_URL=https://api.openai.com/v1
export CHOICE_WEATHER_CITY=Beijing           # weather key is bundled, city only
```

Save to SQLite via CLI:

```bash
python scripts/choice_assistant.py --action config-api --save-to-db \
  --api-key sk-xxx \
  --llm-model gpt-4o-mini \
  --llm-base-url https://api.openai.com/v1 \
  --weather-city Beijing
```

## CLI Usage

```bash
# One-shot decision
python scripts/choice_assistant.py -q "Should I take the new job offer?"
python scripts/choice_assistant.py -q "What should I have for dinner?" --mode random

# Archive & stats
python scripts/choice_assistant.py --action archive
python scripts/choice_assistant.py --action stats

# Manage a single decision
python scripts/choice_assistant.py --action decision --id <id>
python scripts/choice_assistant.py --action decision --id <id> --delete
```

See [SKILL.md](SKILL.md) for the full parameter list.

## Tech Stack

| Layer | Tech |
| --- | --- |
| Backend | Python 3.9+ / FastAPI / SQLite (WAL) / httpx |
| Frontend | Vanilla HTML · CSS · JavaScript (zero build step, zero framework) |
| CLI | Python argparse + httpx, shares backend & DB with the Web UI |
| AI | Any OpenAI-compatible endpoint (bring your own key; vision models enable multimodal image input) |
| TTS | Microsoft Edge TTS (free, no key required; selectable voices) |
| STT | Browser-native Web Speech API (free) |
| Weather | Amap Web API (key bundled, works out of the box) |
| Tests | pytest + Playwright (UI automation) |

## Project Structure

```
choice-skill/
├── backend/              # FastAPI backend
│   ├── main.py           # Entrypoint & static file mount
│   ├── config.py         # 3-tier config (env / SQLite / file) + bundled weather key
│   ├── db.py             # SQLite wrapper
│   ├── routes/           # chat / archive / stats / config / tts / modes
│   └── services/         # LLM (multimodal) / mode router / bazi / weather / scorer
├── frontend/             # Static web UI (no build tools)
│   ├── index.html
│   ├── scripts/          # app / chat / archive / stats / settings / voice / i18n / api / brief
│   └── styles/           # main / chat / archive / stats / settings / desktop
├── scripts/              # CLI entry
├── tests/                # pytest + Playwright test suite
├── docs/                 # GitHub Pages intro, screenshots, animated GIF
├── SKILL.md              # Skill spec & invocation examples
└── README.en.md          # This file
```

## License & Credits

- **License**: MIT, see [LICENSE](LICENSE)
- **Thanks to**:
  - BaZi engine inspired by [jinchenma94/bazi-skill](https://github.com/jinchenma94/bazi-skill) (MIT)
  - De-AI-ification style inspired by [op7418/humanizer-zh](https://github.com/op7418/humanizer-zh)
- **External services**:
  - LLM: any OpenAI-compatible endpoint (bring your own key; vision models for images)
  - TTS: Microsoft Edge TTS (built-in, free)
  - STT: browser Web Speech API (free)
  - Weather: Amap Open Platform (built-in key, works out of the box)

---

<p align="center">Stop overthinking. Start moving.<br>Made with ❤️ for people who overthink.</p>
