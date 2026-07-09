# Beta Phase 13 v1.0 — Operational Intelligence close-out (2026-07-09)

> **Phase 13 (Operational Intelligence v1.0) 의 정식 close-out release**.
> 본 release 는 별도 version bump 없이 4 sub-milestone (v0.13.0 / v0.13.1 /
> v0.13.2 / v0.13.3) 으로 분할 출시된 Phase 13 의 *총괄 정합 release entry point*.
> 4 AC 모두 ✅ close. silent_failing_cycles_count north-star 도달.

## 1. Phase 13 정의 (회고)

**north-star metric**: `silent_failing_cycles_count` — drift prevention guard 가
검출했으나 manual fix 까지 걸린 release cycle 의 누적 갯수. 0 으로 수렴 목표.

**Phase 13 이름**: "Operational Intelligence v1.0 — Self-aware, Self-documenting, Self-recovering"

핵심: *workflow 운영이 외부 intervention 없이 자가 인식 / 자가 문서화 / 자가 복구* 되는 단계.

## 2. Acceptance Criteria 종합 (4 AC 모두 ✅)

| AC | Status | 정의 | Release | north-star |
|---|---|---|---|---|
| **AC1 (drift zero)** | ✅ | drift prevention smoke 6 case PASS + N release 동안 silent fail 0 | v0.11.23 | ✅ |
| **AC1.5 (north-star)** | ✅ | `silent_failing_cycles_count = 0` | v0.13.0 | ✅ |
| **AC1.6 (inline guard)** | ✅ | `guard_status='pass'`, 40ms 내 inline 실행 | v0.13.0 | ✅ |
| **AC2 (memory_index 활용)** | ✅ | 3 skill opt-in retrieval 호출 측정 가능 + baseline 1 release = 1+ 호출 | **v0.13.1** | ✅ |
| **AC3 (self-recovering)** | ✅ | drift 검출 시 자동 fix (manual 0) + 1 release cycle 내 fix cycle closed + self-recovery log 자동 emit | **v0.13.2** | ✅ |
| **AC4+ (self-documenting)** | ✅ | wiki ↔ memory 양방향 link 자동 갱신 + 외부 consumer 신뢰 가능 | **v0.13.3** | ✅ |

## 3. 4 sub-milestone 일괄 summary

### v0.13.0 — Quality Dashboard (Phase 13 sub-milestone 1)

- 5 panel 운영 metric (drift prevention / maturity distribution /
  memory_index utilization / smoke trend / recent release).
- CLI `--format json|markdown|html`.
- Inline drift guard (40ms 내) + release post-emit hook.
- 정적 HTML dashboard renderer (Chart.js).
- → [`Beta-v0.13.0.md`](./Beta-v0.13.0.md)

### v0.13.1 — memory_index telemetry sidecar (AC2 close)

- `ai-workflow/memory/active/memory_index/telemetry/events.jsonl` —
  3 skill + dispatcher 의 opt-in retrieval 호출 자동 emit.
- `MemoryIndexTelemetryEvent` + `MemoryIndexTelemetrySummary` schema.
- `cmd_memory_index_telemetry` subcommand 36 (read-only inspect).
- Dashboard Panel 3 의 `retrieval_hit_rate` placeholder → 실측값 전환.
- → [`Beta-v0.13.1.md`](./Beta-v0.13.1.md)

### v0.13.2 — self-recovering drift prevention (AC3 close)

- `cmd_self_recover` subcommand 37 (detect → classify → fix → re-check 1-cycle).
- 5 case auto-fixable + 2 case manual_required 분리.
- `cmd_release` validate step 후 자동 호출 (--skip-self-recover escape hatch).
- release note 본문 `## Self-recovery log` 자동 append (idempotent).
- in-scope fix 3건 (sys.path / README_PATH / import explicit export).
- → [`Beta-v0.13.2.md`](./Beta-v0.13.2.md)

### v0.13.3 — wiki ↔ memory bidirectional link sync + audit (AC4+ close)

- `bidir_link.py` 신규 (260 line, R-A sync + R-C audit 통합).
- `cmd_bidir_link` subcommand 38.
- `cmd_release` step 2.8 — sync-maturity-matrix 후 audit 자동 호출.
- release note 본문 `## Bidirectional link audit` 자동 append.
- audit 실측: `is_symmetric=true`, `asymmetric_count=0`.
- → [`Beta-v0.13.3.md`](./Beta-v0.13.3.md)

## 4. 누적 정량 metric

| 항목 | 수치 | 비고 |
|---|---|---|
| 누적 release cycle (v0.5.1~v0.13.3) | **93+** | 본 release 포함 |
| 누적 smoke test PASS | **225+** | v0.11.22 baseline 200+ → +25 |
| 신규 file | **15+** | bidir_link.py + telemetry helper + dashboard_data + 4 smoke test + ... |
| 신규 dispatcher subcommand | **3** (v0.13.0~v0.13.3) | dashboard / memory-index-telemetry / self-recover / bidir-link |
| 신규 smoke | **4** | check_quality_dashboard_v0_13_0 (10) / check_memory_index_telemetry (6) / check_self_recovering_v0_13_2 (8) / check_bidir_link_v0_13_3 (6) |
| 누적 dispatcher subcommand | **38+** | dashboard / telemetry / self-recover / bidir-link |
| mypy strict file clean | **36+** | 신규 file 0 (in-place 확장) |
| in-scope fix | **3** (v0.13.2) + **0** (v0.13.3) | sys.path / README_PATH / import export |
| Phase 13 release note 본문 자동 append | **3** | self-recovery log / bidir link audit / dashboard markdown |

## 5. north-star 정량 검증

- `silent_failing_cycles_count = 0` (AC1.5)
- 4 release 동안 drift prevention smoke fail 0 회 (AC1)
- inline guard 6/6 PASS (AC1.6)
- telemetry emit 정상 (AC2)
- self-recover 5 case 자동 fix 성공 (AC3)
- bidir link audit is_symmetric=true (AC4+)

## 6. 후속 cycle 후보 (Phase 13 v1.0 close-out 시점)

| 후보 | 우선순위 | 비고 |
|---|---|---|
| **R-B** Wiki → Memory reverse lookup | v0.13.4+ | 별도 sub-milestone (v0.13.3 design doc §2.2) |
| **ADR-006 retrospective** (full review) | 2026-07-16 scheduled | Phase 13 v1.0 close 후 30일 retro |
| **MCP beta 1st batch stable 승격** (v0.11.26) | 별도 priority track | git_history_summarizer / smart_context_reader / workflow_log_rotator / apply_robust_patch |
| **drift-prevention-91-cycle-classification §5 hook 후보 5 종** | 별도 cycle | 본 release 흡수하지 않음 |
| **MCP beta 2nd batch stable 승격** (v0.11.28) | 별도 priority track | 잔여 Beta MCP |

## 7. external surface (본 Phase 13 v1.0)

- **GitHub Releases**: 4 tag (`v0.13.0-beta` / `v0.13.1-beta` / `v0.13.2-beta` /
  `v0.13.3-beta`) 모두 publish.
- **Dashboard HTML**: `docs/dashboard/index.html` (GitHub Pages 자동 sync).
- **Telemetry sidecar**: `ai-workflow/memory/active/memory_index/telemetry/events.jsonl`
  (runtime-generated, .gitignore 등록).
- **Wiki 토픽 갱신**: `phase-13-definition-north-star.md` 의 모든 AC status
  🟡 → ✅ 정합.
- **Auto memory 갱신**: 4 memory pointer 추가
  (phase-13-v0-13-0 / v0-13-1-ac2-telemetry / v0-13-2-ac3-self-recover /
  v0-13-3-ac4-bidir-link).

## 8. 외부 consumer 영향

- **release-dist wheel**: 영향 없음 (in-place 확장, 0 breaking change)
- **API surface (workflow_kit.__all__)**: 영향 없음 (신규 subcommand 만 추가)
- **Schema SSOT (schemas/generated_output_schemas.json)**: 영향 없음
  (telemetry schema 는 output contract 외부 — sidecar JSONL 만)
- **External wiki consumer**: 양방향 link 안정성 ↑ (audit 0 asymmetric)
- **CI**: drift prevention 6/6 + bidir link smoke 6/6 모두 PASS

## 9. release URL

- 본 close-out 은 별도 tag 없음 (4 sub-milestone tag 의 정합 summary).
- tag: `v0.13.3-beta` (마지막 sub-milestone, Phase 13 v1.0 의 SSOT).
- breaking change: ❌ (4 release 모두 patch)
- PyPI 배포: no (GitHub Releases only)