#!/usr/bin/env python3
"""컨텍스트 압축 전후로 작업 상태를 기록 · 대조 · 재주입한다 (`wk compact-checkpoint`).

## 왜 필요한가 (ADR-030, M-021/WBS-21.1)

하네스의 압축 요약은 "확인했다 / 아직 안 확인했다" 의 구분과 다음 한 걸음을 잃을 수 있다.
이 명령은 그것을 브랜치 메모리의 `.compact/` 에 적어 두고, 압축 뒤 요약과 대조해 빠진 식별자를
세고, 예산 안에서 다시 컨텍스트로 넣는다. 계약은 `core/compact_relay_spec.md`.

## 모드

- ``--note``        스킬이 판단 층을 쓴다 (`--next` · `--unverified` · `--verified` · `--rejected`, 반복 가능)
- ``--hook pre``    `PreCompact` — stdin JSON, 기계 층 수집 + 대기 판단 층 인수
- ``--hook post``   `PostCompact` — stdin JSON, 요약 보관 + 누락 대조
- ``--restore``     `SessionStart(compact)` — 재주입 본문을 stdout 으로
- ``--clear``       세션 종료 — checkpoint · 요약 삭제

hook 모드와 ``--restore`` 는 **항상 exit 0** 이다 — 실패는 한 줄로 말하고 세션을 막지 않는다.
``--output-format codex-json`` 은 그 출력을 Codex hook wire JSON 으로 싼다 (재주입 본문 =
``hookSpecificOutput.additionalContext``, 그 밖 = ``systemMessage``) — Codex 는 ``[`` 로 시작하는 평문을
JSON 으로 오판해 hook 을 ``failed`` 로 버린다 (TASK-2026-09-30-main-009 실측).
워크플로우 메모리가 없는 workspace 에서는 출력도 파일도 없다.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_kit.common import compact_relay as relay
from workflow_kit.common.paths import discover_project_profile_path


def _read_payload() -> tuple[dict[str, Any], str | None]:
    """hook stdin JSON. 대화형 터미널이면 빈 payload (수동 실행)."""
    if sys.stdin is None or sys.stdin.isatty():
        return {}, None
    raw = sys.stdin.read()
    if not raw.strip():
        return {}, None
    try:
        data = json.loads(raw)
    except ValueError as exc:
        return {}, f"stdin JSON 을 읽지 못했다: {exc}"
    if not isinstance(data, dict):
        return {}, "stdin JSON 이 객체가 아니다"
    return data, None


def _locate(args: argparse.Namespace, payload: dict[str, Any]) -> relay.RelayLocation | None:
    if args.project_profile_path is not None:
        return relay.locate_from_profile(args.project_profile_path)
    if payload.get("cwd"):
        return relay.locate_from_cwd(payload["cwd"])
    profile = discover_project_profile_path()
    return relay.locate_from_profile(profile) if profile is not None else None


def _parse_now(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m workflow_kit compact-checkpoint", description=__doc__.split("\n")[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--note", action="store_true", help="판단 층 기록 (스킬)")
    mode.add_argument("--hook", choices=("pre", "post"), help="PreCompact / PostCompact hook")
    mode.add_argument("--restore", action="store_true", help="재주입 본문 출력 (SessionStart compact)")
    mode.add_argument("--clear", action="store_true", help="checkpoint · 요약 삭제 (세션 종료)")
    ap.add_argument("--next", action="append", default=[], dest="next_steps", metavar="TEXT")
    ap.add_argument("--unverified", action="append", default=[], metavar="TEXT")
    ap.add_argument("--verified", action="append", default=[], metavar="TEXT")
    ap.add_argument("--rejected", action="append", default=[], metavar="TEXT")
    ap.add_argument("--project-profile-path", type=Path, default=None)
    ap.add_argument("--now", default=None, help="시각 고정 (ISO 8601 — 검사·재현용)")
    ap.add_argument("--json", action="store_true", dest="as_json", help="--note / --clear 결과를 JSON 으로")
    ap.add_argument(
        "--output-format",
        choices=relay.OUTPUT_FORMATS,
        default=relay.OUTPUT_TEXT,
        help="hook 모드 stdout 형식 — codex-json 은 Codex hook 출력 wire (스펙 §6)",
    )
    return ap


def _emit(args: argparse.Namespace, text: str, *, context: bool = False) -> None:
    """hook 모드 출력 한 곳. ``context`` 는 재주입 본문(모델에게) — 그 밖은 알림 한 줄(사람에게)."""
    if not text:
        return
    if args.output_format == relay.OUTPUT_CODEX_JSON:
        print(relay.codex_additional_context(text) if context else relay.codex_system_message(text))
    elif context:
        sys.stdout.write(text)
    else:
        print(text)


def _run_hook_mode(args: argparse.Namespace) -> int:
    payload, payload_error = _read_payload()
    now = _parse_now(args.now)
    try:
        loc = _locate(args, payload)
        if loc is None:
            return 0
        if payload_error:
            _emit(args, f"{relay.HEADER_TAG} {payload_error} — 건너뜀")
            return 0
        if args.hook == "pre":
            data = relay.hook_pre(loc, payload, now=relay.now_iso(now))
            layers = "기계 층" + (" + 판단 층" if data.get("judgment") else "")
            _emit(args, f"{relay.HEADER_TAG} 기록: {layers} → {loc.rel(loc.checkpoint_path)}")
        elif args.hook == "post":
            data = relay.hook_post(loc, payload, now=relay.now_iso(now))
            if data is not None:
                _emit(args, relay.render_post_report(data))
        else:
            text = relay.render_restore(
                loc,
                relay.load_checkpoint(loc),
                session_id=payload.get("session_id") or None,
                head=relay.current_head(loc.workspace_root),
                now=now,
            )
            _emit(args, text or "", context=True)
    except Exception as exc:  # noqa: BLE001 — hook 은 세션을 막지 않는다 (스펙 §1-4)
        _emit(args, f"{relay.HEADER_TAG} 실패 ({type(exc).__name__}: {exc}) — 세션은 계속된다")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.hook or args.restore:
        return _run_hook_mode(args)
    if args.output_format != relay.OUTPUT_TEXT:
        print("[error] --output-format 은 --hook / --restore 에서만 쓴다 (--note / --clear 는 --json).", file=sys.stderr)
        return 2
    has_items = any((args.next_steps, args.unverified, args.verified, args.rejected))
    if args.clear and has_items:
        print("[error] --clear 는 --next / --unverified / --verified / --rejected 를 받지 않는다.", file=sys.stderr)
        return 2
    if args.note and not has_items:
        print("[error] --note 에는 --next / --unverified / --verified / --rejected 중 하나 이상이 필요하다.", file=sys.stderr)
        return 2
    loc = _locate(args, {})
    if loc is None:
        print(
            "[error] 브랜치 메모리 디렉터리가 없다 — 워크플로우 프로젝트가 아니거나 이 브랜치에 아직 task 가 없다"
            " (`python -m workflow_kit backlog-update` 가 만든다).",
            file=sys.stderr,
        )
        return 1
    now = relay.now_iso(_parse_now(args.now))
    if args.note:
        data = relay.write_note(
            loc,
            next_steps=args.next_steps,
            unverified=args.unverified,
            verified=args.verified,
            rejected=args.rejected,
            now=now,
        )
        result: dict[str, Any] = {
            "status": "ok",
            "mode": "note",
            "path": loc.rel(loc.checkpoint_path),
            "counts": {k: len(data["judgment"][k]) for k in relay.JUDGMENT_KEYS},
        }
        message = f"판단 층 기록 (다음 압축의 PreCompact 가 인수): {result['path']} {result['counts']}"
    else:
        removed = relay.clear(loc)
        result = {"status": "ok", "mode": "clear", "removed": removed}
        message = f"삭제: {', '.join(removed)}" if removed else "지울 checkpoint 가 없다."
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.as_json else message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
