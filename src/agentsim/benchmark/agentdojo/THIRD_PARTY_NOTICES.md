# Third-party notices

## AgentDojo

This benchmark adapter contains a private, modified copy of AgentDojo's
versioned suite definitions, tools, and YAML fixtures. The imported source is
from AgentDojo package version `0.1.35`, benchmark suite `v1.2.2`, upstream
commit `089ed468cf3ed0322acc66b0211f26d9d90dbf60`.

Copyright (c) 2024 Edoardo Debenedetti, Jie Zhang, Mislav Balunovic, Luca
Beurer-Kellner, Marc Fischer, and Florian Tramèr.

AgentDojo is licensed under the MIT License. The complete license text is
included in `AGENTDOJO_LICENSE.md`.

`tools/vendor_agentdojo.py` documents the mechanical import and namespace
rewrite used to reproduce the private `_vendor` tree. AgentDojo itself is not a
runtime dependency of Agent Sim.
