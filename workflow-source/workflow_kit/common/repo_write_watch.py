"""전량 실행이 **추적 중인 저장소 파일을 건드리는가** 를 러너가 직접 관찰한다.

TASK-2026-09-22-main-008.

## 왜 러너로 옮겼는가

이 감시는 원래 `check_no_repo_write` 가 했다. 그 검사는 대표 표본 **16개**를
서브프로세스로 **다시 돌려** 전후를 비교했는데, 그것이 전량 벽시계의 **35%**
(76.7s)를 혼자 썼다 — 이미 병렬 구간에서 돈 검사를 정숙 구간에서 또 직렬로
도는 비용이다 (2026-09-22 실측: 벽시계 221s · 정숙 구간 103s).

러너는 이미 **모든** 검사를 서브프로세스로 돌리고 있고, 어느 검사가 언제
시작·종료했는지 안다. 그래서 감시를 러너로 옮기면:

    감시 범위   표본 16개 → **검사 전수**
    정상 실행   76.7s 재실행 → 폴링 1개 (실측 `git status --porcelain` 12.7ms,
                0.5s 간격 221s 동안 **5.6s**)

## 귀속은 약해진다 — 감추지 않는다

병렬 구간에서는 "누가 썼는가" 를 단정할 수 없다. 대신 변경이 관측된 **시각에
in-flight 였던 검사**를 후보로 내놓는다 (실측 동시성: 중앙 9 · 최대 11).
범인을 좁혀야 하면 그 9개만 직렬로 다시 돌리면 된다 — **비용을 위반이 났을
때로 옮긴 것**이지 없앤 것이 아니다.

## 한계 (과장하지 않는다)

폴링은 타이밍 의존이라 **음성은 증명이 아니다**. 짧은 접촉(touch-and-restore)은
놓칠 수 있다. 전후 비교는 그것과 독립이므로 *끝까지 남은* 변경은 확실히 잡는다.
"""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

#: 폴링 간격. 실측 `git status --porcelain` 12.7ms 이므로 0.5s 면 전체의 2.5% 다.
POLL_INTERVAL_S = 0.5

#: **알려진 touch-and-restore 원장** — 경로 조각 → 그래도 되는 이유.
#:
#: 미지의 transient 접촉은 **red** 다 (옛 `check_no_repo_write` 의 계약을 그대로
#: 옮겼다). 구조적으로 불가피한 것만 여기 이유와 함께 등록하고, **원장은 단방향**
#: 이다 — 늘어나는 것을 눈에 보이게 두려는 것이지 면제 창구가 아니다.
#:
#: 첫 항목은 전수 감시가 켜지자마자 나왔다: 예전 표본 16개에는 없던 접촉이라
#: **아무도 못 보고 있었다.**
KNOWN_TRANSIENT_PATHS: dict[str, str] = {
    "workflow-source/tests/check_zzz_warning_probe.py":
        "check_warning_gate case 6 의 end-to-end probe. 러너가 검사를 `tests/` "
        "에서 discover 하므로 그 자리에 둘 수밖에 없다 — 만들었다 반드시 지운다.",
}


def _known_reason(line: str) -> str | None:
    """`git status --porcelain` 한 줄이 원장에 있는 접촉인가."""
    for fragment, reason in KNOWN_TRANSIENT_PATHS.items():
        if fragment in line:
            return reason
    return None


def _status(repo_root: Path) -> frozenset[str] | None:
    """`git status --porcelain` 한 줄들. 실패하면 ``None``.

    `-uno` 를 쓰지 않는다 — 그러면 **새 파일 생성**을 못 본다. 현재 계약은
    수정·생성·삭제·복원 전부를 잡는 것이라 3.3ms 를 아끼려고 신호를 잃지 않는다.
    """
    try:
        done = subprocess.run(
            ["git", "-C", str(repo_root), "status", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return frozenset(line for line in done.stdout.splitlines() if line.strip())


@dataclass
class Sighting:
    """관측된 변경 하나와, 그 시각에 돌고 있던 검사들."""

    line: str
    at: float
    in_flight: tuple[str, ...] = ()


@dataclass
class RepoWriteWatch:
    """실행 전후 + 실행 중을 함께 본다.

    호출자(러너)는 `note_start` / `note_end` 로 in-flight 집합을 알려 준다 —
    귀속의 근거가 그것이고, 러너는 이미 그 정보를 갖고 있다.
    """

    repo_root: Path
    baseline: frozenset[str] | None = None
    unavailable: str = ""
    sightings: list[Sighting] = field(default_factory=list)
    _running: dict[str, float] = field(default_factory=dict)
    _seen: set[str] = field(default_factory=set)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None

    def start(self) -> None:
        self.baseline = _status(self.repo_root)
        if self.baseline is None:
            # 못 재는 것을 통과로 세지 않는다 — 사유를 남기고 폴링도 걸지 않는다.
            self.unavailable = "git status 를 읽지 못했다 (git 저장소 밖인가)"
            return
        self._seen = set(self.baseline)
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def note_start(self, name: str) -> None:
        with self._lock:
            self._running[name] = time.time()

    def note_end(self, name: str) -> None:
        with self._lock:
            self._running.pop(name, None)

    def _in_flight(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._running))

    def _poll(self) -> None:
        while not self._stop.wait(POLL_INTERVAL_S):
            current = _status(self.repo_root)
            if current is None:
                continue
            fresh = current - self._seen
            if not fresh:
                continue
            flight = self._in_flight()
            now = time.time()
            for line in sorted(fresh):
                self._seen.add(line)
                self.sightings.append(Sighting(line=line, at=now, in_flight=flight))

    def stop(self) -> dict[str, object]:
        """폴링을 멈추고 **판정**을 낸다.

        `lingering` 은 실행이 끝난 뒤에도 남아 있는 변경(확실한 위반),
        `transient` 는 중간에만 보였다 사라진 것(폴링이 잡은 추가 방어층)이다.
        """
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        if self.baseline is None:
            return {"measured": False, "reason": self.unavailable}
        final = _status(self.repo_root)
        if final is None:
            return {"measured": False, "reason": "종료 시점 git status 실패"}
        lingering = sorted(final - self.baseline)
        lingering_set = set(lingering)
        transient = [s for s in self.sightings if s.line not in lingering_set]
        unknown = [s for s in transient if _known_reason(s.line) is None]
        known = [s for s in transient if _known_reason(s.line) is not None]
        return {
            "measured": True,
            "lingering": lingering,
            "transient": [
                {"line": s.line, "in_flight": list(s.in_flight)} for s in unknown
            ],
            "known_transient": [
                {"line": s.line, "reason": _known_reason(s.line)} for s in known
            ],
            "sightings": [
                {"line": s.line, "in_flight": list(s.in_flight)} for s in self.sightings
            ],
            "poll_interval_s": POLL_INTERVAL_S,
        }
