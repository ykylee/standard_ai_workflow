# Beta v3.3.4 — 승인 화면 강화 · 미확인 메시지 정리 · 비밀번호 재설정 (2026-11-25)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- 승인 화면이 보이지 않거나 글자 순서를 뒤집는 문자를 `U+…`로 드러낸다(문서 차이 · 새 본문 · 제목 · 질문 · 설명). 글자는 저장된 순서대로 보인다.
- 요청 뒤 문서 판이 바뀐 승인 요청은 **낡은 요청**으로 보이고 승인 단추가 꺼진다.
- 10분 지난 미확인 메시지를 받은 콜사인이 `hub_inbox_ack(decision="seen")`로, 소유자가 화면의 **읽음으로 정리**로 닫는다. 3.3.3 안내문이 틀린 것을 고쳤다.
- `hub admin account password --username …`: 허브 계정 비밀번호 재설정. 비밀번호는 터미널이나 stdin으로만 받고 그 계정의 로그인 · 잠금을 모두 푼다.
- Python 관리 명령이 모르는 인자의 값을 오류문에 되뇌지 않는다.
- `hub_task_update` 설명에 고칠 수 있는 칸(`wbs` 포함)을 적었다. 동작은 전부터 있었다.

## 검증

- 누적 smoke **359/359 PASS**
- `check_hub_screens`가 문서 차이를 줄 단위로 대조하고 보이지 않는 문자 · 낡은 요청 · 정리 단추를 Chrome에서 Python · Go 허브로 잰다.

## 운영 범위

- 평가용 pre-release다. DB 판은 18 그대로다. Go 허브에 `golang.org/x/term` 의존이 늘었다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-11-25T04:56:29Z)_

- total wiki pages: **104**
- total memory entries: **30**
- symmetric links: **0**
- asymmetric count: **2**
- wiki pages with related memory: **0**
- memory entries with mentioned wiki: **2**
- is_symmetric: **False**

### Asymmetric links (advisory)

- `memory_only`: `MEM-2026-07-09-001` ↔ `topics/workflow-audit-2026-07-09.md`
- `memory_only`: `MEM-2026-08-10-001` ↔ `topics/memory-index-retrospective-2026.md`
