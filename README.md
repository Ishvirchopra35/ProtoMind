# ProtoMind

An autonomous multi-agent hardware prototyping system that turns one natural-language idea into CAD, firmware, sourcing, and simulation outputs.

## Overview

ProtoMind goes beyond a single code-generation script. It runs a LangGraph-based pipeline that decomposes a device concept, generates OpenSCAD geometry, writes Arduino firmware, sources parts with Canadian pricing, and verifies stability with a simulation check.

Built as a Python AI engineering app with both Streamlit and ReactPy/FastAPI frontends.

## Screenshots

<div align="center">

**Landing Page**

<img width="3020" height="1722" alt="image" src="https://github.com/user-attachments/assets/34e179a9-4a5e-4592-9d83-c3b267532dd8" />

**Pipeline Dashboard**

<img width="3014" height="1720" alt="image" src="https://github.com/user-attachments/assets/76bad698-b043-4439-84a2-c35eb2917654" />

**Simulation Output**

<img width="1616" height="1570" alt="image" src="https://github.com/user-attachments/assets/5ba22466-71a1-4e92-b9cc-fdd109a0bc6c" />

</div>

## Features

- **Natural Language to Full Prototype Pack** - enter one build prompt and generate CAD, firmware, parts, and verification artifacts
- **LangGraph Agent Pipeline** - orchestrated flow across `decompose`, `cad`, `firmware`, `sourcing`, and `sim_verify` stages
- **Parallel Agent Execution** - CAD, firmware, and sourcing run in parallel after decomposition to reduce total latency
- **CAD Generation + Compilation** - OpenSCAD code generation with optional STL compilation through OpenSCAD CLI
- **Auto CAD Repair Pass** - if OpenSCAD compilation fails, a corrective LLM pass attempts to fix syntax automatically
- **Arduino Firmware Generation** - outputs ready-to-flash `.ino` code with pin definitions, setup/loop logic, and edge-case handling
- **Smart Parts Sourcing** - search-grounded pricing via Gemini tool use with structured JSON output saved to `outputs/parts_list.json`
- **Pricing Fallback Strategy** - if search pricing fails, fallback estimation prompts still produce usable CAD prices
- **Simulation Verification** - geometric stability checks at 15, 30, and 45 degree tilt with a saved visual result image
- **Self-Correcting Retry Loop** - simulation failures route back into CAD generation up to 3 retries with tighter constraints
- **Dual UI Modes** - run either Streamlit (`app.py`) or ReactPy/FastAPI (`frontend.py`) interfaces
- **Demo Mode** - Streamlit sidebar can load `mock_specs/turret_spec.json` and skip live API calls

## Tech Stack

- **Language:** Python 3.11+
- **Orchestration:** LangGraph, LangChain
- **AI:** Google Gemini (`google-genai`, `langchain-google-genai`)
- **Frontend:** Streamlit, ReactPy, FastAPI
- **Simulation / Math:** NumPy, Matplotlib
- **Runtime / Infra:** Uvicorn, Docker, Render
- **Reliability:** Tenacity (retry with exponential backoff)

## Architecture

```text
User Prompt
	-> LangGraph State Machine
		-> Decompose Agent
		-> (Parallel) CAD Agent + Firmware Agent + Sourcing Agent
		-> Simulation Verifier
		-> Conditional Retry (CAD) if unstable, max 3 attempts
	-> Artifacts in outputs/
```

## Output Schema

```text
outputs/
  turret.scad
  turret.stl                 (if OpenSCAD is installed and compile succeeds)
  firmware.ino
  parts_list.json
  sim_screenshot.png
```

## Getting Started

### Prerequisites

- Python 3.11+
- Google AI Studio API key
- OpenSCAD CLI (optional, but required for STL compilation)

### Installation

```bash
git clone https://github.com/<your-username>/ProtoMind.git
cd ProtoMind
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_ai_studio_api_key_here
```

### Run Locally

Streamlit UI:

```bash
streamlit run app.py
```

ReactPy + FastAPI UI:

```bash
python frontend.py
```

Open `http://localhost:8501` for Streamlit or `http://localhost:8000` for ReactPy/FastAPI.

## Pipeline Logic

```text
1) Decompose prompt into structured hardware spec
2) Run CAD, firmware, and sourcing in parallel
3) Verify geometric stability from STL
4) If unstable and retries < 3, feed failure reason back into CAD constraints
5) Finish and persist artifacts to outputs/
```

If STL is unavailable, simulation is skipped gracefully and the pipeline continues.

## Deployment

This project includes container deployment support:

- `Dockerfile` for containerized runtime
- `render.yaml` for Render web service deployment

Example Render service uses Docker runtime and expects `GOOGLE_API_KEY` in environment settings.

## Roadmap

- [ ] Add direct STL/mesh preview inside the UI
- [ ] Add BOM export to CSV/Google Sheets
- [ ] Add firmware unit checks and compile validation
- [ ] Add cost optimization suggestions by budget target
- [ ] Add multi-provider sourcing (Amazon + DigiKey + Mouser)
- [ ] Add hardware-in-the-loop test support

## License

This project is open source and available for educational and prototyping purposes.

---

**Authors:** Ishvir Singh Chopra and Nikhil Mohan
