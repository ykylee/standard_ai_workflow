"""WATCHES 선언 메타 검증 — audit hook 채취와 판정 (ADR-028, v1.6.0+).

`--changed` 선택 실행의 유일한 위험 실패 모드는 **좁은 선언**이다: 검사가
실제로 읽는 경로가 `WATCHES` 선언 밖이면 그 검사는 조용히 skip 될 수 있다.
이 모듈은 그 선언을 실측으로 재는 두 조각을 제공한다:

1. **채취**: 러너가 검사 프로세스에 주입하는 sitecustomize 소스 —
   `sys.addaudithook` 으로 저장소 안 파일 접근을 기록한다. env 로 전파되므로
   검사가 띄우는 자식 **python** 프로세스까지 같은 훅이 걸린다 (비-python
   자식은 범위 밖 — ADR-028 한계 명시).
2. **판정**: 채취된 접근 − (선언 glob ∪ 자기 파일) 차집합. 비어 있지 않으면
   좁은 선언(red), 역방향(선언했으나 접근 0)은 넓은 선언(warn — 안전한 오차).

계약의 세부는 `core/test_impact_tiering_spec.md` §4, 결정 근거는 ADR-028.
"""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path

OUT_ENV = "META_WATCH_OUT"
REPO_ENV = "META_WATCH_REPO"
SITECUSTOMIZE_FILENAME = "sitecustomize.py"

#: 인프라 경로 — 입력 표면이 아니다 (ADR-028 결정 1). `.egg-info` 는 editable
#: 설치가 굽는 빌드 산출물 — 소스 입력이 아니다 (release_status 2종의 실측
#: 잔차 1건이 정확히 이것이었다, 2026-08-28).
INFRA_PARTS = (".git", ".venv", "node_modules", ".mypy_cache", ".pytest_cache")
INFRA_SUFFIXES = (".egg-info",)

#: 채취 대상 audit 이벤트. open 만으로는 scandir/stat 경유 접근을 놓친다
#: (ADR-028 대안 비교 — archive 검사 실측 201건의 다수가 그 경로였다).
AUDIT_EVENTS = ("open", "os.stat", "os.scandir", "os.listdir", "glob.glob", "os.walk")

# 검사 프로세스(와 그 python 자식)에 주입되는 소스. 실패는 전부 삼킨다 —
# 채취가 검사 자체를 깨뜨리면 메타 검증이 러너를 오염시키는 것이다.
SITECUSTOMIZE_SOURCE = '''\
"""meta-watch 채취 훅 (러너 주입 — workflow_kit.common.meta_watch 가 정본)."""
import os as _os
import sys as _sys

_out = _os.environ.get("META_WATCH_OUT")
_repo = _os.environ.get("META_WATCH_REPO")
if _out and _repo:
    _prefix = _repo + _os.sep
    _events = {"open", "os.stat", "os.scandir", "os.listdir", "glob.glob", "os.walk"}
    _infra = (".git", ".venv", "node_modules", ".mypy_cache", ".pytest_cache")
    _infra_sfx = (".egg-info",)
    _seen = set()

    def _hook(event, args):
        if event not in _events or not args:
            return
        try:
            p = _os.fspath(args[0])
            if isinstance(p, bytes):
                p = p.decode(errors="replace")
            if not _os.path.isabs(p):
                p = _os.path.join(_os.getcwd(), p)
            p = _os.path.normpath(p)
            if not p.startswith(_prefix):
                return
            rel = _os.path.relpath(p, _repo).replace(_os.sep, "/")
            parts = rel.split("/")
            if any(pt in _infra or pt.startswith(".venv")
                   or pt.endswith(_infra_sfx) for pt in parts):
                return
            if "__pycache__" in parts:
                # import 표면은 입력 표면이다 — pyc 를 소스 .py 로 역매핑한다
                # (ADR-028 결정 4). pyc 외의 __pycache__ 접근은 잡음.
                if not rel.endswith(".pyc"):
                    return
                i = parts.index("__pycache__")
                mod = parts[i + 1].split(".", 1)[0] if i + 1 < len(parts) else ""
                if not mod:
                    return
                rel = "/".join(parts[:i] + [mod + ".py"])
            if rel in _seen:
                return
            _seen.add(rel)
            with open(_out, "a", encoding="utf-8") as f:
                f.write(rel + "\\n")
        except Exception:
            pass

    _sys.addaudithook(_hook)
'''


def write_sitecustomize(dir_path: Path) -> Path:
    """주입 디렉터리에 sitecustomize 를 쓴다. 러너가 spawn 전에 한 번 부른다."""
    dir_path.mkdir(parents=True, exist_ok=True)
    target = dir_path / SITECUSTOMIZE_FILENAME
    target.write_text(SITECUSTOMIZE_SOURCE, encoding="utf-8")
    return target


def load_accesses(out_path: Path) -> set[str]:
    """채취 파일 → 저장소 상대 POSIX 경로 집합. 부재는 빈 집합 (채취 0건)."""
    try:
        text = out_path.read_text(encoding="utf-8")
    except OSError:
        return set()
    return {line.strip() for line in text.splitlines() if line.strip()}


def nested_checkout_prefix(rel: str, repo_root: Path, cache: dict[str, bool] | None = None) -> str | None:
    """``rel`` 이 저장소 안에 **중첩된 다른 체크아웃**(git worktree · 하위 clone) 안이면 그 접두.

    중첩 체크아웃은 자기 `.git`(worktree 는 파일, clone 은 디렉터리)을 갖는다. 그 아래
    파일은 이 체크아웃의 입력 표면이 아니라 **다른 작업 트리**다 — 대시보드가
    `git worktree list` 로 찾아 합산하는 state.json 이 그 예다. 저장소 **밖** worktree
    (`~/.codex/worktrees/…`)는 채취 접두에 안 걸려 조용한데, 저장소 **안**
    (`.claude/worktrees/*`, `.worktrees/*`)에 있으면 같은 읽기가 좁은 선언 red 가 됐다
    (TASK-2026-09-30-main-013) — 판정이 호스트에 어떤 worktree 가 있는지에 달렸다.
    """
    parts = rel.split("/")[:-1]
    for i in range(1, len(parts) + 1):
        prefix = "/".join(parts[:i])
        if cache is not None and prefix in cache:
            hit = cache[prefix]
        else:
            hit = (repo_root / prefix / ".git").exists()
            if cache is not None:
                cache[prefix] = hit
        if hit:
            return prefix
    return None


def judge(
    accessed: set[str],
    globs: tuple[str, ...],
    own_rel: str,
    repo_root: Path,
) -> tuple[list[str], list[str]]:
    """(uncovered — 좁은 선언 red 근거, unused_globs — 넓은 선언 warn 근거).

    판정 대상은 **지금 일반 파일로 실재하는 경로**만이다: import 기계와 glob 은
    존재하지 않는 후보 경로를 대량으로 stat 하고, 디렉터리 나열은 그 안 파일
    읽기가 따라올 때만 표면이 된다. 실재하지 않는 경로에의 의존(부재 검사)은
    이 판정의 범위 밖으로 문서화한다.

    **중첩 체크아웃 안의 경로도 범위 밖이다** (`nested_checkout_prefix`).
    """
    uncovered: list[str] = []
    hit_globs: set[str] = set()
    nested_cache: dict[str, bool] = {}
    for rel in sorted(accessed):
        if rel == own_rel:
            continue
        if nested_checkout_prefix(rel, repo_root, nested_cache) is not None:
            continue
        full = repo_root / rel
        if not full.is_file():
            continue
        matched = [g for g in globs if fnmatch.fnmatch(rel, g)]
        if matched:
            hit_globs.update(matched)
        else:
            uncovered.append(rel)
    unused = [g for g in globs if g not in hit_globs]
    return uncovered, unused
