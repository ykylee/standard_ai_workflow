"""mkdocs plugin 'tools.mkdocs_git_dates:GitDatesPlugin' 의 build-time 동작 검증.

v0.11.23+ 신규 (drift prevention P3). mkdocs build 가 docs/*.md 의 '- 최종 수정일' 헤더를
git log date 로 자동 patch 함을 검증.

본 test 가 검증:
  1. plugin file 존재 + mkdocs.yml 의 plugins: 섹션에 GitDatesPlugin 등록.
  2. plugin class import 가능 + on_page_markdown hook 가 git date 로 patch.
  3. mkdocs.yml 의 `exclude_docs` 가 plugin 의 의도 (docs/ 만 cover) 와 정합.
  4. CI workflow (.github/workflows/mkdocs.yml) 가 PYTHONPATH=workflow-source 로
     mkdocs build 를 호출 (plugin import 가능).

CI integration:
  - mkdocs build 자체는 GitHub Actions mkdocs.yml 에서. 본 smoke 는 plugin config 의
    *정합* 만 verify.
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from typing import Iterator

REPO = Path(__file__).resolve().parents[2]
MKDOCS_YML = REPO / "mkdocs.yml"
CI_WORKFLOW = REPO / ".github" / "workflows" / "mkdocs.yml"
PLUGIN_FILE = REPO / "workflow-source" / "tools" / "mkdocs_git_dates.py"


def _load_plugin_module():
    """standalone file-spec 으로 load."""
    spec = importlib.util.spec_from_file_location(
        "_mkdocs_git_dates_under_test",
        str(PLUGIN_FILE),
    )
    if spec is None or spec.loader is None:
        raise ImportError("could not load mkdocs_git_dates.py spec")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# case 1 — plugin file 존재 + mkdocs.yml 의 plugins: 섹션에 등록됨
# ---------------------------------------------------------------------------

def test_case_1_plugin_registered_in_mkdocs_yml() -> None:
    """mkdocs.yml 의 plugins: 섹션에 GitDatesPlugin 등록이 있어야 한다."""
    assert PLUGIN_FILE.exists(), f"plugin file not found: {PLUGIN_FILE}"
    assert MKDOCS_YML.exists(), f"mkdocs.yml not found: {MKDOCS_YML}"
    cfg = MKDOCS_YML.read_text(encoding="utf-8")
    assert "tools.mkdocs_git_dates" in cfg, (
        "mkdocs.yml 의 plugins: 섹션에 tools.mkdocs_git_dates 가 등록 안 됨. "
        "Drift prevention P3 미적용."
    )
    assert "GitDatesPlugin" in cfg, "GitDatesPlugin class reference 없음"


# ---------------------------------------------------------------------------
# case 2 — plugin class import + on_page_markdown 동작
# ---------------------------------------------------------------------------

def test_case_2_plugin_class_on_page_markdown() -> None:
    """GitDatesPlugin class 가 import 가능 + on_page_markdown 이 git date 로 patch."""
    mod = _load_plugin_module()
    plugin = mod.GitDatesPlugin()
    assert hasattr(plugin, "on_page_markdown"), "missing on_page_markdown hook"
    assert hasattr(plugin, "_git_last_modified_date"), "missing _git_last_modified_date helper"

    # 본 repo 의 임의 markdown (docs/INSTALLATION_AND_USAGE.md) 에 대해 on_page_markdown 호출.
    src_path = REPO / "docs" / "INSTALLATION_AND_USAGE.md"
    assert src_path.exists()
    expected_date = plugin._git_last_modified_date(src_path)
    assert expected_date is not None, "git date 조회 실패"
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", expected_date), f"unexpected date format: {expected_date}"

    # page mock object (mkdocs 의 page.file.abs_src_path 만 필요).
    class _MockFile:
        pass

    class _MockPage:
        pass

    mock_page = _MockPage()
    mock_page.file = _MockFile()
    mock_page.file.abs_src_path = str(src_path)

    # '2020-01-01' placeholder 가 git date 로 patch 되어야 한다.
    md = "- 최종 수정일: 2020-01-01\n\nbody\n"
    new_md = plugin.on_page_markdown(md, mock_page)
    assert "2020-01-01" not in new_md, f"placeholder not replaced: {new_md}"
    assert expected_date in new_md, f"expected date {expected_date} not in output: {new_md}"

    # Idempotency: 이미 정합이면 noop.
    md2 = f"- 최종 수정일: {expected_date}\n\nbody\n"
    new_md2 = plugin.on_page_markdown(md2, mock_page)
    assert new_md2 == md2, "second-call should be noop (idempotent)"


# ---------------------------------------------------------------------------
# case 3 — plugin 이 header 부재 시 prepend
# ---------------------------------------------------------------------------

def test_case_3_plugin_prepends_when_header_missing() -> None:
    """`- 최종 수정일:` 헤더 부재 시, plugin 이 첫 line 으로 prepend."""
    mod = _load_plugin_module()
    plugin = mod.GitDatesPlugin()

    src_path = REPO / "docs" / "INSTALLATION_AND_USAGE.md"

    class _MockFile:
        pass

    class _MockPage:
        pass

    mock_page = _MockPage()
    mock_page.file = _MockFile()
    mock_page.file.abs_src_path = str(src_path)

    md_no_header = "# Title\n\nbody without header.\n"
    new_md = plugin.on_page_markdown(md_no_header, mock_page)
    expected_date = plugin._git_last_modified_date(src_path)
    assert new_md.startswith(f"- 최종 수정일: {expected_date}"), (
        f"plugin did not prepend git date header; new_md={new_md[:200]!r}"
    )
    assert "body without header" in new_md, "body content lost"


# ---------------------------------------------------------------------------
# case 4 — CI workflow 가 PYTHONPATH=workflow-source 설정
# ---------------------------------------------------------------------------

def test_case_4_ci_workflow_sets_pythonpath() -> None:
    """`.github/workflows/mkdocs.yml` 의 Build step 이 PYTHONPATH=workflow-source 를 설정."""
    assert CI_WORKFLOW.exists()
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    # mkdocs build 라인을 찾는다.
    build_lines = [
        ln for ln in workflow.splitlines()
        if "mkdocs build" in ln
    ]
    assert build_lines, "mkdocs build step not found in CI workflow"
    # 적어도 한 줄이 PYTHONPATH=workflow-source 로 mkdocs build 를 호출.
    matches = [
        ln for ln in build_lines
        if "PYTHONPATH=workflow-source" in ln and "mkdocs build" in ln
    ]
    assert matches, (
        f"CI workflow 의 mkdocs build 호출이 PYTHONPATH=workflow-source 를 "
        f"설정하지 않음. build_lines={build_lines}"
    )


# ---------------------------------------------------------------------------
# case 5 — mkdocs.yml 의 exclude_docs 가 plugin 의 의도 (docs/ 만 cover) 와 정합
# ---------------------------------------------------------------------------

def test_case_5_mkdocs_yml_excludes_non_public_facing() -> None:
    """mkdocs.yml 의 exclude_docs 가 plugin 적용 범위 (docs/) 와 정합."""
    cfg = MKDOCS_YML.read_text(encoding="utf-8")
    # plugin 은 docs/ 하위 markdown 만 처리. exclude_docs 는 docs/ 내부의
    # non-public-facing 만 제외 (architecture/, planning/, samples/, archive/).
    expected_excludes = [
        "samples/**",
        "archive/**",
        "planning/**",
        "architecture/**",
    ]
    for excl in expected_excludes:
        assert excl in cfg, f"missing exclude_docs entry: {excl}"


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------

def _run_all() -> Iterator[tuple[str, bool, str]]:
    cases = [
        ("test_case_1_plugin_registered_in_mkdocs_yml",
         test_case_1_plugin_registered_in_mkdocs_yml),
        ("test_case_2_plugin_class_on_page_markdown",
         test_case_2_plugin_class_on_page_markdown),
        ("test_case_3_plugin_prepends_when_header_missing",
         test_case_3_plugin_prepends_when_header_missing),
        ("test_case_4_ci_workflow_sets_pythonpath",
         test_case_4_ci_workflow_sets_pythonpath),
        ("test_case_5_mkdocs_yml_excludes_non_public_facing",
         test_case_5_mkdocs_yml_excludes_non_public_facing),
    ]
    for name, fn in cases:
        try:
            fn()
            yield name, True, ""
        except AssertionError as exc:
            yield name, False, str(exc)
        except Exception as exc:  # noqa: BLE001
            yield name, False, f"{type(exc).__name__}: {exc}"


def main() -> int:
    print("=== mkdocs GitDatesPlugin (v0.11.23+ P3) ===")
    failures = 0
    for name, ok, msg in _run_all():
        if ok:
            print(f"  PASS: {name}")
        else:
            print(f"  FAIL: {name}\n    {msg}")
            failures += 1
    print(f"=== {'PASS' if failures == 0 else 'FAIL'}: {5 - failures}/5 ===")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())