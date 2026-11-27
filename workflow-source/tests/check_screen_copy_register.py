#!/usr/bin/env python3
"""사람이 보는 화면 문구의 말투 — 해요체 (TASK-2026-11-27-claude-plex-002, 소유자 결정 2026-11-27).

반말 종결(~다 · ~한다 · ~할까?)이 화면 문구로 다시 들어오지 않게 잰다. 코드 주석은 재지 않는다.

4 cases:
  1. 화면 파일(허브 ``hub.js`` · ``index.html``, PC 중계 ``relay.js`` · ``relay.html``) 문자열 · 본문에 반말 종결 0
  2. Go 내장 사본도 같다 — 정본과 바이트가 같은지는 ``check_go_assets_sync`` 가 보고, 여기서는 사본을 따로 재서 0
  4. 화면에 뜨는 서버 오류 메시지 — Python 허브 ``HubError`` · ``not_found`` · ``forbidden`` · ``invalid_field`` · ``unauthorized`` ·
     ``"message":`` 와 Go 허브 ``Message:`` · ``NotFound`` · ``Forbidden`` · ``InvalidField`` · ``Unauthorized`` · ``"message":`` 의 문자열에 반말 종결 0
  3. 되주입 — 문구에 ``없다.`` · ``할까?`` 를 넣으면 잡히고, 주석에 넣은 것 · 문장 끝이 아닌 ``처리하다`` 는 잡지 않는다
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 30

WATCHES = (
    "workflow-source/workflow_kit/hub/static/*",
    "workflow-source/workflow_kit/relay/static/*",
    "hub-go/internal/assets/static/*",
    "hub-go/internal/relay/static/*",
    "workflow-source/workflow_kit/hub/*",
    "hub-go/internal/*",
)

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCREEN_FILES = (
    "workflow-source/workflow_kit/hub/static/hub.js",
    "workflow-source/workflow_kit/hub/static/index.html",
    "workflow-source/workflow_kit/relay/static/relay.js",
    "workflow-source/workflow_kit/relay/static/relay.html",
)
GO_COPIES = (
    "hub-go/internal/assets/static/hub.js",
    "hub-go/internal/assets/static/index.html",
    "hub-go/internal/relay/static/relay.js",
    "hub-go/internal/relay/static/relay.html",
)
# 문장 끝 자리(뒤가 끝 · 공백 · 문장부호 · 템플릿 ${ )의 한글 낱말이 '다' 나 '까' 로 끝나면 반말 종결이다.
_END = re.compile(r"([가-힣]+(?:다|까))(?=$|[\s.,)\]—·'`\"!?:;<]|\$\{)")
# 문장 끝 꼴이지만 종결이 아닌 낱말 — 이유와 함께 둔다
NOT_ENDINGS = {
    "처리하다": "연결형 '처리하다(가) 실패' — relay.js 실패 문구",
}

# 서버 메시지 자리 — 한 줄 안의 첫 문자열만 본다(여러 줄로 나뉜 인자는 첫 줄 문자열)
_PY_MSG = re.compile(r'(?:HubError\(\s*\d+,\s*"[a-z_]+",\s*|\b(?:not_found|forbidden|unauthorized)\(|\binvalid_field\([^,()]+,\s*|"message":\s*)f?"((?:[^"\\\n]|\\.)*)"')
_GO_MSG = re.compile(r'(?:Message:\s*|\b(?:NotFound|Forbidden|Unauthorized)\(|\bInvalidField\([^,()]+,\s*|"message":\s*)(?:fmt\.Sprintf\()?"((?:[^"\\\n]|\\.)*)"')


def server_plain(text: str, go: bool) -> list[str]:
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        if "A2AError" in line:  # A2A 프로토콜 오류는 에이전트에게 가는 응답 — 화면 문구가 아니다(Python · Go 둘 다 그대로)
            continue
        for m in (_GO_MSG if go else _PY_MSG).finditer(line):
            for w in _END.findall(m.group(1).replace("%", " ").replace("{", " ")):
                if w not in NOT_ENDINGS and w != "보다":
                    found.append(f"{n}:{w}")
    return found


def server_files() -> list[Path]:
    py = sorted((REPO_ROOT / "workflow-source/workflow_kit/hub").glob("*.py"))
    # judge/ 는 1.x 판정 함수(Python workflow_kit.judgecli)와 출력이 같아야 한다(check_judge_parity) — 두 쪽을 함께 바꿀 때까지 뺀다
    go = sorted(p for p in (REPO_ROOT / "hub-go/internal").rglob("*.go") if not p.name.endswith("_test.go") and "/judge/" not in p.as_posix())
    return py + go


_passes: list[str] = []
_failures: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail and not ok else ''}")


def _code_part(line: str, js: bool) -> str:
    """주석을 뺀 줄 — 문자열 밖의 // 만 주석으로 본다(URL 이 든 문자열을 자르지 않게)."""
    s = line.lstrip()
    if s.startswith(("//", "/*", "*")):
        return ""
    if not js:
        return re.sub(r"<!--.*?-->", "", line)
    q = None
    i = 0
    while i < len(line):
        ch = line[i]
        if q:
            if ch == "\\":
                i += 2
                continue
            if ch == q:
                q = None
        elif ch in "\"'`":
            q = ch
        elif line.startswith("//", i):
            return line[:i]
        i += 1
    return line


def plain_endings(text: str, js: bool) -> list[str]:
    found = []
    for n, line in enumerate(text.splitlines(), 1):
        for m in _END.finditer(_code_part(line, js)):
            if m.group(1) not in NOT_ENDINGS:
                found.append(f"{n}:{m.group(1)}")
    return found


def scan(paths: tuple[str, ...]) -> dict[str, list[str]]:
    out = {}
    for rel in paths:
        hits = plain_endings((REPO_ROOT / rel).read_text(encoding="utf-8"), rel.endswith(".js"))
        if hits:
            out[rel] = hits
    return out


def main() -> int:
    print("=== 화면 문구 말투 (해요체) ===")
    bad = scan(SCREEN_FILES)
    _record("case 1 (화면 파일 4개 — 반말 종결 0)", not bad, "; ".join(f"{k} {v[:8]} ({len(v)}건)" for k, v in bad.items()))
    bad_go = scan(GO_COPIES)
    _record("case 2 (Go 내장 사본 4개 — 반말 종결 0)", not bad_go, "; ".join(f"{k} {v[:8]} ({len(v)}건)" for k, v in bad_go.items()))
    srv_bad = {}
    seen = 0
    for f in server_files():
        text = f.read_text(encoding="utf-8")
        go = f.suffix == ".go"
        seen += len((_GO_MSG if go else _PY_MSG).findall(text))
        hits = server_plain(text, go)
        if hits:
            srv_bad[str(f.relative_to(REPO_ROOT))] = hits
    _record("case 4 (화면에 뜨는 서버 오류 메시지 — Python · Go 반말 종결 0)", not srv_bad and seen >= 300,
            f"잰 메시지 {seen} · " + "; ".join(f"{k} {v[:5]} ({len(v)}건)" for k, v in list(srv_bad.items())[:8]))
    sprobe = {"py": (server_plain('raise not_found("세션이 없다")', False), 1), "go": (server_plain('return NotFound("세션이 없다")', True), 1),
              "go-sprintf": (server_plain('Message: fmt.Sprintf("판 %d 이 새롭다", v)', True), 1),
              "py-ok": (server_plain('raise forbidden("권한이 없어요")', False), 0)}
    probes = {
        "문구 끝 '없다.'": ('say("세션이 없다.");', True, 1),
        "질문 '할까?'": ("confirm(`지울까?`);", True, 1),
        "템플릿 앞 '했다'": ("t = `보냈다${x}`;", True, 1),
        "주석 속 '없다'": ('x = 1; // 여기는 없다.', True, 0),
        "줄 주석 '없다'": ("// 세션이 없다.", True, 0),
        "html 주석": ("<!-- 없다. --><p>있어요.</p>", False, 0),
        "연결형 '처리하다'": ('why = "중계가 처리하다 실패했어요";', True, 0),
        "해요체": ('say("세션이 없어요. 다시 눌러 주세요. 지울까요?");', True, 0),
    }
    got = {k: len(plain_endings(src, js)) for k, (src, js, _) in probes.items()}
    want = {k: n for k, (_, _, n) in probes.items()}
    sgot = {k: len(v[0]) for k, v in sprobe.items()}
    swant = {k: v[1] for k, v in sprobe.items()}
    _record("case 3 (되주입 — 문구의 반말은 잡고 주석 · 연결형 · 해요체는 잡지 않는다 · 서버 메시지 자리도)", got == want and sgot == swant,
            f"got={got} want={want} server={sgot} want={swant}")
    print(f"\n{len(_passes)}/{len(_passes) + len(_failures)} passed")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
