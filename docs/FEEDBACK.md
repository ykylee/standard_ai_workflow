# Feedback & Support (v0.7.56+)

외부 consumer 의 feedback 은 `standard-ai-workflow` 의 1차 입력입니다. 본 페이지는 feedback channel 과 우선순위, 그리고 response SLA 를 안내합니다.

## Feedback channel

### 🐛 Bug report

**언제 쓰나**: OKF bundle round-trip fail, CLI crash, lint false positive/negative, doc 오타/링크 깨짐.

**링크**: [GitHub Issues (bug)](https://github.com/ykylee/standard_ai_workflow/issues/new?labels=bug,consumer-feedback&template=bug_report.md)

**포함 권장**:
- 재현 command / code snippet
- 기대 결과 vs 실제 결과
- `python3 --version` + `pip show standard-ai-workflow` (버전)
- 가능하면 `python3 -m workflow_kit.url_validity --help` 처럼 self-diagnostic output

### 💡 Feature request / suggestion

**언제 쓰나**: 새 dispatcher subcommand, 새 lint rule, 새 bundle format 지원, doc 개선.

**링크**: [GitHub Issues (enhancement)](https://github.com/ykylee/standard_ai_workflow/issues/new?labels=enhancement,consumer-feedback&template=feature_request.md)

**포함 권장**:
- use case / motivation
- 제안하는 API / output shape (있으면)
- alternative / trade-off (있으면)

### 💬 General Q&A / how-to

**언제 쓰나**: "이렇게 하려면 어떻게?" / "이 lint rule 의 의미는?" / "내 bundle 이 strict mode 에서 fail 하는 이유?"

**링크**: [GitHub Discussions](https://github.com/ykylee/standard_ai_workflow/discussions)

**왜 Discussions?**: Q&A 가 issue tracker 의 signal-to-noise 를 떨어뜨림. Discussions 는 threaded + searchable.

### 📖 문서 unclear / missing

먼저 다음을 확인:

- [OKF Consumer Quickstart](OKF_CONSUMER_QUICKSTART.md) — 5분 튜토리얼
- [OKF Consumer Guide](OKF_CONSUMER_GUIDE.md) — full reference
- [Code Index](CODE_INDEX.md) — module map
- [samples/](samples/) — example bundles
- [architecture/](architecture/) — design / ADR

이후에도 unclear 하다면 issue 로 보고. **doc PR 환영** — `docs/` 만 edit 하면 mkdocs 가 자동 rebuild (CI ~2분).

## 우선순위 / SLA

| Label | 우선순위 | 1차 response | Resolution target |
|---|---|---|---|
| `bug,critical` (data loss / security) | P0 | 24h | 7d |
| `bug,consumer-feedback` (그 외) | P1 | 7d | 다음 minor release |
| `enhancement,consumer-feedback` | P2 | 14d | backlog — 수요 보고 우선순위 재평가 |
| `question` (Discussion) | P2 | 7d | best-effort |
| `docs,typo` (PR 환영) | P3 | 14d 또는 PR merge | 30d |

**P0 / P1 critical bug** 은 GitHub Issue 의 "Critical" template 사용. Security 이슈는 [private disclosure](https://github.com/ykylee/standard_ai_workflow/security/advisories/new) 권장 (public issue 는 exploit detail 노출 위험).

## Telemetry / privacy

본 사이트 (`ykylee.github.io/standard_ai_workflow/`) 는 **외부 analytics / tracking 스크립트 0개** (privacy-first):

- Google Analytics / Plausible / Fathom **없음**
- Cookie banner **없음** (필요 없음)
- Page view 는 GitHub Pages 의 [traffic tab](https://github.com/ykylee/standard_ai_workflow/graphs/traffic) 으로만 확인 (own 데이터)
- external CDN / font 0개 (mkdocs-material 만 사용, self-hosted)

v0.7.56+ 부터 GitHub Pages native traffic tab 으로 page view 확인 가능. referrer / search term 등 *자세한* 데이터는 GitHub 에서 직접 export 가능 ([insights API](https://docs.github.com/en/rest/metrics/traffic)).

## 1차 출처 / SSOT

- 이 페이지 = `docs/FEEDBACK.md` (in-repo). mkdocs 자동 빌드.
- 1차 출처 (project 의 운영 SSOT) = `ai-workflow/wiki/decisions/` (internal, non-public)
- v0.7.56+ feedback loop 운영 결과는 `ai-workflow/memory/log.md` 에 append.

## Cross-references

- Source repo: <https://github.com/ykylee/standard_ai_workflow>
- OKF spec: <https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md>
- mkdocs workflow: `.github/workflows/mkdocs.yml` (auto-rebuild on `main` push)
- Project profile: [PROJECT_PROFILE.md](PROJECT_PROFILE.md)
- Release notes: [RELEASE.md](RELEASE.md)
