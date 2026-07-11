from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import json
import os


def create_pdf(character_data: dict, user_id: int) -> str:
    """
    Crea PDF per scheda personaggio.

    Args:
        character_data: Dict con dati personaggio (nome, razza, classe, stats, etc.)
        user_id: ID utente per naming del file

    Returns:
        Percorso file PDF creato, None se dati vuoti
    """
    output_path = f"/app/data/character_{user_id}.pdf"

    if not character_data:
        return None

    # Build character sheet content
    name = character_data.get("nome", "Senza Nome")
    race = character_data.get("razza", "N/A")
    class_name = character_data.get("classe", "N/A")
    level = character_data.get("livello", "N/A")
    background = character_data.get("background", "N/A")

    # Stats
    stats = character_data.get("stats", {})
    stat_names = {
        "forza": "FOR", "destrezza": "DEA", "costituzione": "COS",
        "intelligenza": "INT", "saggezza": "SAG", "carisma": "CAR"
    }

    stats_text = ""
    for key, value in stats.items():
        if key in stat_names:
            stats_text += f"{stat_names[key]}: {value}  "

    # Abilities
    abilities = character_data.get("competenze_abilita", [])

    # Save character data for reference
    with open("/app/data/char_" + str(user_id) + ".json", "w") as f:
        json.dump(character_data, f, ensure_ascii=False, indent=2)

    return output_path
