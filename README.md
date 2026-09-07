# lg-thinq-grok-bot

Public package for **LG ThinQ specialty (download/SmartCourse) cycles** plus **Grok Bot** natural-language laundry control.

This is an unofficial **ThinQ2 (app) API** client. It is **not** LG ThinQ Connect / PAT, and it is **not** affiliated with LG Electronics.

## Quick start

```bash
git clone https://github.com/bryan-lmm/lg-thinq-grok-bot.git
cd lg-thinq-grok-bot
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Set LG credentials via the **bot secret card** (refresh token / country / language). Do not paste secrets into chat or commit them.

Then run:

```bash
thinq-specialty login
thinq-specialty devices
thinq-specialty courses --device DEVICE_ID
thinq-specialty start --device DEVICE_ID --course COURSE_ID   # dry-run by default
thinq-specialty start --device DEVICE_ID --course COURSE_ID --execute
```

CLI entry point: `thinq-specialty`.

## Why ThinQ2 (not Connect PAT)

LG's official **ThinQ Connect / PAT** API is useful for device list, state, and a small control surface. On laundry devices it **generally cannot select specialty (download/SmartCourse) cycles**, and it omits many start-option fields the appliance model declares.

The community reverse-engineered **ThinQ2 app API** can list those cycles from model info and include them in remote-start payloads. This package talks ThinQ2 over the internet as a standalone Python library.

## Prior art (please credit)

Heavy credit to the projects that documented ThinQ and laundry remote start:

- **[ollo69/ha-smartthinq-sensors](https://github.com/ollo69/ha-smartthinq-sensors)** (Apache-2.0) — ThinQ2 laundry `WMStart` payloads, `CourseType.COURSE` vs `CourseType.SMARTCOURSE`, model-info catalogs. Specialty cycles live in **SmartCourse**.
- **[sampsyo/wideq](https://github.com/sampsyo/wideq)** (MIT) — original unofficial ThinQ client: gateway discovery, EMP OAuth, refresh tokens.

See [NOTICE](NOTICE) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Safety

- Unofficial. LG may change the app API; this library may break.
- Terms-of-use gray area. Use at your own risk.
- Remote start still requires the appliance to allow it (door closed, remote start enabled on the machine, etc.).
- LG may rate-limit. Prefer dumping model JSON once and working offline with `--model-json`.
- Never commit tokens. Auth is environment / bot secrets only.

## Auth

ThinQ2 uses **LG account OAuth**, not a ThinQ Connect PAT.

1. `thinq-specialty login` — open the printed URL, sign in, copy the redirected callback URL.
2. `thinq-specialty login --callback-url '...'` — prints env exports.
3. Store the refresh token via the **bot secret card** (or `THINQ_REFRESH_TOKEN` in a local gitignored `.env`).

| Variable | Required | Purpose |
| --- | --- | --- |
| `THINQ_REFRESH_TOKEN` | yes (after login) | Long-lived OAuth refresh token |
| `THINQ_COUNTRY` | no | Default `US` |
| `THINQ_LANGUAGE` | no | Default `en-US` |

## CLI notes

All `start` commands are **dry-run by default**. They print the JSON that would be sent and do not call the appliance until you pass `--execute`.

```bash
thinq-specialty devices
thinq-specialty courses --device DEVICE_ID
thinq-specialty courses --model-json tests/fixtures/sample_tower_washer.json --json
thinq-specialty start --model-json tests/fixtures/sample_tower_washer.json \
  --course SPECIALTY_CYCLE_1 --option steam=STEAM_ON
thinq-specialty start --device DEVICE_ID --course SPECIALTY_CYCLE_1 --execute
```

## License

MIT. Prior-art licenses are listed in [NOTICE](NOTICE).
