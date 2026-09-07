# Architecture

This document describes how **lg-thinq-specialty-cycles** maps laundry cycles and start-option fields on the unofficial ThinQ2 app API, and why that differs from the official ThinQ Connect / PAT API.

Nothing here is an official LG specification. The layout was learned from public community clients, especially [ollo69/ha-smartthinq-sensors](https://github.com/ollo69/ha-smartthinq-sensors) and [sampsyo/wideq](https://github.com/sampsyo/wideq).

## ThinQ Connect (PAT) vs ThinQ2 (app)

```
┌─────────────────────┐     PAT + small public profile
│ ThinQ Connect API   │──── list / state / start-stop of an already chosen cycle
│ (official, PAT)     │     specialty cycles and many option fields are absent
└─────────────────────┘

┌─────────────────────┐     LG account OAuth
│ ThinQ2 app API      │──── dashboard, modelJsonUri, control-sync
│ (unofficial)        │     Course + SmartCourse catalogs from model info
└─────────────────────┘
```

ThinQ Connect is a documented developer API. A Personal Access Token authenticates a reduced device profile. On laundry appliances that profile usually allows monitoring and a coarse start/stop/wake. It does **not** generally expose:

- the **SmartCourse / download** catalog (specialty cycles the app can push to the machine)
- many **start-option fields** that exist on the model JSON (flags and enums the app sends with `WMStart`)

ThinQ2 is the API the consumer app uses. After EMP OAuth, clients:

1. `GET` `service/application/gateway-uri` (via `route.lgthinq.com`) for regional hosts
2. `GET` `{thinq2Uri}/service/application/dashboard` (or `service/homes`) for devices
3. Download `modelJsonUri` — a JSON document describing catalogs and controls
4. `POST` `{thinq2Uri}/service/devices/{id}/control-sync` with a `WMStart` envelope

This library implements that path only. It does not wrap the ThinQ Connect SDK.

## Why specialty lives in SmartCourse

ThinQ2 laundry model JSON has more than one course table. Community code (ollo69 `CourseType`) treats them as:

| Family | Typical Config key | Typical section | Meaning |
| --- | --- | --- | --- |
| `Course` | `courseType` | `Course` | Base cycles on the dial / standard list |
| `SmartCourse` | `smartCourseType` or `downloadedCourseType` | `SmartCourse` | Download / specialty cycles |
| `OpCourse` | `opCourseType` | `OpCourse` | Operator / extra table on some models |

A ThinQ2 `MonitoringValue` entry is often a **reference**: `courseType` in `Config` points at a key such as `courseSampleTowerWasher`, and that key's `ref` is the `Course` table. The same pattern applies to SmartCourse.

**The gap:** UI lists that only iterate `CourseType.COURSE` never show download cycles. Those ids still exist in the model and are accepted on remote start when `courseType` is `SmartCourse` and the smart-course key carries the id.

This client always loads **both** tables into one catalog.

## Generic payload shape

Remote start is a ThinQ2 `control-sync` POST. The envelope is:

```json
{
  "command": "Set",
  "ctrlKey": "WMStart",
  "dataSetList": {
    "washerDryer": {
      "courseType": "SmartCourse",
      "<course key from model>": "NOT_SELECTED",
      "<smart course key from model>": "<specialty cycle id>",
      "initialBit": "INITIAL_BIT_ON",
      "<option field present in the device model>": "<model-allowed value>"
    }
  }
}
```

For a **base** cycle the same envelope uses `"courseType": "Course"`, puts the id on the course key, and sets the smart-course key to `NOT_SELECTED`.

Rules used by the builder (aligned with ollo69's `_prepare_command_v2` / `_prepare_course_info`):

- Specialty: smart-course key = selected id; course key = optional base id from the SmartCourse entry (`Course` / `APCourse`) or `NOT_SELECTED`.
- Base: course key = selected id; smart-course key = `NOT_SELECTED` when that key exists.
- `courseType` comes from the cycle family (`Course` vs `SmartCourse`).
- `initialBit` is set to `INITIAL_BIT_ON` when starting from idle remote-start.
- Each cycle may list `function` entries `{ "value": "<field>", "default": "<value>" }`. Those defaults are copied onto the body.
- Additional keys come from `ControlWifi.WMStart.data.washerDryer` when present.
- Callers may override **start-option fields present in the device model**. Unknown names are rejected unless `--force`.

Key names are model-specific (`course…`, `smartCourse…`, option enums). Do not hard-code a marketing cycle name; always read the catalog.

## Device types used in fixtures

The optional synthetic fixture is a generic US WashTower-shaped ThinQ2 washer:

- `SAMPLE_TOWER_WASHER`
- ThinQ `deviceType` **221** (tower washer). **222** is the matching tower dryer family.

No personal serials or account identifiers are included.

## Dry-run vs execute

`build_remote_start` and `thinq-specialty start` only construct JSON. `ThinQClient.execute_start` / `--execute` is the only path that POSTs `control-sync`. Prefer inspecting the dry-run body, then sending once. LG may rate-limit repeated control calls.

## Out of scope

- ThinQ1 binary/XML washer protocols
- Official ThinQ Connect PAT wrappers
- MQTT event streams
- Copying GPL-licensed ThinQ2 source
