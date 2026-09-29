"""문서가 **살아있는 문서**인가 **그 시점의 기록**인가 (TASK-2026-09-22-main-006).

## 왜 필요한가

저장소에는 성격이 다른 markdown 이 섞여 있다. 살아있는 문서는 지금의 사실을
말하므로 고쳐야 하고, 기록은 *그 시점의 사실* 이므로 고치면 날조가 된다.
`check_smoke_count_claims`(2026-09-21)가 숫자 주장에 대해 그 구분을 먼저 세웠고,
2026-09-22 에 **스탬프** 에도 같은 구분이 필요해지면서 판정을 여기로 올렸다.

`tests/` 안에 두면 **읽는 쪽만** 알고 쓰는 쪽(`release_pipeline`)은 못 읽는다 —
바로 그 모양이 `TASK-2026-09-22-main-002`(거짓 스탬프 100건)의 원인이었다.

## 신호 넷 — 전부 파생이다

1. **기록 계층** — `memory_dir_for_workspace` 아래. 그 안은 그 시점의 기록이다.
2. **살아있다는 선언의 부재** — 살아있는 문서는 `- 상태:` 를 단다. wiki 루트
   안의 페이지는 SCHEMA 에 따라 frontmatter `status:` 로 대신 선언한다
   (`is_live_marked`, TASK-2026-09-29-main-010).
3. **발행된 릴리스 노트** — `releases/` 아래. `docs/RELEASE.md` 가 "발행된 노트를
   고치지 않는다" 를 규약으로 못박고 있고, 그 왕복이 71~74차 네 사이클 반복됐다.
4. **테스트 트리** — `tests/` 아래. 픽스처는 검사가 기대하는 입력이라, 밖에서
   고치면 검사가 *그 수정* 을 재게 된다.
5. **`.gitignore` 가 무시하는 경로** — 저장소가 "여기는 관리하지 않는다" 고 **선언**한
   자리다. 추적 파일이 그 안에 남아 있을 수 있는데(`ai-workflow/mcp_servers/` 가
   그렇다), 거기를 건드리면 `git add <배치>` 가 `paths are ignored` 로 죽는다 —
   2026-09-22 에 실제로 `check_release_wrapper_args` case 6 이 그것으로 red 였다.
   판정은 `git check-ignore --no-index` 에게 묻는다(`--no-index` 가 없으면 추적
   파일을 '무시 아님' 으로 답한다).

1·2 만으로는 스탬프에 부족했다 (2026-09-22 실측): `releases/prototype-v1-pre-release.md`
는 `- 상태:` 를 달고 있어 살아있는 문서로 분류됐고, `tests/devhub_temp_source/` 의
번들 사본도 마찬가지였다. 그래서 3·4 를 더했다 — 둘 다 **손 목록이 아니라** 저장소가
이미 가진 경로 상수에서 나온다.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

#: 살아있는 문서가 다는 문서 메타데이터 헤더. 발행된 노트와 날짜가 박힌 기록은
#: 이 헤더가 없다. 굵은 표기(`- **상태**:` · `- **상태: …**`)도 같은 헤더다 —
#: 추적 문서 103건이 그렇게 쓰는데 평문만 알아 그 전부를 '헤더 부재' 로 읽었다
#: (TASK-2026-09-29-main-010).
LIVE_MARKER_RE = re.compile(r"^-\s*(?:\*\*\s*)?상태\s*(?:\*\*\s*)?:", re.MULTILINE)

#: wiki `SCHEMA.md` 의 frontmatter `status:` 어휘 중 **현행**인 것. 나머지 둘
#: (`deprecated` · `superseded`)은 은퇴한 페이지라 동결로 둔다. 어휘 합집합이
#: SCHEMA 와 같은지는 `check_doc_stamp_rule` case 13 이 SCHEMA 를 읽어 강제한다.
WIKI_LIVE_STATUSES = frozenset({"active", "draft", "proposed", "accepted"})
WIKI_RETIRED_STATUSES = frozenset({"deprecated", "superseded"})

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_STATUS_FIELD_RE = re.compile(r"^status:\s*(\S+)\s*$", re.MULTILINE)


def wiki_frontmatter_status(text: str) -> str | None:
    """frontmatter 의 `status:` 값. frontmatter 나 필드가 없으면 None.

    블록을 먼저 잘라 그 안에서만 찾는다 — 본문의 `status:` 줄을 읽지 않게.
    """
    block = _FRONTMATTER_RE.match(text)
    if block is None:
        return None
    field = _STATUS_FIELD_RE.search(block.group(1))
    return field.group(1) if field else None


def is_live_marked(path: Path, text: str, *, repo_root: Path) -> bool:
    """문서가 스스로 '살아있다' 고 선언했는가 — 표식 두 가지.

    1. 문서 메타데이터 헤더의 `- 상태:` (굵은 표기 포함).
    2. **wiki 루트 안에서만**, frontmatter `status:` 가 현행 어휘. wiki 페이지는
       SCHEMA 가 상태를 frontmatter 로 선언하게 하므로 1 을 달지 않는다 — 그래서
       wiki 페이지 전부가 '헤더 부재 = 동결' 로 읽혀 스탬프가 뒤처져도 아무도 안
       봤다 (2026-09-29 실측 6건, 최대 67일). 루트 밖으로 넓히지 않는 이유:
       `docs/samples/okf-bundle-*` 는 wiki 페이지의 export **스냅샷**이라 사본의
       `status: active` 를 그대로 들고 있다.
    """
    if LIVE_MARKER_RE.search(text) is not None:
        return True
    from workflow_kit.common.paths import wiki_dir_for_workspace

    if not _under(path, wiki_dir_for_workspace(repo_root)):
        return False
    return wiki_frontmatter_status(text) in WIKI_LIVE_STATUSES


def _memory_root(repo_root: Path) -> Path:
    from workflow_kit.common.paths import memory_dir_for_workspace

    return memory_dir_for_workspace(repo_root)


def is_record_layer(path: Path, *, repo_root: Path) -> bool:
    """기록 계층 안인가 — 그 안의 주장은 그 시점의 사실이다."""
    try:
        path.resolve().relative_to(_memory_root(repo_root).resolve())
        return True
    except ValueError:
        return False


def _under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def _is_published_note(path: Path, *, repo_root: Path) -> bool:
    return _under(path, repo_root / "workflow-source" / "releases")


def is_frozen_claim_layer(path: Path, text: str, *, repo_root: Path) -> bool:
    """숫자 주장 판정이 쓰는 세 신호 (기록 계층 · 헤더 부재 · 발행된 노트).

    `check_smoke_count_claims` 가 이것을 읽는다 — 사본을 두지 않기 위해서다.

    wiki frontmatter `status:` 는 **여기서 읽지 않는다** (TASK-2026-09-29-main-010).
    그 값은 페이지가 *관리되는가* 이지 본문 수치가 *지금의 사실인가* 가 아니다 —
    `topics/*-2026-06-12` 처럼 제목에 버전·날짜를 박은 분석 페이지가 `active` 로
    그 시점의 '52개' 를 들고 있다. 스탬프(`is_frozen_document`)는 관리 여부를
    묻는 질문이라 그 신호를 쓴다.

    발행된 노트는 헤더 표기와 무관하게 동결이다 — 예전에는 `- **상태**:` 굵은
    표기를 헤더로 못 읽은 덕에 **우연히** 빠져 있었다.
    """
    return (
        is_record_layer(path, repo_root=repo_root)
        or LIVE_MARKER_RE.search(text) is None
        or _is_published_note(path, repo_root=repo_root)
    )


def is_frozen_document(path: Path, text: str, *, repo_root: Path) -> bool:
    """스탬프를 건드리면 안 되는 문서인가.

    신호: 기록 계층 · 살아있다는 선언의 부재(`is_live_marked` — wiki frontmatter
    포함) · 발행된 노트 · 테스트 트리 · `.gitignore`. 테스트 픽스처는 `- 상태:`
    를 달고 있어 헤더만으로는 살아있는 문서로 분류되는데, 그 스탬프를 바깥에서
    올리면 검사 입력을 고치는 것이 된다.
    """
    if is_record_layer(path, repo_root=repo_root):
        return True
    if not is_live_marked(path, text, repo_root=repo_root):
        return True
    if _is_published_note(path, repo_root=repo_root):
        return True
    if _under(path, repo_root / "workflow-source" / "tests"):
        return True
    return is_gitignored(path, repo_root=repo_root)


def is_gitignored(path: Path, *, repo_root: Path) -> bool:
    """`.gitignore` 가 무시하는 경로인가 — 저장소가 관리 밖이라 선언한 자리다.

    `--no-index` 가 필요하다: 그것이 없으면 git 은 **추적되는** 파일을 '무시 아님'
    으로 답한다. 실제로 `ai-workflow/mcp_servers/` 는 무시 선언이 있는데 그 안에
    추적 파일이 남아 있어, 그 답 차이가 판정을 뒤집었다.
    """
    try:
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return False
    try:
        done = subprocess.run(
            ["git", "-C", str(repo_root), "check-ignore", "--no-index", "-q", "--", rel],
            capture_output=True, text=True,
        )
    except OSError:
        return False          # 못 물었으면 무시로 접지 않는다 — 모름 ≠ 동결
    return done.returncode == 0
