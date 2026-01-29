from converter import MarkerConverter, LLMConverter
import os
import tqdm


def main():
    converter = MarkerConverter(source_format="pdf", target_format="markdown", use_LLM=True)
    llm_converter = LLMConverter("gemini-2.0-flash")

    restructure_path = f"{os.environ['HOME_DIR']}/IOI-Bench-Restructured"
    parse_path = f"{os.environ['HOME_DIR']}/IOI-Bench-Parsed"
    parse_statement = True
    parse_solution = False
    total = [0,0]
    total_missing_statements = []
    total_missing_editorials = []
    for competition in tqdm.tqdm(os.listdir(restructure_path)):
        competition_path = os.path.join(restructure_path, competition)
        if not os.path.isdir(os.path.join(restructure_path, competition)):
            continue
        parse_competition = os.path.join(parse_path, competition)

        print(f"Parsing {competition}")
        total_statement, total_editorials, _, _ = converter.parse_competition(
            competition_path,
            parse_competition,
            parse_statement=parse_statement,
            parse_solution=parse_solution,
            rerun=False,
        )
        print(f"Total statements parsed: {total_statement}")
        print(f"Total editorials parsed: {total_editorials}")
        # Parse the competition using LLMConverter
        total_statement, total_editorials, missing_statements, missing_editorials = llm_converter.parse_competition(
            competition_path,
            parse_competition,
            parse_statement=parse_statement,
            parse_solution=parse_solution,
            rerun=False,
        )
        total[0] += total_statement
        total[1] += total_editorials
        total_missing_statements.extend(missing_statements)
        total_missing_editorials.extend(missing_editorials)
    print(f"Total statements parsed: {total[0]}")
    print(f"Total editorials parsed: {total[1]}")
    print(f"Missing statements: ")
    for missing in total_missing_statements:
        print(missing)
    print(f"Missing editorials: ")
    for missing in total_missing_editorials:
        print(missing)

if __name__ == "__main__":
    main()
