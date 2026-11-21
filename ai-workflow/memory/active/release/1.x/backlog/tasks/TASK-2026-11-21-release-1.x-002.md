---
id: TASK-2026-11-21-release-1.x-002
status: planned
created_at: 2026-11-21
source_anchor: generic-task-2026-11-21-release-1.x-002
source_path: backlog/2026-11-21.md
kind: generic
wbs: M-007/WBS-7.2
---

# TASK-2026-11-21-release-1.x-002 — okf_import strict 가 okf_export 가 낸 자기 묶음을 전부 거절한다

## 📝 Description

- Status: planned
- Priority: medium
- Request date: 2026-11-21
- Owner:
- Host:
- Host IP:
- Affected documents:
  - 

- Description: 2026-11-21 main(M-036 WBS-36.3) 실측: 이 저장소 위키를 export_wiki_to_okf(resolve=False) 로 낸 78 페이지 묶음을 import_okf_bundle(mode=strict) 가 78/78 거절 — OKF-§5.1 broken bundle-relative link 467 건(내보내기가 '../concepts/x' 로 쓰고 들여오기는 .md 대상을 찾는다) · V-R9 78 건(last_ingested_from 저장소 경로). loose 로는 78 모두 staged. R16.8 분류: ① 문서화된 동작과 다름.
- Completion criteria: 자기 묶음 strict 들여오기에서 OKF-§5.1 위양성 0 — 내보내기 링크 형식과 들여오기 판정이 같은 규약
- Completion criteria: V-R9 를 strict 에서 어떻게 볼지(저장소 경로 last_ingested_from) 결정을 문서에 남기고 그대로 구현
- Completion criteria: 회귀 case: 저장소 위키 export → strict import, 되주입에서 red

## 🧭 Plan

- Files that change:
- Order of work:
- Plan risks:
- Proof:

## 🛠️ Implementation / Content

- Progress: `2026-11-21 03:05` 기준 2026-11-21 main(M-036 WBS-36.3) 실측: 이 저장소 위키를 export_wiki_to_okf(resolve=False) 로 낸 78 페이지 묶음을 import_okf_bundle(mode=strict) 가 78/78 거절 — OKF-§5.1 broken bundle-relative link 467 건(내보내기가 '../concepts/x' 로 쓰고 들여오기는 .md 대상을 찾는다) · V-R9 78 건(last_ingested_from 저장소 경로). loose 로는 78 모두 staged. R16.8 분류: ① 문서화된 동작과 다름.
- Next session starting point:
- Remaining risks:

## ✅ Outcome

- Result:
- Follow-up:
