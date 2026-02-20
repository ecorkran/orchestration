---
docType: slice-plan
parent: 100-arch.orchestration-v2.md
project: orchestration
dateCreated: 20260217
dateUpdated: 20260219
---

# Slice Plan: Orchestration (Python Reboot)

## Parent Document
`100-arch.orchestration-v2.md` — High-Level Design: Orchestration (Python Reboot)

## Milestone Targets

These milestones define the priority ordering. Slices are sequenced to reach each milestone as early as possible.

**M1 — SDK agent task execution:** Spawn a Claude Agent SDK agent, give it a task, get structured output via CLI. Uses Max subscription — no API cost.

**M2 — Multi-agent communication:** Two agents (SDK and/or API) communicate through the message bus. Proves the unified Agent Protocol works across provider types.

**M3 — Human + agents:** Human participates alongside multiple agents in a shared conversation with configurable topologies.

---

## Foundation Work

1. [x] **Project Setup & Core Models** — `uv init`, pyproject.toml with dependencies (claude-agent-sdk, anthropic, typer, fastapi, pydantic, google-adk, mcp), src/orchestration/ package layout matching HLD structure. Pydantic models for AgentConfig, Message, TopologyConfig. Agent and AgentProvider Protocols in providers/base.py. Provider registry. Pydantic Settings for application configuration. Shared provider error hierarchy. Basic logging setup. Effort: 2/5

---

## Feature Slices (in implementation order)

### → Milestone 1: SDK Agent Task Execution

2. [x] **SDK Agent Provider** — Implement SDKAgentProvider satisfying the AgentProvider Protocol. SDKAgent wraps claude-agent-sdk's `query()` for one-shot tasks and `ClaudeSDKClient` for multi-turn sessions. Agent translates orchestration Messages into SDK queries and SDK responses back into Messages. Configurable: system_prompt, allowed_tools, permission_mode, cwd, setting_sources (for CLAUDE.md loading). Provider auto-registers as "sdk" in the provider registry. Dependencies: [Foundation]. Risk: Low (SDK is well-documented, auth handled by Claude CLI). Effort: 3/5

3. [x] **Agent Registry & Lifecycle** — Agent registry: spawn agent by name, type (sdk/api), and provider config. Track agent state (idle, processing, terminated). Graceful shutdown of individual agents and all-agents. In-process async agent execution. Uses AgentProvider Protocol to create agent instances — registry is provider-agnostic. Dependencies: [SDK Agent Provider]. Risk: Low. Effort: 2/5

4. [x] **CLI Foundation & SDK Agent Tasks** — Typer app with commands: `spawn` (create agent with --type, --provider, --cwd), `list` (show agents with type and state), `task` (send a one-shot task to a named agent, display streaming output), `shutdown` (stop agent). Wire the full path: CLI → Agent Registry → SDK Agent Provider → claude-agent-sdk → response displayed. Dependencies: [Agent Registry]. Risk: Low. Effort: 2/5

5. [ ] **SDK Client Warm Pool** — Pre-initialize and manage a pool of `ClaudeSDKClient` instances to eliminate the ~20-30s cold-start penalty on task execution. Configurable pool size (default 1 for single-agent use). Pool integrated with agent registry — spawning an SDK agent in client mode checks out a warm instance instead of creating one from scratch. Idle client health checks and recycling. CLI `pool` command to show pool status and pre-warm instances. **Completes M1.** Dependencies: [CLI Foundation]. Risk: Medium (client lifecycle edge cases — disconnect/reconnect, stale sessions). Effort: 3/5

### → Milestone 2: Multi-Agent Communication

6. [ ] **Message Bus Core** — Async pub/sub message system. Agents and other participants (human, system) publish and subscribe. Broadcast routing (all subscribers see all messages) as the default topology. Message history (in-memory) with per-agent filtering view. Message schema: sender, recipients, content, timestamp, message_type, metadata. Dependencies: [Agent Registry]. Risk: Low. Effort: 2/5

7. [ ] **Anthropic API Provider** — Implement AnthropicAPIProvider satisfying the AgentProvider Protocol. AnthropicAPIAgent wraps the anthropic SDK's AsyncAnthropic client for conversational message exchange. Supports both api_key and auth_token authentication. Manages conversation history internally. Converts between orchestration Messages and Anthropic message format. Provider auto-registers as "anthropic" in the provider registry. This is the first API provider and validates the Protocol for future providers (OpenAI, Gemini, etc.). Dependencies: [Foundation]. Risk: Low. Effort: 3/5

8. [ ] **Multi-Agent Message Routing** — Connect agents to the message bus. When an agent publishes a message, the bus routes it to other agents based on the active topology. Each receiving agent's `handle_message` is called, and its response messages are published back to the bus. Conversation turn management to prevent infinite loops (max turns, cooldown, explicit stop). CLI `observe` command to watch a multi-agent conversation in real time. **Completes M2.** Dependencies: [Message Bus Core, Anthropic API Provider OR SDK Agent Provider (at least one)]. Risk: Medium (turn management and loop prevention need careful design). Effort: 3/5

### → Milestone 3: Human + Agents

9. [ ] **Human-in-the-Loop Participation** — Human becomes a first-class participant on the message bus (not just a CLI command issuer). In multi-agent mode, human messages are broadcast to all agents alongside agent-to-agent messages. CLI interactive mode: human sees all agent messages and can interject at any point. Agents see human messages in their conversation context. Turn-taking options: free-form (anyone can speak), moderated (human approves each round), or prompted (agents wait for human input between rounds). **Completes M3.** Dependencies: [Multi-Agent Message Routing]. Risk: Low. Effort: 2/5

### Post-Milestone Feature Work

10. [ ] **Communication Topologies** — Topology manager as first-class component. Implement filtered topology (agents see addressed messages + broadcasts only), hierarchical topology (orchestrator sees all, workers see assigned scope), and custom topology (user-provided routing function). CLI commands to select and configure topology per session. Topology affects message bus routing, not agent logic — agents remain unaware of topology details. Dependencies: [Human-in-the-Loop]. Risk: Medium. Effort: 3/5

11. [ ] **Additional LLM Providers** — OpenAI provider implementation (Chat Completions API, API key auth). Provider registry lookup by name. Per-agent provider override at spawn time (e.g., spawn a GPT agent and a Claude agent in the same session). CLI `spawn` gains `--provider openai --model gpt-4o` flags. Validates that the AgentProvider Protocol generalizes beyond Anthropic. Establishes the pattern for Gemini, OpenRouter, and local model providers. Dependencies: [Anthropic API Provider]. Risk: Low. Effort: 2/5

12. [ ] **ADK Integration** — Bridge between ADK workflow patterns (ParallelAgent, SequentialAgent, Loop) and core engine message bus. ADK manages execution order; each agent step routes through the message bus. Define ADK-compatible agent wrappers that use the AgentProvider abstraction. CLI commands for running ADK workflows (`workflow run`, `workflow list`). Dependencies: [Multi-Agent Message Routing]. Risk: Medium (ADK API surface and integration patterns need exploration). Effort: 3/5

13. [ ] **MCP Server** — Expose orchestration as MCP tools via Python MCP SDK. Tools: create_agent, list_agents, send_task, send_message, get_conversation, shutdown_agent, set_topology. Stdio transport for Claude Code / Cursor integration. MCP server reads from same core engine as CLI — no duplication of logic. Dependencies: [Message Bus Core, Agent Registry]. Risk: Low. Effort: 2/5

14. [ ] **REST + WebSocket API** — FastAPI server. REST endpoints for agent lifecycle (create, list, delete) and conversation management (send message, get history). WebSocket endpoint for real-time message streaming (subscribe to message bus events). Automatic OpenAPI docs. CORS configuration for future frontend consumption. Dependencies: [Message Bus Core, Agent Registry]. Risk: Low. Effort: 2/5

---

## Integration Work

15. [ ] **Review Workflow Templates** — Predefined workflow configurations for common review patterns: code review (agent reviews files against rules), task verification (agent checks task file against slice design), cross-agent plan review (one agent evaluates another's plan output). Each template is a configuration combining system_prompt, allowed_tools, cwd, and setting_sources. CLI command: `review` with `--template` flag. Uses SDK agents for file access. Dependencies: [CLI Foundation, SDK Agent Provider]. Risk: Low. Effort: 2/5

16. [ ] **Subprocess Agent Support** — Extend agent registry to spawn agents as OS processes (`asyncio.create_subprocess_exec`). Stdout/stderr streaming piped back through message bus. PID tracking in agent registry. Graceful and forced termination. Orphan cleanup on restart (PID file strategy). Primary use case: spawning non-SDK CLI tools as agent participants. Dependencies: [Agent Registry, Message Bus Core]. Risk: Medium. Effort: 2/5

17. [ ] **End-to-End Testing & Documentation** — Integration tests for core flows (SDK agent task, API agent chat, multi-agent conversation, human-in-the-loop, topology switching, review workflows). CLI help text and usage examples. README with quickstart (install, configure credentials, spawn first agent). Deployment documentation (local dev, MCP config, server mode). Dependencies: [all prior slices]. Risk: Low. Effort: 2/5

---

## Implementation Order

```
Foundation:
  1. Project Setup & Core Models

M1 — SDK Agent Task Execution:
  2. SDK Agent Provider
  3. Agent Registry & Lifecycle
  4. CLI Foundation & SDK Agent Tasks
  5. SDK Client Warm Pool

M2 — Multi-Agent Communication:
  6. Message Bus Core (can start after 3)
  7. Anthropic API Provider (can start after 1, parallel with 2-5)
  8. Multi-Agent Message Routing

M3 — Human + Agents:
  9. Human-in-the-Loop Participation

Post-Milestone (order flexible):
  10. Communication Topologies
  11. Additional LLM Providers
  12. ADK Integration
  13. MCP Server (can start after 6+3)
  14. REST + WebSocket API (can start after 6+3)
  15. Review Workflow Templates (can start after 4)

Integration:
  16. Subprocess Agent Support
  17. End-to-End Testing & Documentation
```

### Parallelization Notes

- **Slices 7 and 2-5 are parallel tracks.** The Anthropic API Provider only depends on Foundation, not on the SDK Agent Provider. An agent working on the API provider can start as soon as Foundation is done, while another works on the SDK path toward M1.
- **Slice 15 (Review Workflow Templates) can start immediately after slice 4.** It only needs the SDK agent and CLI — no message bus or warm pool required. This is the fastest path to the code review use case.
- **Slices 13 and 14 are independent of each other** and can be done in any order after their dependencies are met.

---

## Tracked Enhancements

These are high-value capabilities identified during slice design that are intentionally deferred from their parent slices to keep scope bounded. They should be addressed as dedicated slices or folded into existing slices during post-M1 planning.

### SDK Agent Enhancements (parent: slice 2 — SDK Agent Provider)

- **Hook system integration**: The SDK's `PreToolUse` / `PostToolUse` hooks enable programmatic control over agent behavior — deny dangerous commands, enforce read-only mode, log tool usage, inject review constraints. Natural complement to review workflow templates (slice 15). Candidate: fold into slice 15 or create a dedicated slice if hook patterns are reusable beyond reviews.

- **Custom MCP tool definitions**: The SDK's `@tool` decorator and `create_sdk_mcp_server` allow defining Python functions as tools available to SDK agents, running in-process (no subprocess). Enables orchestration-aware tools: "query the message bus," "check agent state," "submit review verdict." Bridges SDK agent autonomy with orchestration system state. Candidate: dedicated slice post-M2, when agents need awareness of each other.

- **Subagent spawning**: The SDK natively supports subagent definitions via `ClaudeAgentOptions.agents`. An SDK agent can spawn its own subagents for parallel work with isolated context. Complementary to (not competing with) the orchestration framework's multi-agent coordination. Candidate: explore post-M2, after the message bus and multi-agent patterns are established. Lower priority than hooks and custom tools.

---

## Notes

- **Numbering**: Slices use the 100 band (100-119) since this is the project's primary initiative. If this creates index pressure with future initiatives, slices can be re-indexed.
- **Frontend deferred**: The HLD identifies a future React UI. This is explicitly out of scope for this slice plan. When it arrives, it connects to the REST + WebSocket API (slice 14) and warrants its own architecture document and slice plan.
- **SDK initialization cost**: The Claude Agent SDK's `ClaudeSDKClient` has ~20-30s startup time per instance. Slice 5 (SDK Client Warm Pool) addresses this as the final M1 deliverable, ensuring responsive task execution even for single-agent use.
- **ADK exploration**: Slice 12 (ADK Integration) depends on the current ADK Python SDK API surface. A brief spike at the start of that slice may be warranted to validate assumptions from the HLD.
- **Multi-provider validation**: Slice 11 (Additional LLM Providers) is the critical test that the AgentProvider Protocol generalizes. If the OpenAI provider requires Protocol changes, those changes should be backported to Foundation and Anthropic API Provider before proceeding further.
- **Review workflows (slice 15) are high practical value.** They can be started as soon as slice 4 (CLI Foundation) is complete, and they directly enable the code review, task verification, and cross-agent plan review use cases that are immediate priorities.
- **Old orchestration artifacts**: The orch-128, 129, 132, 140 documents in project knowledge describe work from the Node.js/Electron era. They are reference material for design rationale only — no code or architecture carries forward into these slices.
