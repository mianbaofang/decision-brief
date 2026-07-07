# Contributing

Thanks for improving Decision Brief. Keep changes small, practical, and respectful of the project's local-first privacy boundary.

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

## Before opening a pull request

- Run the relevant tests.
- Do not commit `.env`, local SQLite databases, screenshots with private decisions, API keys, or provider credentials.
- Update README, `DISCLAIMER.md`, or `ACKNOWLEDGEMENTS.md` when a user-facing capability or third-party service changes.
- Keep high-stakes decision boundaries visible. The app must not present itself as legal, medical, financial, or psychological advice.

## Privacy rules

- Treat prompts, archived decisions, uploaded images, and voice transcripts as sensitive.
- Do not add telemetry or remote sync without clear user opt-in.
- If a feature sends data to a third-party provider, document what is sent and why.
