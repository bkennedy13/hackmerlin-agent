# HackMerlin Agent

An autonomous agent built in Python to play [hackmerlin.io](https://hackmerlin.io).  
The agent uses a mix of deterministic heuristics and a lightweight local LLM (3B) to solve multiple levels.

## How It Works
- **Browser automation:** `merlin_interface.py` (Selenium) sends questions, captures responses, and submits passwords.  
- **Strategies:** `hardcoded_strategies.py` defines question types (direct, spelling, reverse, fragments, acronyms).  
- **Strategy manager:** `strategy_manager.py` rotates strategies, drops failed ones, and avoids repeats.  
- **LLM + heuristics:** `llm_analyzer.py` extracts candidate passwords via regex, spellcheck, or small LLM calls.  
- **Memory:** `letter_clues_manager.py` stores fragments and stitches them together for later levels.  
- **Controller:** `hackmerlin_agent.py` orchestrates everything and tracks results.

## Requirements
- Python 3.9+  
- Chrome + ChromeDriver  
- Packages: `selenium`, `requests`, `pyspellchecker` (see `requirements.txt`)

## Usage
```bash
# Install dependencies
pip install -r requirements.txt

# Run the agent
python hackmerlin_agent.py
