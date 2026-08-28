---
id: M-007
title: 운영 축 (상설)
sdlc_phase: stabilization
status: in_progress
order: 7
parallel_allowed: []
deliverables: []
---

# M-007 — 운영 축 (상설)

**상설 마일스톤이다 — done 을 목표로 하지 않는다** (소유자 결정 2026-08-28,
스펙 §11 의 "exempt 비율이 높게 유지되면 운영 축 마일스톤을 상설로 둘지
묻는다" 트리거 성립: 첫 실측 1/15=7% → M-006 close 이후 등록 task 전건이
exempt). 반복되는 운영 작업 — 결함 수리·관찰·릴리스 사이클 — 을 exempt
선언 대신 정상 WBS 경로로 흡수한다.

- `deliverables` 는 비워 둔다: 완료 판정이 없는 마일스톤이므로 done 경계
  산출물 검증 대상이 아니다.
- 이후 **새 기능 축 마일스톤(M-008+)은 자기 파일의 `parallel_allowed` 에
  `M-007` 을 선언**하고 연다 — 선언은 대칭이라 어느 쪽에 적어도 유효하지만,
  이 파일을 매번 고치지 않도록 새로 여는 쪽이 적는 것을 기본으로 한다.
- leaf 는 개별 결함이 아니라 **반복 범주**다. task 는 해당 범주 leaf 에
  연결하고, 범주에 안 들어가는 일이 반복되면 leaf 를 늘리는 대신 먼저
  범주 정의를 재검토한다.

## WBS

- **WBS-7.1** 결함 수리 — 플랫폼·크로스호스트 (Windows 경로·해석기, federation 형식)
- **WBS-7.2** 결함 수리 — 탐침·도구 ('잰 단위' 결함족, doctor/release 탐침, kit 자체 결함)
- **WBS-7.3** 관찰·지표 운영 (mypy flake, exempt 비율, memory_index 3-tuple, 로드맵 정비)
- **WBS-7.4** 릴리스·채널 운영 (발행 사이클, 소비 채널 재적용, 브랜치 메모리 정비)
