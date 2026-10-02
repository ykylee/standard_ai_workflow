#!/usr/bin/env python3
"""문서 frontmatter 의 `- 최종 수정일:` 스탬프를 **git 에서** 판정한다.

wiki 페이지(`ai-workflow/wiki/`)의 스탬프는 SCHEMA 가 정한 frontmatter
`updated:` 다 — 어느 필드를 읽고 쓰는지는 `read_stamp` / `write_stamp` 하나가
정한다 (TASK-2026-09-29-main-012).

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
from typing import Callable

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
        env=env, encoding="utf-8", errors="replace",
    )
    return completed.returncode, completed.stdout.strip()


def dirty_paths(repo_root: Path) -> frozenset[str] | None:
    """워킹 트리에서 변경된 경로 전부 (repo-relative posix). 실패하면 ``None``.

    TASK-2026-09-22-main-006. 문서마다 `git status -- <file>` 를 부르면 호출이
    문서 수만큼 늘어난다 — 범위를 242개로 넓히자 그것이 `release --dry-run` 을
    10s 예산 밖으로 밀어 남의 검사를 깨뜨렸다 (실측 8.0s 중 대부분).
    **캐시가 아니라 호출자가 넘기는 명시 인자** 로 만든 이유: 한 프로세스가 트리를
    바꿔 가며 여러 번 재는 경우(검사 fixture)에 캐시는 조용히 낡는다.
    """
    rc, out = _git(["status", "--porcelain"], repo_root=repo_root)
    if rc != 0:
        return None
    changed: set[str] = set()
    for line in out.splitlines():
        entry = line[3:] if len(line) > 3 else ""
        if " -> " in entry:            # rename: 새 경로를 본다
            entry = entry.split(" -> ", 1)[1]
        entry = entry.strip().strip('"')
        if entry:
            changed.add(entry)
    return frozenset(changed)


def last_content_change_date(
    path: Path, *, repo_root: Path, dirty: frozenset[str] | None = None
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

    if dirty is None:
        rc, listed = _git(["status", "--porcelain", "--", rel], repo_root=repo_root)
        if rc != 0:
            return None, f"git status 실패 (rc={rc}) — git 저장소 안에서 돌려야 한다", 0
        is_dirty = bool(listed)
        note = listed.split(chr(10))[0] if listed else ""
    else:
        is_dirty = rel in dirty
        note = rel
    # wiki 여부는 `updated:` 줄이 실제로 바뀌었을 때만 묻는다 — 묻는 순간
    # `workflow_kit` 패키지 전체가 로드되고, wiki 와 무관한 검사(인덱스 문서 스탬프)가
    # 그것을 자기 WATCHES 밖 접근으로 보고한다 (TASK-2026-09-29-main-012).
    def wiki() -> bool:
        return is_wiki_page(path, repo_root=repo_root)

    if is_dirty and not _worktree_change_is_stamp_only(rel, repo_root=repo_root, wiki=wiki):
        return (
            _today_utc(),
            f"워킹 트리에 미커밋 변경이 있다 ({note})",
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
        if _diff_is_stamp_only(body, wiki=wiki):
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


def _worktree_change_is_stamp_only(
    rel: str, *, repo_root: Path, wiki: bool | Callable[[], bool] = False,
) -> bool:
    """미커밋 변경이 그 파일에서 **스탬프 줄만** 바꿨는가.

    커밋 쪽(`_commit_is_stamp_only`)과 같은 판정을 워킹 트리에 적용한다. 판정
    불가는 **False** — 모르는 변경을 '스탬프 전용' 으로 접으면 유예 0 규율이
    풀린다.
    """
    rc, out = _git(["diff", "--unified=0", "--", rel], repo_root=repo_root)
    if rc != 0:
        return False
    return _diff_is_stamp_only(out, wiki=wiki)


def _diff_is_stamp_only(diff_text: str, *, wiki: bool | Callable[[], bool] = False) -> bool:
    """unified diff 본문이 **스탬프 줄만** 바꿨는가.

    커밋 쪽과 워킹트리 쪽이 **같은 판정**을 쓰도록 텍스트만 받는다 — 두 벌로
    두면 한쪽만 고쳐져 갈라진다.

    `wiki` 면 frontmatter `updated:` 줄도 스탬프 줄이다 (`is_wiki_page`). 옛
    `- 최종 수정일:` 줄은 wiki 에서도 스탬프 줄로 센다 — 그것을 걷어내는 커밋이
    내용 변경으로 읽히면 정리 자체가 사실 아닌 '오늘' 스탬프를 요구한다
    (TASK-2026-09-29-main-012).

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
    if all(_STAMP_LINE_RE.search(line[1:]) for line in changed):
        return True
    if not all(
        _STAMP_LINE_RE.search(line[1:]) or _WIKI_STAMP_LINE_RE.search(line[1:])
        for line in changed
    ):
        return False
    return bool(wiki() if callable(wiki) else wiki)


def _commit_is_stamp_only(
    sha: str, rel: str, *, repo_root: Path, wiki: bool | Callable[[], bool] = False,
) -> bool:
    """이 커밋이 그 파일에서 **스탬프 줄만** 바꿨는가.

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
    return _diff_is_stamp_only(out, wiki=wiki)


#: 변경된 줄이 스탬프 줄인지. `release_pipeline.DOC_HEADER_DATE_RE` 와 같은 모양을
#: 보지만 이쪽은 **diff 한 줄**을 받으므로 앵커가 다르다.
#:
#: 날짜 뒤 주석(`2026-07-16 (v0.14.0 …)`)도 스탬프 줄로 센다
#: (TASK-2026-09-29-main-007). 주석은 형식 위반이라 `stamp_format_violation` 이
#: 따로 잡는다 — 여기서 그것을 내용 줄로 세면 **주석을 지우는 정규화 자체가 내용
#: 변경**이 되어, 정규화한 문서가 사실이 아닌 '오늘' 스탬프를 요구받는다.
_STAMP_LINE_RE = re.compile(r"^\s*-\s*최종\s*수정일:\s*\d{4}-\d{2}-\d{2}(\s.*)?$")
#: wiki 페이지의 스탬프 줄 — frontmatter `updated:` (TASK-2026-09-29-main-012).
_WIKI_STAMP_LINE_RE = re.compile(r"^updated:\s*\d{4}-\d{2}-\d{2}\s*$")

#: 스탬프 **필드** 줄 — 값의 형식을 묻지 않고 필드가 있는지만 본다.
_STAMP_FIELD_RE = re.compile(r"^\s*-\s*최종\s*수정일:(.*)$", re.MULTILINE)
#: 판정 가능한 값: 날짜 하나, 뒤에 공백만.
_STAMP_VALUE_RE = re.compile(r"^\s*\d{4}-\d{2}-\d{2}\s*$")
#: 템플릿의 자리표시자 — 채워질 자리라 판정 대상이 아니다.
STAMP_PLACEHOLDER = "YYYY-MM-DD"


def stamp_format_violation(
    text: str, *, path: Path | None = None, repo_root: Path | None = None,
) -> str | None:
    """스탬프 필드가 있는데 **판정할 수 없는 형식**이면 그 설명, 아니면 ``None``.

    TASK-2026-09-29-main-007. 전수 검사(`check_doc_stamp_rule` case 10)와
    `doc-headers-update` 는 날짜 뒤가 줄 끝인 줄만 읽는다. 그래서 날짜 뒤에 주석을
    단 스탬프(`2026-07-16 (v0.14.0 신규 layout 정합)`)는 **판정 없이 건너뛰어졌다** —
    살아있는 문서 5건, 그중 3건은 실제로 뒤처져 있었다. 건너뜀은 통과가 아니므로
    필드가 있으면 형식부터 요구한다.

    `path`·`repo_root` 를 주면 wiki 페이지를 구별한다 (TASK-2026-09-29-main-012).
    wiki 의 정본 스탬프는 frontmatter `updated:` 이고, 거기에 `- 최종 수정일:` 이
    **또 있으면** 두 번째 스탬프라 위반이다 — 둘이 갈라진 채 게이트는 한쪽만 봤다.

    필드가 없는 문서는 ``None`` — 스탬프를 안 다는 문서가 정상적으로 있다.
    """
    header = _STAMP_FIELD_RE.search(text)
    if path is not None and repo_root is not None and is_wiki_page(path, repo_root=repo_root):
        if header is not None:
            return (
                "wiki 페이지에 `- 최종 수정일:` 이 있다 — wiki 의 스탬프는 frontmatter "
                "`updated:` 하나다 (SCHEMA). 두 번째 스탬프를 지운다."
            )
        value = _wiki_updated_value(text)
        if value is None or value == STAMP_PLACEHOLDER or _STAMP_VALUE_RE.match(value):
            return None
        return (
            f"frontmatter `updated:` 값이 날짜 하나가 아니다: {value!r} — 판정할 수 없다."
        )
    if header is None:
        return None
    value = header.group(1).strip()
    if value == STAMP_PLACEHOLDER or _STAMP_VALUE_RE.match(value):
        return None
    return (
        f"`- 최종 수정일:` 값이 날짜 하나가 아니다: {value!r} — 판정할 수 없다. "
        "날짜만 남기고 주석은 본문이나 커밋 메시지로 옮긴다."
    )


#: 문서 헤더 스탬프 — `- 최종 수정일: YYYY-MM-DD` 가 줄 끝까지. 읽기·쓰기가 이것 하나다.
HEADER_STAMP_RE = re.compile(
    r"^(-\s*최종\s*수정일:\s*)(\d{4}-\d{2}-\d{2})(\s*)$", re.MULTILINE
)
#: wiki 페이지의 스탬프 — frontmatter 블록 **안의** `updated: YYYY-MM-DD`.
_WIKI_UPDATED_RE = re.compile(r"^(updated:[ \t]*)(\d{4}-\d{2}-\d{2})([ \t]*)$", re.MULTILINE)
_WIKI_UPDATED_FIELD_RE = re.compile(r"^updated:(.*)$", re.MULTILINE)
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?\n)---\n", re.DOTALL)


def is_wiki_page(path: Path, *, repo_root: Path) -> bool:
    """wiki `SCHEMA.md` 가 관할하는 페이지인가 — 스탬프가 frontmatter `updated:` 인 자리.

    경계는 `doc_layers` 의 살아있음 판정과 같은 정본(`paths.wiki_dir_for_workspace`)
    이다. 루트 밖의 export 스냅샷(`docs/samples/okf-bundle-*`)은 wiki 페이지가 아니다.
    """
    from workflow_kit.common.paths import wiki_dir_for_workspace

    try:
        path.resolve().relative_to(wiki_dir_for_workspace(repo_root).resolve())
        return True
    except (ValueError, OSError):
        return False


def _wiki_updated_value(text: str) -> str | None:
    block = _FRONTMATTER_RE.match(text)
    if block is None:
        return None
    field = _WIKI_UPDATED_FIELD_RE.search(block.group(1))
    return field.group(1).strip() if field else None


def read_stamp(path: Path, text: str, *, repo_root: Path) -> str | None:
    """이 문서의 **판정 가능한** 스탬프 값. 없거나 형식이 틀리면 ``None``.

    wiki 페이지는 frontmatter `updated:`, 나머지는 `- 최종 수정일:` 이다
    (TASK-2026-09-29-main-012). 게이트(`check_doc_stamp_rule` case 10)와 쓰는 쪽
    (`doc-headers-update`)이 **같은 함수**로 읽는다 — 읽는 쪽만 wiki 를 알면 쓰는
    쪽이 영영 못 고치는 red 가 된다.
    """
    if is_wiki_page(path, repo_root=repo_root):
        block = _FRONTMATTER_RE.match(text)
        match = _WIKI_UPDATED_RE.search(block.group(1)) if block else None
    else:
        match = HEADER_STAMP_RE.search(text)
    return match.group(2) if match else None


def write_stamp(path: Path, text: str, stamp: str, *, repo_root: Path) -> str:
    """`read_stamp` 가 읽는 바로 그 필드를 `stamp` 로 바꾼 본문. 필드가 없으면 그대로."""
    if is_wiki_page(path, repo_root=repo_root):
        block = _FRONTMATTER_RE.match(text)
        if block is None:
            return text
        new_block = _WIKI_UPDATED_RE.sub(rf"\g<1>{stamp}\g<3>", block.group(1), count=1)
        return text[: block.start(1)] + new_block + text[block.end(1):]
    return HEADER_STAMP_RE.sub(rf"\g<1>{stamp}\g<3>", text)


def _minus_days(iso: str, days: int) -> str:
    return (date.fromisoformat(iso) - timedelta(days=days)).isoformat()


def check_frontmatter_stamp(
    path: Path, *, repo_root: Path, actual: str,
    dirty: frozenset[str] | None = None,
) -> tuple[bool, str]:
    """스탬프가 마지막 내용 변경일 (유예 포함) 이상인가. ``(ok, 설명)``.

    `dirty` 는 `dirty_paths()` 결과 — 여러 문서를 훑을 때 `git status` 를 한 번만
    부르려고 호출자가 넘긴다. 생략하면 문서마다 따로 묻는다(느리지만 항상 최신).
    """
    changed_at, reason, grace = last_content_change_date(
        path, repo_root=repo_root, dirty=dirty
    )
    if changed_at is None:
        return False, f"기대 스탬프를 판정할 수 없다 — {reason}"
    try:
        floor = _minus_days(changed_at, grace)
    except ValueError:
        return False, f"날짜 형식을 읽을 수 없다: {changed_at!r} ({reason})"
    def field() -> str:   # 실패 문장에만 쓴다 — 통과 경로에서 패키지를 로드하지 않게
        return (
            "frontmatter `updated:`" if is_wiki_page(path, repo_root=repo_root)
            else "`- 최종 수정일:`"
        )

    try:
        date.fromisoformat(actual)
    except ValueError:
        return False, f"{field()} 이 YYYY-MM-DD 가 아니다: {actual!r}"
    if actual < floor:
        return False, (
            f"스탬프가 문서의 마지막 내용 변경보다 뒤처졌다 — "
            f"stamp={actual} < {floor} (변경일 {changed_at} − 유예 {grace}일, {reason}). "
            f"`{path.name}` 의 {field()} 을 올리거나 "
            "`python -m workflow_kit release-pipeline doc-headers-update --apply` 를 돌린다."
        )
    return True, f"스탬프 {actual} >= {floor} (변경일 {changed_at}, {reason})"
