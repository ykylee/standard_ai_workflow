#!/usr/bin/env python3
"""문서 frontmatter 의 `- 최종 수정일:` 스탬프를 **git 에서** 판정한다.

## 계보 (TASK-2026-09-01-main-002)

`check_code_index_v0_15_17` 과 `check_document_index_v0_15_16` 은 기대 스탬프를
`EXPECTED_LAST_UPDATED = "2026-08-31"` 처럼 **리터럴**로 들고 있었다. 그 리터럴은
릴리스 post-step(`release_pipeline.cmd_doc_headers_update`)이 문서 스탬프를 오늘로
올릴 때마다 사람이 같은 커밋에서 손으로 맞춰야 했고, v1.7.0(`4d7a78da`)과
v1.8.0(71차)에서 **정확히 같은 자리**를 두 번 고쳤다.

**단순 '문서에서 파생' 은 답이 아니다.** 문서를 읽어 그 값을 기대값으로 삼으면
단언이 동어반복이 되어 아무것도 못 잡는다 (같은 이유로 `check_packaging` 의
`REQUIRED_IMPORTS` 는 wheel 이 아니라 소스 트리에서 파생한다 —
TASK-2026-09-01-main-001).

그래서 **문서 자신이 아니라 git** 에서 판정한다. 지키려던 규약("이 문서를 고칠 때
스탬프도 같이 올린다")을 문장 그대로 옮긴 것이다:

    스탬프 >= 그 문서의 마지막 내용 변경일

- 워킹 트리에 미커밋 변경이 있으면 기준일은 **오늘(UTC)** 이고 **유예 0** 이다 —
  지금 고치는 중이니 스탬프도 오늘이어야 한다.
- 깨끗하면 기준일은 그 파일의 **마지막 커밋일(UTC)** 이고, 아래 경계 때문에
  **유예 1일** 을 준다.

`>=` 인 이유: 스탬프가 기준일보다 **앞선** 것은 거짓이 아니다 (오늘 스탬프를 찍고
내일 커밋하는 정상 흐름). 잡으려는 것은 **뒤처진** 스탬프 하나다.

UTC 로 재는 이유: 스탬프를 쓰는 `cmd_doc_headers_update` 의 `_today_iso()` 가 UTC 다.
한쪽을 로컬 시간으로 재면 KST(+9) 새벽 커밋에서 하루가 어긋나 근거 없는 red 가 난다.

## 하루의 유예 (`GRACE_DAYS = 1`) — 왜 두는가

스탬프를 **쓰는 시점**과 그것이 **커밋되는 시점**은 같은 UTC 날짜가 아닐 수 있다
(23:50 에 찍고 00:05 에 커밋). 그 경계를 밟을 때마다 근거 없는 red 가 나면, 사람은
사실이 아닌 날짜를 찍어 green 을 만들게 된다 — 리터럴 시절보다 나쁘다. 하루는 그
경계를 흡수하는 **최소** 폭이고, 이 검사가 실제로 잡아야 하는 것(몇 주 지난 스탬프를
단 채 고쳐지는 문서)은 그 폭을 한참 넘는다.

**이 유예는 아래 TZ 결함의 산물이 아니다.** 처음 이 판정을 켰을 때 두 인덱스 문서가
자기 커밋보다 하루 뒤처져 보였는데, 그건 `_git` 이 UTC 를 자칭하면서 실제로는 로컬
(KST) 날짜를 읽고 있었기 때문이다 — 없는 어긋남이었다. TZ 를 고정하자 스탬프
`2026-08-31` 과 커밋 `236a6aa9` 의 UTC 날짜가 **정확히 일치**한다. 유예의 근거는
관측된 어긋남이 아니라 위 경계 하나뿐이다.
"""

from __future__ import annotations

import os
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

#: 스탬프를 쓴 날과 그것이 커밋된 날이 갈릴 수 있어 흡수하는 폭 (모듈 docstring 참고).
GRACE_DAYS = 1


def _today_utc() -> str:
    """UTC today (YYYY-MM-DD) — `release_pipeline._today_iso()` 와 같은 기준."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _git(args: list[str], *, repo_root: Path) -> tuple[int, str]:
    # `--date=format-local:` 은 **실행 환경의 TZ** 를 쓴다. 그래서 TZ 를 여기서
    # 고정하지 않으면 개발 호스트(KST=+9)에서는 UTC 라고 적어 놓고 로컬 날짜를 재게
    # 된다 — 2026-09-01 에 이 파일을 처음 쓰면서 실제로 그렇게 했고, `236a6aa9`
    # (2026-09-01T00:12+09:00 = 2026-08-31 UTC) 가 하루 뒤로 읽혀 없는 어긋남을 봤다.
    env = {**os.environ, "TZ": "UTC"}
    completed = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    return completed.returncode, completed.stdout.strip()


def last_content_change_date(
    path: Path, *, repo_root: Path
) -> tuple[str | None, str, int]:
    """``(YYYY-MM-DD | None, 근거 문장, 허용 유예일)`` — 마지막 내용 변경일 (UTC).

    유예를 **여기서** 돌려주는 이유: 유예가 정당한 것은 커밋된 경우뿐이다 (모듈
    docstring 의 경계). 워킹 트리가 더러우면 그 문서는 *지금* 고쳐지는 중이고,
    거기에 유예를 주면 "어제 스탬프를 단 채 오늘 내용을 고치는 것" 이 통과한다 —
    이 검사가 잡으려는 바로 그 경우다 (실측 2026-09-01: 유예를 두 갈래에 똑같이
    적용했더니 되주입이 green 이었다).

    판정 불가는 `None` 으로 돌려주고 **호출자가 loud 하게 실패**한다. 못 잰 것을
    통과로 치면 이 검사가 있으나 마나가 된다 (저장소 규약: '모름 ≠ 안전').
    """
    rel = path.relative_to(repo_root).as_posix()

    rc, dirty = _git(["status", "--porcelain", "--", rel], repo_root=repo_root)
    if rc != 0:
        return None, f"git status 실패 (rc={rc}) — git 저장소 안에서 돌려야 한다", 0
    if dirty:
        return (
            _today_utc(),
            f"워킹 트리에 미커밋 변경이 있다 ({dirty.split(chr(10))[0]})",
            0,
        )

    # `%cd` + `--date=format:` 은 커밋의 로컬 타임존을 쓴다. `-local` 접미사를 붙이면
    # 실행 환경의 TZ 를 쓰고, TZ=UTC 를 주면 UTC 로 고정된다.
    rc, out = _git(
        ["log", "-1", "--date=format-local:%Y-%m-%d", "--format=%cd %h", "--", rel],
        repo_root=repo_root,
    )
    if rc != 0:
        return None, f"git log 실패 (rc={rc})", 0
    if not out:
        return None, f"git 이 `{rel}` 의 커밋 이력을 모른다 (미추적 파일인가)", 0
    commit_date, _, sha = out.partition(" ")
    return (
        commit_date,
        f"마지막 커밋 {sha or '?'} ({commit_date}, UTC)",
        GRACE_DAYS,
    )


def _minus_days(iso: str, days: int) -> str:
    return (date.fromisoformat(iso) - timedelta(days=days)).isoformat()


def check_frontmatter_stamp(
    path: Path, *, repo_root: Path, actual: str
) -> tuple[bool, str]:
    """스탬프가 마지막 내용 변경일 (유예 포함) 이상인가. ``(ok, 설명)``."""
    changed_at, reason, grace = last_content_change_date(path, repo_root=repo_root)
    if changed_at is None:
        return False, f"기대 스탬프를 판정할 수 없다 — {reason}"
    try:
        floor = _minus_days(changed_at, grace)
    except ValueError:
        return False, f"날짜 형식을 읽을 수 없다: {changed_at!r} ({reason})"
    try:
        date.fromisoformat(actual)
    except ValueError:
        return False, f"`- 최종 수정일:` 이 YYYY-MM-DD 가 아니다: {actual!r}"
    if actual < floor:
        return False, (
            f"스탬프가 문서의 마지막 내용 변경보다 뒤처졌다 — "
            f"stamp={actual} < {floor} (변경일 {changed_at} − 유예 {grace}일, {reason}). "
            f"`{path.name}` 의 `- 최종 수정일:` 을 올리거나 "
            "`wk release-pipeline doc-headers-update --apply` 를 돌린다."
        )
    return True, f"스탬프 {actual} >= {floor} (변경일 {changed_at}, {reason})"
