# standard-ai-workflow

> OKF (Open Knowledge Format) v0.1 consumer guide + workflow_kit reference.
> 본 사이트는 `ykylee/standard_ai_workflow` 의 **public-facing** 문서.
> 운영 / internal 운영 문서는 [`ai-workflow/wiki/`](https://github.com/ykylee/standard_ai_workflow/tree/main/ai-workflow/wiki) 참조.

## What's here

1. **[Consumer Quickstart (5 min)](OKF_CONSUMER_QUICKSTART.md)** — first-time setup, copy-paste commands
2. **[Consumer Guide (full)](OKF_CONSUMER_GUIDE.md)** — write, validate, ingest an OKF bundle
3. **[Project Profile](PROJECT_PROFILE.md)** — what this project is and isn't
4. **[Code Index](CODE_INDEX.md)** — module-by-module map
5. **[Document Index](DOCUMENT_INDEX.md)** — all docs
6. **[Installation & Usage](INSTALLATION_AND_USAGE.md)** — install / update / uninstall
7. **[Release Notes](RELEASE.md)** — version history

## What is OKF?

[Open Knowledge Format (OKF) v0.1](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md) is a bundle distribution format for knowledge graphs, ADR-aligned, and tool-agnostic. `standard-ai-workflow` implements OKF export/import in 4 core modules (`okf_export`, `okf_import`, `path_resolver`, `url_validity`).

## Who is this for?

- **External consumers** who want to ingest an OKF bundle published by a `standard-ai-workflow` user.
- **Tool authors** who want to write their own OKF bundle and have it round-trip with our wiki.
- **Reviewers** who want a stable, versioned URL for documentation (this site).

## Source of truth

This site is **auto-generated** from the `main` branch via [mkdocs-material](https://squidfunk.github.io/mkdocs-material/). To edit, modify files in `docs/` and push to `main`. CI is in `.github/workflows/mkdocs.yml`.

## Cross-references

- Source repo: <https://github.com/ykylee/standard_ai_workflow>
- Internal wiki (in-repo): `ai-workflow/wiki/index.md`
- OKF spec: <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>
- Latest release: see [Release Notes](RELEASE.md)
