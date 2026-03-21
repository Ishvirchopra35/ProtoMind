# Autonomous Prototyper — Codex Agent Context

## What this project does
Multi-agent LangGraph pipeline. User provides a natural language hardware prompt.
Five agents run in sequence (with parallelism where noted) to produce STL, firmware,
parts list, and a physics simulation verification.

## Tech stack
- Python 3.11+
- LangGraph + LangChain
- Gemini API (google-genai, langchain-google-genai)
- PyBullet (physics simulation)
- OpenSCAD CLI (STL compilation — must be installed separately)
- Streamlit (dashboard)
- Tenacity (retry logic)

## Agent responsibilities
1. decompose       — Takes user_prompt, returns structured decomposed_tasks dict
2. cad_agent       — Takes decomposed_tasks, returns OpenSCAD code + compiled STL path
3. firmware_agent  — Takes decomposed_tasks, returns Arduino .ino code string
4. sourcing_agent  — Takes decomposed_tasks, returns parts_list JSON array
5. sim_verifier    — Takes stl_path, returns sim_passed bool + sim_screenshot path

## Parallelism
cad_agent, firmware_agent, and sourcing_agent all run in parallel after decompose.
sim_verifier runs after all three complete (fan-in).

## Self-correction loop
If sim_verifier returns sim_passed=False AND retry_count < 3,
route back to cad_agent with an updated constraint in state["cad_constraint"].
Otherwise proceed to END.

## Key files to edit when making changes
- graph/state.py        — Add new state fields here
- graph/graph.py        — Change routing logic here
- graph/nodes/*.py      — Individual agent logic here
- utils/gemini_client.py — Change models or add retry here
