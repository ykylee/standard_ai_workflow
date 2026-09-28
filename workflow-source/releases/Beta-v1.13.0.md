# Beta v1.13.0 (2026-09-28)

> **상태: 릴리스 준비.** package `1.13.0`, runtime `__version__ = 1.13.0`, tag `v1.13.0`.
> **minor release** — **v1.12.0 에서 예고한 은퇴 API 제거 + 검사가 사용 지표를 오염시키던 경로 하나 수리.**
>
> 등급 근거 (§1.5): `wk release-status` 는 `!` 커밋 1건(`2f3affc5`)으로 **2.0.0** 을 제안한다.
> 이 제거는 v1.12.0 발행 때 소유자가 정한 계획("한 발행 동안 DeprecationWarning shim → v1.13.0
> 제거")의 **이행**이다. stable_guarantee §0 이 v1.x 의 breaking 을 "1 release 경고 → 다음 release
> 제거" 로 허용하므로 minor 다. 판정과 반대 근거는 §0.1.

## 0. 릴리스 판정

v1.12.0 은 GitHub Actions 폐지(main-022)가 유예 없이 지운 공개 API 2종을 shim 으로 되살려
**한 발행 동안 경고**했다. 이 발행이 그 cycle 의 두 번째 단계다 — 정책이 약속한 대로 지운다.

### 0.1 `!` 1건에 §1.5 적용 → minor

| 커밋 | 무엇이 깨지나 | 판정 |
|---|---|---|
| `2f3affc5` refactor! | `release_pipeline.verify_required_ci` · `REQUIRED_CI_WORKFLOWS` 제거 — 동결 표면(`tools/`) | v1.12.0 에서 `DeprecationWarning`(removal `v1.13.0` 명시)을 한 발행 동안 냈다. **deprecation cycle 완료에 따른 제거** |

**반대 근거 (감추지 않는다)**: v1.12.0 을 건너뛰고 v1.11.x 에서 곧장 올라오는 소비자는 경고를
한 번도 못 보고 두 이름을 잃는다. 대체는 `release_pipeline.verify_gate_evidence` 이고,
`REQUIRED_CI_WORKFLOWS` 는 대체가 없다(필수 CI 워크플로가 더는 없다). 정본:
`core/v0_9_0_deprecation_policy_spec.md` §3.7.

## 1. 릴리스 요약

- 범위: `v1.12.0..` 발행 준비 직전까지 **4 commit**. 이 중 1건(`18790f49`)은 **v1.12.0 발행
  마무리**가 태그 뒤에 착지한 것이고 1건은 memory 기록이라 실질은 **2 commit** 이다.
- 누적 smoke **296/296 PASS** (로컬 `--branch-context=all` = 296 × native/slash).
- 검사 **296 → 296** (신설·은퇴 없음).

## 2. 소비자에게 보이는 변화

### 2.1 은퇴 API 제거

`from workflow_kit.tools.release_pipeline import verify_required_ci` 와 `REQUIRED_CI_WORKFLOWS`
는 이제 `ImportError` / `AttributeError` 다. 발행 게이트 판정은 `verify_gate_evidence()` 를 쓴다.

### 2.2 `check_self_application` 이 사용 지표를 오염시키지 않는다

이 검사는 CLAUDE.md 가 커밋 전마다 **러너 밖에서 단독으로** 돌리는 검사인데, 자기
session-start 를 실제 저장소에서 부르면서 memory_index telemetry 에 **실행마다 1건**을 붙였다
(`23162c90`). 러너는 자식에게 제외 표식을 넘기지만 단독 실행에는 표식이 없었다. 이제 검사가
표식을 스스로 걸고, case 8 이 실제 `events.jsonl` 증가 0 을 단언한다.

이 조사(TASK-2026-09-23-main-018)의 판정: memory_index 조회가 session-start 에 몰린 것은
**배선 누락이 아니라** 측정 오염 + 호출 빈도다. doc-sync 는 호출마다 조회하고 실측 4건을 집는다.

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- 제거: `check_release_gate_evidence` case 10 이 '제거됨' 을 잰다. v1.12.0 판 shim 을 되주입하면
  세 판정(두 이름 · `__getattr__`) 모두 red
- telemetry: 표식을 빼는 되주입 → `check_self_application` case 8 red (`+1줄`)

## 4. 알려진 한계 (감추지 않는다)

- 과거 telemetry(`events.jsonl`, gitignore 로컬 데이터)에는 수리 전 오염분이 섞인 채 남아 있다.
  지우지 않았다 — 대시보드의 누적 지표는 그만큼 부풀어 있다.
- memory_index 30 entry 중 한 번이라도 선택된 것은 15 — 질의가 `state.json` 축에서 유도돼 세션
  내내 같다. 결함 판정 밖의 관찰로 남긴다.
- **Windows 는 현재 미측정이다** (`TASK-2026-08-25-main-017` blocked).

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-09-28T09:30:04Z)_

- total wiki pages: **96**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
