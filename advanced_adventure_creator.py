# Codex20 Advanced Adventure Creator
# Sistema di generazione avventure complete multi-parte

import asyncio
from typing import Dict, List

class AdvancedAdventureCreator:
    """Adventure Creator che genera avventure complete, non solo riassunti"""
    
    def __init__(self, generate_content_func, search_5etools_func):
        self.generate_content = generate_content_func
        self.search_5etools = search_5etools_func
    
    async def create_complete_adventure(self, prompt: str, user_id: int):
        """Crea avventura completa in parti multiple"""
        
        # 1. Genera outline iniziale
        adventure_outline = await self._generate_outline(prompt)
        
        # 2. Espande ogni sezione
        complete_adventure = {}
        
        # Background e setup
        complete_adventure['background'] = await self._generate_background_section(adventure_outline)
        
        # Encounters dettagliati
        complete_adventure['encounters'] = await self._generate_encounter_sections(adventure_outline)
        
        # NPCs con personalità
        complete_adventure['npcs'] = await self._generate_npc_sections(adventure_outline)
        
        # Locations descritte
        complete_adventure['locations'] = await self._generate_location_sections(adventure_outline)
        
        # Hooks e conclusioni
        complete_adventure['hooks_conclusions'] = await self._generate_hooks_conclusions(adventure_outline)
        
        # Handouts e props
        complete_adventure['handouts'] = await self._generate_handouts(adventure_outline)
        
        return complete_adventure
    
    async def _generate_outline(self, prompt: str) -> Dict:
        """Genera outline strutturato dell'avventura"""
        
        # Usa RAG per contesto
        context_data = self.search_5etools(prompt)
        
        outline_prompt = f"""Crea un outline dettagliato per un'avventura D&D 5e basata su: {prompt}

{context_data}

Genera un outline JSON con questa struttura:
{{
    "title": "Titolo avventura",
    "party_level": 3,
    "party_size": 4,
    "estimated_sessions": 1,
    "setting": "Ambientazione principale",
    "theme": "Tema narrativo",
    "main_plot": "Trama principale in 2-3 frasi",
    "encounters": [
        {{
            "type": "combat/social/exploration",
            "title": "Titolo encounter",
            "location": "Dove avviene", 
            "challenge": "CR o difficoltà",
            "purpose": "Scopo narrativo"
        }}
    ],
    "locations": [
        {{
            "name": "Nome location",
            "type": "dungeon/city/wilderness",
            "key_features": ["caratteristica1", "caratteristica2"]
        }}
    ],
    "npcs": [
        {{
            "name": "Nome NPC",
            "role": "alleato/nemico/neutro",
            "importance": "major/minor",
            "motivation": "Cosa vuole"
        }}
    ],
    "treasure_theme": "tipo di tesoro prevalente",
    "ending_options": ["opzione1", "opzione2"]
}}

Rispondi SOLO con il JSON, nient'altro."""

        response = await self.generate_content(outline_prompt)
        
        # Parse JSON dall'output
        import json
        import re
        
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```|(\{.*\})', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1) if json_match.group(1) else json_match.group(2)
            try:
                return json.loads(json_str)
            except:
                pass
        
        # Fallback - outline minimale se parsing fallisce
        return {
            "title": "Avventura Misteriosa",
            "party_level": 3,
            "party_size": 4,
            "main_plot": "Un'avventura da completare",
            "encounters": [{"title": "Incontro principale", "type": "combat"}],
            "locations": [{"name": "Location principale"}],
            "npcs": [{"name": "PNG importante"}]
        }
    
    async def _generate_background_section(self, outline: Dict) -> str:
        """Genera background e setup dettagliato"""
        
        background_prompt = f"""Scrivi la sezione BACKGROUND per l'avventura "{outline.get('title', 'Untitled')}"

OUTLINE:
- Trama: {outline.get('main_plot', 'Trama da definire')}
- Ambientazione: {outline.get('setting', 'Generica')}
- Livello party: {outline.get('party_level', 3)}

Scrivi un background di 300-500 parole che includa:
1. **Situazione iniziale** - Cosa sta succedendo nel mondo
2. **Il problema** - Perché servono gli avventurieri  
3. **Hook iniziale** - Come vengono coinvolti i PCs
4. **Informazioni di background** - Cosa potrebbero sapere i personaggi

Usa uno stile coinvolgente ma pratico per il DM. Includi dettagli utilizzabili al tavolo."""

        return await self.generate_content(background_prompt)
    
    async def _generate_encounter_sections(self, outline: Dict) -> List[str]:
        """Genera tutti gli encounters dettagliati"""
        
        encounters = []
        
        for i, enc_outline in enumerate(outline.get('encounters', []), 1):
            
            encounter_prompt = f"""Scrivi l'ENCOUNTER {i} completo per l'avventura "{outline.get('title')}"

ENCOUNTER OUTLINE:
- Titolo: {enc_outline.get('title', 'Incontro')}
- Tipo: {enc_outline.get('type', 'combat')}
- Location: {enc_outline.get('location', 'Area generica')}
- Scopo: {enc_outline.get('purpose', 'Avanzare la trama')}
- Party Level: {outline.get('party_level', 3)}

Scrivi una descrizione completa (400-600 parole) che includa:

**DESCRIZIONE INIZIALE:**
- Cosa vedono/sentono i PCs quando arrivano
- Atmosfera e dettagli sensoriali
- Elementi interattivi

**SVILUPPO:**
- Come si svolge l'encounter passo-passo
- Opzioni tattiche per mostri/NPCs
- Reazioni a diverse azioni dei PCs

**STATISTICHE:**
- Mostri/NPCs con HP, CA, attacchi principali
- DC per prove di abilità
- Tesoro/ricompense

**COLLEGAMENTI:**
- Come si collega all'encounter precedente/successivo
- Indizi per avanzare la trama

Scrivi per un DM che deve far giocare questo encounter stasera."""

            encounter_text = await self.generate_content(encounter_prompt)
            encounters.append(encounter_text)
            
            # Pausa per evitare rate limits
            await asyncio.sleep(1)
        
        return encounters
    
    async def _generate_npc_sections(self, outline: Dict) -> List[str]:
        """Genera NPCs con personalità complete"""
        
        npcs = []
        
        for npc_outline in outline.get('npcs', []):
            
            npc_prompt = f"""Crea l'NPC completo per l'avventura "{outline.get('title')}"

NPC OUTLINE:
- Nome: {npc_outline.get('name', 'PNG')}
- Ruolo: {npc_outline.get('role', 'neutro')}
- Importanza: {npc_outline.get('importance', 'minor')}
- Motivazione: {npc_outline.get('motivation', 'Sopravvivere')}

Scrivi una descrizione completa (200-300 parole) che includa:

**ASPETTO:**
- Descrizione fisica distintiva
- Abbigliamento e possesso caratteristici
- Peculiarità o cicatrici

**PERSONALITÀ:**
- Tratti caratteriali principali
- Come parla (formale/informale, accento, frasi ricorrenti)
- Cosa lo motiva/lo spaventa

**BACKGROUND:**
- Storia breve ma significativa
- Legami con l'avventura
- Segreti che potrebbe rivelare

**ROLEPLAY:**
- Come reagisce ai PCs
- Informazioni che possiede
- Cosa può offrire (aiuto, ostacolo, informazioni)

Scrivi tutto quello che serve al DM per interpretarlo al tavolo."""

            npc_text = await self.generate_content(npc_prompt)
            npcs.append(npc_text)
            
            # Pausa per evitare rate limits
            await asyncio.sleep(1)
        
        return npcs
    
    async def _generate_location_sections(self, outline: Dict) -> List[str]:
        """Genera locations dettagliate"""
        
        locations = []
        
        for loc_outline in outline.get('locations', []):
            
            location_prompt = f"""Descrivi la LOCATION completa per l'avventura "{outline.get('title')}"

LOCATION OUTLINE:
- Nome: {loc_outline.get('name', 'Luogo')}
- Tipo: {loc_outline.get('type', 'generica')}
- Caratteristiche: {', '.join(loc_outline.get('key_features', ['Normale']))}

Scrivi una descrizione completa (300-400 parole) che includa:

**OVERVIEW:**
- Descrizione generale dell'area
- Dimensioni e layout basilare
- Prima impressione che dà ai PCs

**DETTAGLI IMPORTANTI:**
- Aree specifiche di interesse
- Elementi interattivi (porte, leve, altari, etc.)
- Pericoli ambientali o trappole

**ATMOSFERA:**
- Suoni, odori, illuminazione
- Sensazioni che trasmette
- Elementi che creano tensione

**SEGRETI/NASCOSTO:**
- Elementi non immediatamente visibili
- Cosa possono scoprire con indagini
- Passaggi segreti o stanze nascoste

**TATTICHE:**
- Come nemici potrebbero usare l'ambiente
- Vantaggi/svantaggi per il combattimento
- Possibili vie di fuga

Scrivi tutto quello che serve per far vivere il luogo ai giocatori."""

            location_text = await self.generate_content(location_prompt)
            locations.append(location_text)
            
            # Pausa per evitare rate limits
            await asyncio.sleep(1)
        
        return locations
    
    async def _generate_hooks_conclusions(self, outline: Dict) -> Dict[str, str]:
        """Genera hooks e possibili conclusioni"""
        
        hooks_prompt = f"""Scrivi HOOKS e CONCLUSIONI per l'avventura "{outline.get('title')}"

OUTLINE: {outline.get('main_plot', 'Trama principale')}

Crea:

**ADVENTURE HOOKS (3 diverse opzioni):**
Come coinvolgere i PCs nell'avventura. Ogni hook per diversi tipi di party.

**POSSIBILI CONCLUSIONI (3 scenari):**
- Successo totale: cosa succede se risolvono tutto
- Successo parziale: qualcosa va storto ma vincono
- Fallimento: conseguenze se non riescono

**SEQUEL HOOKS:**
Come questa avventura può portare a nuove storie

Scrivi 300-400 parole totali con esempi pratici."""

        return {
            'hooks_and_conclusions': await self.generate_content(hooks_prompt)
        }
    
    async def _generate_handouts(self, outline: Dict) -> List[str]:
        """Genera handouts e props per i giocatori"""
        
        handouts_prompt = f"""Crea HANDOUTS per l'avventura "{outline.get('title')}"

Scrivi 2-3 handouts utili:
- Lettera, mappa, o documento in-character
- Descrizioni che il DM può leggere ad alta voce
- Indovinelli o puzzle testuali

Ogni handout deve essere pronto per essere copiato/stampato e dato ai giocatori.
Formato: testo diretto, senza descrizioni meta."""

        handouts_text = await self.generate_content(handouts_prompt)
        return [handouts_text]

# Funzioni di formatting per output multi-parte

def format_adventure_part(part_name: str, content: str, part_num: int, total_parts: int) -> str:
    """Formatta una parte dell'avventura per output Telegram"""
    
    header = f"🎲 **PARTE {part_num}/{total_parts}: {part_name.upper()}**\n\n"
    
    # Trunca se troppo lungo per Telegram
    if len(content) > 3500:
        content = content[:3500] + "\n\n[...continua nella prossima parte...]"
    
    footer = f"\n\n📖 Parte {part_num} di {total_parts}"
    
    return header + content + footer

async def send_complete_adventure_async(message, adventure_data, bot):
    """Invia avventura completa in parti multiple"""
    
    parts = [
        ("Background & Setup", adventure_data['background']),
        ("Encounters", "\n\n".join(adventure_data['encounters'])),
        ("NPCs", "\n\n".join(adventure_data['npcs'])),
        ("Locations", "\n\n".join(adventure_data['locations'])),
        ("Hooks & Conclusioni", adventure_data['hooks_conclusions']['hooks_and_conclusions']),
        ("Handouts & Props", "\n\n".join(adventure_data['handouts']))
    ]
    
    total_parts = len(parts)
    
    for i, (part_name, content) in enumerate(parts, 1):
        if content.strip():  # Solo se ha contenuto
            formatted_part = format_adventure_part(part_name, content, i, total_parts)
            
            try:
                await message.answer(formatted_part, parse_mode="Markdown")
            except Exception:
                await message.answer(formatted_part)
            
            # Pausa tra parti per evitare spam
            await asyncio.sleep(2)
    
    # Messaggio finale
    await message.answer("🏆 **Avventura completa generata!**\n\nPuoi ora utilizzarla direttamente al tavolo. Buona fortuna, Dungeon Master! 🎲✨")