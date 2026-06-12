# Smart Update Hotfix Plan (v0.5.10.1)

- 문서 목적: bootstrap_lib / apply_workflow_upgrade 가 다른 환경에서 wheel 설치 후 기존 파일 존재 시 `FileExistsError` 로 fail 하는 문제를 VERSION marker + content hash 기반 smart update 로 해결하는 작업 명세.
- 범위: workflow_kit/upgrade_diff.py 신규, bootstrap_lib/writes.py refactor, apply_workflow_upgrade.py refactor, 신규 test `check_smart_update.py`, 회귀 0.
- 대상 독자: Sisyphus (orchestrator), maintainer, 다른 환경에서 wheel 설치하는 사용자.
- 상태: draft (Momus 1 round 검수 완료, Rev 1 보정)
- 최종 수정일: 2026-06-09
- 관련 문서: `workflow-source/core/upgrade_policy.md` (spec), `.omo/plans/v0.5.11-plus-roadmap.md` (장기 plan), `workflow-source/core/workflow_release_spec.md` (릴리스 절차)

- 작성일: 2026-06-09
- 작성자: Sisyphus (orchestrator)
- 기준선: v0.5.10-beta (HEAD = e927060)
- 사용자 요청: 다른 환경에서 wheel 설치 후 `bootstrap_lib` 실행 시 기존 파일 존재하면 `FileExistsError` 로 진행 불가 → smart update 로 변경
- 사용자 결정 (질의 응답):
  - **범위**: bootstrap + upgrade 둘 다
  - **비교**: VERSION marker 우선 + content 해시 fallback
  - **로깅**: 조용히 + manifest 리포트 (stdout 없음)

---

## 0. 문제

`workflow-source/scripts/bootstrap_lib/writes.py:39-43`:

```python
def write_text(path: Path, content: str, *, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"Destination already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
```

다른 환경에서:
1. `pip install standard-ai-workflow-kit` (v0.5.10 wheel)
2. `python3 -m bootstrap_lib --target-root . --harness ... --no-interactive` 실행
3. 기존 `ai-workflow/` 가 있으면 **즉시 `FileExistsError`** → silent break

**기대 동작**: smart update — 기존 파일이 (a) 같은 버전 같은 내용 → 무시, (b) 더 높은 버전 marker 가 있거나 (c) 내용이 다르면 → 갱신, (d) PRESERVE 경로 (사용자 데이터) → 항상 보존.

**비교 진입점 (이미 존재)**:
- `apply_workflow_upgrade.py:148-158` 는 이미 content hash 비교 + `updated` / `ignored` 분리 로직 보유
- 본 hotfix 는 (a) VERSION marker 우선 정책 + (b) bootstrap 까지 확장

---

## 1. 정책 (Smart Update)

### 1.1 VERSION marker 형식

생성된 모든 bootstrap 파일의 **첫 줄 또는 front matter** 에 marker:
```
<!-- standard-ai-workflow-kit: v0.5.10-beta -->
```

또는 텍스트 파일일 경우:
```
# standard-ai-workflow-kit: v0.5.10-beta
```

- 위치: 파일 첫 줄 또는 front matter 첫 줄 (markdown, yaml, toml 등 구조화된 파일)
- 형식: `<comment_prefix> standard-ai-workflow-kit: <version>`
- comment_prefix 매핑:
  - `.md` → `<!-- -->`
  - `.py`, `.sh`, `.bash`, `.toml` (전용 prefix 없을 때) → `#`
  - `.json` → 적용 안 함 (front matter 불가). 해시 fallback.
  - 그 외 → 첫 줄을 임의 comment 로 시작 (e.g. `// standard-ai-workflow-kit: v0.5.10-beta`)

### 1.2 비교 우선순위 (decide_action)

```
0. (short-circuit) kit_version(target) >= kit_version(source) 이고 두 버전이 같으면:
   - bundle 내 모든 파일 한꺼번에 IGNORED (per-file 비교 skip, I/O 절약)
1. PRESERVE_RELATIVE_PATHS 하위 경로 → PRESERVED (갱신 X, force=True 여도 무조건)
2. 파일이 target 에 없음              → CREATE
3. marker 가 있고 dst marker > src    → IGNORED (이미 더 최신, 사용자 의도)
4. marker 가 있고 dst marker < src    → UPDATED (구버전 → 신버전)
5. marker 가 있고 dst marker == src   → 해시 비교:
   - 해시 같음 → IGNORED
   - 해시 다름 → UPDATED (사용자가 손댄 경우)
6. marker 가 src 에 없음 (legacy 파일):
   - 해시 같음 → IGNORED
   - 해시 다름 → UPDATED
7. force=True (사용자 명시)           → CREATE/UPDATED (위 3~6 무시)
   **단, PRESERVE_RELATIVE_PATHS 는 force=True 여도 항상 PRESERVED**
```

### 1.3 기본 동작

- `bootstrap_lib` default = **smart update** (silent). force 플래그는 그대로 유지 (기존 호환). force=True 여도 PRESERVE 경로는 항상 보존.
- `apply_workflow_upgrade` 도 동일 정책. `--force-cleanup` 동작은 유지 (stale 파일 삭제, 별도 옵션).
- **버전 bump (Rev 2)**: `workflow_kit/__init__.py` 의 `__version__` 을 `v0.5.0-beta` → `v0.5.10.1-beta` 로 갱신. pre-existing drift 해결.

### 1.4 manifest 키

`writes.build_manifest` 결과 + `apply_upgrade` 결과 양쪽:
```json
{
  "file_actions": {
    "created":   ["path1", ...],
    "updated":   ["path2 (v0.5.0 → v0.5.10)", ...],
    "ignored":   ["path3 (unchanged)", ...],
    "preserved": ["path4 (user data)", ...]
  }
}
```

stdout 출력 없음. human-readable 리포트는 별도 `--report path` 옵션 (v0.5.11+ 후속, 본 hotfix 범위 외).

---

## 2. 모듈 구조

### 2.1 신규: `workflow_kit/upgrade_diff.py`

- `parse_version_marker(text: str, file_suffix: str) -> str | None` — 파일 내용에서 marker 추출, 버전 문자열 또는 None
- `format_version_marker(version: str, file_suffix: str) -> str` — marker 문자열 생성
- `content_hash(path_or_text) -> str` — SHA256 16자 (충분히 collision-resistant, 짧은 리포트용)
- `compare_marker(src_version: str, dst_version: str) -> int` — 의미론적 버전 비교 (`v0.5.10-beta` > `v0.5.0-beta` 인지). 단순 tuple 비교 (major, minor, patch, pre)
- `decide_action(src_path, src_version, src_hash, dst_path, dst_version, dst_hash, *, force, preserve_predicate) -> Action` — 7-규칙 적용
- `Action` Enum: `CREATE | UPDATED | IGNORED | PRESERVED`
  - `SKIPPED_FORCE` 없음 — force=True 는 3~6 규칙을 우회하되 `PRESERVED` 는 항상 우선
- `read_kit_version(target_root: Path) -> str | None` — `ai-workflow/VERSION` 파일 읽기 (Rev 2 신규, short-circuit 용)

비교/해시/marker 모두 한 곳에 모음. bootstrap + upgrade 양쪽 import.

### 2.2 변경: `bootstrap_lib/writes.py`

- `write_text(path, content, *, force, src_version, ...)`:
  - `src_version` 인자 추가 (caller 가 `__version__` 전달)
  - `decide_action()` 호출 후 action 별 처리:
    - `CREATE` / `UPDATED` / `SKIPPED_FORCE` → `path.write_text()`
    - `IGNORED` / `PRESERVED` → no-op, manifest 에 기록
- `copy_core_docs()`: 각 파일에 대해 동일 정책. `src_version` 은 kit `__version__` 기본값.
- 새 return: `list[FileActionResult]` — manifest 가 받을 수 있는 dict 리스트
- 하위 호환: `force` 인자 그대로, `src_version` 은 optional (None 이면 marker 비교 skip, 해시 비교만)

### 2.3 변경: `bootstrap_lib/__main__.py`

- `write_text` / `copy_core_docs` 호출 시 `src_version=__version__` 전달
- `build_manifest` 에 `file_actions` 통합 (writes 결과를 받아 manifest 에 합류)
- 또는 `build_manifest` 가 `writes` 결과를 직접 합치는 헬퍼 (e.g. `aggregate_actions(*results)`)

### 2.4 변경: `apply_workflow_upgrade.py`

- 라인 148-158 의 hash 기반 로직을 `decide_action()` 호출로 교체
- `src_version`: source bundle 내 파일의 marker (없으면 `None` — hash fallback)
- `dst_version`: target 파일의 marker
- `force` 인자 추가 (기존 `--force-cleanup` 와 별도, 단순 파일 overwrite 용)
- 결과 dict 의 키: `created` / `updated` / `ignored` / `preserved` / `version-downgrade-skip` (marker 비교에서 dst > src 인 경우)

### 2.5 신규: `workflow-source/core/upgrade_policy.md`

- VERSION marker 형식 명세
- 7-규칙 의사코드
- bootstrap / upgrade 양쪽의 default 정책 + opt-out 방법
- 호환성 / 마이그레이션 (v0.5.10 이전에 설치된 환경)

---

## 3. 구현 단계

1. **spec 확정**: `upgrade_policy.md` 작성 (위 §2.5)
2. **core helpers**: `workflow_kit/upgrade_diff.py` 구현 + 단위 test
3. **bootstrap 통합**: `writes.py` + `__main__.py` + `build_manifest` 갱신
4. **upgrade 통합**: `apply_workflow_upgrade.py` 의 hash 로직을 `decide_action` 으로 교체
5. **회귀 test**:
   - `tests/check_smart_update.py` 신규 (또는 `check_bootstrap.py` 확장)
   - 시나리오 4종:
     - (a) 기존 파일 + src marker > dst → `updated` (manifest + 파일 갱신 확인)
     - (b) 기존 파일 + src marker == dst + 같은 hash → `ignored` (manifest + 파일 그대로 확인)
     - (c) 기존 파일 + marker 없음 + 같은 hash → `ignored` (legacy fallback)
     - (d) 기존 파일 + marker 없음 + 다른 hash → `updated`
   - bootstrap + upgrade 양쪽 동일 시나리오
6. **릴리스 노트**: `workflow-source/releases/Beta-v0.5.10.1.md` 작성

---

## 4. 검증 기준 (Definition of Done)

- [ ] `upgrade_policy.md` spec 작성
- [ ] `workflow_kit/__init__.py` `__version__` 을 `v0.5.10.1-beta` 로 갱신 (Rev 2)
- [ ] `workflow_kit/upgrade_diff.py` 단위 동작 (test 1개) + `read_kit_version` helper
- [ ] `bootstrap_lib` default 가 smart update (기존 `FileExistsError` 발생 안 함, 시나리오 a/b/c/d 모두 통과)
- [ ] `bootstrap_lib --force` 는 기존 동작 유지 (PRESERVE 경로만 보존, 나머지 overwrite)
- [ ] `apply_workflow_upgrade` 의 결과 dict 가 `created/updated/ignored/preserved` 4-key 모두 채워짐
- [ ] `check_smart_update.py` 또는 확장된 `check_bootstrap.py` 의 신규 시나리오 test 5종 통과 (Rev 2: 기존 4 + 시나리오 e = force+PRESERVE 보존)
- [ ] `apply_workflow_upgrade` 에 `--force` 인자 추가 (PRESERVE 경로 보존)
- [ ] 기존 smoke 58개 (v0.5.10 baseline) 회귀 0
- [ ] `Beta-v0.5.10.1.md` 릴리스 노트 작성

---

## 5. 위험 요소

| ID | 항목 | 영향 | 완화책 |
|---|---|---|---|
| R1 | marker 가 있는 파일을 사용자가 손으로 편집한 경우 → "UPDATED" 로 덮어씀 | 중간 | 시나리오 (e): marker 가 같고 hash 가 다르면 `UPDATED` 인데, 이게 사용자 편집 손실. 완화: spec 에 "marker 동일 + hash 다름 = 사용자 편집" 으로 명시하고, **manifest 에 `updated: [<path> (user-modified, will overwrite)]` 로 표기**. 또는 v0.5.11+ 에서 `--preserve-user-edits` 옵션 추가. 본 hotfix 는 UPDATED 유지. |
| R2 | version 비교 시 semver 가 아닌 `v0.5.0-beta` vs `v0.5.10-beta` 가 lexical 비교로 잘못 정렬됨 | 낮음 | `compare_marker` 가 `(major, minor, patch, pre)` tuple 비교. 사전식 X. 테스트로 검증. |
| R3 | `apply_workflow_upgrade` 의 `force_cleanup` 동작과 conflict | 낮음 | smart update 는 파일 단위 결정. `force_cleanup` 는 source 에 없는 target 파일 삭제. 책임 분리. **단 force=True 가 PRESERVE 경로도 덮어쓸 위험 → Rule 7 명시 수정 + 회귀 test 시나리오 e 추가 (Rev 2)**. |
| R4 | `.json` / `.toml` 등 marker 형식이 다른 파일의 marker 추출 실패 | 낮음 | fallback: marker 없음 → hash 비교. 실패는 의도된 동작. |
| R5 | marker 가 잘못된 형식으로 들어간 경우 (사용자가 임의로 추가) | 낮음 | regex strict: `^.{0,8}standard-ai-workflow-kit: v\d+\.\d+\.\d+(-[\w.]+)?\s*$`. 비매칭은 marker 없음 처리. |

---

## 6. 범위 외 (별도 plan)

- `--report <path>` 옵션 (human-readable 갱신 리포트) — v0.5.11+
- `--preserve-user-edits` 옵션 (marker 동일 + hash 다름 시 skip) — v0.5.11+
- interactive confirm ("10개 파일이 갱신됩니다. 계속? [y/N]") — v0.5.11+
- marker 없는 legacy 파일 일괄 marker 부착 (force-revision) — v0.5.11+

---

## 다음 단계

1. Momus 1-round 검수
2. PASS 시 §3 구현 단계 진행
3. v0.5.10.1 hotfix 릴리스
