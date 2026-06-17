# OKF Consumer Guide — write, validate, ingest an Open Knowledge Format bundle

> **Status**: stable (v0.7.38)
> 본 문서는 `standard_ai_workflow` 외부에서 OKF v0.1 bundle 을 작성, 검증, ingest 하는 consumer 가이드. 우리 저장소 의 4 module (`okf_export`, `okf_import`, `path_resolver`, `url_validity`) 의 CLI / Python API 사용법 + 1차 출처 (1) ADR-006/007/008/018 (2) OKF spec v0.1 draft (3) wiki V-1/V-4/V-T1/V-R10/V-R11/V-R12/V-R13 rule.

## §0 Quick start (TL;DR)

```bash
# 1. install workflow_kit (editable)
pip install -e /path/to/standard_ai_workflow/workflow-source

# 2. ingest OKF bundle (consumer-side) into our wiki
python -m workflow_kit.okf_import ./external-okf-bundle/ --mode=loose
# → 로컬 staging dir 에 page-level write + strict + loose lint

# 3. validate our wiki's OKF output
python -m workflow_kit.okf_export ./out-bundle/ \
  --vcs-ref v0.7.38 --vcs-commit $(git rev-parse HEAD)
# → wiki → OKF bundle export with pinned URLs

# 4. URL semantic check (V-R13 opt-in)
python -m workflow_kit.url_validity <url>... --semantic --expected-commit-sha abc1234
```

## §1 What is OKF?

Open Knowledge Format (OKF) v0.1 은 `GoogleCloudPlatform/knowledge-catalog` 의 `okf/SPEC.md` (2026-06-12 draft) 의 *bundle distribution format*. 우리 의 1차 출처:

- **Primary source**: [knowledge-catalog/okf/SPEC.md](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) (457 lines, v0.1 Draft)
- **우리 의 wrapper**: `workflow-source/workflow_kit/okf_export.py` (wiki → OKF) + `okf_import.py` (OKF → wiki)
- **Wiki rule**: [concepts/okf-open-knowledge-format.md](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/wiki/concepts/okf-open-knowledge-format.md)
- **ADR**: ADR-006 (frontmatter compat) + ADR-007 (consumer mode) + ADR-008 (in-repo path) + ADR-018 (commit-pinned URL)

## §2 Bundle directory layout (OKF spec §3)

```text
<bundle-name>/
├── okf-bundle.yaml          # v0.7.38+ per-bundle manifest (vcs_commit + integrity_hash)
├── index.md                 # bundle-level entry, lists all pages
├── README.md                # human-readable bundle description
├── concepts/                # category dirs (free-form: concepts/, decisions/, entities/, patterns/)
│   └── <page-name>.md
├── decisions/
│   └── <adr-name>.md
├── entities/
└── patterns/
```

| Path | Required? | Purpose |
|---|---|---|
| `okf-bundle.yaml` | optional (v0.7.38+ emit, recommended) | per-bundle manifest: `vcs_commit`, `integrity_hash`, `okf_version`, `generated_at`, `generator` |
| `index.md` | required (per OKF spec) | bundle entry point; lists every page |
| `README.md` | optional | human-readable description |
| `<category>/*.md` | required (≥1 page) | one Markdown file per page |

## §3 Page frontmatter (OKF spec §4.1)

Each page (`<category>/*.md`) 는 YAML frontmatter 로 시작:

```yaml
---
okf_version: "0.1"
type: concept | decision | entity | pattern | query
title: "Human-readable title"
description: "One-line summary"
resource: "https://github.com/<org>/<repo>/blob/<sha>/<path>"  # optional
tags: ["tag1", "tag2"]                                          # optional
created: "2026-06-16"                                            # optional
updated: "2026-06-16"                                            # optional
vcs_commit: "abc1234..."                                         # v0.7.38+ per-page
vcs_ref: "v0.7.38"                                               # v0.7.38+ per-page
---
```

`type` field 는 5-value enum (per our SCHEMA.md R-2):

| type | Meaning | Example |
|---|---|---|
| `concept` | rule/principle/heuristic | `v-r10-url-validity-lint.md` |
| `decision` | formal ADR | `adr-006-okf-compat-frontmatter.md` |
| `entity` | concrete component/system | `workflow-kit.md` |
| `pattern` | reusable design/template | `wiki-stub-emit.md` |
| `query` | question for downstream agents | (rare, v0.7.39+ planned) |

## §4 Writing an OKF bundle (external consumer use case)

### 4.1 Minimal example

```bash
mkdir -p my-bundle/concepts
cat > my-bundle/index.md <<EOF
---
okf_version: "0.1"
generated_at: "$(date -Iseconds)"
---

# My Bundle

- [Hello concept](concepts/hello.md)
EOF

cat > my-bundle/concepts/hello.md <<'EOF'
---
okf_version: "0.1"
type: concept
title: "Hello concept"
description: "First page"
---

# Hello

Body text here.
EOF
```

### 4.2 Validate before sharing

```bash
# option A: lint via our url_validity tool
python -m workflow_kit.url_validity $(grep -rhoE 'https?://[^ )]+' my-bundle/ | sort -u)

# option B: import dry-run
python -m workflow_kit.okf_import my-bundle/ --mode=strict --dry-run
```

### 4.3 Sign with V-R13 integrity hash (v0.7.38+)

```python
import hashlib, pathlib
bundle = pathlib.Path("my-bundle")
# SHA256 of all page bytes (deterministic order)
sha = hashlib.sha256()
for p in sorted(bundle.rglob("*.md")):
    sha.update(p.read_bytes())
integrity = f"sha256:{sha.hexdigest()}"
# write okf-bundle.yaml
(bundle / "okf-bundle.yaml").write_text(
    f"okf_version: '0.1'\nintegrity_hash: '{integrity}'\n"
)
```

## §5 Consuming an OKF bundle (ingest into our wiki)

### 5.1 Mode detection (ADR-007)

`okf_import` 의 mode resolution priority: **CLI > manifest > index.md > default (strict)**

| Source | Field | Example |
|---|---|---|
| CLI flag | `--mode={strict,loose}` | `python -m workflow_kit.okf_import ... --mode=loose` |
| `okf-bundle.yaml` | `mode: loose` | per-bundle override |
| `index.md` frontmatter | `mode: loose` | per-bundle default |
| Fallback | strict | (default, *operational rigor*) |

| Mode | Unknown keys | Broken wiki links | Behavior |
|---|---|---|---|
| **strict** (default) | error | error | abort ingest; log error per page |
| **loose** | warn | warn | ingest with WARN log; downstream V-T1 / V-R10 lint flags |

### 5.2 CLI usage

```bash
# strict ingest (default)
python -m workflow_kit.okf_import ./external-okf-bundle/

# loose ingest (tolerant)
python -m workflow_kit.okf_import ./external-okf-bundle/ --mode=loose

# staging-only (no promote)
python -m workflow_kit.okf_import ./external-okf-bundle/ --staging-only

# dry-run
python -m workflow_kit.okf_import ./external-okf-bundle/ --dry-run
```

### 5.3 Python API

```python
from workflow_kit.okf_import import ingest_bundle, Mode
result = ingest_bundle(
    bundle_dir=Path("./external-okf-bundle"),
    mode=Mode.LOOSE,
    staging_dir=Path("./staging"),
)
print(f"ingested {result.pages_imported} pages, {result.warnings} warnings")
```

### 5.4 Version compatibility (ADR-011)

`okf_version` 의 major = **reject** (error), minor = **warn**:

| okf_version (page) | okf_version (tool) | Behavior |
|---|---|---|
| 0.1 | 0.1 | pass |
| 0.1.5 | 0.1 | pass (minor higher = warn) |
| 0.2 | 0.1 | reject (major mismatch, strict) / warn (loose) |
| missing | 0.1 | warn (best effort) |

## §6 V-R10 URL validity (offline + online + body)

`url_validity` tool 의 3 layer:

### 6.1 Offline (default) — 8 check

| # | Check | Rule |
|---|---|---|
| 1 | https only | `scheme == "https"` |
| 2 | no path traversal | no `..` in path |
| 3 | no private IP | no `10.*` / `192.168.*` / `172.16-31.*` / `127.*` |
| 4 | no localhost | no `localhost` / `*.local` |
| 5 | no file:// | `scheme != "file"` |
| 6 | no credentials | no `user:pass@` |
| 7 | GitHub URL form | `github.com/<org>/<repo>/blob/<ref>/<path>` |
| 8 | no fragments-as-path | `#` not in path |

### 6.2 Online (--online) — 8 case

`200` = pass, `3xx` = warn, `404/410` = stale, `5xx` = warn, `429` = rate-limited, `timeout/TLS/DNS` = warn.

### 6.3 Body (--body) — 4 check (V-R11 ADR-017)

`Content-Type` (HTML), size (≤ 1MB), 8 phishing keywords, HTML renderable (has `<html>` tag).

## §7 V-R12 commit-pinned URL (ADR-018)

`path_resolver` 의 `resolve_in_repo_path_to_url_pinned(path, commit_sha)`:

- `commit_sha` (7-40 hex): 정밀 (e.g. `abc1234`)
- `ref` (single segment, e.g. `v0.7.38`, `main`): ref-pinned (mutable but human-readable)
- `feature/branch`: `?` (validation reject) — *feature branch* 는 `None` return

CLI 사용:

```bash
# per-bundle
python -m workflow_kit.okf_export ./out/ --vcs-ref v0.7.38 --vcs-commit $(git rev-parse HEAD)

# per-page (wiki frontmatter 우선, kwarg > frontmatter)
# In a wiki page:
# ---
# vcs_commit: "abc1234..."
# vcs_ref: "v0.7.38"
# ---
```

## §8 V-R13 semantic URL verification (ADR-019, v0.7.38+ convention)

8 semantic check + 2 layer (`?hash=sha256:...` + `?range=A..B`).

| Layer | Query param | Purpose |
|---|---|---|
| content hash | `?hash=sha256:<hex>` | byte-level integrity (between-commit content change detect) |
| commit range | `?range=A..B` | content change between A and B (semantic range) |

본 release (v0.7.38) 은 *convention* 채택 — 구현 (`check_url_semantic()`) 은 v0.7.39+ PoC.

## §9 CI integration (.github/workflows/okf-validate.yml)

```yaml
jobs:
  okf-online-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/cache@v4
        with:
          path: ~/.cache/workflow_kit
          key: url-validity-cache-${{ hashFiles('**/*.md') }}
      - run: pip install -e workflow-source
      - run: python -m workflow_kit.okf_export ./out-bundle/ \
              --vcs-ref ${{ github.ref_name }} \
              --vcs-commit ${{ github.sha }}
      - run: python -m workflow_kit.url_validity $(grep -rhoE 'https?://[^ )]+' ./out-bundle/ | sort -u) --online --body
```

## §10 Troubleshooting

| Error | Cause | Fix |
|---|---|---|
| `unknown frontmatter key 'foo'` | strict mode + unknown key | rename to known key OR add to loose manifest |
| `git origin URL not found` | path_resolver no `git config remote.origin.url` | run from repo root with git remote |
| `lock acquisition timeout` | _CacheLock 30s timeout exceeded | check for hung process; orphan lock cleanup (v0.7.38+) |
| `404 stale` | URL no longer exists | refresh with `--online` + `--expected-commit-sha` |
| `major version mismatch` | OKF spec v0.2 vs tool v0.1 | upgrade tool to v0.2+ (or use `--mode=loose` to warn) |

## §11 Compliance

- [SCHEMA.md §5.1 R1-R9](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/wiki/SCHEMA.md): 본 가이드 의 모든 page 는 R-1~R-9 의 standard format 준수.
- ADR-006 (frontmatter): `okf_version` + 5 enum type
- ADR-007 (mode): strict default / loose opt-in
- ADR-008 (in-repo path): `git config remote.origin.url` + `main` fallback
- ADR-011 (version): major reject / minor warn
- ADR-018 (commit-pinned): commit SHA + ref
- ADR-019 (semantic): 8 check + 2 layer convention

## §12 Related

- [concepts/okf-open-knowledge-format.md](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/wiki/concepts/okf-open-knowledge-format.md) — OKF rule definition
- [decisions/adr-006-okf-compat-frontmatter.md](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/wiki/decisions/adr-006-okf-compat-frontmatter.md)
- [decisions/adr-007-okf-consumer-mode.md](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/wiki/decisions/adr-007-okf-consumer-mode.md)
- [decisions/adr-008-in-repo-path-to-url.md](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/wiki/decisions/adr-008-in-repo-path-to-url.md)
- [decisions/adr-011-okf-version-auto-detect.md](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/wiki/decisions/adr-011-okf-version-auto-detect.md)
- [decisions/adr-018-v-r12-commit-pinned-url.md](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/wiki/decisions/adr-018-v-r12-commit-pinned-url.md)
- [decisions/adr-019-v-r13-semantic-url-verification.md](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/wiki/decisions/adr-019-v-r13-semantic-url-verification.md)
- [concepts/v-r10-url-validity-lint.md](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/wiki/concepts/v-r10-url-validity-lint.md)
- [concepts/v-r11-body-audit.md](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/wiki/concepts/v-r11-body-audit.md)
- [concepts/v-r13-semantic-url-verification.md](https://github.com/ykylee/standard_ai_workflow/blob/main/ai-workflow/wiki/concepts/v-r13-semantic-url-verification.md)
- [OKF spec (primary source)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
- [Sample bundle](https://github.com/ykylee/standard_ai_workflow/tree/main/docs/samples/okf-bundle-2026-06-16/) — generated by our `okf_export`

## §13 Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. v0.7.38 release: 외부 OKF consumer 가이드 (write/validate/ingest). 12 section + 1차 출처 (ADR-006/007/008/011/018/019, V-R10/V-R11/V-R12/V-R13). 5 mode matrix + 8 check + 4 body check + 2 V-R13 layer. CI integration + troubleshooting + compliance. TASK-V0738-OKF-CONSUMER-DOCS (Phase 2/6 of v0.7.38 follow-up bundle). | Sisyphus (orchestrator) |
