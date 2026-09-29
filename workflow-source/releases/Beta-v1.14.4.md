# Beta v1.14.4 (2026-09-29)

> **상태: 릴리스 준비.** package `1.14.4`, runtime `__version__ = 1.14.4`, tag `v1.14.4`.
> **patch release** — **Windows 에서 `wk doctor` 의 MCP 해석기 탐침이 `python3.CMD` shim 을
> 거치면 결과를 못 내던 결함** + **문서 스탬프 판정이 wiki 페이지와 굵은 `- **상태**:` 헤더
> 문서를 판정 밖에 두던 결함** 수리.
>
> 등급 근거 (§1.5): `wk release-status` 는 **1.14.4 (patch)** 를 제안하고 그대로 따른다
> (fix 3 · feat 0 · breaking 0). 공개 Python API 는 **추가만** 있다 —
> `workflow_kit.common.doc_stamp` 의 `is_wiki_page` · `read_stamp` · `write_stamp` ·
> `HEADER_STAMP_RE`, `doc_layers.is_live_marked`, `paths.wiki_dir_for_workspace`.
> `stamp_format_violation` 에 붙은 `path` · `repo_root` 는 기본값 `None` 인 키워드 전용
> 인자라 기존 호출이 그대로 동작한다. 진입점 증감 0.

## 0. 릴리스 판정

Windows 결함은 소유자가 전달받은 소비자 환경 실측이다. `wk doctor` 가 MCP 서버를 띄울
해석기를 재는 절이 Windows 에서는 늘 `probe_failed` 로 끝나, 해석기 · 버전 정합을 확인할
길이 없었다. 소비자에게 바로 닿으므로 발행한다.

## 1. 릴리스 요약

- 범위: `v1.14.3..` 발행 준비 직전까지 **6 commit**. 이 중 1건(`0c7a89e9`)은 **v1.14.3 발행
  마무리**가 태그 뒤에 착지한 것이고 2건은 세션 종료 기록이라 실질은 **3 commit** 이다.
- 누적 smoke **296/296 PASS** (로컬 `--branch-context=all` = 296 × native/slash).
- 검사 **296 → 296** (신설·은퇴 없음 — 기존 검사에 case 추가).

## 2. 소비자에게 보이는 변화

### 2.1 doctor 의 MCP 해석기 탐침이 Windows 배치 shim 을 지난다 (`388ee750`, TASK-2026-09-29-main-013)

탐침은 MCP command(`python3`)를 PATH 에서 해석한 실행 파일로 38줄짜리 스크립트를 돌린다.
그 스크립트를 `-c` 인자로 넘겼는데, Windows 에서 해석 결과가 `python3.CMD` 같은 배치
shim 이면 cmd.exe 가 명령행을 다시 해석하며 **첫 개행 뒤를 버린다**. 탐침은 첫 줄만 돌고
아무것도 출력하지 않아 `probe_failed` 가 됐다.

이제 스크립트를 **stdin 으로**(`python -`) 넘긴다. 인자에는 개행 없는 `-` 하나만 남는다.
스크립트는 ASCII 만 쓴다 — Windows 에서 stdin 은 로캘 인코딩으로 쓰이기 때문이다.

**적용**: kit 을 1.14.4 로 올린 뒤 `wk doctor` 를 다시 돌리면 MCP 해석기 절이 실제 판정
(`in_sync` / `version_mismatch` 등)을 낸다.

### 2.2 wiki 페이지의 스탬프는 frontmatter `updated:` 하나다 (`31fdfd64`, TASK-2026-09-29-main-012)

wiki `SCHEMA.md` 는 `updated:` 를 스탬프로 정하고 lint · `score_wiki_maintainability` ·
okf export 가 그것을 읽는데, `wk release-pipeline doc-headers-update` 는 문서 헤더
`- 최종 수정일:` 만 알았다. 이제 `ai-workflow/wiki/` 안의 페이지는 `updated:` 를 읽고
올린다. 어느 필드인지는 `doc_stamp.read_stamp` / `write_stamp` 하나가 정한다. wiki
페이지에 `- 최종 수정일:` 이 또 있으면 `stamp_format_violation(text, path=…, repo_root=…)`
이 두 번째 스탬프로 거절한다.

**적용**: wiki 를 쓰는 프로젝트는 `doc-headers-update --dry-run` 으로 뒤처진 `updated:`
목록을 먼저 본다. wiki 페이지에 헤더식 `- 최종 수정일:` 을 달아 두었다면 그 줄을 지운다
(스탬프 줄만 지우는 변경은 내용 변경으로 세지 않는다).

### 2.3 살아있다는 선언을 두 표기 더 읽는다 (`c54a3a54`, TASK-2026-09-29-main-010)

스탬프 판정은 `- 상태:` 헤더가 없는 문서를 동결로 본다. 그 헤더를 평문 한 가지로만 알아서
**굵은 `- **상태**:`** 문서와 **wiki frontmatter `status:`**(active · draft · proposed ·
accepted) 페이지가 전부 동결로 읽혔다. `doc_layers.is_live_marked` 가 둘을 함께 읽는다.
wiki 루트 밖의 export 스냅샷(`docs/samples/okf-bundle-*`)은 여전히 동결이다.

**적용**: 굵은 헤더를 쓰는 프로젝트는 `doc-headers-update` 가 보는 문서가 늘어난다.
`--dry-run` 으로 먼저 확인한다.

## 3. 검증

- 전량 게이트 `--branch-context=all` — 발행 준비 커밋에서 실행 (결과는 발행 기록에 남긴다)
- `check_deploy_doctor` 53/53: 인자를 첫 개행에서 자르는 fake shim 경유 탐침 case 신설.
  shim 이 결함을 재현하는지 같은 case 에서 따로 잰다. 옛 `-c` 호출 되주입 → red
  (출력 없음 → JSON 파싱 실패, 보고 증상과 같은 모양)
- `check_doc_stamp_rule` 15/15 (case 13 · 14 · 15 신설): case 10 은 살아있는 316건 중 300건 판정,
  그중 wiki `updated:` 88건. 되주입 main-010 6종 · main-012 8종 전부 red

## 4. 알려진 한계 (감추지 않는다)

- **Windows 는 여전히 이 저장소가 직접 재지 못한다.** 2.1 은 cmd.exe 의 절단을 모형화한
  fake shim 으로 검증했고, 실제 cmd.exe 실측은 소유자 환경에 맡긴다.
- 같은 부류의 다줄 `-c` 호출이 개발 게이트 전용 `common.python_floor` 에 남아 있다 —
  게이트를 Windows 에서 돌리지 않으므로 이번 범위 밖이다.
- `TASK-2026-08-25-main-017` (MCP emit command 가 항상 `python3`) 는 blocked 그대로다.
- MiniMax Code CLI 가 프로젝트 로컬에서 어느 대소문자 경로를 읽는지는 여전히 미실측이다.

## Bidirectional link audit

_자동 emit (Phase 13 AC4+, 2026-09-29T05:15:02Z)_

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
