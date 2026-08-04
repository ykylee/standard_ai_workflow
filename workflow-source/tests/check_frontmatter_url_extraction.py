"""frontmatter URL 추출 + `resource` bare-URI 규약 검사 (V-R10 입력단, v1.0.4 §2.58).

**왜 이 검사가 생겼나.** `okf-validate`(V-R10)가 7주 만에 처음 실제로 돌자 결함 2건이
나왔고, 판정 이름(`V-R10-online-stale` = "링크가 죽었다")과 실제 원인이 **둘 다** 달랐다.

| 검출된 URL | 실제 원인 |
|---|---|
| ``…/workflow_kit/README.md`).`` | 추출기가 frontmatter 가 아니라 *산문* 을 훑었다 (위양성) |
| ``…/blob/main/external`` | 생산자가 자유 서술 값을 경로로 취급해 없는 URL 을 만들었다 |

셋 다 고쳐야 하나가 되돌아오지 않는다 — 추출기(어디서 뽑는가), 데이터(값이 규약을
지키는가), 생산자(파생물을 만드는 쪽이 규약을 아는가). 이 파일이 그 셋을 각각 고정한다.

Test list:
1. test_body_prose_url_is_not_extracted: 산문 속 URL 은 데이터가 아니다 (위양성 재발 방지)
2. test_trailing_punctuation_is_trimmed: ``…md`).`` → 문장부호 제거
3. test_compound_value_yields_every_url: ``a + b`` 의 두 URL 을 **전부** (조용한 누락 방지)
4. test_parenthetical_source_note_url_is_clean: ``x (https://…, 날짜)`` → URL 만 깨끗이
5. test_resource_must_be_bare_uri: `resource` 규약 위반 검출 (실제 결함 값으로)
6. test_repo_scan_has_no_convention_violation: 저장소 전수 — 위반 0 + 스캔 0건 아님
7. test_extracted_urls_pass_v_r10_offline: 뽑힌 URL 이 V-R10 offline 검사를 통과한다
8. test_consumer_workflow_uses_the_module: `okf-validate.yml` 이 실제로 이 모듈을 부른다
9. test_zero_scan_is_not_a_pass: 스캔 0건은 통과가 아니다 (exit 2)
10. test_producer_refuses_compound_value: 생산자가 서술 값을 URI 로 만들지 않는다
11. test_producer_refuses_nonexistent_path: 저장소에 없는 경로를 URL 로 만들지 않는다
12. test_bundle_resource_matches_producer: 커밋된 bundle 의 `resource` = 지금 생산자의 출력
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SOURCE_ROOT.parent
FRONTMATTER_URLS = SOURCE_ROOT / "workflow_kit" / "frontmatter_urls.py"
OKF_EXPORT = SOURCE_ROOT / "workflow_kit" / "okf_export.py"
URL_VALIDITY = SOURCE_ROOT / "workflow_kit" / "url_validity.py"
OKF_VALIDATE_WF = REPO_ROOT / ".github" / "workflows" / "okf-validate.yml"

WIKI_ROOT = REPO_ROOT / "ai-workflow" / "wiki"
BUNDLE_ROOT = REPO_ROOT / "docs" / "samples" / "okf-bundle-2026-06-16"

# 실제로 검출됐던 값 — fixture 는 내가 상상한 모양이 아니라 **있었던 모양** 이어야 한다.
REAL_PROSE_LINE = (
    "| 2026-06-16 | 0.2.0 | ADR-008 의 in-repo path → GitHub URL 자동 resolve 로 "
    "`resource` field 자동 채움 (예: `workflow-kit` page 의 "
    "`resource: https://github.com/ykylee/standard_ai_workflow/blob/main/"
    "workflow-source/workflow_kit/README.md`). |"
)
REAL_COMPOUND_RESOURCE = (
    "https://github.com/ykylee/standard_ai_workflow/blob/main/external "
    "(https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md, 2026-06-16)"
)
REAL_LAST_INGESTED_FROM = (
    "external (https://raw.githubusercontent.com/GoogleCloudPlatform/"
    "knowledge-catalog/main/okf/SPEC.md, 2026-06-16)"
)
REAL_PONYTAIL_VALUE = (
    "https://github.com/DietrichGebert/ponytail + "
    "https://blog.scottlogic.com/2026/06/16/ponytail-yagni-and-the-problem-with-prompt-benchmarks.html + "
    "workflow-source/releases/Beta-v1.0.0.md §2.19~§2.26"
)


def _import(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec and spec.loader, path
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _fu():
    return _import("frontmatter_urls", FRONTMATTER_URLS)


def _okf():
    return _import("okf_export", OKF_EXPORT)


def _write(tmpdir: Path, name: str, text: str) -> Path:
    path = tmpdir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- 1. 산문 속 URL 은 데이터가 아니다 ---


def test_body_prose_url_is_not_extracted() -> None:
    """frontmatter 밖의 URL 은 뽑지 않는다.

    이전 grep 은 파일 전체를 훑어 `docs/samples/…/README.md:96` 의 표 한 칸에서
    URL 을 뽑았고, 거기 붙은 백틱·괄호·마침표까지 URL 에 넣어 **존재한 적 없는**
    주소를 만들었다. 검사는 그걸 "죽은 링크" 라고 보고했다.
    """
    mod = _fu()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # 두 모양을 한 파일에 넣는다. 표 한 칸의 백틱 예시(실제 위양성)와,
        # 코드펜스 안에서 **줄 첫머리가 `resource:` 인** 예시 — 후자는
        # `ai-workflow/wiki/concepts/okf-open-knowledge-format.md:124` 에 실재하고,
        # frontmatter 블록 경계를 안 보면 이쪽이 그대로 데이터로 둔갑한다.
        path = _write(
            tmp, "README.md",
            "---\ntype: sample\nstatus: snapshot\n---\n\n# S\n\n"
            + REAL_PROSE_LINE + "\n\n```yaml\n"
            "resource: https://console.cloud.google.com/bigquery?p=acme&d=sales&t=orders\n"
            "last_ingested_from: https://example.com/body-example.md\n"
            "```\n",
        )
        urls, issues = mod.scan_file(path)
        assert not urls, f"본문에서 URL 을 뽑았다 (위양성 재발): {[u.url for u in urls]}"
        assert not issues, f"본문 예시를 규약 위반으로 보고했다: {issues}"

    # 실제 파일에서도 같아야 한다 — fixture 만 통과하면 의미가 없다.
    for real in (BUNDLE_ROOT / "README.md", WIKI_ROOT / "concepts" / "okf-open-knowledge-format.md"):
        assert real.exists(), f"실측 대상이 사라졌다: {real}"
        urls, _ = mod.scan_file(real)
        body_urls = [u.url for u in urls if "console.cloud.google.com" in u.url or "`" in u.url]
        assert not body_urls, f"{real} 본문에서 URL 이 뽑혔다: {body_urls}"


# --- 2. 문장부호 제거 ---


def test_trailing_punctuation_is_trimmed() -> None:
    """URL 뒤에 붙은 ``` `).` ``` 류를 URL 에 포함하지 않는다."""
    mod = _fu()
    base = "https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/workflow_kit/README.md"
    for suffix in ("`).", ").", ".", ",", ")", "`", "]"):
        assert mod.trim_url(base + suffix) == base, f"{suffix!r} 가 안 떨어졌다"
    # 괄호는 균형을 본다 — URL 안의 `(` 가 있으면 끝의 `)` 는 URL 의 일부다.
    balanced = "https://en.wikipedia.org/wiki/Ruby_(programming_language)"
    assert mod.trim_url(balanced) == balanced, "균형 잡힌 괄호를 잘랐다"


# --- 3. 복수 URL 을 전부 ---


def test_compound_value_yields_every_url() -> None:
    """``a + b + path`` 값에서 URL 을 **둘 다** 뽑는다.

    공백에서 끊던 이전 추출기는 첫 URL 만 검사하고 나머지를 아무 말 없이 버렸다.
    `topics/ponytail-adoption-design-2026-07-23` 의 blog URL 은 그래서 한 번도
    검사된 적이 없다. 0건은 "결함 없음" 과 "안 봤음" 을 같은 모양으로 낸다.
    """
    mod = _fu()
    urls = mod.find_urls(REAL_PONYTAIL_VALUE)
    assert urls == [
        "https://github.com/DietrichGebert/ponytail",
        "https://blog.scottlogic.com/2026/06/16/ponytail-yagni-and-the-problem-with-prompt-benchmarks.html",
    ], urls


# --- 4. 괄호 주석 안의 URL ---


def test_parenthetical_source_note_url_is_clean() -> None:
    """``external (https://…SPEC.md, 2026-06-16)`` → URL 만, 끝의 쉼표 없이."""
    mod = _fu()
    urls = mod.find_urls(REAL_LAST_INGESTED_FROM)
    assert urls == [
        "https://raw.githubusercontent.com/GoogleCloudPlatform/knowledge-catalog/main/okf/SPEC.md"
    ], urls


# --- 5. `resource` bare-URI 규약 ---


def test_resource_must_be_bare_uri() -> None:
    """`resource` 는 canonical URI 하나. 실제 결함 값으로 되주입한다."""
    mod = _fu()
    assert mod.check_bare_uri("resource", REAL_COMPOUND_RESOURCE) is not None, (
        "실제로 커밋돼 있던 복합 값을 규약 검사가 통과시켰다"
    )
    assert mod.check_bare_uri("resource", "https://example.com/spec.md") is None
    assert mod.check_bare_uri("resource", "workflow-source/README.md") is not None, (
        "scheme 없는 값이 canonical URI 로 통과했다"
    )
    # `last_ingested_from` 은 자유 서술이다 (56개 중 대부분이 복합 값) — 규약 대상 아님.
    assert mod.check_bare_uri("last_ingested_from", REAL_PONYTAIL_VALUE) is None

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        path = _write(
            tmp, "p.md",
            f'---\ntype: concept\nresource: "{REAL_COMPOUND_RESOURCE}"\n---\n\n# P\n',
        )
        _urls, issues = mod.scan_file(path)
        assert len(issues) == 1 and issues[0].rule == mod.RULE_NOT_BARE_URI, issues
        assert issues[0].line == 3, f"줄번호가 틀리면 고칠 자리를 못 찾는다: {issues[0]}"


# --- 6. 저장소 전수 ---


def test_repo_scan_has_no_convention_violation() -> None:
    """실제 wiki + sample bundle 에 규약 위반 0. 그리고 **스캔 0건이 아니다**."""
    mod = _fu()
    result = mod.scan_paths([WIKI_ROOT, BUNDLE_ROOT], relative_to=REPO_ROOT)
    assert len(result.scanned_paths) > 50, (
        f"스캔한 파일이 {len(result.scanned_paths)}건뿐이다 — 경로가 바뀌었나? "
        f"조사 0건은 결함 0건이 아니다."
    )
    assert not result.issues, "\n".join(
        f"{i.path}:{i.line} {i.rule}: {i.message}" for i in result.issues
    )


# --- 7. 뽑힌 URL 이 V-R10 offline 을 통과 ---


def test_extracted_urls_pass_v_r10_offline() -> None:
    """추출 결과가 **검사기 입력으로서** 성립한다 (네트워크 없이).

    online 검사는 네트워크 의존이라 여기서 돌리지 않는다. 하지만 *뽑힌 문자열이
    URL 이기는 한가* 는 오프라인 사실이고, 이번 결함(``…md`).``)이 정확히 거기서
    걸렸어야 했다.
    """
    mod = _fu()
    uv = _import("url_validity", URL_VALIDITY)
    result = mod.scan_paths([WIKI_ROOT, BUNDLE_ROOT], relative_to=REPO_ROOT)
    assert result.urls, "추출된 URL 이 0건이다 — 추출기가 입을 닫았나?"
    for u in result.urls:
        assert not re.search(r"[\s`\"'<>]", u.url), f"{u.path}:{u.line} URL 에 잡문자: {u.url!r}"
        assert u.url.count("(") == u.url.count(")"), f"{u.path}:{u.line} 괄호 불균형: {u.url!r}"
        errors = [i for i in uv.check_url(u.url) if i.severity == "error"]
        assert not errors, f"{u.path}:{u.line} {u.url} → {[e.message for e in errors]}"


# --- 8. 소비자 대조 ---


def test_consumer_workflow_uses_the_module() -> None:
    """`okf-validate.yml` 이 이 모듈을 부르고, 넘기는 root 가 **실재**한다.

    §2.57 과 같은 축이다 — 소비자와 도구가 갈라지면 그 사실이 안 보인다. 손으로 베낀
    목록을 두지 않고 워크플로우 파일에서 직접 뽑아 대조한다.
    """
    text = OKF_VALIDATE_WF.read_text(encoding="utf-8")
    assert "workflow_kit.frontmatter_urls" in text, (
        "소비자가 추출 모듈을 안 부른다 — 규약을 아는 자리가 다시 둘로 갈라졌다"
    )
    assert "grep -rEho \"resource:" not in text, "옛 grep 추출기가 남아 있다"
    assert "--check" in text, "규약 검사(--check) 호출이 워크플로우에 없다"

    roots = set(re.findall(r"^\s+(?:roots=\()?((?:ai-workflow/wiki|docs/samples/[\w.-]+))", text, re.M))
    roots |= set(re.findall(r"(ai-workflow/wiki|docs/samples/okf-bundle-[\d-]+)", text))
    assert roots, "워크플로우에서 스캔 root 를 못 뽑았다 — 호출 형태가 바뀌었나?"
    for root in sorted(roots):
        assert (REPO_ROOT / root).exists(), f"워크플로우가 없는 경로를 스캔한다: {root}"


# --- 9. 스캔 0건은 통과가 아니다 ---


def test_zero_scan_is_not_a_pass() -> None:
    """대상이 0건이면 exit 2. 감사자도 감사 대상이다.

    "위반 0건" 과 "아무것도 안 봤음" 이 같은 모양이면 경로가 바뀌는 날 검사는
    조용히 통과한다.
    """
    with tempfile.TemporaryDirectory() as td:
        proc = subprocess.run(
            [sys.executable, "-m", "workflow_kit.frontmatter_urls", td, "--check"],
            cwd=str(SOURCE_ROOT), capture_output=True, text=True, timeout=60,
        )
        assert proc.returncode == 2, f"빈 디렉토리인데 exit {proc.returncode}: {proc.stderr}"
        assert "V-R10-no-input" in proc.stderr, proc.stderr
        # --allow-empty 를 **명시** 했을 때만 통과다.
        proc2 = subprocess.run(
            [sys.executable, "-m", "workflow_kit.frontmatter_urls", td, "--check", "--allow-empty"],
            cwd=str(SOURCE_ROOT), capture_output=True, text=True, timeout=60,
        )
        assert proc2.returncode == 0, proc2.stderr


# --- 10~11. 생산자 ---


def test_producer_refuses_compound_value() -> None:
    """`_derive_resource` 는 서술 값을 canonical URI 로 만들지 않는다."""
    mod = _okf()
    got = mod._derive_resource(REAL_LAST_INGESTED_FROM, repo_root=REPO_ROOT)
    assert got is None, f"서술 값이 URI 가 됐다: {got!r}"
    got2 = mod._derive_resource(
        "workflow-source/MEMORY_GOVERNANCE.md §4 + workflow-source/releases/Beta-v0.6.1.5.md",
        repo_root=REPO_ROOT,
    )
    assert got2 is None, f"복수 출처가 URI 가 됐다: {got2!r}"


def test_producer_refuses_nonexistent_path() -> None:
    """저장소에 **없는** 경로는 URL 이 되지 않는다. 있는 경로는 그대로 된다."""
    mod = _okf()
    assert mod._derive_resource("external", repo_root=REPO_ROOT) is None, (
        "`external` 은 경로가 아니라 표식이었고, 그게 `…/blob/main/external` 이 된 원인이다"
    )
    assert mod._derive_resource("workflow-source/does-not-exist.md", repo_root=REPO_ROOT) is None
    real = mod._derive_resource("workflow-source/workflow_kit/README.md", repo_root=REPO_ROOT)
    assert real and real.endswith("workflow-source/workflow_kit/README.md"), (
        f"실재하는 경로가 resolve 안 됐다: {real!r}"
    )
    # URL 값은 저장소와 무관하게 그대로 통과한다.
    assert mod._derive_resource("https://example.com/a.md") == "https://example.com/a.md"


# --- 12. 파생물 ↔ 생산자 대조 ---


def _blob_suffix(url: str) -> str:
    """GitHub blob URL 에서 `<origin>/blob/<ref>/` 를 뗀 나머지 (fork/ref 무관 비교용)."""
    m = re.match(r"^https://[^/]+/[^/]+/[^/]+/blob/[^/]+/(.*)$", url)
    return m.group(1) if m else url


def test_bundle_resource_matches_producer() -> None:
    """커밋된 sample bundle 의 `resource` 가 **지금 생산자가 만드는 값** 과 같다.

    같은 손질을 두 번 하게 되는 자리다 — 데이터를 손으로 고쳐 놓고 생산자를 그대로
    두면 다음 export 가 되돌린다. 파생물은 만드는 쪽이 규약을 알아야 한다.
    """
    fu, okf = _fu(), _okf()
    checked = 0
    for bundle_page in sorted(BUNDLE_ROOT.rglob("*.md")):
        rel = bundle_page.relative_to(BUNDLE_ROOT)
        if rel.name in ("README.md", "index.md"):
            continue
        wiki_page = WIKI_ROOT / rel
        if not wiki_page.exists():
            continue
        wiki_fm = {k: v for _ln, k, v in fu.frontmatter_scalars(wiki_page.read_text(encoding="utf-8"))}
        bundle_fm = {
            k: fu.strip_quotes(v)
            for _ln, k, v in fu.frontmatter_scalars(bundle_page.read_text(encoding="utf-8"))
        }
        expected = okf._derive_resource(
            wiki_fm.get("last_ingested_from"),
            repo_root=REPO_ROOT,
            vcs_commit=wiki_fm.get("vcs_commit"),
            vcs_ref=wiki_fm.get("vcs_ref"),
        )
        actual = bundle_fm.get("resource")
        checked += 1
        if expected is None:
            assert actual is None, (
                f"{rel}: 생산자는 `resource` 를 안 만드는데 bundle 에는 {actual!r} 가 있다 — "
                f"손으로 넣었거나 옛 생산자의 산물이다"
            )
            continue
        assert actual is not None, f"{rel}: 생산자는 {expected!r} 를 만드는데 bundle 에 `resource` 가 없다"
        if expected != actual:
            # fork/ref 가 다른 환경에서도 판정이 성립해야 한다 — 경로부로 비교하고
            # 무엇으로 비교했는지 남긴다 (조용한 완화는 무력화와 구분이 안 된다).
            print(f"    note: origin 이 달라 경로부로 비교 — expected={expected} actual={actual}")
            assert _blob_suffix(expected) == _blob_suffix(actual), f"{rel}: {expected!r} != {actual!r}"
    assert checked >= 3, f"대조한 page 가 {checked}건뿐이다 — bundle 경로가 바뀌었나?"


def main() -> int:
    test_funcs = [
        test_body_prose_url_is_not_extracted,
        test_trailing_punctuation_is_trimmed,
        test_compound_value_yields_every_url,
        test_parenthetical_source_note_url_is_clean,
        test_resource_must_be_bare_uri,
        test_repo_scan_has_no_convention_violation,
        test_extracted_urls_pass_v_r10_offline,
        test_consumer_workflow_uses_the_module,
        test_zero_scan_is_not_a_pass,
        test_producer_refuses_compound_value,
        test_producer_refuses_nonexistent_path,
        test_bundle_resource_matches_producer,
    ]
    failed: list[str] = []
    for fn in test_funcs:
        name = fn.__name__
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
            failed.append(name)
    total = len(test_funcs)
    print(f"\n{total - len(failed)}/{total} tests passed.")
    if failed:
        print("\n" + "\n".join(f"  - {n}" for n in failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
