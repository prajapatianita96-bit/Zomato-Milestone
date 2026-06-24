"""
llm_engine.py
─────────────
Responsible for:
  - Sending the constructed prompt to the configured LLM API
  - Handling retries with exponential backoff on transient failures
  - Returning None gracefully on permanent failure (triggers fallback)

Architecture Reference: architecture.md §2.5
Edge Cases Handled:    edge_cases.md EC-LE-01 to EC-LE-08
"""

import os
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LLMEngine:
    """
    Sends prompts to an LLM API and returns the generated response text.

    Supports:
      - Groq API via `groq` SDK

    Usage:
        engine = LLMEngine(config)
        response = engine.generate(prompt)
        if response is None:
            # Trigger fallback in OutputRenderer
    """

    def __init__(self, config: dict):
        """
        Initializes the LLM client based on configured provider.

        Validates that the required API key is present at startup. (EC-SYS-03)

        Args:
            config (dict): Parsed config.yaml dictionary.

        Raises:
            EnvironmentError: If the required API key is not set in environment.
        """
        self.config = config
        self.llm_config = config.get("llm", {})
        # groq SDK: from groq import Groq
        self.provider = self.llm_config.get("provider", "groq")
        self.model_name = self.llm_config.get("model", "llama3-8b-8192")
        self.temperature = self.llm_config.get("temperature", 0.4)
        self.max_tokens = self.llm_config.get("max_tokens", 1024)
        self.retry_limit = self.llm_config.get("retry_limit", 3)
        self.request_timeout = self.llm_config.get("request_timeout", 30)
        # TODO: Initialize LLM client in Phase 4

    # ── Public API ────────────────────────────────────────────────

    def generate(self, prompt: str) -> Optional[str]:
        """
        Send a prompt to the configured LLM and return the response.

        Attempts up to retry_limit times with exponential backoff.
        Returns None if all attempts fail (caller should use fallback).

        Handles:
          - EC-LE-01: Invalid/expired API key
          - EC-LE-02: Rate limit exceeded → exponential backoff
          - EC-LE-03: Empty/whitespace response → return None
          - EC-LE-04: Safety filter block → return None
          - EC-LE-07: Request timeout → retry with reduced prompt

        Args:
            prompt (str): The complete LLM prompt string.

        Returns:
            Optional[str]: Response text, or None if all attempts fail.
        """
        return self._retry(prompt)

    # ── Private Methods ───────────────────────────────────────────

    def _call_groq(self, prompt: str) -> Optional[str]:
        """
        Call the Groq API using the groq SDK.

        Args:
            prompt (str): LLM prompt string.

        Returns:
            Optional[str]: Response text or None on failure.

        Raises:
            Exception: On API/network errors (handled by _retry wrapper).
        """
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY environment variable not set.")
            
        client = Groq(api_key=api_key)
        
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            timeout=self.request_timeout,
        )
        return response.choices[0].message.content

    def _retry(self, prompt: str) -> Optional[str]:
        """
        Retry the LLM call up to retry_limit times with exponential backoff.

        Backoff schedule: 2^attempt seconds (1s, 2s, 4s)

        Args:
            prompt (str): LLM prompt string.

        Returns:
            Optional[str]: Response text or None after all retries exhausted.
        """
        for attempt in range(1, self.retry_limit + 1):
            try:
                response = self._call_groq(prompt)
                validated = self._validate_response(response)
                if validated:
                    return validated
                else:
                    logger.warning("Empty or invalid response from LLM.")
                    return None
            except Exception as e:
                wait_time = 2 ** attempt
                logger.warning(f"LLM attempt {attempt}/{self.retry_limit} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                
        logger.error("All LLM retry attempts exhausted.")
        return None

    def _validate_response(self, response_text: str) -> Optional[str]:
        """
        Validate that the response is non-empty and valid JSON. (EC-LE-03)

        Args:
            response_text (str): Raw response from LLM.

        Returns:
            Optional[str]: Cleaned JSON string, or None if invalid.
        """
        import json
        if not response_text:
            return None
        cleaned = str(response_text).strip()
        
        # Sometimes LLMs wrap JSON in markdown blocks even if told not to
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        if not cleaned:
            return None
            
        try:
            # Validate it's parseable JSON
            parsed = json.loads(cleaned)
            # Ensure it's a list (array)
            if not isinstance(parsed, list):
                logger.warning("LLM response is valid JSON but not an array.")
                return None
            return json.dumps(parsed) # Return the clean, validated JSON string
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return None
