#!/usr/bin/env python3
"""Python ↔ Go 순수 판정 차분 검사 · corpus (M-054 WBS-54.3, hub_go_spec §5.1 · §5.2).

검사 구성:
  1. corpus 완비 — 7개 op 모두 fixture/*.jsonl + edge/*.jsonl 존재 및 비어 있지 않음
  2. 7개 op 바이트 차분 — fixture + edge + 이 저장소 실데이터(git ls-files · git show 이력)
     를 `python -m workflow_kit.judgecli <op> --batch` 와 `workflow-hub judge <op> --batch` 에
     넣어 stdout 바이트 불일치 0 확인
  3. 프로토콜 오류 일치 — 모르는 op · 모르는 필드 · 프로토콜 불일치 · 잘못된 JSON · 잘못된 옵션
     시 양쪽 모두 종료 코드 2 및 동일 error_code 출력
  4. 양방향 되주입 — Python 출력 1줄 변조 → red, Go 출력 1줄 변조 → red 확인
"""

from __future__ import annotations

CHECK_TIMEOUT_S = 180
REQUIRES_QUIET_REPO = True

WATCHES = (
    "ai-workflow/memory/active/*",
    "docs/PROJECT_PROFILE.md",
    "hub-go/*",
    "workflow-source/pyproject.toml",
    "workflow-source/workflow_kit/*",
)

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "workflow-source"
HUB_GO = REPO_ROOT / "hub-go"
CORPUS_DIR = HUB_GO / "testdata" / "corpus"

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from workflow_kit.common.project_docs import TASK_FIELD_ALIASES  # noqa: E402
from workflow_kit.common.state.roadmap import assemble_roadmap, collect_task_wbs_links  # noqa: E402

OPS: tuple[str, ...] = (
    "plan.lint",
    "plan.states",
    "task.status",
    "wbs.gate",
    "roadmap.derive",
    "handoff.parse",
    "state.build",
)

_passes: list[str] = []
_failures: list[str] = []
_skips: list[str] = []


def _record(case: str, ok: bool, detail: str = "") -> None:
    (_passes if ok else _failures).append(case if ok else f"{case}: {detail}")
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  {case}: {status}{suffix}")


def _py_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    parts = [str(SOURCE_ROOT)] + ([existing] if existing else [])
    env["PYTHONPATH"] = os.pathsep.join(parts)
    env["PYTHONUTF8"] = "1"
    return env


def _go_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GOTOOLCHAIN"] = "local"
    env["CGO_ENABLED"] = "0"
    return env


def _probe_go() -> tuple[bool, str, str]:
    go_mod = HUB_GO / "go.mod"
    declared = ""
    if go_mod.is_file():
        for line in go_mod.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s.startswith("go "):
                declared = s.split(None, 1)[1].strip()
                break
    exe = shutil.which("go")
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
        return False, "", f"go version 오류(rc={proc.returncode})"
    m = re.search(r"\bgo(\d+\.\d+(?:\.\d+)?)\b", proc.stdout)
    actual = m.group(1) if m else ""
    if declared and actual != declared:
        return False, exe, f"go 판 불일치: 호스트 {actual} != go.mod {declared}"
    return True, exe, ""


def _git_lines(*args: str) -> list[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=30,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        return []
    return [line for line in proc.stdout.splitlines() if line]


def _git_show(spec: str) -> str | None:
    proc = subprocess.run(
        ["git", "show", spec],
        cwd=str(REPO_ROOT),
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return None
    try:
        return proc.stdout.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _extract_task_plan_inputs_from_text(text: str, rel: str) -> dict[str, Any]:
    lines = text.splitlines()
    # done_criteria 추출 (plan_tasks.read_task_plan 과 같은 기준)
    criteria_aliases = tuple(TASK_FIELD_ALIASES["done_criteria"])
    criteria: list[str] = []
    capture = False
    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(f"- {alias}:") for alias in criteria_aliases):
            val = stripped.split(":", 1)[1].strip()
            if val:
                criteria.append(val)
                capture = False
            else:
                capture = True
            continue
        if capture:
            if stripped.startswith("- "):
                item = stripped[2:].strip()
                if item:
                    criteria.append(item)
            elif stripped == "":
                continue
            else:
                capture = False
    return {"plan_md": text, "criteria": criteria, "line_counts": None, "_source": rel}


def _collect_live_inputs(op: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if op == "plan.lint":
        tracked_tasks = sorted(_git_lines("ls-files", "ai-workflow/memory/active/main/backlog/tasks/TASK-*.md"))
        for rel in tracked_tasks:
            p = REPO_ROOT / rel
            if not p.is_file():
                continue
            raw = p.read_bytes().decode("utf-8")
            parsed = _extract_task_plan_inputs_from_text(raw, rel)
            parsed.pop("_source", None)
            items.append(parsed)
        # 이력 1건 (plan_claims 도입 이후 커밋 중 가장 최근 변경분 1회 과거 판)
        hist_revs = _git_lines("log", "-n", "2", "--skip=1", "--format=%H", "--", "ai-workflow/memory/active/main/backlog/tasks/")
        if hist_revs:
            rev = hist_revs[0]
            hist_files = _git_lines("diff-tree", "--no-commit-id", "--name-only", "-r", rev, "--", "ai-workflow/memory/active/main/backlog/tasks/")
            for rel in hist_files[:5]:
                hist_text = _git_show(f"{rev}:{rel}")
                if hist_text is not None:
                    parsed = _extract_task_plan_inputs_from_text(hist_text, rel)
                    parsed.pop("_source", None)
                    items.append(parsed)
    elif op == "plan.states":
        resp_root = REPO_ROOT / "ai-workflow" / "memory" / "active" / "main" / "plan_responses"
        if resp_root.is_dir():
            import base64
            for task_dir in sorted(resp_root.iterdir()):
                if not task_dir.is_dir():
                    continue
                task_file = REPO_ROOT / "ai-workflow" / "memory" / "active" / "main" / "backlog" / "tasks" / f"{task_dir.name}.md"
                if not task_file.is_file():
                    continue
                resps = []
                for rf in sorted(task_dir.rglob("*.md")):
                    resps.append({
                        "name": rf.name,
                        "bytes_b64": base64.b64encode(rf.read_bytes()).decode("ascii"),
                    })
                items.append({
                    "plan_md": task_file.read_bytes().decode("utf-8"),
                    "task_id": task_dir.name,
                    "responses": resps,
                })
    elif op in ("wbs.gate", "roadmap.derive"):
        rm_files = sorted(_git_lines("ls-files", "ai-workflow/memory/active/roadmap/*.md"))
        docs: dict[str, str] = {}
        for rel in rm_files:
            p = REPO_ROOT / rel
            if p.is_file():
                docs[p.name] = p.read_bytes().decode("utf-8")
        if "index.md" in docs:
            if op == "wbs.gate":
                items.extend([
                    {"roadmap_docs": docs, "wbs": None},
                    {"roadmap_docs": docs, "wbs": "exempt", "exempt_reason": "실데이터 검증"},
                    {"roadmap_docs": docs, "wbs": "M-054/WBS-54.3"},
                    {"roadmap_docs": docs, "wbs": "M-054/WBS-54.99"},
                ])
            else:
                links = [
                    {
                        "task_id": l.task_id,
                        "task_status": l.task_status,
                        "wbs_ref": l.wbs_ref,
                        "exempt_reason": l.exempt_reason,
                        "source_path": l.source_path,
                    }
                    for l in collect_task_wbs_links(REPO_ROOT)
                ]
                rm_obj, _ = assemble_roadmap(docs["index.md"], {k: v for k, v in docs.items() if k != "index.md"})
                deliv_map = {d: (REPO_ROOT / d).exists() for m in rm_obj.milestones for d in m.deliverables}
                items.append({"roadmap_docs": docs, "links": links, "deliverables": deliv_map, "generated_at": "2026-11-22"})
                items.append({"roadmap_docs": docs, "links": links, "deliverables": None, "generated_at": "2026-11-22"})

                # 이력 판 로드맵 1개
                hist_revs = _git_lines("log", "-n", "2", "--skip=1", "--format=%H", "--", "ai-workflow/memory/active/roadmap/index.md")
                if hist_revs:
                    rev = hist_revs[0]
                    hist_names = _git_lines("ls-tree", "--name-only", f"{rev}:ai-workflow/memory/active/roadmap")
                    hdocs: dict[str, str] = {}
                    for fname in hist_names:
                        if fname.endswith(".md"):
                            htext = _git_show(f"{rev}:ai-workflow/memory/active/roadmap/{fname}")
                            if htext is not None:
                                hdocs[fname] = htext
                    if "index.md" in hdocs:
                        items.append({"roadmap_docs": hdocs, "links": links, "deliverables": None, "generated_at": "2026-11-22"})
    elif op == "handoff.parse":
        ho = REPO_ROOT / "ai-workflow" / "memory" / "active" / "main" / "session_handoff.md"
        if ho.is_file():
            items.append({"text": ho.read_bytes().decode("utf-8")})
        hist_revs = _git_lines("log", "-n", "2", "--skip=1", "--format=%H", "--", "ai-workflow/memory/active/main/session_handoff.md")
        if hist_revs:
            htext = _git_show(f"{hist_revs[0]}:ai-workflow/memory/active/main/session_handoff.md")
            if htext is not None:
                items.append({"text": htext})
    elif op == "state.build":
        tracked_state_globs = [
            "docs/PROJECT_PROFILE.md",
            "ai-workflow/memory/active/PURPOSE.md",
            "ai-workflow/memory/active/main/session_handoff.md",
            "ai-workflow/memory/active/main/backlog/*.md",
            "ai-workflow/memory/active/main/backlog/tasks/TASK-*.md",
            "ai-workflow/memory/active/main/sessions/*.md",
            "ai-workflow/memory/active/memory_index/entries/*.json",
        ]
        state_files: dict[str, str] = {}
        for rel in sorted(_git_lines("ls-files", *tracked_state_globs)):
            p = REPO_ROOT / rel
            if p.is_file():
                state_files[rel] = p.read_bytes().decode("utf-8")
        if "docs/PROJECT_PROFILE.md" in state_files:
            items.append({"files": state_files, "generated_at": "2026-11-22"})
    return items


def _load_op_requests(op: str) -> tuple[list[str], dict[str, int]]:
    lines: list[str] = []
    counts = {"fixture": 0, "edge": 0, "live": 0}
    for bucket in ("fixture", "edge"):
        p = CORPUS_DIR / bucket / f"{op}.jsonl"
        if not p.is_file():
            continue
        for raw in p.read_text(encoding="utf-8").splitlines():
            s = raw.strip()
            if s:
                lines.append(s)
                counts[bucket] += 1
    live_inputs = _collect_live_inputs(op)
    for inp in live_inputs:
        lines.append(json.dumps({"protocol": "judge/1", "input": inp}, ensure_ascii=False))
        counts["live"] += 1
    return lines, counts


def _run_batch(cmd: list[str], stdin_bytes: bytes, env: dict[str, str]) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        cmd,
        input=stdin_bytes,
        capture_output=True,
        env=env,
        timeout=90,
    )


def compare_batch_streams(op: str, req_lines: list[str], py_bytes: bytes, go_bytes: bytes) -> tuple[int, list[str]]:
    """두 --batch 출력 바이트 스트림을 줄 단위로 대조한다 -> (불일치 수, 첫 3건 요약)."""
    py_lines = py_bytes.splitlines()
    go_lines = go_bytes.splitlines()
    total = max(len(req_lines), len(py_lines), len(go_lines))
    mismatches = 0
    details: list[str] = []

    for idx in range(total):
        pl = py_lines[idx] if idx < len(py_lines) else b"<EOF>"
        gl = go_lines[idx] if idx < len(go_lines) else b"<EOF>"
        if pl != gl:
            mismatches += 1
            if len(details) < 3:
                req_summary = req_lines[idx][:120] if idx < len(req_lines) else "<none>"
                p_str = pl.decode("utf-8", errors="replace")[:240]
                g_str = gl.decode("utf-8", errors="replace")[:240]
                details.append(f"[{op} #{idx}] req={req_summary}\n        py={p_str}\n        go={g_str}")
    return mismatches, details


def case_1_corpus_present() -> None:
    missing: list[str] = []
    for op in OPS:
        for bucket in ("fixture", "edge"):
            p = CORPUS_DIR / bucket / f"{op}.jsonl"
            if not p.is_file():
                missing.append(f"{bucket}/{op}.jsonl(부재)")
                continue
            non_empty = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if not non_empty:
                missing.append(f"{bucket}/{op}.jsonl(비어 있음)")
    _record(
        "case 1 (corpus 완비 — 7 op × fixture·edge JSONL 존재 및 비어 있지 않음)",
        not missing,
        ", ".join(missing) or f"14/14 파일 확인 ({CORPUS_DIR.relative_to(REPO_ROOT)})",
    )


def case_2_parity_all_ops(go_bin: Path) -> dict[str, tuple[list[str], bytes, bytes]]:
    artifacts: dict[str, tuple[list[str], bytes, bytes]] = {}
    problems: list[str] = []
    summary_parts: list[str] = []
    py_env = _py_env()
    go_env = _go_env()

    for op in OPS:
        req_lines, counts = _load_op_requests(op)
        stdin_bytes = ("\n".join(req_lines) + "\n").encode("utf-8")
        py_proc = _run_batch([sys.executable, "-m", "workflow_kit.judgecli", op, "--batch"], stdin_bytes, py_env)
        go_proc = _run_batch([str(go_bin), "judge", op, "--batch"], stdin_bytes, go_env)

        if py_proc.returncode != 0:
            err = py_proc.stdout.decode("utf-8", errors="replace") + py_proc.stderr.decode("utf-8", errors="replace")
            problems.append(f"{op} Python rc={py_proc.returncode}: {err[:200]}")
            continue
        if go_proc.returncode != 0:
            err = go_proc.stdout.decode("utf-8", errors="replace") + go_proc.stderr.decode("utf-8", errors="replace")
            problems.append(f"{op} Go rc={go_proc.returncode}: {err[:200]}")
            continue

        mismatches, mismatch_details = compare_batch_streams(op, req_lines, py_proc.stdout, go_proc.stdout)
        total = len(req_lines)
        matched = total - mismatches
        summary_parts.append(
            f"{op}: {matched}/{total} (fixture={counts['fixture']},edge={counts['edge']},live={counts['live']},mismatch={mismatches})"
        )
        print(f"    [op] {summary_parts[-1]}")
        if mismatches > 0:
            problems.append(f"{op} 불일치 {mismatches}건:\n      " + "\n      ".join(mismatch_details))
        else:
            artifacts[op] = (req_lines, py_proc.stdout, go_proc.stdout)

    _record(
        "case 2 (7개 op 바이트 차분 — fixture + edge + 실데이터 불일치 0)",
        not problems,
        "; ".join(problems) or f"{len(OPS)}/{len(OPS)} op 일치 100%",
    )
    return artifacts


def case_3_error_parity(go_bin: Path) -> None:
    error_cases = [
        ("unknown_op", ["bogus.op"], '{"protocol":"judge/1","input":{}}\n', "unknown_op"),
        ("bad_flag", ["--nope", "task.status"], "", "invalid_args"),
        ("invalid_json", ["task.status"], "{not-json\n", "invalid_json"),
        ("protocol_mismatch", ["task.status"], '{"protocol":"judge/0","input":{"operation_type":"update"}}\n', "protocol_mismatch"),
        ("unknown_env_field", ["task.status"], '{"protocol":"judge/1","input":{"operation_type":"update"},"extra":1}\n', "unknown_field"),
        ("unknown_input_field", ["wbs.gate"], '{"protocol":"judge/1","input":{"nope":true}}\n', "unknown_field"),
    ]
    py_env = _py_env()
    go_env = _go_env()
    problems: list[str] = []

    for label, args, raw_in, want_code in error_cases:
        py_p = subprocess.run([sys.executable, "-m", "workflow_kit.judgecli", *args], input=raw_in, capture_output=True, text=True, env=py_env, timeout=30, encoding="utf-8", errors="replace")
        go_p = subprocess.run([str(go_bin), "judge", *args], input=raw_in, capture_output=True, text=True, env=go_env, timeout=30, encoding="utf-8", errors="replace")
        if py_p.returncode != 2 or go_p.returncode != 2:
            problems.append(f"{label}: rc py={py_p.returncode} go={go_p.returncode} (want 2)")
            continue
        try:
            po = json.loads(py_p.stdout)
            go_o = json.loads(go_p.stdout)
        except json.JSONDecodeError as exc:
            problems.append(f"{label}: 비JSON 오류 출력 {exc}")
            continue
        if po.get("error_code") != want_code or go_o.get("error_code") != want_code or po.get("protocol") != "judge/1" or go_o.get("protocol") != "judge/1":
            problems.append(f"{label}: error_code 어긋남 py={po} go={go_o} want={want_code}")

    _record(
        "case 3 (프로토콜 오류 parity — 모르는 op·필드·판 불일치 시 종료 코드 2 + error_code 일치)",
        not problems,
        "; ".join(problems) or f"{len(error_cases)}/{len(error_cases)} 오류 케이스 일치",
    )


def case_4_bidirectional_reinjection(artifacts: dict[str, tuple[list[str], bytes, bytes]], go_exe: str, go_bin: Path) -> None:
    problems: list[str] = []
    sample_op = "task.status"
    if sample_op not in artifacts:
        _record("case 4 (양방향 되주입 — Python 변조 · Go 변조 모두 red)", False, "기준 아티팩트 부재")
        return

    req_lines, py_bytes, go_bytes = artifacts[sample_op]
    stdin_bytes = ("\n".join(req_lines) + "\n").encode("utf-8")

    # 1) Python 정본 변조 복사본 → 실실행 출력과 정상 Go 출력 비교 시 mismatch 검출
    with tempfile.TemporaryDirectory(prefix="parity-py-inj-") as tmpdir:
        tmp_pkg = Path(tmpdir) / "workflow_kit"
        shutil.copytree(SOURCE_ROOT / "workflow_kit", tmp_pkg, ignore=shutil.ignore_patterns("__pycache__"))
        jcli = tmp_pkg / "judgecli.py"
        orig_py = jcli.read_text(encoding="utf-8")
        patched_py = orig_py.replace(
            'return {"status": status, "warnings": list(warnings)}',
            'return {"status": "TAMPERED", "warnings": list(warnings)}',
            1,
        )
        if patched_py == orig_py:
            problems.append("Python 되주입 패치 대상 미발견")
        else:
            jcli.write_text(patched_py, encoding="utf-8")
            tamper_env = _py_env()
            tamper_env["PYTHONPATH"] = tmpdir
            py_bad = _run_batch([sys.executable, "-m", "workflow_kit.judgecli", sample_op, "--batch"], stdin_bytes, tamper_env)
            if py_bad.returncode != 0:
                problems.append(f"변조 Python 실행 실패(rc={py_bad.returncode})")
            else:
                m_py, _ = compare_batch_streams(sample_op, req_lines, py_bad.stdout, go_bytes)
                if m_py < 1:
                    problems.append("Python 변조 시 차분 검사가 불일치를 잡지 못했다")

    # 2) Go 판 변조 복사본 빌드 → 정상 Python 출력과 비교 시 mismatch 검출
    with tempfile.TemporaryDirectory(prefix="parity-go-inj-") as tmpdir:
        tmp_hub_go = Path(tmpdir) / "hub-go"
        shutil.copytree(HUB_GO, tmp_hub_go, ignore=shutil.ignore_patterns("bin"))
        ts_go = tmp_hub_go / "internal" / "judge" / "cli.go"
        orig_go = ts_go.read_text(encoding="utf-8")
        patched_go = orig_go.replace(
            "Status:   status,",
            'Status:   status + "-TAMPERED",',
            1,
        )
        if patched_go == orig_go:
            problems.append("Go 되주입 패치 대상 미발견")
        else:
            ts_go.write_text(patched_go, encoding="utf-8")
            bad_bin = Path(tmpdir) / ("workflow-hub-bad.exe" if os.name == "nt" else "workflow-hub-bad")
            bproc = subprocess.run(
                [go_exe, "build", "-o", str(bad_bin), "./cmd/workflow-hub"],
                cwd=str(tmp_hub_go),
                env=_go_env(),
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="replace",
            )
            if bproc.returncode != 0 or not bad_bin.is_file():
                problems.append(f"변조 Go 빌드 실패: {(bproc.stdout + bproc.stderr).strip()[:200]}")
            else:
                go_bad = _run_batch([str(bad_bin), "judge", sample_op, "--batch"], stdin_bytes, _go_env())
                if go_bad.returncode != 0:
                    problems.append(f"변조 Go 실행 실패(rc={go_bad.returncode})")
                else:
                    m_go, _ = compare_batch_streams(sample_op, req_lines, py_bytes, go_bad.stdout)
                    if m_go < 1:
                        problems.append("Go 변조 시 차분 검사가 불일치를 잡지 못했다")

    _ = go_bin
    _record(
        "case 4 (양방향 되주입 — Python 변조 · Go 변조 실실행 모두 red)",
        not problems,
        "; ".join(problems) or "양방향 실실행 변조 모두 불일치 검출 확인",
    )


def main() -> int:
    print("=== 순수 판정 차분 검사 · corpus (M-054 WBS-54.3) ===")
    case_1_corpus_present()

    measured, go_exe, reason = _probe_go()
    if not measured:
        _skips.append(f"case 2~4 ({reason} — 미측정)")
        print(f"  [unmeasured] {reason}")
    else:
        with tempfile.TemporaryDirectory(prefix="judge-parity-") as tmpdir:
            go_bin = Path(tmpdir) / ("workflow-hub.exe" if os.name == "nt" else "workflow-hub")
            build = subprocess.run(
                [go_exe, "build", "-o", str(go_bin), "./cmd/workflow-hub"],
                cwd=str(HUB_GO),
                env=_go_env(),
                capture_output=True,
                text=True,
                timeout=120,
                encoding="utf-8",
                errors="replace",
            )
            if build.returncode != 0 or not go_bin.is_file():
                _record("go build (judge parity 바이너리 빌드)", False, (build.stdout + build.stderr).strip()[:300])
            else:
                artifacts = case_2_parity_all_ops(go_bin)
                case_3_error_parity(go_bin)
                case_4_bidirectional_reinjection(artifacts, go_exe, go_bin)

    total = len(_passes) + len(_failures)
    unmeas = f" · 미측정 {len(_skips)}" if _skips else ""
    print(f"\n{len(_passes)}/{total} passed{unmeas}")
    if _failures:
        for f in _failures:
            print(f"  ✗ {f}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
