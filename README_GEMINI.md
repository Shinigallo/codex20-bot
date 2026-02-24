# Codex20 con Gemini

Questo bot è stato aggiornato per utilizzare l'API di Google Gemini invece di Ollama locale.

## Configurazione

1.  Aggiungi la tua chiave API di Gemini al file `.env`:
    ```env
    GEMINI_API_KEY=tua_chiave_qui
    GEMINI_MODEL=gemini-1.5-flash  # Opzionale, default: gemini-1.5-flash
    ```

2.  Assicurati di avere le dipendenze installate:
    ```bash
    pip install -r requirements.txt
    ```

## Esecuzione Locale

Se vuoi eseguire il bot localmente (senza Docker), devi assicurarti che la cartella `data` sia accessibile.
Puoi creare un link simbolico alla cartella dei dati di 5etools:

```bash
ln -s ../5etools-docker/htdocs/data data
```

Poi avvia il bot:
```bash
python bot.py
```

## Esecuzione con Docker

Ricostruisci ed avvia il container:

```bash
docker-compose up --build -d
```
