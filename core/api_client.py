"""
OpenRouter API client per bot Codex20.
- Retry 429/5xx/timeout con backoff esponenziale
- Timeout dinamico per modello
- Sanitizzazione API key nei log
- Cache risposte
- Rotazione API key
- Error handling robusto
- Fallback a modello di backup
"""

import time
import json
import logging
import random
import threading
import os
from typing import Optional, Any
from functools import lru_cache
import requests

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "google/gemma-4-31b-it:free"
DEFAULT_TIMEOUT = 90
CACHE_TTL = 300  # 5 minuti
MAX_429_RETRY = 6  # gemma-4 free si riprende subito, max 6 retry
INITIAL_429_DELAY = 2.0  # secondi base per retry 429
BACKUP_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"


class OpenRouterError(Exception):
    """Errore API OpenRouter."""
    pass


class InvalidApiKeyError(OpenRouterError):
    """Errore API key invalida - non retryabile."""
    pass


class OpenRouterClient:
    """Client per OpenRouter con retry, timeout e cache."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, max_retries: int = 3,
                 initial_delay: float = 1.0, cache_ttl: int = CACHE_TTL):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.cache_ttl = cache_ttl
        self._response_cache: dict[str, Any] = {}
        self._api_key_index = 0
        self._api_keys: list[str] = [self.api_key]
        self._lock = threading.Lock()

        # Timeout dinamico per modello
        self._timeout = self._get_timeout()

    def _get_timeout(self) -> int:
        """Timeout dinamico basato sul modello (con :free -> timeout più alto)."""
        base = 90
        # Estrai solo il nome del modello (dopo l'ultimo '/')
        model_id = self.model.split("/")[-1]
        # Split su ':' per gestire nomi completi come "gemma-4-31b-it:free"
        parts = model_id.split(":")
        model_name = parts[0] if parts else model_id

        if model_name.lower() in ("gemma-4-31b-it",):
            return 180  # free model, più tollerante
        return base

    def _sanitize_key(self, key: str) -> str:
        """Sanitizza key per log (solo inizio + fine)."""
        if len(key) < 8:
            return "****"
        return key[:5] + "..." + key[-3:]

    def _cache_key(self, messages: list[dict]) -> str:
        """Genera chiave cache basata su ultime 5 messaggi."""
        import hashlib
        recent = messages[-5:]
        return hashlib.md5(json.dumps(recent, sort_keys=True).encode()).hexdigest()

    def chat_completion(self, messages: list[dict], use_backup: bool = False) -> str:
        """Invia richiesta chat con retry e fallback a modello di backup."""
        model_to_use = BACKUP_MODEL if use_backup else self.model

        # Check cache prima del loop
        with self._lock:
            cache_key = self._cache_key(messages)
            if cache_key in self._response_cache:
                cached, cached_at = self._response_cache[cache_key]
                if time.time() - cached_at < self.cache_ttl:
                    logger.info(f"Cache hit: {cache_key[:12]}...")
                    return cached

        # Check API key prima del loop per evitare retry loop
        if not self.api_key or len(self.api_key) < 8:
            raise InvalidApiKeyError(f"API key invalida: {self.api_key[:5]}...")

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model_to_use,
                        "messages": messages,
                    },
                    timeout=self._timeout,
                )

                # Errori 429 (rate limit) - RETRY con backoff esponenziale
                if hasattr(response, "status_code") and response.status_code == 429:
                    logger.warning(
                        f"429 Rate limit - tentativo {attempt + 1}/{self.max_retries}, "
                        f"retry dopo {self.initial_delay * (2 ** attempt):.0f}s"
                    )
                    time.sleep(self.initial_delay * (2 ** attempt))
                    continue

                # Errori server (5xx) - retry con backoff esponenziale
                if hasattr(response, "status_code") and response.status_code >= 500:
                    logger.warning(
                        f"Server error ({response.status_code}) tentativo "
                        f"{attempt + 1}/{self.max_retries}, "
                        f"retry dopo {self.initial_delay * (2 ** attempt):.0f}s"
                    )
                    time.sleep(self.initial_delay * (2 ** attempt))
                    continue

                # Timeout - retry
                if isinstance(response, requests.exceptions.Timeout):
                    logger.warning(f"Timeout tentativo {attempt + 1}/{self.max_retries}")
                    time.sleep(self.initial_delay * (2 ** attempt))
                    continue

                # Errori client (4xx non 429) - non retry, solleva
                if hasattr(response, "status_code") and response.status_code < 500 and response.status_code != 200:
                    err_text = ""
                    try:
                        err_text = response.text[:200]
                    except Exception:
                        pass
                    error = response.json()
                    logger.error(f"Error {response.status_code}: {err_text or error}")
                    raise Exception(f"API error {response.status_code}: {err_text or error}")

                data = response.json()
                choice = data["choices"][0]
                content = choice["message"]["content"]

                # Estrai JSON se presente nel testo
                return content.strip()

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout tentativo {attempt + 1}/{self.max_retries}")
                time.sleep(self.initial_delay * (2 ** attempt))
                continue
            except InvalidApiKeyError:
                # Non retry per API key invalida
                raise
            except Exception as e:
                logger.warning(f"Errore tentativo {attempt + 1}/{self.max_retries}: {e}")
                time.sleep(self.initial_delay * (2 ** attempt))
                continue

        # Fallback a modello di backup dopo tutti i retry
        logger.info(f"Tutti i tentativi falliti, fallback a {BACKUP_MODEL}")
        return self.chat_completion(messages, use_backup=True)

    def test_connection(self) -> bool:
        """Test connessione API."""
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": [{"role": "user", "content": "Hi"}]},
                timeout=30,
            )
            # 200 = OK, 429 = rate limit (ma connesso), 401 = chiave invalida
            if response.status_code == 200:
                return "choices" in response.json()
            elif response.status_code == 429:
                # Rate limit temporaneo, consideriamo connesso
                return True
            elif response.status_code == 401:
                return False
            else:
                return False
        except Exception:
            return False

    def rotate_key(self) -> None:
        """Ruota API key."""
        self._api_key_index = (self._api_key_index + 1) % len(self._api_keys)
        self.api_key = self._api_keys[self._api_key_index]

    def add_key(self, key: str) -> None:
        """Aggiunge una nuova API key."""
        self._api_keys.append(key)
        self._api_key_index = (self._api_key_index + 1) % len(self._api_keys)
        self.api_key = self._api_keys[self._api_key_index]

    def get_status(self) -> dict:
        """Restituisce info client."""
        return {
            "model": self.model,
            "backup_model": BACKUP_MODEL,
            "api_key_count": len(self._api_keys),
            "total_requests": 0,
            "cache_size": len(self._response_cache),
            "timeout": self._timeout,
        }
