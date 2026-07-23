#!/usr/bin/env python3
"""
v0.7.25: migrate_legacy_l2 smoke test (5/5 PASS)

Test cases:
1. test_dry_run_detect_legacy — dry-run 의 legacy 판별 로직 (fixture 외부 wiki)
2. test_apply_writes_mirror — apply 가 in-repo mirror file 생성
3. test_idempotency_skip — 동일 content 재apply 시 skipped (identical)
4. test_drift_warning — 외부 wiki 의 file 변경 시 drift 감지 + skip (manual review)
5. test_unknown_args — argparse error (--dry-run / --apply 모두 부재 시)
6. test_committed_mirror_is_self_consistent — 커밋된 산출물의 자기 정합

## v1.0.1+ — `~/wiki` 의존 제거

Test 1 은 **실제 저장소 + `~/wiki/wiki/projects/standard-ai-workflow/sources`** 를
읽어 "legacy 15건" 을 단언했다. 저장소 밖, 특정 사용자 머신에만 있는 경로다. 그래서
이 smoke 는 작성자 로컬에서만 green 이었고 CI 에서는 4/5 로 영구 red 였다.

게다가 그 단언은 근거가 어긋나 있었다. 커밋된 산출물
(`ai-workflow/memory/release/_external-wiki-legacy.md`) 의 frontmatter 를 보면
출처가 **`/Users/yklee/...` (macOS)** 이고 `migrated_at: 2026-06-15` 다 — 즉 그
mirror 는 *다른 머신의* wiki 에서 만들어졌다. 지금 리눅스 홈에 있는 `~/wiki` 는
그때 그 디렉터리가 아니며, 15라는 숫자가 맞아떨어진 것은 우연에 가깝다.

마이그레이션은 v0.7.25 에서 **이미 완료**됐고 (`migrate_legacy_l2` 는 일회성 closure
도구), 그 결과물은 저장소에 커밋돼 있다. 그러므로 이 smoke 가 지켜야 할 것은 둘이다:

- **도구의 로직** — fixture 외부 wiki 로 검사한다 (`--external-wiki`, v1.0.1+ 신설).
  숫자를 하드코딩하지 않고 fixture 가 만든 개수를 그대로 대조한다.
- **커밋된 산출물의 자기 정합** — 그것이 이 저장소에 남아 있는 durable 한 사실이다.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# === Test setup ===
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL = REPO_ROOT / "workflow-source" / "tools" / "migrate_legacy_l2.py"
PYTHON = sys.executable

# v0.7.25 마이그레이션의 커밋된 산출물 (in-repo, durable).
COMMITTED_MIRROR = REPO_ROOT / "ai-workflow" / "memory" / "release" / "_external-wiki-legacy.md"

# fixture 외부 wiki 가 만들 legacy version (in-repo 에는 없는 것들).
FIXTURE_LEGACY_VERSIONS = ["v0.1.0", "v0.2.0", "v0.3.1", "v0.5.7.1", "v0.6.3"]
# fixture in-repo 에 이미 있는 version (legacy 로 세면 안 된다).
FIXTURE_INREPO_VERSIONS = ["v0.7.24", "v0.9.0"]


def _make_external_wiki(base: Path) -> Path:
    """fixture 외부 wiki — legacy release page + 무시돼야 할 잡파일."""
    ext = base / "external_wiki"
    ext.mkdir(parents=True, exist_ok=True)
    for v in FIXTURE_LEGACY_VERSIONS:
        prefix = "alpha" if v.startswith(("v0.1", "v0.2", "v0.3.0", "v0.3.1")) else "beta"
        (ext / f"releases-{prefix}-{v}.md").write_text(f"# {v}\n\nbody\n", encoding="utf-8")
    # in-repo 에도 있는 version → legacy 아님
    for v in FIXTURE_INREPO_VERSIONS:
        (ext / f"releases-beta-{v}.md").write_text(f"# {v}\n\nbody\n", encoding="utf-8")
    # 패턴에 맞지 않는 파일 → 무시돼야 한다
    (ext / "README.md").write_text("# readme\n", encoding="utf-8")
    (ext / "notes.txt").write_text("ignore me\n", encoding="utf-8")
    return ext


def _make_repo_root(base: Path, versions: list[str]) -> Path:
    """fixture in-repo — `ai-workflow/memory/release/<version>/` dir 집합."""
    repo_root = base / "fake_repo"
    release_dir = repo_root / "ai-workflow" / "memory" / "release"
    release_dir.mkdir(parents=True, exist_ok=True)
    for v in versions:
        (release_dir / v).mkdir(parents=True, exist_ok=True)
    return repo_root


def _run_tool(*args: str, repo_root: Path, external_wiki: Path | None = None) -> dict:
    """Run migrate_legacy_l2.py with given args + repo_root override. Returns parsed JSON."""
    cmd = [
        PYTHON, str(TOOL), *args,
        "--repo-root", str(repo_root),
        "--json",
    ]
    if external_wiki is not None:
        cmd += ["--external-wiki", str(external_wiki)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if proc.returncode != 0:
        return {"error": proc.stderr, "returncode": proc.returncode, "stdout": proc.stdout}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse fail: {e}", "stdout": proc.stdout}


# === Test 1: dry-run detect legacy ===
def test_dry_run_detect_legacy() -> bool:
    """dry-run 의 legacy 판별 로직 — external 에만 있는 version 만 골라낸다.

    기대값을 하드코딩하지 않는다. fixture 가 심은 것과 대조한다 — 숫자를 박아 두면
    입력이 바뀌었을 때 무엇이 틀렸는지가 아니라 *숫자가 틀렸다* 만 알게 된다.
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        external_wiki = _make_external_wiki(base)
        repo_root = _make_repo_root(base, FIXTURE_INREPO_VERSIONS)

        result = _run_tool("--dry-run", repo_root=repo_root, external_wiki=external_wiki)
        if result.get("error"):
            print(f"  FAIL: tool error: {result['error']}")
            return False
        if result.get("mode") != "dry-run":
            print(f"  FAIL: expected mode=dry-run, got {result.get('mode')}")
            return False

        expected = sorted(FIXTURE_LEGACY_VERSIONS)
        versions = sorted(f["version"] for f in result.get("files", []))
        if versions != expected:
            print(f"  FAIL: expected legacy {expected}, got {versions}")
            return False
        if result.get("legacy_count") != len(expected):
            print(f"  FAIL: legacy_count={result.get('legacy_count')} != {len(expected)}")
            return False
        # in-repo 에 있는 version 은 legacy 로 세면 안 된다
        leaked = set(versions) & set(FIXTURE_INREPO_VERSIONS)
        if leaked:
            print(f"  FAIL: in-repo version 이 legacy 로 분류됨: {sorted(leaked)}")
            return False
        print(f"  PASS: dry-run detect {len(expected)} legacy files (fixture 대조)")
        return True


# === Test 6: 커밋된 산출물의 자기 정합 ===
def test_committed_mirror_is_self_consistent() -> bool:
    """v0.7.25 마이그레이션의 **커밋된 결과물**이 스스로 앞뒤가 맞는가.

    외부 wiki 를 다시 읽어 재현하는 대신 (그 wiki 는 다른 머신에 있었다),
    저장소에 남아 있는 산출물의 정합만 본다 — 이것이 durable 한 사실이다.
    """
    if not COMMITTED_MIRROR.is_file():
        print(f"  FAIL: 커밋된 mirror 부재: {COMMITTED_MIRROR}")
        return False
    text = COMMITTED_MIRROR.read_text(encoding="utf-8")

    # **선행 frontmatter 블록만** 본다. 본문은 각 릴리스 원본의 frontmatter 를 그대로
    # 미러링하고 있어서, 파일 전체에 정규식을 걸면 `  - ` 가 2배로 잡힌다.
    if not text.startswith("---\n"):
        print("  FAIL: frontmatter 로 시작하지 않는다")
        return False
    end = text.find("\n---\n", 4)
    if end == -1:
        print("  FAIL: frontmatter 종료 구분자 부재")
        return False
    front = text[4:end]

    m_versions = re.search(r"^versions: \[(.*?)\]$", front, re.MULTILINE)
    m_count = re.search(r"^version_count: (\d+)$", front, re.MULTILINE)
    if not m_versions or not m_count:
        print("  FAIL: frontmatter 에 versions / version_count 부재")
        return False
    versions = [v.strip() for v in m_versions.group(1).split(",") if v.strip()]
    declared = int(m_count.group(1))
    if len(versions) != declared:
        print(f"  FAIL: version_count={declared} != versions 개수 {len(versions)}")
        return False

    sources = re.findall(r"^  - (.+)$", front, re.MULTILINE)
    if len(sources) != declared:
        print(f"  FAIL: frontmatter sources {len(sources)}건 != version_count {declared}")
        return False
    # 각 version 이 본문에 자기 섹션을 갖는가
    missing = [v for v in versions if f"\n## {v}\n" not in text]
    if missing:
        print(f"  FAIL: 본문 섹션 부재: {missing}")
        return False
    print(f"  PASS: 커밋된 mirror 자기 정합 ({declared} version, sources {len(sources)}건)")
    return True


# === Test 2: apply writes mirror ===
def test_apply_writes_mirror() -> bool:
    """apply 가 in-repo mirror file 생성하는지 확인."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = Path(tmp) / "fake_repo"
        repo_root.mkdir(parents=True, exist_ok=True)
        (repo_root / "ai-workflow" / "memory" / "release").mkdir(parents=True, exist_ok=True)
        (repo_root / "ai-workflow" / "memory" / "release" / "v0.7.24").mkdir(parents=True, exist_ok=True)

        result = _run_tool("--apply", repo_root=repo_root)
        if result.get("error"):
            print(f"  FAIL: tool error: {result['error']}")
            return False
        mirror = Path(result["inrepo_mirror"])
        if not mirror.exists():
            print(f"  FAIL: mirror file not created: {mirror}")
            return False
        if result.get("action_performed") != "written (fresh)":
            print(f"  FAIL: expected 'written (fresh)', got {result.get('action_performed')}")
            return False
        # mirror content 에 frontmatter + 15 version 모두 포함
        content = mirror.read_text(encoding="utf-8")
        if not content.startswith("---"):
            print(f"  FAIL: mirror missing frontmatter")
            return False
        for v in ["v0.1.0", "v0.6.3"]:
            if v not in content:
                print(f"  FAIL: mirror missing version {v}")
                return False
        print(f"  PASS: apply wrote mirror ({mirror.stat().st_size:,} bytes)")
        return True


# === Test 3: idempotency skip ===
def test_idempotency_skip() -> bool:
    """apply 후 재apply 시 skipped (identical)."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = Path(tmp) / "fake_repo"
        repo_root.mkdir(parents=True, exist_ok=True)
        (repo_root / "ai-workflow" / "memory" / "release").mkdir(parents=True, exist_ok=True)
        (repo_root / "ai-workflow" / "memory" / "release" / "v0.7.24").mkdir(parents=True, exist_ok=True)

        # 1st apply
        result1 = _run_tool("--apply", repo_root=repo_root)
        if result1.get("error") or result1.get("action_performed") != "written (fresh)":
            print(f"  FAIL: 1st apply: {result1.get('error') or result1.get('action_performed')}")
            return False
        # 2nd apply (동일 external content, 동일 git HEAD, 거의 동일 hash)
        # commit 이 동일 hash 로 evaluate 되므로 content 동일 → identical
        result2 = _run_tool("--apply", repo_root=repo_root)
        if result2.get("error"):
            print(f"  FAIL: 2nd apply tool error: {result2['error']}")
            return False
        action = result2.get("action_performed")
        if action not in ("skipped (identical)", "skipped (drift — manual review)"):
            print(f"  FAIL: 2nd apply expected idempotency, got {action}")
            return False
        print(f"  PASS: 2nd apply idempotent ({action})")
        return True


# === Test 4: drift warning ===
def test_drift_warning() -> bool:
    """mirror file 의 frontmatter 를 *의도적으로* 변조 → drift 감지 + skip."""
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = Path(tmp) / "fake_repo"
        repo_root.mkdir(parents=True, exist_ok=True)
        (repo_root / "ai-workflow" / "memory" / "release").mkdir(parents=True, exist_ok=True)
        (repo_root / "ai-workflow" / "memory" / "release" / "v0.7.24").mkdir(parents=True, exist_ok=True)

        # 1st apply
        result1 = _run_tool("--apply", repo_root=repo_root)
        if result1.get("error"):
            print(f"  FAIL: 1st apply: {result1['error']}")
            return False
        mirror = Path(result1["inrepo_mirror"])
        # mirror 변조
        original = mirror.read_text(encoding="utf-8")
        tampered = original.replace("last_touched: 2026-06-15", "last_touched: 2027-01-01")
        mirror.write_text(tampered, encoding="utf-8")
        # 2nd apply → drift
        result2 = _run_tool("--apply", repo_root=repo_root)
        if result2.get("error"):
            print(f"  FAIL: 2nd apply tool error: {result2['error']}")
            return False
        if result2.get("drift", {}).get("status") != "drift":
            print(f"  FAIL: expected drift, got {result2.get('drift')}")
            return False
        if result2.get("action_performed") != "skipped (drift — manual review)":
            print(f"  FAIL: expected 'skipped (drift — manual review)', got {result2.get('action_performed')}")
            return False
        # tampered file 이 그대로 보존됨 (덮어쓰기 안 됨)
        if mirror.read_text(encoding="utf-8") != tampered:
            print(f"  FAIL: mirror was overwritten despite drift")
            return False
        print("  PASS: drift detected + skipped (manual review)")
        return True


# === Test 5: unknown args (no --dry-run / --apply) ===
def test_unknown_args() -> bool:
    """--dry-run / --apply 모두 부재 시 argparse error."""
    cmd = [PYTHON, str(TOOL), "--json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if proc.returncode == 0:
        print(f"  FAIL: expected argparse error, got success")
        return False
    if "at least one of --dry-run or --apply" not in proc.stderr:
        print(f"  FAIL: expected argparse error message, got: {proc.stderr[:200]}")
        return False
    print("  PASS: argparse rejects missing mode flag")
    return True


# === Main ===
def main() -> int:
    print("=" * 60)
    print("migrate_legacy_l2 smoke test (v0.7.25)")
    print("=" * 60)

    tests = [
        test_dry_run_detect_legacy,
        test_apply_writes_mirror,
        test_idempotency_skip,
        test_drift_warning,
        test_unknown_args,
        test_committed_mirror_is_self_consistent,
    ]
    passed = 0
    for test in tests:
        print(f"\n{test.__name__}:")
        if test():
            passed += 1

    print()
    print("=" * 60)
    print(f"Result: {passed}/{len(tests)} PASS")
    print("=" * 60)
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
