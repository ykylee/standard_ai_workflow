# OKF Consumer Quick-Start (5 min)

> **Status**: stable (v0.7.44+, ADR-025)
> **Companion to**: [OKF_CONSUMER_GUIDE.md](./OKF_CONSUMER_GUIDE.md) (prose documentation)
> 본 문서는 external consumer 가 *first-time setup* 을 *5 min* 안에 완료할 수 있는 *machine-readable* 의 *copy-paste-able* 정공법.

## §0. TL;DR

```bash
# 1. install
pip install -e /path/to/standard_ai_workflow/workflow-source

# 2. verify
python -c "import workflow_kit; print(workflow_kit.__version__)"
# Expected: v0.7.44-beta

# 3. inspect sample bundle
ls docs/samples/okf-bundle-2026-06-16/

# 4. ingest (strict mode)
python -m workflow_kit.okf_import ./docs/samples/okf-bundle-2026-06-16/

# 5. lint URLs
python -m workflow_kit.url_validity <url>... --semantic
```

## §1. Install workflow_kit (1 min)

```bash
# From local checkout (editable install)
pip install -e /path/to/standard_ai_workflow/workflow-source

# OR from PyPI (v0.7.44+ when released)
pip install standard-ai-workflow
```

**Expected output**:
```
Successfully installed standard-ai-workflow-0.7.44 ...
```

## §2. Verify install (10 sec)

```bash
python -c "import workflow_kit; print(workflow_kit.__version__)"
```

**Expected output**:
```
v0.7.44-beta
```

If you see a different version, you're on an older release — check the release note in `workflow-source/releases/Beta-v0.7.44.md`.

## §3. Inspect sample bundle (30 sec)

```bash
ls docs/samples/okf-bundle-2026-06-16/
```

**Expected output**:
```
README.md
concepts
decisions
index.md
okf-bundle.yaml
```

### Read the manifest

```bash
cat docs/samples/okf-bundle-2026-06-16/okf-bundle.yaml
```

**Expected output** (sample):
```yaml
okf_version: '0.1'
generated_at: '2026-06-16T...'
generator: 'workflow_kit.okf_export v0.7.38-beta'
vcs_commit: 'abc1234...'
integrity_hash: 'sha256:...'
page_count: 5
```

### Read the index

```bash
cat docs/samples/okf-bundle-2026-06-16/index.md
```

**Expected output**: lists all pages by type (concept, decision, etc).

## §4. Ingest (strict mode) (1 min)

```bash
python -m workflow_kit.okf_import ./docs/samples/okf-bundle-2026-06-16/
```

**Expected output**:
```
ImportReport:
  mode: strict
  pages_total: 5
  pages_staged: 5
  pages_with_errors: 0
  pages_with_warnings: 0
  promoted: False
  okf_version: '0.1'
  version_check: VersionCheckResult(major_match=True, minor_match=True, patch_higher=False, action='pass', message='...')
  r2_batch_warning: None  # 5 pages is in the 5-15 range
```

### Optional: ingest in loose mode

```bash
python -m workflow_kit.okf_import ./docs/samples/okf-bundle-2026-06-16/ --mode=loose
```

Loose mode allows unknown frontmatter keys and broken wiki links (with WARN).

## §5. Lint URLs (2 min)

```bash
# Parse-only (fast, default)
python -m workflow_kit.url_validity <url>... --semantic

# Full mode (HEAD + GitHub API, opt-in)
python -m workflow_kit.url_validity <url>... --semantic --perform-head --perform-github
```

**Example**:
```bash
python -m workflow_kit.url_validity \
  "https://github.com/foo/bar/blob/abc1234/docs/spec.md" \
  --semantic
```

**Expected output** (sample):
```
[WARN] V-R13-no-content-hash https://github.com/...: URL query missing ?hash=sha256:... (layer 1)
[WARN] V-R13-stub-content-type ...: V-R11 body audit 위임 (check 3 stub)
[WARN] V-R13-stub-size ...: size_limit check requires --perform-head (check 4 stub)
[WARN] V-R13-stub-author ...: author check requires GitHub API (check 5 stub)
[WARN] V-R13-stub-last-modified ...: last_modified check requires --perform-head (check 6 stub)
[WARN] V-R13-stub-freshness ...: freshness check requires --perform-head (check 7 stub)
```

The 5 stub warnings are expected in fast mode (ADR-020 PoC). Use `--perform-head --perform-github` for full check 3-7.

## §6. Sample bundle walkthrough (5-step table)

| Step | Action | Expected output |
|---|---|---|
| 1 | `cat okf-bundle.yaml` | okf_version, vcs_commit, integrity_hash, page_count |
| 2 | `cat index.md` | bundle entry, lists all pages by type |
| 3 | `ls concepts/` | `<page>.md` files (concept pages) |
| 4 | `python -m workflow_kit.okf_import .` | `ImportReport(pages_total=5, errors=0)` |
| 5 | `python -m workflow_kit.url_validity <url> --semantic` | V-R13 issues (layer 0/1/2 status) |

## §7. Common issues

### Issue 1: ImportError: No module named 'workflow_kit'
**Cause**: install not done, or wrong Python interpreter.
**Fix**: re-run `pip install -e /path/to/standard_ai_workflow/workflow-source`.

### Issue 2: 'okf-bundle.yaml' not found
**Cause**: bundle structure invalid (missing manifest).
**Fix**: ensure bundle contains `okf-bundle.yaml` (or `index.md` as fallback). See [OKF spec §6](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).

### Issue 3: 'major version mismatch' error
**Cause**: OKF spec v0.2+ vs tool v0.1 (or vice versa).
**Fix**: upgrade tool to v0.7.44+ (supports v0.1 + warns on v0.2), or use `--mode=loose` for v0.2 bundles.

### Issue 4: 'r2_batch_warning: too_large'
**Cause**: ingest has > 15 pages.
**Fix**: split into multiple bundles (5-15 page batches recommended). See [SCHEMA.md R-2](../ai-workflow/wiki/SCHEMA.md).

### Issue 5: 'V-R13-stub-content-type' warning
**Cause**: fast mode (default) skips check 3 (content_type).
**Fix**: use `--perform-head` for full check 3 (HEAD + Content-Type).

## §8. Next steps

- **Deep dive**: read [OKF_CONSUMER_GUIDE.md](./OKF_CONSUMER_GUIDE.md) for full reference.
- **V-R13 spec**: read [concepts/v-r13-semantic-url-verification.md](../ai-workflow/wiki/concepts/v-r13-semantic-url-verification.md) for semantic URL convention.
- **V-R12 spec**: read [concepts/v-r13-implementation.md](../ai-workflow/wiki/concepts/v-r13-implementation.md) for layer 1+2 carrier.
- **V-R11 body audit**: see [ADR-017](../ai-workflow/wiki/decisions/adr-017-v-r11-body-audit.md) for phishing detection.
- **OKF spec**: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md (primary source).

## §9. CLI command reference

| Command | Purpose | Use case |
|---|---|---|
| `python -m workflow_kit.okf_import <bundle>` | Ingest OKF bundle into wiki | External consumer integration |
| `python -m workflow_kit.okf_export <wiki> <out>` | Export wiki → OKF bundle | Wiki → external distribution |
| `python -m workflow_kit.url_validity <url>...` | V-R10 URL lint (8 check) | URL form validation |
| `python -m workflow_kit.url_validity <url>... --semantic` | V-R13 semantic URL check | Layer 0/1/2 validation |
| `python -m workflow_kit.url_validity <url>... --online` | V-R10 online HEAD check | Live URL validation |
| `python -m workflow_kit.url_validity <url>... --body` | V-R11 body audit (phishing + size + content-type) | Page content validation |

## §10. Revision Log

| Date | Version | Change | Author |
|---|---|---|---|
| 2026-06-16 | 0.1.0 | 초안. ADR-025 (proposed) 와 동시. 10 section + 5 step walkthrough table + CLI command reference. 5 min 의 *time-to-value* 의 *operational* 정공법. | Sisyphus (orchestrator) |
