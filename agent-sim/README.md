# Agent-Sim Framework

A modular, multi-agent simulation framework where the **Environment** is the core kernel, providing standard interfaces for pluggable **Runtimes** and **Agents**. Features built-in **Trace Monitoring** for full observability and a **Sandboxed File System** for secure execution.

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Defined Logic                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Runtime    │  │    Agent     │  │    Tools     │      │
│  │  (Strategy)  │  │   (Logic)    │  │ (Capabilities)│      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │
┌─────────▼─────────────────▼─────────────────▼───────────────┐
│                  Environment (Core Kernel)                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Shared State│  │Tool Registry│  │   Trace Monitor     │ │
│  │ (Blackboard)│  │ (Sandboxed) │  │ (Built-in Observer) │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │           Sandboxed File System                       │ │
│  │  All I/O confined to ./sandbox (Security Boundary)    │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Key Features

- **🔌 Pluggable Components**: Swap Runtimes (schedulers) and Agents (logic) without changing the core environment.
- **🤝 Multi-Agent Collaboration**: Built-in support for role-based communication, message passing, and shared state.
- **🔍 Comprehensive Tracing**: Every decision, tool call, and message is recorded for debugging and evaluation.
- **🔒 Secure Execution**: File operations are strictly sandboxed to prevent system access.
- **🛠 Extensible Tools**: Easy registration of custom capabilities with automatic validation.

## 🚀 Quick Start

### 1. Run the Demo

```bash
cd agent-sim
python demo_multi_agent.py
```

This runs a multi-agent scenario where:
- A **Planner** delegates a math task (`25 * 4`)
- An **Executor** calculates and saves the result to a file
- Full trace is saved to `trace_log.json`

### 2. Verify Results

```bash
# Check the created file (sandboxed)
cat sandbox/output.txt

# View the execution trace
cat trace_log.json | jq '.events[:5]'  # First 5 events
```

## 📂 Project Structure

```
agent-sim/
├── environment.py        # Core kernel (State, Tools, Monitor)
├── runtime.py            # Runtime strategies (Single, Multi-Agent)
├── agents.py             # Agent interface & mock implementations
├── tools.py              # Tool registry & built-in tools
├── trace_monitor.py      # Observability system
├── demo_multi_agent.py   # End-to-end demonstration
├── sandbox/              # Secure file operation directory
├── progress.md           # Development progress log
└── README.md             # This file
```

## 🧩 Core Components

### Environment
The central orchestrator managing:
- Global shared state
- Tool registration and execution
- Trace monitoring
- Sandbox enforcement

### Runtime
Defines **how** agents collaborate:
- `SingleAgentRuntime`: Simple loop for single agents
- `MultiAgentRuntime`: Round-robin scheduler with message queues
- *Extensible*: Implement custom strategies (Hierarchical, Market, etc.)

### Agent
Defines **what** logic each role performs:
- Implements `decide()` method
- Receives state and available tools
- Returns actions (call_tool, send_message, finish)

### Trace Monitor
Built-in observer recording:
- Agent decisions
- Tool invocations and results
- Inter-agent messages
- System lifecycle events

## 🔐 Security Model

All file operations are confined to the `./sandbox` directory:
- Paths are normalized to prevent traversal (`../`)
- Attempts to access files outside sandbox are blocked
- Safe for running untrusted agent code

## 📈 Next Steps

- [ ] Add more Runtime strategies (Hierarchical, Market-based)
- [ ] Integrate real LLM Agents (OpenAI, Anthropic, Local)
- [ ] Build Trace visualizer (timeline view)
- [ ] Add concurrency for parallel agent execution
- [ ] Implement evaluation metrics based on traces

## 📄 License

MIT
