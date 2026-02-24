import json
import os
import re
import logging
import difflib
from typing import Optional, List, Dict, Tuple

logger = logging.getLogger(__name__)

DATA_DIR = "data"

class KnowledgeBase:
    def __init__(self, data_path: str = "data"):
        self.data_path = data_path
        self.spells_index = {} # name_lower: (file_path, original_name)
        self.monsters_index = {} # name_lower: (file_path, original_name)
        self.items_index = {} # name_lower: (file_path, original_name)
        self.loaded = False
        self._build_index()

    def _build_index(self):
        try:
            # 1. Spells
            spells_dir = os.path.join(self.data_path, "spells")
            if os.path.exists(spells_dir):
                index_file = os.path.join(spells_dir, "index.json")
                if os.path.exists(index_file):
                    with open(index_file, 'r') as f:
                        source_files = json.load(f)
                        for source, filename in source_files.items():
                            file_path = os.path.join(spells_dir, filename)
                            if os.path.exists(file_path):
                                with open(file_path, 'r') as sf:
                                    data = json.load(sf)
                                    for s in data.get("spell", []):
                                        name = s.get("name")
                                        if name:
                                            self.spells_index[name.lower()] = (file_path, name)
            
            # 2. Monsters
            bestiary_dir = os.path.join(self.data_path, "bestiary")
            if os.path.exists(bestiary_dir):
                index_file = os.path.join(bestiary_dir, "index.json")
                if os.path.exists(index_file):
                    with open(index_file, 'r') as f:
                        source_files = json.load(f)
                        for source, filename in source_files.items():
                            file_path = os.path.join(bestiary_dir, filename)
                            if os.path.exists(file_path):
                                with open(file_path, 'r') as sf:
                                    data = json.load(sf)
                                    for m in data.get("monster", []):
                                        name = m.get("name")
                                        if name:
                                            name_lower = name.lower()
                                            self.monsters_index[name_lower] = (file_path, name)
                                            # Add partial match for named creatures or long names
                                            parts = name_lower.split()
                                            if len(parts) > 1:
                                                first_word = parts[0]
                                                if first_word not in ["the", "ancient", "adult", "young", "giant", "greater", "lesser"]:
                                                    if first_word not in self.monsters_index:
                                                        self.monsters_index[first_word] = (file_path, name)
                                            
            # 3. Items
            items_file = os.path.join(self.data_path, "items.json")
            if os.path.exists(items_file):
                with open(items_file, 'r') as f:
                    data = json.load(f)
                    for item in data.get("item", []):
                        name = item.get("name")
                        if name:
                            name_lower = name.lower()
                            self.items_index[name_lower] = (items_file, name)
                            # Add partial match for items
                            parts = name_lower.split()
                            if len(parts) > 1:
                                first_word = parts[0]
                                if first_word not in ["the", "cloak", "ring", "wand", "staff", "potion", "scroll", "bag"]:
                                    if first_word not in self.items_index:
                                        self.items_index[first_word] = (items_file, name)

            self.loaded = True
            logger.info(f"KnowledgeBase loaded: {len(self.spells_index)} spells, {len(self.monsters_index)} monsters, {len(self.items_index)} items.")
        except Exception as e:
            logger.error(f"Error building KnowledgeBase index: {e}")

    def get_entity_data(self, name: str) -> Optional[Dict]:
        name_lower = name.lower().strip()
        
        # Priority: Exact match in spells, then monsters, then items
        for index, key in [(self.spells_index, "spell"), (self.monsters_index, "monster"), (self.items_index, "item")]:
            if name_lower in index:
                file_path, original_name = index[name_lower]
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                        for entity in data.get(key, []):
                            if entity.get("name").lower() == original_name.lower():
                                # We strip some metadata if needed, but for now we give it all
                                return {"type": key, "data": entity}
                except Exception as e:
                    logger.error(f"Error loading entity data for {name_lower}: {e}")
        return None

    def find_potential_entities(self, text: str) -> List[str]:
        found = []
        # Pulizia testo: rimuovi punteggiatura comune
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        words = clean_text.split()
        
        all_keys = list(self.spells_index.keys()) + list(self.monsters_index.keys()) + list(self.items_index.keys())
        
        # 1. Exact matches for n-grams
        for n in range(4, 0, -1):
            for i in range(len(words) - n + 1):
                phrase = " ".join(words[i:i+n])
                if phrase in self.spells_index or phrase in self.monsters_index or phrase in self.items_index:
                    found.append(phrase)
        
        # 2. If no exact matches found for a word, try fuzzy matching for single words
        # and only if the word is at least 4 characters long
        if not found:
            for word in words:
                if len(word) >= 4:
                    matches = difflib.get_close_matches(word, all_keys, n=1, cutoff=0.8)
                    if matches:
                        logger.info(f"Fuzzy match found: {word} -> {matches[0]}")
                        found.append(matches[0])
        
        logger.info(f"Potential entities found in text: {found}")
        return list(set(found))

kb = KnowledgeBase()
