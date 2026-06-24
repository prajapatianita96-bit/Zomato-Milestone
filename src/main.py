"""
main.py
───────
Entry point and pipeline orchestrator for the Zomato AI
Restaurant Recommendation System.

Wires together all 6 components in the correct sequence:
  DataLoader → InputHandler → FilterEngine →
  PromptBuilder → LLMEngine → OutputRenderer

Architecture Reference: architecture.md §3 (Data Flow)
Implementation Phase:   Phase 5 (full wiring)

Usage:
    python src/main.py
    python src/main.py --plain        # disable emoji/unicode
    python src/main.py --location Delhi --budget medium --cuisine "north indian" --rating 4.0
"""

import sys
import os
import logging
import argparse

# Add parent directory to python path so 'src' imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Python version guard (EC-SYS-02) ─────────────────────────────
if sys.version_info < (3, 10):
    raise SystemExit(
        f"❌ Python 3.10+ is required. "
        f"Current version: {sys.version_info.major}.{sys.version_info.minor}. "
        f"Please upgrade your Python installation."
    )

# ── Imports ───────────────────────────────────────────────────────
from dotenv import load_dotenv
import yaml


def load_config(config_path: str = "config/config.yaml") -> dict:
    """
    Load and return the YAML configuration file.

    Falls back to DEFAULT_CONFIG if the file is missing or malformed. (EC-SYS-04)

    Args:
        config_path (str): Path to config.yaml.

    Returns:
        dict: Parsed configuration dictionary.
    """
    DEFAULT_CONFIG = {
        "llm": {
            "provider": "groq",
            "model": "llama-3.1-8b-instant",
            "temperature": 0.4,
            "max_tokens": 1024,
            "retry_limit": 3,
            "request_timeout": 30,
        },
        "dataset": {
            "source": "ManikaSaini/zomato-restaurant-recommendation",
            "cache_path": "data/zomato_dataset.pkl",
            "cache_ttl_hours": 24,
            "max_filter_results": 20,
            "min_result_threshold": 5,
        },
        "budget_tiers": {
            "low":    {"min": 0,    "max": 500},
            "medium": {"min": 501,  "max": 1200},
            "high":   {"min": 1201, "max": 99999},
        },
        "input": {
            "max_extra_preferences_length": 200,
            "rating_min": 0.0,
            "rating_max": 5.0,
            "default_rating": 3.0,
            "default_budget": "medium",
            "fuzzy_match_cutoff": 0.6,
        },
        "prompt": {
            "max_prompt_tokens": 3000,
            "token_estimate_divisor": 4,
            "max_restaurants_in_prompt": 10,
        },
        "output": {
            "max_display_chars": 1500,
            "max_restaurant_name_length": 40,
            "save_response_path": "output/last_response.txt",
        },
        "logging": {
            "level": "INFO",
            "log_to_file": False,
            "log_file_path": "logs/app.log",
        },
    }

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            logging.info(f"✅ Config loaded from {config_path}")
            return config
    except FileNotFoundError:
        logging.warning(f"⚠️  Config file not found at '{config_path}'. Using default configuration.")
        return DEFAULT_CONFIG
    except yaml.YAMLError as e:
        logging.warning(f"⚠️  Config file is malformed: {e}. Using default configuration.")
        return DEFAULT_CONFIG


def check_environment() -> None:
    """
    Validate that all required environment variables are set. (EC-SYS-03)

    Raises:
        SystemExit: If any required env variable is missing.
    """
    REQUIRED_ENV = ["GROQ_API_KEY"]
    missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
    if missing:
        raise SystemExit(
            f"❌ Missing required environment variables: {missing}\n"
            f"   Please set them in your .env file and try again."
        )


def setup_logging(config: dict) -> None:
    """
    Configure logging based on settings in config.yaml.

    Args:
        config (dict): Parsed configuration dictionary.
    """
    log_config = config.get("logging", {})
    level_str = log_config.get("level", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_config.get("log_to_file", False):
        log_path = log_config.get("log_file_path", "logs/app.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def parse_args() -> argparse.Namespace:
    """
    Parse optional CLI arguments for non-interactive mode.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="🍽️  Zomato AI Restaurant Recommendation System"
    )
    parser.add_argument("--location",  type=str,   help="City/area (e.g., Delhi)")
    parser.add_argument("--budget",    type=str,   help="Budget: low / medium / high")
    parser.add_argument("--cuisine",   type=str,   help="Cuisine type (e.g., 'North Indian')")
    parser.add_argument("--rating",    type=float, help="Minimum rating (0.0 – 5.0)")
    parser.add_argument("--extra",     type=str,   default="", help="Additional preferences")
    parser.add_argument("--plain",     action="store_true",    help="Disable emoji/unicode output")
    return parser.parse_args()


def get_recommendations(preferences: dict, config: dict) -> list:
    """
    Programmatic entry point for the API backend.
    Returns recommendations as a structured list of dictionaries.
    """
    from src.data_loader import DataLoader
    from src.filter_engine import FilterEngine
    from src.prompt_builder import PromptBuilder
    from src.llm_engine import LLMEngine
    from src.input_handler import InputHandler
    import json
    import pandas as pd
    
    logging.info("Starting programmatic recommendation pipeline...")
    
    # 1. Load data
    loader = DataLoader(config)
    df = loader.load()

    # 1.5 Validate input
    handler = InputHandler(df["location"].unique(), df["cuisines"].unique(), config)
    valid_prefs = handler.validate(preferences)

    # 2. Filter
    engine = FilterEngine(df, config)
    filtered = engine.filter(valid_prefs)

    if filtered.empty:
        return []

    # 3. LLM
    builder = PromptBuilder(config)
    prompt = builder.build(valid_prefs, filtered)

    llm = LLMEngine(config)
    response = llm.generate(prompt)

    if response:
        try:
            return json.loads(response)
        except Exception as e:
            logging.error(f"Failed to parse LLM JSON in get_recommendations: {e}")
            
    # 4. Fallback if LLM fails
    logging.warning("Falling back to raw ratings for API response.")
    top_5 = filtered.sort_values(by="aggregate_rating", ascending=False).head(5)
    fallback = []
    for _, row in top_5.iterrows():
        fallback.append({
            "name": str(row.get("name", "Unknown")),
            "cuisine": str(row.get("cuisines", "N/A")),
            "rating": str(row.get("aggregate_rating", "N/A")),
            "cost": str(row.get("cost_for_two", "N/A")),
            "explanation": "Recommended based on overall rating (Fallback)."
        })
    return fallback


def run_pipeline(config: dict, args: argparse.Namespace) -> None:
    """
    Execute the full recommendation pipeline.

    Pipeline:
      1. DataLoader  → clean DataFrame
      2. InputHandler → validated preferences
      3. FilterEngine → filtered restaurant list
      4. PromptBuilder → LLM prompt string
      5. LLMEngine → ranked recommendations text
      6. OutputRenderer → formatted display

    Args:
        config (dict):              Parsed configuration.
        args   (argparse.Namespace): CLI arguments.
    """
    from src.data_loader import DataLoader
    from src.input_handler import InputHandler
    from src.filter_engine import FilterEngine
    from src.prompt_builder import PromptBuilder
    from src.llm_engine import LLMEngine
    from src.output_renderer import OutputRenderer

    logging.info("Starting Zomato AI Recommendation Pipeline...")

    try:
        # 1. Load & preprocess dataset
        loader = DataLoader(config)
        df = loader.load()

        # 2. Collect user preferences
        handler = InputHandler(df["location"].unique(), df["cuisines"].unique(), config)
        if args.location and args.budget and args.cuisine and args.rating is not None:
            # Non-interactive CLI mode
            preferences = {
                "location": args.location,
                "budget": args.budget,
                "cuisine": args.cuisine,
                "min_rating": args.rating,
                "extra_preferences": args.extra
            }
        else:
            # Interactive CLI mode
            preferences = handler.collect_from_cli()

        # 3. Filter restaurants
        engine = FilterEngine(df, config)
        filtered = engine.filter(preferences)

        # 4. Build LLM prompt
        builder = PromptBuilder(config)
        prompt = builder.build(preferences, filtered)

        # 5. Call LLM
        if filtered.empty:
            logging.info("No restaurants matched criteria. Skipping LLM generation.")
            response = None
        else:
            llm = LLMEngine(config)
            response = llm.generate(prompt)

        # 6. Render output
        renderer = OutputRenderer(config, plain_mode=args.plain)
        renderer.render(response, fallback_df=filtered)

    except Exception as e:
        logging.error(f"Pipeline error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # 1. Load .env
    load_dotenv()

    # 2. Parse CLI args
    args = parse_args()

    # 3. Load config (with fallback)
    config = load_config()

    # 4. Configure logging
    setup_logging(config)

    # 5. Validate environment
    check_environment()

    # 6. Run the pipeline
    run_pipeline(config, args)
