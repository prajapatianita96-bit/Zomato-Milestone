import os
import sys
from dotenv import load_dotenv

# Add src to python path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.llm_engine import LLMEngine
from src.prompt_builder import PromptBuilder
import pandas as pd

def test_llm_call():
    load_dotenv(override=True)
    api_key = os.getenv("GROQ_API_KEY", "")
    print(f"Loaded API Key (first 5 chars): '{api_key[:5]}...'")
    
    config = {
        "llm": {
            "provider": "groq",
            "model": "llama-3.1-8b-instant",
            "temperature": 0.4,
            "max_tokens": 1024,
            "retry_limit": 1,
            "request_timeout": 30,
        },
        "prompt": {
            "max_prompt_tokens": 3000,
            "token_estimate_divisor": 4,
            "max_restaurants_in_prompt": 10
        }
    }
    
    # 1. Dummy Preferences & Restaurants
    preferences = {
        "location": "delhi",
        "budget": "medium",
        "cuisine": "north indian",
        "min_rating": 4.0,
        "extra_preferences": "romantic atmosphere"
    }
    
    restaurants = pd.DataFrame({
        "name": ["Spice Garden"],
        "location": ["delhi"],
        "cuisines": ["North Indian"],
        "aggregate_rating": [4.5],
        "votes": [120],
        "cost_for_two": [800],
        "budget_tier": ["medium"],
        "highlights": ["Romantic Seating, Live Music"]
    })
    
    # 2. Build Prompt
    print("Building prompt...")
    builder = PromptBuilder(config)
    prompt = builder.build(preferences, restaurants)
    print(f"Prompt built successfully. Length: {len(prompt)} chars.")
    
    # 3. Call LLM
    print("Calling Groq API...")
    engine = LLMEngine(config)
    response = engine.generate(prompt)
    
    print("\n" + "="*50)
    print("LLM RESPONSE:")
    print("="*50)
    if response:
        print(response)
    else:
        print("❌ Failed to get a response from the LLM.")
    print("="*50)

if __name__ == "__main__":
    test_llm_call()
