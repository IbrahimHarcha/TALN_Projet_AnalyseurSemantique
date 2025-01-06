import os
import re
import json
import requests
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict

###############################################################################
#                                DATA
###############################################################################

@dataclass
class Node:
    word: str
    node_id: Optional[int] = None
    node_type: Optional[str] = None
    weight: float = 1.0
    
    def __post_init__(self):
        self.relations: List["Relation"] = []
        self.pos_tags: Set[str] = set()   # e.g. {"Nom", "Det", "V"}
        self.senses: List[str] = []
        self.head_token: Optional["Node"] = None

@dataclass
class Relation:
    rel_type: str
    source_node: Node
    target_node: Node
    weight: float = 1.0
    annotations: Dict = field(default_factory=dict)

class SemanticGraph:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.relations: List[Relation] = []
        
    def add_node(self, node: Node) -> None:
        # Évite la duplication
        if node.word not in self.nodes:
            self.nodes[node.word] = node
    
    def get_or_create_node(self, word: str, **kwargs) -> Node:
        if word not in self.nodes:
            new_node = Node(word, **kwargs)
            self.nodes[word] = new_node
            return new_node
        return self.nodes[word]
        
    def add_relation(self, source: Node, target: Node, rel_type: str, weight: float = 1.0) -> None:
        for rel in self.relations:
            if (rel.source_node == source 
                and rel.target_node == target 
                and rel.rel_type == rel_type):
                # MàJ du poids si besoin
                rel.weight = weight
                return
        relation = Relation(rel_type, source, target, weight)
        self.relations.append(relation)
        source.relations.append(relation)

    def get_node(self, word: str) -> Optional[Node]:
        return self.nodes.get(word)
    
    def get_relations_between(self, source: Node, target: Node) -> List[Relation]:
        return [r for r in self.relations 
                if r.source_node == source and r.target_node == target]

###############################################################################
#                          JDM CLIENT
###############################################################################

class JDMClient:
    """
    Exemple de client JDM un peu plus complet, 
    pour /api/v1/nodes/search + /api/v1/nodes/<id>/relations
    """
    BASE_URL = "https://jdm-api.demo.lirmm.fr/api/v1"
    
    def __init__(self, cache_dir: str = ".jdm_cache"):
        self.cache_dir = cache_dir
        self.session = requests.Session()
        os.makedirs(cache_dir, exist_ok=True)
        
    def search_node(self, word: str) -> Optional[Dict]:
        """
        Cherche un node par le mot (term). Ex: /nodes/search?term=chat
        """
        cache_file = os.path.join(self.cache_dir, f"search_{word}.json")
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        
        url = f"{self.BASE_URL}/nodes/search"
        params = {"term": word}
        try:
            resp = self.session.get(url, params=params, timeout=3)
            if resp.ok:
                data = resp.json()
                if data:
                    # on prend la 1ère entrée
                    best = data[0]
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(best, f, ensure_ascii=False, indent=2)
                    return best
        except requests.exceptions.RequestException:
            pass
        return None
    
    def get_node_relations(self, node_id: int) -> List[Dict]:
        """
        Récupère la liste des relations sortantes d'un node_id
        Ex: /nodes/<id>/relations
        """
        if not node_id:
            return []
        
        cache_file = os.path.join(self.cache_dir, f"rels_{node_id}.json")
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        
        url = f"{self.BASE_URL}/nodes/{node_id}/relations"
        try:
            resp = self.session.get(url, timeout=3)
            if resp.ok:
                data = resp.json()
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return data
        except requests.exceptions.RequestException:
            pass
        return []

###############################################################################
#                 TOKENIZER + COMPOUND TERMS
###############################################################################

def morphological_tokenize(text: str) -> List[str]:
    """
    Sépare les apostrophes : "l'algorithme" -> ["l'", "algorithme"], etc.
    Sépare la ponctuation, etc. 
    Simplifié.
    """
    # Supprime la ponctuation simple
    text = re.sub(r"[.,!?;]+", "", text)

    tokens = text.split()
    final_tokens = []
    
    # On gère seulement certains patterns
    pattern_apostrophe = re.compile(r"^([ldjtnscqu])'(.*)$", re.IGNORECASE)
    
    for tok in tokens:
        # Cherche "l'algorithme", "n'aime"
        m = pattern_apostrophe.match(tok)
        if m:
            part1 = m.group(1) + "'"
            part2 = m.group(2)
            final_tokens.append(part1.lower())
            final_tokens.append(part2.lower())
        else:
            final_tokens.append(tok.lower())
    return final_tokens

class CompoundTermFinder:
    """
    Repère les composés. On stocke la liste dans un set ; 
    on cherche si 'du lait' est dans la liste, etc.
    """
    def __init__(self, compound_terms_file: str):
        self.terms = set()
        if os.path.exists(compound_terms_file):
            with open(compound_terms_file, "r", encoding="utf-8") as f:
                for line in f:
                    self.terms.add(line.strip().lower())
    
    def find_compounds(self, tokens: List[str]) -> List[Tuple[int,int,str]]:
        results = []
        n = len(tokens)
        for i in range(n):
            for j in range(i+1, n+1):
                candidate = " ".join(tokens[i:j])
                if candidate in self.terms:
                    results.append((i,j,candidate))
        return results

###############################################################################
#                       ANALYZER
###############################################################################

class SemanticAnalyzer:
    def __init__(self, 
                 compound_file: str = "compound_terms.txt", 
                 max_rule_iterations: int = 5):
        self.jdm_client = JDMClient()
        self.compound_finder = CompoundTermFinder(compound_file)
        self.max_rule_iterations = max_rule_iterations
        self.pos_patterns = self.load_pos_patterns()

    def load_pos_patterns(self) -> Dict[str, str]:
        """
        Regex -> POS
        """
        return {
            r"^(le|la|les|un|une|du|de|des|au|aux|l')$": "Det",
            r"^(est|sont|a|ont|boit|mange|tombe|pleure|aboie|aboyé|aime|explose|regarde|comprend|présenté|implémenter|implémenté|été)$": "V",
            r"^(petit|grande?s?|profonde?s?|difficile)$": "Adj",
            r"^(rapidement|lentement|toute|toutes?|jamais)$": "Adv",
            r"^(chat|chien|souris|lait|chèvre|queue|puits|nuit|algorithme|cours|voisine|religieuse|pâtisserie|missile|croiseur|vers|chairs|cadavres|échelle|savoir|garçon|enfant|glace)$": "Nom",
            r"^(ne|n')$": "Neg",
            r"^(pas)$": "Neg",
            r"^(il|elle|ils|elles|son|sa|ses)$": "Pro"
        }

    def analyze(self, text: str) -> SemanticGraph:
        graph = SemanticGraph()

        # 1) Tokenize (avec gestion rudimentaire des apostrophes)
        tokens = morphological_tokenize(text)

        # 2) Créer la chaîne r_succ
        prev_node = graph.get_or_create_node("_START")
        for tok in tokens:
            node = graph.get_or_create_node(tok)
            graph.add_relation(prev_node, node, "r_succ")
            prev_node = node
        end_node = graph.get_or_create_node("_END")
        graph.add_relation(prev_node, end_node, "r_succ")

        # 3) Composés
        found_compounds = self.compound_finder.find_compounds(tokens)
        for (start_i, end_i, phrase) in found_compounds:
            # On insère un noeud parallèle
            c_node = graph.get_or_create_node(phrase)
            # Relie c_node dans la chaîne
            left_tok = tokens[start_i-1] if start_i > 0 else "_START"
            right_tok = tokens[end_i] if end_i < len(tokens) else "_END"
            left_node = graph.get_node(left_tok)
            right_node = graph.get_node(right_tok)
            if left_node and right_node:
                graph.add_relation(left_node, c_node, "r_succ")
                graph.add_relation(c_node, right_node, "r_succ")

        # 4) POS Tagging
        self.add_pos_tags(graph)

        # 5) Application de règles
        self.apply_syntax_rules(graph)

        # 6) Intégration JDM (optionnel)
        self.apply_jdm_relations(graph)

        # 7) Règle d’inférence (ex. A r_isa C et C r_agent X => A r_agent X)
        self.apply_inference(graph)

        return graph

    def add_pos_tags(self, graph: SemanticGraph) -> None:
        for node in graph.nodes.values():
            if node.word in ("_START", "_END"):
                continue
            # Regex matching
            for pat, pos in self.pos_patterns.items():
                if re.match(pat, node.word, re.IGNORECASE):
                    node.pos_tags.add(pos)

    def apply_syntax_rules(self, graph: SemanticGraph) -> None:
        rules = [
            SyntaxRules.rule_noun_phrase,
            SyntaxRules.rule_passive_form,
            SyntaxRules.rule_subject_verb,
            SyntaxRules.rule_verb_object,
            SyntaxRules.rule_negation
        ]
        for _ in range(self.max_rule_iterations):
            changed_any = False
            for rule in rules:
                changed = rule(graph)
                if changed:
                    changed_any = True
            if not changed_any:
                break

    def apply_jdm_relations(self, graph: SemanticGraph) -> None:
        """
        Exemple: on cherche si le node existe dans JDM (via /nodes/search).
        On récupère ensuite ses relations sortantes (via /nodes/<id>/relations).
        Puis on crée dans le graphe des relations r_isa, r_syn, etc.
        """
        for node in graph.nodes.values():
            if node.word in ("_START", "_END"):
                continue
            # 1) Chercher l'id
            search_data = self.jdm_client.search_node(node.word)
            if not search_data:
                continue
            node.node_id = search_data.get("id", 0)
            # 2) Récupérer les relations
            rels = self.jdm_client.get_node_relations(node.node_id)
            # rels est typiquement une liste de dict
            for rdict in rels:
                rel_type_id = rdict.get("rel_type")
                node2_id = rdict.get("node2_id")
                weight = rdict.get("weight", 0)
                # Ex: pour un id de type 1 => r_syn, 10 => r_isa... (à adapter)
                # Pour la démo, imaginons que 10 => "r_isa", 1 => "r_syn"
                if rel_type_id == 10:
                    rel_str = "r_isa"
                elif rel_type_id == 1:
                    rel_str = "r_syn"
                else:
                    # On ignore
                    continue
                # On crée un noeud "JDM_xxx" (simplifié)
                node2_word = f"JDM_{node2_id}"
                n2 = graph.get_or_create_node(node2_word)
                graph.add_relation(node, n2, rel_str, weight)

    def apply_inference(self, graph: SemanticGraph) -> None:
        """
        Ex: A r_isa C et C r_agent X => A r_agent X
        """
        changed = True
        max_iter = 5
        while changed and max_iter > 0:
            max_iter -= 1
            changed = False
            # On récupère toutes les r_isa
            isa_list = [r for r in graph.relations if r.rel_type == "r_isa"]
            # On récupère toutes les r_agent
            agent_list = [r for r in graph.relations if r.rel_type == "r_agent"]
            for isa_rel in isa_list:
                A = isa_rel.source_node
                C = isa_rel.target_node
                # Cherchons si C a un r_agent verbe
                for r_ag in agent_list:
                    if r_ag.source_node == C:
                        # C r_agent X => A r_agent X
                        X = r_ag.target_node
                        # Vérifions si (A, r_agent, X) existe déjà
                        existing = graph.get_relations_between(A, X)
                        if not any(rr.rel_type == "r_agent" for rr in existing):
                            graph.add_relation(A, X, "r_agent")
                            changed = True

###############################################################################
#                       SYNTAX RULES
###############################################################################

class SyntaxRules:
    @staticmethod
    def rule_noun_phrase(graph: SemanticGraph) -> bool:
        """
        Rechercher Det + Nom => GN (ou Det + Adj* + Nom).
        """
        changed = False
        for node in list(graph.nodes.values()):
            if "Det" in node.pos_tags:
                current = node
                adjs = []
                while True:
                    succ = next((r for r in current.relations if r.rel_type == "r_succ"), None)
                    if not succ:
                        break
                    nxt = succ.target_node
                    if "Adj" in nxt.pos_tags:
                        adjs.append(nxt)
                        current = nxt
                    elif "Nom" in nxt.pos_tags:
                        # on a Det + adjs + Nom
                        phrase = " ".join([node.word] + [a.word for a in adjs] + [nxt.word])
                        if not graph.get_node(phrase):
                            gn_node = Node(phrase, node_type="GN")
                            gn_node.head_token = nxt
                            graph.add_node(gn_node)
                        changed = True
                        break
                    else:
                        break
        return changed

    @staticmethod
    def rule_passive_form(graph: SemanticGraph) -> bool:
        """
        Gère (GN) + est + (mangé) + par + GN => GN2 r_agent manger GN1
        Simplifié (pas de lemmatisation).
        """
        changed = False
        # On cherche un pattern : GN1 -> est -> (mot) -> par -> GN2
        # (mot) doit être un verbe (ex. mangé/e) => "V" ou "VPP"
        # On ne fait pas la distinction ici, c'est un code d'exemple.
        # ...
        # Ex: "la souris est mangée par le chat"
        
        for gn1 in list(graph.nodes.values()):
            if gn1.node_type == "GN" and gn1.head_token:
                # Chercher "est" en r_succ depuis le head_token
                r_est = next((r for r in gn1.head_token.relations if r.rel_type == "r_succ"), None)
                if not r_est:
                    continue
                est_node = r_est.target_node
                if "V" not in est_node.pos_tags:
                    continue
                # ok, c'est "est"
                # next => un verbe ou "mange/mangée"
                r_vpp = next((r for r in est_node.relations if r.rel_type == "r_succ"), None)
                if not r_vpp:
                    continue
                vpp_node = r_vpp.target_node
                # on suppose "V" => verbe, "None" => pas taggué...
                # on part du principe "mangée" n'a pas été reconnu. On fera simple.
                
                # ensuite => "par"
                r_par = next((r for r in vpp_node.relations if r.rel_type == "r_succ"), None)
                if not r_par:
                    continue
                par_node = r_par.target_node
                if par_node.word != "par":
                    continue
                
                # ensuite => GN2
                r_gn2 = next((r for r in par_node.relations if r.rel_type == "r_succ"), None)
                if not r_gn2:
                    continue
                gn2_candidate = r_gn2.target_node
                if gn2_candidate.node_type == "GN" or "Nom" in gn2_candidate.pos_tags:
                    # on a "gn2_candidate r_agent vpp_node" + "vpp_node r_patient gn1"
                    # On ne fait pas de lemmatisation sur vpp_node
                    graph.add_relation(gn2_candidate, vpp_node, "r_agent")
                    graph.add_relation(vpp_node, gn1, "r_patient")
                    changed = True
        return changed

    @staticmethod
    def rule_subject_verb(graph: SemanticGraph) -> bool:
        changed = False
        # GN + verbe => GN r_agent verbe
        for node in list(graph.nodes.values()):
            if node.node_type == "GN":
                # On regarde s'il y a un r_succ depuis .head_token
                if node.head_token:
                    succ_rel = next((r for r in node.head_token.relations if r.rel_type == "r_succ"), None)
                    if succ_rel:
                        v_node = succ_rel.target_node
                        if "V" in v_node.pos_tags:
                            graph.add_relation(node, v_node, "r_agent")
                            changed = True
            elif "Nom" in node.pos_tags:
                # pattern Nom -> verbe
                succ_rel = next((r for r in node.relations if r.rel_type == "r_succ"), None)
                if succ_rel and "V" in succ_rel.target_node.pos_tags:
                    graph.add_relation(node, succ_rel.target_node, "r_agent")
                    changed = True
        return changed

    @staticmethod
    def rule_verb_object(graph: SemanticGraph) -> bool:
        changed = False
        # Verbe -> GN => verbe r_patient GN
        for node in list(graph.nodes.values()):
            if "V" in node.pos_tags:
                succ_rel = next((r for r in node.relations if r.rel_type == "r_succ"), None)
                if succ_rel:
                    obj_node = succ_rel.target_node
                    if obj_node.node_type == "GN" or "Nom" in obj_node.pos_tags:
                        graph.add_relation(node, obj_node, "r_patient")
                        changed = True
        return changed

    @staticmethod
    def rule_negation(graph: SemanticGraph) -> bool:
        changed = False
        # ex: n' -> aime => n' -r_neg-> aime
        # ou ne -> verbe
        for node in list(graph.nodes.values()):
            if "Neg" in node.pos_tags:
                # On cherche un verbe en r_succ
                succ_rel = next((r for r in node.relations if r.rel_type == "r_succ"), None)
                if succ_rel and "V" in succ_rel.target_node.pos_tags:
                    graph.add_relation(node, succ_rel.target_node, "r_neg")
                    changed = True
        return changed

###############################################################################
#                          PRINT & MAIN
###############################################################################

def print_analysis_results(graph: SemanticGraph) -> None:
    print("\n===== NODES =====")
    for node in graph.nodes.values():
        pos_str = ",".join(node.pos_tags) if node.pos_tags else "None"
        print(f" - {node.word} (type={node.node_type}, POS=[{pos_str}], weight={node.weight:.2f})")
    
    print("\n===== RELATIONS =====")
    for rel in graph.relations:
        if rel.weight > 0:
            print(f" - {rel.source_node.word} -{rel.rel_type}-> {rel.target_node.word} (weight={rel.weight})")

def print_semantic_relations(graph: SemanticGraph) -> None:
    """
    On affiche seulement les relations qu'on juge 'sémantiques'
    (r_agent, r_patient, r_neg, r_isa, r_syn, etc.)
    """
    print("\n===== SEMANTIC RELATIONS =====")
    for rel in graph.relations:
        if rel.rel_type in ("r_agent", "r_patient", "r_neg", "r_isa", "r_syn"):
            print(f"{rel.source_node.word} -{rel.rel_type}-> {rel.target_node.word}")

def main():
    analyzer = SemanticAnalyzer(compound_file="compound_terms.txt", max_rule_iterations=5)
    
    test_sentences = [
        "le chat boit du lait",
        "la souris est mangée par le chat",
        "le petit chat n'aime pas le lait de chèvre",
        "le chien est tombé dans le puits. Il a pleuré toute la nuit",
        "l'algorithme a été présenté en cours. Il est difficile de l'implémenter."
    ]
    
    for sentence in test_sentences:
        print(f"\n=== Analyzing: {sentence} ===")
        graph = analyzer.analyze(sentence)
        print_analysis_results(graph)
        print_semantic_relations(graph)

if __name__ == "__main__":
    main()
