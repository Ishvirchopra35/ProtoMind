# Autonomous Prototyper

Autonomous Prototyper is a LangGraph-driven hardware pipeline that turns one natural-language prompt into:

- OpenSCAD geometry and a compiled STL
- Arduino firmware
- A sourced parts list with pricing links
- A PyBullet stability verification artifact
- A Streamlit dashboard that shows the pipeline live

## Stack

- Python 3.11+
- LangGraph
- Gemini API
- Streamlit
- PyBullet
- OpenSCAD CLI

## Run

```bash
pip install -r requirements.txt
cp .env.example .env
streamlit run app.py
```

Install OpenSCAD separately if you want live STL compilation:

- macOS: `brew install openscad`
- Ubuntu: `sudo apt install openscad`
- Windows: install from [openscad.org](https://openscad.org)

The sidebar includes a demo mode that loads `mock_specs/turret_spec.json` and skips API calls.
