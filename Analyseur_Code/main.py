from semantic_pipeline import GlobalAnalyzer

def main():
    sample_text = "Le petit chat boit du lait de chèvre. Il est si mignon!"
    print(f"Analysing text: {sample_text}")
    analyzer = GlobalAnalyzer()
    analyzer(sample_text)
    print("Analysis finished")
    analyzer.generate_image(out_file="analyse_result013.png", graph_title="Analyse Sémantique")
    print("Image generated at analyse_result.png")

if __name__ == "__main__":
    main()