"""workflow_kit.workflow_kit_cli - unified CLI dispatcher (consolidated v0.7.52,
extended v0.7.53 with okf-export / okf-import, v0.7.54 with okf-validate /
cache-migrate / release-doctor, v0.7.55 with okf-version-check / cache-decay /
score-wiki-trend, v0.7.56 with okf-cleanup / cache-prune + score-wiki-trend
in-process, v0.7.57 with cache-merge-multi / cache-import-csv / cache-export-json,
v0.9.6 with refresh-purpose, v0.13.0-dev with dashboard, v0.13.1 with memory-index-telemetry).

Replaces 6 per-feature CLI modules (cache_dashboard_cli, v_r13_layer2_cli,
cache_analytics_trend_chart_cli, cache_dashboard_export_cli,
phishing_federation_v5_cli, cache_analytics_alerting_cli).

Usage:
    wk <name> [args...]                                       # v1.1.2+ (CLI 化 B안)
    python -m workflow_kit.workflow_kit_cli --command=<name> [args...]

두 형식은 같은 `COMMANDS` 를 본다. `--command=` 는 v0.7.52 부터의 약속이라 그대로
두고, `wk <name>` positional 을 v1.1.2 에서 얹었다. `wk` 는 위 subcommand 에 더해
`tools/*.py` 29개를 같은 이름 공간에서 부른다 (`wk survey-remote-workspaces --json`
= `workflow-survey-remote-workspaces --json`). 목록은 `wk --list-commands`.

Commands:
    cache-dashboard    [--cache-path=PATH]
    dashboard-export   --output=PATH [--format=json|markdown|html] [--cache-path=PATH]
    trend-chart        --snapshots=PATH [--metric=total_size|total_hits|total_misses]
    alert              [--max-size=N] [--min-hit-rate=0.5] [--max-evictions=N] [--cache-path=PATH]
    layer2             --layer2 URL [--user=USER --token=TOKEN]
    federate           [--phishtank-key=KEY] [--min-confidence=0.0]
    okf-export         --wiki=PATH --out=PATH [--include=SUBSTR]... [--exclude=SUBSTR]...
                       [--json] [--repo-root=PATH] [--no-resolve]
                       [--vcs-commit=SHA] [--vcs-ref=REF]
    okf-import         --bundle=PATH [--staging=PATH] [--mode=strict|loose|auto]
                       [--promote] [--json]
    okf-validate       --bundle=PATH [--mode=strict|loose] [--json]
    okf-version-check  --okf-version=X.Y  OR  --bundle=PATH [--json]
    okf-cleanup        [--staging=PATH] [--older-than=SECONDS] [--apply] [--json]
    cache-migrate      [--cache-path=PATH] [--mode=migrate|split|both]
                       [--lfu-threshold=N] [--json]
    cache-merge-multi  [--cache-path=PATH] [--delete-sources] [--json]
    cache-import-csv   --csv=PATH [--cache-path=PATH] [--replace] [--json]
    cache-export-json  --output=PATH [--cache-path=PATH] [--compact] [--json]
    cache-decay        --scores=PATH [--saved-at=ISO8601] [--output=PATH]
                       [--half-life=N] [--inplace] [--json]
    cache-prune        [--cache-path=PATH] [--older-than=SECONDS]
                       [--min-access-count=N] [--apply] [--json]
    release-doctor     [--skip-packaging] [--skip-doctor] [--skip-state] [--skip-git]
    release-bump       [--to=VERSION | --patch | --minor | --major]
                       [--no-init] [--apply] [--json]
    release-note       --to=VERSION --from-tag=TAG [--apply] [--json]
    release-changelog  [--from-tag=TAG] [--to-tag=REF] [--apply] [--json]
    release-create     --version=VERSION [--notes-template=PATH] [--skip-validate]
                       [--auto-bump] [--apply] [--json]
    release-verify     --tag=TAG [--json]
    release-rollback   --tag=TAG [--apply] [--json]
    release-dist       [--apply] [--json]
    score-wiki-trend   [--record-current | --record-range=N | --show | --json]
    refresh-purpose    [--apply] [--window-days=N] [--wiki-log-path=PATH]
                       [--purpose-path=PATH] [--json]
    cascade-delete     --deleted-paths=PATH [--deleted-paths=PATH] ...
                       --wiki-root=PATH [--project=SLUG] [--apply] [--json]
    dashboard          [--format=json|markdown|html] [--output=PATH] [--publish]
                       [--workspace-root=PATH] [--recent-limit=N] [--top-n=N]
                       [--inline-guard=true|false]

Exit codes: 0 = success (or no alerts), 1 = alerts triggered / operation result, 2 = usage error.

Note: okf-* / cache-* use their own argparse or function-call API internally.
The dispatcher forwards argv verbatim after stripping --command. Their full
arg surface is documented in each module's main() docstring (and via --help).
release-doctor and score-wiki-trend (v0.7.56+) call tools/* scripts via
in-process import (no subprocess overhead).
"""

from __future__ import annotations

import json
import sys
from typing import cast

from workflow_kit.cli_registry import (
    COMMANDS,
    _has_flag,
    _parse_flag,
    _print_usage,
    register,
)

# v1.1.7 부분 분할 (TASK-2026-08-11-main-011): 아래 from-import 는 재-export 이자
# *등록 side effect* 다 — 각 cli_commands_* 모듈의 `@register` 가 import 시점에
# `cli_registry.COMMANDS` 에 싣는다. 파일 하단의 `_register_tool_commands()` 호출
# (ALREADY_REGISTERED 보호) 보다 반드시 먼저 와야 한다.
from workflow_kit.cli_commands_cache import (
    cmd_alert,
    cmd_cache_dashboard,
    cmd_cache_decay,
    cmd_cache_export_json,
    cmd_cache_import_csv,
    cmd_cache_lfu_decay_persist,
    cmd_cache_lru_decay,
    cmd_cache_merge_csv,
    cmd_cache_merge_multi,
    cmd_cache_migrate,
    cmd_cache_prune,
    cmd_dashboard_export,
    cmd_trend_chart,
)
from workflow_kit.cli_commands_doctor import (
    cmd_doctor,
)
from workflow_kit.cli_commands_memory import (
    cmd_cascade_delete,
    cmd_graph_insights,
    cmd_ingest_purpose,
    cmd_memory_index_query,
    cmd_memory_index_telemetry,
    cmd_refresh_purpose,
)
from workflow_kit.cli_commands_okf import (
    cmd_okf_cleanup,
    cmd_okf_export,
    cmd_okf_import,
    cmd_okf_validate,
    cmd_okf_version_check,
)
from workflow_kit.cli_commands_release import (
    _wrap_release_pipeline,
    cmd_release_bump,
    cmd_release_changelog,
    cmd_release_dist,
    cmd_release_doctor,
    cmd_release_note,
    cmd_release_rollback,
    cmd_release_verify,
)

__all__ = [
    # registry (cli_registry 재-export)
    "COMMANDS",
    "register",
    "_print_usage",
    "_parse_flag",
    "_has_flag",
    # cli_commands_cache 재-export
    "cmd_cache_dashboard",
    "cmd_dashboard_export",
    "cmd_trend_chart",
    "cmd_alert",
    "cmd_cache_decay",
    "cmd_cache_migrate",
    "cmd_cache_prune",
    "cmd_cache_merge_multi",
    "cmd_cache_import_csv",
    "cmd_cache_export_json",
    "cmd_cache_lfu_decay_persist",
    "cmd_cache_lru_decay",
    "cmd_cache_merge_csv",
    # cli_commands_doctor 재-export
    "cmd_doctor",
    # cli_commands_memory 재-export
    "cmd_refresh_purpose",
    "cmd_ingest_purpose",
    "cmd_graph_insights",
    "cmd_cascade_delete",
    "cmd_memory_index_query",
    "cmd_memory_index_telemetry",
    # cli_commands_okf 재-export
    "cmd_okf_export",
    "cmd_okf_import",
    "cmd_okf_version_check",
    "cmd_okf_validate",
    "cmd_okf_cleanup",
    # cli_commands_release 재-export
    "_wrap_release_pipeline",
    "cmd_release_doctor",
    "cmd_release_bump",
    "cmd_release_note",
    "cmd_release_changelog",
    "cmd_release_verify",
    "cmd_release_rollback",
    "cmd_release_dist",
    # 본 모듈 정의
    "cmd_layer2",
    "cmd_federate",
    "cmd_score_wiki_trend",
    "cmd_dashboard",
    "cmd_release_create",
    "cmd_consumer_metrics",
    "cmd_release_status",
    "run_workflow_kit_cli",
    "wk_main",
]

@register("layer2")
def cmd_layer2(argv: list[str]) -> int:
    # Find URL (first non-flag arg)
    url = None
    for arg in argv:
        if not arg.startswith("--") and arg:
            url = arg
            break
    if url is None:
        print("ERROR: URL required", file=sys.stderr)
        return 2
    user = _parse_flag(argv, "--user")
    token = _parse_flag(argv, "--token")
    try:
        from workflow_kit.v_r13_commit_diff import run_layer2_pipeline
        result = run_layer2_pipeline(url, user=user, token=token)
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("federate")
def cmd_federate(argv: list[str]) -> int:
    phishtank_key = _parse_flag(argv, "--phishtank-key")
    min_conf_s = _parse_flag(argv, "--min-confidence")
    min_confidence = float(min_conf_s) if min_conf_s else 0.0
    try:
        from workflow_kit.phishing_federation import (
            fetch_federated_phishing_urls,
            build_default_sources,
        )
        sources = build_default_sources(phishtank_api_key=phishtank_key)
        result = fetch_federated_phishing_urls(sources, min_confidence=min_confidence)
        output = [
            {"url": u, "confidence": c, "sources": s}
            for u, c, s in result
        ]
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("score-wiki-trend")
def cmd_score_wiki_trend(argv: list[str]) -> int:
    """Wiki maintainability score trend (v0.7.1+).

    In-process wrapper (v0.7.56+, previously subprocess) for
    `workflow_kit/tools/score_wiki_trend.py`. v1.2.0 (2nd cycle): 구경로
    `tools.score_wiki_trend` shim drop — 정위치 `workflow_kit.tools` 를 직접
    import 한다 (sys.path 조작 불필요).

    Args (forwarded verbatim):
        --record-current   record current HEAD score
        --record-range=N   backfill N recent commits
        --show             ASCII chart of trend
        --json             JSON output
        --alert --baseline=X  baseline 비교 (dim alert)
    """
    try:
        import importlib as _il
        mod = _il.import_module("workflow_kit.tools.score_wiki_trend")
        # main() uses argparse.parse_args() (reads sys.argv[1:]). Patch sys.argv
        # in-place to forward our argv. Restore on exit (incl. exceptions).
        old_argv = sys.argv
        try:
            sys.argv = ["score_wiki_trend", *argv]
            return cast(int, mod.main())
        finally:
            sys.argv = old_argv
    except SystemExit as e:
        # argparse / main() may call sys.exit — convert to rc
        return e.code if isinstance(e.code, int) else 2
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("dashboard")
def cmd_dashboard(argv: list[str]) -> int:
    """Quality Dashboard 5-panel snapshot (Phase 13 v0.13.0+, dispatcher subcommand 38).

    Read-only diagnostic. 5 panels:
      1. drift_prevention: maturity_matrix.json freshness + harness count + smoke count
      2. maturity_distribution: skill / mcp / transport / harness / milestone stage 분포
      3. memory_index_utilization: entries 갯수 + cue_anchor frequency + cumulative timeline
      4. smoke_trend: 누적 smoke count + 최근 release 의 smoke fail 갯수
      5. recent_releases: state.json.session.recent_done_items timeline

    Args:
        --format=json|markdown|html  출력 포맷 (default: json). v0.13.2+ html 추가.
        --output=PATH            출력 파일 (생략 시 stdout)
        --workspace-root=PATH    workspace root (생략 시 CWD 에서 REPO_ROOT 자동 탐색)
        --recent-limit=N         smoke_trend panel 의 release note 갯수 (default: 5)
        --top-n=N                recent_releases panel 의 timeline 갯수 (default: 10)
        --publish                (v0.13.2+ html 전용) output 외 추가 로 docs/dashboard/index.html copy.
                                  GitHub Pages workflow 와 정합.
        --inline-guard=false     (v0.13.1+) drift guard inline 실행 skip. true (default) 면 inline 결과 emit.
    """
    fmt = _parse_flag(argv, "--format") or "json"
    if fmt not in ("json", "markdown", "html"):
        print(
            f"ERROR: invalid --format '{fmt}' (expected: json|markdown|html)",
            file=sys.stderr,
        )
        return 2
    output = _parse_flag(argv, "--output")
    workspace_root_s = _parse_flag(argv, "--workspace-root")
    recent_limit_s = _parse_flag(argv, "--recent-limit") or "5"
    top_n_s = _parse_flag(argv, "--top-n") or "10"
    publish = _has_flag(argv, "--publish")
    inline_guard_s = _parse_flag(argv, "--inline-guard") or "true"
    inline_guard = inline_guard_s.lower() not in ("0", "false", "no", "off")
    try:
        recent_limit = int(recent_limit_s)
        top_n = int(top_n_s)
    except ValueError as e:
        print(f"ERROR: --recent-limit / --top-n 정수 parse 실패: {e}", file=sys.stderr)
        return 2

    try:
        from pathlib import Path as _P
        from workflow_kit.common.dashboard_data import (
            collect_dashboard_snapshot,
            render_dashboard_markdown,
            render_dashboard_html,
        )
        ws_root = _P(workspace_root_s) if workspace_root_s else None
        snap = collect_dashboard_snapshot(ws_root, inline_guard=inline_guard)
        if fmt == "json":
            payload = json.dumps(snap, ensure_ascii=False, indent=2, sort_keys=True)
        elif fmt == "markdown":
            payload = render_dashboard_markdown(snap)
        else:
            payload = render_dashboard_html(snap)

        if output:
            out_path = _P(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="" if payload.endswith("\n") else "\n")

        # --publish: docs/dashboard/index.html 로 추가 copy (html format 전용 권장).
        if publish:
            from pathlib import Path as _Pp
            publish_path = _Pp("docs/dashboard/index.html")
            publish_path.parent.mkdir(parents=True, exist_ok=True)
            publish_path.write_text(payload, encoding="utf-8")
            print(f"  [publish] {publish_path}", file=sys.stderr)

        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("release-create")
def cmd_release_create(argv: list[str]) -> int:
    """Create GitHub Release (v0.7.56+, dispatcher subcommand 20, destructive).

    Args:
        --version=VERSION        target version (required)
        --notes-template=PATH    notes template file (optional)
        --skip-validate          skip 4-source validate (not recommended)
        --skip-mypy              skip mypy strict pre-check (v0.11.12+, not recommended)
        --skip-cross-verify      skip mypy CI cross-verify (v0.11.13+, advisory 만 default)
        --strict-cross-verify    mypy CI cross-verify 시 drift / ci_stale / ci_fail hard fail (v0.11.13+)
        --auto-bump              auto-bump if remote tag exists
        --full-auto              pre-check conflict 시 --auto-bump / --allow-existing-tag 자동 활성화
        --apply                  actually create release (default dry-run)
        --json                   JSON output
    """
    version = _parse_flag(argv, "--version")
    if version is None:
        print("ERROR: --version=VERSION required", file=sys.stderr)
        return 2
    return _wrap_release_pipeline(
        argv, "cmd_release",
        version=version,
        notes_template=_parse_flag(argv, "--notes-template"),
        skip_validate=_has_flag(argv, "--skip-validate"),
        skip_mypy=_has_flag(argv, "--skip-mypy"),
        skip_cross_verify=_has_flag(argv, "--skip-cross-verify"),
        strict_cross_verify=_has_flag(argv, "--strict-cross-verify"),
        auto_bump=_has_flag(argv, "--auto-bump"),
        full_auto=_has_flag(argv, "--full-auto"),
        allow_existing_tag=_has_flag(argv, "--allow-existing-tag"),
        apply=_has_flag(argv, "--apply"),
    )


# ---------------------------------------------------------------------------
# consumer feedback metrics (v0.7.58+, dispatcher subcommand 27)
# ---------------------------------------------------------------------------


@register("consumer-metrics")
def cmd_consumer_metrics(argv: list[str]) -> int:
    """Consumer feedback metrics snapshot (v0.7.58+, subcommand 27).

    In-process wrapper (v0.7.59+, previously subprocess) for
    `workflow_kit/tools/consumer_metrics.py`. v1.2.0 (2nd cycle): 구경로
    `tools.consumer_metrics` shim drop — 정위치 `workflow_kit.tools` 직접 import.

    Args (forwarded verbatim, consumer_metrics.main() argparse 가 처리):
        --repo=OWNER/REPO     target repo (default: ykylee/standard_ai_workflow)
        --days=N              lookback window (1-90, default 14)
        --json                JSON output

    Exit code: 0 = success, 1 = gh CLI not authenticated, 2 = usage error.
    """
    try:
        import importlib as _il
        mod = _il.import_module("workflow_kit.tools.consumer_metrics")
        # main() uses argparse.parse_args() (reads sys.argv[1:]). Patch sys.argv
        # in-place to forward our argv. Restore on exit (incl. exceptions).
        old_argv = sys.argv
        try:
            sys.argv = ["consumer_metrics", *argv]
            return cast(int, mod.main())
        finally:
            sys.argv = old_argv
    except SystemExit as e:
        # argparse / main() may call sys.exit — convert to rc
        return e.code if isinstance(e.code, int) else 2
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("release-status")
def cmd_release_status(argv: list[str]) -> int:
    """Release pipeline status aggregator (v0.11.14+, read-only, subcommand 35).

    v0.11.16+: --auto-bump flag 추가. current_version == last_release_tag 분기에서
    자동으로 next_version (patch) bump + post-step sync_release_hash.py 자동 호출.
    write 발생 (read-only 깨짐). 명시적 opt-in.

    Aggregates:
    - current pyproject version
    - last release tag (git describe)
    - unreleased commits (count + list)
    - CI mypy cross-verify verdict (v0.11.13+ Layer 1)
    - local mypy strict status (v0.11.12+ Layer 2)
    - next version (auto-bump hint)
    - ready_to_release verdict (all checks pass)
    - auto_bump_applied + auto_bump_result (v0.11.16+, --auto-bump 시)

    Args:
        --json          JSON output
        --auto-bump     v0.11.16+: current_version == last_release_tag 일 때
                        자동으로 next_version (patch) 적용. in-process
                        cmd_version_bump --patch --apply 호출 +
                        sync_release_hash.py post-step 자동 호출.
    """
    import json as _json
    use_json = _has_flag(argv, "--json")
    auto_bump = _has_flag(argv, "--auto-bump")
    try:
        # lazy import (release_status 는 v0.11.14 신규)
        from workflow_kit.release_status import cmd_release_status as _impl
        import argparse
        args = argparse.Namespace(auto_bump=auto_bump)
        result = _impl(args)
        if use_json:
            print(_json.dumps(result, indent=2, ensure_ascii=False, default=str))
        else:
            # v0.11.15+ 1-line summary 가독성
            print(f"summary: {result.get('summary')}")
            print(f"current_version: {result.get('current_version')}")
            print(f"last_release_tag: {result.get('last_release_tag')}")
            print(f"unreleased_commits: {result.get('unreleased_commits', {}).get('count', 0)}")
            print(f"ci_mypy.verdict: {result.get('ci_mypy', {}).get('verdict')}")
            print(f"ci_mypy.head_sha_match: {result.get('ci_mypy', {}).get('head_sha_match')}")
            print(f"local_mypy.ok: {result.get('local_mypy', {}).get('ok')}")
            print(f"local_mypy.error_count: {result.get('local_mypy', {}).get('error_count')}")
            print(f"next_version: {result.get('next_version', {}).get('next')}")
            print(f"ready_to_release: {result.get('ready_to_release')}")
            print(f"ready_reason: {result.get('ready_reason')}")
            # v0.11.16+ auto-bump 결과 출력
            print(f"auto_bump_applied: {result.get('auto_bump_applied')}")
            ab_result = result.get('auto_bump_result')
            if ab_result is not None:
                if ab_result.get('ok'):
                    print(f"auto_bump.new_version: {ab_result.get('new_version')}")
                else:
                    print(f"auto_bump.error: {ab_result.get('error')}")
        return 0
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


def _register_tool_commands() -> None:
    """`tools/*.py` 29개를 `COMMANDS` 에 lazy 등록한다 (CLI 化 B안, v1.1.2+).

    새 dispatcher 를 만들지 않고 기존 registry 에 얹는다 — 진입점이 둘로 갈리면
    `--help` 도 둘로 갈리고, 어느 쪽이 정본인지가 곧 흐려진다. 이미 손으로 쓴
    wrapper 가 있는 이름(`score-wiki-trend` / `consumer-metrics`)은 덮지 않는다:
    그쪽 docstring 에 arg surface 가 적혀 있고 호출 경로도 v0.7.56 부터의 약속이다.
    """
    from workflow_kit.common.tool_dispatch import (
        ALREADY_REGISTERED,
        make_tool_runner,
        tool_command_names,
    )

    for name in tool_command_names():
        if name in ALREADY_REGISTERED or name in COMMANDS:
            continue
        COMMANDS[name] = make_tool_runner(name)


_register_tool_commands()


def run_workflow_kit_cli(argv: list[str]) -> int:
    """Run workflow_kit_cli from argv (v0.7.52+, positional 형식 v1.1.2+).

    받는 형식 두 가지 — 둘 다 같은 `COMMANDS` 를 본다:
        ``--command=<name> [args...]``  (v0.7.52+, 기존 호출 경로 전부 보존)
        ``<name> [args...]``            (v1.1.2+, `wk` 가 쓰는 형식)

    `--list-commands` 는 이름만 줄바꿈으로 흘린다 — shell completion 이 이걸 먹는다.
    """
    if not argv:
        _print_usage()
        return 2

    if argv[0] in ("--list-commands", "-l"):
        for name in sorted(COMMANDS):
            print(name)
        return 0

    if argv[0] in ("--help", "-h"):
        _print_usage()
        return 0

    has_command_flag = any(
        a == "--command" or a.startswith("--command=") for a in argv
    )

    if has_command_flag:
        cmd_name = None
        rest: list[str] = []
        for arg in argv:
            if arg == "--command" or arg.startswith("--command="):
                if "=" in arg:
                    cmd_name = arg.split("=", 1)[1]
            else:
                rest.append(arg)
    else:
        # positional 형식. 첫 인자가 flag 면 command 가 아니라 오타다 — usage 로 돌린다.
        if argv[0].startswith("-"):
            _print_usage()
            return 2
        cmd_name = argv[0]
        rest = argv[1:]

    if cmd_name is None:
        _print_usage()
        return 2
    if cmd_name not in COMMANDS:
        print(f"ERROR: unknown command: {cmd_name}", file=sys.stderr)
        _print_usage()
        return 2
    return COMMANDS[cmd_name](rest)


def wk_main() -> int:
    """`wk` console_script 진입점 (v1.1.2+, CLI 化 B안)."""
    return run_workflow_kit_cli(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(run_workflow_kit_cli(sys.argv[1:]))
