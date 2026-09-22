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
import re
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
    if dirty and not _worktree_change_is_stamp_only(rel, repo_root=repo_root):
        return (
            _today_utc(),
            f"워킹 트리에 미커밋 변경이 있다 ({dirty.split(chr(10))[0]})",
            0,
        )
    # 미커밋 변경이 **스탬프 줄뿐** 이면 내용은 그대로다 — 아래 이력 판정으로 간다.
    # 이 분기가 없으면 스탬프를 고치는 행위 자체가 '오늘 내용을 고쳤다' 로 읽혀,
    # 교정이 곧 위반이 되는 자가당착이 된다 (2026-09-22 소급 교정에서 실측:
    # `check_document_index` 가 정확히 그 이유로 red 였다).

    # `%cd` + `--date=format:` 은 커밋의 로컬 타임존을 쓴다. `-local` 접미사를 붙이면
    # 실행 환경의 TZ 를 쓰고, TZ=UTC 를 주면 UTC 로 고정된다.
    # **이력과 diff 를 한 번에 받는다.** 커밋 목록을 받고 커밋마다 `git show` 를
    # 다시 부르면 문서 하나에 `1 + N` 번 프로세스를 띄운다 — 저장소 문서 93개에서
    # 그것이 `doc-headers-update` 를 **6.2s** 로 만들었고, 그 단계를 auto-step 으로
    # 부르는 `release --dry-run` 이 9.6s 가 되면서 병렬 검사의 경합 창을 벌려
    # CI smoke 를 2연속 red 로 만들었다 (2026-09-22, TASK-2026-09-22-main-005).
    # `log -p` 하나면 같은 정보를 프로세스 **1번**으로 얻는다.
    rc, out = _git(
        ["log", f"-{_HISTORY_SCAN_LIMIT}", "--date=format-local:%Y-%m-%d",
         "--format=%x00%cd %h", "-p", "--unified=0", "--", rel],
        repo_root=repo_root,
    )
    if rc != 0:
        return None, f"git log 실패 (rc={rc})", 0
    if not out.strip():
        return None, f"git 이 `{rel}` 의 커밋 이력을 모른다 (미추적 파일인가)", 0

    skipped = 0
    oldest: tuple[str, str] | None = None
    # `%x00` 로 커밋 경계를 넣었으므로 그것으로 자른다 — diff 본문에 나올 수 없는
    # 바이트라 경계가 본문과 섞이지 않는다.
    for chunk in out.split("\x00"):
        if not chunk.strip():
            continue
        header, _, body = chunk.partition("\n")
        parts = header.split()
        if len(parts) < 2:
            continue
        commit_date, short_sha = parts[0], parts[1]
        oldest = (commit_date, short_sha)
        if _diff_is_stamp_only(body):
            skipped += 1
            continue
        note = f"마지막 내용 변경 {short_sha} ({commit_date}, UTC)"
        if skipped:
            note += f" — 스탬프만 바꾼 커밋 {skipped}개 건너뜀"
        return commit_date, note, GRACE_DAYS

    # 훑은 범위가 전부 스탬프 전용이었다. 더 파고들지 않고 **가장 오래된 것**을
    # 쓴다 — 여기서 '마지막 커밋' 으로 되돌리면 이 함수가 다시 이름과 어긋난다.
    if oldest is None:
        return None, f"git log 출력을 해석하지 못했다 (`{rel}`)", 0
    return (
        oldest[0],
        f"최근 {_HISTORY_SCAN_LIMIT}개 커밋이 전부 스탬프 전용이라 "
        f"그 범위의 가장 오래된 것({oldest[1]})을 기준으로 삼았다",
        GRACE_DAYS,
    )


#: 스탬프 전용 커밋을 건너뛰며 되짚을 최대 깊이.
#:
#: 실측 (2026-09-22, 스탬프가 있는 git 추적 md **467개 전수**): 건너뛸 것이 없는
#: 문서가 370개이고, 나머지의 깊이는 최대 **15** · 평균 2.2 다 (분포는 4·11·13·15
#: 에 몰려 있는데 그것이 blanket bump 를 실은 발행들의 횟수다). 상한 20 을 소진한
#: 문서는 **0건**. 넘어가면 판정을 조용히 바꾸지 않고 **그 사실을 근거 문장에 적는다.**
_HISTORY_SCAN_LIMIT = 20


def _worktree_change_is_stamp_only(rel: str, *, repo_root: Path) -> bool:
    """미커밋 변경이 그 파일에서 **`- 최종 수정일:` 줄만** 바꿨는가.

    커밋 쪽(`_commit_is_stamp_only`)과 같은 판정을 워킹 트리에 적용한다. 판정
    불가는 **False** — 모르는 변경을 '스탬프 전용' 으로 접으면 유예 0 규율이
    풀린다.
    """
    rc, out = _git(["diff", "--unified=0", "--", rel], repo_root=repo_root)
    if rc != 0:
        return False
    return _diff_is_stamp_only(out)


def _diff_is_stamp_only(diff_text: str) -> bool:
    """unified diff 본문이 **`- 최종 수정일:` 줄만** 바꿨는가.

    커밋 쪽과 워킹트리 쪽이 **같은 판정**을 쓰도록 텍스트만 받는다 — 두 벌로
    두면 한쪽만 고쳐져 갈라진다.

    변경 줄이 하나도 없으면 **False**. 이름만 바뀐 커밋은 내용 변경도 스탬프
    변경도 아니고, 여기서 True 로 접으면 기준선이 근거 없이 과거로 내려간다.
    """
    changed = [
        line
        for line in diff_text.splitlines()
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith("+++")
        and not line.startswith("---")
    ]
    if not changed:
        return False
    return all(_STAMP_LINE_RE.search(line[1:]) for line in changed)


def _commit_is_stamp_only(sha: str, rel: str, *, repo_root: Path) -> bool:
    """이 커밋이 그 파일에서 **`- 최종 수정일:` 줄만** 바꿨는가.

    TASK-2026-09-22-main-004. 이 구분이 없으면 이 함수는 이름과 docstring 이
    말하는 '마지막 **내용** 변경' 이 아니라 '마지막 커밋' 을 재게 된다. 실제로
    그랬다 — 릴리스의 `doc-headers-update` 가 스탬프만 바꾼 커밋을 만들고,
    그것이 기준선을 앞으로 밀어 **스탬프가 내용보다 최대 126일 앞선 문서 97개**
    가 판정을 통과하고 있었다 (2026-09-22 실측, `v1.9.2` 의 144파일 bump 등).

    판정 불가(diff 를 못 읽는다)는 **False** 로 떨어뜨린다 — 모르는 커밋을
    '스탬프 전용' 으로 접으면 기준선이 근거 없이 과거로 내려간다.
    """
    rc, out = _git(
        ["show", "--format=", "--unified=0", sha, "--", rel], repo_root=repo_root
    )
    if rc != 0:
        return False
    return _diff_is_stamp_only(out)


#: 변경된 줄이 스탬프 줄인지. `release_pipeline.DOC_HEADER_DATE_RE` 와 같은 모양을
#: 보지만 이쪽은 **diff 한 줄**을 받으므로 앵커가 다르다.
_STAMP_LINE_RE = re.compile(r"^\s*-\s*최종\s*수정일:\s*\d{4}-\d{2}-\d{2}\s*$")


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
