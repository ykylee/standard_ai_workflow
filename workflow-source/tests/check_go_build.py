#!/usr/bin/env python3
"""Go 빌드 · 정적 검사 · 단위 테스트 · 6 대상 크로스 빌드 게이트 (M-052 WBS-52.1).

설계 정본: ``workflow-source/core/hub_go_spec.md`` §2 · §5.4 · §7, 요구 R31.1 · R31.3 · R32.1 · R32.2.

5 cases:
  1. go.mod 선언 — 모듈 경로 · go 판 고정 · cmd/workflow-hub 파일 존재
  2. 미측정 판정 — go 실행 파일 부재 및 go.mod 판 불일치는 통과가 아니라 미측정
  3. go vet ./... · go test ./... 통과 (호스트에 선언 판 go 가 있을 때)
  4. 6 대상 크로스 빌드(linux/darwin/windows × amd64/arm64, CGO_ENABLED=0) · 판 주입(--version) · SHA256SUMS
  5. 되주입 — 깨진 테스트 · 깨진 코드에서 go test · go vet · go build 가 실제로 실패한다
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 180

WATCHES = (
    "hub-go/*",
    "workflow-source/pyproject.toml",
)

import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HUB_GO = REPO_ROOT / "hub-go"
GO_MOD = HUB_GO / "go.mod"
PYPROJECT = REPO_ROOT / "workflow-source" / "pyproject.toml"

EXPECTED_MODULE = "github.com/ykylee/standard_ai_workflow/hub-go"

TARGETS: tuple[tuple[str, str, bytes], ...] = (
    ("linux", "amd64", b"\x7fELF"),
    ("linux", "arm64", b"\x7fELF"),
    ("darwin", "amd64", b"\xcf\xfa\xed\xfe"),
    ("darwin", "arm64", b"\xcf\xfa\xed\xfe"),
    ("windows", "amd64", b"MZ"),
    ("windows", "arm64", b"MZ"),
)

_failures: list[str] = []
_passes: list[str] = []
_skips: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    print(f"  {case}: {'PASS' if ok else 'FAIL'}{(' — ' + detail) if detail else ''}")


def parse_go_mod(path: Path) -> tuple[str | None, str | None]:
    """``go.mod`` 에서 ``module`` 과 ``go`` 판을 읽는다."""
    if not path.is_file():
        return None, None
    mod: str | None = None
    go_ver: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("module "):
            mod = line.split(None, 1)[1].strip()
        elif line.startswith("go "):
            go_ver = line.split(None, 1)[1].strip()
    return mod, go_ver


def parse_pyproject_version(path: Path) -> str:
    """``workflow-source/pyproject.toml`` 의 ``[project] version`` 을 읽는다."""
    in_project = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("["):
            in_project = line == "[project]"
            continue
        if in_project:
            m = re.match(r'^version\s*=\s*"([^"]+)"', line)
            if m:
                return m.group(1)
    raise ValueError(f"[project] version 을 찾지 못했다: {path}")


def _go_env(**extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env["GOTOOLCHAIN"] = "local"
    env["CGO_ENABLED"] = "0"
    env.update(extra)
    return env


def probe_go(expected_go_ver: str, go_bin: str | None = None) -> tuple[bool, str, str]:
    """선언된 Go 도구 사슬 존재 여부와 판 일치를 확인한다 -> (measured, actual, reason)."""
    exe = shutil.which(go_bin) if go_bin is not None else shutil.which("go")
    if not exe:
        return False, "", "go 실행 파일이 PATH 에 없다"
    try:
        proc = subprocess.run(
            [exe, "version"],
            capture_output=True,
            text=True,
            env=_go_env(),
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, "", f"go version 실행 실패: {exc}"
    if proc.returncode != 0:
        return False, "", f"go version 오류(rc={proc.returncode}): {proc.stderr.strip()}"
    m = re.search(r"\bgo(\d+\.\d+(?:\.\d+)?)\b", proc.stdout)
    if not m:
        return False, "", f"go version 파싱 실패: {proc.stdout.strip()}"
    actual = m.group(1)
    if actual != expected_go_ver:
        return False, actual, f"go 판 불일치: 호스트 {actual} != go.mod {expected_go_ver}"
    return True, actual, ""


def _host_os_arch() -> tuple[str, str]:
    sys_name = platform.system().lower()
    mach = platform.machine().lower()
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    return sys_name, arch_map.get(mach, mach)


def case_1_go_mod_and_skeleton() -> tuple[str | None, str]:
    mod, go_ver = parse_go_mod(GO_MOD)
    main_go = HUB_GO / "cmd" / "workflow-hub" / "main.go"
    main_test = HUB_GO / "cmd" / "workflow-hub" / "main_test.go"
    kit_ver = parse_pyproject_version(PYPROJECT)
    ver_ok = bool(go_ver and re.fullmatch(r"\d+\.\d+\.\d+", go_ver))
    ok = (
        mod == EXPECTED_MODULE
        and ver_ok
        and main_go.is_file()
        and main_test.is_file()
        and bool(kit_ver)
    )
    detail = f"module={mod} go={go_ver} kit={kit_ver}"
    _record("case 1 (go.mod 선언 — 모듈 경로 · go 판 고정 · cmd/workflow-hub 뼈대)", ok, detail)
    return go_ver, kit_ver


def case_2_unmeasured_on_absent_or_mismatch(declared_go: str) -> None:
    m_absent, _, r_absent = probe_go(declared_go, go_bin="/nonexistent/go")
    problems: list[str] = []
    if m_absent or not r_absent:
        problems.append(f"부재 시 measured={m_absent} reason={r_absent!r}")
    if shutil.which("go"):
        m_mis, _, r_mis = probe_go("99.99.99")
        if m_mis or "불일치" not in r_mis:
            problems.append(f"판 불일치 시 measured={m_mis} reason={r_mis!r}")
    _record(
        "case 2 (미측정 판정 — Go 부재 · 판 불일치는 통과가 아니라 미측정)",
        not problems,
        "; ".join(problems) or "부재/불일치 모두 unmeasured 반환 확인",
    )


def case_3_vet_and_test(go_exe: str) -> None:
    problems: list[str] = []
    vet = subprocess.run(
        [go_exe, "vet", "./..."],
        cwd=str(HUB_GO),
        env=_go_env(),
        capture_output=True,
        text=True,
        timeout=60,
        encoding="utf-8",
        errors="replace",
    )
    if vet.returncode != 0:
        problems.append(f"go vet 실패(rc={vet.returncode}): {(vet.stdout + vet.stderr).strip()[:300]}")
    test = subprocess.run(
        [go_exe, "test", "-v", "./..."],
        cwd=str(HUB_GO),
        env=_go_env(),
        capture_output=True,
        text=True,
        timeout=60,
        encoding="utf-8",
        errors="replace",
    )
    if test.returncode != 0:
        problems.append(f"go test 실패(rc={test.returncode}): {(test.stdout + test.stderr).strip()[:300]}")
    _record(
        "case 3 (go vet ./... · go test ./... 통과)",
        not problems,
        "; ".join(problems) or "vet · test PASS",
    )


def case_4_cross_build_six_targets(go_exe: str, kit_ver: str) -> None:
    problems: list[str] = []
    host_os, host_arch = _host_os_arch()
    host_bin: Path | None = None
    checksum_lines: list[str] = []
    with tempfile.TemporaryDirectory(prefix="gobuild-") as tmpdir:
        out_dir = Path(tmpdir)
        for goos, goarch, magic in TARGETS:
            ext = ".exe" if goos == "windows" else ""
            name = f"workflow-hub-{kit_ver}-{goos}-{goarch}{ext}"
            out_path = out_dir / name
            proc = subprocess.run(
                [
                    go_exe,
                    "build",
                    "-trimpath",
                    "-ldflags",
                    f"-s -w -X main.version={kit_ver}",
                    "-o",
                    str(out_path),
                    "./cmd/workflow-hub",
                ],
                cwd=str(HUB_GO),
                env=_go_env(GOOS=goos, GOARCH=goarch),
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode != 0:
                problems.append(f"{goos}/{goarch} build 실패: {(proc.stdout + proc.stderr).strip()[:200]}")
                continue
            if not out_path.is_file():
                problems.append(f"{name} 미생성")
                continue
            data = out_path.read_bytes()
            if len(data) <= 500_000:
                problems.append(f"{name} 크기 비정상({len(data)} bytes)")
            if not data.startswith(magic):
                problems.append(f"{name} 매직 바이트 불일치({data[:4]!r} != {magic!r})")
            digest = hashlib.sha256(data).hexdigest()
            checksum_lines.append(f"{digest}  {name}")
            if (goos, goarch) == (host_os, host_arch):
                host_bin = out_path

        if host_bin is not None:
            vproc = subprocess.run(
                [str(host_bin), "--version"],
                capture_output=True,
                text=True,
                timeout=30,
                encoding="utf-8",
                errors="replace",
            )
            want_ver = f"workflow-hub {kit_ver}"
            if vproc.returncode != 0 or vproc.stdout.strip() != want_ver:
                problems.append(
                    f"--version 불일치: rc={vproc.returncode} out={vproc.stdout.strip()!r} want={want_ver!r}"
                )
        sums_file = out_dir / "SHA256SUMS"
        sums_file.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
        if len(checksum_lines) != len(TARGETS):
            problems.append(f"SHA256SUMS 줄 수 {len(checksum_lines)} != {len(TARGETS)}")

    _record(
        "case 4 (6 대상 크로스 빌드 · 판 주입 --version · SHA256SUMS)",
        not problems,
        "; ".join(problems) or f"6/6 대상 빌드 · {host_os}/{host_arch} --version={kit_ver} · SHA256SUMS 확인",
    )


def case_5_reinjection_catches_failures(go_exe: str) -> None:
    problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="gobuild-inject-") as tmpdir:
        copy_root = Path(tmpdir) / "hub-go"
        shutil.copytree(HUB_GO, copy_root, ignore=shutil.ignore_patterns("bin"))

        # 1) 깨진 테스트 주입 → go test 실패
        test_file = copy_root / "cmd" / "workflow-hub" / "main_test.go"
        test_file.write_text(
            test_file.read_text(encoding="utf-8")
            + '\nfunc TestInjectedFail(t *testing.T) { t.Fatal("injected") }\n',
            encoding="utf-8",
        )
        t_fail = subprocess.run(
            [go_exe, "test", "./..."],
            cwd=str(copy_root),
            env=_go_env(),
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
        if t_fail.returncode == 0:
            problems.append("깨진 테스트 주입 시 go test 가 통과했다")

        # 2) 컴파일 오류 주입 → go vet · go build 모두 실패
        main_file = copy_root / "cmd" / "workflow-hub" / "main.go"
        main_file.write_text(
            main_file.read_text(encoding="utf-8") + '\nvar _ int = "bad"\n',
            encoding="utf-8",
        )
        v_fail = subprocess.run(
            [go_exe, "vet", "./..."],
            cwd=str(copy_root),
            env=_go_env(),
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
        if v_fail.returncode == 0:
            problems.append("컴파일 오류 주입 시 go vet 이 통과했다")
        b_fail = subprocess.run(
            [go_exe, "build", "-o", str(Path(tmpdir) / "bad-bin"), "./cmd/workflow-hub"],
            cwd=str(copy_root),
            env=_go_env(),
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="replace",
        )
        if b_fail.returncode == 0:
            problems.append("컴파일 오류 주입 시 go build 가 통과했다")

    _record(
        "case 5 (되주입 — 깨진 테스트 · 깨진 코드에서 go test · vet · build 실패)",
        not problems,
        "; ".join(problems) or "3/3 되주입 red 확인",
    )


def main() -> int:
    print("=== Go 빌드 · 정적 검사 · 크로스 빌드 (M-052 WBS-52.1) ===")
    declared_go, kit_ver = case_1_go_mod_and_skeleton()
    case_2_unmeasured_on_absent_or_mismatch(declared_go or "1.26.8")

    if not declared_go:
        _skips.append("case 3~5 (go.mod 판 미선언 — 미측정)")
        print("    [unmeasured] go.mod 에서 go 판을 읽지 못했다")
    else:
        measured, _actual, reason = probe_go(declared_go)
        if not measured:
            _skips.append(f"case 3~5 ({reason} — 미측정)")
            print(f"    [unmeasured] {reason}")
        else:
            go_exe = shutil.which("go") or "go"
            case_3_vet_and_test(go_exe)
            case_4_cross_build_six_targets(go_exe, kit_ver)
            case_5_reinjection_catches_failures(go_exe)

    total = len(_passes) + len(_failures)
    print(f"\n{len(_passes)}/{total} passed" + (f" · 미측정 {len(_skips)}" if _skips else ""))
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
