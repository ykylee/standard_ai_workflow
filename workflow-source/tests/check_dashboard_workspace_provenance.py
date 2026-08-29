"""dashboard 가 **어디를 쟀는지** 를 말하는가 (v1.0.7).

## 왜 필요한가

`collect_dashboard_snapshot(workspace_root=None)` 은 `Path(__file__).resolve().parents[3]`
로 떨어졌다. 이 저장소는 editable install 이라 그 값이 **우연히** 저장소 루트였다.
설치본에서는 아니다 — 실측:

    모듈: <venv>/lib/python3.13/site-packages/workflow_kit/common/dashboard_data.py
    parents[3] → <venv>/lib/python3.13     (실재하는 디렉터리, ai-workflow/ 없음)

그러면 8 panel 이 전부 빈 값을 내고, 그 빈 값이 **그 경로의 측정 결과처럼** 보고된다.
오류가 아니라 조용히 틀린 측정이다. `workspace_root` 는 payload 에 있었지만 그 값을
**어떻게 얻었는지**(명시인지 추측인지)는 없었다 — §2.47/§2.49 와 같은 축이다.

이 모듈의 주석이 이미 답을 적고 있었다: *"판정 지표는 값만 내지 않는다 — 무엇을 보고
그렇게 판정했는지 함께 낸다."* workspace root 는 **모든 panel 의 기준**인데 정작
그 자신은 근거를 안 내고 있었다.

## 계약

1. 미지정이면 **cwd** 다 (모듈 위치에서 유도하지 않는다).
2. 명시 인자가 있으면 그것이 우선한다.
3. snapshot 이 `workspace_root_source` 로 어느 쪽이었는지 밝힌다.
4. 보고하는 경로와 panel 이 실제로 쓰는 경로가 같다.

Cross-ref: releases/Beta-v1.0.0.md §2.51.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "ai-workflow/memory/active/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common import dashboard_data as dd  # noqa: E402

PROBE = """
import json, sys
from pathlib import Path
from workflow_kit.common.dashboard_data import (
    resolve_workspace_root, collect_dashboard_snapshot,
)
import workflow_kit.common.dashboard_data as m
root, source = resolve_workspace_root(None)
snap = collect_dashboard_snapshot(inline_guard=False)
print(json.dumps({
    "resolved": str(root),
    "source": source,
    "repo_root_helper": str(m._repo_root(None)),
    "snapshot_root": snap["workspace_root"],
    "snapshot_source": snap["workspace_root_source"],
    "module_parents3": str(Path(m.__file__).resolve().parents[3]),
    "cwd": str(Path.cwd()),
}))
"""


def _probe_from(cwd: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", PROBE],
        capture_output=True, text=True, timeout=180, cwd=str(cwd),
        env={"PYTHONPATH": str(SOURCE_ROOT), "PATH": "/usr/bin:/bin", "HOME": str(cwd)},
    )
    assert proc.returncode == 0, f"exit {proc.returncode}: {proc.stderr[-800:]}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_unspecified_root_is_cwd_not_module_location() -> None:
    """미지정이면 cwd — 모듈 위치에서 유도하지 않는다 (원래 결함)."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        out = _probe_from(cwd)
        assert Path(out["resolved"]).resolve() == cwd.resolve(), out
        assert out["source"] == dd.WORKSPACE_SOURCE_CWD, out
        assert Path(out["resolved"]).resolve() != Path(out["module_parents3"]).resolve(), (
            "모듈 위치와 같다 — 추측으로 되돌아갔을 수 있다: " + json.dumps(out)
        )


def test_snapshot_reports_the_source() -> None:
    """snapshot 이 `workspace_root_source` 로 출처를 밝힌다."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        out = _probe_from(cwd)
        assert out["snapshot_source"] == dd.WORKSPACE_SOURCE_CWD, out
        assert Path(out["snapshot_root"]).resolve() == cwd.resolve(), out


def test_explicit_argument_wins_and_is_labeled() -> None:
    """명시 인자가 우선하고, 그 사실이 출처로 남는다."""
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "ws"
        ws.mkdir()
        root, source = dd.resolve_workspace_root(ws)
        assert root == ws and source == dd.WORKSPACE_SOURCE_ARGUMENT, (root, source)
        # str 도 받는다 (기존 caller 호환)
        root_s, source_s = dd.resolve_workspace_root(str(ws))
        assert root_s == ws and source_s == dd.WORKSPACE_SOURCE_ARGUMENT, (root_s, source_s)

        snap = dd.collect_dashboard_snapshot(ws, inline_guard=False)
        assert snap["workspace_root"] == str(ws), snap["workspace_root"]
        assert snap["workspace_root_source"] == dd.WORKSPACE_SOURCE_ARGUMENT, snap


def test_reported_root_is_the_one_panels_use() -> None:
    """보고하는 경로와 panel 이 실제로 쓰는 경로가 갈라지지 않는다.

    갈라지면 보고가 사실이 아니게 된다 — 값과 근거를 다른 코드에서 만들지 않는다.

    **저장소 루트에서 재면 안 된다.** 거기서는 cwd 와 모듈의 `parents[3]` 이 우연히
    같아서, 둘을 갈라 놓아도 차이가 안 보인다(이 검사의 첫 버전이 그래서 되주입을
    놓쳤다). 그래서 **다른 cwd 에서** 잰다.
    """
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td) / "ws"
        ws.mkdir()
        assert dd._repo_root(ws) == dd.resolve_workspace_root(ws)[0]

        out = _probe_from(Path(td))
        assert Path(out["repo_root_helper"]).resolve() == Path(out["resolved"]).resolve(), (
            "panel 이 쓰는 경로와 보고된 경로가 다르다: " + json.dumps(out)
        )
        assert Path(out["repo_root_helper"]).resolve() == Path(out["cwd"]).resolve(), out


def main() -> int:
    test_funcs = [
        test_unspecified_root_is_cwd_not_module_location,
        test_snapshot_reports_the_source,
        test_explicit_argument_wins_and_is_labeled,
        test_reported_root_is_the_one_panels_use,
    ]
    failures: list[tuple[str, str]] = []
    for func in test_funcs:
        try:
            func()
            print(f"  PASS: {func.__name__}")
        except AssertionError as e:
            failures.append((func.__name__, f"AssertionError: {e}"))
            print(f"  FAIL: {func.__name__} — {e}")
        except Exception as e:  # noqa: BLE001
            failures.append((func.__name__, f"{type(e).__name__}: {e}"))
            print(f"  FAIL: {func.__name__} — {type(e).__name__}: {e}")

    total = len(test_funcs)
    print(f"\n{total - len(failures)}/{total} PASS")
    if failures:
        for name, err in failures:
            print(f"  - {name}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
