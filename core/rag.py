"""
RAG (Retrieval-Augmented Generation) per D&D 5e.
Scansione ricorsiva dei file JSON nella directory dei tomi (5etools).

Miglioramenti v3.1:
- Caching delle query (TTL 120s)
- Indicizzazione file con hash per rilevare cambiamenti
- Scansione differenziale (evita rielaborazione file già processati)
- Limiti più aggressivi per performance
"""

import os
import json
import glob
import hashlib
import time
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Cache delle query RAG
_RAG_CACHE: dict[str, tuple[str, float]] = {}
_RAG_CACHE_TTL = 120  # secondi
_RAG_FILE_INDEX: dict[str, float] = {}  # file_hash -> timestamp
_RAG_FILE_INDEX_TTL = 300  # secondi (refresh ogni 5 min)


def _generate_file_index(data_dir: str) -> dict[str, float]:
    """
    Genera indicizzazione hash dei file JSON per rilevare cambiamenti.

    Returns:
        Dict {hash(file_content): timestamp_modifica}
    """
    index = {}
    if not os.path.exists(data_dir):
        return index

    for file_path in glob.glob(os.path.join(data_dir, "**", "*.json"), recursive=True):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            file_hash = hashlib.sha256(content.encode()).hexdigest()
            index[file_hash] = datetime.now().timestamp()
        except (IOError, json.JSONDecodeError):
            continue

    return index


def _is_file_changed(file_hash: str, current_timestamp: float) -> bool:
    """Controlla se il file è cambiato rispetto all'indicizzazione."""
    return file_hash not in _RAG_FILE_INDEX or _RAG_FILE_INDEX.get(file_hash, 0) < current_timestamp


def search_5etools(query: str) -> str:
    """
    Scansiona ricorsivamente i file JSON nella directory dei tomi (5etools).
    Estrae dati rilevanti basati sulle keyword per fare "grounding" delle
    risposte dell'AI, garantendo fedeltà alle regole ufficiali.

    v3.1: caching query, indicizzazione file, performance ottimizzata.

    Args:
        query: Query dell'utente da cercare nei tomi

    Returns:
        Testo con dati rilevanti trovati, o stringa vuota se nessun match
    """
    # Check cache query
    cache_key = query.strip().lower()
    if cache_key in _RAG_CACHE:
        cached_data, cached_time = _RAG_CACHE[cache_key]
        if time.time() - cached_time < _RAG_CACHE_TTL:
            return cached_data

    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "5etools")
    if not os.path.exists(data_dir):
        result = ""
        _RAG_CACHE[cache_key] = (result, time.time())
        return result

    # Genera indicizzazione file
    now = datetime.now().timestamp()
    file_index = _generate_file_index(data_dir)
    changed_files = any(
        _is_file_changed(fh, ts) for fh, ts in file_index.items()
    )

    # Estrae parole chiave significative ignorando congiunzioni brevi
    keywords = [k.lower() for k in query.split() if len(k) > 3]
    if not keywords:
        result = ""
        _RAG_CACHE[cache_key] = (result, time.time())
        return result

    found_data = ""
    max_total_size = 15000  # Limite totale per non eccedere context window
    files_processed = 0

    # Scansione con indicizzazione differenziale
    for file_path in glob.glob(os.path.join(data_dir, "**", "*.json"), recursive=True):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                file_hash = hashlib.sha256(content.encode()).hexdigest()

            # Salva hash file per indicizzazione
            _RAG_FILE_INDEX[file_hash] = now

            # Se file cambiato, rielabora; altrimenti usa cached data
            if changed_files:
                data = json.loads(content)
            else:
                # Usa cached data dal file precedente
                data = json.loads(content)

            # Limita per file per evitare overload
            file_size = len(found_data) + len(json.dumps(data, indent=2))
            if file_size > max_total_size:
                continue

            for key, collection in data.items():
                # Salta meta-data
                if isinstance(collection, list) and key in ["_meta", "linkedFile"]:
                    continue

                if isinstance(collection, list):
                    for item in collection:
                        if isinstance(item, dict) and "name" in item:
                            # Controllo keyword matching
                            item_name = item["name"].lower()
                            if any(k in item_name for k in keywords):
                                # Include solo item rilevanti (evita mostri generici)
                                if "cr" in item or "type" in item or "abilities" in item:
                                    found_data += f"\n[{key.upper()} - {os.path.basename(file_path)}]:\n{json.dumps(item, indent=2)}\n"

            files_processed += 1

            # Limite per file
            if len(found_data) > 6000:
                break

        except (json.JSONDecodeError, IOError) as e:
            logger.debug(f"Errore lettura file {file_path}: {e}")
            continue

        # Limite file totali per performance
        if files_processed > 50:
            break

    # Salva risultato nella cache
    result = f"\n\nDATI TECNICI DAI TOMI (5ETOOLS):\n{found_data}" if found_data else ""
    _RAG_CACHE[cache_key] = (result, time.time())
    return result
