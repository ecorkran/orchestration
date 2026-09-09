---
docType: review
layer: project
reviewType: tasks
slice: tool-use-discipline-and-diagnosability-for-non-sdk-agents
project: squadron
verdict: CONCERNS
sourceDocument: project-documents/user/tasks/267-tasks.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md
aiModel: moonshotai/kimi-k2.7-code
status: complete
dateCreated: 20260908
dateUpdated: 20260908
reviewedSha: 495f0b3e30b73482a4f2903b9ef515590ed7171c
toolsGiven: [read_file, list_files, grep]
toolCallsMade: 2
findings:
  - id: F001
    severity: concern
    category: sequencing
    summary: "T13 commits prompt-affecting Parts A and C before their live verification"
    location: "project-documents/user/tasks/267-tasks.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md"
  - id: F002
    severity: note
    category: sequencing
    summary: "T22 references a degraded artifact produced by the later T26"
    location: "project-documents/user/tasks/267-tasks.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md"
  - id: F003
    severity: note
    category: scoping
    summary: "T27 bundles implementation, wiring, and tests in one conditional task"
    location: "project-documents/user/tasks/267-tasks.tool-use-discipline-and-diagnosability-for-non-sdk-agents.md"
---

# Review: tasks — slice 267

**Verdict:** CONCERNS
**Model:** moonshotai/kimi-k2.7-code

## Findings

### [CONCERN] T13 commits prompt-affecting Parts A and C before their live verification

The Context Summary's Commit checkpoints explicitly state: "prompt-affecting changes (Parts A and C) are confirmed by a live run before their commits are treated as final, so keep them on the slice branch and do not merge until Part E's live steps are recorded. Parts B and D are suite-provable and commit normally." Yet T13 is placed immediately after Part C and instructs: "Commit Parts A-C as separate commits per part, on the slice branch." This would commit Part A before the SC10 A/B live run (T24) and Part C before the SC7b SDK before/after live run (T23), defeating the PM's standing preference. The task should be restructured so Part B commits after T8, Part C commits after T23, and Part A commits after T24.

### [NOTE] T22 references a degraded artifact produced by the later T26

T22 suggests using the review that produced #84 in T26 as a source for a degraded artifact, but T26 occurs later in the task order. The fallback ("If no degraded artifact arises from any Part E run, say so under Observed: and rely on T17") prevents this from being blocking, but the forward reference is confusing. Consider rewording to list all Part E runs as candidate sources without singling out a later task.

### [NOTE] T27 bundles implementation, wiring, and tests in one conditional task

T27 includes registering `agent.max_output_tokens` in `config/keys.py`, reading it in the provider, passing it through the agent, and writing tests across two test files. The rest of the breakdown rigorously splits implementation and tests (e.g., T9/T10, T11/T12, T16/T17). Splitting T27 into an implementation task and a test-with task would be more consistent, even though the task is conditional.
