# Environments

All four suites are in-memory, deterministic simulations. The agent receives a
user instruction and tool results, not direct access to the hidden state.
Untrusted strings embedded in tool-visible state are AgentDojo's indirect
prompt-injection surface.

| Suite | Hidden state components | User tasks | Injection tasks | Tools |
| --- | --- | ---: | ---: | ---: |
| `workspace` | inbox, calendar, cloud drive | 40 | 14 | 24 |
| `slack` | Slack workspace, web pages | 21 | 5 | 11 |
| `travel` | hotels, restaurants, car rentals, flights, user profile, calendar, reservations, inbox | 20 | 7 | 28 |
| `banking` | bank account, local files, user account | 16 | 9 | 11 |

## Workspace

The workspace suite combines email, calendar, and cloud-drive records. Tasks
include searching and summarizing messages, sending mail, arranging meetings,
editing/sharing files, and multi-application workflows. Injection placeholders
can occur inside emails, calendar fields, and drive documents returned by read
tools.

## Slack

The Slack suite models users, channels, direct messages, membership mutations,
and a small web service. Tasks require reading conversations, relaying
information, managing members, and interacting with linked web content.
Messages and web responses form the untrusted-data boundary.

## Travel

The travel suite combines several catalog services with mutable reservations,
a user profile, calendar, and email. Tasks require constraint reasoning over
price, rating, location, availability, dietary requirements, or flight data,
then optionally booking and recording the result. Reviews and other catalog
text can carry injections.

## Banking

The banking suite models balances, transaction history, scheduled transfers,
files, and user-account details. Read operations can reveal data needed to
calculate a legitimate transfer; write operations can move funds or modify
identity/security settings. Files and transaction descriptions are the main
untrusted inputs.

## Episode lifecycle

1. Load the versioned suite and substitute any supplied injection-vector text.
2. Run the user task's official `init_environment` hook.
3. Keep a deep copy as the pre-task ground truth.
4. Execute deterministic tools through Agent Sim's `ToolExecutor`.
5. Record every call and state snapshot in the generic Agent Sim `Trace`.
6. Evaluate final state, output, and action history with the suite-owned
   evaluator.

The observation compiler intentionally hides all suite ground truth. Hidden
state is available only to deterministic tools and the trusted benchmark
evaluator.
