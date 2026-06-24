# Architecture: AI-Powered Restaurant Recommendation System

> **Based on**: [`context.md`](file:///d:/Zomato-Milestone/Docs/context.md) · [`Problemstatement.txt`](file:///d:/Zomato-Milestone/Docs/Problemstatement.txt)

---

## 1. High-Level Architecture Overview

The system follows a **layered pipeline architecture** with five distinct stages that transform raw restaurant data and raw user preferences into personalized, AI-generated recommendations.

```
┌────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE LAYER                        │
│               (CLI / Web UI / Notebook Interface)                  │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ User Preferences
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                        INPUT HANDLER                               │
│         Validate & Normalize: Location, Budget, Cuisine,           │
│         Minimum Rating, Additional Preferences                     │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ Structured Preference Object
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                        FILTER ENGINE                               │
│      Query In-Memory / Pandas DataFrame for matching restaurants   │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ Filtered Restaurant Records
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                       PROMPT BUILDER                               │
│     Compose structured LLM prompt with context + user intent       │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ LLM Prompt String
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                        LLM ENGINE                                  │
│     Call LLM API (e.g., Groq)                                     │
│     Rank restaurants & generate explanations                       │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ Ranked Recommendations + Explanations
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                      OUTPUT RENDERER                               │
│     Format and display: Name, Cuisine, Rating, Cost, AI Summary    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component-Level Architecture

### 2.1 Data Loader

| Attribute | Detail |
|---|---|
| **Responsibility** | Fetch, load, and preprocess the Zomato dataset |
| **Data Source** | Hugging Face — `ManikaSaini/zomato-restaurant-recommendation` |
| **Library** | `datasets` (Hugging Face), `pandas` |
| **Output** | Cleaned `DataFrame` stored in memory |

**Sub-tasks:**
- Download dataset via `datasets.load_dataset()`
- Convert to `pandas.DataFrame`
- Drop null/incomplete rows for critical fields
- Normalize text fields (lowercase location, cuisine)
- Map cost columns to budget tiers: `Low / Medium / High`
- Cache preprocessed data to avoid re-loading on each run

**Key Fields Extracted:**

| Field | Description |
|---|---|
| `name` | Restaurant name |
| `location` / `city` | City or area of the restaurant |
| `cuisines` | Comma-separated cuisine types |
| `cost_for_two` | Approximate cost for two people |
| `aggregate_rating` | Overall rating (0–5 scale) |
| `votes` | Number of user votes |
| `highlights` | Tags like "Family-friendly", "Quick bites" |

---

### 2.2 Input Handler

| Attribute | Detail |
|---|---|
| **Responsibility** | Collect, validate, and normalize user preferences |
| **Interface** | CLI prompts / Web form / Function arguments |
| **Output** | A structured `UserPreferences` object / dict |

**Accepted Inputs:**

| Parameter | Type | Example | Validation |
|---|---|---|---|
| `location` | `str` | `"Delhi"` | Must match known cities in dataset |
| `budget` | `str` | `"medium"` | One of `low`, `medium`, `high` |
| `cuisine` | `str` | `"Italian"` | Fuzzy-matched against dataset values |
| `min_rating` | `float` | `4.0` | Range: `0.0 – 5.0` |
| `extra_preferences` | `str` | `"family-friendly"` | Free text, passed to LLM as context |

**Validation Rules:**
- Unrecognized locations fall back to a closest-match warning
- Budget strings normalized to lowercase
- Rating clamped to `[0.0, 5.0]`

---

### 2.3 Filter Engine

| Attribute | Detail |
|---|---|
| **Responsibility** | Query the dataset based on validated user preferences |
| **Library** | `pandas` |
| **Output** | List of up to N matching restaurant records (default: top 20) |

**Filtering Logic:**

```
filtered = dataset
  WHERE location CONTAINS user.location (case-insensitive)
  AND   budget_tier == user.budget
  AND   cuisines CONTAINS user.cuisine (partial match)
  AND   aggregate_rating >= user.min_rating
ORDER BY aggregate_rating DESC, votes DESC
LIMIT 20
```

**Fallback Strategy:**
- If result set < 5 records → relax budget constraint
- If result set still < 5 → relax cuisine constraint
- Always return at least 3 restaurants if data exists for the location

---

### 2.4 Prompt Builder

| Attribute | Detail |
|---|---|
| **Responsibility** | Convert filtered records + user preferences into an LLM prompt |
| **Output** | A formatted string (the LLM prompt) |

**Prompt Template Structure:**

```
System Role:
  "You are an expert restaurant recommendation assistant.
   Analyze the following restaurants and recommend the top 3–5
   that best match the user's preferences. Provide a brief
   explanation for each recommendation."

User Context Block:
  - Location: {location}
  - Budget: {budget}
  - Preferred Cuisine: {cuisine}
  - Minimum Rating: {min_rating}
  - Additional Preferences: {extra_preferences}

Restaurant Data Block:
  [Numbered list of filtered restaurants with fields:
   Name, Cuisine, Rating, Cost, Votes, Highlights]

Instruction:
  "Rank the top restaurants, explain why each fits the user's
   preferences, and optionally provide a brief summary of the
   best overall choice."
```

**Design Decisions:**
- Restaurant data injected as a numbered list for easy LLM reference
- System prompt establishes expert persona to improve output quality
- Prompt is token-aware: limits restaurant list to avoid exceeding context window

---

### 2.5 LLM Engine

| Attribute | Detail |
|---|---|
| **Responsibility** | Send the prompt to an LLM API and retrieve the recommendation response |
| **Supported LLMs** | Groq (`llama3-8b-8192` or similar) |
| **Library** | `groq` SDK |
| **Output** | Raw LLM text response (ranked recommendations + explanations) |

**API Call Flow:**

```
1. Initialize LLM client with API key
2. Set temperature = 0.4 (balanced creativity vs. accuracy)
3. Send system prompt + user prompt
4. Receive and return raw text response
5. Handle API errors / retries (max 3 attempts)
```

**Configuration Parameters:**

| Parameter | Value | Purpose |
|---|---|---|
| `temperature` | `0.4` | Controlled, consistent output |
| `max_tokens` | `1024` | Sufficient for top-5 recommendations |
| `model` | `llama3-8b-8192` | Primary LLM |
| `retry_limit` | `3` | Resilience against transient failures |

---

### 2.6 Output Renderer

| Attribute | Detail |
|---|---|
| **Responsibility** | Parse and display LLM response in a structured, readable format |
| **Output** | Formatted console output / JSON / UI-rendered cards |

**Output Format per Recommendation:**

```
╔══════════════════════════════════════════════╗
║  🏆 Recommendation #1                        ║
╠══════════════════════════════════════════════╣
║  🍽️  Name        : Spice Garden              ║
║  🍜  Cuisine     : North Indian              ║
║  ⭐  Rating      : 4.5 / 5.0                ║
║  💰  Est. Cost   : ₹800 for two             ║
║  🤖  AI Summary  : "Perfect for a family    ║
║                    dinner with authentic    ║
║                    North Indian flavors..." ║
╚══════════════════════════════════════════════╝
```

---

### 2.7 Presentation Layer (Phase 6)

| Attribute | Detail |
|---|---|
| **Responsibility** | Serve an end-to-end web UI and process HTTP requests |
| **Technology** | FastAPI (Backend) serving HTML/CSS/JS (Frontend) |
| **Output** | Interactive web interface |

**Key Features:**
- A dark-mode, glassmorphic UI matching modern aesthetic standards.
- Form inputs mapped to `UserPreferences` schema.
- Dynamic rendering of LLM responses using smooth animations and cards.

---

### 2.8 Hardening & Ship (Phase 7)

| Attribute | Detail |
|---|---|
| **Responsibility** | Testing, documentation, and ensuring a demo-ready application |
| **Outputs** | Expanded unit/integration tests, final `README.md`, stable deployment |

**Key Focus Areas:**
- Complete end-to-end testing of the FastAPI endpoints and UI.
- Finalize documentation to ensure easy onboarding for stakeholders.

## 3. Data Flow Diagram

```
[Hugging Face Dataset]
        │
        ▼
  ┌─────────────┐
  │ Data Loader │ ──► Cleaned DataFrame (in-memory)
  └─────────────┘
                              │
              [User provides preferences]
                              │
                    ┌──────────────────┐
                    │  Input Handler   │ ──► UserPreferences object
                    └──────────────────┘
                              │
                    ┌──────────────────┐
                    │  Filter Engine   │ ──► Filtered Restaurant List (≤20)
                    └──────────────────┘
                              │
                    ┌──────────────────┐
                    │  Prompt Builder  │ ──► LLM Prompt String
                    └──────────────────┘
                              │
                    ┌──────────────────┐
                    │   LLM Engine     │ ──► Raw LLM Response
                    └──────────────────┘
                              │
                    ┌──────────────────┐
                    │ Output Renderer  │ ──► Formatted Recommendations (JSON/Text)
                    └──────────────────┘
                               │
                    ┌──────────────────┐
                    │    Web UI        │ ──► Displayed to User in Browser
                    └──────────────────┘
```

---

## 4. Module & File Structure

```
zomato-recommendation/
│
├── data/
│   └── zomato_dataset.pkl          # Cached preprocessed dataset
│
├── src/
│   ├── data_loader.py              # DataLoader class
│   ├── input_handler.py            # InputHandler class
│   ├── filter_engine.py            # FilterEngine class
│   ├── prompt_builder.py           # PromptBuilder class
│   ├── llm_engine.py               # LLMEngine class
│   ├── output_renderer.py          # OutputRenderer class
│   ├── api.py                      # FastAPI application
│   └── main.py                     # Orchestrator / entry point
│
├── frontend/                       # Web UI Assets (Phase 6)
│   ├── index.html                  # Main UI structure
│   ├── style.css                   # Premium dark mode aesthetics
│   └── app.js                      # UI logic and API calls
│
├── config/
│   └── config.yaml                 # LLM model, API keys, thresholds
│
├── Docs/
│   ├── Problemstatement.txt
│   ├── context.md
│   └── architecture.md             # ← This file
│
├── tests/
│   ├── test_data_loader.py
│   ├── test_filter_engine.py
│   └── test_prompt_builder.py
│
├── requirements.txt
└── README.md
```

---

## 5. Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Dataset Loading | `datasets` (Hugging Face), `pandas` |
| Data Processing | `pandas`, `numpy` |
| LLM Integration | `groq` |
| Config | `PyYAML` / `python-dotenv` |
| Testing | `pytest` |
| Interface | Web UI (FastAPI static files, HTML/CSS/JS) & CLI (`argparse`) |

---

## 6. Key Design Decisions

| Decision | Rationale |
|---|---|
| In-memory DataFrame over a database | Dataset is small enough; avoids infrastructure overhead |
| Pandas for filtering | Simple, expressive queries; no SQL setup required |
| Prompt-based LLM ranking | LLMs excel at contextual reasoning vs. rule-based ranking |
| Temperature = 0.4 | Balances creativity with factual consistency |
| Fallback relaxation in Filter Engine | Ensures user always gets a result even with strict criteria |
| Modular class-per-component design | Each component is independently testable and replaceable |

---

## 7. Error Handling Strategy

| Scenario | Handling |
|---|---|
| Dataset fails to load | Raise descriptive error; suggest checking internet / credentials |
| No restaurants match filters | Relax constraints progressively; notify user of relaxation |
| LLM API failure | Retry up to 3 times with exponential backoff; fallback to raw list |
| Invalid user input | Validate upfront with clear error messages before processing |
| Empty LLM response | Display filtered list directly with a warning |

---

## 8. Scalability Considerations

- **Dataset Growth**: Replace in-memory DataFrame with a vector database (e.g., FAISS, ChromaDB) for semantic search at scale
- **Multi-user**: Wrap in a REST API (FastAPI) for concurrent requests
- **LLM Costs**: Cache repeated identical queries using a hash of the preference object
- **Streaming Output**: Use LLM streaming APIs for real-time response display

---

## References

- [context.md](file:///d:/Zomato-Milestone/Docs/context.md)
- [Problemstatement.txt](file:///d:/Zomato-Milestone/Docs/Problemstatement.txt)
- [Hugging Face Dataset](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation)
