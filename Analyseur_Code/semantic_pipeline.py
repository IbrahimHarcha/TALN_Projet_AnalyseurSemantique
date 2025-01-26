import networkx as nx
import re
import matplotlib.pyplot as plt
from typing import List

from multiword_detector import MultiWordDetector
from disambiguator_storage import LexicalSenseStorage
from jdm_fetcher import JDMFetcher
from anaphora_connector import SimpleAnaphoraLinker
from pos_retrieve import POSTagger
from semantic_rules import RuleEngine


class GlobalAnalyzer:
    def __init__(self):
        self.g = nx.Graph()
        self.token_list: List[str] = []
        self.apostrophe_regex = re.compile(r"(\S+)'(\S+)|(\S+)", re.IGNORECASE)
        self.clean_regex = re.compile(r"[^\w'-]")
        self.multiw_store = MultiWordDetector()
        self.sense_storage = LexicalSenseStorage()
        self.jdm_data = JDMFetcher()
        self.pos_tagger = POSTagger()
        self.anaphora_module = SimpleAnaphoraLinker(self.g)
        self.rules_engine = RuleEngine(self.g)

    def generate_image(self, out_file: str = "semantic_output.png", graph_title: str = "Semantic Graph"):
        layout_pos = nx.spring_layout(self.g, k=2, iterations=50)
        edges_labels = {}

        # Récupérer correctement les labels des arêtes
        for (u, v, d) in self.g.edges(data=True):
            if isinstance(d, dict) and 'label' in d:
                edges_labels[(u, v)] = d['label']
            elif isinstance(d, str):
                edges_labels[(u, v)] = d

        plt.figure(figsize=(20, 20))
        nx.draw(
            self.g,
            layout_pos,
            with_labels=True,
            node_size=3000,
            node_color="lightgreen",
            font_size=8,
            font_weight="bold",
        )
        nx.draw_networkx_edge_labels(
            self.g,
            layout_pos,
            edge_labels=edges_labels,
            font_size=6
        )
        plt.title(graph_title)
        plt.savefig(out_file, dpi=300, bbox_inches='tight')
        plt.close()

    def __call__(self, phrase: str):
        self._analyze_text(phrase)

    def _analyze_text(self, phrase: str):
        phrase = phrase.lower()
        self.token_list = self._custom_tokenize(phrase)

        # Insert START & END
        self.token_list.insert(0, "_START")
        self.token_list.append("_END")

        # 1. Ajout des nœuds dans le graphe
        self.g.add_nodes_from(self.token_list)

        # 2. Création relations r_succ
        for i in range(len(self.token_list) - 1):
            self.g.add_edge(self.token_list[i], self.token_list[i + 1], label="r_succ")

        # 3. On fetch JDM pour chaque token
        real_words = self.token_list[1:-1]
        self.jdm_data.fetch_entries_for_words(real_words)

        # 4. POS Tagging
        self._do_pos_tagging(real_words)

        # 5. Détection de composés
        self._detect_compounds(" ".join(self.token_list))

        # 6. Désambiguïsation
        self._resolve_ambiguity()

        # 7. Résolution anaphorique
        self.anaphora_module.link_pronouns()

        # 8. Application des règles sémantiques
        print("DEBUG: Starting semantic rules application")
        # Dans _analyze_text
        self.rules_engine.apply_rules()
        print("DEBUG: Finished semantic rules application")

    def _custom_tokenize(self, sentence: str) -> List[str]:
        all_matches = self.apostrophe_regex.findall(sentence)
        raw_toks = [tk for group in all_matches for tk in group if tk]
        cleaned = [self.clean_regex.sub("", t).lower() for t in raw_toks]
        return [c for c in cleaned if c]

    def _do_pos_tagging(self, words: List[str]):
        for w in words:
            pos_info = self.pos_tagger.get_pos_tags(w)
            for pos_type, weight in pos_info.items():
                if pos_type == "Nom":
                    pos_node = "Nom:"
                elif pos_type == "Ver":
                    pos_node = "Ver:"
                elif pos_type == "Adj":
                    pos_node = "Adj:"
                elif pos_type == "Det":
                    pos_node = "Det:"
                else:
                    pos_node = f"{pos_type}:"

                self.g.add_node(pos_node)
                self.g.add_edge(w, pos_node, label="r_pos:", weight=weight)

    def _detect_compounds(self, full_str: str):
        for multi_expr in self.multiw_store.known_composites:
            if multi_expr not in full_str:
                continue
            splitted = self._custom_tokenize(multi_expr)
            idx = 0
            while idx < len(self.token_list):
                try:
                    start_i = self.token_list.index(splitted[0], idx)
                    if all(
                            self.token_list[start_i + off] == splitted[off]
                            for off in range(len(splitted))
                    ):
                        self.token_list.append(multi_expr)
                        self.g.add_node(multi_expr)
                        final_pos = start_i + len(splitted) - 1

                        if start_i > 0:
                            self.g.add_edge(self.token_list[start_i - 1], multi_expr, label="r_succ")
                        if final_pos < len(self.token_list) - 1:
                            self.g.add_edge(multi_expr, self.token_list[final_pos + 1], label="r_succ")

                        idx = final_pos + 1
                    else:
                        idx = start_i + 1
                except ValueError:
                    break

    def _resolve_ambiguity(self):
        for tk in self.token_list:
            sense, w = self.sense_storage.find_best_sense(tk)
            if sense:
                self.g.add_node(sense)
                self.g.add_edge(tk, sense, label="r_disambiguate")