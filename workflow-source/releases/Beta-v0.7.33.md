# Beta v0.7.33 — TASK-V0733-001 + TASK-V0734-001 (Atomic Rotation + Yearly Aggregation)

> **Status**: in-flight
> 본 release 의 변경. v0.7.32 의 log rotation + metrics aggregation 의 *2 follow-up* — atomic crash safety + yearly period.

## 본 release 의 1차 출처

1. **v0.7.32 release note** (TASK-V0731-001 + V0732-001 log rotation + metrics aggregation) — 본 release 의 *2 follow-up* 의 1차 출처
2. **v0.7.18 release note** (destructive subcommand 정공법, --dry-run 필수) — 본 release 의 *atomic rotation 의 *3-checklist*** 의 1차 출처 (atomic rename + cleanup + main preservation)
3. **v0.7.25 release note** (F-6 closure, SHA256 idempotency) — 본 release 의 *idempotency 의 *crash safety* 의 1차 출처

## 발견 (v0.7.32 의 2 follow-up)

### TASK-V0733-001: atomic rotation 부재
v0.7.32 의 `rotate_log_if_needed` 의 *crash safety* 부족:
- *gzip write* 와 *truncate* 의 *사이에 crash* 시 → *gzip archive* (손실 X, write 미완) + *main log* (full) — main log 의 *재처리* 시 *dedup* 필요
- *truncate* 후 *crash* 시 → *gzip archive* (full) + *main log* (empty) — 정상

**v0.7.33 의 정공법**: *3-step atomic rotation*:
1. **temp file** (`*.gz.tmp`) 에 gzip write (사전 *data* 검증)
2. **`os.replace(temp, archive)`** (POSIX/NTFS atomic rename)
3. **`f.truncate(0)`** (main log truncate, `r+b` mode)

*crash safety*:
- step 1 mid-crash → *temp file* 만 partial. *main log* (full) + *archive* (없음) — main full 보존
- step 2 mid-crash → `os.replace` atomic — *archive* (full) + *main log* (full) — *둘 다* 보존
- step 3 mid-crash → *archive* (full) + *main log* (full) — *둘 다* 보존 (main log 의 *중복* 가능)
- 정상 결과: *archive* (full) + *main log* (empty)

### TASK-V0734-001: yearly period 부재
v0.7.32 의 `aggregate_metrics` 의 *period* 가 `daily|weekly|monthly|all` 4종. *yearly* 미지원. *장기 추세* (multi-year) 분석 어려움.

**v0.7.33 의 정공법**: `bucket_key` 의 *yearly* 분기 추가 (`ts.strftime("%Y")`). `--aggregate=yearly` validation 에 추가. cross-year boundary (2025-12 + 2026-01) → 2 buckets.

## 본 release 의 변경

### 1. `archive_stale_memory.py` 의 atomic rotation + yearly aggregation

**TASK-V0733-001: rotate_log_if_needed 의 3-step atomic implementation**:
```python
def rotate_log_if_needed(memory_dir, *, line_threshold=10000):
    log_path = memory_dir / METRICS_LOG_NAME
    if not log_path.exists():
        return {"rotated": False, ...}
    with log_path.open("r", encoding="utf-8") as f:
        line_count = sum(1 for _ in f)
    if line_count <= line_threshold:
        return {"rotated": False, ...}
    # 3-step atomic rotation (TASK-V0733-001)
    timestamp = dt.datetime.now(tz=dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    archive_path = memory_dir / f"{METRICS_LOG_NAME}.{timestamp}.gz"
    temp_path = archive_path.with_suffix(archive_path.suffix + ".tmp")
    try:
        # step 1: temp file 에 gzip write
        with log_path.open("rb") as f_in, gzip.open(temp_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        # step 2: os.replace (atomic rename)
        os.replace(temp_path, archive_path)
        # step 3: main log truncate
        with log_path.open("r+b") as f:
            f.truncate(0)
        archive_size = archive_path.stat().st_size
    except (OSError, IOError, gzip.BadGzipFile):
        # cleanup temp file (best-effort)
        try:
            if temp_path.exists():
                temp_path.unlink()
        except (OSError, IOError):
            pass
        return {"rotated": False, ..., "error": "rotation-failed"}
    return {"rotated": True, ...}
```

**TASK-V0734-001: aggregate_metrics 의 yearly 분기**:
```python
def bucket_key(ts_str: str) -> str:
    ...
    if period == "daily":
        return ts.strftime("%Y-%m-%d")
    elif period == "weekly":
        iso = ts.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    elif period == "monthly":
        return ts.strftime("%Y-%m")
    elif period == "yearly":  # v0.7.33 (TASK-V0734-001)
        return ts.strftime("%Y")
    return "unknown"
```

**cmd_aggregate_metrics 의 period validation**:
```python
if period not in ("daily", "weekly", "monthly", "yearly", "all"):
    return {"ok": False, "error": f"invalid --aggregate: {period} (expected: daily|weekly|monthly|yearly|all)"}
```

### 2. 10 smoke test (10/10 PASS, 5-run stable)

`tests/check_v0_7_33_atomic_yearly.py` (in-process import + mock):

**TASK-V0733-001 (5 smoke)**:
1. `test_atomic_rotation_no_temp_leftover` — rotation 성공 시 `.tmp` file 부재 (os.replace 정상)
2. `test_atomic_rotation_archive_exists` — `.gz` archive file 존재 + valid gzip (105 lines)
3. `test_atomic_rotation_main_log_empty` — main log = 0 byte (truncate)
4. `test_atomic_rotation_temp_cleanup_on_fail` — gzip write fail 시 `.tmp` cleanup + main log *preserved* (crash safety)
5. `test_atomic_rotation_no_temp_on_under_threshold` — under-threshold 시 `.tmp`/`.gz` file 생성 0

**TASK-V0734-001 (5 smoke)**:
6. `test_yearly_aggregation_2_years` — 5 entries (2025-01, 2025-06, 2025-12, 2026-03, 2026-09) → 2 buckets
7. `test_yearly_aggregation_1_year` — 3 entries (2026 only) → 1 bucket
8. `test_yearly_aggregation_cross_year_boundary` — 2025-12 + 2026-01 → 2 buckets (cross-year)
9. `test_yearly_aggregation_total_sum` — total.archived = sum(buckets.archived) (sum 정합)
10. `test_yearly_aggregation_invalid_period` — invalid `--aggregate=decade` → ok=False, error message

**10/10 PASS** (257+ → 267+ 누적 test, **5-run stable 50/50**).

### 3. cumulative 267+ test (회귀 0)

- v0.7.32 의 10 신규 test = 257+
- v0.7.33 의 10 신규 test (TASK-V0733-001 5 + TASK-V0734-001 5) = **267+**
- 기존 v0.7.28/v0.7.30/v0.7.31/v0.7.32 의 test 회귀 0
- v0.7.32 의 `test_aggregate_invalid_period` 의 `yearly` → `decade` fix (v0.7.33 의 *yearly* 가 valid 가 됨)

## 발견된 cross-cutting lesson (v0.7.33)

- **`os.replace` 의 *atomic guarantee***: POSIX (`rename(2)` atomic) + NTFS. *cross-device* 시 fail (`EXDEV`). **v0.7.32 의 *truncate-after-compress* 의 race condition 회피** 정공법.
- **`Path.with_suffix(`.gz` → `.gz.tmp`)` 의 정공법**: `archive_path.with_suffix(archive_path.suffix + ".tmp")` = `archive.gz.tmp`. **suffix 체이닝** 정공법.
- **`f.truncate(0)` 의 *r+b mode* 정공법**: `open("r+b")` 로 read + binary write. *write* 후 *truncate(0)* = file size = 0. **data preservation 의 *inverse*** 정공법.
- **3-step atomic 의 *3-축* crash safety**: step 1 (write temp) + step 2 (atomic rename) + step 3 (truncate). *어디서 crash* 하든 *main log* 또는 *archive* 중 *최소 1개* 보존. *post-recovery* 의 *dedup* 가능. **모든 state 가 *eventually consistent***.
- **ISO 8601 year 의 *calendar year***: `ts.strftime("%Y")` = calendar year (e.g. `2026`). **ISO 8601 week-year* 와 *다름* (week-year 는 week 의 50%+ 가 속한 연도)**. 본 release 는 *calendar year* 사용 (단순).
- **`--aggregate=decade` 같은 *truly invalid* 의 *명시적 error***: silent fallback ❌, error message + option list ✅. **v0.7.18 의 destructive subcommand 정공법** (명시적 error).
- **`bucket_key` 의 *4-축* 정합**: `daily` (`%Y-%m-%d`) / `weekly` (`YYYY-Www`) / `monthly` (`%Y-%m`) / `yearly` (`%Y`) — *format 일관성* (`%Y` prefix) + *period 별 suffix* (`-%m-%d` / `-Www` / `-%m` / *none*). **4-period 정합 정공법**.
- **5-run stable 의 *crash-safety test* 의 의미**: `test_atomic_rotation_temp_cleanup_on_fail` 의 *gzip fail* 시뮬레이션 — *crash recovery* 가 *정상*. **crash safety test** = *5-run stable* + *failure simulation* 의 *2-축* 정합.

## Reference (다른 release note)

- v0.7.32 release note (TASK-V0731-001 + V0732-001 log rotation + metrics aggregation, 본 release 의 *2 follow-up* 의 1차 출처)
- v0.7.31 release note (TASK-V0729-001 + V0730-001 metrics log + idempotency, 본 release 의 *2 단계 상위* 의 1차 출처)
- v0.7.25 release note (F-6 closure, 본 release 의 *idempotency 의 crash safety* 의 1차 출처)
- v0.7.21 release note (--allow-existing-tag, 본 release 의 *--aggregate=decade* invalid period 의 *caller opt-in* 정신의 1차 출처)
- v0.7.18 release note (destructive subcommand 정공법, 본 release 의 *3-step atomic rotation* 의 *3-checklist* 의 1차 출처)
- v0.7.12 release note (4-priority REPO_ROOT, 본 release 의 REPO_ROOT auto-detect 의 1차 출처)

## 2 TASK (본 release)

### TASK-V0733-001: Atomic rotation (3-step crash safety)
- **상태**: in-flight
- **commit**: TBD
- **scope**: `rotate_log_if_needed` 의 3-step implementation (temp file + os.replace + truncate + cleanup-on-fail) (~50 line 추가)
- **정합성 검증**: 5/5 smoke test PASS, 5-run stable (50/50)

### TASK-V0734-001: Yearly aggregation (period=yearly)
- **상태**: in-flight
- **commit**: TBD
- **scope**: `aggregate_metrics` 의 *yearly* 분기 (`ts.strftime("%Y")`) + `cmd_aggregate_metrics` 의 *yearly* validation (~5 line)
- **정합성 검증**: 5/5 smoke test PASS, 5-run stable

## Follow-up (v0.7.34+)

- **F-1 (ci-publish, Phase 5)** — GH Actions 자동 release (`.github/workflows/release.yml`)
- **TASK-V0734-001 follow-up**: `--aggregate=yearly-iso` (ISO 8601 week-year 의 *별도* 지원)
- **TASK-V0735-001**: atomic rotation 의 *crash recovery* test — *temp file* detect + *main log* dedup 후 *완전한* state 복구

## Metric

- v0.7.33 = 1 feat commit (TBD) + 1 chore (TBD) = 2 commit (TASK-V0727-001 의 2-phase + amend 의 *1 commit* 정공법)
- archive_stale_memory.py 변경 (~55 line: atomic rotation + yearly period)
- 1 신규 test file (10 smoke, 10/10 PASS, 5-run stable) + 1 v0.7.32 test fix (`yearly` → `decade`)
- 누적 test 267+ (v0.7.32 257+ + 10 신규)
- 28 release 누적 (v0.7.5~v0.7.33)
- 97 commit code-repo (v0.7.32 까지) + 2 commit = **99 commit** (estimated)
- wheel + sdist 빌드 + gh release + verify (read-only)
