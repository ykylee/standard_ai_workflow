# standard-ai-workflow

- 문서 목적: `standard-ai-workflow` 의 public-facing 문서 사이트 랜딩 페이지. OKF consumer 가이드와 workflow_kit reference 로 가는 진입점.
- 범위: 사이트 구성 안내, 주요 문서 링크. 운영/internal 문서는 범위 밖(`ai-workflow/wiki/`).
- 대상 독자: 외부 consumer, OKF bundle 작성자, workflow_kit 사용자
- 상태: stable
- 최종 수정일: 2026-06-17
- 관련 문서: [OKF Consumer Guide](./OKF_CONSUMER_GUIDE.md), [OKF Consumer Quick-Start](./OKF_CONSUMER_QUICKSTART.md), [Feedback & Support](./FEEDBACK.md)

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

## Feedback (v0.7.56+)

외부 consumer 의 feedback 은 *project 의 1차 입력*. 본 사이트 사용 중 issue / suggestion / contribution 이 있으시면:

- 🐛 **Bug report** → [GitHub Issues](https://github.com/ykylee/standard_ai_workflow/issues/new?labels=bug,consumer-feedback&template=bug_report.md)
- 💡 **Feature request / suggestion** → [GitHub Issues (enhancement)](https://github.com/ykylee/standard_ai_workflow/issues/new?labels=enhancement,consumer-feedback&template=feature_request.md)
- 💬 **General Q&A** → [GitHub Discussions](https://github.com/ykylee/standard_ai_workflow/discussions)
- 📖 **문서 unclear / missing** → [docs/samples](https://github.com/ykylee/standard_ai_workflow/tree/main/docs/samples/) 또는 [docs/architecture](https://github.com/ykylee/standard_ai_workflow/tree/main/docs/architecture/) 먼저 확인 후 issue
- 📊 **Public-facing telemetry** → 본 사이트는 외부 analytics / tracking 스크립트 0개 (privacy-first). v0.7.56+ 부터는 GitHub Pages 의 [traffic tab](https://github.com/ykylee/standard_ai_workflow/graphs/traffic) 으로 page view 확인 가능.

**Response SLA**: consumer-feedback label issue 는 7일 내 1차 response (acknowledge / triage). critical bug 은 48h. PR review 는 3-5 영업일.
