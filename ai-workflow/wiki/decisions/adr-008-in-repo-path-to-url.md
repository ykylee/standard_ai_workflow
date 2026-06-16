---
type: decision
status: proposed
adr_id: ADR-008
decided_at: 2026-06-16
accepted_in: (proposed — v0.7.33+ candidate)
alternatives_considered: [no-resolve, ci-time-resolve, opaque-resource-key, full-vcs-integration, runtime-web-fetch]
related_pages: [concepts/okf-open-knowledge-format, decisions/adr-006-okf-compat-frontmatter, decisions/adr-007-okf-consumer-mode, concepts/wiki-source-rule-r9, patterns/wiki-stub-emit]
created: 2026-06-16
updated: 2026-06-16
r9_skip: true
---

# ADR-008: in-repo `last_ingested_from` path 의 OKF `resource` 자동 resolve

## Status

**Proposed** (2026-06-16). 본 ADR 은 `concepts/okf-open-knowledge-format.md` §12.1 follow-up 2 + ADR-006 §5 (Negative 3) 의 "Resource URL 좁음" 문제 해결. 채택 확정 시 status 를 `accepted` 로 전환하고 v0.7.33 PATCH release note 에 등재.

## Context

ADR-006 채택으로 우리 wiki 가 OKF spec 권장 5 field bridge 를 가지게 됐다. mapping 로직은 `_derive_resource(last_ingested_from)` 함수 하나 — `last_ingested_from` 이 URL 일 때만 `resource` 로 emit, in-repo path 면 `resource` 비움.

**관측된 한계** (ADR-006 §5 Negative 3):

> **Resource URL 좁음**: `last_ingested_from` 가 in-repo path 면 OKF `resource` emit 안 함. OKF consumer 가 이 page 의 underlying asset URI 모름. → follow-up: in-repo path 를 외부 URL 로 resolve 하는 helper 검토 (별도 turn).

**예시:**

```yaml
# 현재 wiki frontmatter (ADR-006 채택 후, in-repo path)
last_ingested_from: workflow-source/workflow_kit/README.md
```

→ export 시 OKF frontmatter:

```yaml
type: entity
title: workflow_kit
last_ingested_from: workflow-source/workflow_kit/README.md   # extra key (unknown key OK)
# resource: <empty>   ← OKF consumer 가 이 page 의 underlying asset URI 모름
```

**OKF spec §4.1 의 `resource` 의미** (verbatim):

> `resource` (Optional canonical URI for the underlying asset)

`workflow-source/workflow_kit/README.md` 의 canonical URI 가 GitHub blob URL 라면, OKF consumer 가 그 URL 로 직접 fetch 가능 — wiki page 의 *single source of truth* 에 접근 가능.

**현재 상황 (2026-06-16):**

- ADR-006 (status: proposed) 채택. `workflow_kit/okf_export.py` PoC 가 `resource` 를 URL-only 로 매핑.
- 우리 repo 의 GitHub remote: `https://github.com/ykylee/standard_ai_workflow.git` (canonical origin)
- 우리 wiki 의 `last_ingested_from` 가 in-repo path 일 때 80% 이상 (release note, source code, README, docs, etc.)

## Decision

**in-repo `last_ingested_from` path 를 canonical GitHub blob URL 로 자동 resolve 하는 helper 를 도입한다. resolve 결과는 OKF `resource` field 에 emit, `last_ingested_from` 은 그대로 extra key 로 보존.**

**구체적 결정:**

1. **Resolve Algorithm** (deterministic, no runtime fetch):
   - Input: relative path (e.g. `workflow-source/workflow_kit/README.md`)
   - Output: canonical GitHub blob URL (e.g. `https://github.com/ykylee/standard_ai_workflow/blob/main/workflow-source/workflow_kit/README.md`)
   - Steps:
     1. `git config --get remote.origin.url` 로 origin URL 추출 (HTTPS form normalize)
     2. origin URL 에서 `.git` suffix 제거
     3. base URL = `<origin>/blob/<default-branch>/`
     4. in-repo path 와 결합 → `f"{base}{path}"`
     5. default branch 는 `git symbolic-ref refs/remotes/origin/HEAD` 또는 `git branch --show-current` (CI/local 분기)

2. **Fallback 정책** (resolve 실패 시):
   - git remote 미설정 → `resource` 비움 (현재와 동일), `last_ingested_from` 보존
   - default branch detect 실패 → `main` 가정 (warning emit)
   - path 가 repo root 외부 (`../` 또는 `/` 시작) → `resource` 비움 (security: path traversal 방지)
   - path 에 URL scheme 포함 (`http://`, `https://`) → resolve skip, 그대로 `resource` 사용 (ADR-006 의 기존 URL-only path)

3. **CI 환경 처리**:
   - CI runner 에서 origin remote 가 보통 설정됨. 다만 `git fetch` 미실행 시 `refs/remotes/origin/HEAD` 부재 가능 → fallback chain
   - GitHub Actions 의 `GITHUB_SERVER_URL` + `GITHUB_REPOSITORY` env var 도 사용 가능 (CI 우선, local fallback)
   - 환경별 우선순위:
     1. `GITHUB_SERVER_URL` + `GITHUB_REPOSITORY` (CI, 가장 신뢰)
     2. `git config --get remote.origin.url` (local + fetch 후)
     3. `None` (resource 비움, warning)

4. **Branch 추적**:
   - default branch (`main` / `master` / `HEAD`) 가 canonical. → URL 의 `blob/main/` 하드코딩
   - commit-pinned URL (`blob/<sha>/<path>`) 는 *out of scope* (deterministic + simple 우선)
   - 향후 `adr-XXX-commit-pinned-url` 후보

5. **도구 surface** (ADR-006 의 `workflow_kit/okf_export.py` enhancement):
   - 신규 module: `workflow_kit/path_resolver.py` (단일 책임, ~80 lines)
   - API: `resolve_in_repo_path_to_url(relative_path: str, repo_root: Path) -> str | None`
   - `okf_export.py` 의 `_derive_resource` 가 이 helper 호출. URL-only heuristic + in-repo resolve 양쪽 처리.

6. **CLI flag** (opt-out):
   - `python -m workflow_kit.okf_export --no-resolve` — in-repo path 의 자동 resolve 끄기 (기존 ADR-006 behavior 보존)
   - default: resolve ON. 80% 케이스에서 `resource` 채워짐.

7. **Lint 영향**:
   - V-R9 unchanged (path 가 아니라 URL 출력이라 lint 무관)
   - 신규 lint 후보: V-R10 (URL validity) — 별도 ADR

8. **scope 경계**:
   - **in-scope**: GitHub (HTTPS origin) only. GitLab / Bitbucket 는 *out of scope* (heuristic 변환 위험).
   - **in-scope**: `https://` origin 만. `git@github.com:...` SSH form 은 detect 시 normalize.
   - **out-of-scope**: commit-pinned URL, branch-specific URL, submodule path, symlink resolve

## Alternatives Considered

### A. No resolve (status quo, ADR-006 default)

- **장점**: 0 구현 비용. lint 영향 0.
- **단점**: 우리 wiki 의 80% page 가 in-repo path → `resource` 비움 → OKF consumer 가 underlying asset fetch 불가. ADR-006 의 "interop unlock" 의 *partial* 미달.
- **탈락 사유**: OKF spec 의 `resource` 가 *optional* 이긴 하나, 채울 수 있는데 안 채우면 spec 의 *semantic value* (canonical URI for the underlying asset) 미사용. 손쉬운 win.

### B. CI-time resolve (매 commit 마다 GitHub Actions 에서 URL table 생성)

- **장점**: local 환경 의존 0. deterministic.
- **단점**: wiki frontmatter 와 CI artifact 가 분리됨. merge 시 artifact 갱신 필요. 우리 R5 (additive merge) 와 충돌. 운영자 confusion (어느 게 source of truth?).
- **탈락 사유**: wiki 가 SSOT 인데 artifact 가 별도면 *two source of truth* anti-pattern. ADR-001 (3-layer) 의 Source 가 SSOT 원칙 위배.

### C. Opaque resource key (random ID + sidecar mapping table)

- **장점**: URL 노출 안 함. internal-only 식별자.
- **단점**: OKF spec 의 `resource` 는 *canonical URI* 명시. opaque ID 는 spec 위반. OKF consumer 가 ID 해석 못함.
- **탈락 사유**: OKF spec 위반. ADR-006 의 "spec-aligned" 와 정면 충돌.

### D. Full VCS integration (commit hash, branch, dirty flag 등 metadata 포함)

- **장점**: reproducibility, audit, provenance 최강.
- **단점**: 구현 복잡. OKF spec 의 `resource` 는 canonical URI 1개 (단일 field). metadata 는 별도 frontmatter key 로 (e.g. `vcs_commit: <sha>`). 우리 R-9 의 *provenance* 와 중복.
- **탈락 사유**: OKF spec 의 *semantic* URI vs *operational* metadata 분리. 본 ADR 은 URI 부분만 다룸. metadata 부분은 별도 ADR (V-R10 + commit-pinned URL).

### E. Runtime web fetch (HTTP HEAD 로 URL 유효성 검증)

- **장점**: stale URL 즉시 detect. CI 에서 link checker 역할.
- **단점**: deterministic 아님. CI 시간 증가. OKF consumer 가 stale URL 받으면 *useless*. → resolve 가 *best-effort* 라 offline OK 여야.
- **탈락 사유**: ADR-008 의 resolve 는 *deterministic + offline* 원칙. runtime fetch 는 별도 lint (V-R10) 후보.

## Consequences

### Positive

1. **Resource coverage 80% → ~100%**: 우리 wiki 의 80% page (in-repo path) 가 OKF `resource` 채워짐. ADR-006 의 *partial interop* → *full interop* 으로 격상.
2. **OKF spec semantic 활용**: `resource` 의 *canonical URI for the underlying asset* 의미가 실제 fetch 가능한 URL 로 채워짐. OKF consumer (e.g. reference `visualize` viewer) 가 link click → GitHub source 로 직접 이동 가능.
3. **Provenance dual preservation**: `last_ingested_from` (in-repo path) + `resource` (GitHub URL) 양쪽 emit. 우리 R-9 의 *audit* + OKF spec 의 *canonical* 동시 만족.
4. **CI/local 양립**: GitHub Actions env var 우선, local `git config` fallback. CI runner 와 local dev 모두 deterministic.
5. **Opt-out 보존**: `--no-resolve` flag 로 기존 ADR-006 behavior 보존. backward-compatible.
6. **Security**: path traversal 방지 (`..` prefix reject), URL scheme 검증 (HTTPS only, SSH normalize). supply-chain attack surface 축소.

### Negative

1. **GitHub 의존성**: GitLab / Bitbucket / self-hosted Git 의 URL heuristic 변환은 *out of scope*. 우리 repo 가 GitHub 라 현재 OK이나, 향후 platform 이동 시 별도 ADR.
2. **Default branch 가정**: `main` 가정 fallback. 우리 repo 는 `main` 이라 OK. 다른 default branch (`master`, `develop`) 사용 시 warning + URL 부정확 가능.
3. **CI 환경 차이**: local `git symbolic-ref` 가 미설정 시 `main` 가정. CI 에서 `GITHUB_SERVER_URL` + `GITHUB_REPOSITORY` env var 없으면 fallback. → 두 layer 모두 부재 시 `resource` 비움 (warning).
4. **Branch drift**: feature branch 작업 중 export 시에도 URL 은 `main` 가리킴. working copy 의 branch 와 URL 의 branch mismatch. → commit 후 merge 시 자동 정정 (main rebase 시점). 일시적 mismatch 는 ADR-008 의 *expected behavior*.
5. **Path 변경 시 URL 갱신**: `last_ingested_from` path 가 rename 되면 `resource` 도 갱신. manual 갱신 부담. → 별도 lint (V-R10, ADR 후보) 가 stale URL detect.
6. **`last_ingested_from` extra key 중복**: `last_ingested_from` (in-repo path) + `resource` (URL) 양쪽 emit → 1 page frontmatter 비대. ADR-006 의 5 OKF field + 우리 6 native field = 11+ field. → OKF spec 이 unknown key tolerate 하므로 OK, 그러나 lint 가 *frontmatter cardinality* 추적 시 noise.

### Neutral

- `resource` URL format 은 GitHub 만 검증. 다른 forge 의 URL 은 그대로 `last_ingested_from` 보존.
- `blob/main/` 하드코딩. commit-pinned / branch-pinned URL 은 별도 ADR.
- `.gitignore` 의 `/docs/` 패턴과 무관 (wiki frontmatter 의 in-repo path 는 source of truth, gitignore 무관).

## Compliance

- [SCHEMA.md](../SCHEMA.md) §5.1 R1~R9: 모두 unchanged. R-9 의 `last_ingested_from` 의미 보존 + OKF `resource` 추가.
- [concepts/okf-open-knowledge-format.md](../concepts/okf-open-knowledge-format.md) §12.1 follow-up 2 + ADR-006 §5 Negative 3: **해소**
- [OKF SPEC.md §4.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): `resource` field 채움 (optional → populated)
- [OKF SPEC.md §4.1 Extensions](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md): `last_ingested_from` extra key 보존 (unknown key tolerate)
- ADR-001 (3-layer): `resource` URL 은 *knowledge* layer 의 artifact. Source layer (코드) 의 in-repo path 와 1:1 매핑 — single source of truth 유지.

## Implementation

| Item | Status | Location |
|---|---|---|
| `workflow_kit/path_resolver.py` (신규, ~80 lines) | ⏳ proposed | `workflow-source/workflow_kit/path_resolver.py` |
| `workflow_kit/okf_export.py` enhancement (`_derive_resource` 에 resolve 통합) | ⏳ proposed | `workflow-source/workflow_kit/okf_export.py` |
| `--no-resolve` CLI flag | ⏳ proposed | `workflow_kit.okf_export` argparse |
| `tests/check_path_resolver.py` (5+ tests: git remote normalize, fallback chain, security path traversal, SSH→HTTPS, branch detect) | ⏳ proposed | `workflow-source/tests/check_path_resolver.py` |
| `check_okf_export.py` 확장: in-repo path → `resource` URL 자동 채움 test | ⏳ proposed | `workflow-source/tests/check_okf_export.py` |
| `last_ingested_from` path → URL round-trip 검증 | ⏳ proposed | `tests/check_okf_export.py` 추가 |
| `_derive_resource` 단위 test (URL / in-repo / path traversal / fallback) | ⏳ proposed | `tests/check_okf_export.py` 추가 |

## Follow-up Candidates (별도 ADR/turn)

1. **ADR-010** (선택): commit-pinned URL (`blob/<sha>/<path>`) — provenance 강화. `vcs_commit` extra frontmatter key 추가.
2. **ADR-011** (선택): GitLab / Bitbucket / self-hosted Git forge 의 URL heuristic. 우리 repo 가 GitHub 라 deferred.
3. **V-R10 lint** (별도 ADR): URL validity check. OKF `resource` URL + 우리 wiki 의 cross-link URL 양쪽 검증. runtime HEAD 요청.
4. **`workflow_kit/path_resolver.py` 고도화**: symlink resolve, submodule path, monorepo path (`workflow-source/` prefix 자동화) — 별도 ADR.
5. **v0.7.33 PATCH release note** (본 ADR 채택 시): ADR-006 + 007 + 008 등재 + PoC 검증 결과.
6. **OKF bundle sample 재-export**: ADR-008 채택 후 5 page PoC re-export → 모든 page 의 `resource` 가 GitHub URL 로 채워진 sample commit.
7. **CI integration**: GitHub Actions workflow 에 `python -m workflow_kit.okf_export --wiki <path> --out <artifact>` step 추가, artifact upload → release page 에 attach. ADR-008 의 `GITHUB_SERVER_URL` + `GITHUB_REPOSITORY` env var 활용.

## Related

- [[concepts/okf-open-knowledge-format]] — ADR 의 1차 source. §12.1 follow-up 2.
- [[decisions/adr-006-okf-compat-frontmatter]] — export 1-way 짝. 본 ADR 은 `_derive_resource` 의 in-repo branch 추가.
- [[decisions/adr-007-okf-consumer-mode]] — import 1-way 짝. `resource` URL 채워진 bundle import 시 *extra* `resource` key 보존 경로 명확.
- [[concepts/wiki-source-rule-r9]] — R9 의 `last_ingested_from` (in-repo path) 가 ADR-008 의 resolve input. R9 unchanged.
- [[patterns/wiki-stub-emit]] — wiki stub 생성 시 `last_ingested_from` 자동 populate 패턴. ADR-008 의 resolve 와 결합 시 wiki stub → OKF bundle 의 `resource` 가 즉시 채워짐.
- [OKF SPEC.md v0.1 §4.1 Frontmatter](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) — `resource` field 의 primary definition.

## Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. `concepts/okf-open-knowledge-format.md` §12.1 follow-up 2 + ADR-006 §5 Negative 3 기반 | Sisyphus (orchestrator) |
