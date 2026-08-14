# 37차 세션 — 브랜치 정리, 그리고 검사가 자기 세션 기록을 못 견딘 자리 (2026-08-14)

- 문서 목적: TASK-2026-08-14-main-001·002 기록. 36차가 handoff 에 남긴 미결을 닫고, 배포 채널을 확정한다.
- 상태: done
- 관련: [task-001](../backlog/tasks/TASK-2026-08-14-main-001.md), [task-002](../backlog/tasks/TASK-2026-08-14-main-002.md), [RELEASE.md §1](../../../../docs/RELEASE.md), [36차 세션 기록](../../archived/fix/archive-history-integrity/sessions/archive_history_integrity_2026-08-13.md)

## 요약

36차가 만든 브랜치 메모리 생애주기를 **처음으로 실물에 적용**했다. 도구는 설계대로
동작했다 — 참조 재작성(handoff 링크 2 + archived `state.json` 5경로)이 실제로 됐고,
미완료 차단도 걸렸다. 그런데 **닫는 과정 자체가 세 가지를 더 드러냈다.** 셋 다
"만든 사람이 자기 산출물을 아직 안 밟아봤다" 계열이다.

## 1. 종료 순서에 한 걸음이 빠져 있었다

브랜치 task 가 `in_progress` 인 채였다. 일은 PR #25 로 끝났는데 **파일이 안 따라왔다** —
`완료 기준`은 `(작성 필요 — 검증 방법을 구체적으로 적는다)` 그대로였고 `작업 결과`·
`검증 결과`도 빈칸, `진행 현황`은 "시작 전." 이었다. 아카이브는 정당하게 막혔다.

36차가 handoff 에 적어둔 종료 순서는 1번이 "미완료 task 를 먼저 **처리**한다
(이월했으면 `carried_over_to`)" 였다. **이월만 말하고 "내 일이 끝났으면 닫는다" 를
안 말하고 있었다.** 이월은 브랜치가 끝났는데 일이 안 끝난 경우고, 지금은 그 반대였다.
순서에 그 문장을 추가했다.

빈 완료 기준으로 닫지 않았다 — 세션 기록에서 실제 산출물과 검증치를 끌어와 채운 뒤
`done` 으로 만들었다. `wk backlog-update` 는 `--validation-result` 가 없으면 `done` 을
`in_progress` 로 낮춘다 (그 가드가 여기서 정확히 작동했다).

> **도구 함정**: `--done-criteria` / `--result-note` 는 반복 지정해도 **마지막 하나만**
> 남는다 (append 아님). 5건을 적었는데 1건만 들어갔고 diff 를 보고 알았다. 여러 줄이
> 필요하면 값 안에 개행 + `- 완료 기준: ` 접두사를 직접 넣는다.

> **도구 함정 2 — `done` 이 후속 편집에서 되돌아간다.** `--validation-result` 없이
> `--mode update` 를 한 번 더 부르면 (필드 하나만 고치려는 흔한 동작) 같은 가드가
> **파일에 이미 적힌 검증 결과를 안 보고** `done` → `in_progress` 로 낮춘다. 판정이
> *파일 상태*가 아니라 *이번 호출의 입력*으로만 이뤄지기 때문이다. 실제로 이 세션에서
> 밟았고 — 경고는 출력됐는데 내가 안 읽었다 — `check_self_application` 의
> `task_status_mismatch` 가 잡았다. **후속 편집에도 `--validation-result` 를 같이
> 넘기고, 반환된 `warnings` 를 읽는다.**

## 2. 유령 ID — 완료 기록이 어느 파일과도 연결돼 있지 않았다

handoff §4 와 36차 세션 기록이 `TASK-2026-08-13-fix-archive-history-integrity-001` 을
가리켰다. **존재한 적 없는 ID** 다 (실재는 `…-2026-08-14-…`). 그래서:

- 세션 기록의 `관련 문서` 링크는 **죽어 있었다** (태어날 때부터)
- handoff §4 의 완료 기록은 **어느 task 파일과도 연결되지 않았다** — ID 로 추적하면 끊긴다

호스트가 UTC 라 도구 기본 날짜는 `08-13`, 사람이 쓴 문장은 KST 기준 `08-14` 였다.
같은 하루를 두 이름으로 부르면 ID 가 갈린다. 둘 다 실재 ID 로 교정했다.

## 3. 아카이브 직후 신설 검사가 red — 위양성이었다

`check_archive_history_integrity` case 7(자기 적용: `archived/` 링크가 전부 resolve
되는가)이 방금 아카이브한 문서를 두 번 지목했다:

```
archived/…/sessions/archive_history_integrity_2026-08-13.md → path "제목"
archived/…/sessions/archive_history_integrity_2026-08-13.md → <path>
```

그 줄은 36차가 **자기 수리를 설명한 문장**이다:

> 5. **제목·꺾쇠 링크 미처리** — `](path "제목")` / `](<path>)` 는 CommonMark 정식 형태인데…

**검사가 자기 세션의 기록을 못 견뎠다.** 원인은 case 7 이 쓰던 링크 정규식이
**자체 사본**이었다는 것이다:

| | 패턴 | label 요구 |
|---|---|---|
| 정본 `workflow_kit.common.markdown.LINK_RE` | `\[[^\]]+\]\(([^)]+)\)` | ✅ |
| case 7 자체 사본 | `\]\(([^)]+)\)` | ❌ |

사본이 **약한 형제**였다. `](…)` 만 보므로 label 없는 예시 산문을 링크로 집어삼킨다.
정본은 애초에 안 잡는다 — 그것들은 링크가 아니기 때문이다.

**문서를 고치지 않았다.** 위양성을 문서 쪽에서 피하면 다음 사람은 같은 문장을 못 쓰고,
위양성을 내는 검사는 결국 무시당한다. 판정을 정본에 맞추고 사본을 걷었다
(`normalize_link_target` 도 같이 받아 `<…>`·앵커 처리가 정본과 같아졌다).

### case 14 — 양방향으로 못 박았다

case 7 은 **살아 있는 저장소를 관찰할 뿐**이다. "안 잡는" 쪽으로 무력화돼도 corpus 가
깨끗하면 조용히 green 이 된다. 그래서 fixture 로 두 방향을 같이 잰다:

1. 링크 문법을 *설명하는* 산문은 링크가 아니다 → 0건
2. 이어서 진짜 깨진 링크(`[없는 문서](./gone.md)`)를 넣으면 → **잡는다**

되주입 실측: 약한 정규식으로 되돌리면 case 14 가 1번에서 FAIL 하며 이유를 지목한다.
13 → 14 cases.

## 4. 실물에서 확인된 것 (36차 기능의 첫 자기 적용)

- `origin/fix/archive-history-integrity` 삭제 — 고유 커밋 0, tip `f798947` 은 main 이력에 잔존
- `wk archive-branch-memory --apply` → handoff 링크 2건 + archived `state.json` **5경로 전부** 재작성
- `.archived.json` 의 `open_task_ids` = `[]` (차단을 우회하지 않았다는 증거)
- `active/` 에 남은 브랜치 네임스페이스는 `main` 하나 (빈 `active/fix/` 도 제거)
- `check_branch_memory_namespace` 는 main 에서 다른 네임스페이스를 고쳐도 PASS —
  기본 브랜치는 자기 네임스페이스가 전체다 (case 8)

## 5. 검증

- 전량 2축 **255/255 ×2 green** (native/slash, 각 ~195s)
- 되주입 1건 — 약한 정규식 → case 14 FAIL, 정본 → 14/14 PASS
- CI: **10 체크 전부 success** (smoke 2축 native/slash · mypy-strict · os-matrix · mcp-sdk-matrix) — commit `8a56e96`

## 6. 별건 — 배포 채널이 닫혔다 (TASK-2026-08-14-main-002)

소유자 결정: **PyPI 에 발행하지 않는다.** 키 관리가 번거롭고, 배포는 본인 GitHub 으로만
간다. 그래서 GitHub Releases 가 유일 채널로 확정됐다.

**기록의 목적이 결정 자체가 아니라 *재론 방지*다.** 기술 제약은 v1.2.0 에서 이미 0 이
됐으므로(wheel top-level = `workflow_kit` 하나) "이제 올릴 수 있다" 는 관찰이 앞으로도
계속 나온다 — 그 관찰은 결정을 다시 여는 근거가 아니다. 그래서 정본 한 자리
(`docs/RELEASE.md` §1 **각주 0**)에 결정 + 근거 3 + **재검토 트리거 3** 을 같이 박았다.
트리거(외부 사용자의 실제 요청 / 저장소 밖 배포 사유 / 소유자 지시)가 성립하기 전에는
열지 않는다.

- `TASK-2026-08-13-main-008`(TestPyPI 리허설) → **취소로 done.** 그 task 는 *발행 여부
  판단*의 사전 검증이었고 판단이 끝나 목적이 사라졌다. 업로드는 실행되지 않았다.
  업로드 직전까지의 실측 8종은 **이력으로 보존** — README 렌더링·메타데이터·이름 해석·
  라이선스 동봉·진입점은 GitHub Releases 소비자에게도 유효한 검증이기 때문이다.
- `RELEASE.md` §1 의 각주 1(TestPyPI 1회 한정 허용, 08-13)은 **만료**. 같은 행이
  **하루 만에 두 번** 움직였다 — `release_pipeline.py` 주석이 정책 값을 재진술하지
  않고 정본을 가리키기만 하는 이유의 실증이라, 주석에 그 사실을 적어 뒀다.
- 검토 문서 2건(`pypi-publication-policy-review` / `cli-distribution-review`)은 종결
  표기 후 근거 자료로만 남는다. `blocked` 대기열이 비었다.

## 7. 남은 것

- case 7 은 여전히 코드 블록 안의 *형태가 온전한* 링크는 링크로 본다. 현재 corpus 에는
  없다. 나오면 그때 코드 스팬을 걷는다 (지금 하면 쓰지 않을 코드다).
- **다음 축이 비었다.** PyPI 가 닫히면서 주 작업 축이 사라졌고, 남은 것은 전부 관찰·대기
  항목이다 — [TASK-2026-08-13-main-004] mypy flake 33 run 연속 green(현재 5) /
  [TASK-2026-08-13-main-009] 검사 시간(정숙 구간 36%) / macOS PEP 668 (MacBook 전원 시) /
  cross-host federation / darwin mavis e2e / memory_index 3-tuple 추이.
  다음 세션은 **무엇을 할지부터 정하는 자리**다.
