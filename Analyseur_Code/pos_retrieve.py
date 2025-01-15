# pos_retriever.py

import requests
from datetime import datetime
from tqdm import tqdm
from base_store import StorableResource

API_ENDPOINT = "https://jdm-api.demo.lirmm.fr/v0/relations/from/{word}"
POS_CLASS = 4


class POSTagger(StorableResource):
    """
    Anciennement 'TaggerStore'.
    Récupère pour un mot ses étiquettes de type POS depuis l'API JDM (type=4).
    """

    def __init__(self):
        super().__init__(cache_filename="pos_infos.pkl")

    def _fetch_resource(self) -> dict:
        """
        On renvoie un dict vide initialement ; on le complète après coup.
        """
        return {}

    @staticmethod
    def _ask_for_pos(mot: str) -> dict:
        try:
            link = API_ENDPOINT.format(word=mot)
            r = requests.get(link)
            r.raise_for_status()
            data_j = r.json()
        except requests.RequestException as e:
            print(f"POS request failed for '{mot}': {e}")
            return {}

        output = {}
        for nd in tqdm(data_j.get("nodes", []), desc=f"POS for {mot}"):
            if nd.get("type") == POS_CLASS and "name" in nd:
                output[nd["name"]] = nd["w"]
        return output

    def _save_pos_for_word(self, mot: str, info: dict):
        self.resource_data[mot] = info
        self.last_save = datetime.now()
        self._write_cache()

    def get_pos_tags(self, mot: str) -> dict:
        if mot not in self.resource_data:
            result = self._ask_for_pos(mot)
            self._save_pos_for_word(mot, result)
        return self.resource_data.get(mot, {})
