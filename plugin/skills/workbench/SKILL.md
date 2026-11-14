---
name: workbench
description: |
  [KO] 표준 AI 워크플로우 워크벤치 — 계획 · 진척을 브라우저로 보고 결정에 답하는 서버를 소유자가 띄우는 법(토큰 · 시작 · URL)을 안내한다.
  [EN] Standard AI workflow workbench — guide the owner to start the browser server for reading task plans and progress and answering open decisions (token, start, URL). Use when the owner wants to review or answer a plan outside the terminal.
---

# workbench

## Role

Let the owner read task plans and progress in a browser and answer open decisions there
(ADR-032). The server only ever writes answers into the branch memory inbox; the work session
applies them with `plan-import`. **Do not start, stop or drive the server yourself** — give
the owner the commands and the URL. No model is called by the server.

## Procedure

1. The owner makes a token file once per person (`0600`, the value is never printed):

   ```bash
   python -m workflow_kit workbench --new-token approver:<name> --out "$HOME/.config/workbench/<name>.token"
   ```

   The parent directory is created (`0700`) if missing; an existing file is never overwritten. Use `viewer:<name>` for someone who only reads. Names are `[A-Za-z0-9_-]{1,32}` and become
   the `responder` of an answer.
2. The owner starts the server in their own terminal (it prints the URL and keeps running):

   ```bash
   python -m workflow_kit workbench --token "approver:<name>=file:$HOME/.config/workbench/<name>.token"
   ```

   It binds `127.0.0.1:8766` by default. Behind a tunnel or reverse proxy, pass the address
   the browser uses: `--public-url https://host/prefix/` (plus `--trusted-proxy <addr>`).
   A non-loopback `--bind` needs TLS (`--tls-cert`/`--tls-key`) or `--allow-plain-http`.
3. Tell the owner the URL to open — `python -m workflow_kit workbench --status` prints it while the server runs, and
   `session-start` reports it too.
4. When answers arrive, `session-start` and `backlog-update` report pending plan responses.
   Apply them with `plan-import`; a task with pending responses cannot move to `done`.

## Usage

```bash
python -m workflow_kit workbench --help
python -m workflow_kit workbench --status
```

One server per checkout. Its run record lives in `.workbench/server.json` at the checkout
root, which ignores itself in git; sessions live only in memory, so a restart means logging in
again.

## Memory Update Paths

<!-- generated-from: core/global_workflow_standard.md §1 · §3 · §8 · §11 — do not edit this block directly; edit the standard document and regenerate. -->

- Restore session-start baseline: `python -m workflow_kit session-start`
- Register / update a task: `python -m workflow_kit backlog-update`
- Sync affected documents (advisory): `python -m workflow_kit doc-sync`
- Regenerate state.json at session close: `python -m workflow_kit refresh-state`
- Roll off handoff §1 baselines over cap: `python -m workflow_kit rollover-baselines`
- Roll off handoff §5 notes over budget: `python -m workflow_kit rollover-handoff-notes`
- Propose memory_index entries at close (advisory): `python -m workflow_kit suggest-memory-entries`
- Relay working state across compaction: `python -m workflow_kit compact-checkpoint`
- Apply plan responses: `python -m workflow_kit plan-import`
- Review plans and progress in a browser: `python -m workflow_kit workbench`

- Run them with the Python that has `workflow_kit` installed (`python` on Windows, usually `python3` elsewhere) — not a `wk` executable, which Windows antivirus blocks.
- Empty handoff `in_progress` / `blocked` lists hold an **empty bullet `-`** — prose there is parsed as a work item.
- Handoff recently-completed entries start with `TASK-`, at most 10.
- `state.json` is a **generated artifact** — never hand-edit it; regenerate with `refresh-state` (sources: `backlog/tasks/` + `session_handoff.md`).
- Over the handoff §1 baseline cap, **move** lines with `rollover-baselines` — never delete them.
- Over the handoff §5 notes budget, **move** the oldest with `rollover-handoff-notes` (rules → `lessons.md`, notes → `sessions/`).
- Write the handoff and backlog only in their format — they feed the state.json generator.
