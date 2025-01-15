# disambiguator_storage.py

import requests
import io
import zipfile
import re
import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

from base_store import StorableResource

class LexicalSenseStorage(StorableResource):
    """
    Gère la désambiguïsation lexicale (anciennement 'AmbiguityResolver').
    On récupère un ZIP (ex: JeuxDeMots) pour avoir des associations de sens.
    """

    SOURCE_URL = "https://www.jeuxdemots.org/JDM-LEXICALNET-FR/20241010-LEXICALNET-JEUXDEMOTS-R1.txt.zip"
    REGEX_LINE = re.compile(r"^(.*?)\s;\s(.*?)\s;\s(\d+)$")

    def __init__(self):
        super().__init__(cache_filename="senses_cache.pkl")

    def _fetch_resource(self) -> Dict[str, List[Tuple[str, int]]]:
        data_map = defaultdict(list)
        try:
            r = requests.get(self.SOURCE_URL)
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
                fname = zf.namelist()[0]
                with zf.open(fname) as fl:
                    for line in fl:
                        line_str = line.decode("latin1").strip().lower()
                        match = self.REGEX_LINE.match(line_str)
                        if match:
                            raw_term = match.group(1)
                            splitted = match.group(2).split(">")
                            if len(splitted) < 2:
                                continue
                            wgt = int(match.group(3))
                            data_map[raw_term].append((splitted[1], wgt))
        except requests.RequestException as e:
            print(f"Error retrieving sense data: {e}")
        return dict(data_map)

    @property
    def sense_map(self) -> Dict[str, List[Tuple[str, int]]]:
        return self.retrieve()

    def find_best_sense(self, word: str) -> Tuple[str, int]:
        """
        Retourne le sens le mieux 'pondéré' pour ce mot.
        """
        possible_list = self.sense_map.get(word, [])
        if not possible_list:
            return ("", 0)
        return max(possible_list, key=lambda x: x[1])
