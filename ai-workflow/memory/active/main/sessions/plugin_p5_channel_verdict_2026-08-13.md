# 28차 세션 기록 — 플러그인 전환 P5: 실측 게이트 + 채널 전환 판정 (2026-08-13)

- 문서 목적: 28차 세션의 작업 내용·산출물·다음 시작 포인트 기록
- 범위: TASK-2026-08-12-main-018 (P5 — 실측 종합 + INSTALLATION 개편 + 판정)
- 상태: done
- 최종 수정일: 2026-08-13
- 관련 문서: [전환 계획 §3-P5·§6-보론](../../../../docs/planning/plugin-transition-plan-2026-08.md), [27차 세션 기록](./plugin_multi_harness_adapters_2026-08-13.md)

## 1. 지시

사용자: "좋아 다음 진행하자" — 기준선의 다음 작업(TASK-018, P5) 실행. 판정 2건은
AskUserQuestion 으로 소유자 확인을 받았다.

## 2. 실측 3건

1. **SessionStart hook 규칙 주입: 성립.** 프로브 플러그인(마커 echo hook)을
   `--plugin-dir` 로 싣고 중립 디렉터리에서 headless 로 물었더니 **모델이 마커를
   그대로 반환했다** — hook stdout 은 모델 컨텍스트에 실제 주입된다. 원칙 3 이
   걸어 둔 "CLAUDE.md 형 상시 주입 갭" 전제가 채워졌다.
2. **Gemini 모델 주입 계층: 미검증 유지** (P3 의 tier 차단 그대로) — 판정에는
   로드 계층 실측만 반영.
3. **marketplace 업데이트: 수동 흐름 성립.** `marketplace update <name>` +
   `plugin update <name>@<marketplace>` — **plugin update 는 풀 id 필수** (이름만
   주면 not found, 실측). 최신이면 버전 비교로 "already at latest", 적용은 재시작 후.

## 3. 부수 발견 — 설치 선언 소실 사고

P2 의 자기 적용 선언(user settings 의 `extraKnownMarketplaces`/`enabledPlugins`)이
세션 시작 시점에 **통째로 사라져 있었다** (marketplace 목록에 official 만).
settings.json 외부 재작성 추정, 원인 미확정. 재설치로 복구 (v1.1.8-beta, scope
user, enabled). INSTALLATION §7.0 에 재설치 명령과 리스크를 명시했다.

## 4. 판정 (소유자 확인, 2026-08-13)

- **채널 판정 = (a) 플러그인 주 채널 승격 + bootstrap 병행 유지.** bootstrap 은
  진입점 규칙 주입 / 플러그인 미지원 하네스 / 오프라인 담당.
- **hook 규칙 주입 편입 = 별도 task** [TASK-2026-08-13-main-003] — 진입점에 규칙
  블록이 이미 있는 프로젝트의 이중 주입 방지를 위해 **조건부 주입** 설계 선행.

## 5. 산출물

- 계획 §3-P5 실행 결과 + **§6-보론 전환 완료 판정** (4조건 전부 성립 — 본 전환
  계획 종료). 헤더 상태 = 완료.
- `INSTALLATION_AND_USAGE.md` **§7.0 신설** — 플러그인 설치 권장 경로 승격
  (Claude Code marketplace 2명령 + Gemini 로컬 경로 설치 — GitHub URL 설치는
  manifest 루트 제약으로 불성립 명시), §7.1 bootstrap 은 미지원 하네스·오프라인·
  진입점 규칙 주입 담당으로 재배치. wk 설치 전제(원칙 4)와 선언 소실 리스크 명시.
- 로드맵 §8 플러그인 축 = 완료 갱신 (+ `ai-workflow/core` 미러 동기 — HEAD 시점
  동일성 확인 후 cp).
- 후속 task 등록: [TASK-2026-08-13-main-003] hook 조건부 규칙 주입.
- 전량 2축 **252/252 ×2 green** (exit 0).

## 6. 남은 것 (전환 계획 밖 후속)

- Gemini 모델 주입 실측 — 계정 tier(Antigravity 이전) 해소 후.
- goose 실기 검증 — goose 가용 환경 (예: MacBook 합류 시).
- [TASK-2026-08-13-main-003] hook 조건부 규칙 주입 / [TASK-2026-08-13-main-002]
  bootstrap OpenCode 방언 / [TASK-2026-08-13-main-001] bump 검사 sandbox 이관 /
  [TASK-2026-08-12-main-019] macOS PEP 668.
- 다음 릴리스 (v1.1.9 또는 v1.2.0): P1~P5 산출물 + 기존 예약분 (2nd cycle shim
  drop + `--bundle` 기본값 전환) — 발행 시점은 소유자 결정.
