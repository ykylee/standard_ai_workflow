# 세션 기록 — 기술보고서 작성 + TIMEOUT flake 해소 (2026-08-11, 4차)

- 문서 목적: 2026-08-11 4차 세션 (TASK-014~016 + 부수 수정) 의 결정·산출물·교훈 기록
- 범위: TASK-2026-08-11-main-014/015/016, watcher handshake 수정, 소유자 결정 2건
- 대상 독자: AI agent (다음 세션), 저장소 관리자
- 상태: archived (세션 종료 시점 기록)
- 최종 수정일: 2026-08-11
- 관련 문서: [state.json](../state.json), [session_handoff.md](../session_handoff.md), [backlog/2026-08-11.md](../backlog/2026-08-11.md)

## 1. 세션이 한 일 (시간순)

1. **TASK-014 종결 (미삽입 확정)** — v1.1.0·v1.1.1 노트 누적 표기: 태그 시점
   파일 수는 실측 (251/252) 이나 당시 전량 green 실행 기록이 없어 N/N PASS
   사후 삽입은 날조. 파서 2곳은 최신 노트만 읽어 동작 지장 0. 사용자 결정.
2. **소유자 결정: branch protection 보류** — `main` 미보호 (404) 인지한 채
   일단 켜지 않음. 재검토 시 `wk check-branch-protection` 부터.
3. **전체 상태 검토** — dashboard 전 패널 정상 (north-star 0, smoke 249/249,
   drift 6/6). 신규 발견: 로컬 병렬 전량 TIMEOUT flake 2건 → TASK-015 등록.
   부수 자기 사례: 첫 전량 실행을 `| tail` 로 파이프해 exit 1 을 가릴 뻔
   ("게이트 명령은 파이프에 넣지 않는다" 재현).
4. **TASK-016: 학습회 자료 → 사내 기술보고서** — 산출물 2건
   (`docs/reports/ai-agent-workflow-tech-report-plan.md` + `-report.html`,
   논문 8장 + 참고문헌, 단일 파일, A4 12p). **사후 검토 4회전**:
   ①내용 (실명 오류·표3 전재 누락) ②수치 전수 (기간 "14개월" 날조 → 실측
   4개월 — 사용자 지적, "smoke 24→249" → 199→249, CLI 65+ → 68,
   "세 검사 모두 되주입" 과장 완화) ③문체·어휘 (비일상 어휘 12종 교체/풀이,
   폭 920px, 부제 축약) ④**학습회 독립화** (사용자 결정 — 보고서에서 학습회·
   발표 서술 전부 제거, 보고서가 단독으로 성립).
5. **watcher handshake 수정** — `check_watch_transient_writer` CI flake:
   0.5s 고정 sleep 중 watcher 가 baseline 을 못 뜨면 변경 2건이 1건으로 접힘.
   도구가 baseline 확보 직후 `watcher_ready.json` 을 남기고 검사가 대기 (708eb94).
6. **TASK-015: TIMEOUT flake 근본 해소** — `CHECK_TIMEOUT_S` 파일 안 선언 신설
   (runner 가 AST 로 읽어 `--timeout` 과 max — 늘릴 수만 있음). 부하 실측 ≥40s
   위험군 6검사에 150s 선언 (`wiki_score` 57s 는 다음 flake 후보였음).
   `check_parallel_smoke` case 10 (되주입 양방향 + decoy 불인정 + max 의미론),
   `--tests-dir` 외부 경로 ValueError 수정, CLAUDE.md 규약 문서화.
   **검증: 전량 2축 ×2회 = 4패스 249/249, TIMEOUT 0** (b636e2f).

## 2. 교훈

- **산문 속 수치가 날조의 주 경로** — 표 수치는 출처를 물으며 채우는데, 문장
  속 기간·추이·개수는 서사 리듬에 맞는 그럴듯한 값이 검증 없이 흘러든다.
  실명 문서는 발행 전 숫자 포함 문장을 전수 추출해 실측 대조할 것 (agent
  memory `prose-numbers-are-the-fabrication-path` 로 고정).
- **고정 sleep 은 handshake 가 아니다** — 기동 대기는 준비 신호 (ready 마커)
  를 기다려야 한다. 로컬에서 빠르면 통과하는 race 는 CI 부하에서 터진다.
- **timeout 상한과 실행 시간의 여유를 재라** — 60s 상한에 solo 30s 검사는
  병렬 부하 2배면 죽는다. 상한 조정은 목록이 아니라 파일 안 선언으로
  (드리프트 방지, REQUIRES_QUIET_REPO 와 동일 패턴).

## 3. 남긴 것

- 2026-08-11 backlog **16건 전부 종결** (planned/in_progress/blocked 0).
- 다음 후보 축 2건 (이 호스트에서 즉시 진행 불가): darwin homelab 검증
  (mavis e2e + federation cross-host) / memory_index 3-tuple 지표 추이 관찰.
- 기술보고서 제출 전 사용자 기입: 작성자 소속·이름 / 문서번호 placeholder.
