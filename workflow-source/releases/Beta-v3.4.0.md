# Beta v3.4.0 — 아이디어 박스 (2026-11-25)

> **상태: 실환경 pilot용 pre-release.** GitHub Release는 prerelease로 표시하고 안정판 latest는 v2.1.0에 둔다.

## 변경

- 프로젝트에 **아이디어** 화면을 더했다. 로그인한 승인된 사람이 대충 적으면 다음 에이전트 세션이 읽기만 해 검토하고 회신한다.
- 사람이 회신을 보고 더 묻기 · 보관 · 닫기 · task 등록을 고른다. task 등록은 WBS 게이트를 거친다.
- 새 도구 `hub_idea_add` · `hub_idea_list` · `hub_idea_get` · `hub_idea_claim` · `hub_idea_reply`. 세션 시작 응답이 검토할 아이디어를 최대 2건 가리킨다(worker 제외).
- Go 허브의 다른 출처 거절 코드가 Python 과 같은 `origin_mismatch` 다.

## 검증

- 누적 smoke **360/360 PASS**
- `check_hub_ideas` 가 Python · Go 실프로세스를 같은 요청으로 재고 응답을 대조하며, 실제 Chrome 으로 적기 · 회신 · 등록 · 휴대폰 폭을 잰다.

## 운영 범위

- 평가용 pre-release다. **DB 판이 18 → 19로 오른다** — 3.3.x 실행 파일은 이관된 DB를 열지 못하므로 되돌리려면 배포 전 백업을 쓴다.
- 허브는 LLM을 부르지 않는다. 회신은 에이전트 세션이 열릴 때 나온다. 검토 세션이 규칙(읽기만)을 지키는지는 하네스별로 재지 않았다.
