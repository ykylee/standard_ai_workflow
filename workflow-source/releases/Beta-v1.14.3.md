# Beta v1.14.3 (2026-09-29)

> **상태: 릴리스 준비.** package `1.14.3`, runtime `__version__ = 1.14.3`, tag `v1.14.3`.
> **patch release** — **`wk backlog-update` 의 update 에서 명시한 `--kind` 가 daily index 의
> `[kind]` 표식에 반영되지 않던 결함** + **문서 스탬프 판정이 날짜 뒤 주석 달린 스탬프를
> 판정 없이 건너뛰던 결함** 수리.
>
> 등급 근거 (§1.5): `wk release-status` 는 **1.14.3 (patch)** 를 제안하고 그대로 따른다
> (fix 2 · feat 0 · breaking 0). 공개 Python API 시그니처 변경 0, 진입점 증감 0.
> `upsert_backlog_entry` 에 추가된 `index_kind` 는 기본값 `None` 인 키워드 전용 인자라 기존
> 호출이 그대로 동작한다.

## 0. 릴리스 판정

두 결함 모두 이 저장소의 99차 세션에서 실제로 밟았다. `--kind session` 으로 만든 task 를
`--kind generic` 으로 고쳤더니 frontmatter 만 바뀌고 daily index 는 `[session]` 으로 남아
index 표식을 손으로 고쳐야 했다. 소비자 프로젝트도 `wk backlog-update` 로 같은 길을 밟으므로
발행한다.

## 1. 릴리스 요약

- 범위: `v1.14.2..` 발행 준비 직전까지 **3 commit**. 이 중 1건(`5a0fd083`)은 **v1.14.2 발행
  마무리**가 태그 뒤에 착지한 것이라 실질은 **2 commit** 이다.
- 누적 smoke **296/296 PASS** (로컬 `--branch-context=all` = 296 × native/slash).
- 검사 **296 → 296** (신설·은퇴 없음 — 기존 검사에 case 추가).

## 2. 소비자에게 보이는 변화

### 2.1 update 에서 명시한 `--kind` 가 daily index 표식을 따라 바꾼다 (`8f5619ca`, TASK-2026-09-29-main-008)

update 는 daily index block 을 보존하고 `- status:` 줄만 바꾼다 (TASK-2026-08-11-main-023 —
그 전에는 교체가 손 sub-bullet 과 `[kind]` 를 덮었다). 그 보존이 `--kind` 를 **명시한**
경우까지 적용돼, task SSOT frontmatter 의 kind 와 index 의 `[kind]` 표식이 갈라졌다.

이제 `--kind` 를 명시하면 head 줄의 `[kind]` 표식만 그 값으로 바꾸고, 제목·sub-bullet 은 여전히
보존한다. `--kind` 를 생략하면 표식을 건드리지 않는다.

**적용**: kit 을 1.14.3 으로 올리면 된다. 이미 갈라진 항목은 같은 task 에 `--kind <값>` 으로
update 를 한 번 돌리면 맞춰진다.

### 2.2 날짜 뒤 주석 달린 스탬프는 판정 불가로 낸다 (`cad0d836`, TASK-2026-09-29-main-007)

`workflow_kit.common.doc_stamp` 에 `stamp_format_violation(text)` 를 추가했다. 문서에
`- 최종 수정일:` 필드가 있는데 값이 날짜 하나가 아니면(`2026-07-16 (v0.14.0 …)` 처럼 뒤에
주석이 있으면) 그 설명을 돌려준다. 템플릿 자리표시자 `YYYY-MM-DD` 는 예외다.

같은 모듈의 스탬프 전용 변경 판정은 날짜 뒤 주석 달린 줄도 스탬프 줄로 센다. 그래서 주석만
지우는 정규화가 '내용 변경' 으로 잡혀 오늘 날짜를 요구받지 않는다.

**적용**: 이 판정을 게이트로 쓰는 곳은 이 저장소의 `check_doc_stamp_rule` 이다. kit 의
`doc-headers-update` 동작은 바뀌지 않는다 — 여전히 날짜만 있는 스탬프 줄을 올린다.

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- `check_backlog_update_layout` 11/11 (case 11 신설): session → `--kind generic` update 에서
  frontmatter · index 표식 모두 generic, 손 sub-bullet 보존. 되주입(표식 전달 제거) red
- `check_appendonly_memory_layout`: session 표식 항목이 `tasks/<id>.md` SSOT 를 가지면 resolve.
  되주입(교정 제거 + 실저장소 `[session]` 표식) red
- `check_doc_stamp_rule` 12/12 (case 11·12 신설). 정규화 전 실저장소 case 10 이 주석 달린
  스탬프 5건으로 red. 되주입 2종(주석 줄 비인정 → case 10·12 red / 형식 판정 무력화 → case 11 red)

## 4. 알려진 한계 (감추지 않는다)

- `ai-workflow/wiki/` 의 `- 상태:` 헤더 없는 페이지 6건은 스탬프를 달고 있지만 동결 문서로
  분류돼 판정 밖이다. 헤더 부재를 동결 신호로 보는 규칙이 wiki 페이지에 맞는지는 별도 판단이다.
- MiniMax Code CLI 가 프로젝트 로컬에서 어느 대소문자 경로를 읽는지는 여전히 미실측이다.
- **Windows 는 현재 미측정이다** (`TASK-2026-08-25-main-017` blocked).

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-09-29T03:40:25Z)_

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
