"""workflow_kit.frontmatter_urls — frontmatter URL 추출 + `resource` 규약 검사 (V-R10 입력단).

**왜 이 모듈이 있나.** V-R10(online URL validity)의 입력은 `okf-validate.yml` 안의
`grep -rEho "resource: ['\"]?https?://[^ '\"]+"` 한 줄이었다. 검사가 7주 만에 처음
실제로 돌자 그 한 줄이 만든 결함 두 종류가 같이 나왔다.

1. **위양성** — grep 은 frontmatter 가 아니라 *파일 전체* 를 훑는다. 산문 한 줄
   (``docs/samples/…/README.md:96``) 의 백틱 안 예시에서 URL 을 뽑았고, 정규식
   ``[^ '"]+`` 이 백틱·괄호·마침표까지 URL 에 포함시켜 ``…README.md`).`` 라는
   존재한 적 없는 URL 을 만들어 냈다. 판정은 "링크가 죽었다"(`V-R10-online-stale`)
   였지만 사실은 *애초에 그런 URL 이 없었다* 는 것이다 — **이름과 원인이 다르다**.
2. **조용한 누락** — 값이 공백에서 끊기므로 ``a + b`` 형태의 복수 출처는 **첫 URL 만**
   검사되고 나머지는 아무 말 없이 사라진다. `topics/ponytail-adoption-design-2026-07-23`
   의 blog URL 은 그렇게 한 번도 검사된 적이 없었다. 0건은 "결함 없음" 과 "안 봤음" 을
   같은 모양으로 낸다.

그래서 규약을 아는 자리를 **하나**로 만든다. 추출은 여기서만 하고, 소비자
(`okf-validate.yml`)는 이 모듈을 부른다.

규약:
- **frontmatter 만** 본다. 파일 선두 ``---`` 블록 밖(본문·코드펜스·표)은 데이터가 아니다.
- `last_ingested_from` 은 **자유 서술**이다(56개 중 대부분이 ``a + b``/``§`` 형태의
  복수 출처 메모). 그래서 값 안의 URL 을 **전부** 뽑는다.
- `resource` 는 OKF §4.1 의 *canonical URI* 다. 따라서 **bare URI 하나**여야 하고,
  괄호 주석·복수 출처·서술이 섞이면 규약 위반으로 보고한다(`V-R10-resource-not-bare-uri`).

Usage:
    from workflow_kit.frontmatter_urls import scan_paths

    result = scan_paths([Path("ai-workflow/wiki")])
    for u in result.urls:
        print(u.path, u.line, u.key, u.url)

CLI:
    python -m workflow_kit.frontmatter_urls <root>... --format urls     # xargs 입력용
    python -m workflow_kit.frontmatter_urls <root>... --format json     # 출처 포함 전체
    python -m workflow_kit.frontmatter_urls <root>... --check           # 규약 위반 시 exit 1
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import IO, Sequence

# 추출 대상 key. `resource` 는 OKF canonical URI, `last_ingested_from` 은 wiki 출처 메모.
DEFAULT_KEYS: tuple[str, ...] = ("resource", "last_ingested_from")

# canonical URI 를 요구하는 key (bare URI 규약 적용 대상).
BARE_URI_KEYS: frozenset[str] = frozenset({"resource"})

_FRONTMATTER_DELIMITER = "---"

# top-level scalar key 만 본다 (들여쓰기된 줄은 리스트/중첩 값이다).
_KEY_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):[ \t]*(.*)$")

# URL 후보. 공백과 따옴표·꺾쇠·백틱은 URL 문자가 아니므로 여기서 이미 끊는다.
_URL_CANDIDATE = re.compile(r"https?://[^\s\"'`<>]+")

# URL 끝에 붙기 쉬운 문장부호. 위 정규식이 이미 끊는 문자(백틱·따옴표)도 함께 넣는다 —
# `trim_url` 은 정규식을 거치지 않은 값에도 불릴 수 있고, 두 층이 같은 규약을 알아야 한다.
_TRAILING_PUNCT = ",.;:!?*`\"'"

RULE_NOT_BARE_URI = "V-R10-resource-not-bare-uri"
RULE_NO_INPUT = "V-R10-no-input"


@dataclass(frozen=True)
class FrontmatterUrl:
    """frontmatter 에서 뽑힌 URL 하나 + **어디서 뽑혔는지**.

    출처(path/line/key)를 같이 들고 다니는 것이 요점이다. 이전 grep 은 URL 문자열만
    남겨서, 실패한 URL 이 어느 파일 어느 필드에서 왔는지 손으로 찾아야 했다.
    """

    path: str
    line: int
    key: str
    url: str


@dataclass(frozen=True)
class ConventionIssue:
    """규약 위반 하나 (검사 실패로 보고되는 사실)."""

    path: str
    line: int
    key: str
    rule: str
    value: str
    message: str


@dataclass(frozen=True)
class ScanResult:
    """스캔 결과 + **무엇을 봤는지**.

    `scanned_paths` 를 함께 내는 이유: 훑은 파일이 0개인데 "위반 0건" 이라고 말하면
    검사가 통과한 것처럼 보인다. 조사 0건은 결함 0건이 아니다.
    """

    roots: tuple[str, ...]
    scanned_paths: tuple[str, ...]
    urls: tuple[FrontmatterUrl, ...]
    issues: tuple[ConventionIssue, ...]


def frontmatter_lines(text: str) -> list[tuple[int, str]]:
    """선두 ``---`` 블록의 (1-based 줄번호, 줄) 목록. 블록이 없으면 빈 목록.

    본문에 나오는 ``---``(수평선)이나 코드펜스 안의 예시 frontmatter 는 잡지 않는다 —
    파일이 ``---`` 로 *시작* 할 때만 frontmatter 다.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONTMATTER_DELIMITER:
        return []
    out: list[tuple[int, str]] = []
    for idx, line in enumerate(lines[1:], start=2):
        if line.strip() == _FRONTMATTER_DELIMITER:
            return out
        out.append((idx, line))
    # 닫히지 않은 frontmatter — 블록으로 인정하지 않는다.
    return []


def frontmatter_scalars(text: str) -> list[tuple[int, str, str]]:
    """frontmatter 의 top-level scalar (줄번호, key, 원시 값) 목록."""
    out: list[tuple[int, str, str]] = []
    for lineno, line in frontmatter_lines(text):
        m = _KEY_LINE.match(line)
        if not m:
            continue
        out.append((lineno, m.group(1), m.group(2).strip()))
    return out


def strip_quotes(value: str) -> str:
    """YAML scalar 의 감싼 따옴표 한 겹 제거 + 줄 끝 ``#`` 주석 제거."""
    v = value.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1].strip()
    # 따옴표가 없을 때만 주석으로 본다 (따옴표 안의 `#` 는 값의 일부다).
    if "#" in v:
        head, _, _tail = v.partition("#")
        if head.strip() and head != v:
            return head.strip()
    return v


def trim_url(raw: str) -> str:
    """URL 후보 끝의 문장부호를 떼어 낸다.

    ``…/README.md`).`` 같은 값이 나온 자리다. 괄호는 **균형** 을 본다 — URL 안에
    ``(`` 가 있으면 끝의 ``)`` 는 URL 의 일부일 수 있다(위키백과 형태).
    """
    url = raw
    while url:
        last = url[-1]
        if last in _TRAILING_PUNCT:
            url = url[:-1]
            continue
        if last == ")" and url.count("(") < url.count(")"):
            url = url[:-1]
            continue
        if last in "]}>":
            url = url[:-1]
            continue
        break
    return url


def find_urls(value: str) -> list[str]:
    """값 안의 http(s) URL 을 **전부** 순서대로. 첫 하나로 끊지 않는다."""
    urls: list[str] = []
    for m in _URL_CANDIDATE.finditer(value):
        url = trim_url(m.group(0))
        if url:
            urls.append(url)
    return urls


def check_bare_uri(key: str, value: str) -> str | None:
    """`resource` 규약 위반 메시지 (위반 없으면 None).

    canonical URI 는 **토큰 하나** 다. 공백이 있으면 그 값은 URI 가 아니라 서술이고,
    그런 값을 URI 자리에 넣으면 소비자가 없는 URL 을 만들어 낸다(§2.58).
    """
    if key not in BARE_URI_KEYS:
        return None
    if not value:
        return None
    if value.split() != [value]:
        return (
            f"`{key}` 는 canonical URI 하나여야 한다 (OKF §4.1). 값에 공백이 있다 — "
            f"괄호 주석·복수 출처·서술은 `last_ingested_from` 쪽에 둔다: {value!r}"
        )
    if not value.startswith(("http://", "https://")):
        return (
            f"`{key}` 가 절대 URI 가 아니다 (scheme 부재): {value!r}"
        )
    return None


def _iter_markdown(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(p for p in root.rglob("*.md") if p.is_file())


def scan_file(
    path: Path,
    *,
    keys: Sequence[str] = DEFAULT_KEYS,
    display_path: str | None = None,
) -> tuple[list[FrontmatterUrl], list[ConventionIssue]]:
    """파일 하나의 frontmatter 에서 URL 추출 + 규약 검사."""
    shown = display_path if display_path is not None else str(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [], []
    urls: list[FrontmatterUrl] = []
    issues: list[ConventionIssue] = []
    for lineno, key, raw_value in frontmatter_scalars(text):
        if key not in keys:
            continue
        value = strip_quotes(raw_value)
        message = check_bare_uri(key, value)
        if message is not None:
            issues.append(
                ConventionIssue(
                    path=shown, line=lineno, key=key,
                    rule=RULE_NOT_BARE_URI, value=value, message=message,
                )
            )
        for url in find_urls(value):
            urls.append(FrontmatterUrl(path=shown, line=lineno, key=key, url=url))
    return urls, issues


def scan_paths(
    roots: Sequence[Path],
    *,
    keys: Sequence[str] = DEFAULT_KEYS,
    relative_to: Path | None = None,
) -> ScanResult:
    """root 목록(디렉토리 또는 파일)을 훑어 URL + 위반 + **본 파일 목록** 을 낸다."""
    scanned: list[str] = []
    urls: list[FrontmatterUrl] = []
    issues: list[ConventionIssue] = []
    for root in roots:
        for path in _iter_markdown(root):
            shown = str(path)
            if relative_to is not None:
                try:
                    shown = str(path.resolve().relative_to(relative_to.resolve()))
                except ValueError:
                    shown = str(path)
            scanned.append(shown)
            file_urls, file_issues = scan_file(path, keys=keys, display_path=shown)
            urls.extend(file_urls)
            issues.extend(file_issues)
    return ScanResult(
        roots=tuple(str(r) for r in roots),
        scanned_paths=tuple(scanned),
        urls=tuple(urls),
        issues=tuple(issues),
    )


def unique_urls(result: ScanResult) -> list[str]:
    """정렬된 고유 URL 목록 (검사기 입력용)."""
    return sorted({u.url for u in result.urls})


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="workflow_kit.frontmatter_urls",
        description="frontmatter URL 추출 + `resource` bare-URI 규약 검사 (V-R10 입력단)",
    )
    p.add_argument("roots", nargs="+", type=Path, help="스캔할 디렉토리 또는 파일")
    p.add_argument(
        "--format", dest="fmt", choices=("urls", "json", "text"), default="urls",
        help="urls: URL 만 한 줄씩 (기본) / json: 출처·위반·스캔 목록 / text: 사람이 읽는 형태",
    )
    p.add_argument(
        "--key", dest="keys", action="append",
        help=f"추출할 frontmatter key (반복 가능, 기본: {', '.join(DEFAULT_KEYS)})",
    )
    p.add_argument(
        "--check", action="store_true",
        help="규약 위반이 있으면 exit 1",
    )
    p.add_argument(
        "--relative-to", type=Path, default=None,
        help="출력 경로를 이 디렉토리 기준 상대경로로",
    )
    p.add_argument(
        "--allow-empty", action="store_true",
        help="스캔 대상이 0건이어도 성공으로 본다 (기본: exit 2)",
    )
    return p


def main(argv: list[str] | None = None, *, stdout: IO[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    out = stdout if stdout is not None else sys.stdout
    keys: Sequence[str] = tuple(args.keys) if args.keys else DEFAULT_KEYS
    result = scan_paths(args.roots, keys=keys, relative_to=args.relative_to)

    if args.fmt == "json":
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2), file=out)
    elif args.fmt == "text":
        for u in result.urls:
            print(f"{u.path}:{u.line}  {u.key}  {u.url}", file=out)
    else:
        for url in unique_urls(result):
            print(url, file=out)

    # 스캔 0건은 "위반 없음" 이 아니라 "안 봤음" 이다 — 조용히 통과시키지 않는다.
    if not result.scanned_paths and not args.allow_empty:
        print(
            f"::error::{RULE_NO_INPUT}: 스캔한 파일이 0건이다 (roots={list(result.roots)}) — "
            f"경로가 바뀌었는지 확인할 것. 0건은 결함 없음이 아니다.",
            file=sys.stderr,
        )
        return 2

    if result.issues:
        for issue in result.issues:
            print(
                f"::error file={issue.path},line={issue.line}::{issue.rule}: {issue.message}",
                file=sys.stderr,
            )
        print(
            f"{len(result.issues)} convention issue(s) in {len(result.scanned_paths)} file(s)",
            file=sys.stderr,
        )
        if args.check:
            return 1
    elif args.check:
        print(
            f"OK: {len(result.scanned_paths)} file(s) scanned, "
            f"{len(unique_urls(result))} unique URL(s), 0 convention issue(s)",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
