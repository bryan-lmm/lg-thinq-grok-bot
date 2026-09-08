# lg-thinq-grok-bot

Unofficial **ThinQ2** client for LG laundry specialty (SmartCourse) cycles and remote start. Not ThinQ Connect / PAT. Not affiliated with LG.

## Quick start

```bash
git clone https://github.com/bryan-lmm/lg-thinq-grok-bot.git
cd lg-thinq-grok-bot
./scripts/bootstrap.sh
```

Use the venv (`.venv/bin/thinq-specialty`). Bare `pip` often fails on PEP 668.

```bash
.venv/bin/thinq-specialty login
.venv/bin/thinq-specialty devices
.venv/bin/thinq-specialty courses --device DEVICE_ID
.venv/bin/thinq-specialty start --device DEVICE_ID --course COURSE_ID
.venv/bin/thinq-specialty start --device DEVICE_ID --course COURSE_ID --execute
```

Starts are dry-run until `--execute`. Put `THINQ_REFRESH_TOKEN` and `THINQ_CLIENT_ID` in a gitignored `.env` (or bot secrets). Keep the same client id.

## Why ThinQ2

Connect/PAT generally cannot select specialty cycles. ThinQ2 can list SmartCourse from model info and include those fields in `WMStart` payloads.

## Prior art

- [ollo69/ha-smartthinq-sensors](https://github.com/ollo69/ha-smartthinq-sensors) (Apache-2.0)
- [sampsyo/wideq](https://github.com/sampsyo/wideq) (MIT)

See [NOTICE](NOTICE) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Safety

Unofficial; API can change. Remote start needs the machine armed. Do not commit tokens.

## Auth

1. `thinq-specialty login` — open the URL and sign in.
2. After sign-in the page often looks like the login box again. That is normal. When the address bar has `access_token`, copy the full URL (or hit I'm done on a bot handoff).
3. `thinq-specialty login --callback-url '...'` prints env exports.

| Variable | Required | Purpose |
| --- | --- | --- |
| `THINQ_REFRESH_TOKEN` | yes | OAuth refresh token |
| `THINQ_CLIENT_ID` | recommended | Sticky id from login; do not rotate |
| `THINQ_COUNTRY` | no | Default `US` |
| `THINQ_LANGUAGE` | no | Default `en-US` |

## CLI notes

```bash
thinq-specialty courses --model-json tests/fixtures/sample_tower_washer.json --json
thinq-specialty start --model-json tests/fixtures/sample_tower_washer.json \
  --course SPECIALTY_CYCLE_1 --option steam=STEAM_ON
```

## License

MIT. Prior-art licenses in [NOTICE](NOTICE).
