# anaphora_connector.py

import networkx as nx


class SimpleAnaphoraLinker:
    """
    Traite la résolution anaphorique de base (pronoms -> antécédents).
    """

    def __init__(self, nxgraph: nx.Graph):
        self.graph = nxgraph

    def link_pronouns(self):
        """
        Méthode principale : repère pronoms et antécédents, ajoute r_reference.
        """
        ants = self._locate_determiners()
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

        # Pour chaque pronom identifié :
        # on cherche le meilleur antécédent possible en utilisant la fonction _evaluate_antecedent qui évalue la pertinence en fonction de la distance dans le graphe.
        # si un antécédent est trouvé, une relation r_reference est ajoutée dans le graphe pour lier le pronom à son antécédent.


    def _locate_determiners(self):
        determiner_list = {
            "le", "la", "les", "l",
            "un", "une", "des", "du",
            "de la", "de l", "de les",
        }
        found = {}
        for node in self.graph.nodes:
            if node in determiner_list:
                for nei in self.graph.neighbors(node):
                    edge_lab = self.graph[node][nei].get("label")
                    if edge_lab == "r_succ":
                        found[node] = nei
        # Ici, on parcourt tous les nœuds du graphe.
        # on cherche les déterminants parmi la liste determiner_list
        # si un det est trouvé, son voisin immédiat dans la relation r_succ est enregistré comme un antécédent potentiel.

        return found


    def _locate_pronouns(self):
        possible = {"il", "elle", "ils", "elles", "le", "la", "les", "lui", "leur"}
        return [x for x in self.graph.nodes if x in possible]
        # on recherche dans le graphe tous les nœuds qui correspondent à des pronoms personnels ou possessifs dans la liste "possible"

    def _evaluate_antecedent(self, a_node, p_node):
        dist = nx.shortest_path_length(self.graph, source=a_node, target=p_node)
        return 1 / (1 + dist)
        # Calcule la distance la plus courte entre un antécédent potentiel (a_node) et le pronom (p_node) dans le graphe.
        # utilise une formule d'inversion de distance pour attribuer un score plus élevé aux antécédents plus proches.

        # par ex : [le] → [chat] → [mange] → [la] → [souris] → [.] → [il] → [est] → [rapide]
        # si on cherche à relier il :
        # distance entre chat et il = 3
        # score = 1 / (1 + 3) = 0.25
        # distance entre souris et il = 2
        # score = 1 / (1 + 2) = 0.33
        # on choisira donc souris comme antécédent de il


        # IL FAUT TENIR COMPTE DU GENRE





