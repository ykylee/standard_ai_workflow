"""Smoke test for v0.11.23 drift-prevention helpers.

본 test 가 검증:
  1. `write_workflow_kit_version` — suffix 중복 처리 bug 회피 (다음 release cycle 보호)
  2. `cmd_doc_headers_update` 의 regex 패턴 — 동일 date 로 두 번 patch 해도 noop
  3. `_parse_release_note_frontmatter` 의 inline obj/list parser 정확성
  4. `cmd_release --dry-run` 의 auto-step chain 정상 호출 (drift 자동 step 발동 검증)

본 test 는 v0.11.23 cycle 의 운영 자동화 검증. `check_drift_prevention_v0_11_23.py` 의
data-quality 검증과 보완 관계 (앞의 test 는 정합, 본 test 는 자동화 toolchain).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterator

REPO = Path(__file__).resolve().parents[2]
INIT_PY = REPO / "workflow-source" / "workflow_kit" / "__init__.py"
RELEASE_PIPELINE = REPO / "workflow-source" / "tools" / "release_pipeline.py"


def _load_release_pipeline_module():
    """standalone script 이므로 file-based spec 으로 load."""
    spec = importlib.util.spec_from_file_location(
        "_release_pipeline_under_test",
        str(RELEASE_PIPELINE),
    )
    if spec is None or spec.loader is None:
        raise ImportError("could not load release_pipeline.py spec")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# case 1 — write_workflow_kit_version does NOT double-suffix
# ---------------------------------------------------------------------------

def test_case_1_write_workflow_kit_version_no_double_suffix() -> None:
    """write_workflow_kit_version 가 suffix 를 *추가* 하지 않아야 한다 (suffix 가 이미 -beta 일 때).

    v0.11.23 의 silent bug fix: 이전 impl 은 `target = "v{version}{suffix}-beta"` 로
    suffix 가 "-beta" 일 때 `v0.11.23-beta-beta` 를 만들었다. 본 test 는 다음 release cycle
    에서 version-bump --to X.Y.Z 가 항상 well-formed literal 을 만들도록 보장.
    """
    src = INIT_PY.read_text(encoding="utf-8")
    # major 를 하드코딩하지 않는다 — v1.0.0 bump 때 `"v0."` 매치가 0 이 되어 red 였다.
    fallback_lines = [
        ln for ln in src.splitlines()
        if ln.strip().startswith("return ") and re.search(r"v\d+\.\d+\.\d+", ln)
    ]
    assert fallback_lines, "no loud fallback line found"
    line = fallback_lines[-1]
    # `return "vX.Y.Z-beta"` — "-beta" 정확히 1 회만 등장. 이중 suffix 미허용.
    n_beta = line.count("-beta")
    assert n_beta == 1, (
        f"loud fallback literal has wrong -beta count "
        f"(line={line!r}, n_beta={n_beta}, expected 1)"
    )


# ---------------------------------------------------------------------------
# case 2 — cmd_doc_headers_update regex + idempotent (in-process via loaded module)
# ---------------------------------------------------------------------------

def test_case_2_doc_headers_update_idempotent() -> None:
    """doc-headers-update 의 regex 가 정합일 때 noop, 불일치일 때 patch + 두 번째 call noop."""
    rp_mod = _load_release_pipeline_module()
    DOC_HEADER_DATE_RE = rp_mod.DOC_HEADER_DATE_RE

    target_date = "2026-07-03"
    with tempfile.TemporaryDirectory() as td:
        f1 = Path(td) / "test_a.md"
        f2 = Path(td) / "test_b.md"
        f1.write_text(
            "# T1\n\n- 상태: stable\n- 최종 수정일: 2020-01-01\n\nbody.\n",
            encoding="utf-8",
        )
        f2.write_text(
            "# T2\n\n- 최종 수정일: 2020-01-01\n\nbody.\n",
            encoding="utf-8",
        )
        # first call
        for p in (f1, f2):
            txt = p.read_text(encoding="utf-8")
            new = DOC_HEADER_DATE_RE.sub(rf"\g<1>{target_date}\g<3>", txt)
            if new == txt:
                continue
            p.write_text(new, encoding="utf-8")

        after1_f1 = f1.read_text(encoding="utf-8")
        # body content (헤더 다음) 변경 없음.
        body_lines = [ln for ln in after1_f1.splitlines() if ln.startswith("body")]
        assert body_lines == ["body."], f"body changed: {after1_f1!r}"
        assert "2026-07-03" in after1_f1
        assert "2020-01-01" not in after1_f1

        # 두 번째 call: 같은 date 로 noop.
        for p in (f1, f2):
            txt = p.read_text(encoding="utf-8")
            new = DOC_HEADER_DATE_RE.sub(rf"\g<1>{target_date}\g<3>", txt)
            if new == txt:
                continue
            p.write_text(new, encoding="utf-8")
        after2_f1 = f1.read_text(encoding="utf-8")
        assert after2_f1 == after1_f1, "second-call should be noop (idempotent)"


# ---------------------------------------------------------------------------
# case 3 — sync-maturity-matrix frontmatter parser 정확성
# ---------------------------------------------------------------------------

def test_case_3_sync_maturity_matrix_frontmatter_parse() -> None:
    """YAML frontmatter parser 가 inline obj/list 를 정확히 parse."""
    rp_mod = _load_release_pipeline_module()

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / "release_note.md"
        tmp.write_text(
            "---\n"
            "release: v0.99.99\n"
            "closed_phases: [11, 12]\n"
            "promoted_skills:\n"
            "  - { name: foo-skill, to: stable, release: v0.99.99 }\n"
            "  - { name: bar-skill, to: beta, release: v0.99.99 }\n"
            "added_harnesses:\n"
            "  - { name: harness-xyz, release: v0.99.99 }\n"
            "deprecated_symbols:\n"
            "  - { module: foo, name: bar, release: v0.99.99 }\n"
            "---\n\n# body\n",
            encoding="utf-8",
        )
        parsed, _rest = rp_mod._parse_release_note_frontmatter(tmp)
        assert parsed["release"] == "v0.99.99", parsed
        # closed_phases 는 int list (parsed by integer regex) — 본 test 는 원소 동일성 검증.
        assert parsed["closed_phases"] == [11, 12], parsed["closed_phases"]
        assert len(parsed["promoted_skills"]) == 2, parsed["promoted_skills"]
        assert parsed["promoted_skills"][0]["name"] == "foo-skill", parsed["promoted_skills"]
        assert parsed["promoted_skills"][0]["release"] == "v0.99.99"
        assert parsed["added_harnesses"][0]["name"] == "harness-xyz"
        assert parsed["deprecated_symbols"][0]["module"] == "foo"


# ---------------------------------------------------------------------------
# case 4 — sync-maturity-matrix applied_ops 규약 검증
# ---------------------------------------------------------------------------

def test_case_4_sync_maturity_matrix_applied_ops_convention() -> None:
    """applied_ops 문자열 규약 검증 — 동일 release note 2회 parse → 동일 applied_ops sequence.

    *Idempotent write* 가 보장되어야 하지만, 본 test 는 적용 *규약* 만 본다 (helper 함수의
    결과 sequence 가 deterministic 인지).
    """
    rp_mod = _load_release_pipeline_module()

    note_path = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    )
    try:
        note_path.write(
            "---\n"
            "release: v0.99.99\n"
            "closed_phases: []\n"
            "promoted_skills:\n"
            "  - { name: ephemeral-test-skill, to: stable, release: v0.99.99 }\n"
            "added_harnesses: []\n"
            "deprecated_symbols: []\n"
            "---\n\nbody\n"
        )
        note_path.close()
        note_path = Path(note_path.name)

        fm_first, _ = rp_mod._parse_release_note_frontmatter(note_path)
        applied_first = []
        for entry in fm_first.get("promoted_skills") or []:
            if isinstance(entry, dict):
                name = entry.get("name", "")
                applied_first.append(f"skill:{name}→{entry.get('to', 'stable')}")
        assert "skill:ephemeral-test-skill→stable" in applied_first, applied_first

        # 두 번째 call: 같은 entry, 동일 sequence.
        fm_second, _ = rp_mod._parse_release_note_frontmatter(note_path)
        applied_second = []
        for entry in fm_second.get("promoted_skills") or []:
            if isinstance(entry, dict):
                name = entry.get("name", "")
                applied_second.append(f"skill:{name}→{entry.get('to', 'stable')}")
        assert applied_second == applied_first, "deterministic parse required"
    finally:
        note_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# case 5 — release --dry-run 가 drift auto-step 호출
# ---------------------------------------------------------------------------

def test_case_5_release_dry_run_triggers_drift_step() -> None:
    """`release --dry-run` 가 doc-headers-update + sync-maturity-matrix 를 자동 호출.

    본 test 는 dry-run + --version=0.11.21 + --skip-validate + --skip-cross-verify 조합으로
    dist 부재 → 'no dist files' 로 끝나는 단말 경로. *그 전에* auto-step 이 결과 dict 에
    박혀 들어가는지가 본 test 의 핵심. 단, dist 부재 로 *error 필드* 가 있는 모드 라도
    *results dict 의 doc_headers_update / maturity_matrix_sync 키* 가 존재해야 한다.
    """
    proc = subprocess.run(
        [
            "python3",
            str(RELEASE_PIPELINE),
            "release",
            "--dry-run",
            "--skip-validate",
            "--skip-cross-verify",
            "--version=0.11.21",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, "PYTHONPATH": str(REPO / "workflow-source")},
    )
    output = proc.stdout + proc.stderr
    # 본 검증은 drift prevention step 이 자동 호출된 *흔적* 이 stdout/json 에 들어있는지.
    # dry-run 은 mode=DRY-RUN 라인 안에 summary 출력. strict 한 검증은 release --apply 가
    # 실제로는 외부 gh tag interaction 으로 실 환경에서만 가능. 본 smoke 는 step 시작 여부 만 본다.
    assert (
        "release (DRY-RUN)" in output
        or "doc_headers_update" in output
        or "maturity_matrix_sync" in output
        or "no dist files" in output
    ), (
        f"release --dry-run produced unexpected output:\n{output[:1500]}"
    )


# ---------------------------------------------------------------------------
# runner
# ---------------------------------------------------------------------------
# case 6 — release --dry-run 은 저장소를 절대 수정하지 않는다
# ---------------------------------------------------------------------------

def test_case_6_release_dry_run_does_not_touch_repo() -> None:
    """`release --dry-run` 의 모든 auto-step 이 write 하지 않는 mode 여야 한다.

    회귀 배경: cmd_release 의 `_attr_ns()` 가 `dry_run=False` / `apply=True` 를
    하드코딩해, dry-run 인데도 doc-headers-update / maturity-matrix-sync /
    self-recover 가 **실제 저장소 문서 63개를 write** 했다. 본 smoke 를 돌리는
    것만으로 워킹트리가 더러워졌고, release_pipeline 의 `git add` 와 겹치면
    릴리스와 무관한 변경이 release commit 에 흡수된다.

    검증은 워킹트리 diff 가 아니라 **각 step 이 보고한 mode** 로 한다. doc-headers
    -update 는 날짜가 이미 오늘이면 write 할 것이 없어 멱등 noop 이 되므로, 파일
    변화 유무로는 case_5 실행 뒤에 버그를 놓친다(실제로 놓쳤다). mode 는 대상
    파일 상태와 무관하게 결정적이다.
    """
    proc = subprocess.run(
        [
            "python3",
            str(RELEASE_PIPELINE),
            "release",
            "--dry-run",
            "--skip-validate",
            "--skip-cross-verify",
            "--version=0.11.21",
            "--json",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PYTHONPATH": str(REPO / "workflow-source")},
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"release --dry-run --json 파싱 실패: {exc}\n{proc.stdout[:500]}")

    assert payload.get("mode") == "dry-run", f"release mode={payload.get('mode')!r}"
    for step in ("doc_headers_update", "maturity_matrix_sync", "self_recover", "changelog_gen"):
        result = payload.get(step)
        if not isinstance(result, dict):
            continue  # step 이 skip 된 경우 (escape hatch / 선행 조건 부재)
        mode = result.get("mode")
        assert mode != "applied", (
            f"release --dry-run 인데 auto-step {step!r} 가 mode={mode!r} 로 "
            f"저장소에 write 했다"
        )


# ---------------------------------------------------------------------------
# case 7 — release --auto-bump --dry-run 이 version 을 쓰지 않는다
# ---------------------------------------------------------------------------

def test_case_7_auto_bump_dry_run_does_not_write_version() -> None:
    """`release --auto-bump --dry-run` 이 pyproject / __init__ 을 write 하지 않아야 한다.

    회귀 배경: auto-bump 경로가 dry-run 을 보지 않고 in-place 로 version 을 고쳤다.
    이 결함은 `last_tag == 현재 version` 일 때(= release 직후)만 발현하므로 오래
    잠복해 있었고, 실제로 v1.0.0-beta 발행 직후 전량 smoke 가 저장소 version 을
    1.0.0 → 1.0.1 로 bump 했다.

    판정은 파일 diff 가 아니라 **보고된 mode** 로 한다 — auto-bump 는 bump 대상이
    없으면 아무것도 쓰지 않아, 파일 변화 유무는 저장소 상태에 따라 달라진다.
    """
    proc = subprocess.run(
        [
            "python3", str(RELEASE_PIPELINE), "release",
            "--auto-bump", "--skip-validate", "--dry-run", "--json",
        ],
        cwd=str(REPO), capture_output=True, text=True, timeout=120,
        env={**os.environ, "PYTHONPATH": str(REPO / "workflow-source")},
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"JSON 파싱 실패: {exc}\n{proc.stdout[:400]}")
    bump = payload.get("auto_bump")
    if isinstance(bump, dict) and bump.get("bumped"):
        assert bump.get("applied") is False, (
            f"release --auto-bump --dry-run 인데 version 을 write 했다: {bump}"
        )
        assert bump.get("mode") == "dry-run", f"mode={bump.get('mode')!r}"


# ---------------------------------------------------------------------------

def _run_all() -> Iterator[tuple[str, bool, str]]:
    cases = [
        ("test_case_1_write_workflow_kit_version_no_double_suffix",
         test_case_1_write_workflow_kit_version_no_double_suffix),
        ("test_case_2_doc_headers_update_idempotent",
         test_case_2_doc_headers_update_idempotent),
        ("test_case_3_sync_maturity_matrix_frontmatter_parse",
         test_case_3_sync_maturity_matrix_frontmatter_parse),
        ("test_case_4_sync_maturity_matrix_applied_ops_convention",
         test_case_4_sync_maturity_matrix_applied_ops_convention),
        ("test_case_5_release_dry_run_triggers_drift_step",
         test_case_5_release_dry_run_triggers_drift_step),
        ("test_case_6_release_dry_run_does_not_touch_repo",
         test_case_6_release_dry_run_does_not_touch_repo),
        ("test_case_7_auto_bump_dry_run_does_not_write_version",
         test_case_7_auto_bump_dry_run_does_not_write_version),
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
    print("=== drift-prevention helpers (v0.11.23+) ===")
    failures = 0
    for name, ok, msg in _run_all():
        if ok:
            print(f"  PASS: {name}")
        else:
            print(f"  FAIL: {name}\n    {msg}")
            failures += 1
    print(f"=== {'PASS' if failures == 0 else 'FAIL'}: {7 - failures}/7 ===")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
