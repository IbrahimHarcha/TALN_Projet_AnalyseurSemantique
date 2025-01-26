# pos_retriever.py

import requests
from datetime import datetime
from tqdm import tqdm
from base_store import StorableResource

API_ENDPOINT = "https://jdm-api.demo.lirmm.fr/v0/relations/from/{word}"
POS_CLASS = 4 # désigne les relations grammaticales dans l'API JDM


# Cette classe interroge l'API JDM pour récupérer les étiquettes grammaticales d'un mot.
# Elle stocke ces informations en cache pour éviter les requêtes répétitives.
# Elle fournit les étiquettes POS sous forme d'un dictionnaire.

class POSTagger(StorableResource):
    """
    Récupère pour un mot ses étiquettes de type POS depuis l'API JDM (type=4).
    """

    def __init__(self):
        super().__init__(cache_filename="pos_infos.pkl")

    def _fetch_resource(self) -> dict:
        """
        On renvoie un dict vide initialement ; on le complète après coup.
        """
        return {}
        # Ce dict est utilisé pour stocker les informations de POS au fur et à mesure qu'elles sont obtenues.


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
    
        # Lecture des données JSON retournées par l'API.
        # Extraction des informations POS :
        # L'API renvoie une liste de nœuds contenant différents types de relations.
        # On ne conserve que les nœuds dont type == POS_CLASS (4) et qui possèdent un champ "name".
        # On enregistre chaque étiquette POS avec son poids w.

        # pos_tags = POSTagger._ask_for_pos("chat")
        # print(pos_tags)

# {
#     "nodes": [
#         {"type": 4, "name": "Nom", "w": 100},
#         {"type": 4, "name": "Verbe", "w": 50}
#     ]
# }

        # res : {"Nom": 100, "Verbe": 50}

    def _save_pos_for_word(self, mot: str, info: dict):
        self.resource_data[mot] = info
        self.last_save = datetime.now()
        self._write_cache()

    def get_pos_tags(self, mot: str) -> dict:
        if mot not in self.resource_data:
            result = self._ask_for_pos(mot)
            self._save_pos_for_word(mot, result)
        return self.resource_data.get(mot, {})
