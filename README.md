# 🍽️ Zomato AI Restaurant Recommendation System

An AI-powered restaurant recommendation service that combines a real-world Zomato dataset with a Large Language Model (LLM) to deliver personalized, human-like restaurant suggestions.

---

## 📋 Project Documents

| Document | Description |
|---|---|
| [`Docs/Problemstatement.txt`](Docs/Problemstatement.txt) | Original problem statement |
| [`Docs/context.md`](Docs/context.md) | Project context and overview |
| [`Docs/architecture.md`](Docs/architecture.md) | System architecture and component design |
| [`Docs/implementation_plan.md`](Docs/implementation_plan.md) | Phase-wise implementation plan |
| [`Docs/edge_cases.md`](Docs/edge_cases.md) | Edge case handling guide |

---

## 🗂️ Project Structure

```
zomato-recommendation/
│
├── data/                       # Auto-generated dataset cache
├── output/                     # Saved LLM responses
├── src/
│   ├── data_loader.py          # Fetch & preprocess Zomato dataset
│   ├── input_handler.py        # Collect & validate user preferences
│   ├── filter_engine.py        # Query dataset based on preferences
│   ├── prompt_builder.py       # Build structured LLM prompt
│   ├── llm_engine.py           # Call Gemini/OpenAI API
│   ├── output_renderer.py      # Display formatted recommendations
│   └── main.py                 # Pipeline orchestrator
├── config/
│   └── config.yaml             # All tuneable parameters
├── tests/                      # Unit tests per component
├── Docs/                       # Project documentation
├── .env                        # API keys (not committed)
├── .gitignore
└── requirements.txt
```

---

## ⚙️ Setup Instructions

### 1. Prerequisites
- Python 3.10 or higher
- A Groq API key ([get one here](https://console.groq.com/keys))

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API Keys

Edit the `.env` file and add your key:

```env
GROQ_API_KEY=your_actual_api_key_here
```

### 4. (Optional) Adjust Settings

Edit `config/config.yaml` to change the LLM model, budget tiers, filter limits, etc.

---

## 🚀 Running the System

### Interactive Mode (CLI prompts)

```bash
python src/main.py
```

### Non-Interactive Mode (pass arguments)

```bash
python src/main.py --location Delhi --budget medium --cuisine "north indian" --rating 4.0
```

### Plain Terminal Mode (no emoji/unicode)

```bash
python src/main.py --plain
```

### Sample Output

```text
╔══════════════════════════════════════════════════════════╗
║        🍽️  ZOMATO AI RESTAURANT RECOMMENDATIONS        ║
╚══════════════════════════════════════════════════════════╝

Based on your preferences, here are the top recommendations:

1. **Spice Garden**
   - **Cuisine:** North Indian
   - **Rating:** 4.5 ⭐ (120 votes)
   - **Cost:** ₹800 for two
   This fits your preferences perfectly!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

With coverage report:

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## 🔄 System Pipeline

```
User Input → InputHandler → FilterEngine → PromptBuilder → LLMEngine → OutputRenderer
                ↑
           DataLoader (Hugging Face dataset)
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Dataset | Hugging Face `datasets` + `pandas` |
| LLM | Groq API (`llama-3.1-8b-instant`) |
| Config | `PyYAML` + `python-dotenv` |
| Testing | `pytest` + `pytest-cov` |

---

## 📊 Implementation Status

| Phase | Focus | Status |
|---|---|---|
| Phase 1 | Project Setup & Environment | ✅ Complete |
| Phase 2 | Data Ingestion & Preprocessing | ✅ Complete |
| Phase 3 | User Input & Filter Engine | ✅ Complete |
| Phase 4 | LLM Integration & Prompt Design | ✅ Complete |
| Phase 5 | Output Display & Integration | ✅ Complete |

---

## 📄 Dataset

**Source**: [ManikaSaini/zomato-restaurant-recommendation](https://huggingface.co/datasets/ManikaSaini/zomato-restaurant-recommendation) on Hugging Face

Key fields used: `name`, `location`, `cuisines`, `cost_for_two`, `aggregate_rating`, `votes`, `highlights`
