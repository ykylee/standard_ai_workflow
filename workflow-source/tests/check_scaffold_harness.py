#!/usr/bin/env python3
"""Smoke test the harness scaffold helper."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
SCAFFOLD_SCRIPT = SOURCE_ROOT / "scripts" / "scaffold_harness.py"

# v1.0.0: repo 복사에서 제외할 무거운 트리.
#
# 이전 impl 은 `cp -R <REPO_ROOT>` 로 저장소를 통째로 (327MB, 그중 `.venv` 258MB)
# staging 했다. 복사가 runner 의 per-check timeout (run_all_checks.py 기본 60s) 을
# 넘기면 프로세스가 kill 되고, `tempfile.TemporaryDirectory` 의 정리 코드는 SIGKILL
# 에서 돌지 않아 temp dir 이 그대로 남는다. 실측 결과 `/var/tmp` 에 1431개 /
# 약 211GB 가 누적되어 루트 파일시스템을 100% 채웠다 (부분 복사본의 내용물이
# `.venv` 172K 에서 잘린 것이 증거). scaffold 는 template/spec 파일만 읽으므로
# 아래 트리는 애초에 필요 없다.
EXCLUDED_TREE_DIRS = (
    ".venv",
    ".venv-build",
    "venv",
    ".git",
    "site",
    "dist",
    "build",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "*.egg-info",
)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        scratch = Path(tmpdir)
        harness_name = "test-harness"
        repo_copy = scratch / "repo"
        shutil.copytree(
            REPO_ROOT,
            repo_copy,
            symlinks=True,
            ignore=shutil.ignore_patterns(*EXCLUDED_TREE_DIRS),
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(repo_copy / "workflow-source" / "scripts" / "scaffold_harness.py"),
                "--harness-name",
                harness_name,
                "--display-name",
                "Test Harness",
                "--root-entrypoint",
                "TODO: test-entry.md",
                "--config-file",
                "TODO: test-config.json",
            ],
            cwd=repo_copy,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(completed.stdout)
        generated = payload["generated_files"]
        readme_path = Path(generated["readme"])
        overlay_spec_path = Path(generated["overlay_spec"])
        if not readme_path.exists() or not overlay_spec_path.exists():
            raise AssertionError("Harness scaffold did not create the expected files.")

        readme_text = readme_path.read_text(encoding="utf-8")
        if "Test Harness Harness Package" not in readme_text:
            raise AssertionError("Harness README did not include the display name.")
        if "read_only_transport_descriptors.json" not in readme_text:
            raise AssertionError("Harness README did not mention read-only transport descriptors.")

        overlay_spec_text = overlay_spec_path.read_text(encoding="utf-8")
        if "test-harness" not in overlay_spec_text:
            raise AssertionError("Overlay spec did not include the harness slug.")
        if "read_only_transport_descriptors.json" not in overlay_spec_text:
            raise AssertionError("Overlay spec did not mention read-only transport descriptors.")

    print("Harness scaffold smoke check passed.")
    return 0


def test_case_1() -> None:
    assert main() == 0, "case_1 smoke FAIL"


def test_case_2() -> None:
    assert main() == 0, "case_2 smoke FAIL"


def test_case_3() -> None:
    assert main() == 0, "case_3 smoke FAIL"


def test_case_4() -> None:
    assert main() == 0, "case_4 smoke FAIL"


def test_case_5() -> None:
    assert main() == 0, "case_5 smoke FAIL"



if __name__ == "__main__":
    raise SystemExit(main())
