# Beta v0.10.4 — CodeWhale 10번째 하네스 overlay (2026-07-03)

> **SemVer minor** (v0.10.3 → v0.10.4) — Phase 12 의 *delivery layer 확장* release 의 후속. **CodeWhale harness 1종 추가** (단일 `SKILL.md` overlay 패턴). PyPI 배포: no (GitHub Releases only).

## 1. CodeWhale harness 추가 (10번째 supported harness)

v0.10.2 의 3종 (aider / goose / custom) 까지 9종이었고, 본 release 로 **CodeWhale** 이 10번째 supported harness 로 추가됐다.

### 1.1 적용 방식 (단일 SKILL.md overlay)

CodeWhale 은 다른 9종과 달리 **단일 `SKILL.md` overlay** 만 사용한다.

- **위치**: `workflow-source/harnesses/codewhale/SKILL.md` (1 file)
- **다른 harness 와의 차이**: `apply_guide.md` + `README.md` + `AGENTS.md` 다중 file 대신 **단일 `SKILL.md`** 만 emit
- **역할 분담**: Constitution 이 verification / parallelism / context 관리, harness 는 session start + Korean output + backlog management 의 additive rule 만 담당

### 1.2 HARNESS_SPECS 등록

`workflow-source/scripts/bootstrap_lib/harnesses/__init__.py` 의 `HARNESS_SPECS` 에 1줄 추가 + `register_harness_builder` 한 줄 등록.

```python
HARNESS_SPECS["codewhale"] = {
    "display_name": "CodeWhale",
    "entry_files": ("SKILL.md",),
    "read_files": ("README.md", "AGENTS.md"),  # 옵션
    "overlay_spec": None,  # 단일 overlay
    "added_in_release": "v0.10.4 (2026-07-03)",
    "codewhale_note": "단일 SKILL.md overlay, additive rules only",
}
```

## 2. 검증

- bootstrap smoke + harness SSOT alignment test 통과
- drift-prevention 의 `case_5_harness_supported_ssot_alignment` 정합 유지

## 3. 다음 단계

- 10 harness 모두 1 cycle 검증 (apply_guide + README + entry file 정합)
- CodeWhale 실 consumer 검증 (외부 pilot)
