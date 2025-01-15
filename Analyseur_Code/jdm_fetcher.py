# jdm_fetcher.py

import requests
from tqdm import tqdm
from datetime import datetime
import re
from base_store import StorableResource


class JDMFetcher(StorableResource):
    """
    Anciennement 'JDMDataStore'.
    Stocke localement les retours du rezo-dump (JeuxDeMots).
    """

    def __init__(self):
        super().__init__(cache_filename="jdm_dumpdata.pkl")

    def _fetch_resource(self) -> dict:
        """
        Première init : on renvoie un dict vide qu'on remplira plus tard 
        au fur et à mesure des fetches de mots.
        """
        return {}

    def _store_word_info(self, mot: str, info: dict):
        # On met à jour self.resource_data
        self.resource_data[mot] = info
        self.last_save = datetime.now()
        self._write_cache()

    @staticmethod
    def _download_dump(word: str) -> dict:
        """
        Interroge rezo-dump pour un mot donné.
        """
        url = "https://www.jeuxdemots.org/rezo-dump.php?gotermsubmit=Chercher&gotermrel=" + word.replace(" ","+") + "&rel="
        try:
            resp = requests.get(url, stream=True)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"Could not fetch rezo-dump for {word}: {e}")
            return {}

        data_collect = {
            "eid": "",
            "nt": [],
            "entries": [],
            "relations": []
        }
        for raw_line in resp.iter_lines():
            if raw_line:
                txt = raw_line.decode("latin-1")
                # On recherche par ex. '(eid=1234)' etc.
                if "(eid=" in txt:
                    splitted = txt.split("eid=")[1].split(")")[0]
                    data_collect["eid"] = splitted
                # On pourrait y ajouter des parse...
        return data_collect

    def fetch_entries_for_words(self, word_list):
        """
        Va chercher les infos pour chaque mot, si pas dans self.resource_data.
        """
        for w in word_list:
            if w not in self.resource_data:
                info = self._download_dump(w)
                self._store_word_info(w, info)
