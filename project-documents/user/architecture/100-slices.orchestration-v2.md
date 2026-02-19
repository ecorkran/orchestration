---
docType: slice-plan
parent: 100-arch.orchestration-v2.md
project: orchestration
dateCreated: 20260217
dateUpdated: 20260217
---

# Slice Plan: Orchestration (Python Reboot)

## Parent Document
`100-arch.orchestration-v2.md` — High-Level Design: Orchestration (Python Reboot)

## Milestone Targets

These milestones define the priority ordering. Slices are sequenced to reach each milestone as early as possible.

**M1 — Single-agent CLI chat:** Spawn one Claude agent authenticated via credentials (Max account), exchange messages via CLI.

**M2 — Agent-to-agent conversation:** Two Claude agents communicate with each other through the message bus.

**M3 — Human + agents:** Human participates alongside multiple agents in a shared conversation.

---

## Foundation Work

1. [x] **Project Setup & Core Models** — `uv init`, pyproject.toml with dependencies (anthropic, typer, fastapi, pydantic, google-adk, mcp), src/orchestration/ package layout matching HLD structure, Pydantic models for Agent, Message, ProviderConfig, TopologyConfig. Pydantic Settings for application configuration (provider credentials, defaults). Basic logging setup. Effort: 2/5

---

## Feature Slices (in implementation order)

### → Milestone 1: Single-Agent CLI Chat

2. [ ] **Anthropic Provider with Credential Auth** — Define `LLMProvider` Protocol (send message, stream response, validate credentials). Implement Anthropic provider with credential/session-based auth (Claude Max) as the primary path and API key as fallback. Provider config via Pydantic Settings (env vars or config file). Credential validation on startup. Dependencies: [Foundation]. Risk: Medium (credential auth flow needs investigation — exact OAuth/session mechanism for Anthropic SDK). Effort: 3/5

3. [ ] **Agent Registry & Lifecycle** — Agent registry: spawn agent with name, instructions, and provider config. Track agent state (idle, processing, terminated). Graceful shutdown of individual agents and all-agents. In-process async agent execution (asyncio tasks). Uses LLMProvider to create agent instances. Dependencies: [Anthropic Provider]. Risk: Low. Effort: 2/5

4. [ ] **Message Bus Core** — Async pub/sub message system. Agents and other participants (human, system) publish and subscribe. Broadcast routing (all subscribers see all messages) as the default and initial topology. Message history (in-memory) with per-agent filtering view. Message schema: sender, recipients, content, timestamp, message type, topology metadata. Dependencies: [Agent Registry]. Risk: Low. Effort: 2/5

5. [ ] **CLI Foundation & Single-Agent Chat** — Typer app with commands: `spawn` (create agent), `list` (show agents), `chat` (interactive session with a named agent), `shutdown` (stop agent). Wire the full path: CLI → Agent Registry → Provider → Message Bus → response displayed. Interactive chat mode with input prompt and streaming response output. **Completes M1.** Dependencies: [Message Bus Core]. Risk: Low. Effort: 2/5

6. [ ] **Supervisor Component** — Core supervision and health monitoring. Supervisor watches asyncio task state, detects failures (crashed tasks, unhandled exceptions) and response timeouts (agent stuck in processing beyond configurable threshold). one_for_one restart strategy: restart only the failed agent with clean state. New agent states (restarting, failed) added to registry state machine. CLI list command reflects supervisor-managed states. Dependencies: [Agent Registry, Message Bus Core]. Risk: Low. Effort: 2/5

7. [ ] **Supervisor Restart Strategies & Recovery** — Extend supervisor with additional restart strategies for agent groups: one_for_all (restart all agents in group) and rest_for_one (restart failed agent and all agents spawned after it). Circuit breaker: max N restarts within configurable time window; exceeded marks agent failed and stops retrying. State recovery policy configurable per agent: clean slate (fresh instance, no history) or conversation resume (restore message history from bus). Supervisor publishes events (agent_restarted, agent_failed, restart_limit_exceeded) to message bus for observability by CLI, other agents, and external interfaces. Dependencies: [Supervisor Component]. Risk: Low (design decisions on recovery policies are the substantive work; implementation is straightforward). Effort: 2/5

### → Milestone 2: Agent-to-Agent Conversation

8. [ ] **Multi-Agent Message Routing** — Extend message bus so agents can respond to each other's messages, not just human input. Agent "listening" loop: when a message arrives for an agent (or broadcast), the agent evaluates whether to respond. Response flows back through message bus, triggering other agents' evaluation. Configurable response behavior (always respond, self-select, round-robin). Conversation turn management to prevent infinite loops (max turns, cooldown, explicit stop). CLI `observe` command to watch a multi-agent conversation in real time. **Completes M2.** Dependencies: [CLI Foundation]. Risk: Medium (turn management and loop prevention need careful design). Effort: 3/5

### → Milestone 3: Human + Agents

9. [ ] **Human-in-the-Loop Participation** — Human becomes a first-class participant on the message bus (not just a CLI command issuer). In multi-agent mode, human messages are broadcast to all agents alongside agent-to-agent messages. CLI interactive mode: human sees all agent messages and can interject at any point. Agents see human messages in their conversation context. Turn-taking options: free-form (anyone can speak), moderated (human approves each round), or prompted (agents wait for human input between rounds). **Completes M3.** Dependencies: [Multi-Agent Message Routing]. Risk: Low. Effort: 2/5

### Post-Milestone Feature Work

10. [ ] **Communication Topologies** — Topology manager as first-class component. Implement filtered topology (agents see addressed messages + broadcasts only), hierarchical topology (orchestrator sees all, workers see assigned scope), and custom topology (user-provided routing function). CLI commands to select and configure topology per session. Topology affects message bus routing, not agent logic — agents remain unaware of topology details. Dependencies: [Human-in-the-Loop]. Risk: Medium. Effort: 3/5

11. [ ] **Additional LLM Providers** — OpenAI provider implementation (API key auth). Provider registry for runtime lookup by name. Per-agent provider override at spawn time (e.g., spawn a GPT agent and a Claude agent in the same session). CLI `spawn` gains `--provider` and `--model` flags. Dependencies: [CLI Foundation]. Risk: Low. Effort: 2/5

12. [ ] **ADK Integration** — Bridge between ADK workflow patterns (ParallelAgent, SequentialAgent, Loop) and core engine message bus. ADK manages execution order; each agent step routes through the message bus. Define ADK-compatible agent wrappers that use the LLMProvider abstraction. CLI commands for running ADK workflows (`workflow run`, `workflow list`). Dependencies: [Multi-Agent Message Routing]. Risk: Medium (ADK API surface and integration patterns need exploration). Effort: 3/5

13. [ ] **MCP Server** — Expose orchestration as MCP tools via Python MCP SDK. Tools: create_agent, list_agents, send_message, get_conversation, shutdown_agent, set_topology. Stdio transport for Claude Code / Cursor integration. MCP server reads from same core engine as CLI — no duplication of logic. Dependencies: [Message Bus Core, Agent Registry]. Risk: Low. Effort: 2/5

14. [ ] **REST + WebSocket API** — FastAPI server. REST endpoints for agent lifecycle (create, list, delete) and conversation management (send message, get history). WebSocket endpoint for real-time message streaming (subscribe to message bus events). Automatic OpenAPI docs. CORS configuration for future frontend consumption. Dependencies: [Message Bus Core, Agent Registry]. Risk: Low. Effort: 2/5

---

## Integration Work

15. [ ] **Subprocess Agent Support** — Extend agent registry to spawn agents as OS processes (`asyncio.create_subprocess_exec`). Stdout/stderr streaming piped back through message bus. PID tracking in agent registry. Graceful and forced termination. Orphan cleanup on restart (PID file strategy). Primary use case: spawning Claude Code CLI sessions as agents. Dependencies: [Agent Registry, Message Bus Core]. Risk: Medium. Effort: 2/5

16. [ ] **End-to-End Testing & Documentation** — Integration tests for core flows (single agent chat, multi-agent conversation, human-in-the-loop, topology switching). CLI help text and usage examples. README with quickstart (install, configure credentials, spawn first agent). Deployment documentation (local dev, MCP config, server mode). Dependencies: [all prior slices]. Risk: Low. Effort: 2/5

---

## Notes

- **Numbering**: Slices use the 100 band (100-119) since this is the project's primary initiative derived from the project-level HLD. If this creates index pressure with future project-level architecture docs, slices can be re-indexed to a working range band.
- **Frontend deferred**: The HLD identifies a future React UI. This is explicitly out of scope for this slice plan. When it arrives, it connects to the REST + WebSocket API (slice 12) and warrants its own architecture document and slice plan.
- **Credential auth risk**: Slice 2 (Anthropic Provider) carries the highest uncertainty. The exact mechanism for credential/session-based auth with the Anthropic SDK should be investigated early. If the auth flow proves more complex than expected, this slice may split into credential auth + API key fallback as separate slices.
- **ADK exploration**: Slice 10 (ADK Integration) depends on the current ADK Python SDK API surface. A brief spike at the start of that slice may be warranted to validate assumptions from the HLD.
- **Slices 9, 11, 12 are independent of each other** and can be done in any order after their dependencies are met. They're numbered by estimated value priority but are parallelizable.
- **Old orchestration artifacts**: The orch-128, 129, 132, 140 documents in project knowledge describe work from the Node.js/Electron era. They are reference material for design rationale only — no code or architecture carries forward into these slices.
