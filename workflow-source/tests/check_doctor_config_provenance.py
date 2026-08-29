"""`workflow-doctor` CLI 의 **기준 경로와 설정 출처** (v1.0.5).

## 왜 필요한가

§2.47 이 린터에서 고친 것과 **같은 결함이 CLI 에도 있었다**.

    DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent

이 저장소에서 그 값은 `/home/yklee/repos` — **저장소 루트의 두 단계 위**다(실측). 게다가
kit 이 site-packages 에 설치되면 그 경로는 사용자의 프로젝트와 아무 관계도 없다. 모듈
위치로 사용자의 workspace 를 추측할 수 있다는 전제 자체가 틀렸다. 결과:

- `load_config(project_root)` 가 없는 pyproject 를 물어 **언제나 기본값**. 선언한
  `partial_rules = { resiliency = [...] }` / `opt_in` 이 평가에 도달한 적이 없다.
- `_read_state_json(project_root)` 도 같은 값을 써서 state.json 을 못 찾는다.

**기존 doctor smoke 는 전부 `--project-root` 를 명시해서 돌고 있었다.** 그래서 기본값이
깨져 있어도 아무 검사도 실패하지 않았다 — §2.47 의 "통과하면서 아무것도 보장하지 못하는
검사" 와 같은 자리다.

## 계약

1. `--project-root` 기본값은 **cwd** 다 (모듈 위치가 아니다).
2. `--show-config` 는 v0.7.7 의 5 field 를 **top-level 에 그대로** 두고, 출처를 옆에 붙인다.
3. 설정이 기본값으로 떨어진 사실과 그 이유가 산출물에 남는다.
4. `--config-path` 는 명시가 우선하고, 선언한 설정이 **실제 평가까지 도달**한다.
5. pretty 출력은 기본값으로 떨어졌으면 그 사실을 숫자보다 먼저 적는다.

Cross-ref: releases/Beta-v1.0.0.md §2.49.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
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

from workflow_kit.cli.doctor import default_project_root  # noqa: E402
from workflow_kit.common.metadata import (  # noqa: E402
    CONFIG_REASON_FILE_MISSING,
    CONFIG_REASON_SECTION_MISSING,
    CONFIG_SOURCE_DEFAULT,
    CONFIG_SOURCE_PYPROJECT,
)

DECLARED = (
    "[tool.workflow-doctor]\n"
    'partial_rules = { resiliency = ["RES-WF-01", "RES-WF-02"] }\n'
    'opt_in = { "security-auth" = ["SEC-AUTH-04"] }\n'
    'excluded_paths = ["vendor/*"]\n'
)


def _run(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "workflow_kit.cli.doctor", *args],
        capture_output=True, text=True, timeout=180, cwd=str(cwd),
        env={"PYTHONPATH": str(SOURCE_ROOT), "PATH": "/usr/bin:/bin", "HOME": str(cwd)},
    )


def _show_config(cwd: Path, *args: str) -> dict:
    proc = _run(cwd, "--show-config", *args)
    assert proc.returncode == 0, f"exit {proc.returncode}: {proc.stderr[-600:]}"
    return json.loads(proc.stdout)


# --- 1. 기준 경로 ---------------------------------------------------------


def test_default_project_root_is_cwd_not_module_location() -> None:
    """기본값은 호출자가 서 있는 자리다 — 모듈 위치에서 유도하지 않는다 (원래 결함)."""
    assert default_project_root() == Path.cwd()
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        out = _show_config(cwd)
        actual = Path(out["config_provenance"]["project_root"]).resolve()
        assert actual == cwd.resolve(), (
            f"project_root={actual} 가 cwd({cwd}) 가 아니다 — 모듈 위치로 추측하고 있다."
        )


# --- 2. 기존 계약 유지 ----------------------------------------------------


def test_show_config_keeps_five_fields_top_level() -> None:
    """v0.7.7 의 5 field 는 top-level 그대로 (출처를 더한다고 소비자를 깨지 않는다)."""
    with tempfile.TemporaryDirectory() as td:
        out = _show_config(Path(td))
        for key in ("partial_rules", "opt_in", "thresholds", "excluded_paths", "fail_on"):
            assert key in out, (key, sorted(out))
        assert "config_provenance" in out, sorted(out)


# --- 3. 출처가 남는가 -----------------------------------------------------


def test_missing_config_is_reported_not_silent() -> None:
    """pyproject 자체가 없으면 `default` + `file_missing`."""
    with tempfile.TemporaryDirectory() as td:
        prov = _show_config(Path(td))["config_provenance"]
        assert prov["config_source"] == CONFIG_SOURCE_DEFAULT, prov
        assert prov["config_default_reason"] == CONFIG_REASON_FILE_MISSING, prov


def test_section_missing_is_distinct_from_file_missing() -> None:
    """pyproject 는 있는데 section 이 없는 것은 **다른 사실**이다."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        (cwd / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
        prov = _show_config(cwd)["config_provenance"]
        assert prov["config_source"] == CONFIG_SOURCE_DEFAULT, prov
        assert prov["config_default_reason"] == CONFIG_REASON_SECTION_MISSING, prov


# --- 4. 명시가 우선하고, 실제로 적용되는가 --------------------------------


def test_explicit_config_path_wins_and_reaches_evaluation() -> None:
    """`--config-path` 로 준 선언이 **평가까지 도달**한다 (표시만 하는 게 아니다)."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        (cwd / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
        kit = cwd / "kit"
        kit.mkdir()
        (kit / "pyproject.toml").write_text(DECLARED, encoding="utf-8")

        out = _show_config(cwd, "--config-path", str(kit))
        assert out["config_provenance"]["config_source"] == CONFIG_SOURCE_PYPROJECT, out
        assert out["excluded_paths"] == ["vendor/*"], out["excluded_paths"]

        proc = _run(cwd, "--json", "--config-path", str(kit / "pyproject.toml"))
        assert proc.returncode == 0, proc.stderr[-600:]
        payload = json.loads(proc.stdout)
        assert payload["config"]["partial_rules"] == {
            "resiliency": ["RES-WF-01", "RES-WF-02"]
        }, payload["config"]
        applied = payload["results"]["resiliency"].get("partial_rules") or []
        assert "RES-WF-01" in applied, (
            f"선언한 partial_rules 가 평가에 도달하지 않았다: {applied}"
        )
        assert "config_provenance" in payload, sorted(payload)


# --- 5. 사람이 읽는 출력에도 남는가 ---------------------------------------


def test_pretty_footer_states_the_config_source() -> None:
    """기본값으로 떨어졌으면 표의 숫자보다 먼저 그 사실이 보인다."""
    with tempfile.TemporaryDirectory() as td:
        proc = _run(Path(td))
        assert proc.returncode == 0, proc.stderr[-600:]
        assert "Config source: default" in proc.stdout, proc.stdout[-800:]
        assert "Project root:" in proc.stdout, proc.stdout[-800:]


def main() -> int:
    test_funcs = [
        test_default_project_root_is_cwd_not_module_location,
        test_show_config_keeps_five_fields_top_level,
        test_missing_config_is_reported_not_silent,
        test_section_missing_is_distinct_from_file_missing,
        test_explicit_config_path_wins_and_reaches_evaluation,
        test_pretty_footer_states_the_config_source,
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
