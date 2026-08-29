"""`rotate_handoff_tasks` smoke (TASK-2026-08-09-main-006)

이 도구에는 회귀 검사가 없었고, 그래서 **한 번도 동작한 적이 없다는 사실이 드러나지
않았다**. 두 결함이 동시에 있었다:

1. 섹션 이름을 고정 문자열(`## 5. 최근 완료 작업` / `## 6. 잔여 작업`)로 찾아서
   실제 문서(`## 4.` / `## 5. 다음 세션 시작 포인트`)를 못 찾았다 → 늘 `error`.
2. `items[-max:]` 로 뒤를 남겼다. §4 는 앞이 최신이므로, 1번만 고쳤다면 도구가
   **동작하면서 최신을 지웠을 것이다.**

검증 케이스 (9):
    1. 실제 문서 형식(`## 4. …` + 다음 섹션이 `## 5. 다음 세션 시작 포인트`) 인식
    2. 번호 없는 헤더(`## 최근 완료 작업`)도 인식
    3. 상한 이하 → no-op (`rotated: False`)
    4. 상한 초과 → **뒤(오래된)** 를 버리고 앞 CAP 건을 남긴다
    5. newest_first=False → 반대로 앞을 버린다
    6. 라벨 줄 / 빈 줄 / 다른 섹션이 보존된다
    7. 섹션 부재 → error (조용히 성공하지 않는다)
    8. idempotent — 두 번 돌려도 두 번째는 no-op
    9. baseline(`- 현재 기준선:`) 을 건드리지 않는다 + 끝 개행 보존

Stdlib only.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.rotation import rotate_handoff_tasks  # noqa: E402

BASELINE = "- 현재 기준선: v1.1.1-beta + `origin/main` = `abc1234`"


def _handoff(tmp: Path, items: list[str], *, header: str = "## 4. 최근 완료 작업") -> Path:
    """실제 `session_handoff.md` 와 같은 뼈대로 만든다."""
    body = [
        "# Session Handoff",
        "",
        "## 1. 현재 작업 요약",
        "",
        BASELINE,
        "",
        "## 3. 차단 작업",
        "",
        "- 현재 `blocked` 작업:",
        "-",
        "",
        header,
        "",
        "- 최근 완료 작업 목록:",
        *items,
        "",
        "## 5. 다음 세션 시작 포인트",
        "",
        "무엇이 끝났나.",
        "",
    ]
    path = tmp / "session_handoff.md"
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


def _items(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("- TASK-")
    ]


def main() -> int:
    failures: list[str] = []

    def check(label: str, cond: bool, detail: str = "") -> None:
        if cond:
            print(f"PASS: {label}")
        else:
            print(f"FAIL: {label} — {detail}")
            failures.append(label)

    # 최신이 앞. n=13 이 가장 최신.
    def labels(n: int) -> list[str]:
        return [f"- TASK-2026-06-{i:02d}-main-001 완료 {i}" for i in range(n, 0, -1)]

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # 1) 실제 문서 형식 인식
        (tmp / "a").mkdir()
        path = _handoff(tmp / "a", labels(13))
        result = rotate_handoff_tasks(path, 10)
        check(
            "1) 실제 문서 형식(## 4. + 다음 섹션) 인식",
            result["status"] == "ok" and result["rotated"] is True,
            f"{result}",
        )

        # 4) 뒤(오래된)를 버린다 — 최신이 남는다
        remaining = _items(path)
        check(
            "4) 앞 CAP 건(최신)이 남고 뒤(오래된)가 버려진다",
            len(remaining) == 10
            and remaining[0].endswith("완료 13")
            and remaining[-1].endswith("완료 4")
            and result["rotated_count"] == 3,
            f"first={remaining[0][-12:]!r} last={remaining[-1][-12:]!r} n={len(remaining)}",
        )

        # 6) 주변 보존
        text = path.read_text(encoding="utf-8")
        check(
            "6) 라벨 줄 / 다른 섹션 / baseline 보존",
            "- 최근 완료 작업 목록:" in text
            and "## 5. 다음 세션 시작 포인트" in text
            and "## 3. 차단 작업" in text
            and BASELINE in text,
            "",
        )

        # 9) baseline 오염 없음 + 끝 개행
        check(
            "9) baseline 을 건드리지 않는다 + 끝 개행 보존",
            text.count(BASELINE) == 1
            and "완료 1" not in text.split("## 4.")[0]
            and text.endswith("\n"),
            f"baseline_count={text.count(BASELINE)} endswith_nl={text.endswith(chr(10))}",
        )

        # 8) idempotent
        again = rotate_handoff_tasks(path, 10)
        check(
            "8) idempotent — 두 번째는 no-op",
            again["rotated"] is False and len(_items(path)) == 10,
            f"{again}",
        )

        # 2) 번호 없는 헤더
        (tmp / "b").mkdir()
        path_b = _handoff(tmp / "b", labels(12), header="## 최근 완료 작업")
        result_b = rotate_handoff_tasks(path_b, 10)
        check(
            "2) 번호 없는 헤더도 인식",
            result_b["status"] == "ok" and result_b["rotated"] is True and len(_items(path_b)) == 10,
            f"{result_b}",
        )

        # 3) 상한 이하 → no-op
        (tmp / "c").mkdir()
        path_c = _handoff(tmp / "c", labels(5))
        before = path_c.read_text(encoding="utf-8")
        result_c = rotate_handoff_tasks(path_c, 10)
        check(
            "3) 상한 이하 → no-op (파일 무변경)",
            result_c["rotated"] is False and path_c.read_text(encoding="utf-8") == before,
            f"{result_c}",
        )

        # 5) newest_first=False → 반대
        (tmp / "d").mkdir()
        path_d = _handoff(tmp / "d", labels(13))
        rotate_handoff_tasks(path_d, 10, newest_first=False)
        rem_d = _items(path_d)
        check(
            "5) newest_first=False → 앞을 버린다",
            len(rem_d) == 10 and rem_d[0].endswith("완료 10") and rem_d[-1].endswith("완료 1"),
            f"first={rem_d[0][-12:]!r} last={rem_d[-1][-12:]!r}",
        )

        # 7) 섹션 부재 → error
        (tmp / "e").mkdir()
        path_e = tmp / "e" / "session_handoff.md"
        path_e.write_text("# Session Handoff\n\n## 1. 요약\n\n내용.\n", encoding="utf-8")
        result_e = rotate_handoff_tasks(path_e, 10)
        check(
            "7) 섹션 부재 → error (조용히 성공 ❌)",
            result_e["status"] == "error" and result_e.get("rotated") is False,
            f"{result_e}",
        )

    total = 9
    print()
    if failures:
        print(f"{total - len(failures)}/{total} PASS — FAILED: {failures}")
        return 1
    print(f"{total}/{total} PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
