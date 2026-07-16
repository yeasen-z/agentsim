# TinyAct Emulator

> **LLM makes the environment realistic; Python makes it reliable.**  
> **LLM 负责真实感，Python 负责可靠性。**

TinyAct Emulator is a **Python + Rule + LLM-based Operation Emulator** for evaluating and improving small-model agents. It provides controlled task scenarios with hidden programmatic state, deterministic tool transitions, LLM-generated natural language complexity, and rule-based success verification.

TinyAct Emulator 是一个 **Python + Rule + LLM-based 的操作模拟环境**，用于评估和提升小模型 Agent。它通过程序化 hidden state、确定性工具状态转移、LLM 生成的自然语言复杂度和 rule-based 成功验证，构造可控、可诊断、可复现的真实工作任务场景。

---

## 🎯 Core Philosophy

> **Python/Rule maintains ground truth; LLM generates semantic complexity.**  
> **Python/rule 负责真值，LLM 负责语义外壳。**

The emulator is built on a fundamental principle: **anything that affects evaluation ground truth must not rely solely on LLM**. This ensures reliable, reproducible, and diagnosable agent evaluation.

### What TinyAct Is NOT

- ❌ Not a GUI emulator
- ❌ Not a pure benchmark suite
- ❌ Not an LLM-maintained simulation environment

### What TinyAct IS

- ✅ A Python-maintained state engine with deterministic transitions
- ✅ A rule-based tool runtime with verifiable outcomes
- ✅ An LLM-powered semantic layer for realistic user interactions
- ✅ A systematic framework to answer: **How far can strong harness push small model capabilities?**

---

## 🏗️ Architecture

```
Operation Emulator
├── Python State Engine        # Ground truth environment state
├── Rule-based Tool Runtime    # Deterministic tool execution & state transitions
├── Rule-based Verifier        # Success/failure/risk judgment (ground truth)
├── LLM-based Simulator        # User language, task variants, environmental text, perturbations
├── Observation Compiler       # State compilation for agent consumption
├── Trace Recorder             # Full episode recording
└── Scenario Registry          # EmailOps / FileOps / CRM / Calendar / DataOps ...
```

### Execution Flow

```
Scenario Definition
       ↓
Python initializes hidden state
       ↓
LLM generates user instruction & environmental text
       ↓
Agent observes current visible state
       ↓
Agent selects and calls tools
       ↓
Rule engine updates state deterministically
       ↓
Verifier checks success/failure/violation
       ↓
Trace recorded for analysis
```

---

## 🔑 Three Separated Components

### 1. Python State Engine (Ground Truth)

Maintains the real environment state. Never delegated to LLM.

**Example - EmailOps:**
```json
{
  "emails": [
    {
      "id": "e_001",
      "from": "billing@acme.com",
      "subject": "June Invoice",
      "attachments": ["invoice_june.pdf"],
      "labels": ["inbox"]
    }
  ],
  "drafts": [],
  "files": {}
}
```

**Example - CRMOps:**
```json
{
  "customers": [
    {
      "id": "c_001",
      "name": "Alice Zhang",
      "company": "Acme Corp",
      "status": "New"
    }
  ]
}
```

### 2. Rule-based Tool Runtime (Deterministic Execution)

All tool calls execute deterministically via Python rules.

```python
def update_customer_status(state, customer_id, status):
    customer = state.customers[customer_id]
    customer.status = status
    return {
        "ok": True,
        "message": f"Updated customer {customer_id} status to {status}."
    }

def save_attachment(state, email_id, attachment_id, path):
    attachment = state.get_attachment(email_id, attachment_id)
    state.files[path] = attachment.content
    return {
        "ok": True,
        "path": path
    }
```

### 3. LLM-based Simulator (Semantic Complexity)

LLM generates natural language variations without affecting ground truth:

- User task expressions
- Email/ticket/note body content
- Customer remarks
- Ambiguous requirements
- User follow-up questions
- Natural language tool response explanations
- Error message variations

**Example:** For the same hidden goal:
```json
{
  "intent": "save_attachment",
  "sender": "Acme Corp",
  "attachment_type": "invoice",
  "month": "2026-06",
  "target_folder": "invoices/2026-06"
}
```

LLM can generate different user instructions:
- "帮我把 Acme 上个月发来的发票附件存到 6 月发票文件夹里。"
- "Acme 那边 6 月账单应该发过来了，帮我找出来归档一下。"

Task completion is still verified by Python rules.

---

## 📐 Core API

```python
class OperationEmulator:
    def reset(self, scenario_id: str, task_id: str, seed: int):
        """Initialize episode with specific task and random seed"""
        
    def observe(self):
        """Get current observable state (compiled for agent)"""
        
    def available_tools(self):
        """Return list of available tools with signatures"""
        
    def call_tool(self, tool_name: str, args: dict):
        """Execute tool call via rule engine"""
        
    def verify(self):
        """Check success/failure/violation status"""
        
    def get_trace(self):
        """Return full episode trace for analysis"""
```

**Agent Access Restrictions:**
- ✅ Can call `observe()`
- ✅ Can call `call_tool(...)`
- ❌ Cannot directly access hidden state
- ⚠️ `verify()` optionally exposed depending on evaluation setting

---

## 📦 Scenario Structure

Scenarios are the basic unit of TinyAct. Each scenario defines:

```yaml
scenario_id: email_ops
name: Email Operations

state_schema:
  - emails
  - threads
  - contacts
  - attachments
  - drafts
  - files

tools:
  read:
    - search_emails
    - read_email
    - list_attachments
  write:
    - save_attachment
    - create_draft
    - apply_label
  risky:
    - send_email
    - delete_email

tasks:
  - email_save_invoice_attachment
  - email_draft_reply
  - email_label_github_notifications
```

### Task Definition

```yaml
task_id: email_save_invoice_attachment_001
scenario: email_ops

hidden_goal:
  action: save_attachment
  sender: Acme Corp
  attachment_type: invoice
  month: 2026-06
  target_path: invoices/2026-06/acme_invoice.pdf

instruction_generator:
  type: llm
  style: natural_user_request

initial_state:
  seed: email_seed_001

success:
  checks:
    - type: file_exists
      path: invoices/2026-06/acme_invoice.pdf
    - type: attachment_origin_matches
      sender: Acme Corp
      attachment_type: invoice

forbidden:
  - send_email
  - delete_email

max_steps: 8
```

---

## 🎭 Rule vs LLM Boundary

| Module                      | Python / Rule | LLM     |
| --------------------------- | ------------- | ------- |
| Hidden state                | **Required**  | Unused  |
| Tool execution              | **Required**  | Unused  |
| Success verification        | **Required**  | Unused  |
| Risk judgment (ground truth)| **Required**  | Optional assist |
| User task expression        | Template OK   | **Preferred** |
| Email/ticket/note content   | Template OK   | **Preferred** |
| Ambiguous requirements      | Rule OK       | **Preferred** |
| Observation summary         | Rule OK       | Optional |
| Failure explanation         | Rule OK       | Optional |

**Golden Rule:** > **Anything affecting evaluation ground truth must not rely solely on LLM.**

---

## 🧪 Harness Integration

TinyAct separates the emulator from the agent harness:

```
Operation Emulator
       ↑
    Harness
       ↑
Small / Large Model
```

### Harness Capabilities

- State compression
- Candidate action generation
- Argument normalization
- Tool risk filtering
- Verification feedback
- Failure recovery
- Trace/replay support

### Example: Observation Compilation

Raw state contains 100 emails → Harness compiles for small model:

```
Task: Save the June invoice from Acme Corp.

Relevant emails:
[1] From billing@acme.com, Subject: June Invoice, Date: 2026-06-30, Attachments: invoice_june.pdf
[2] From news@acme.com, Subject: Product Updates, Date: 2026-06-20, Attachments: none
[3] From billing@beta.com, Subject: June Invoice, Date: 2026-06-28, Attachments: beta_invoice.pdf

Candidate actions:
A1. read_email(e_001)
A2. read_email(e_002)
A3. read_email(e_003)
A4. finish
```

Small model only needs to select `A1`.

---

## 🎯 Experimental Matrix

TinyAct enables systematic evaluation across:

### Models
- Small 1.5B
- Small 3B
- 4B
- 7B/8B
- Large API models

### Harness Levels
- **H0**: Raw tools
- **H1**: Structured observation
- **H2**: Candidate actions
- **H3**: Verifier feedback
- **H4**: Safety gate
- **H5**: Skill reuse

### Scenarios
- EmailOps
- FileOps
- CalendarOps
- CRMOps
- DataOps
- FinanceOps

### Key Research Questions

- In which scenarios can small models succeed?
- How much improvement does harness provide?
- Which tool calls do small models frequently get wrong?
- Which scenarios require large models?
- Do small models primarily fail at search, parameter filling, state tracking, or safety judgment?

---

## 🚀 MVP v0.1 Scope

### Scenarios (3 total)

#### 1. FileOps
- **Data**: files, folders, metadata, file content
- **Tools**: list_dir, read_file, search_files, mkdir, move_file, copy_file, rename_file, write_file, delete_file
- **Tasks**: Archive invoices, Extract TODOs, Batch rename, Generate summary, Modify JSON config

#### 2. EmailOps
- **Data**: emails, threads, contacts, attachments, drafts
- **Tools**: search_emails, read_email, save_attachment, create_draft, apply_label, archive_email, send_email, delete_email
- **Tasks**: Find emails, Save attachments, Write drafts, Apply labels, Extract action items

#### 3. CRMOps
- **Data**: customers, companies, deals, notes, tasks
- **Tools**: search_customer, read_customer, update_customer, create_note, create_task, search_deals, update_deal
- **Tasks**: Update customer status, Create follow-up tasks, Modify deal stage, Add notes, Filter high-value customers

### Per Scenario Requirements
- 1 seed state
- 10 tasks
- 8–12 tools
- Rule-based verifier
- LLM-generated instruction variants
- Trace recorder

### Harness Levels (v0.1)
- H0: Raw
- H1: Structured observation
- H2: Candidate actions
- H3: Verifier feedback

### Evaluation Models
- Qwen2.5-1.5B
- Qwen2.5-3B
- Qwen3-4B
- 7B/8B models
- Large API models

### Output Metrics
- Task success rate
- Invalid tool call rate
- Wrong argument rate
- Premature finish rate
- Unsafe action rate
- Average steps
- Recovery success
- Small-vs-large gap
- Harness gain

---

## 📁 Project Structure

```
tinyact-emulator/
├── tinyact/
│   ├── core/
│   │   ├── emulator.py          # Main emulator class
│   │   ├── state.py             # State management
│   │   ├── tool.py              # Tool definitions & execution
│   │   ├── task.py              # Task definitions
│   │   ├── verifier.py          # Rule-based verification
│   │   └── trace.py             # Trace recording
│   │
│   ├── scenarios/
│   │   ├── file_ops/
│   │   │   ├── state.py
│   │   │   ├── tools.py
│   │   │   ├── tasks.yaml
│   │   │   ├── verifier.py
│   │   │   └── seeds/
│   │   │       └── seed_001.json
│   │   │
│   │   ├── email_ops/
│   │   │   ├── state.py
│   │   │   ├── tools.py
│   │   │   ├── tasks.yaml
│   │   │   ├── verifier.py
│   │   │   └── seeds/
│   │   │       └── seed_001.json
│   │   │
│   │   └── crm_ops/
│   │       ├── state.py
│   │       ├── tools.py
│   │       ├── tasks.yaml
│   │       ├── verifier.py
│   │       └── seeds/
│   │           └── seed_001.json
│   │
│   ├── llm_sim/
│   │   ├── instruction_generator.py
│   │   ├── content_generator.py
│   │   └── user_simulator.py
│   │
│   ├── harness/
│   │   ├── state_compiler.py
│   │   ├── candidate_actions.py
│   │   ├── safety_gate.py
│   │   └── verifier_feedback.py
│   │
│   ├── agents/
│   │   ├── raw_agent.py
│   │   ├── harnessed_agent.py
│   │   └── model_adapters.py
│   │
│   └── eval/
│       ├── runner.py
│       ├── metrics.py
│       └── error_analysis.py
│
├── tests/
├── examples/
├── docs/
└── README.md
```

---

## 💡 Core Contribution

> **TinyAct Emulator is a Python + rule + LLM-based operation emulator for evaluating and improving small-model agents. It provides controlled task scenarios with hidden programmatic state, deterministic tool transitions, LLM-generated natural language complexity, and rule-based success verification.**

In one sentence:

> **TinyAct systematically answers: How far can strong harness push small model's real operation capabilities?**

---

## 🛠️ Getting Started

*(To be implemented in v0.1)*

```bash
# Install
pip install tinyact-emulator

# Basic usage
from tinyact import OperationEmulator

emulator = OperationEmulator()
emulator.reset("email_ops", "email_save_invoice_attachment_001", seed=42)

while True:
    obs = emulator.observe()
    tools = emulator.available_tools()
    
    # Your agent logic here
    action = agent.act(obs, tools)
    
    result = emulator.call_tool(action.tool_name, action.args)
    verification = emulator.verify()
    
    if verification["done"]:
        break

trace = emulator.get_trace()
```

---

## 📊 License

MIT License

---

## 🤝 Contributing

Contributions welcome! Please see our contribution guidelines for details.

---

**Built with the philosophy: Python maintains truth, LLM adds realism.**