#!/usr/bin/env python3
"""저장소 소스의 **컴파일 시점 경고** 를 캐시와 무관하게 잰다.

TASK-2026-09-21-main-008. 계약과 실측 근거는
`workflow_kit/common/check_warnings.py` 의 `sweep_compile` 위 주석이 정본이다.

## 왜 실행 수집만으로는 부족한가 (2026-09-21 실측)

82차(main-007)가 '저장소 코드가 낸 Python 경고 = 게이트 red' 를 세웠다. 그런데 그
수집 지점은 **per-check 서브프로세스 출력** 하나뿐이고, 거기에는 구멍이 둘 있다.

**① 판정이 `__pycache__` 상태에 달려 있다.** `SyntaxWarning` 류는 *컴파일 시점*
신호라 `.pyc` 가 유효하면 아예 나지 않는다. `dashboard_data.py` 에 invalid escape 를
주입하고 **소스를 그대로 둔 채** 두 번 돌린 실측:

    1차(cold cache): exit 1   ← 게이트가 잡는다
    2차(warm cache): exit 0   ← 고친 것이 없는데 green

**고친 것 없이 재실행만으로 green 이 되는 게이트** 였다. CI 는 체크아웃이 fresh 라
안 물지만, 로컬 push 게이트는 바로 문다.

**② runner 부모가 낸 경고는 아무도 안 봤다.** 부모는 `workflow_kit` 모듈 **44/196**
을 transitively import 한다. `branch_matrix.py` 주입 실측에서 경고가 배너보다 먼저
화면에 찍히는데도 EXIT=0 이었다. 이쪽은 runner 의 `PARENT_WARNINGS` 가 닫았고,
이 검사는 ①을 원리적으로 없앤다 — `compile()` 은 `__pycache__` 를 **보지 않는다**.

## 범위는 손 목록이 아니라 파생이다

대상은 `python_floor.iter_sources(repo_root)` 다. 하한 호환 판정과 **같은 열거를
공유** 한다 — 사본을 두면 갈라지고, 좁은 쪽은 조용히 그 밖을 못 잰다. case 2 가
그 파생 집합이 git 추적 `*.py` 전수와 일치하는지 매 게이트마다 대조한다.

검증 케이스 (6):
    1. 스윕이 저장소 소스 전수를 **실제로 컴파일한다** (긍정 증거)
    2. 범위가 git 추적 `*.py` 와 일치한다 (조용한 축소를 잡는다)
    3. 이 저장소의 저장소-출처 컴파일 경고는 0 이다 (실 저장소 판정)
    4. 되주입 — invalid escape 를 스윕이 잡는다
    5. **캐시 무관** — import 기반 탐지는 warm cache 에서 눈이 머는데 스윕은 안 먼다
    6. 컴파일 실패를 삼키지 않고 `errors` 로 내놓는다 (모름 ≠ 안전)

Stdlib only.
"""

from __future__ import annotations

#: 전역 선언 (spec `core/test_impact_tiering_spec.md` §2). 좁힐 수 있는 표면이
#: 아니다 — 이 검사의 입력은 **저장소 Python 소스 전수** 이고, 그 전수성이 곧
#: 이 검사의 계약이다 (case 2 가 git 추적 집합과 대조해 좁아짐을 red 로 잡는다).
WATCHES_ALL_REASON = (
    "저장소 Python 소스 전수를 컴파일한다 — meta-watch 실측 (2026-09-21) 566개 "
    "소스 + 열거·판정 정본(python_floor · check_warnings) + pyproject.toml"
)

#: 이 검사가 강제하는 정본 요구 (spec `core/test_impact_tiering_spec.md` §7).
ENFORCES = (
    "repo-warnings-are-a-gate-signal",
    "compile-warning-verdict-is-cache-independent",
)

#: case 1 이 565개 소스를 컴파일한다 (실측 0.6s) + case 5 가 서브프로세스를 띄운다.
CHECK_TIMEOUT_S = 150

import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.check_warnings import (  # noqa: E402
    gated_only,
    sweep_compile,
)
from workflow_kit.common.python_floor import (  # noqa: E402
    iter_sources,
    resolve_scope,
)

#: 컴파일 대상 루트. 하한 호환 판정과 **같은 결정** 을 쓴다 — 두 축이 각자 루트를
#: 정하면 한쪽만 좁아져도 아무도 모른다 (main-009).
COMPILE_ROOT, _PYPROJECT = resolve_scope(REPO_ROOT)

_failures: list[str] = []
_passes: list[str] = []


def _ok(name: str) -> None:
    _passes.append(name)
    print(f"  [PASS] {name}")


def _fail(name: str, why: str) -> None:
    _failures.append(f"{name}: {why}")
    print(f"  [FAIL] {name}: {why}")


# --- case 1 · 3 · 6: 실 저장소 스윕 ------------------------------------------

sources = iter_sources(COMPILE_ROOT)
result = sweep_compile(sources)

if result.compiled > 0 and result.compiled == len(sources):
    _ok(f"case 1: 저장소 소스 {result.compiled}개를 실제로 컴파일했다 (긍정 증거)")
else:
    _fail("case 1",
        f"컴파일 {result.compiled} / 대상 {len(sources)} — "
        "'실패가 안 보였다' 는 통과가 아니다")

gated = gated_only(result.warnings, str(REPO_ROOT))
if not gated:
    _ok(f"case 3: 저장소-출처 컴파일 경고 0 (스윕 {len(sources)}개)")
else:
    _fail("case 3", "저장소 코드가 컴파일 시점 경고를 낸다: "
        + " / ".join(w.render() for w in gated[:5]))

# case 6 은 저장소 관찰만으로는 **발화할 수 없다** — 오늘 컴파일 실패가 0 이라
# `errors` 수집을 통째로 지워도 0 은 0 이다. 되주입이 정확히 그것을 잡았다
# (R4, 2026-09-21). 그래서 관찰과 **기전** 을 같이 건다: 실제로 깨진 소스를 물려
# errors 에 잡히는지 본다. 그러지 않으면 '모름' 이 '통과' 로 접힌다.
with tempfile.TemporaryDirectory() as _tmp:
    _broken = Path(_tmp) / "broken_probe.py"
    _broken.write_text("def f(:" + chr(10), encoding="utf-8")
    _probe_result = sweep_compile([_broken])

if result.errors:
    _fail("case 6", "게이트 해석기에서 컴파일 실패: "
        + " / ".join(f"{path}: {why}" for path, why in result.errors[:5]))
elif not _probe_result.errors:
    _fail("case 6",
        "깨진 소스를 물렸는데 errors 가 비어 있다 — 컴파일 실패를 삼키고 있다. "
        "못 잰 것을 통과로 세면 거짓 안심이 된다")
elif _probe_result.compiled != 0:
    _fail("case 6",
        f"깨진 소스를 compiled 로 셌다 ({_probe_result.compiled}) — 긍정 증거가 거짓이다")
else:
    _ok("case 6: 저장소 컴파일 실패 0 이고, 깨진 소스는 errors 로 잡힌다 "
       f"({_probe_result.errors[0][1]})")


# --- case 2: 범위가 파생인가 --------------------------------------------------

proc = subprocess.run(
    ["git", "ls-files", "*.py"],
    cwd=REPO_ROOT, capture_output=True, text=True,
)
if proc.returncode != 0:
    _fail("case 2", f"git ls-files 실패: {proc.stderr.strip()[:200]}")
else:
    tracked = {line for line in proc.stdout.split() if line}
    swept = {str(path.relative_to(REPO_ROOT)) for path in sources}
    missing = sorted(tracked - swept)
    extra = sorted(swept - tracked)
    # **좁아지는 쪽만 red 다.** 이 case 가 막는 것은 '범위가 조용히 줄어 그 밖이
    # 갈라지는 것' 이고, 추적 밖 파일까지 스윕하는 것은 범위가 *넓은* 것이라 그
    # 실패 모드가 아니다 (새로 만들어 아직 `git add` 안 한 파일이 정확히 그것이다).
    # 넓은 쪽은 삼키지 않고 통과 줄에 수를 적는다 — 조용한 쪽이 틀린 쪽이다.
    if not missing:
        note = f" (+추적 밖 {len(extra)}건)" if extra else ""
        _ok(f"case 2: git 추적 *.py {len(tracked)}개를 전부 스윕한다{note}")
    else:
        _fail("case 2",
            f"추적되는데 못 잰 것 {len(missing)}건 {missing[:3]} — "
            "범위가 조용히 좁아졌다")


# --- case 4 · 5: 되주입 -------------------------------------------------------

_PROBE = 'BAD = "\\d+ invalid escape"\n'


def _escape_warnings(found: list) -> list:
    """invalid escape 경고를 **범주에 의존하지 않고** 고른다.

    같은 결함의 범주가 해석기마다 다르다 — 3.12+ 는 `SyntaxWarning`, 3.11 이하는
    `DeprecationWarning` 이다. 처음엔 `SyntaxWarning` 으로 하드코딩했고, **CI 와
    같은 3.11 셀에서만 case 4·5 가 red** 였다 (2026-09-21 push 게이트 실측).
    판정이 실행 해석기에 달리는 바로 그 결함족이라, 이 축이 자기 자신을 잡았다.
    """
    return [w for w in found if "invalid escape" in w.message]


with tempfile.TemporaryDirectory() as tmp:
    probe = Path(tmp) / "probe_module.py"
    probe.write_text(_PROBE, encoding="utf-8")

    injected = sweep_compile([probe])
    escape_warnings = _escape_warnings(injected.warnings)
    if escape_warnings:
        _ok(f"case 4: 되주입한 invalid escape 를 잡는다 ({escape_warnings[0].render()})")
    else:
        _fail("case 4",
              "invalid escape 를 심었는데 스윕이 아무것도 못 봤다 — 판정이 죽어 있다")

    # case 5: **이 검사의 존재 이유** — 같은 결함을 import 로 탐지하면 warm cache 에서
    # 눈이 먼다. 두 수단을 같은 파일에 나란히 걸어 대조한다.
    driver = Path(tmp) / "driver.py"
    driver.write_text(textwrap.dedent('''
        import json, sys, warnings
        sys.path.insert(0, sys.argv[1])
        seen = []
        with warnings.catch_warnings(record=True) as cap:
            warnings.simplefilter("always")
            import probe_module  # noqa: F401
        # 범주는 해석기마다 다르다 (3.12+ SyntaxWarning / 3.11 이하 DeprecationWarning).
        seen.append(len([w for w in cap if "invalid escape" in str(w.message)]))
        print(json.dumps(seen))
    '''), encoding="utf-8")

    # 드라이버는 **바이트코드 캐시를 반드시 쓸 수 있어야** 한다 — 이 case 가 재는
    # 축이 정확히 그것이다. 주변 환경의 `PYTHONDONTWRITEBYTECODE` 를 그대로 물려주면
    # 캐시가 안 생겨 case 가 미측정으로 떨어진다 (되주입 harness 가 실제로 그것을
    # 켜고 돌아 이 결함을 잡았다). 판정이 호스트 환경에 달리지 않게 여기서 지운다.
    driver_env = {k: v for k, v in os.environ.items()
                  if k != "PYTHONDONTWRITEBYTECODE"}

    def import_detects() -> int:
        run = subprocess.run([sys.executable, str(driver), tmp],
                             capture_output=True, text=True, timeout=60,
                             env=driver_env)
        return int(run.stdout.strip().splitlines()[-1].strip("[]"))

    first = import_detects()          # cold: .pyc 가 없다 → 컴파일 → 경고
    second = import_detects()         # warm: 방금 쓴 .pyc 가 유효 → 침묵
    again = sweep_compile([probe])
    sweep_still = len(_escape_warnings(again.warnings))

    cache_written = any(Path(tmp).glob("__pycache__/probe_module.*.pyc"))
    if not cache_written:
        _fail("case 5",
            "드라이버가 .pyc 를 안 남겼다 — 캐시 축을 재지 못했으므로 "
            "이 case 는 통과가 아니라 미측정이다")
    elif first > 0 and second == 0 and sweep_still > 0:
        _ok("case 5: import 탐지는 warm cache 에서 눈이 먼다(1차 %d → 2차 %d)는데 "
           "스윕은 여전히 %d건을 본다" % (first, second, sweep_still))
    else:
        _fail("case 5",
            f"캐시 무관성을 실증하지 못했다 — import 1차 {first} / 2차 {second} / "
            f"스윕 {sweep_still}")


print()
print(f"=== Result: {len(_passes)}/{len(_passes) + len(_failures)} PASS ===")
for line in _failures:
    print(f"  ✗ {line}")
sys.exit(1 if _failures else 0)
