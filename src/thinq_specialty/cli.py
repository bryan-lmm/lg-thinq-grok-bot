"""Command-line interface: login, devices, courses, start (dry-run by default)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

from . import __version__
from .auth import credentials_from_callback, discover_gateway
from .catalog import CourseCatalog
from .client import ThinQClient
from .const import DEFAULT_COUNTRY, DEFAULT_LANGUAGE, DEFAULT_TIMEOUT
from .devices import Device, describe_device_type
from .exceptions import ThinQError
from .start import RemoteStartPlan, build_remote_start

PROG = "thinq-specialty"


def _country() -> str:
    return os.environ.get("THINQ_COUNTRY", DEFAULT_COUNTRY).strip() or DEFAULT_COUNTRY


def _language() -> str:
    return os.environ.get("THINQ_LANGUAGE", DEFAULT_LANGUAGE).strip() or DEFAULT_LANGUAGE


def _http() -> httpx.Client:
    return httpx.Client(timeout=DEFAULT_TIMEOUT, follow_redirects=True)


def _print_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


def _load_model(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ThinQError("Model JSON must be an object")
    return payload


def _parse_options(pairs: list[str] | None) -> dict[str, Any]:
    options: dict[str, Any] = {}
    for item in pairs or []:
        if "=" not in item:
            raise ThinQError(f"Option {item!r} must be field=value")
        name, value = item.split("=", 1)
        if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
            options[name] = int(value)
        else:
            options[name] = value
    return options


def cmd_login(args: argparse.Namespace) -> int:
    country = args.country or _country()
    language = args.language or _language()
    with _http() as client:
        gateway = discover_gateway(client, country=country, language=language)
        if not args.callback_url:
            print("Unofficial ThinQ2 login (LG account OAuth).")
            print()
            print("1. Open this URL in a browser and sign in:")
            print()
            print(f"   {gateway.login_url()}")
            print()
            print("2. After sign-in the browser is redirected. Copy the full URL")
            print("   from the address bar (it may start with lgaccount.lgsmartthinq:).")
            print("3. Re-run with --callback-url '<pasted url>'.")
            print()
            print("Tokens are printed as env exports. Do not commit them.")
            return 0
        creds = credentials_from_callback(client, gateway, args.callback_url)
    print("# Add these to your shell. Do not commit them or paste them into issues.")
    sys.stdout.write(creds.export_lines())
    return 0


def cmd_devices(args: argparse.Namespace) -> int:
    with ThinQClient.from_env() as client:
        devices = client.list_devices(laundry_only=not args.all)
    if not devices:
        print("No devices found on this account.")
        return 0
    rows = [
        {
            "device_id": item.device_id,
            "name": item.name,
            "model": item.model_name,
            "type": describe_device_type(item.device_type),
            "device_type_code": int(item.device_type),
            "platform": item.platform_type,
            "online": item.online,
        }
        for item in devices
    ]
    if args.json:
        _print_json(rows)
        return 0
    for row in rows:
        online = "online" if row["online"] else "offline"
        print(
            f"{row['device_id']}  {row['name']}  "
            f"{row['model']}  {row['type']} ({row['device_type_code']})  "
            f"{row['platform']}  {online}"
        )
    return 0


def _catalog_for(
    client: ThinQClient | None,
    *,
    device_id: str | None,
    model_json: str | None,
) -> tuple[CourseCatalog, Device | None]:
    if model_json:
        catalog = CourseCatalog.from_model(_load_model(model_json))
        device = None
        if client and device_id:
            try:
                device = client.get_device(device_id)
            except ThinQError:
                device = None
        return catalog, device
    if not client or not device_id:
        raise ThinQError("Provide --device and/or --model-json")
    device = client.get_device(device_id)
    return client.course_catalog(device), device


def cmd_courses(args: argparse.Namespace) -> int:
    client: ThinQClient | None = None
    try:
        if args.device and not args.model_json:
            client = ThinQClient.from_env()
        catalog, device = _catalog_for(client, device_id=args.device, model_json=args.model_json)
    finally:
        if client:
            client.close()

    payload = {
        "model_type": catalog.model_type,
        "device_id": device.device_id if device else None,
        "course_key": catalog.course_key,
        "smart_course_key": catalog.smart_course_key,
        "courses": [
            {
                "id": item.course_id,
                "type": item.course_type.value,
                "label": item.label,
                "specialty": item.is_specialty,
                "base_course_id": item.base_course_id,
                "defaults": item.defaults,
            }
            for item in catalog.courses
        ],
        "start_option_fields": [
            {
                "name": item.name,
                "allowed_values": list(item.allowed_values),
                "default": item.default,
            }
            for item in catalog.start_option_fields
        ],
    }
    if args.json:
        _print_json(payload)
        return 0

    print(f"Model: {catalog.model_type}")
    if device:
        print(f"Device: {device.name} ({device.device_id})")
    print(f"Course key: {catalog.course_key}")
    print(f"SmartCourse key: {catalog.smart_course_key}")
    print()
    print("Cycles (base + specialty):")
    for item in catalog.courses:
        kind = "specialty/SmartCourse" if item.is_specialty else "base/Course"
        print(f"  {item.course_id:24}  {kind:22}  {item.label}")
    print()
    print("Start-option fields present in the device model:")
    if not catalog.start_option_fields:
        print("  (none declared)")
    for item in catalog.start_option_fields:
        values = ", ".join(item.allowed_values[:8])
        extra = "..." if len(item.allowed_values) > 8 else ""
        suffix = f"  [{values}{extra}]" if values else ""
        print(f"  {item.name}{suffix}")
    return 0


def _print_plan(plan: RemoteStartPlan, *, execute: bool) -> None:
    mode = "EXECUTE" if execute else "DRY-RUN"
    print(f"[{mode}] course={plan.course.course_id} type={plan.course.course_type.value}")
    for note in plan.notes:
        print(f"# {note}")
    _print_json(plan.as_control_payload())
    if not execute:
        print(
            "# Dry-run only. The payload was not sent. "
            "Re-run with --execute to POST control-sync."
        )


def cmd_start(args: argparse.Namespace) -> int:
    if args.execute and args.model_json and not args.device:
        raise ThinQError("--execute requires --device")
    options = _parse_options(args.option)
    client: ThinQClient | None = None
    try:
        needs_client = bool(args.device) and (args.execute or not args.model_json)
        if needs_client:
            client = ThinQClient.from_env()
        if args.model_json:
            catalog, device = _catalog_for(
                client, device_id=args.device, model_json=args.model_json
            )
            plan = build_remote_start(
                catalog, args.course, options=options, strict_options=not args.force
            )
        else:
            if not client or not args.device:
                raise ThinQError("Provide --device (or --model-json for an offline dry-run)")
            device = client.get_device(args.device)
            plan = client.plan_start(device, args.course, options=options)

        if args.execute:
            if not device:
                raise ThinQError("--execute requires a live --device")
            assert client is not None
            result = client.execute_start(device.device_id, plan)
            _print_plan(plan, execute=True)
            print("# Service response:")
            _print_json(result)
        else:
            _print_plan(plan, execute=False)
    finally:
        if client:
            client.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=(
            "Unofficial ThinQ2 client for specialty (download/SmartCourse) laundry "
            "cycles and model-declared start-option fields. Not affiliated with LG. "
            "Start is a dry-run unless you pass --execute."
        ),
    )
    parser.add_argument("--version", action="version", version=f"{PROG} {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="Start LG account OAuth and print env exports")
    login.add_argument("--country", default=None, help="Country code (default THINQ_COUNTRY or US)")
    login.add_argument(
        "--language", default=None, help="Language tag (default THINQ_LANGUAGE or en-US)"
    )
    login.add_argument(
        "--callback-url",
        default=None,
        help="Full redirected URL after browser sign-in",
    )
    login.set_defaults(func=cmd_login)

    devices = sub.add_parser("devices", help="List ThinQ devices on the account")
    devices.add_argument("--all", action="store_true", help="Include non-laundry devices")
    devices.add_argument("--json", action="store_true", help="Print JSON")
    devices.set_defaults(func=cmd_devices)

    courses = sub.add_parser(
        "courses",
        help="Dump base + specialty cycles and start-option fields from model info",
    )
    courses.add_argument("--device", help="ThinQ device id")
    courses.add_argument(
        "--model-json",
        help="Path to a saved model JSON (offline; no account needed)",
    )
    courses.add_argument("--json", action="store_true", help="Print JSON")
    courses.set_defaults(func=cmd_courses)

    start = sub.add_parser(
        "start",
        help="Build a remote-start payload (dry-run by default; --execute to send)",
    )
    start.add_argument("--device", help="ThinQ device id")
    start.add_argument(
        "--course",
        required=True,
        help="Cycle id from `courses` (base or specialty)",
    )
    start.add_argument(
        "--option",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
        help="Set a start-option field present in the device model (repeatable)",
    )
    start.add_argument("--model-json", help="Path to a saved model JSON (offline dry-run)")
    start.add_argument(
        "--force",
        action="store_true",
        help="Allow option field names that are not listed in the model catalog",
    )
    start.add_argument(
        "--execute",
        action="store_true",
        help="POST the payload to ThinQ2 control-sync (otherwise dry-run only)",
    )
    start.set_defaults(func=cmd_start)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ThinQError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return 2
    except httpx.HTTPError as exc:
        print(f"{PROG}: HTTP error: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
