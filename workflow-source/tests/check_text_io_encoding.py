#!/usr/bin/env python3
"""텍스트 I/O 가 로캘 인코딩에 기대지 않는지 잰다 — Windows cp949 대응.

TASK-2026-10-02-main-006. 소유자 보고: Windows OpenCode 데스크톱에서 `wk` 가 cp949
인코딩 에러로 죽었다. Linux 재현은 `PYTHONIOENCODING=cp949 wk session-start` 다.
`—`(U+2014)를 출력하다 `UnicodeEncodeError` 로 exit 2 가 난다. 하네스가 `wk` 를
파이프로 부르면 Python 은 stdio 에 로캘 인코딩을 쓴다. 터미널에서 직접 돌리면 콘솔
API 를 타서 안 난다.

두 층으로 막는다:

1. **stdio** — `wk` 와 하네스가 `python -m` 으로 부르는 진입점이 시작 시
   `common/stdio.force_utf8_stdio()` 로 UTF-8 을 고정한다 (case 3 · 4 · 5).
2. **파일 · subprocess 텍스트 I/O** — 호출마다 `encoding=` 을 명시한다. 기본값은
   로캘을 따르고 UTF-8 mode 는 실행 중에 켤 수 없다 (case 1 · 2). 수리 전에는
   `-X warn_default_encoding` 으로 session-start 한 번에 13건이 났다. AST 전수는
   subprocess 108 · 파일 7 이었다.

Linux 호스트 로캘은 UTF-8 이라 기본값 사용이 여기서는 증상을 안 낸다. 그래서 실행
결과가 아니라 **호출 형태**를 잰다 (case 1). 실행 쪽은 `PYTHONIOENCODING=cp949` 로
Windows 의 stdio 조건을 그대로 만든다 (case 3 · 4).
"""
from __future__ import annotations

WATCHES = (
    "workflow-source/workflow_kit/*",
    # case 3 · 4 의 자식이 `import workflow_kit` 할 때 버전을 읽는다.
    "workflow-source/pyproject.toml",
)

import ast
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
PACKAGE_ROOT = SOURCE_ROOT / "workflow_kit"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

#: 하네스가 `python -m <module>` 으로 부르는 진입점 — `__main__` 블록이 stdio 를
#: 고정해야 한다. `read_only_mcp_sdk` 는 빠진다: `mcp` SDK 의 stdio transport 가
#: `sys.stdin.buffer` / `sys.stdout.buffer` 를 UTF-8 TextIOWrapper 로 직접 감싼다.
MAIN_ENTRY_MODULES = (
    "workflow_kit/workflow_kit_cli.py",
    "workflow_kit/server/read_only_jsonrpc.py",
    "workflow_kit/bootstrap_lib/__main__.py",
    "workflow_kit/plugin_payload.py",
)

_SUBPROCESS_FUNCS = frozenset({"run", "check_output", "Popen", "call", "check_call"})
#: `.open(...)` 이 파일 텍스트 open 이 아닌 모듈 수신자.
_NON_TEXT_OPEN_RECEIVERS = frozenset(
    {"os", "gzip", "zipfile", "tarfile", "webbrowser", "tempfile", "io", "codecs"}
)
#: cp949 에 없는 문자 — 재현에 쓴 `—` 와 상태 표시 `✅`, 그리고 한글(입력 왕복용).
_PROBE_TEXT = "— ✅ 한글"

_failures: list[str] = []
_passes: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def _is_text_mode(mode: ast.expr | None) -> bool:
    """mode 가 생략됐거나 'b' 없는 문자열 리터럴이면 텍스트 모드다."""
    if mode is None:
        return True
    return isinstance(mode, ast.Constant) and isinstance(mode.value, str) and "b" not in mode.value


def find_default_encoding_calls(tree: ast.AST) -> list[tuple[str, int]]:
    """로캘 기본 인코딩으로 떨어지는 텍스트 I/O 호출 (종류, 줄) 목록."""
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        keywords = {k.arg for k in node.keywords}
        # `**kwargs` 는 encoding 을 실어 나를 수 있어 판정하지 않는다.
        if "encoding" in keywords or None in keywords:
            continue
        func = node.func
        mode_kw = next((k.value for k in node.keywords if k.arg == "mode"), None)
        if isinstance(func, ast.Name) and func.id == "open":
            mode = node.args[1] if len(node.args) > 1 else mode_kw
            if _is_text_mode(mode):
                found.append(("open", node.lineno))
        elif isinstance(func, ast.Attribute):
            receiver = func.value
            receiver_name = receiver.id if isinstance(receiver, ast.Name) else ""
            if func.attr == "open" and receiver_name not in _NON_TEXT_OPEN_RECEIVERS:
                mode = node.args[0] if node.args else mode_kw
                if _is_text_mode(mode):
                    found.append(("Path.open", node.lineno))
            # 위치 인자는 encoding 이다 (Path.read_text(encoding) · write_text(data, encoding)).
            # importlib Distribution.read_text(filename) 도 위치 인자 1개라 같이 빠진다.
            elif func.attr == "read_text" and not node.args:
                found.append(("read_text", node.lineno))
            elif func.attr == "write_text" and len(node.args) < 2:
                found.append(("write_text", node.lineno))
            elif func.attr in _SUBPROCESS_FUNCS and receiver_name == "subprocess":
                if any(
                    k.arg in ("text", "universal_newlines")
                    and isinstance(k.value, ast.Constant) and k.value.value is True
                    for k in node.keywords
                ):
                    found.append((f"subprocess.{func.attr}", node.lineno))
    return found


def case_1_package_has_no_default_encoding_io() -> None:
    """workflow_kit 전수 — 로캘 기본 인코딩 텍스트 I/O 0건 (긍정 증거: 훑은 파일 수)."""
    sources = sorted(PACKAGE_ROOT.rglob("*.py"))
    hits: list[str] = []
    unparsed: list[str] = []
    for path in sources:
        rel = path.relative_to(SOURCE_ROOT).as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError) as exc:
            unparsed.append(f"{rel} ({type(exc).__name__})")
            continue
        hits.extend(f"{rel}:{line} {kind}" for kind, line in find_default_encoding_calls(tree))
    # 못 읽은 파일은 통과가 아니다 — 따로 세서 실패로 낸다.
    ok = not hits and not unparsed and len(sources) >= 100
    detail = f"{len(sources)} 파일 훑음"
    if hits:
        detail += f" · 기본 인코딩 {len(hits)}건: " + ", ".join(hits[:8])
    if unparsed:
        detail += f" · 파싱 실패 {len(unparsed)}건: " + ", ".join(unparsed[:4])
    _record("case 1 (workflow_kit 텍스트 I/O 가 전부 encoding 을 명시)", ok, detail)


def case_2_scanner_catches_each_form() -> None:
    """스캐너가 각 형태를 잡고, 명시형 · 바이너리형은 놓아준다 — case 1 의 0 이 맹목이 아니다."""
    flagged = {
        "open(p)": "open",
        "open(p, 'w')": "open",
        "open(p, mode='a')": "open",
        "p.open()": "Path.open",
        "p.open('r')": "Path.open",
        "p.read_text()": "read_text",
        "p.write_text(s)": "write_text",
        "subprocess.run(c, text=True)": "subprocess.run",
        "subprocess.check_output(c, universal_newlines=True)": "subprocess.check_output",
        "subprocess.Popen(c, stdout=PIPE, text=True)": "subprocess.Popen",
    }
    clean = (
        "open(p, 'rb')",
        "open(p, encoding='utf-8')",
        "p.open('wb')",
        "os.open(p, flags)",
        "gzip.open(p, 'wt')",
        "p.read_text('utf-8')",
        "p.read_text(encoding='utf-8')",
        "dist.read_text('direct_url.json')",
        "p.write_text(s, 'utf-8')",
        "p.write_text(s, encoding='utf-8')",
        "subprocess.run(c, text=True, encoding='utf-8')",
        "subprocess.run(c, capture_output=True)",
        "subprocess.run(c, **kw)",
    )
    missed = [src for src, kind in flagged.items()
              if [k for k, _ in find_default_encoding_calls(ast.parse(src))] != [kind]]
    false_hits = [src for src in clean if find_default_encoding_calls(ast.parse(src))]
    _record(
        "case 2 (스캐너가 형태 10종을 잡고 13종을 놓아준다)",
        not missed and not false_hits,
        f"놓침 {missed} · 오판 {false_hits}" if (missed or false_hits) else "",
    )


def _run_cp949(code: str, stdin: bytes) -> subprocess.CompletedProcess[bytes]:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp949"
    env.pop("PYTHONUTF8", None)
    env["PYTHONPATH"] = str(SOURCE_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-c", code], input=stdin, capture_output=True,
        env=env, timeout=60, check=False,
    )


def case_3_force_utf8_stdio_round_trips_under_cp949() -> None:
    """cp949 stdio 에서 — 대조군은 죽고, `force_utf8_stdio()` 뒤에는 UTF-8 로 왕복한다."""
    payload = _PROBE_TEXT.encode("utf-8")
    echo = "import sys\n{prep}sys.stdout.write(sys.stdin.read())\n"
    control = _run_cp949(echo.format(prep=""), payload)
    fixed = _run_cp949(
        echo.format(prep="from workflow_kit.common.stdio import force_utf8_stdio\n"
                         "force_utf8_stdio()\n"),
        payload,
    )
    # 대조군이 통과하면 이 환경이 Windows 조건을 못 만든 것 — 수리 쪽 green 은 무의미하다.
    control_reproduces = control.returncode != 0 or control.stdout != payload
    ok = control_reproduces and fixed.returncode == 0 and fixed.stdout == payload
    detail = (
        f"대조군 rc={control.returncode} · 수리 rc={fixed.returncode} "
        f"stdout={fixed.stdout[:40]!r}"
    )
    if not ok and fixed.stderr:
        detail += f" · stderr={fixed.stderr.decode('utf-8', 'replace')[-200:]}"
    _record("case 3 (cp949 stdio 에서 force_utf8_stdio 가 UTF-8 왕복)", ok, detail)


def case_4_wk_main_fixes_stdio_before_dispatch() -> None:
    """`wk` console_script 진입점이 dispatch **전에** stdio 를 고정한다 — 실물 wk_main 으로."""
    code = (
        "import sys\n"
        "import workflow_kit.workflow_kit_cli as cli\n"
        "def _dispatch(argv):\n"
        f"    print({_PROBE_TEXT!r})\n"
        "    return 0\n"
        "cli.run_workflow_kit_cli = _dispatch\n"
        "sys.argv = ['wk']\n"
        "raise SystemExit(cli.wk_main())\n"
    )
    result = _run_cp949(code, b"")
    expected = (_PROBE_TEXT + "\n").encode("utf-8")
    ok = result.returncode == 0 and result.stdout.replace(b"\r\n", b"\n") == expected
    _record(
        "case 4 (wk_main 이 cp949 stdio 에서 UTF-8 로 출력)",
        ok,
        f"rc={result.returncode} stdout={result.stdout[:40]!r}"
        + (f" stderr={result.stderr.decode('utf-8', 'replace')[-200:]}" if not ok else ""),
    )


def _calls_force_utf8(nodes: list[ast.stmt]) -> bool:
    for node in nodes:
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                    and sub.func.id == "force_utf8_stdio"):
                return True
    return False


def case_5_main_entry_modules_fix_stdio() -> None:
    """하네스가 `python -m` 으로 부르는 모듈의 `__main__` 블록이 stdio 를 고정한다."""
    missing: list[str] = []
    for rel in MAIN_ENTRY_MODULES:
        path = SOURCE_ROOT / rel
        if not path.is_file():
            missing.append(f"{rel} (파일 없음)")
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        main_blocks = [
            n for n in tree.body
            if isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
            and isinstance(n.test.left, ast.Name) and n.test.left.id == "__name__"
        ]
        # `__main__` 블록이 직접 부르거나, 블록이 부르는 같은 모듈 함수가 부른다 (wk_main).
        funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        reached: list[ast.stmt] = []
        for block in main_blocks:
            reached.extend(block.body)
            for sub in ast.walk(block):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name)
                        and sub.func.id in funcs):
                    reached.append(funcs[sub.func.id])
        if not main_blocks or not _calls_force_utf8(reached):
            missing.append(rel)
    _record(
        f"case 5 (python -m 진입점 {len(MAIN_ENTRY_MODULES)}개가 stdio 를 고정)",
        not missing,
        f"미고정: {missing}" if missing else "",
    )


def main() -> int:
    print("=== 텍스트 I/O 인코딩 — Windows cp949 (TASK-2026-10-02-main-006) ===")
    for fn in (case_1_package_has_no_default_encoding_io,
               case_2_scanner_catches_each_form,
               case_3_force_utf8_stdio_round_trips_under_cp949,
               case_4_wk_main_fixes_stdio_before_dispatch,
               case_5_main_entry_modules_fix_stdio):
        fn()
    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
