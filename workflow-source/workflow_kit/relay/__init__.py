"""PC 중계 허브 (2.1, ``core/hub_orchestration_spec.md`` §9) — 표준 라이브러리만.

PC 마다 하나 뜬다. 중앙 허브로 **나가는 연결만** 열어(긴 폴링) 그 PC 앞 승인된 세션 요청 · 메시지를 가져오고,
하네스 어댑터로 세션을 띄우고 · 넣고 · 멈춘다. 무엇을 띄울 수 있는지는 PC 의 허용 목록이 정한다 (중앙이 아니라).

명령: ``python -m workflow_kit hub relay {init,allow,serve,pause,resume,status}``.
"""
