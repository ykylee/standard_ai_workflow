# 다중 워크스페이스 오케스트레이션 — 설계부터 §10.2 도구화까지 (2026-08-07~08)

- 문서 목적: 이번 세션의 사고 흐름과 실측 근거를 남긴다. handoff 가 담기엔 긴 맥락.
- 범위: 컨셉 검토 → 설계 → 표준 반영 → 도구 3종 구현
- 대상 독자: 다음 세션의 AI agent, 저장소 관리자
- 상태: closed
- 최종 수정일: 2026-08-08
- 관련 문서: [multi_workspace_orchestration.md](../../../../../workflow-source/core/multi_workspace_orchestration.md) (§0 = 정본 요약), [global_workflow_standard.md §10](../../../../../workflow-source/core/global_workflow_standard.md)

## 1. 무엇을 했나 (커밋 5건)

| 커밋 | 내용 |
| --- | --- |
| `7cfdb60` | 설계 문서 + `.gitattributes` union merge (저장소 최초) |
| `8a2a7a9` | 표준 §10 신설 + §1 bullet 2건 — 12 하네스 진입점 전파 |
| `9751cc5` | `seed_workspace_memory.py` (+ smoke 8) |
| `e547942` | `survey_remote_workspaces.py` (+ smoke 8) |
| `c51d052` | `claim_workspace.py` (+ smoke 9) — §10.2 플로우 완결 |

시작 질문은 "사용자 - 서버 - 하네스 3계층으로 워크스페이스를 나누자" 였고, 끝난 자리는
**"브랜치로 나누고 git 이 배타를 판정한다"** 였다. 아래가 그 사이에서 방향을 바꾼 실측들이다.

## 2. 판단을 뒤집은 실측 6건

### 2.1 격리 키를 하네스로 잡으면 기존 도구가 치운다

원안은 `active/<harness>/` 였다. `archive_branch_memory.py` 의
`find_branch_memories()` + `branch_exists()` 를 임시 트리에 **직접 호출**해 보니:

```
active/feat-x/codex   -> branch_exists? False   → 아카이브 대상
active/feat-x/claude  -> branch_exists? False   → 아카이브 대상
active/main           -> branch_exists? True    → 유지
```

하네스 이름 디렉터리는 고아로 판정돼 치워진다. **격리 키는 git 이 존재를 검증할 수 있는
이름이어야 한다** — 이 제약은 우연이 아니라 자동 아카이브가 성립하는 근거다.

### 2.2 hostname 도 IP 도 식별자가 못 된다 — 이미 시도된 적이 있었다

task 템플릿에 `호스트명` / `호스트 IP` 필드가 이미 있었다. 전체 메모리 66 파일 집계:

| 값 | 건수 |
| --- | --- |
| 호스트 IP (빈칸) | 87 |
| `127.0.0.1` | 20 |
| `192.168.0.139` | 12 |
| 호스트명 (빈칸) | 35 |
| `homelab (darwin)` | 2 |

손으로 채우는 필드는 **채워지지 않는다**. 채워진 값도 `127.0.0.1`(아무것도 식별 못 함),
DHCP 사설 IP(재사용), 실제 hostname(`iyeong-gyun-ui-MacBookAir.local`)과 이미 갈라진
별명이었다. → `host_id`(발급) / hostname·IP(진단) / endpoint(접속) 3분리.

### 2.3 인벤토리는 이미 만들어졌고 비어 있었다

`state.json.environment_path` 가 `active/environments/` 를 가리키는데 **그 디렉터리가
없다**. bootstrap 기본값도 생성 도구(`create_environment_record_stub`)도 있는데
**읽는 코드가 없다** — `project_docs.py:266` → `builder.py:445` 로 옮겨 담기만 한다.

2.2 의 빈칸 87건과 같은 실패다: **쓰는 곳은 있는데 읽는 곳이 없으면 아무도 채우지
않는다.** → registry 는 "소비자를 먼저 만든다" 를 조건으로 걸었다.

### 2.4 브랜치 선점이 lease 를 대체한다

파일 lease 를 설계했다가, TTL 회수에 race 가 있음을 실측했다(동시 steal 시 **2명 동시
획득 + 크래시**). `os.link` 원자 claim 으로 고칠 수 있었지만 — 같은 파일시스템 전제라
다중 호스트에서 무너진다.

그때 사용자가 "원격 브랜치 push 로 선점하면?" 을 제안했고, 5-way 경합을 실측했다:

```
agent3 WON / agent1,2,4,5 lost
```

**정확히 1명.** git ref 생성이 원자적이라 push 가 분산 CAS 다. TTL race · NFS 원자성 ·
registry 저장 위치를 **전부 회피**하고 새 인프라가 0 이다. 파일 lease 설계를 폐기했다.

### 2.5 "조용한 소실" 진단이 틀렸다 (자기 정정)

§5B.2 에 "같은 브랜치 whole-file rewrite → 조용한 데이터 소실" 을 실측으로 적었는데,
그건 **내가 손으로 덮어썼을 때**였다. 실제 도구 `upsert_backlog_entry` 는
read-modify-write 라 그렇게 동작하지 않는다 — 두 호스트가 각자 task 를 추가하면
**가시적 CONFLICT** 가 난다. 규약을 "whole-file rewrite 금지" 가 아니라
**"도구를 통해 갱신"** 으로 정정했고, 구현은 불필요해졌다.

### 2.6 fetch 없이 stale 을 판정하면 살아있는 작업을 지우자고 제안한다

다른 호스트가 브랜치를 되살린 뒤 조회하면:

```
fetch 전: idle=72h   → STALE 로 오판
fetch 후: idle= 0h   → active
```

`survey_remote_workspaces.py` 가 fetch 를 **기본값**으로 두고, 생략하려면 `--no-fetch`
를 명시하게 한 이유다. 회귀 검사가 이 경로를 양방향으로 고정한다.

## 3. 검사를 어떻게 잡았나 — "파일이 생겼나" 가 아니라 "복원되나"

seed 도구 구현 중 결함 3건이 나왔는데 전부 **파일은 생겼지만 복원은 안 되는** 부류였다:

1. 라벨 `주 작업 축` ≠ 정본 `현재 주 작업 축` → 필수 섹션 누락
2. 백틱이 summary 에 깨진 문자열로 누출
3. in_progress 를 `- <ID> <제목>: <상태>` 로 썼는데 파서는 ``현재 `in_progress` 작업:``
   라벨 뒤 목록을 읽음 → **빈 리스트**

파일 존재만 보는 검사로는 셋 다 못 잡는다. 그래서 회귀 검사를
**"seed 후 session-start 가 `status=ok` + warnings 0"** 으로 잡았다.

`claim_workspace` 의 force 금지 검사도 같은 의심을 했다 — 공허하게 통과하는 것 아닌가.
도구에 `push --force` 를 일시 주입해 **FAIL 을 재현**한 뒤 원복했다. (초안은 안내 문구의
`--force` 문자열까지 잡는 위양성이 있어 git 호출 인자만 보도록 좁혔다.)

## 4. 사고 1건 (복구됨)

`CLAUDE.md` 규칙 블록을 갱신하면서 `text.index('## 작업 원칙')` 를 썼는데, **본문
인용구(L14)** 에 먼저 걸려 상위 40줄이 삭제됐다. `git checkout` 으로 즉시 복원하고
`re.search(r'^## …$', re.M)` **줄 앵커**로 재작업했다. 최종 diff 는 +2줄.

> 마크다운 섹션 치환은 반드시 줄 앵커를 쓴다.

## 5. 남긴 것

- **표준 §10** — 규칙(모든 소비자 적용). §1 bullet 2건은 12 하네스 진입점에 자동 주입.
  빈 저장소 bootstrap 으로 `AGENTS.md` 2/2, `GEMINI.md` 2/2 전파 실측.
- **설계 문서 §0** — 정본 요약. §1~§8 은 조사 기록이며 뒤집힌 절에 교체 표시를 달았다.
- **도구 3종** — smoke 25 assertions (8+8+9), 전부 green.

## 6. close-out 에서 함께 닫은 것

세션 정리 중 **사전 존재 red 2건**을 닫았다 (이번 작업과 무관하지만 비용이 낮았다):

- `handoff_bloat` — handoff 가 1096줄 / done items 13(cap 10)이었다. 지난 세션들의 교훈
  246줄이 §6 에 그대로 쌓여 있던 게 원인. **106줄로 줄이고 교훈은 각 세션 기록으로
  포인터화**했다. → `check_self_application` **8/8 passed** (오래 red 였던 항목).
- `check_appendonly_memory_layout` — 2026-08-06 task 3건에 frontmatter 가 없었다. 추가. → PASS.

정리 중 두 가지를 실수했고 둘 다 검사가 잡았다:

- 새 handoff 에서 `- **현재 기준선**:` 로 적었더니 파서가 못 읽었다 (`- <label>:` 형식만
  인식). 굵게 표시를 빼서 해결 — `session-start` warnings **0**.
- 세션 기록의 상대 링크를 `../../../../` 로 적었는데 `sessions/` 는 한 단계 더 깊어
  `../../../../../` 였다. 링크 검사가 잡았다.

남은 red 2건: `mcp_installation_by_harness.md` 사본 divergence(`c63b54e`~),
`bootstrap_interactive_picker` 의 `ModuleNotFoundError`.

## 7. 다음 세션에

1. **복수 root 취합** — `_branch_state_paths(root)` 가 단일 root 만 받는다. 지금 바로
   이득이 있는 유일한 항목.
2. **registry** — 범위가 계속 줄어 *다중 호스트 경로 매핑* 만 남았다. 단일 호스트면
   불필요하고, §2.3 의 전례대로 **소비자가 생길 때** 만든다.
3. **사전 존재 red** — append-only frontmatter 3건(2026-08-06 task),
   `mcp_installation_by_harness.md` 사본 divergence(`c63b54e`~),
   `bootstrap_interactive_picker` import 오류.
