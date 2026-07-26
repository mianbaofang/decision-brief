# Changelog

## v0.9.0 - 2026-07-26

### Added

- Four switchable interface styles: Heritage, Quiet Workbench, Decision Journal, and Modular Console.
- Six browser-rendered random effects: pointer draw, fortune sticks, 3D dice, six-card draw, ticket machine, and ink path.
- Richer Nature evidence including location, temperature, humidity, wind, daylight, moon phase, forecast, alerts, air information, and signal weights.
- Dialogue answer history persisted as question-and-answer pairs in `dialogueHistory`.
- User-managed Amap weather Key, Base URL, and city settings in both Web and CLI flows.
- Detailed Chinese and English feature maps and module-level project structure documentation.
- Updated Chinese and English intro animations with the Mini Program logo, four interface styles, and six random effects.

### Changed

- Reused the Mini Program logo in the open-source desktop interface.
- Renamed the user-facing Fengshui label to Traditional Culture while keeping the internal `fengshui` id for compatibility.
- Reworked the random result presentation and added a standalone effect preview page.
- Nature mode now uses live Amap data only when both Key and Base URL are configured; otherwise it clearly labels simulated weather.
- Removed the previously embedded weather credential and corrected public documentation that described weather as built in.
- Updated repository discovery metadata and added a downloadable source archive to the Release.

### Fixed

- Dialogue option clicks now save the selected answer instead of sending an unused completion flag.
- Weather settings no longer show the bare label "simulated data" without explaining when it is used.
- Static asset versions were bumped so updated settings and translations are not hidden by browser cache.

### Verification

- `87 passed, 15 skipped` in the full pytest suite.
- `15 passed` in the desktop Playwright suite.
- Browser console clean; desktop settings and random effect layouts checked without horizontal overflow.

## v0.8.4 - 2026-07-07

### Added

- Local-first decision archive with Web UI and CLI access.
- Six decision lenses: Auto, Rational, Random, Nature, Dialogue, and Fengshui.
- Multimodal input support for text, voice, and image-based decision context.
- Internationalized UI with Chinese and English README files.
- TTS, browser speech input, weather context, archive, statistics, and mock fallback mode.
- Public repository materials: disclaimer, acknowledgements, security policy, contribution guide, and GitHub templates.

### Notes

- This project is decision-support software, not professional advice.
- Users should read `DISCLAIMER.md` before using it for personal or high-stakes decisions.
