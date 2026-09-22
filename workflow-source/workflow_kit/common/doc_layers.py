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
2. **문서 메타데이터 헤더 부재** — 살아있는 문서는 `- 상태:` 를 단다.
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
#: 이 헤더가 없다.
LIVE_MARKER_RE = re.compile(r"^-\s*상태:", re.MULTILINE)


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


def is_frozen_claim_layer(path: Path, text: str, *, repo_root: Path) -> bool:
    """숫자 주장 판정이 쓰는 두 신호 (기록 계층 · 헤더 부재).

    `check_smoke_count_claims` 가 이것을 읽는다 — 사본을 두지 않기 위해서다.
    """
    return is_record_layer(path, repo_root=repo_root) or (
        LIVE_MARKER_RE.search(text) is None
    )


def is_frozen_document(path: Path, text: str, *, repo_root: Path) -> bool:
    """스탬프를 건드리면 안 되는 문서인가 — 위 네 신호의 합.

    숫자 주장보다 넓다. 발행된 노트와 테스트 픽스처는 `- 상태:` 를 달고 있어
    두 신호만으로는 살아있는 문서로 분류되는데, 그 스탬프를 바깥에서 올리면
    각각 역사와 검사 입력을 고치는 것이 된다.
    """
    if is_frozen_claim_layer(path, text, repo_root=repo_root):
        return True
    source_root = repo_root / "workflow-source"
    if _under(path, source_root / "releases") or _under(path, source_root / "tests"):
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
