# Privacy Guard

**COS30018 Intelligent Systems · Semester 2 2026 · Option A · Group 10**

Three autonomous agents on different model tiers, cooperating to prepare related documents for release to an external AI service — and disagreeing about how far to go.

---

## The problem

Two documents about the same person are sent to an external AI service. Neither identifies them alone — one keeps the employer, the other keeps the role and the suburb. Together they may.

Privacy Guard takes both documents plus a stated downstream purpose and removes or generalises the identifying information. An **Attacker** then tries to re-identify the person from the release, while a **Reviewer** independently reports which required facts the transformation destroyed. When the two disagree, a deterministic rule adjudicates and the Defender revises once.

**The hypothesis under test.** Whether an adaptive Defender–Attacker–Reviewer design handles cross-document disclosure risk more effectively than a deterministic workflow and a single autonomous agent, and whether any improvement justifies its additional cost. That is a question for the evaluation to answer, not an assumption of the design.

---

## Architecture

```
Gradio UI ──► Controller (plain Python, no model calls)
                  │
                  ├──► Defender agent  [strong tier]
                  │      scan_identifiers · inspect_context
                  │      get_policy · propose_edit · render_preview
                  │                    │
                  │                    ▼
                  ├──► Edit engine (deterministic) ──► Release + hash + edit audit
                  │                                          │
                  │                    ┌─────────────────────┴────────────────┐
                  │                    ▼                                      ▼
                  ├──► Attacker agent [mid tier]        Reviewer agent [small tier]
                  │      search_profiles · fetch_profile   fetch_previous_release
                  │              │                          get_edit_audit
                  │              ▼                                  │
                  │      SQLite profile store                       │
                  │              │                                  │
                  │         Attack report ──► Adjudication ◄── Damage report
                  │                          (deterministic)
                  │                                │
                  ├──► Final rescan (controller-side, authoritative)
                  └──► QA service (single call, fixed model)
```

Three agents with **different information views**, enforced by distinct Pydantic view types, distinct tool lists and tests — not by prompting:

| | Tools | Can see |
|---|---|---|
| **Defender** | Detection, context evidence, policy, edit proposal, preview — in-process | Originals, pseudonym map, policy, both reports |
| **Attacker** | `search_profiles`, `fetch_profile` — MCP only | The registered release. Nothing else. |
| **Reviewer** | `fetch_previous_release`, `get_edit_audit` | Current release, previous release, and an audit of span categories and transformation levels. No source text, no answer keys. |

The Defender cannot invoke the Attacker. The outer workflow is bounded and deterministic — that is the coordination mechanism. The **autonomy sits inside each agent activation**, where the next tool depends on what the last one returned.

### Why the Reviewer matters

The Attacker argues for more masking; the Reviewer argues that a needed fact has been destroyed. The controller resolves it in code: mandatory privacy always wins, a fact-critical span gets a lower generalisation level rather than suppression, and if nothing satisfies both positions the case terminates `needs_review` with both recorded.

Terminating on an unresolved conflict is a **correct outcome**, not a failure. A system that always resolves is hiding the trade-off rather than surfacing it.

### Why three model tiers

Each agent runs on a model matched to the difficulty of its job — the Defender's combination reasoning is far harder than the Reviewer's bounded diagnostic. The brief requires reporting model names and versions, and the Week 4 lab configures separate manager and worker models, so per-role configuration is both permitted and taught.

**The single-agent baseline runs on the strongest tier**, the same model as the Defender. It performs all three jobs, so it gets the best model in the system — if the three-agent design wins, it cannot be because it had better models anywhere.

---

## Status

Specification complete. Implementation begins after the scope discussion with the tutor.

| | |
|---|---|
| Specification | Complete — [`docs/PrivacyGuard_Project_Specification.md`](docs/PrivacyGuard_Project_Specification.md) |
| Sprint plan | Complete — [`docs/PrivacyGuard_Sprint_Plan.md`](docs/PrivacyGuard_Sprint_Plan.md) |
| Sprint 1 | Issues created, not started |
| Sprints 2–4 | Planned |

---

## Documents

- **[Project Specification](docs/PrivacyGuard_Project_Specification.md)** — what the system does, how each part is built, contracts, adjudication rule, evaluation design. The reference for every implementation decision.
- **[Sprint Plan](docs/PrivacyGuard_Sprint_Plan.md)** — 58 tasks across four sprints, each with what to build, what the result looks like, and how to prove it is done.

---

## Repository layout

Directories appear as their workstream is built.

```
privacyguard/
  contracts/     Pydantic models, per-agent view types
  controller/    Run loop, budget, adjudication, terminal status, residual risk
  agents/        Defender, Attacker, Reviewer, prompts
  tools/         Detection, context evidence, policy
  engine/        Span registry, edit engine, edit audit, pseudonym map
  registry/      Release registry, MCP service
  ui/            Gradio interface
  eval/          Harness, offline evaluator, scorer, metrics
data/
  cases/         Generated cases (answer keys held separately)
  profiles.db    Fictional profile store
docs/            Specification, sprint plan, model validation
scripts/         Project tooling
tests/           Invariants, boundaries, adjudication, permissions, budgets
traces/
  exported/      Sanitised events — safe to share
  raw/           Local debugging only, gitignored
```

---

## Setup

Requires Python 3.11.

```bash
git clone https://github.com/noJacky/COS30018_Privacy_Guard_Hy-Group-10.git
cd COS30018_Privacy_Guard_Hy-Group-10

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env               # add your API key and the six model ids
pytest
```

`.env` configures a model per role — Defender, Attacker, Reviewer, QA service, offline evaluator, plus the baseline which resolves to the Defender's model. Take current ids from [ai.google.dev/gemini-api/docs/models](https://ai.google.dev/gemini-api/docs/models); never copy the tutorial's.

Once Sprint 1 lands:

```bash
# terminal 1 — MCP service
python -m privacyguard.registry.server

# terminal 2 — one case, or the interface
python -m privacyguard.run --case dev-001
python app.py                      # http://127.0.0.1:7860
```

Evaluation never uses the interface:

```bash
python -m privacyguard.eval.harness --partition validation --conditions 1,2,3a,3b
```

---

## Creating the GitHub issues

The sprint plan is the single source of truth. `scripts/create_issues.py` parses it and creates the labels, milestones and issues, so there is no second copy of the task list to keep in step.

```bash
export GITHUB_TOKEN=...             # PowerShell: $env:GITHUB_TOKEN = "..."

python scripts/create_issues.py --dry-run     # parse and preview, changes nothing
python scripts/create_issues.py --sprint 1    # one sprint at a time
python scripts/create_issues.py               # everything
```

Fill in the GitHub usernames in the `CONTRIBUTORS` map at the top of the script first. Unknown usernames make GitHub reject the request, so a contributor left as `None` produces an unassigned but correctly labelled issue.

The script is **idempotent** — an issue whose title already exists is skipped, so editing the plan and re-running only adds what is new. It **cannot update an existing issue**; if a task's body changes, edit that issue by hand. It runs in two passes, creating the issues and then rewriting bodies so a `Depends on PG-07` becomes a real `#12` link. Standard library only.

**Labels:** `sprint-1`…`sprint-4` · `ws-A`…`ws-H` · `contributor-1`…`contributor-4` · `blocked` · `needs-review`

---

## Working agreements

- One active issue per person. Push progress within 48 hours of starting.
- Blocked? Comment on the issue with the blocker and the next action rather than going quiet.
- `main` stays runnable. Integrate at least twice weekly.
- Contract changes need a comment on the contract issue and its owner's agreement before merging.
- Weekly worklogs in `docs/worklogs/`. The brief states that sprint marks account for worklogs and progress checks, and reconstructing them in November is not possible.
- Stubs are scaffolding. Label them unimplemented; they never satisfy an acceptance check.

**Definition of done** for every issue: acceptance check passes, branch merged to a runnable `main`, work recorded in that week's worklog.

**One hard gate.** PG-53 validates each model **in its actual role** before further agent work proceeds. A model that cannot reliably emit structured tool calls fails that role and is escalated a tier, with the reason recorded in `docs/model_validation.md`. Discovering this on 9 September is a design decision; discovering it in October is a crisis.

---

## Data and privacy

Every document, person, profile and identifier in this repository is **fictional**. Australian identifier *formats* are used with invented values.

- Never commit `.env` or any API key.
- Never place real personal information in this repository, including in test fixtures or screenshots.
- Only sanitised traces go in `traces/exported/`. Raw traces are local, gitignored, and excluded from submission.
- Answer keys live with the evaluation harness and are never reachable from application code.
- The edit audit shown to the Reviewer carries span categories and transformation levels only, never source text.
- The interface warns against uploading real personal documents while a cloud model backend is active.

**On what the system claims.** A `completed` status means the workflow ran, deterministic checks passed, and the Attacker abstained *under the defined threat model*. It does not mean anonymous, or safe against any other attacker or background knowledge. Pseudonymisation is not anonymity, and loop termination is not evidence of anonymity.

---

## Unit information

Assessment 1 (Project) is 50% of COS30018; the Continuous Oral Defence is the other 50%. Four individual sprint reports contribute up to 40 of the project's 100 marks, alongside working software (35), report (20) and video (5). Individual contribution can reduce the team portfolio mark.

Every member should be able to explain the agent loops, the information separation, the adjudication rule, the per-role model rationale and the measured trade-offs — not only the part they implemented.

Submission: 11:59 pm, 3 November 2026.

Generative AI was used for planning and structuring under the unit's Assessment Task 1 allowance. Prompts and outputs are retained for the required appendix.
