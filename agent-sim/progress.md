# Agent-Sim Framework Progress

## Overview
Developed a modular, multi-agent simulation framework where the **Environment** is the core contribution, exposing standard interfaces for pluggable **Runtimes** and **Agents**. The framework includes a built-in **Trace Monitor** for comprehensive observability and a **Sandbox File System** for safe execution.

## Key Architectural Decisions

### 1. Core-Centric Architecture
- **Environment as the Kernel**: The `Environment` class is the central orchestrator. It manages:
  - Global State (Shared Blackboard)
  - Tool Registry (Sandboxed)
  - Trace Monitoring (Built-in Observer)
  - Sandbox Root Directory (Security Boundary)
- **Pluggable Components**:
  - **Runtime**: Defines *how* agents collaborate (e.g., RoundRobin, Hierarchical, Market). Swappable without changing the environment.
  - **Agent**: Defines *what* logic each role performs. Swappable implementations.

### 2. Multi-Agent Support
- Implemented a `MultiAgentRuntime` demonstrating:
  - **Role-Based Communication**: Agents send messages to specific roles via the shared state.
  - **Turn-Taking Scheduler**: Deterministic execution order (configurable).
  - **Shared Context**: All agents see the same `global_state` and `message_queue`.
- **Demo Scenario**: "Planner" delegates math tasks to "Executor", who uses tools and reports back.

### 3. Comprehensive Trace Monitoring
- **Built-in Observer**: The `TraceMonitor` is embedded in the Environment.
- **Granular Events**: Records:
  - Agent decisions (`agent_decide`)
  - Tool calls & results (`tool_call`, `tool_result`)
  - Inter-agent messages (`message_sent`, `message_received`)
  - System events (`runtime_start`, `runtime_end`)
- **Output**: Full execution trace saved to JSON for debugging and evaluation.

### 4. Security: Sandboxed File System
- **Sandbox Root**: All file operations are strictly confined to a dedicated directory (e.g., `/workspace/agent-sim/sandbox`).
- **Path Normalization**: Prevents directory traversal attacks (`../`).
- **Automatic Cleanup**: Sandbox can be reset between runs.
- **Real Execution**: Tools like `file_writer` perform real I/O, but *only* within the safe zone.

## Implementation Status

| Component | Status | Description |
| :--- | :--- | :--- |
| **Environment Core** | ✅ Complete | Manages state, tools, and monitoring. |
| **Trace Monitor** | ✅ Complete | Records all interactions to JSON. |
| **Sandbox FS** | ✅ Complete | Secure file read/write within root. |
| **Tool Registry** | ✅ Complete | Dynamic registration with spec validation. |
| **Multi-Agent Runtime** | ✅ Complete | Round-robin scheduler with message passing. |
| **Mock Agents** | ✅ Complete | Simple rule-based agents for demo. |
| **End-to-End Demo** | ✅ Verified | Successfully ran multi-agent task with file I/O. |

## Demo Verification
- **Scenario**: Calculate `25 * 4` and save to `output.txt`.
- **Flow**:
  1. `Planner` sends task to `Executor`.
  2. `Executor` calls `calculator` tool.
  3. `Executor` calls `file_writer` (sandboxed).
  4. `Executor` replies to `Planner`.
  5. `Planner` signals completion.
- **Result**:
  - File created at `sandbox/output.txt` with correct content.
  - `trace_log.json` contains 26 detailed events.
  - No files outside sandbox were touched.

## Next Steps
- [ ] Add more Runtime strategies (Hierarchical, Market-based).
- [ ] Integrate real LLM Agents (connect to OpenAI/Anthropic).
- [ ] Add visualizer for Trace logs.
- [ ] Implement concurrency support for parallel agent execution.
- [ ] Add evaluation metrics based on Trace data.
