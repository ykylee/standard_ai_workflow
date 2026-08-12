"""release_pipeline.py 에서 추출한 dist(build/twine) helper 모듈 (TASK-2026-08-11-main-007).

`tools/release_pipeline.py` 의 dist (Phase 3 — v0.7.11) 관련 private helper 를
verbatim 으로 옮긴 것이다. `cmd_dist` 자체는 release_pipeline.py 에 남는다.
`release_pipeline.py` 가 `from release_pipeline_dist import *` 로 전량 재-export
하므로, 기존 check / caller 는 계속 `release_pipeline` 의 attribute
(`rp._twine_check`, `rp._build_command` 등) 로 접근한다. 이 모듈은
release_pipeline 을 import 하지 않는다 (순환 금지).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# release_pipeline.py 의 REPO_ROOT 와 동일한 값 (같은 tools/ 디렉터리 기준).
# ⚠️ 이름과 달리 git 저장소 루트가 아니라 `workflow-source/` 다 (`parents[2]`).
REPO_ROOT = Path(__file__).resolve().parents[2]

__all__ = [
    "_check_build_module",
    "_build_command",
    "_expected_dist_pattern",
    "_twine_check",
    "_simulate_testpypi_upload",
    "_simulate_production_upload",
]


def _check_build_module() -> dict:
    """`build` module 가용성 체크. 없으면 pip install 안내.

    Returns:
        {"available": bool, "hint": str (if not available)}
    """
    try:
        import build  # type: ignore[import-not-found]  # noqa: F401

        return {"available": True, "version": getattr(build, "__version__", "unknown")}
    except ImportError:
        return {
            "available": False,
            "hint": "pip install build (or `python3 -m pip install --user build`)",
        }


def _build_command(out_dir: Path, *, sdist_only: bool = False, wheel_only: bool = False) -> list[str]:
    """`python3 -m build` 호출 command list. PEP 517/518 build."""
    cmd = [sys.executable, "-m", "build", "--outdir", str(out_dir)]
    if sdist_only:
        cmd.append("--sdist")
    elif wheel_only:
        cmd.append("--wheel")
    cmd.append(str(REPO_ROOT))
    return cmd


def _expected_dist_pattern(version: str) -> str:
    """version (e.g. '0.7.10' or '0.7.10-beta') → dist file prefix (PEP 440 normalize)."""
    return version.split("-")[0]


def _twine_check(dist_dir: Path, *, timeout: int = 300) -> dict[str, object]:
    """Run `twine check dist/*` for metadata validation (spec §7.1 step 2).

    Args:
        dist_dir: dist/ directory containing wheel + sdist
        timeout: subprocess timeout in seconds (default 300)

    Returns:
        dict with `ok` (bool), `returncode`, `stdout_tail`, `stderr_tail`, optional `error`.
    """
    import sys
    artifacts = sorted(str(p) for p in dist_dir.glob("*") if p.suffix in (".whl", ".tar.gz"))
    if not artifacts:
        return {"ok": False, "error": "no wheel/sdist artifacts in dist/"}
    try:
        # `python -m twine` 는 PATH 와 무관하게 현재 Python 의 twine module 사용
        # (venv / system Python / pip install 모두 동작)
        proc = subprocess.run(
            [sys.executable, "-m", "twine", "check"] + artifacts,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"twine check timeout after {timeout}s"}
    # "twine 이 설치돼 있지 않다" 와 "twine 이 metadata 를 거부했다" 는 전혀 다른
    # 사건인데 둘 다 `ok=False, error=unknown` 으로 보고돼 원인 파악이 불가능했다.
    # `build` 는 이미 `{"available": ..., "version": ...}` 로 가용성을 따로 보고하는데
    # twine 만 빠져 있던 비대칭. twine 은 `release` extra 로 선언돼 있다.
    if proc.returncode != 0 and "No module named twine" in proc.stderr:
        return {
            "ok": False,
            "available": False,
            "returncode": proc.returncode,
            "error": "twine 미설치 — `pip install -e 'workflow-source[release]'` 로 설치",
            "stdout_tail": [],
            "stderr_tail": proc.stderr.strip().splitlines()[-5:],
        }
    return {
        "ok": proc.returncode == 0,
        "available": True,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout.strip().splitlines()[-5:] if proc.stdout.strip() else [],
        "stderr_tail": proc.stderr.strip().splitlines()[-5:] if proc.stderr.strip() else [],
    }


def _simulate_testpypi_upload(
    artifacts: list[Path], version: str,
) -> dict[str, object]:
    """Simulate `twine upload --repository testpypi` (spec §7.1 step 3).

    Policy: no actual TestPyPI deployment (release channel: GitHub Releases only).
    Reports what *would* be uploaded + command for manual execution.

    Returns:
        dict with `command`, `artifacts`, `note` (no-actual-upload policy).
    """
    artifact_names = [p.name for p in artifacts]
    cmd = ["twine", "upload", "--repository", "testpypi", "--skip-existing"] + artifact_names
    return {
        "command": " ".join(cmd),
        "artifacts": artifact_names,
        "version": version,
        "would_upload_to": "https://test.pypi.org/project/standard-ai-workflow/",
        "actual_upload": False,
        "note": (
            "Per release channel policy (memory #5: GitHub Releases only), "
            "no actual TestPyPI upload performed. Use the command above manually "
            "if TestPyPI validation is needed."
        ),
    }


def _simulate_production_upload(
    artifacts: list[Path], version: str,
) -> dict[str, object]:
    """Simulate `twine upload` to production PyPI (spec §7.1 step 5).

    Policy: no actual PyPI deployment (release channel: GitHub Releases only).
    Reports what *would* be uploaded + command for manual execution.

    Returns:
        dict with `command`, `artifacts`, `note` (no-actual-upload policy).
    """
    artifact_names = [p.name for p in artifacts]
    cmd = ["twine", "upload"] + artifact_names
    return {
        "command": " ".join(cmd),
        "artifacts": artifact_names,
        "version": version,
        "would_upload_to": "https://pypi.org/project/standard-ai-workflow/",
        "actual_upload": False,
        "note": (
            "Per release channel policy (memory #5: GitHub Releases only), "
            "no actual PyPI upload performed. Use the command above manually "
            "if PyPI production upload is needed."
        ),
    }
