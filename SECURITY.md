# Security Policy

## Supported versions

`v0.8.x` receives security fixes while this project is actively maintained.

## Reporting a vulnerability

Please avoid posting real API keys, personal decisions, private images, local databases, or exploit details in public issues. Use GitHub Security Advisories when available, or contact the maintainer through the GitHub profile linked from the repository.

Include:

- affected route, script, or UI area
- reproduction steps
- expected impact
- whether private decision data, images, or provider credentials were involved

## Sensitive data

Do not commit:

- `.env`
- SQLite databases
- API keys or provider tokens
- local decision archives
- uploaded images or voice transcripts containing private information

## Provider boundary

When users configure third-party LLM, TTS, weather, or vision providers, data may leave the local machine. New features must keep that boundary explicit in README and `DISCLAIMER.md`.
