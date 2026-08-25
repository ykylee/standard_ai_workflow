# Beta v1.4.0 (2026-08-24)

> **상태: 릴리스 준비.** package `1.4.0`, runtime `__version__ = 1.4.0`, tag `v1.4.0`.
> **minor release** — 52~56차 세션 묶음. 축 둘을 닫았다: **소유권 4번째 분류
> '포크됨'** 과 **혼합 표기**(생성기와 코퍼스 양쪽).
>
> `!` 커밋이 셋 있지만 **major 가 아니다.** `docs/RELEASE.md` §1.5 의 4문항이
> 전부 "아니오" 로 답한다 — 공개 시그니처 변경 **0**(사라진 정의 2개는 비공개
> 개명과 동일 시그니처 재작성), 진입점 제거 **0**(오히려 `migrate-task-labels`
> 추가), `TASK_FIELD_ALIASES` **17/17 필드가 한국어를 계속 받아** 소비자가
> 잃는 것이 없다. `Action` 열거형도 `+FORKED` 하나만 늘어난 additive 다.
> 도구(`release-status`)는 `!` 표기만 세어 `2.0.0` 을 냈고 `requires_decision`
> 으로 사람에게 넘겼다 — §1.5 는 정확히 그 자리를 위해 쓰인 절이다.

## 0. 릴리스 판정

이 사이클의 공통 주제는 **"신호가 읽는 쪽 가정만큼을 뜻하지 않는다"** 다.
같은 모양이 자리를 바꿔 가며 반복해서 나왔고, 그 반복 자체가 이번 릴리스의
내용이다.

- **`in_sync ≠ 쓸 수 있음` · `인벤토리 ≠ 세션 가용성` · `이벤트 1건 ≠ 완결본`.**
  파일이 같다는 것, 목록에 있다는 것, 이벤트가 쌓였다는 것 — 셋 다 읽는 쪽이
  기대한 것보다 적게 말한다. 세 번 모두 도구는 옳았고 **가정이 틀렸다**.
- **그물이 N개 자리만 보면 N+1번째에서 갈린다.** 같은 어긋남(session-end 명령)이
  플러그인 · 생성기 · 산출물 · 레지스트리 · 진입 문서 산문 다섯 자리에서 났고,
  마지막 자리는 **손으로 쓴 목록**이라 검사가 볼 수 없었다. 파일 형식 경계
  (`.py` ↔ `.yml`)에서도 같은 일이 났다.
- **검사가 리터럴로 든 기대값은 계약이 아니라 그 시점 상수다.** 이 사이클에서
  다섯 자리를 정본 파생으로 바꿨다 — `okf_version` · 실행 기본값 절 제목 ·
  daily 문서 목적 문구 · 총계 세 파일 · CODE_INDEX 개수.
- **갱신이 상태를 나쁘게 만드는 조언은 틀린 조언이다.** `wk doctor` 가
  포크된 진입점을 "재적용 대상" 이라 말했는데, 따르면 측정으로 얻은 90여 줄이
  placeholder 가 된다.
- **사본을 고치지 말고 없앤다.** bootstrap 이 템플릿 사본으로 쓰고 도구가
  정본 작성기로 쓰니 갈라졌다. 템플릿을 고쳐도 다음에 또 갈라진다.

## 1. 릴리스 요약

- 범위: `v1.3.0..HEAD` (16 commit — fix 7 · feat 4 · chore 4 · refactor 1 · docs 1)
- 검사 **264 → 267**, 전량 2축 267/267 PASS, mypy strict 0 errors
- 소유권 4번째 분류 신설 · 혼합 표기 축 완결 · CI red 2건 해소 · flake 1건 규명

## 2. deliverable

### 2.1 소유권 4번째 분류 '포크됨' (TASK-2026-08-20-main-012)

정본 §3 은 진입점(`CLAUDE.md` 등)을 *kit 소유(덮는다)* 로 분류하는데, 바로
아래 §4-2 는 *additive* 라 말한다 — **같은 파일에 두 규칙**이 붙어 있었다.
실제 프로젝트는 그 진입점에 자기 운영 규칙을 넣으므로, 재적용 한 번이면
사라진다.

해법은 추측이 아니라 **선언**이다. "내용이 많으니 포크겠지" 는 휴리스틱이고
휴리스틱은 조용히 틀린다. 파일이 스스로 말한다:

```markdown
<!-- standard-ai-workflow-kit: v1.0.0-beta -->
<!-- standard-ai-workflow-kit-fork: 이 저장소가 소유한다 — … -->
```

버전 marker 는 **건드리지 않는다** — 그것이 *어느 시점에서 갈라졌는지* 를
남기고, 그 버전의 생성물과 diff 하는 것이 놓친 kit 변경을 되찾는 유일한
길이다. **`--force` 는 이긴다**: 불가침(사용자 상태)과 갈리는 자리가 정확히
여기다. 포크는 *"덮지 마라"* 가 아니라 *"모르고 덮지 마라"* 다.

### 2.2 혼합 표기 — 증상이 아니라 원인을 닫았다 (main-002·003·004)

질문이 "레거시 190파일을 옮길까" 로 서 있었는데, 실측이 다른 곳을 가리켰다 —
**생성기가 아직 옛 형식을 냈다.** 오늘 bootstrap 한 새 프로젝트가 **첫날부터
두 표기를 같이** 받고 있었고(bootstrap 은 한국어 템플릿, 도구는 `task_label`
영어), 그 템플릿은 표기만 낡은 게 아니라 **v0.14.0 이전 레이아웃**이라 임베드
task 와 append-only 인덱스가 한 파일에 겹쳐 쌓였다.

- **생성기**(main-003): `render_daily_backlog` 이 템플릿 읽기를 그만두고 도구와
  같은 정본 작성기로 조립한다. 겸사겸사 **씨앗 task 파일이 아예 없어** 인덱스가
  빈 곳을 가리키던 것과, 기본 ID `TASK-001` 이 **kit 자신의 `TASK_ID_PATTERN`
  과 안 맞던** 것을 고쳤다.
- **코퍼스**(main-004): `wk migrate-task-labels` 신설 — 193파일 · 2418줄,
  한국어만 188 → 0 · 혼재 2 → 0. **파싱 동일성이 잠금장치다**: 쓰기 전후로
  집계를 대조하고 다르면 전부 되돌린다. 라벨은 사람이 읽는 면이고 상태의 근거는
  frontmatter 이므로, 이 마이그레이션은 정의상 집계를 바꾸면 안 된다.
  소비자 저장소도 같은 레거시 코퍼스를 가지므로 **배포되는 도구**로 만들었다.

### 2.3 baseline 에서 사라지던 것들 (main-013·014·015, 2026-08-22-main-001)

- **`planned` 은 어휘 안인데 어느 목록에도 안 담겼다.** 어휘 *밖* 값을 끝까지
  지키던 원칙이 정작 어휘 *안*의 한 값에는 적용되지 않았다. 실측 비용:
  `main-018` 이 **6일간** baseline 에서 안 보였고 그 사이 그 일은 다른 task 들이
  이미 끝냈다. 그물은 **어휘 전수**로 짰다.
- **handoff §5 가 SSOT 를 복제하고 있었다.** 판정 기준이 다른 네 부류가 한
  목록에 섞였고, 넷 중 둘은 이미 기계가 읽는 자리를 가진 채 산문이 그것을
  복제했다 — 하루에 잔재 2건이 확인됐다. 부류별로 갈라 각자의 SSOT 를
  가리키게 하고 `check_handoff_next_steps` 가 대조한다.

### 2.4 CI red 2건 — 돌지 않은 워크플로는 통과한 워크플로가 아니다 (main-016·017)

- `okf-validate` 가 6회 연속 red 였다. 원인은 export 가 아니라 **검사**다 —
  `okf_version: "0.1"` 리터럴이 남아 있었다. 같은 이행이 `.py` 리터럴은 정본
  참조로 바꿨는데 **`.yml` 은 그물 밖**이었다.
- 그 규칙을 처음 적용하자마자 **두 번째 red** 가 나왔다 —
  `consumer-metrics-digest` 가 옮겨진 파일을 부르고 있었고, 주간 cron 이라
  3일간 신호가 없었다. **자주 안 도는 워크플로일수록 정적으로 잡아야 한다.**

### 2.5 flake 규명 (2026-08-24-main-001)

`watch_transient_writer` 가 부하에서만 깨졌다. 도구는 내내 옳았고, 테스트가
`Path.write_text`(truncate 후 write, **비원자적**)로 쓰는 사이의 빈/부분 파일을
감시자가 정직하게 관측한 것이었다. 원자적 쓰기로 바꾸고, **"실재했던 중간
상태는 보고된다"** 를 계약으로 못박았다 — 없으면 다음 사람이 그 관측을 잡음으로
보고 도구를 뭉갠다. 그 계약 case 의 첫 판이 스스로 flaky 해서 다시 만들었다.

## 3. smoke 회귀

누적 smoke test **274/274 PASS** ×2축 (2026-08-25, `dev,release,mcp-sdk` extra 를
깐 격리 venv, `--tmp-dir` 실디스크). 이 줄은 릴리스 시점 스냅샷이 아니라 *최신
전량 결과* 를 반영하는 살아있는 지표다.

## 4. 1차 출처 (cross-ref)

- [배포 일관성·멱등성 컨셉](../core/workflow_deployment_idempotency.md) §3 (소유권 4분류) · §3.1
- [설치·사용 가이드](../../docs/INSTALLATION_AND_USAGE.md) §7.0.1 · §7.0.2
- [릴리스 등급 판단 기준](../../docs/RELEASE.md) §1.5
- [메모리 거버넌스](../MEMORY_GOVERNANCE.md) §2 (append-only layout)

## 5. 후속

- **mypy flake** ([TASK-2026-08-13-main-004]) — 원인 계열은 mypy INTERNAL ERROR
  로 확정됐고 증거 확보 배선도 끝났다. 다음 재발이 트레이스백을 남기면 상류
  보고/우회 판단이 선다.
- **`archived/` 라벨** — 의도적으로 범위 밖. 어떤 집계도 읽지 않으므로 churn 이다.
  필요해지면 `wk migrate-task-labels --active-dir` 로 돌린다.
- **cross-host federation** — 두 번째 호스트(MacBook) 확보 시점.
- **memory_index 3-tuple** — 지표 추이 관찰.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-08-24T03:49:57Z)_

- total wiki pages: **94**
- total memory entries: **13**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
