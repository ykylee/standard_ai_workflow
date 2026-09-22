"""tools/release_pipeline.py release --version flag smoke test (v0.7.13+).

v0.7.13 follow-up: `cmd_release --version=<X.Y.Z>` flag 추가.
backfill 시 staging 용도 (pyproject.toml 일시 patch 불필요).
3 test PASS 기준.

Test list:
1. test_version_argparse_recognized: --version=<X.Y.Z> argparse error 없음 + version_source=cli-flag
2. test_version_override_pyproject: --version=0.7.5 일 때 tag=v0.7.5 + notes_file=Beta-v0.7.5.md (staging area 가용 시)
3. test_version_default_pyproject: --version 미지정 시 version_source=pyproject.toml (default) + tag=v{HEAD} 동적
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
TOOL = SOURCE_ROOT / "workflow_kit" / "tools" / "release_pipeline.py"


# --- Test 1: --version argparse 인식 + cli-flag source ---

def test_version_argparse_recognized() -> None:
    """release --version=<X.Y.Z> 가 argparse error 없이 받아들여짐 + version_source=cli-flag."""
    proc = subprocess.run(
        [sys.executable, str(TOOL), "release", "--version=0.7.5", "--skip-validate", "--dry-run", "--json"],
        capture_output=True, text=True, timeout=30,
    )
    # argparse 가 --version 을 인식하면 stderr 에 'unrecognized arguments' 없어야 함
    assert "unrecognized arguments" not in proc.stderr, f"argparse error: {proc.stderr}"
    out = json.loads(proc.stdout)
    # version_source: cli-flag (override 적용)
    assert out["version_source"] == "cli-flag", \
        f"expected cli-flag, got {out.get('version_source')}"
    # tag 도 override 적용 (dist 부재 error 시 tag 부재 가능)
    if "tag" in out:
        assert out["tag"] == "v0.7.5", f"expected v0.7.5, got {out['tag']}"
    else:
        # dist 부재 → error 에서 version 0.7.5 가 반영
        assert "0.7.5" in out.get("error", ""), f"expected version 0.7.5 in error, got {out.get('error')}"


# --- Test 2: --version=0.7.5 의 tag / notes_file / assets 검증 ---


def test_version_override_pyproject() -> None:
    """--version=0.7.5 일 때 tag=v0.7.5 + notes_file=Beta-v0.7.5.md.

    staging area (/tmp/dist_v_0.7.5/) 가 없으면 dry-run 결과 (version_source=cli-flag) 만 검증.
    """
    import shutil

    src = Path("/tmp/dist_v_0.7.5")
    whl = src / "standard_ai_workflow-0.7.5-py3-none-any.whl"
    tar = src / "standard_ai_workflow-0.7.5.tar.gz"

    has_staging = whl.exists() and tar.exists()

    if has_staging:
        # v0.7.11 dist 보존: pre-stage 에서 보장 (있으면 backup, 없으면 staging area 에서 copy)
        v11_whl = SOURCE_ROOT / "dist" / "standard_ai_workflow-0.7.11-py3-none-any.whl"
        v11_tar = SOURCE_ROOT / "dist" / "standard_ai_workflow-0.7.11.tar.gz"
        v11_staging = Path("/tmp/dist_v0_7_11")
        backup_dir = Path("/tmp/dist_v0_7_11_version_flag_test")
        backup_dir.mkdir(parents=True, exist_ok=True)

        # pre-stage: v0.7.11 dist 보장
        if not v11_whl.exists() and (v11_staging / v11_whl.name).exists():
            shutil.copy(v11_staging / v11_whl.name, v11_whl)
        if not v11_tar.exists() and (v11_staging / v11_tar.name).exists():
            shutil.copy(v11_staging / v11_tar.name, v11_tar)

        # backup (있을 때만)
        if v11_whl.exists():
            shutil.copy(v11_whl, backup_dir / v11_whl.name)
        if v11_tar.exists():
            shutil.copy(v11_tar, backup_dir / v11_tar.name)

        # 0.7.5 staging
        shutil.copy(whl, SOURCE_ROOT / "dist" / whl.name)
        shutil.copy(tar, SOURCE_ROOT / "dist" / tar.name)

    try:
        proc = subprocess.run(
            [sys.executable, str(TOOL), "release", "--version=0.7.5", "--skip-validate", "--dry-run", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        out = json.loads(proc.stdout)
        assert out["version_source"] == "cli-flag", \
            f"expected cli-flag, got {out.get('version_source')}"
        if has_staging:
            assert out["tag"] == "v0.7.5", f"expected v0.7.5, got {out.get('tag')}"
            assert out["notes_file"].endswith("Beta-v0.7.5.md"), \
                f"unexpected notes_file: {out.get('notes_file')}"
            assert any("0.7.5" in a for a in out["assets"]), \
                f"no 0.7.5 asset: {out.get('assets')}"
        else:
            # staging 부재 → error return (no dist files). version 만 검증.
            assert "0.7.5" in out.get("error", ""), \
                f"expected 0.7.5 in error, got {out.get('error')}"
    finally:
        if has_staging:
            # staging cleanup
            for f in (whl, tar):
                (SOURCE_ROOT / "dist" / f.name).unlink(missing_ok=True)
            # v0.7.11 dist restore
            backup_dir = Path("/tmp/dist_v0_7_11_version_flag_test")
            v11_whl = SOURCE_ROOT / "dist" / "standard_ai_workflow-0.7.11-py3-none-any.whl"
            v11_tar = SOURCE_ROOT / "dist" / "standard_ai_workflow-0.7.11.tar.gz"
            if (backup_dir / "standard_ai_workflow-0.7.11-py3-none-any.whl").exists():
                shutil.copy(
                    backup_dir / "standard_ai_workflow-0.7.11-py3-none-any.whl",
                    v11_whl,
                )
            if (backup_dir / "standard_ai_workflow-0.7.11.tar.gz").exists():
                shutil.copy(
                    backup_dir / "standard_ai_workflow-0.7.11.tar.gz",
                    v11_tar,
                )


# --- Test 3: --version 미지정 시 default (pyproject.toml) ---


def test_version_default_pyproject() -> None:
    """--version 미지정 시 version_source=pyproject.toml (default).

    dist/ 에 현재 버전 산출물이 없으면 (fresh CI checkout) dry-run 은 error 를
    반환하고 `tag` 키가 없다 — test 2 와 같은 분기. 예전에는 phase3 검사가
    원본 dist/ 에 실빌드를 남겨 이 부재 경로가 CI 에서 밟힌 적이 없었다.
    """
    spec = importlib.util.spec_from_file_location("release_pipeline", str(TOOL))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    current = mod.read_version()

    proc = subprocess.run(
        [sys.executable, str(TOOL), "release", "--skip-validate", "--dry-run", "--json"],
        capture_output=True, text=True, timeout=120,
    )
    out = json.loads(proc.stdout)
    assert out["version_source"] == "pyproject.toml", \
        f"expected pyproject.toml, got {out.get('version_source')}"

    # **기대 분기를 공유 상태로 고르지 않는다** (TASK-2026-09-22-main-005).
    #
    # 예전에는 subprocess 실행 **전에** `dist/` 존재를 재서 분기를 골랐다. 그런데
    # 병렬로 도는 다른 검사(`check_release_pipeline_phase3` · `_lib` ·
    # `wrapper_args`)가 그 사이에 `dist/` 를 만들면 고른 분기가 틀어진다 — 전형적인
    # TOCTOU 다. 2026-09-22 실측: `release --dry-run` 이 9.6s 로 늘자 그 창이
    # 벌어져 CI smoke 가 2연속 red 였고, **셀은 매번 달랐다**(경합의 지문).
    # `a9c408b8`(2026-08-11)이 같은 자리에서 '우연 의존' 만 걷고 TOCTOU 는 남겼다.
    #
    # 이제 페이로드 **자신** 으로 판정한다. 두 상태 모두 정당하고, 어느 쪽이든
    # 말해야 하는 것은 같다 — **현재 버전**. 그래서 분기를 고를 필요가 없다.
    if out.get("error"):
        assert current in out["error"], \
            f"dist 부재 경로인데 error 가 현재 버전을 안 말한다: {out['error']!r}"
    elif out.get("tag") is not None:
        assert out["tag"] == f"v{current}", f"expected v{current}, got {out.get('tag')}"
    else:
        raise AssertionError(
            "dry-run 이 error 도 tag 도 내지 않았다 — 어느 경로를 탔는지 알 수 없다. "
            f"keys={sorted(out)}"
        )


# --- 메인 실행 ---


def main() -> int:
    test_funcs = [
        test_version_argparse_recognized,
        test_version_override_pyproject,
        test_version_default_pyproject,
    ]

    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)

    total = len(test_funcs)
    passed = total - len(failed)
    print(f"\n{passed}/{total} tests passed.")
    if failed:
        print(f"\n{len(failed)} tests failed:")
        for name in failed:
            print(f"  - {name}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
