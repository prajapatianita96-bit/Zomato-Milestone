# Phase-Wise Implementation Plan
## AI-Powered Restaurant Recommendation System (Zomato Use Case)

> **References**: [`architecture.md`](file:///d:/Zomato-Milestone/Docs/architecture.md) · [`context.md`](file:///d:/Zomato-Milestone/Docs/context.md) · [`Problemstatement.txt`](file:///d:/Zomato-Milestone/Docs/Problemstatement.txt)

---

## Overview

This plan breaks the project into **5 sequential phases**, each building on the previous, following the pipeline architecture defined in `architecture.md`. Each phase has clear goals, tasks, deliverables, and a definition of done.

| Phase | Name | Focus Area | Est. Effort |
|---|---|---|---|
| **Phase 1** | Project Setup & Environment | Infrastructure & scaffolding | ~0.5 day |
| **Phase 2** | Data Ingestion & Preprocessing | DataLoader component | ~1 day |
| **Phase 3** | User Input & Filter Engine | InputHandler + FilterEngine | ~1 day |
| **Phase 4** | LLM Integration & Prompt Design | PromptBuilder + LLMEngine | ~1–2 days |
| **Phase 5** | Output Display & End-to-End Testing | OutputRenderer + Integration | ~1 day |
| **Phase 6** | Presentation Layer | End-to-end UI for users | ~2 days |
| **Phase 7** | Hardening & Ship | Tests, Docs, Demo-ready app | ~1 day |

---

## Phase 1 — Project Setup & Environment

### Goal
Establish the project structure, install all dependencies, and configure credentials so every subsequent phase has a clean working foundation.

### Tasks

#### 1.1 Initialize Project Structure
Create the following directory layout as defined in `architecture.md §4`:

```
zomato-recommendation/
├── data/
├── src/
├── config/
├── Docs/
├── tests/
├── requirements.txt
└── README.md
```

#### 1.2 Create `requirements.txt`

```txt
# Data
datasets>=2.18.0
pandas>=2.0.0
numpy>=1.26.0

# LLM
groq>=0.4.2

# Config & Env
python-dotenv>=1.0.0
PyYAML>=6.0

# Testing
pytest>=8.0.0
```

#### 1.3 Create `config/config.yaml`

```yaml
llm:
  provider: groq
  model: llama3-8b-8192
  temperature: 0.4
  max_tokens: 1024
  retry_limit: 3

dataset:
  source: ManikaSaini/zomato-restaurant-recommendation
  cache_path: data/zomato_dataset.pkl
  max_filter_results: 20
  min_result_threshold: 5

budget_tiers:
  low: [0, 500]
  medium: [501, 1200]
  high: [1201, 99999]
```

#### 1.4 Create `.env` File

```env
GROQ_API_KEY=your_groq_api_key_here
```

#### 1.5 Install Dependencies

```bash
pip install -r requirements.txt
```

#### 1.6 Create `src/__init__.py` and empty module stubs

Create placeholder files for each module:
- `src/data_loader.py`
- `src/input_handler.py`
- `src/filter_engine.py`
- `src/prompt_builder.py`
- `src/llm_engine.py`
- `src/output_renderer.py`
- `src/main.py`

### Deliverables
- [ ] Full directory structure created
- [ ] `requirements.txt` installed successfully
- [ ] `config/config.yaml` configured
- [ ] `.env` with valid API key
- [ ] All `src/` module stubs created

### Definition of Done
> `python -c "import pandas, datasets, google.generativeai"` runs without errors.

---

## Phase 2 — Data Ingestion & Preprocessing

### Goal
Implement the `DataLoader` component that fetches, cleans, and caches the Zomato dataset from Hugging Face, producing a clean `pandas.DataFrame` ready for filtering.

### Architecture Reference
> `architecture.md §2.1 — Data Loader`

### Tasks

#### 2.1 Implement `DataLoader` class in `src/data_loader.py`

```python
class DataLoader:
    def __init__(self, config: dict): ...
    def load(self) -> pd.DataFrame: ...         # Load from HF or cache
    def _download(self) -> pd.DataFrame: ...    # Fetch from Hugging Face
    def _preprocess(self, df) -> pd.DataFrame: ...  # Clean & normalize
    def _cache(self, df): ...                   # Save to .pkl
    def _load_cache(self) -> pd.DataFrame: ...  # Load from .pkl
```

#### 2.2 Preprocessing Steps (inside `_preprocess`)

| Step | Action |
|---|---|
| Drop nulls | Drop rows missing `name`, `location`, `cuisines`, `aggregate_rating`, `cost_for_two` |
| Normalize text | Lowercase `location` and `cuisines` columns |
| Map budget tiers | `cost_for_two` → `budget_tier` (`low` / `medium` / `high`) using config ranges |
| Cast types | Ensure `aggregate_rating` is `float`, `votes` is `int` |
| Strip whitespace | Clean leading/trailing spaces in all string columns |
| Reset index | `df.reset_index(drop=True)` |

#### 2.3 Fields to Retain in Final DataFrame

| Column | Source Field | Notes |
|---|---|---|
| `name` | `name` / `restaurant_name` | Restaurant name |
| `location` | `location` / `city` | Lowercase |
| `cuisines` | `cuisines` | Lowercase, comma-separated |
| `cost_for_two` | `average_cost_for_two` | Raw numeric |
| `budget_tier` | Derived | `low` / `medium` / `high` |
| `aggregate_rating` | `aggregate_rating` | Float |
| `votes` | `votes` | Int |
| `highlights` | `highlights` | Optional tags |

#### 2.4 Caching Logic

```
IF cache file exists AND file age < 24 hours:
    load from cache
ELSE:
    download from Hugging Face
    preprocess
    save to cache
```

#### 2.5 Write Unit Test — `tests/test_data_loader.py`
- Test that `load()` returns a non-empty DataFrame
- Test that required columns exist
- Test that no nulls exist in critical fields
- Test that `budget_tier` values are only `low`, `medium`, or `high`

### Deliverables
- [ ] `src/data_loader.py` fully implemented
- [ ] Dataset loads and preprocesses without errors
- [ ] Cache file created at `data/zomato_dataset.pkl`
- [ ] `tests/test_data_loader.py` passing

### Definition of Done
> `DataLoader(config).load()` returns a clean DataFrame with all required columns; unit tests pass.

---

## Phase 3 — User Input Handling & Filter Engine

### Goal
Implement the `InputHandler` (collect & validate user preferences) and `FilterEngine` (query the dataset) components, so filtered restaurant lists are produced correctly based on user criteria.

### Architecture Reference
> `architecture.md §2.2 — Input Handler` · `§2.3 — Filter Engine`

### Tasks

#### 3.1 Implement `InputHandler` in `src/input_handler.py`

```python
class InputHandler:
    def __init__(self, valid_locations: list, valid_cuisines: list): ...
    def collect_from_cli(self) -> dict: ...         # Interactive CLI prompts
    def collect_from_args(self, **kwargs) -> dict:  # Programmatic input
    def validate(self, preferences: dict) -> dict:  # Normalize & validate
```

**Validation Rules:**

| Field | Rule |
|---|---|
| `location` | Fuzzy match against known locations in dataset; warn if not found |
| `budget` | Normalize to `low` / `medium` / `high`; reject invalid values |
| `cuisine` | Partial match against known cuisines; allow `"any"` to skip filter |
| `min_rating` | Cast to float; clamp to `[0.0, 5.0]` |
| `extra_preferences` | Accept any string; default to `""` if not provided |

**Output — `UserPreferences` dict:**

```python
{
    "location": "delhi",
    "budget": "medium",
    "cuisine": "north indian",
    "min_rating": 4.0,
    "extra_preferences": "family-friendly"
}
```

#### 3.2 Implement `FilterEngine` in `src/filter_engine.py`

```python
class FilterEngine:
    def __init__(self, df: pd.DataFrame, config: dict): ...
    def filter(self, preferences: dict) -> pd.DataFrame: ...
    def _apply_strict_filter(self, prefs) -> pd.DataFrame: ...
    def _apply_relaxed_filter(self, prefs, relax_budget=False, relax_cuisine=False) -> pd.DataFrame: ...
```

**Filtering Logic (Strict → Relaxed):**

```
Step 1 (strict):
  location CONTAINS prefs.location
  AND budget_tier == prefs.budget
  AND cuisines CONTAINS prefs.cuisine
  AND aggregate_rating >= prefs.min_rating
  ORDER BY aggregate_rating DESC, votes DESC
  LIMIT 20

Step 2 (relax budget if results < 5):
  Remove budget_tier filter; repeat

Step 3 (relax cuisine if still < 5):
  Remove cuisine filter; repeat
  Log: "Relaxed cuisine filter to find more results"

Always return at least 3 results if location matches exist.
```

#### 3.3 Write Unit Tests — `tests/test_filter_engine.py`
- Test strict filter returns correct results
- Test budget relaxation triggers when results < 5
- Test cuisine relaxation triggers appropriately
- Test empty result when location doesn't exist in dataset

### Deliverables
- [ ] `src/input_handler.py` — CLI and programmatic input modes
- [ ] `src/filter_engine.py` — strict + fallback filtering logic
- [ ] Validation covers all 5 preference fields
- [ ] `tests/test_filter_engine.py` passing

### Definition of Done
> Providing sample preferences returns a non-empty, correctly filtered DataFrame; validation rejects invalid inputs with clear error messages.

---

## Phase 4 — LLM Integration & Prompt Design

### Goal
Implement the `PromptBuilder` (compose the LLM prompt from filtered data) and `LLMEngine` (call the LLM API and retrieve ranked recommendations) components.

### Architecture Reference
> `architecture.md §2.4 — Prompt Builder` · `§2.5 — LLM Engine`

### Tasks

#### 4.1 Implement `PromptBuilder` in `src/prompt_builder.py`

```python
class PromptBuilder:
    def __init__(self, config: dict): ...
    def build(self, preferences: dict, restaurants: pd.DataFrame) -> str: ...
    def _format_restaurant_list(self, df: pd.DataFrame) -> str: ...
    def _estimate_tokens(self, text: str) -> int: ...
```

**Prompt Template:**

```
SYSTEM:
You are an expert restaurant recommendation assistant with deep knowledge
of Indian dining. Given a list of restaurants and user preferences, your
task is to recommend the top 3–5 best-matching restaurants.
For each recommendation:
  1. State the restaurant name
  2. Highlight cuisine, rating, and estimated cost
  3. Provide a 2–3 sentence personalized explanation of why it fits

USER:
## My Preferences
- Location       : {location}
- Budget         : {budget}
- Preferred Cuisine: {cuisine}
- Minimum Rating : {min_rating} / 5.0
- Extra Preferences: {extra_preferences}

## Available Restaurants
{numbered_restaurant_list}

## Instructions
Please rank and recommend the top restaurants from the list above.
Explain briefly why each fits my preferences.
End with a one-line overall summary of the best choice.
```

**Restaurant List Format (per entry):**

```
{n}. {name}
   Cuisine  : {cuisines}
   Rating   : {aggregate_rating} ⭐ ({votes} votes)
   Cost     : ₹{cost_for_two} for two ({budget_tier} budget)
   Tags     : {highlights}
```

**Token Safety:**
- Estimate tokens using `len(text) / 4` heuristic
- If prompt > 3000 tokens → trim restaurant list to top 10 by rating

#### 4.2 Implement `LLMEngine` in `src/llm_engine.py`

```python
class LLMEngine:
    def __init__(self, config: dict): ...
    def generate(self, prompt: str) -> str: ...
    def _call_groq(self, prompt: str) -> str: ...
    def _retry(self, fn, retries: int) -> str: ...
```

**Groq API Integration:**

```python
import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
completion = client.chat.completions.create(
    model=config["llm"]["model"],
    messages=[
        {"role": "user", "content": prompt}
    ],
    temperature=config["llm"]["temperature"],
    max_tokens=config["llm"]["max_tokens"]
)
return completion.choices[0].message.content
```

**Retry Logic:**

```
For attempt in 1..retry_limit:
    Try: return LLM response
    On API error: wait 2^attempt seconds (exponential backoff)
    On final failure: return None
```

**Fallback Behavior (when LLM returns None):**
- Skip LLM ranking
- Return top 5 restaurants from filter results sorted by rating
- Append warning: `"⚠️ AI recommendations unavailable. Showing top-rated matches."`

#### 4.3 Write Unit Test — `tests/test_prompt_builder.py`
- Test prompt contains all user preference fields
- Test restaurant list is correctly formatted
- Test token trimming activates when input is large
- Test prompt is a non-empty string

### Deliverables
- [ ] `src/prompt_builder.py` — structured prompt generation
- [ ] `src/llm_engine.py` — Groq API call + retry + fallback
- [ ] Prompt verified to include all required sections
- [ ] `tests/test_prompt_builder.py` passing
- [ ] Live LLM call tested manually with sample data

### Definition of Done
> Given a filtered restaurant DataFrame and user preferences, the LLM returns a non-empty ranked recommendation text within 30 seconds.

---

## Phase 5 — Output Display & End-to-End Integration

### Goal
Implement the `OutputRenderer` to format and display LLM results cleanly, then wire all components together in `main.py` for a working end-to-end system.

### Architecture Reference
> `architecture.md §2.6 — Output Renderer` · `§3 — Data Flow`

### Tasks

#### 5.1 Implement `OutputRenderer` in `src/output_renderer.py`

```python
class OutputRenderer:
    def __init__(self): ...
    def render(self, llm_response: str, fallback_df: pd.DataFrame = None): ...
    def _render_llm_output(self, text: str): ...
    def _render_fallback(self, df: pd.DataFrame): ...
    def _print_header(self): ...
    def _print_divider(self): ...
```

**Console Output Format:**

```
╔══════════════════════════════════════════════════════════╗
║      🍽️  ZOMATO AI RESTAURANT RECOMMENDATIONS           ║
╚══════════════════════════════════════════════════════════╝

🏆 Recommendation #1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🍽️  Name      : Spice Garden
🍜  Cuisine   : North Indian, Mughlai
⭐  Rating    : 4.5 / 5.0
💰  Est. Cost : ₹800 for two
🤖  Why?      : "Perfect for a family dinner, Spice Garden offers
               authentic North Indian flavors within your medium
               budget with a consistently high rating."
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[... additional recommendations ...]

📝 Summary: Spice Garden stands out as the top pick for its
   exceptional rating and family-friendly atmosphere.
```

#### 5.2 Implement `main.py` — Orchestrator

```python
# main.py — Full pipeline orchestration
def run_pipeline():
    # 1. Load config
    config = load_config("config/config.yaml")

    # 2. Load & preprocess dataset
    loader = DataLoader(config)
    df = loader.load()

    # 3. Collect user preferences
    handler = InputHandler(df["location"].unique(), df["cuisines"].unique())
    preferences = handler.collect_from_cli()

    # 4. Filter restaurants
    engine = FilterEngine(df, config)
    filtered = engine.filter(preferences)

    # 5. Build LLM prompt
    builder = PromptBuilder(config)
    prompt = builder.build(preferences, filtered)

    # 6. Call LLM
    llm = LLMEngine(config)
    response = llm.generate(prompt)

    # 7. Render output
    renderer = OutputRenderer()
    renderer.render(response, fallback_df=filtered)

if __name__ == "__main__":
    run_pipeline()
```

#### 5.3 End-to-End Integration Test

Run the complete pipeline with at least **3 test scenarios**:

| # | Location | Budget | Cuisine | Min Rating | Expected Outcome |
|---|---|---|---|---|---|
| T1 | Delhi | Medium | North Indian | 4.0 | 3–5 ranked results with AI explanations |
| T2 | Bangalore | Low | Chinese | 3.5 | Results or relaxed fallback |
| T3 | InvalidCity | High | Italian | 4.5 | Graceful error: no location match |

#### 5.4 Error Handling Verification

| Scenario | Test |
|---|---|
| No internet for dataset download | Disconnect → verify cache loads |
| LLM API key invalid | Set wrong key → verify fallback list shown |
| All filters too strict | Use rating=5.0 → verify progressive relaxation |

#### 5.5 Final README Update

Document in `README.md`:
- Setup instructions (env, install)
- How to run: `python src/main.py`
- Sample output screenshot
- Configuration options in `config.yaml`

### Deliverables
- [ ] `src/output_renderer.py` — formatted console display
- [ ] `src/main.py` — full end-to-end orchestrator
- [ ] 3 integration test scenarios verified
- [ ] Error handling verified for all scenarios in `architecture.md §7`
- [ ] `README.md` updated

### Definition of Done
> Running `python src/main.py` completes the full pipeline — from dataset load to LLM-ranked output — without errors for all 3 test scenarios.

---

## Phase 6 — Presentation Layer

### Goal
Implement an end-to-end UI for users so they can interact with the recommendation system visually instead of through a CLI.

### Tasks

#### 6.1 Set Up Web Framework / UI
- Initialize the web app structure (e.g., Streamlit, or a React frontend interacting with `api.py`).
- Integrate the frontend with the existing orchestration logic.

#### 6.2 Design User Input Interface
- Create form fields for Location, Budget, Cuisine, Minimum Rating, and Extra Preferences.
- Ensure validation logic mirrors the existing `InputHandler`.

#### 6.3 Implement Results Display
- Design cards or a list view to cleanly display the LLM's ranked output.
- Show Restaurant Name, Cuisine, Rating, Cost, and the AI-generated explanation.

### Deliverables
- [ ] UI codebase fully integrated with the orchestrator or API.
- [ ] User can input preferences visually.
- [ ] Recommendations are displayed in a formatted, user-friendly UI.

### Definition of Done
> The user can launch the UI locally, input preferences, and see AI-ranked restaurant recommendations in a web browser.

---

## Phase 7 — Hardening & Ship

### Goal
Ensure the application is robust, well-documented, fully tested, and ready for a demo. 

### Tasks

#### 7.1 Comprehensive Testing
- Expand unit tests to cover UI endpoints and edge cases.
- Run end-to-end integration tests to ensure stability across the full stack.

#### 7.2 Documentation Updates
- Finalize `README.md` with instructions on how to start the UI.
- Ensure inline comments and docstrings are complete.

#### 7.3 Final Polish and Demo Prep
- Resolve any outstanding warnings or performance bottlenecks.
- Prepare a demo scenario for presentation.

### Deliverables
- [ ] Test coverage meets the target threshold.
- [ ] Documentation is up-to-date and clear.
- [ ] Application runs flawlessly in a demo environment.

### Definition of Done
> The project has passing tests, complete documentation, and is ready to be showcased to stakeholders.

---

## Completion Checklist

```
Phase 1 — Setup
  [ ] Project structure created
  [ ] Dependencies installed
  [ ] Config and .env ready

Phase 2 — Data Ingestion
  [x] DataLoader implemented
  [x] Dataset loads and preprocesses correctly
  [x] Caching working
  [x] Unit tests pass

Phase 3 — Input & Filter
  [x] InputHandler implemented (CLI + programmatic)
  [x] FilterEngine with fallback logic working
  [x] Unit tests pass

Phase 4 — LLM Integration
  [x] PromptBuilder generates valid prompts
  [x] LLMEngine calls Groq API and returns response
  [x] Retry + fallback logic working
  [x] Unit tests pass

Phase 5 — Output & Integration
  [x] OutputRenderer displays results clearly
  [x] main.py orchestrates full pipeline
  [x] 3 end-to-end test scenarios pass
  [x] README.md updated

Phase 6 — Presentation Layer
  [x] UI Framework setup
  [x] Input interface implemented
  [x] Results display integrated

Phase 7 — Hardening & Ship
  [ ] Comprehensive testing complete
  [ ] Documentation finalized
  [ ] Demo preparation
```

---

## Milestone Summary

```
Week 1
├── Day 1 (AM) — Phase 1: Setup & Scaffolding
├── Day 1 (PM) — Phase 2: DataLoader + Preprocessing
├── Day 2       — Phase 3: InputHandler + FilterEngine
├── Day 3       — Phase 4: PromptBuilder + LLMEngine
├── Day 4       — Phase 5: OutputRenderer + Integration + Testing
├── Day 5       — Phase 6: Presentation Layer
└── Day 6       — Phase 7: Hardening & Ship
```

---

## References

- [architecture.md](file:///d:/Zomato-Milestone/Docs/architecture.md)
- [context.md](file:///d:/Zomato-Milestone/Docs/context.md)
- [Problemstatement.txt](file:///d:/Zomato-Milestone/Docs/Problemstatement.txt)
- [Hugging Face Dataset](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
