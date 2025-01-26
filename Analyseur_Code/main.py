# main.py

from semantic_pipeline import GlobalAnalyzer

def main():
    sample_text = "Le petit chat boit du lait de chèvre. Il est si mignon!"
    analyzer = GlobalAnalyzer()
    analyzer(sample_text)
    analyzer.generate_image(out_file="analyse_result3.png", graph_title="Analyse Sémantique")

if __name__ == "__main__":
    main()
