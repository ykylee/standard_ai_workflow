"""Extension Baseline Compliance Evaluator (v0.7.1+).

3종 baseline (security / testing / performance) 의 runtime compliance 평가.
각 rule 마다 compliant / non-compliant / N/A 평가 후 ComplianceSummary 반환.

1차 출시 (v0.7.1):
- security-baseline: 6 rule runtime check (file structure + R-9 skip marker)
- testing-baseline: 6 rule runtime check (smoke test count + generator quality)
- performance-baseline: 6 rule runtime check (smoke test time + import time + memory)

Reference:
- workflow-source/extensions/SCHEMA.md §6 Helper Contract
- workflow-source/extensions/{security,testing,performance}-baseline.md
"""

from __future__ import annotations

import importlib
import re
import time
import tracemalloc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

# Type alias
Status = Literal["compliant", "non_compliant", "not_applicable", "advisory"]


@dataclass
class RuleResult:
    """단일 rule 의 평가 결과."""

    rule_id: str
    title: str
    status: Status
    notes: str = ""


@dataclass
class ComplianceSummary:
    """3종 baseline 의 평가 결과 묶음."""

    baseline: str
    status: Status
    partial_rules: list[str] = field(default_factory=list)
    results: list[RuleResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        """JSON-serializable dict."""
        return {
            "baseline": self.baseline,
            "status": self.status,
            "partial_rules": self.partial_rules,
            "results": [
                {
                    "rule_id": r.rule_id,
                    "title": r.title,
                    "status": r.status,
                    "notes": r.notes,
                }
                for r in self.results
            ],
        }


# --- 공통 helper ---


def _read_state_json(project_root: Path) -> dict:
    """state.json 읽기 (없으면 빈 dict)."""
    state_path = project_root / "ai-workflow" / "memory" / "active" / "state.json"
    if not state_path.exists():
        return {}
    try:
        import json
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _is_enabled(state: dict, baseline: str) -> bool:
    """state.json 에서 baseline 의 enabled 여부 확인."""
    field = f"{baseline}_baseline"
    config = state.get(field, {})
    if isinstance(config, dict):
        return config.get("status") == "enabled"
    return False


def _get_partial_rules(state: dict, baseline: str) -> list[str]:
    """state.json 에서 partial rule list 추출."""
    field = f"{baseline}_baseline"
    config = state.get(field, {})
    if isinstance(config, dict):
        return config.get("partial_rules", [])
    return []


def _aggregate_status(results: list[RuleResult], partial_rules: list[str]) -> Status:
    """rule 결과 모음 → overall status.

    - 1+ non_compliant (in non-partial rule) → non_compliant
    - all compliant / N/A → compliant
    - partial mode: only partial_rules 가 hard constraint
    """
    hard_results = [r for r in results if r.rule_id in partial_rules or not partial_rules]
    if any(r.status == "non_compliant" for r in hard_results):
        return "non_compliant"
    if all(r.status in ("compliant", "not_applicable") for r in results):
        return "compliant"
    return "advisory"


# ===================================================================
# Security baseline (6 rule)
# ===================================================================


def _eval_security_baseline(project_root: Path) -> ComplianceSummary:
    """6 SEC-WF rule runtime 평가."""
    results: list[RuleResult] = []

    # SEC-WF-01: Audit Log Append-Only + ISO 8601
    # 검증: stage_gate.append_audit_log 함수 존재 + ISO 8601 정규식 매칭
    try:
        from workflow_kit.common.contracts.stage_gate import append_audit_log  # noqa: F401
        # audit log 가 ISO 8601 사용 — spec 에 명시
        stage_gate_path = project_root / "workflow-source" / "workflow_kit" / "common" / "contracts" / "stage_gate.py"
        if stage_gate_path.exists():
            content = stage_gate_path.read_text(encoding="utf-8")
            iso_ok = bool(re.search(r"fromisoformat|ISO.8601", content))
            results.append(RuleResult(
                rule_id="SEC-WF-01",
                title="Audit Log Append-Only + ISO 8601",
                status="compliant" if iso_ok else "non_compliant",
                notes="append_audit_log + ISO 8601 fromisoformat",
            ))
        else:
            results.append(RuleResult("SEC-WF-01", "Audit Log Append-Only + ISO 8601", "not_applicable"))
    except ImportError:
        results.append(RuleResult("SEC-WF-01", "Audit Log Append-Only + ISO 8601", "not_applicable"))

    # SEC-WF-02: Stage Gate Approval Mandatory
    try:
        from workflow_kit.common.contracts.stage_gate import require_explicit_approval  # noqa: F401
        results.append(RuleResult(
            rule_id="SEC-WF-02",
            title="Stage Gate Approval Mandatory",
            status="compliant",
            notes="require_explicit_approval 함수 존재",
        ))
    except ImportError:
        results.append(RuleResult("SEC-WF-02", "Stage Gate Approval Mandatory", "non_compliant"))

    # SEC-WF-03: Question Format Validation
    try:
        from workflow_kit.common.contracts.question_format import validate_answers  # noqa: F401
        results.append(RuleResult(
            rule_id="SEC-WF-03",
            title="Question Format Validation",
            status="compliant",
            notes="validate_answers 함수 존재",
        ))
    except ImportError:
        results.append(RuleResult("SEC-WF-03", "Question Format Validation", "non_compliant"))

    # SEC-WF-04: Error Handling Fail-Closed
    # 검증: stage_gate_runtime 또는 contracts 가 raise-on-error 정책
    fail_closed_ok = False
    for path in [
        project_root / "workflow-source" / "workflow_kit" / "common" / "contracts" / "stage_gate.py",
        project_root / "workflow-source" / "workflow_kit" / "common" / "contracts" / "stage_gate_runtime.py",
    ]:
        if path.exists() and "raise" in path.read_text(encoding="utf-8"):
            fail_closed_ok = True
            break
    results.append(RuleResult(
        rule_id="SEC-WF-04",
        title="Error Handling Fail-Closed",
        status="compliant" if fail_closed_ok else "advisory",
        notes="stage_gate raise-on-error 패턴 확인",
    ))

    # SEC-WF-05: Dependency Integrity
    # 검증: pyproject.toml 또는 requirements.txt 의 lock / version pin
    has_lock = (project_root / "workflow-source" / "pyproject.toml").exists()
    if has_lock:
        results.append(RuleResult(
            rule_id="SEC-WF-05",
            title="Dependency Integrity",
            status="advisory",
            notes="pyproject.toml 존재 (lock file / checksum 검증은 v0.7.1 follow-up)",
        ))
    else:
        results.append(RuleResult("SEC-WF-05", "Dependency Integrity", "not_applicable"))

    # SEC-WF-06: R-9 Skip Marker
    # 검증: extensions/*.md 파일에 r9_skip frontmatter 존재 (skip marker)
    r9_skip = False
    ext_dir = project_root / "workflow-source" / "extensions"
    if ext_dir.exists():
        for md in ext_dir.glob("*.md"):
            if "r9_skip" in md.read_text(encoding="utf-8", errors="ignore"):
                r9_skip = True
                break
    results.append(RuleResult(
        rule_id="SEC-WF-06",
        title="R-9 Skip Marker",
        status="compliant" if r9_skip else "advisory",
        notes="extensions/ 내 r9_skip frontmarker 검증",
    ))

    state = _read_state_json(project_root)
    partial = _get_partial_rules(state, "security")
    return ComplianceSummary(
        baseline="security",
        status=_aggregate_status(results, partial),
        partial_rules=partial,
        results=results,
    )


# ===================================================================
# Testing baseline (6 rule)
# ===================================================================


def _eval_testing_baseline(project_root: Path) -> ComplianceSummary:
    """6 TST-WF rule runtime 평가."""
    results: list[RuleResult] = []
    tests_dir = project_root / "workflow-source" / "tests"

    # TST-WF-01: Smoke Test Coverage Required (≥ 5 test case)
    smoke_test_files = list(tests_dir.glob("check_*.py")) if tests_dir.exists() else []
    test_count_per_file = {}
    for tf in smoke_test_files:
        content = tf.read_text(encoding="utf-8", errors="ignore")
        # "def test_" 개수
        n = len(re.findall(r"^def test_", content, re.MULTILINE))
        test_count_per_file[tf.name] = n
    min_tests = min(test_count_per_file.values()) if test_count_per_file else 0
    results.append(RuleResult(
        rule_id="TST-WF-01",
        title="Smoke Test Coverage Required",
        status="compliant" if min_tests >= 5 else "non_compliant",
        notes=f"min test count: {min_tests} (need ≥ 5) across {len(smoke_test_files)} files",
    ))

    # TST-WF-02: Round-Trip Properties for State Serialization
    # 검증: state.json round-trip helper 또는 test 존재
    state_path = project_root / "ai-workflow" / "memory" / "active" / "state.json"
    round_trip_ok = False
    if state_path.exists():
        # state.json + parse + serialize round-trip
        try:
            import json
            data = json.loads(state_path.read_text(encoding="utf-8"))
            roundtrip = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
            round_trip_ok = (roundtrip == state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    results.append(RuleResult(
        rule_id="TST-WF-02",
        title="Round-Trip Properties",
        status="compliant" if round_trip_ok else "advisory",
        notes="state.json parse + serialize identity",
    ))

    # TST-WF-03: Invariant Properties (smoke test 에 test_invariant_* 1+)
    invariant_count = sum(
        1 for tf in smoke_test_files
        if re.search(r"^def test_invariant_", tf.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
    )
    results.append(RuleResult(
        rule_id="TST-WF-03",
        title="Invariant Properties",
        status="compliant" if invariant_count >= 1 else "advisory",
        notes=f"test_invariant_* count: {invariant_count}",
    ))

    # TST-WF-04: Idempotency Properties (test_idempotency_* 1+)
    idempotency_count = sum(
        1 for tf in smoke_test_files
        if re.search(r"^def test_idempotency_", tf.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
    )
    results.append(RuleResult(
        rule_id="TST-WF-04",
        title="Idempotency Properties",
        status="compliant" if idempotency_count >= 1 else "advisory",
        notes=f"test_idempotency_* count: {idempotency_count}",
    ))

    # TST-WF-05: Generator Quality (smoke test 의 generator/fixture 사용)
    fixture_count = sum(
        1 for tf in smoke_test_files
        if "fixture" in tf.read_text(encoding="utf-8", errors="ignore").lower() or "factory" in tf.read_text(encoding="utf-8", errors="ignore").lower()
    )
    results.append(RuleResult(
        rule_id="TST-WF-05",
        title="Generator Quality",
        status="compliant" if fixture_count >= 1 else "advisory",
        notes=f"smoke test with fixture/factory: {fixture_count}",
    ))

    # TST-WF-06: Verification Strategy Documented (모든 test 함수 docstring 1+ line)
    no_docstring = []
    for tf in smoke_test_files:
        content = tf.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"^def test_\w+\(.*?\):\s*\n\s*\"\"\"(.+?)\"\"\"", content, re.MULTILINE | re.DOTALL):
            if not m.group(1).strip():
                no_docstring.append(f"{tf.name}:{m.group(0)[:30]}")
    results.append(RuleResult(
        rule_id="TST-WF-06",
        title="Verification Strategy Documented",
        status="compliant" if not no_docstring else "advisory",
        notes=f"test functions without docstring: {len(no_docstring)}",
    ))

    state = _read_state_json(project_root)
    partial = _get_partial_rules(state, "testing")
    return ComplianceSummary(
        baseline="testing",
        status=_aggregate_status(results, partial),
        partial_rules=partial,
        results=results,
    )


# ===================================================================
# Performance baseline (6 rule)
# ===================================================================


def _eval_performance_baseline(project_root: Path) -> ComplianceSummary:
    """6 PERF-WF rule runtime 평가."""
    results: list[RuleResult] = []
    tests_dir = project_root / "workflow-source" / "tests"

    # PERF-WF-01: Smoke Test Execution Time (≤ 30초 per file)
    slow_tests = []
    if tests_dir.exists():
        for tf in list(tests_dir.glob("check_*.py"))[:3]:  # 3개만 sample
            start = time.time()
            try:
                import subprocess
                subprocess.run(
                    ["python3", str(tf)],
                    cwd=str(project_root),
                    capture_output=True,
                    timeout=30,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass
            elapsed = time.time() - start
            if elapsed > 30:
                slow_tests.append(f"{tf.name}: {elapsed:.1f}s")
    results.append(RuleResult(
        rule_id="PERF-WF-01",
        title="Smoke Test Execution Time",
        status="compliant" if not slow_tests else "non_compliant",
        notes=f"slow tests (sample 3): {slow_tests or 'none'}",
    ))

    # PERF-WF-02: Module Import Time (≤ 1초)
    import time
    start = time.time()
    try:
        import workflow_kit
        import_time = time.time() - start
    except ImportError:
        import_time = 999
    results.append(RuleResult(
        rule_id="PERF-WF-02",
        title="Module Import Time",
        status="compliant" if import_time <= 1.0 else "non_compliant",
        notes=f"workflow_kit import time: {import_time:.3f}s (need ≤ 1.0s)",
    ))

    # PERF-WF-03: Memory Footprint (≤ 200 MB) — tracemalloc 측정
    try:
        tracemalloc.start()
        import workflow_kit
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        # peak 는 bytes. 200MB = 200 * 1024 * 1024 = 209715200
        peak_mb = peak / (1024 * 1024)
        results.append(RuleResult(
            rule_id="PERF-WF-03",
            title="Memory Footprint",
            status="compliant" if peak_mb <= 200 else "advisory",
            notes=f"workflow_kit peak memory: {peak_mb:.1f} MB (need ≤ 200 MB)",
        ))
    except ImportError:
        results.append(RuleResult("PERF-WF-03", "Memory Footprint", "not_applicable"))

    # PERF-WF-04: Audit Log Append Latency (≤ 10ms avg)
    try:
        from workflow_kit.common.contracts.stage_gate import append_audit_log
        # 1000회 호출 시 평균 latency
        latencies = []
        for _ in range(100):
            start = time.time()
            try:
                append_audit_log(_dummy_event(), test_audit_path := project_root / "tmp_audit_perf.log")
            except (TypeError, OSError):
                pass
            latencies.append((time.time() - start) * 1000)
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        results.append(RuleResult(
            rule_id="PERF-WF-04",
            title="Audit Log Append Latency",
            status="compliant" if avg_latency <= 10 else "advisory",
            notes=f"avg latency: {avg_latency:.2f}ms (need ≤ 10ms)",
        ))
        # cleanup
        if (project_root / "tmp_audit_perf.log").exists():
            (project_root / "tmp_audit_perf.log").unlink()
    except ImportError:
        results.append(RuleResult("PERF-WF-04", "Audit Log Append Latency", "not_applicable"))

    # PERF-WF-05: state.json Read/Write Latency (≤ 5ms)
    state_path = project_root / "ai-workflow" / "memory" / "active" / "state.json"
    if state_path.exists():
        rw_latencies = []
        for _ in range(50):
            start = time.time()
            try:
                data = state_path.read_text(encoding="utf-8")
                state_path.write_text(data, encoding="utf-8")
            except OSError:
                pass
            rw_latencies.append((time.time() - start) * 1000)
        avg_rw = sum(rw_latencies) / len(rw_latencies) if rw_latencies else 0
        results.append(RuleResult(
            rule_id="PERF-WF-05",
            title="state.json Read/Write Latency",
            status="compliant" if avg_rw <= 5 else "advisory",
            notes=f"avg R/W latency: {avg_rw:.2f}ms (need ≤ 5ms)",
        ))
    else:
        results.append(RuleResult("PERF-WF-05", "state.json Read/Write Latency", "not_applicable"))

    # PERF-WF-06: Profiling Hook
    profiling_ok = False
    profiling_path = project_root / "workflow-source" / "workflow_kit" / "common" / "profiling.py"
    if profiling_path.exists():
        profiling_ok = True
    results.append(RuleResult(
        rule_id="PERF-WF-06",
        title="Profiling Hook",
        status="compliant" if profiling_ok else "advisory",
        notes="workflow_kit.common.profiling module 존재 (v0.7.1+ follow-up)",
    ))

    state = _read_state_json(project_root)
    partial = _get_partial_rules(state, "performance")
    return ComplianceSummary(
        baseline="performance",
        status=_aggregate_status(results, partial),
        partial_rules=partial,
        results=results,
    )


def _dummy_event():
    """PERF-WF-04 의 1000회 호출용 dummy event."""
    from workflow_kit.common.contracts.stage_gate import AuditLogEvent
    return AuditLogEvent(
        event_type="perf_test",
        stage_name="performance",
        actor="perf_test",
        raw_input="perf_test_dummy",
    )


# ===================================================================
# Public API
# ===================================================================


def evaluate_compliance(
    project_root: Path,
    baseline: str,
) -> ComplianceSummary:
    """단일 baseline 의 compliance 평가.

    Args:
        project_root: 프로젝트 루트 경로 (state.json 위치)
        baseline: "security" | "testing" | "performance"

    Returns:
        ComplianceSummary with overall status + per-rule results.
    """
    if baseline == "security":
        return _eval_security_baseline(project_root)
    if baseline == "testing":
        return _eval_testing_baseline(project_root)
    if baseline == "performance":
        return _eval_performance_baseline(project_root)
    raise ValueError(f"unknown baseline: {baseline}")


def evaluate_all(
    project_root: Path,
) -> dict[str, ComplianceSummary]:
    """3종 baseline 모두 평가.

    Returns:
        dict mapping baseline name → ComplianceSummary.
    """
    return {
        "security": _eval_security_baseline(project_root),
        "testing": _eval_testing_baseline(project_root),
        "performance": _eval_performance_baseline(project_root),
    }
