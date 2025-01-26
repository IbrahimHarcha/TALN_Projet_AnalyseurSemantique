# multiword_detector.py

import requests
from tqdm import tqdm
import re
from base_store import StorableResource  # Assurez-vous que l'import est correct
from datetime import timedelta
from typing import List

class MultiWordDetector(StorableResource):
    """
    Détecte les expressions composées (anciennement 'CompoundTermManager').
    """

    DUMMY_URL = "https://www.jeuxdemots.org/JDM-LEXICALNET-FR/20240924-LEXICALNET-JEUXDEMOTS-ENTRIES-MWE.txt"
    WORD_PATTERN = re.compile(r"(\d+);\"(.+)\";")  # Pattern pour matcher les lignes du fichier

    def __init__(self, days_valid=30):
        super().__init__(
            cache_filename="multiwords.pkl",
            validity=timedelta(days=days_valid),
        )

    def _fetch_resource(self) -> List[str]:
        """
        Récupère les mots composés depuis l'URL donnée, puis les stocke dans un cache local.
        """
        try:
            response = requests.get(self.DUMMY_URL, stream=True)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Erreur lors de la récupération des mots composés : {e}")
            raise Exception("Impossible de récupérer les mots composés")

        compound_words = []
        for line in tqdm(
            response.iter_lines(), desc="Récupération des mots composés depuis JeuxDeMots..."
        ):
            line = line.decode("latin1").strip().lower()
            match = self.WORD_PATTERN.match(line)
            if match:
                compound_words.append(match.group(2))

        return compound_words

    @property
    def known_composites(self) -> List[str]:
        """
        Retourne la liste des mots composés connus.
        """
        return self.retrieve()
