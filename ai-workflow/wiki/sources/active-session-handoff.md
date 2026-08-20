---
type: meta
status: draft
r9_skip: true
title: active-session-handoff
created: 2026-07-22
last_touched: 2026-08-20
---

# Active Session Handoff (Derived View, 2026-08-20)

> L1 SSOT: `ai-workflow/memory/active/main/session_handoff.md` (364 lines)
> 본 L2 파생 뷰는 in-repo retrieval 용 압축 요약이다. 정본은 L1 SSOT 를 본다.
> 생성: `2026-08-20` by `workflow_kit.tools.refresh_wiki_memory --emit-l2`

## 현재 기준선

**50차 세션 (이어서) — main-003 close: OKF v0.2 이행 (ADR-026 채택).** ADR-006 이 고정한 v0.1 을 새 ADR 로 옮겼다. SPEC 원문(1003줄) §13 을 직접 대조 — breaking 2건에 **둘 다 소비자 fallback 이 명시**(`timestamp`, 본문 `# Citations`)돼 있고 나머지는 전부 additive 라, **legacy 를 남긴 채 정규 필드를 더하면 한 번들이 v0.1·v0.2 소비자를 다 만족**한다 — 이 관측이 결정의 축이다. **`status` 만 실질 위험**: v0.2 에서 정규 필드로 승격돼 §11 의 관용 보장(unknown key 한정) 밖이 됐고, `stable` 필터에 71장 중 69장이 조용히 빠진다. `active`/`accepted`→`stable` · `proposed`/`draft`→`draft` · `superseded`/`deprecated`→`deprecated`, 원문은 `wiki_status` 로 보존. **생략도 답이 아니다** — §5.4 의 `Absent status ⇒ stable` 때문에 생략이 곧 stable 주장이다. **`sources` 를 낸다** — in-repo 출처가 처음으로 본문 산문이 아니라 기계가 읽는 필드에 들어갔다(§5.1 이 entry `resource` 로 경로·범위 서술을 허용). **`generated` 는 안 낸다** — §5.2 가 `by` 를 REQUIRED 로 두는데 우리는 페이지별 actor 기록이 없고, 도구 이름은 거짓이며 `human:` 은 생성물까지 사람 것으로 만들어 §5.3 trust tier 를 부풀린다. **이행이 결함 하나를 드러냈다**: ADR-011 정책이 `older → error` 라 v0.2 로 올리는 순간 **v0.1 번들 전부를 거부**한다 — 우리가 v0.1 인 동안 **도달 불가능한 분기**였고, 48차에 실측한 openwiki 가 바로 v0.1 이다. SPEC §12/§13 이 정반대를 말하므로 같은 major 의 낮은 minor 는 `pass` 로 바꿨다. **버전을 올리는 일은 생산 형식만의 문제가 아니었다.** 버전 리터럴은 `okf_export.OKF_SPEC_VERSION` 한 곳이고 튜플은 파생이다. check_okf_export 20→25 · check_okf_import 25→27, 되주입 6종 red 실증, 검사 파일 수 264 유지.

## 진행 중

- TASK-2026-08-14-main-009 task SSOT 4단계 — 본문 라벨 영어 전환 (release 경계)

## 차단

- (없음)
