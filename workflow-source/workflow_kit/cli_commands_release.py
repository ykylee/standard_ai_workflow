"""workflow_kit.cli_commands_release - release pipeline dispatcher subcommands.

workflow_kit_cli.py 에서 verbatim 추출 (TASK-2026-08-11-main-011, dispatcher
부분 분할). `_wrap_release_pipeline` helper + 7개 handler: release-doctor /
release-bump / release-note / release-changelog / release-verify /
release-rollback / release-dist.

release-create / release-status 는 workflow_kit_cli.py 에 남는다 — 4개 검사
(check_release_status_v0_11_14 / _auto_bump_v0_11_16 /
check_mypy_strict_release_gate_v0_11_12 / check_mypy_ci_cross_verify_v0_11_13)
가 그 파일의 소스 본문을 regex 로 대조한다. 남은 cmd_release_create 는
`_wrap_release_pipeline` 을 workflow_kit_cli 의 명시적 from-import (재-export)
로 계속 쓴다.

`@register` 가 import 시점에 `cli_registry.COMMANDS` 에 등록하고,
workflow_kit_cli 가 본 모듈의 handler 를 재-export 한다 — arg surface 문서는
workflow_kit_cli 모듈 docstring 이 계속 정본이다.
"""

from __future__ import annotations

import json
import sys
from typing import Any, cast

from workflow_kit.cli_registry import _has_flag, _parse_flag, register

__all__ = [
    "_wrap_release_pipeline",
    "cmd_release_doctor",
    "cmd_release_bump",
    "cmd_release_note",
    "cmd_release_changelog",
    "cmd_release_verify",
    "cmd_release_rollback",
    "cmd_release_dist",
]


def _is_source_checkout_required(exc: BaseException) -> bool:
    """설치본 거부 예외인가 (`release_pipeline_lib.SourceCheckoutRequired`).

    `isinstance` 를 못 쓴다 — 본 모듈은 release_pipeline_lib 을 `importlib` 로
    **파일 경로에서** 로드하므로, 같은 소스라도 `import` 로 얻은 클래스와 다른
    객체가 된다 (module instance 가 둘). 이름으로 대조하는 것이 이 로딩 방식에서
    유일하게 성립하는 판정이다.
    """
    return type(exc).__name__ == "SourceCheckoutRequired"


@register("release-doctor")
def cmd_release_doctor(argv: list[str]) -> int:
    """Release pre-flight: 4-source release-readiness check (in-process, v0.7.55+).

    Calls `tools.release_pipeline_lib.cmd_validate` in-process (no subprocess
    overhead, no script-path coupling). 4 checks:
      1. check_packaging: pyproject [tool.setuptools.packages] ↔ disk
      2. workflow_kit.cli.doctor: 7 baseline evaluate
      3. state.json freshness
      4. git status: working tree clean

    Args:
        --skip-packaging   skip check 1
        --skip-doctor      skip check 2
        --skip-state       skip check 3
        --skip-git         skip check 4
    """
    skip = {
        "packaging": _has_flag(argv, "--skip-packaging"),
        "doctor": _has_flag(argv, "--skip-doctor"),
        "state": _has_flag(argv, "--skip-state"),
        "git": _has_flag(argv, "--skip-git"),
    }
    try:
        # Find workflow_kit/tools dir relative to this module (v1.2.0: 구경로
        # workflow-source/tools shim drop — 정위치 workflow_kit/tools 를 본다).
        from pathlib import Path as _P
        kit_dir = _P(__file__).resolve().parent
        tools_dir = kit_dir / "tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        # importlib 사용 — sys.path manipulation 후에도 mypy 가 stub 못 찾으므로
        # importlib.util.spec_from_file_location 으로 명시적 로드
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            "release_pipeline_lib", str(tools_dir / "release_pipeline_lib.py")
        )
        if _spec is None or _spec.loader is None:
            raise ImportError("failed to load release_pipeline_lib spec")
        _mod = _ilu.module_from_spec(_spec)
        sys.modules["release_pipeline_lib"] = _mod
        _spec.loader.exec_module(_mod)
        _cmd_validate = _mod.cmd_validate
        results = _cmd_validate(
            skip_packaging=skip["packaging"],
            skip_doctor=skip["doctor"],
            skip_state=skip["state"],
            skip_git=skip["git"],
        )
        print(json.dumps(results, indent=2, default=str))
        # rc: 0 = all OK, 1 = at least one source not ok
        any_fail = any(
            v.get("ok") is False for v in results.values() if isinstance(v, dict)
        )
        return 1 if any_fail else 0
    except Exception as e:
        if _is_source_checkout_required(e):
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


# ---------------------------------------------------------------------------
# release-pipeline wrappers (v0.7.56+, dispatcher subcommand 17-23)
# ---------------------------------------------------------------------------

def _wrap_release_pipeline(argv: list[str], wrapper_name: str, **kwargs: Any) -> int:
    """Helper: call a release_pipeline_lib wrapper with JSON output + rc conversion.

    Args:
        argv: dispatcher argv
        wrapper_name: name of the function in release_pipeline_lib
        **kwargs: forwarded to the wrapper

    Returns:
        rc: 0 = success, 1 = warn, 2 = error/usage
    """
    import json as _json
    use_json = _has_flag(argv, "--json")
    try:
        from pathlib import Path as _P
        kit_dir = _P(__file__).resolve().parent
        tools_dir = kit_dir / "tools"  # v1.2.0: 정위치 workflow_kit/tools
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        # importlib 사용 — sys.path manipulation 후에도 mypy 가 stub 못 찾으므로
        # importlib.util.spec_from_file_location 으로 명시적 로드 (cmd_release_doctor 와 동일 패턴)
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            "release_pipeline_lib", str(tools_dir / "release_pipeline_lib.py")
        )
        if _spec is None or _spec.loader is None:
            raise ImportError("failed to load release_pipeline_lib spec")
        _mod = _ilu.module_from_spec(_spec)
        sys.modules["release_pipeline_lib"] = _mod
        _spec.loader.exec_module(_mod)
        _lib = cast(Any, _mod)  # release_pipeline_lib module — wrapper_name attribute
        fn = getattr(_lib, wrapper_name)
        result = fn(**kwargs)
        if use_json:
            print(_json.dumps(result, indent=2, default=str))
        else:
            mode = result.get("mode", "?")
            print(f"{wrapper_name}: mode={mode}")
            for k, v in result.items():
                if k == "mode":
                    continue
                print(f"  {k}: {v}")
        # rc: success if mode=apply or dry-run OK; error if mode=error
        if result.get("mode") == "error":
            return 2
        return 0
    except Exception as e:
        # 설치본에서의 호출은 결함이 아니라 **전제 불성립**이다 (main-012). 메시지가
        # 두 경로와 대체 명령을 이미 담고 있으므로 예외 이름 접두 없이 그대로 찍는다 —
        # `ERROR: FileNotFoundError: <venv>/…/pyproject.toml` 는 처방을 엉뚱한
        # 곳으로 보냈다.
        if _is_source_checkout_required(e):
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        print(f"ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


@register("release-bump")
def cmd_release_bump(argv: list[str]) -> int:
    """Bump pyproject.toml version (v0.7.56+, dispatcher subcommand 17).

    Args:
        --to=VERSION    explicit target version (e.g. "0.7.56")
        --patch         increment patch (default if no --to)
        --minor         increment minor
        --major         increment major
        --no-init       skip workflow_kit/__init__.py __version__ sync
        --apply         actually write (default dry-run)
        --json          JSON output
    """
    to = _parse_flag(argv, "--to")
    kwargs = {
        "apply": _has_flag(argv, "--apply"),
        "no_init": _has_flag(argv, "--no-init"),
        "to": to,
        "patch": _has_flag(argv, "--patch"),
        "minor": _has_flag(argv, "--minor"),
        "major": _has_flag(argv, "--major"),
    }
    return _wrap_release_pipeline(argv, "cmd_version_bump", **kwargs)


@register("release-note")
def cmd_release_note(argv: list[str]) -> int:
    """Draft release note (v0.7.56+, dispatcher subcommand 18).

    Args:
        --to=VERSION       target version (required)
        --from-tag=TAG     source tag (required)
        --apply            actually write Beta-v<X>.md (default dry-run)
        --json             JSON output
    """
    to = _parse_flag(argv, "--to")
    from_tag = _parse_flag(argv, "--from-tag")
    if to is None or from_tag is None:
        print("ERROR: --to=VERSION and --from-tag=TAG required", file=sys.stderr)
        return 2
    return _wrap_release_pipeline(
        argv, "cmd_note_draft",
        to=to, from_tag=from_tag, dry_run=not _has_flag(argv, "--apply"),
    )


@register("release-changelog")
def cmd_release_changelog(argv: list[str]) -> int:
    """Generate CHANGELOG.md body (v0.7.56+, dispatcher subcommand 19).

    Args:
        --from-tag=TAG     start tag (default = all history)
        --to-tag=REF       end tag/REF (default = HEAD)
        --apply            actually write CHANGELOG.md (default dry-run)
        --json             JSON output
    """
    from_tag = _parse_flag(argv, "--from-tag")
    to_tag = _parse_flag(argv, "--to-tag") or "HEAD"
    return _wrap_release_pipeline(
        argv, "cmd_changelog_gen",
        from_tag=from_tag, to_tag=to_tag, dry_run=not _has_flag(argv, "--apply"),
    )


@register("release-verify")
def cmd_release_verify(argv: list[str]) -> int:
    """Verify GitHub Release (v0.7.56+, dispatcher subcommand 21, read-only).

    Args:
        --tag=TAG    tag to verify (e.g. v0.7.56 or 0.7.56, required)
        --json       JSON output
    """
    tag = _parse_flag(argv, "--tag")
    if tag is None:
        print("ERROR: --tag=TAG required", file=sys.stderr)
        return 2
    return _wrap_release_pipeline(argv, "cmd_verify", tag=tag)


@register("release-rollback")
def cmd_release_rollback(argv: list[str]) -> int:
    """Delete GitHub Release + git tag (v0.7.56+, dispatcher subcommand 22, destructive).

    Args:
        --tag=TAG     tag to delete (required)
        --apply       actually delete (default dry-run)
        --json        JSON output
    """
    tag = _parse_flag(argv, "--tag")
    if tag is None:
        print("ERROR: --tag=TAG required", file=sys.stderr)
        return 2
    return _wrap_release_pipeline(
        argv, "cmd_rollback",
        tag=tag, apply=_has_flag(argv, "--apply"),
    )


@register("release-dist")
def cmd_release_dist(argv: list[str]) -> int:
    """Build wheel + sdist (v0.7.56+, dispatcher subcommand 23).

    Args:
        --apply     actually run `python3 -m build` (default dry-run)
        --json      JSON output
    """
    return _wrap_release_pipeline(argv, "cmd_dist", apply=_has_flag(argv, "--apply"))
