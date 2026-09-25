"""pre-push hook installer smoke (TASK-2026-08-08-main-019, §0.8 #4)

`tools/install_pre_push_hook.py` 의 3 sub-command (install / uninstall / status) +
hook script 의 force 차단 동작 검증. stdlib only. *로컬 repo 격리* — 실제
`/Users/yklee/repos/standard_ai_workflow/.git/hooks/` 를 건드리지 않고, 별도 temp
git repo 에서 검증. **in-process** 함수 호출 (subprocess mock 한계 회피 — installer
의 *logic* 자체가 검증 대상).

검증 케이스 (8):
    1. dry-run install — hook 파일 *생성 안됨*, report 만 emit
    2. install --apply — hook 파일 *생성됨*, mode 0o755
    3. install idempotent — 두 번 install, backup 0개 유지, hook content 동일
    4. install with existing — 기존 hook backup 됨, 새 hook 설치, backup 1개
    5. status — installed / matches_src / backups 정확
    6. **실제 `git push`** 로 bare remote 에 — force non-ff 거부(원격 불변) · 원격 sha 미상
       거부 · 새 ref / fast-forward / ff 인 `--force` / 삭제 / `--no-verify` 통과.
       + **되주입**: 판정을 뺀 변형 hook 으로 같은 시나리오를 돌려 결과가 갈리는지 본다.
       (이전 case 6 은 스크립트에 `--force` 를 **인자로 직접** 넘겼다 — git 은 push 옵션을
       hook 에 넘기지 않으므로 인터페이스를 재지 않았고, hook 은 실제 force push 에 무력했다.
       2026-09-25 실측, TASK-2026-09-25-main-002)
    7. uninstall — hook 제거 + backup 에서 복원
    8. **mock 없이** cwd 의 git root 를 고르는가 + hook 원본이 실재하는가
       (1~7 은 `_git_root` 를 monkeypatch 해서 그 둘을 한 번도 재지 않았다)

Stdlib only. subprocess (for hook script test) + os + stat + tempfile.
"""

from __future__ import annotations

#: 이 검사의 입력 표면 (spec `core/test_impact_tiering_spec.md` §2).
#: 게이트 채취 실측에서 뽑아 넓은 쪽으로 올렸다 — 좁으면 meta-watch 가 red 로 잡는다.
WATCHES = (
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import argparse
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.tools import install_pre_push_hook  # noqa: E402

HOOK_SOURCE = (
    REPO_ROOT / "workflow-source" / "workflow_kit" / "assets" / "hooks"
    / "pre-push-no-force.sh"
)


def _git(cwd: Path, *args: str, hooks: Path | None = None) -> subprocess.CompletedProcess[str]:
    """``hooks`` 를 주면 그 디렉터리를 hooksPath 로 고정한다 — 사용자 전역 `core.hooksPath`
    가 있으면 `.git/hooks` 가 무시되어 검사가 엉뚱한 hook(또는 없음)을 잰다."""
    pre = ["-c", f"core.hooksPath={hooks}"] if hooks is not None else []
    return subprocess.run(["git", *pre, *args], cwd=cwd, capture_output=True, text=True, timeout=60)


def _commit(work: Path, tag: str) -> None:
    (work / "push-case.txt").write_text(f"{tag}\n", encoding="utf-8")
    _git(work, "add", "push-case.txt")
    _git(work, "commit", "-q", "-m", tag)


def _real_push_outcomes(work: Path, hooks: Path, remote: Path) -> dict:
    """새 bare remote 에 실제 `git push` 시나리오를 돌린다. 이름 → (rc, stderr)."""
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True, capture_output=True)
    _git(work, "remote", "remove", "origin")
    _git(work, "remote", "add", "origin", str(remote))
    out: dict = {}

    def push(name: str, *args: str) -> None:
        r = _git(work, "push", "origin", *args, hooks=hooks)
        out[name] = (r.returncode, r.stderr)

    def remote_main() -> str:
        return _git(work, "ls-remote", str(remote), "refs/heads/main").stdout.split("\t")[0]

    push("new_ref", "HEAD:refs/heads/main")
    _commit(work, f"{remote.name}-ff")
    push("ff", "HEAD:refs/heads/main")
    _git(work, "reset", "-q", "--hard", "HEAD~1")
    _commit(work, f"{remote.name}-diverge")
    before = remote_main()
    push("force_nonff", "--force", "HEAD:refs/heads/main")
    out["force_nonff_remote_moved"] = remote_main() != before
    push("no_verify", "--force", "--no-verify", "HEAD:refs/heads/main")
    _commit(work, f"{remote.name}-ff2")
    push("force_ff", "--force", "HEAD:refs/heads/main")
    # 다른 클론이 올린 커밋을 이 저장소는 모른다 (fetch 안 함)
    other = remote.parent / f"{remote.stem}-other"
    subprocess.run(["git", "clone", "-q", "-b", "main", str(remote), str(other)],
                   check=True, capture_output=True)
    for key, val in (("user.email", "o@o"), ("user.name", "o")):
        _git(other, "config", key, val)
    _commit(other, f"{remote.name}-other")
    pushed = _git(other, "push", "-q", "origin", "HEAD:refs/heads/main", hooks=other / ".git" / "hooks")
    # 준비가 조용히 실패하면 아래 push 는 평범한 fast-forward 가 되어 아무것도 안 잰다
    out["unknown_setup"] = (pushed.returncode, pushed.stderr)
    _commit(work, f"{remote.name}-blind")
    push("unknown_remote", "--force", "HEAD:refs/heads/main")
    push("side", "HEAD:refs/heads/side")
    push("delete", ":refs/heads/side")
    return out


def main() -> int:
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        # 격리: 별도 git repo 생성
        repo_dir = Path(tmp) / "test_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.email", "test@test"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "config", "user.name", "test"], cwd=repo_dir, capture_output=True, check=True)
        (repo_dir / "README.md").write_text("test\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, capture_output=True, check=True)

        hook_target = repo_dir / ".git" / "hooks" / "pre-push"

        # _git_root(REPO_ROOT) → repo_dir mock (in-process 함수 호출용)
        original_git_root = install_pre_push_hook._git_root
        install_pre_push_hook._git_root = lambda cwd: repo_dir
        try:
            # 1) dry-run install — args.dry_run → --apply not set
            ns = argparse.Namespace(apply=False)
            install_pre_push_hook.cmd_install(ns)
            if hook_target.exists():
                failures.append(f"[1] dry-run: hook created (should NOT be created)")
            else:
                print("  [1] dry-run install        ✓  (hook 미생성, preview 만)")

            # 2) install --apply
            ns = argparse.Namespace(apply=True)
            install_pre_push_hook.cmd_install(ns)
            if not hook_target.is_file():
                failures.append(f"[2] install --apply: hook not created")
            elif stat.S_IMODE(os.stat(hook_target).st_mode) != 0o755:
                failures.append(f"[2] install --apply: mode {oct(stat.S_IMODE(os.stat(hook_target).st_mode))} != 0o755")
            elif hook_target.read_bytes() != HOOK_SOURCE.read_bytes():
                failures.append(f"[2] install --apply: content differs from source")
            else:
                print("  [2] install --apply        ✓  (hook 생성, mode 0o755, content 동일)")

            # 3) idempotent — 두 번 install
            backups_before = list((repo_dir / ".git" / "hooks").glob("pre-push.bak.*"))
            install_pre_push_hook.cmd_install(argparse.Namespace(apply=True))
            backups_after = list((repo_dir / ".git" / "hooks").glob("pre-push.bak.*"))
            if len(backups_after) != len(backups_before):
                failures.append(f"[3] idempotent: backup created on identical content ({len(backups_after)} vs {len(backups_before)})")
            else:
                print(f"  [3] idempotent              ✓  (2회 install, backup {len(backups_after)}개 유지)")

            # 4) install with existing — 기존 hook 다른 내용
            custom_old = "#!/bin/sh\necho custom\n"
            hook_target.write_text(custom_old, encoding="utf-8")
            hook_target.chmod(0o755)
            install_pre_push_hook.cmd_install(argparse.Namespace(apply=True))
            backups_now = sorted((repo_dir / ".git" / "hooks").glob("pre-push.bak.*"))
            if len(backups_now) != 1:
                failures.append(f"[4] existing: expected 1 backup, got {len(backups_now)}")
            elif backups_now[0].read_text(encoding="utf-8") != custom_old:
                failures.append(f"[4] existing: backup content != original")
            elif hook_target.read_bytes() != HOOK_SOURCE.read_bytes():
                failures.append(f"[4] existing: hook not replaced with source")
            else:
                print(f"  [4] install with existing   ✓  (backup 1개, hook 교체)")

            # 5) status (in-process, capture stdout)
            import io
            import contextlib
            buf = io.StringIO()
            ns = argparse.Namespace(json=True)
            with contextlib.redirect_stdout(buf):
                install_pre_push_hook.cmd_status(ns)
            payload = json.loads(buf.getvalue())
            if not payload.get("hook_installed"):
                failures.append(f"[5] status: hook_installed should be True")
            elif not payload.get("hook_matches_source"):
                failures.append(f"[5] status: hook_matches_source should be True")
            elif len(payload.get("backups", [])) != 1:
                failures.append(f"[5] status: backups count should be 1, got {payload.get('backups')}")
            else:
                print("  [5] status                 ✓  (installed=True, matches_source=True, backups=1)")

            # 6) 실제 git push — git 이 hook 에 넘기는 인터페이스(인자 2개 + stdin ref 줄)로 잰다
            real = _real_push_outcomes(repo_dir, hook_target.parent, Path(tmp) / "remote-real.git")
            expected = {
                "new_ref": 0, "ff": 0, "force_nonff": 1, "no_verify": 0,
                "force_ff": 0, "unknown_remote": 1, "delete": 0,
            }
            for name, want in expected.items():
                got_rc, err = real[name]
                if got_rc != want:
                    failures.append(f"[6] {name}: git push rc={got_rc} (expected {want}) {err[-200:]!r}")
            if real["unknown_setup"][0] != 0:
                failures.append(f"[6] unknown_remote 준비 실패 — 다른 클론이 못 올렸다: {real['unknown_setup'][1][-200:]!r}")
            if real["force_nonff_remote_moved"]:
                failures.append("[6] force_nonff: 거부됐다면서 원격 ref 가 바뀌었다")
            if "non-fast-forward" not in real["force_nonff"][1]:
                failures.append("[6] force_nonff: 거부 사유가 non-fast-forward 를 말하지 않는다")
            if "모른다" not in real["unknown_remote"][1]:
                failures.append("[6] unknown_remote: 거부 사유가 '원격 sha 를 모른다' 를 말하지 않는다")
            # 되주입 — 판정을 빼면(조상 검사 무력화) 같은 시나리오가 갈려야 한다
            mutant_dir = Path(tmp) / "mutant-hooks"
            mutant_dir.mkdir()
            source = HOOK_SOURCE.read_text(encoding="utf-8")
            needle = 'if git merge-base --is-ancestor "$remote_sha" "$local_sha" 2>/dev/null; then'
            if needle not in source:
                failures.append("[6] 되주입 지점(조상 검사)이 hook 원본에 없다 — 판정이 바뀌었나")
            else:
                mutant = mutant_dir / "pre-push"
                mutant.write_text(source.replace(needle, "if true; then"), encoding="utf-8")
                mutant.chmod(0o755)
                mut = _real_push_outcomes(repo_dir, mutant_dir, Path(tmp) / "remote-mutant.git")
                if mut["force_nonff"][0] != 0 or mut["unknown_remote"][0] != 0:
                    failures.append(
                        "[6] 되주입이 red 를 못 만든다 — 조상 검사를 빼도 시나리오 결과가 같다 "
                        f"(force_nonff rc={mut['force_nonff'][0]}, unknown rc={mut['unknown_remote'][0]})")
            if not any(f.startswith("[6]") for f in failures):
                print("  [6] 실제 git push          ✓  (force non-ff·원격 미상 거부, 5 경로 통과, 되주입 발화)")

            # 7) uninstall — hook 제거 + backup 복원
            install_pre_push_hook.cmd_uninstall(argparse.Namespace(apply=True))
            if not hook_target.is_file():
                failures.append(f"[7] uninstall: hook not restored from backup")
            elif hook_target.read_text(encoding="utf-8") != custom_old:
                failures.append(f"[7] uninstall: restored content != original custom_old")
            else:
                print("  [7] uninstall              ✓  (hook 복원, backup 보존)")

        finally:
            install_pre_push_hook._git_root = original_git_root

        # 8) **mock 없이** — 대상 저장소를 cwd 에서 고른다.
        #
        # cases 1~7 은 `_git_root` 를 통째로 monkeypatch 해서 "어느 저장소를
        # 고르는가" 를 **한 번도 재지 않았다**. 그래서 `_git_root(REPO_ROOT)`
        # (= 모듈 파일 위치) 라는 결함이 7 case 를 전부 통과했고, 설치본에서는
        # git 저장소인 소비자 프로젝트에서도 `not a git repository` 가 났다
        # (2026-08-18 실측). 여기서만 진짜 프로세스를 띄운다.
        env = {**os.environ, "PYTHONPATH": str(SOURCE_ROOT)}
        proc = subprocess.run(
            [sys.executable, "-m", "workflow_kit.tools.install_pre_push_hook",
             "status", "--json"],
            cwd=str(repo_dir), capture_output=True, text=True, timeout=60, env=env,
        )
        if proc.returncode != 0:
            failures.append(f"[8] cwd 기준 status 실패 (exit {proc.returncode}): {proc.stderr.strip()[:200]}")
        else:
            try:
                got = json.loads(proc.stdout)
            except json.JSONDecodeError:
                got = {}
                failures.append(f"[8] status --json 출력이 JSON 이 아니다: {proc.stdout[:120]!r}")
            git_root = Path(got.get("git_root", "")).resolve() if got else None
            if got and git_root != repo_dir.resolve():
                failures.append(
                    f"[8] cwd 대신 다른 저장소를 골랐다: {git_root} != {repo_dir.resolve()}")
            elif got and not Path(got.get("source_path", "")).is_file():
                failures.append(f"[8] hook 원본이 없다: {got.get('source_path')}")
            elif got:
                print("  [8] cwd 기준 대상 선택     ✓  (mock 없이, hook 원본도 존재)")

    print()
    if failures:
        print(f"FAIL: {len(failures)} case(s) failed:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL PASS: pre-push hook installer — 8 case (dry-run / install / idempotent / existing / status / 실제 git push + 되주입 / uninstall / cwd 대상 선택)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

