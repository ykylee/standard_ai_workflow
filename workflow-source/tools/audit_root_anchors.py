#!/usr/bin/env python3
"""기준을 잡는 자리를 **전수 조사**한다 — 경로 축 + branch 축 (v1.0.8).

## 왜 이 도구가 있는가

§2.47(린터) · §2.49(doctor) · §2.50(branch 해석기) · §2.51(dashboard)은 **같은 결함
네 번**이었다: *어떤 기준으로 재는지를 모듈 자신의 위치에서 유도하고, 그 사실을 말하지
않는다.* 네 번째까지 오는 동안 찾는 방법은 매번 "이 모양이 또 어디 있나" 를 손으로
세는 것이었고, §2.50 에서 한 번은 AST 로 전수 조사했지만 **그 스크립트를 저장소에
남기지 않았다**. 그래서 §2.51 은 다시 손으로 찾았다.

이 도구는 그 조사를 저장소에 고정한다. 손으로 세지 않는다.

## 무엇을 판정하는가 (네 규칙)

- **R1 `anchor_outside_workspace`** — 모듈 위치에서 유도한 기준이 **저장소 밖**에
  착지한다. §2.49 의 doctor 가 이 모양이었다(저장소 루트의 두 단계 위).
- **R2 `module_anchor_as_default`** — workspace 성격의 인자가 미지정일 때 **모듈 위치**로
  떨어진다. §2.51 의 `dashboard_data._repo_root` 가 이 모양이었다 — 이 저장소는 editable
  install 이라 *우연히* 맞았고, 설치본에서는 `<venv>/lib/python3.13` 이 나왔다.
  R1 이 못 잡는 이유가 여기 있다: **착지가 저장소 안이어도 틀릴 수 있다.**
- **R3 `branch_from_module_repo`** — workspace/profile 로 파라미터화된 함수가 branch 를
  `get_current_branch()`(= *이 모듈이 속한* 저장소)에서 얻는다. §2.50 의
  `workflow_branch_dir` 가 이 모양이었다. **경로만 기준이 아니다 — branch 도 경로를 고른다.**
- **R4 `stale_ledger_entry`** — 아래 원장에 선언돼 있는데 코드에는 없다. 원장이 썩으면
  다음 사람은 이미 사라진 예외를 사실로 읽는다.

## 원장(ledger)이 있는 이유

R1~R3 에 걸리는 것이 전부 결함은 아니다. `<repo>/workflow-source/` 배치를 가정하는
`server/*` 는 `pyproject.toml` 이 "나머지는 저장소 디렉터리 레이아웃으로 소비한다" 고
적은 **선언된 설계**다. 그런 것은 지우지 않고 **이유와 함께 선언**한다 — 선언되지 않은
것만 결함이다. 원장의 key 는 `(rule, path, symbol)` 이라 줄이 밀려도 안 깨진다.

## 이 도구 자신의 기준

자기가 감사하는 함정에 자기가 빠지지 않도록, 기준 경로는 **명시 인자 → cwd** 두 갈래만
두고 `scan_root_source` 로 어느 쪽이었는지 밝힌다 (모듈 위치에서 유도하지 않는다).

사용:

    python3 workflow-source/tools/audit_root_anchors.py            # 사람용 요약
    python3 workflow-source/tools/audit_root_anchors.py --json     # 기계용
    python3 workflow-source/tools/audit_root_anchors.py --all      # 인벤토리 전량

Cross-ref: releases/Beta-v1.0.0.md §2.47 / §2.49 / §2.50 / §2.51.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCAN_SOURCE_ARGUMENT = "argument"
SCAN_SOURCE_CWD = "cwd"

#: 조사 대상 트리 (scan_root 기준 상대 경로). 없으면 조용히 건너뛰지 않고 보고한다.
SCAN_DIRS: tuple[str, ...] = (
    "workflow-source/workflow_kit",
    "workflow-source/tools",
    "workflow-source/tests",
    "workflow-source/scripts",
    "workflow-source/mcp_servers",
    "workflow-source/extensions",
    "workflow-source/harnesses",
    "scripts",
)

#: 이것이 없으면 기준 경로가 틀린 것이다. **없는데 "미선언 0건" 이라고 말하면 안 된다** —
#: 조사 0건은 결함 0건이 아니다 (실행 못 한 검사는 통과가 아니다).
REQUIRED_SCAN_DIRS: tuple[str, ...] = ("workflow-source/workflow_kit",)

#: 생성물/캐시/가상환경 — 소스가 아니다.
EXCLUDED_PARTS: frozenset[str] = frozenset(
    {"build", "dist", "site", "__pycache__", ".venv", "node_modules", ".git",
     "standard_ai_workflow.egg-info"}
)

#: workspace 루트를 담는 인자 이름. 이 이름의 인자가 미지정일 때 무엇으로 떨어지는지가 R2.
WORKSPACE_PARAM_NAMES: frozenset[str] = frozenset(
    {"workspace_root", "project_root", "repo_root", "workspace", "root_dir", "project_dir"}
)

#: workspace 를 *가리키는* 인자 (profile 경로는 workspace 를 역산할 수 있다). R3 대상.
WORKSPACE_BEARING_PARAM_NAMES: frozenset[str] = WORKSPACE_PARAM_NAMES | {
    "project_profile_path", "profile_path", "profile", "active_dir",
}

#: 모듈 위치에서 branch 를 얻는 함수 — workspace 를 받는 자리에서 쓰면 R3.
MODULE_BRANCH_FUNCS: frozenset[str] = frozenset({"get_current_branch"})


# ---------------------------------------------------------------------------
# 선언된 예외 원장 (single source — 이 도구와 check_root_anchor_audit 가 같이 읽는다)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LedgerEntry:
    rule: str
    path: str
    symbol: str
    reason: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.rule, self.path, self.symbol)


ROOT_ANCHOR_LEDGER: tuple[LedgerEntry, ...] = (
    LedgerEntry(
        rule="branch_from_module_repo",
        path="workflow-source/workflow_kit/common/paths.py",
        symbol="path_in_active",
        reason=(
            "`active_dir` 만 받고 workspace 를 역산하지 않는 것이 의도다 — active dir 에서 "
            "workspace 를 되짚으면 layout 분기(docs/ 배치)를 다시 추측하게 된다. workspace 를 "
            "아는 caller 는 `state_path_for_workspace` 를 쓴다. (§2.50 에서 남긴 결정)"
        ),
    ),
    LedgerEntry(
        rule="branch_from_module_repo",
        path="workflow-source/workflow_kit/common/paths.py",
        symbol="branch_for_workspace",
        reason=(
            "workspace 가 git 저장소가 아닐 때(temp fixture 등) 모듈 저장소 기준으로 "
            "되돌아가는 **선언된 fallback**이다 — 이 함수가 R3 규칙 자체의 정본이다."
        ),
    ),
)

LEDGER_BY_KEY: dict[tuple[str, str, str], LedgerEntry] = {e.key: e for e in ROOT_ANCHOR_LEDGER}


# ---------------------------------------------------------------------------
# 조사
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    rule: str
    path: str
    line: int
    symbol: str
    detail: str

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.rule, self.path, self.symbol)

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule": self.rule, "path": self.path, "line": self.line,
            "symbol": self.symbol, "detail": self.detail,
        }


@dataclass
class Inventory:
    """조사가 *무엇을 봤는지*. 결함 0건과 **조사 0건**은 다른 사실이다."""

    scanned_files: int = 0
    unparsable_files: list[str] = field(default_factory=list)
    missing_dirs: list[str] = field(default_factory=list)
    module_anchors: int = 0
    cwd_anchors: int = 0
    deep_parent_chains: int = 0
    module_branch_calls: int = 0
    #: 각 규칙이 *들여다본* 함수 수. 결함 0건과 **볼 자리가 0건**은 다른 사실이다 —
    #: 인자 이름 목록이 코드와 갈라지면 규칙은 깨지지 않고 조용히 무력화된다.
    r2_candidate_functions: int = 0
    r3_candidate_functions: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "scanned_files": self.scanned_files,
            "unparsable_files": self.unparsable_files,
            "missing_dirs": self.missing_dirs,
            "module_anchors": self.module_anchors,
            "cwd_anchors": self.cwd_anchors,
            "deep_parent_chains": self.deep_parent_chains,
            "module_branch_calls": self.module_branch_calls,
            "r2_candidate_functions": self.r2_candidate_functions,
            "r3_candidate_functions": self.r3_candidate_functions,
        }


def resolve_scan_root(raw: Path | str | None) -> tuple[Path, str]:
    """기준 경로와 **그 출처**. 모듈 위치에서 유도하지 않는다 (§2.51 과 같은 규칙)."""
    if raw is None:
        return Path.cwd().resolve(), SCAN_SOURCE_CWD
    return Path(raw).resolve(), SCAN_SOURCE_ARGUMENT


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_PARTS for part in path.parts)


def iter_source_files(scan_root: Path, inventory: Inventory) -> list[Path]:
    files: list[Path] = []
    for rel in SCAN_DIRS:
        base = scan_root / rel
        if not base.is_dir():
            inventory.missing_dirs.append(rel)
            continue
        for py in sorted(base.rglob("*.py")):
            if _is_excluded(py.relative_to(scan_root)):
                continue
            files.append(py)
    root_main = scan_root / "main.py"
    if root_main.is_file():
        files.append(root_main)
    return files


def _dunder_file_depth(node: ast.AST) -> int | None:
    """`Path(__file__)` 에서 시작하는 상승 연쇄의 **깊이**. 아니면 None.

    `Path(__file__).resolve().parents[2]` → 2, `Path(__file__).parent.parent` → 2,
    `Path(__file__).resolve()` → 0.
    """
    depth = 0
    cur: ast.AST = node
    while True:
        if isinstance(cur, ast.Subscript) and isinstance(cur.value, ast.Attribute) \
                and cur.value.attr == "parents":
            index = cur.slice
            if not (isinstance(index, ast.Constant) and isinstance(index.value, int)):
                return None  # 동적 인덱스는 정적으로 못 센다 — 조용히 0 으로 세지 않는다.
            depth += index.value
            cur = cur.value.value
            continue
        if isinstance(cur, ast.Attribute) and cur.attr == "parent":
            depth += 1
            cur = cur.value
            continue
        if isinstance(cur, ast.Attribute) and cur.attr in {"resolve", "absolute"}:
            cur = cur.value
            continue
        if isinstance(cur, ast.Call):
            # `Path(__file__)` / `os.path.dirname(__file__)` 처럼 **인자**가 뿌리인 형태와
            # `x.resolve()` 처럼 **수신자**가 뿌리인 형태를 갈라 본다. 인자 쪽을 안 보면
            # 가장 흔한 `Path(__file__)` 을 통째로 놓친다.
            if cur.args:
                cur = cur.args[0]
            else:
                cur = cur.func
            continue
        break

    if isinstance(cur, ast.Name) and cur.id == "__file__":
        return depth
    return None


def _cwd_depth(node: ast.AST) -> int | None:
    """`Path.cwd()` 에서 시작하는 연쇄인가."""
    cur: ast.AST = node
    while True:
        if isinstance(cur, ast.Subscript) and isinstance(cur.value, ast.Attribute) \
                and cur.value.attr == "parents":
            cur = cur.value.value
            continue
        if isinstance(cur, ast.Attribute) and cur.attr in {"parent", "resolve", "absolute"}:
            cur = cur.value
            continue
        if isinstance(cur, ast.Call):
            cur = cur.func
            continue
        break
    return 0 if isinstance(cur, ast.Attribute) and cur.attr == "cwd" else None


def _enclosing_symbol(tree: ast.AST, target: ast.AST) -> str:
    """`target` 을 담고 있는 최내곽 함수/클래스 이름. 없으면 `<module>`."""
    best = "<module>"
    best_span = None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        start = node.lineno
        end = getattr(node, "end_lineno", None) or start
        tgt = getattr(target, "lineno", None)
        if tgt is None or not (start <= tgt <= end):
            continue
        span = end - start
        if best_span is None or span < best_span:
            best, best_span = node.name, span
    return best


def _workspace_params(fn: ast.FunctionDef | ast.AsyncFunctionDef,
                      names: frozenset[str]) -> list[str]:
    args = fn.args
    all_args = [*args.posonlyargs, *args.args, *args.kwonlyargs]
    return [a.arg for a in all_args if a.arg in names]


def _optional_workspace_params(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """workspace 성격이면서 **미지정 가능**한 인자.

    "미지정 가능" 은 두 형태다 — 기본값이 `None` 이거나, 型이 `None` 을 받는다
    (`Path | None`, `Optional[Path]`). **후자를 빼면 §2.51 을 놓친다**:
    `resolve_workspace_root(workspace_root: Path | str | None)` 은 기본값이 없고
    型으로만 미지정을 받았는데, 그 미지정 분기가 바로 모듈 위치로 떨어지던 자리였다.
    """
    args = fn.args
    positional = [*args.posonlyargs, *args.args]
    pairs: list[tuple[ast.arg, ast.expr | None]] = []
    pad = len(positional) - len(args.defaults)
    for i, a in enumerate(positional):
        pairs.append((a, args.defaults[i - pad] if i >= pad else None))
    for a, d in zip(args.kwonlyargs, args.kw_defaults):
        pairs.append((a, d))

    out = []
    for arg, default in pairs:
        if arg.arg not in WORKSPACE_PARAM_NAMES:
            continue
        default_is_none = isinstance(default, ast.Constant) and default.value is None
        if default_is_none or _annotation_admits_none(arg.annotation):
            out.append(arg.arg)
    return out


def _annotation_admits_none(annotation: ast.expr | None) -> bool:
    """`X | None` / `Optional[X]` / `None` 을 받는 annotation 인가."""
    if annotation is None:
        return False
    if isinstance(annotation, ast.Constant):
        # 문자열 annotation (`"Path | None"`) — 파싱해서 다시 본다.
        if isinstance(annotation.value, str):
            try:
                inner = ast.parse(annotation.value, mode="eval").body
            except SyntaxError:
                return False
            return _annotation_admits_none(inner)
        return annotation.value is None
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return (_annotation_admits_none(annotation.left)
                or _annotation_admits_none(annotation.right))
    if isinstance(annotation, ast.Subscript):
        base = annotation.value
        name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
        if name == "Optional":
            return True
        if name == "Union":
            elts = annotation.slice.elts if isinstance(annotation.slice, ast.Tuple) else []
            return any(_annotation_admits_none(e) for e in elts)
    return False


def audit_file(py: Path, scan_root: Path, inventory: Inventory) -> list[Finding]:
    rel = py.relative_to(scan_root).as_posix()
    try:
        with warnings.catch_warnings():
            # 남의 소스에 있는 `\`` 같은 escape 경고는 이 조사의 관심사가 아니다.
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(py.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError) as exc:
        inventory.unparsable_files.append(f"{rel}: {type(exc).__name__}")
        return []

    findings: list[Finding] = []

    # --- 경로 축 -------------------------------------------------------------
    module_anchor_lines: list[tuple[int, int]] = []  # (line, depth)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Attribute, ast.Subscript)):
            continue
        depth = _dunder_file_depth(node)
        if depth is not None and depth > 0:
            # 부모 노드가 같은 연쇄의 일부이면 중복이므로, 최외곽만 센다.
            module_anchor_lines.append((node.lineno, depth))
            continue
        if _cwd_depth(node) is not None:
            inventory.cwd_anchors += 1

    module_anchor_lines = _outermost(tree, module_anchor_lines)
    inventory.module_anchors += len(module_anchor_lines)

    for line, depth in module_anchor_lines:
        landing = _landing(py, depth)
        if landing is None or not _within(landing, scan_root):
            findings.append(Finding(
                rule="anchor_outside_workspace", path=rel, line=line,
                symbol=_symbol_at(tree, line),
                detail=(f"parents[{depth}] → {landing} (저장소 밖). "
                        f"모듈이 옮겨지면 조용히 다른 곳을 잰다."),
            ))

    # --- 함수 단위 축 --------------------------------------------------------
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body_nodes = list(ast.walk(fn))

        # R2: workspace 인자가 미지정일 때 모듈 위치로 떨어진다.
        optional_ws = _optional_workspace_params(fn)
        if optional_ws:
            inventory.r2_candidate_functions += 1
            for node in body_nodes:
                if not isinstance(node, (ast.Attribute, ast.Subscript)):
                    continue
                depth = _dunder_file_depth(node)
                if depth is not None and depth > 0:
                    findings.append(Finding(
                        rule="module_anchor_as_default", path=rel, line=node.lineno,
                        symbol=fn.name,
                        detail=(f"인자 {optional_ws} 가 미지정이면 parents[{depth}] 로 떨어진다. "
                                f"설치본에서는 저장소가 아닌 곳을 잰다 — 명시 인자 → cwd 로 갈 것."),
                    ))
                    break

        # R3: workspace 를 받는데 branch 는 모듈 저장소에서 얻는다.
        if _workspace_params(fn, WORKSPACE_BEARING_PARAM_NAMES):
            inventory.r3_candidate_functions += 1
            for node in body_nodes:
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                        and node.func.id in MODULE_BRANCH_FUNCS:
                    inventory.module_branch_calls += 1
                    findings.append(Finding(
                        rule="branch_from_module_repo", path=rel, line=node.lineno,
                        symbol=fn.name,
                        detail=(f"{node.func.id}() 는 *이 모듈이 속한* 저장소를 본다. "
                                f"workspace 를 받는 자리는 branch_for_workspace() 를 쓴다."),
                    ))
                    break

    # 인벤토리: `__file__` 이 아닌 뿌리에서 두 단계 이상 거슬러 올라가는 연쇄.
    # 규칙은 아니고 **눈에 띄어야 하는 자리**다 — 기준을 값에서 역산하는 곳은 값의
    # 배치가 바뀌면 조용히 다른 곳을 잰다 (§2.50 이 손으로 세던 부류).
    inventory.deep_parent_chains += len(_deep_parent_chains(tree))

    return findings


def _deep_parent_chains(tree: ast.AST) -> list[int]:
    """`__file__` 유래가 아닌 depth>=2 상승 연쇄의 줄 번호 (최외곽만)."""
    hits: dict[int, int] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Attribute, ast.Subscript)):
            continue
        if _dunder_file_depth(node) is not None:
            continue  # 모듈 유도는 별도 축에서 이미 센다
        depth = _generic_ascent_depth(node)
        if depth >= 2:
            hits[node.lineno] = max(hits.get(node.lineno, 0), depth)
    return sorted(hits)


def _generic_ascent_depth(node: ast.AST) -> int:
    """뿌리를 가리지 않고 `.parent` / `.parents[n]` 상승 단계를 센다."""
    depth = 0
    cur: ast.AST = node
    while True:
        if isinstance(cur, ast.Subscript) and isinstance(cur.value, ast.Attribute) \
                and cur.value.attr == "parents":
            index = cur.slice
            if not (isinstance(index, ast.Constant) and isinstance(index.value, int)):
                return 0
            depth += index.value
            cur = cur.value.value
            continue
        if isinstance(cur, ast.Attribute) and cur.attr == "parent":
            depth += 1
            cur = cur.value
            continue
        if isinstance(cur, ast.Attribute) and cur.attr in {"resolve", "absolute"}:
            cur = cur.value
            continue
        if isinstance(cur, ast.Call):
            cur = cur.func
            continue
        break
    return depth


def _outermost(tree: ast.AST, hits: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """같은 줄에 중첩으로 잡힌 연쇄는 **가장 깊은 것 하나**만 남긴다."""
    best: dict[int, int] = {}
    for line, depth in hits:
        best[line] = max(best.get(line, 0), depth)
    return sorted(best.items())


def _landing(py: Path, depth: int) -> Path | None:
    parents = py.resolve().parents
    return parents[depth - 1] if depth - 1 < len(parents) else None


def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _symbol_at(tree: ast.AST, line: int) -> str:
    class _Probe:
        lineno = line
    return _enclosing_symbol(tree, _Probe())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 집계 / 출력
# ---------------------------------------------------------------------------

def run_audit(scan_root: Path | str | None = None) -> dict[str, Any]:
    root, source = resolve_scan_root(scan_root)
    inventory = Inventory()
    files = iter_source_files(root, inventory)
    inventory.scanned_files = len(files)

    findings: list[Finding] = []
    for py in files:
        findings.extend(audit_file(py, root, inventory))

    missing_required = [d for d in REQUIRED_SCAN_DIRS if d in inventory.missing_dirs]
    scan_ok = not missing_required and inventory.scanned_files > 0

    seen_keys = {f.key for f in findings}
    undeclared = [f for f in findings if f.key not in LEDGER_BY_KEY]
    declared = [f for f in findings if f.key in LEDGER_BY_KEY]
    stale = [e for e in ROOT_ANCHOR_LEDGER if e.key not in seen_keys]

    return {
        "scan_root": str(root),
        "scan_root_source": source,
        "inventory": inventory.as_dict(),
        "findings": [f.as_dict() for f in findings],
        "undeclared": [f.as_dict() for f in undeclared],
        "declared": [
            {**f.as_dict(), "reason": LEDGER_BY_KEY[f.key].reason} for f in declared
        ],
        "stale_ledger": [
            {"rule": e.rule, "path": e.path, "symbol": e.symbol, "reason": e.reason}
            for e in stale
        ],
        # 두 판정을 갈라 둔다. fixture 트리에서 조사하면 원장 항목은 전부 잔재로 보이므로,
        # 되주입 검증은 `undeclared_ok` 만 봐야 한다.
        "undeclared_ok": not undeclared,
        "ledger_ok": not stale,
        "scan_ok": scan_ok,
        "missing_required_dirs": missing_required,
        "ok": scan_ok and not undeclared and not stale,
    }


def _print_human(result: dict[str, Any], show_all: bool) -> None:
    inv = result["inventory"]
    print("=== audit_root_anchors (v1.0.8) ===")
    print(f"기준 경로: {result['scan_root']}  (출처: {result['scan_root_source']})")
    print(f"조사: {inv['scanned_files']} file — "
          f"모듈 유도 기준 {inv['module_anchors']} / cwd {inv['cwd_anchors']} / "
          f"기타 상승 연쇄(depth>=2) {inv['deep_parent_chains']} / "
          f"모듈 branch 호출 {inv['module_branch_calls']}")
    print(f"      규칙이 들여다본 함수: R2 {inv['r2_candidate_functions']} / "
          f"R3 {inv['r3_candidate_functions']}")
    if not result["scan_ok"]:
        print(f"\n  FAIL: 기준 경로가 틀렸다 — 필수 대상 부재 {result['missing_required_dirs']}, "
              f"조사 {inv['scanned_files']} file.")
        print("        조사 0건은 결함 0건이 아니다. --repo-root 로 저장소 루트를 줄 것.")
    elif inv["missing_dirs"]:
        print(f"  [warn] 조사 대상인데 없는 디렉터리: {inv['missing_dirs']}")
    if inv["unparsable_files"]:
        print(f"  [warn] 파싱 실패 {len(inv['unparsable_files'])}건: "
              f"{inv['unparsable_files'][:5]}")

    if result["undeclared"]:
        print(f"\n미선언 {len(result['undeclared'])}건 — 고치거나 원장에 이유와 함께 선언할 것:")
        for f in result["undeclared"]:
            print(f"  FAIL [{f['rule']}] {f['path']}:{f['line']} ({f['symbol']})")
            print(f"       {f['detail']}")
    else:
        print("\n미선언 0건")

    if result["stale_ledger"]:
        print(f"\n원장 잔재 {len(result['stale_ledger'])}건 — 코드에 없다. 원장에서 지울 것:")
        for e in result["stale_ledger"]:
            print(f"  FAIL [{e['rule']}] {e['path']} ({e['symbol']})")

    if show_all or result["declared"]:
        print(f"\n선언된 예외 {len(result['declared'])}건:")
        for f in result["declared"]:
            print(f"  [ok] [{f['rule']}] {f['path']}:{f['line']} ({f['symbol']})")
            print(f"       이유: {f['reason']}")

    print(f"\n결과: {'OK' if result['ok'] else 'FAIL'}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__ and __doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=None,
                        help="조사 기준 경로 (기본: cwd — 모듈 위치에서 유도하지 않는다)")
    parser.add_argument("--json", action="store_true", help="기계용 JSON 출력")
    parser.add_argument("--all", action="store_true", help="선언된 예외까지 전부 출력")
    args = parser.parse_args(argv)

    result = run_audit(args.repo_root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result, args.all)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
