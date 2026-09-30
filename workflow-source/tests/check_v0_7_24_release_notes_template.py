#!/usr/bin/env python3
"""v0.7.24+: cmd_release --notes-template flag smoke test.

`Beta-v<X>.<Y>.<Z>.md` 의 default 외에, simple (1-line summary) / changelog
(Keep-a-Changelog 1.1.0) / custom:<path> 4가지 template 지원. GH release notes
format 자유도.

Test 구성 (5 test):
1. test_notes_template_default_argparse: --notes-template=default argparse error 부재
2. test_notes_template_simple: simple template 의 1-line summary 자동 generate
3. test_notes_template_changelog: changelog template 가 CHANGELOG.md 가리킴
4. test_notes_template_custom: custom:<path> 의 임의 path 지원
5. test_notes_template_unknown: unknown value 시 명확한 error message

Reference:
- workflow-source/workflow_kit/tools/release_pipeline.py (v0.7.24 본 release, --notes-template + _resolve_notes_file)
- v0.7.14 release note (changelog-gen subcommand, 본 release 의 'changelog' template 의 1차 출처)
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py"


def _import_tool():
    spec = importlib.util.spec_from_file_location("release_pipeline", str(TOOL))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["release_pipeline"] = mod
    spec.loader.exec_module(mod)
    return mod


# --- Test 1: --notes-template argparse error 부재 ---


def test_notes_template_default_argparse() -> None:
    """release --notes-template=default 가 argparse error 없이 받아들여짐."""
    import subprocess
    proc = subprocess.run(
        [sys.executable, str(TOOL), "release", "--notes-template=default", "--skip-validate", "--dry-run", "--json"],
        capture_output=True, text=True, timeout=30,
    )
    assert "unrecognized arguments" not in proc.stderr, f"argparse error: {proc.stderr}"
    # output 이 valid JSON (dist 부재 error 가능)
    import json
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return  # graceful
    assert "error" in out or "notes_template" in out or "version_source" in out


# --- Test 2: simple template 자동 generate ---


def _repo_releases_snapshot(mod) -> set[str]:
    """저장소 releases/ 의 파일 이름 집합 — 검사가 저장소를 건드리지 않았는지 재는 기준."""
    # `_resolve_notes_file` 은 release_pipeline_changelog 에 정의돼 있어 그 모듈의
    # RELEASES_DIR 을 본다 (release_pipeline 은 `import *` 로 재-export 만 한다).
    releases = sys.modules["release_pipeline_changelog"].RELEASES_DIR
    assert releases == mod.RELEASES_DIR, f"두 RELEASES_DIR 이 갈라졌다: {releases} != {mod.RELEASES_DIR}"
    return {p.name for p in releases.iterdir()} if releases.is_dir() else set()


def test_notes_template_simple() -> None:
    """simple template 가 default notes 의 1st paragraph 자동 generate.

    simple 은 파일을 **쓴다**. 예전에는 저장소 `workflow-source/releases/` 에
    `Beta-v9.9.9-test*.md` 를 썼다 지워, 게이트의 저장소 접촉 탐지기가 간헐로 잡았다
    (2026-09-30). 지금은 임시 디렉터리를 `releases_dir` 로 주입하고, 저장소 releases/
    가 전후로 같은지 단언한다 — 주입이 무시되면 simple 파일이 임시 디렉터리에 생기지
    않아 실패하고, 저장소에 쓰면 스냅샷 비교가 실패한다.
    """
    import tempfile

    mod = _import_tool()
    before = _repo_releases_snapshot(mod)
    test_version = "9.9.9-test"
    with tempfile.TemporaryDirectory(prefix="notes-template-") as td:
        releases = Path(td) / "releases"
        releases.mkdir()
        (releases / f"Beta-v{test_version}.md").write_text(
            "# Beta v9.9.9-test — Test Release\n\n"
            "## 핵심 추가\n\n"
            "이것은 본 release 의 *1st paragraph* 입니다.\n\n"
            "## 다음 섹션\n\n"
            "이건 안 포함.\n",
            encoding="utf-8",
        )
        result = mod._resolve_notes_file(test_version, "simple", releases_dir=releases)
        assert result.get("error") is None, result
        assert result["source"] == "simple"
        notes_file = result["notes_file"]
        assert notes_file == releases / f"Beta-v{test_version}-simple.md", (
            f"releases_dir 주입이 무시됐다: {notes_file}"
        )
        assert notes_file.is_file(), f"simple notes 가 생성되지 않았다: {notes_file}"
        content = notes_file.read_text(encoding="utf-8")
        # 1st # 헤더 + 1st ## 헤더 + 1st paragraph 본문 포함
        assert "Beta v9.9.9-test" in content
        assert "핵심 추가" in content
        assert "1st paragraph" in content
        # 2nd ## 헤더 ("다음 섹션") 와 그 paragraph 는 포함 안 됨
        assert "다음 섹션" not in content
        assert "이건 안 포함" not in content

    after = _repo_releases_snapshot(mod)
    assert after == before, f"검사가 저장소 releases/ 를 건드렸다: +{sorted(after - before)} -{sorted(before - after)}"


# --- Test 3: changelog template ---


def test_notes_template_changelog() -> None:
    """changelog template 가 workflow-source/CHANGELOG.md 가리킴."""
    mod = _import_tool()
    result = mod._resolve_notes_file("0.7.24", "changelog")
    assert result.get("error") is None
    assert result["source"] == "changelog"
    notes_file = result["notes_file"]
    assert notes_file.name == "CHANGELOG.md"
    assert "workflow-source" in str(notes_file)


# --- Test 4: custom:<path> ---


def test_notes_template_custom() -> None:
    """custom:<path> 의 임의 path 지원 (in-repo + absolute)."""
    mod = _import_tool()
    # in-repo custom path
    custom_rel = "workflow-source/releases/Beta-v0.7.24.md"
    result = mod._resolve_notes_file("0.7.24", f"custom:{custom_rel}")
    assert result.get("error") is None
    assert result["source"] == f"custom:{custom_rel}"
    notes_file = result["notes_file"]
    assert notes_file.name == "Beta-v0.7.24.md"
    assert notes_file.is_absolute(), (
        f"custom path 가 absolute 가 아님: {notes_file}"
    )

    # absolute path
    abs_path = "/tmp/test-notes.md"
    result_abs = mod._resolve_notes_file("0.7.24", f"custom:{abs_path}")
    assert result_abs.get("error") is None
    assert str(result_abs["notes_file"]) == abs_path


# --- Test 5: unknown template ---


def test_notes_template_unknown() -> None:
    """unknown --notes-template value 시 명확한 error message."""
    mod = _import_tool()
    result = mod._resolve_notes_file("0.7.24", "invalid-template-name")
    assert result.get("error") is not None
    assert "unknown" in result["error"]
    assert "--notes-template" in result["error"]
    # 사용 가능한 option 들이 error message 에 명시
    for opt in ("default", "detailed", "simple", "changelog", "custom"):
        assert opt in result["error"], f"{opt} not in error message: {result['error']}"


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_notes_template_default_argparse,
        test_notes_template_simple,
        test_notes_template_changelog,
        test_notes_template_custom,
        test_notes_template_unknown,
    ]
    passed = 0
    failed = 0
    for func in test_funcs:
        try:
            func()
            print(f"  PASS  {func.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {func.__name__}: {e}")
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {func.__name__}: {type(e).__name__}: {e}")
            failed += 1

    print()
    print(f"{passed} pass, {failed} fail")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
