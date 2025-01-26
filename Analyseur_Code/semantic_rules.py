class RuleEngine:
    def __init__(self, graph):
        self.g = graph
        self.rules = [
            self.rule_agent_simple,
            self.rule_patient_simple,
            self.rule_caracteristique,
            self.rule_lieu
        ]

    def apply_rules(self):
        modified = True
        while modified:
            modified = False
            for rule in self.rules:
                if rule():
                    modified = True
                    print(f"Rule {rule.__name__} applied")

    def _has_pos(self, node, pos_type):
        """Vérifie si un nœud a un type POS."""
        for _, neighbor, data in self.g.edges(node, data=True):
            if data.get("label", "").startswith("r_pos"):
                # Conversion des tags reçus
                if pos_type == "Nom:" and neighbor == "Nom::":
                    return True
                elif pos_type == "Ver:" and neighbor == "Ver::":
                    return True
                elif pos_type == "Adj:" and neighbor == "Adj::":
                    return True
                elif pos_type == "Det:" and neighbor.startswith("Det:"):
                    return True
        return False

    def _has_succ(self, node1, node2):
        edge_data = self.g.get_edge_data(node1, node2)
        if not edge_data:
            return False

        # Check si l'arête a le label r_succ
        for key in edge_data:
            data = edge_data[key]
            if isinstance(data, dict) and data.get("label") == "r_succ":
                return True
            elif isinstance(data, str) and data == "r_succ":
                return True
        return False
        # Si on a un dict avec attributs
        return any(
            isinstance(data, dict) and data.get("label") == "r_succ"
            for data in edge_data.values()
        )

    def rule_agent_simple(self):
        """
        $x r_pos Det: & $y r_pos Nom: & $z r_pos Ver: & 
        $x r_succ $y & $y r_succ $z 
        => $z r_agent $y & $y r_agent-1 $z
        """
        modified = False
        for x in self.g.nodes():
            if not self._has_pos(x, "Det:"):
                continue
            for y in self.g.neighbors(x):
                if not self._has_pos(y, "Nom:"):
                    continue
                for z in self.g.neighbors(y):
                    if not self._has_pos(z, "Ver:"):
                        continue
                    if self._has_succ(x, y) and self._has_succ(y, z):
                        print(f"Adding agent relation between {z} and {y}")
                        self.g.add_edge(z, y, label="r_agent", weight=1)
                        self.g.add_edge(y, z, label="r_agent-1", weight=1)
                        modified = True
        return modified

    def rule_patient_simple(self):
        modified = False
        nodes = list(self.g.nodes())  # Créer une copie de la liste des nœuds

        for x in nodes:
            if not self._has_pos(x, "Ver:"):
                continue
            for y in list(self.g.neighbors(x)):  # Copie des voisins
                if not self._has_pos(y, "Det:"):
                    continue
                for z in list(self.g.neighbors(y)):  # Copie des voisins
                    if not self._has_pos(z, "Nom:"):
                        continue
                    if self._has_succ(x, y) and self._has_succ(y, z):
                        print(f"Adding patient relation between {x} and {z}")
                        self.g.add_edge(x, z, label="r_patient", weight=1)
                        self.g.add_edge(z, x, label="r_patient-1", weight=1)
                        modified = True
        return modified
    def rule_caracteristique(self):
        """
        $x r_pos Nom: & $y r_pos Adj: & ($x r_succ $y | $y r_succ $x)
        => $x r_carac $y
        """
        modified = False
        for x in self.g.nodes():
            if not self._has_pos(x, "Nom:"):
                continue
            for y in self.g.neighbors(x):
                if not self._has_pos(y, "Adj:"):
                    continue
                if self._has_succ(x, y) or self._has_succ(y, x):
                    print(f"Adding caracteristique relation between {x} and {y}")
                    self.g.add_edge(x, y, label="r_carac", weight=1)
                    modified = True
        return modified

    def rule_lieu(self):
        """
        $x r_pos Ver: & $y == "dans"/"sur" & $z r_pos Det: & $t r_pos Nom: &
        $x r_succ $y & $y r_succ $z & $z r_succ $t
        => $x r_lieu $t
        """
        modified = False
        preps_lieu = {"dans", "sur", "sous", "en"}
        for x in self.g.nodes():
            if not self._has_pos(x, "Ver:"):
                continue
            for y in self.g.neighbors(x):
                if y not in preps_lieu:
                    continue
                for z in self.g.neighbors(y):
                    if not self._has_pos(z, "Det:"):
                        continue
                    for t in self.g.neighbors(z):
                        if not self._has_pos(t, "Nom:"):
                            continue
                        if (self._has_succ(x, y) and self._has_succ(y, z) 
                            and self._has_succ(z, t)):
                            print(f"Adding lieu relation between {x} and {t}")
                            self.g.add_edge(x, t, label="r_lieu", weight=1)
                            modified = True
        return modified