# anaphora_connector.py

import networkx as nx


class SimpleAnaphoraLinker:
    """
    Anciennement 'PronounLinker'.
    Traite la résolution anaphorique de base (pronoms -> antécédents).
    """

    def __init__(self, nxgraph: nx.Graph):
        self.graph = nxgraph

    def link_pronouns(self):
        """
        Méthode principale : repère pronoms et antécédents, ajoute r_reference.
        """
        ants = self._locate_articles()
        pros = self._locate_pronouns()

        for prn in pros:
            best_ante = None
            best_val = float("-inf")
            for art, target in ants.items():
                sc = self._evaluate_antecedent(target, prn)
                if sc > best_val:
                    best_val = sc
                    best_ante = target

            if best_ante:
                self.graph.add_edge(prn, best_ante, label="r_reference")

    def _locate_articles(self):
        article_list = {
            "le", "la", "les", "l",
            "un", "une", "des", "du",
            "de la", "de l", "de les",
        }
        found = {}
        for node in self.graph.nodes:
            if node in article_list:
                for nei in self.graph.neighbors(node):
                    edge_lab = self.graph[node][nei].get("label")
                    if edge_lab == "r_succ":
                        found[node] = nei
        return found

    def _locate_pronouns(self):
        possible = {"il", "elle", "ils", "elles", "le", "la", "les", "lui", "leur"}
        return [x for x in self.graph.nodes if x in possible]

    def _evaluate_antecedent(self, a_node, p_node):
        dist = nx.shortest_path_length(self.graph, source=a_node, target=p_node)
        return 1 / (1 + dist)
