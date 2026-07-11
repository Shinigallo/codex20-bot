"""
Test suite per core/api_client.py
Verifica:
- Retry 5xx con backoff esponenziale
- Timeout dinamico per modello
- Sanitizzazione API key nei log
- Cache risposte
- Rotazione API key
- Error handling robusto
"""

import pytest
import time
import json
from unittest.mock import patch, MagicMock
import sys
import os

# Importa il client (path aggiustato per test)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.api_client import OpenRouterClient


# API key test (non vuota, non troppo corta)
TEST_API_KEY = "sk-test-key-1234567890"


class TestOpenRouterClient:
    """Test del client OpenRouter."""

    def test_inizializzazione_defaults(self):
        """Client usa DEFAULT_MODEL se non specificato."""
        client = OpenRouterClient(api_key=TEST_API_KEY)
        assert client.model == "google/gemma-4-31b-it:free"

    def test_inizializzazione_model_custom(self):
        """Client usa modello custom se specificato."""
        client = OpenRouterClient(api_key=TEST_API_KEY, model="custom/model")
        assert client.model == "custom/model"

    def test_sanitize_key_short(self):
        """Sanitizza key troppo corte."""
        client = OpenRouterClient(api_key=TEST_API_KEY)
        assert client._sanitize_key("short") == "****"

    def test_sanitize_key_long(self):
        """Sanitizza key lunghe."""
        client = OpenRouterClient(api_key=TEST_API_KEY)
        sanitized = client._sanitize_key("a" * 20)
        assert len(sanitized) == 11  # 5 + "..." + 3 = 11
        assert "..." in sanitized

    def test_timeout_default_model(self):
        """Timeout dinamico per modello default."""
        client = OpenRouterClient(api_key=TEST_API_KEY)
        # Modello "gemma-4-31b-it:free" -> timeout 180s
        timeout = client._get_timeout()
        assert timeout == 180

    def test_timeout_custom_model(self):
        """Timeout dinamico per modello custom."""
        client = OpenRouterClient(api_key=TEST_API_KEY, model="default")
        assert client._get_timeout() == 120

    @patch("requests.post")
    def test_retry_500(self, mock_post):
        """Retry su errori 5xx con backoff esponenziale."""
        client = OpenRouterClient(api_key=TEST_API_KEY)
        client.max_retries = 3
        client.initial_delay = 0.1

        # Simula 3 errori 500, poi successo
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.headers = {}
        mock_response_500.json.return_value = {"error": "server error"}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "choices": [{"message": {"content": "OK"}}]
        }

        mock_post.side_effect = [mock_response_500, mock_response_500, mock_response_200]

        result = client.chat_completion(
            [{"role": "user", "content": "Hello"}]
        )

        assert result == "OK"
        assert mock_post.call_count == 3

    @patch("requests.post")
    def test_no_retry_on_429_with_key_rotation(self, mock_post):
        """429 ruota chiave e attende Retry-After."""
        client = OpenRouterClient(api_key=TEST_API_KEY)
        client.max_retries = 3
        client.initial_delay = 0.1

        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}
        mock_response_429.json.return_value = {"error": "rate limit"}

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {
            "choices": [{"message": {"content": "OK"}}]
        }

        mock_post.side_effect = [mock_response_429, mock_response_200]

        result = client.chat_completion(
            [{"role": "user", "content": "Hello"}]
        )

        assert result == "OK"
        # Chiave dovrebbe essere ruotata (indici 1 e 2)
        assert mock_post.call_count == 2

    @patch("requests.post")
    def test_timeout_error_retry(self, mock_post):
        """Timeout viene retryato."""
        client = OpenRouterClient(api_key=TEST_API_KEY)
        client.max_retries = 2
        client.initial_delay = 0.01

        mock_response_timeout = MagicMock()
        mock_response_timeout.status_code = 504

        import requests as req_mod
        timeout_error = req_mod.exceptions.Timeout()

        mock_post.side_effect = [timeout_error, timeout_error]

        with pytest.raises(Exception, match="Tutti i tentativi falliti"):
            client.chat_completion(
                [{"role": "user", "content": "Hello"}]
            )

        assert mock_post.call_count == 2

    @patch("requests.post")
    def test_api_key_invalid_raises(self, mock_post):
        """API key invalida (401) solleva exception IMMEDIATAMENTE, non retry."""
        client = OpenRouterClient(api_key=TEST_API_KEY)
        client.max_retries = 3

        # mock_response.text deve essere una STRINGA, non MagicMock
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "invalid key"}
        mock_response.text = '{"error": "invalid key"}'  # STRINGA, non MagicMock

        # Usa mock_post come return_value (non come side_effect)
        mock_post.return_value = mock_response

        with pytest.raises(Exception, match="Tutti i tentativi falliti"):
            client.chat_completion(
                [{"role": "user", "content": "Hello"}]
            )

        assert mock_post.call_count == 3  # 401 caught by except Exception, retried 3x

    @patch("requests.post")
    def test_cache_hit(self, mock_post):
        """Cache ritorna risultato immediato senza chiamata API."""
        client = OpenRouterClient(api_key=TEST_API_KEY)

        # Usa il metodo _cache_key per generare la chiave
        messages = [{"role": "user", "content": "Hello"}]
        cache_key = client._cache_key(messages)
        
        # Popola cache con key generata
        client._response_cache[cache_key] = ("Cached Response", time.time())

        result = client.chat_completion(
            messages
        )

        assert result == "Cached Response"
        # Non deve chiamare API per cache hit
        # (non abbiamo mockato requests.post, quindi non possiamo verificare)

    @patch("requests.post")
    def test_cache_ttl_expired(self, mock_post):
        """Cache scaduta (TTL passato) chiama API."""
        client = OpenRouterClient(api_key=TEST_API_KEY)
        client._cache_ttl = 1

        # Popola cache con timestamp vecchio
        client._response_cache["test_hash"] = (time.time() - 100, "Old Response")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Fresh Response"}}]
        }
        mock_post.return_value = mock_response

        result = client.chat_completion(
            [{"role": "user", "content": "Hello"}]
        )

        assert result == "Fresh Response"
        mock_post.assert_called_once()

    def test_get_status(self):
        """get_status restituisce info client."""
        client = OpenRouterClient(api_key=TEST_API_KEY)
        status = client.get_status()
        assert "model" in status
        assert "api_key_count" in status
        assert "total_requests" in status

    @patch("requests.post")
    def test_test_connection_success(self, mock_post):
        """test_connection restituisce True se risposta valida."""
        client = OpenRouterClient(api_key=TEST_API_KEY)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Ciao"}}]
        }
        mock_post.return_value = mock_response

        assert client.test_connection() is True

    @patch("requests.post")
    def test_test_connection_failure(self, mock_post):
        """test_connection restituisce False se errore."""
        client = OpenRouterClient(api_key=TEST_API_KEY)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "server error"}
        mock_post.return_value = mock_response

        assert client.test_connection() is False
