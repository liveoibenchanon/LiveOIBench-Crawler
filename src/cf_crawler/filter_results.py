import os
import pandas as pd
from generate_results import remove_curve_outliers_auto

global count
count = 0

def filter_and_save(df, output_path):
    plot_dir = f"{os.environ['HOME_DIR']}/IOI-User_Database/model_rankings/human_plots"
    
    competition = output_path.split('/')[1]
    year = output_path.split('/')[2]
    contest = output_path.split('/')[3]
    if contest == "results.csv":
        contest_key = f"{competition}-{year}-contest"
    else:
        contest_key = f"{competition}-{year}-{contest}"
    if competition == "COCI" and "formal" not in contest:
        return
    
    df['Total'] = pd.to_numeric(df['Total'], errors='coerce')
    df['CF_Rating'] = pd.to_numeric(df['CF_Rating'], errors='coerce')
    ranked_humans = df.dropna(subset=['Total', 'CF_Rating'])
    ranked_humans = ranked_humans[ranked_humans['CF_Rating'] >= 500]
    if len(ranked_humans) == 0:
        print(f"!!!No ranked humans with CF_Rating >= 500 in {output_path}")
        ranked_humans.to_csv(output_path, index=False)
        return
    global count
    count += 1
    path = os.path.join(plot_dir, f"{contest_key}_human_plot.png")
    ranked_humans, removed, _ = remove_curve_outliers_auto(ranked_humans, path, std_threshold=2, max_degree=3, plot=True)
    print(f"Removed {len(removed)} outliers from human rankings in {output_path}")
    if len(ranked_humans) < 15:
        print(f"!Not enough ranked humans with CF_Rating >= 500 in {output_path}")
    ranked_humans = ranked_humans.sort_values('Total', ascending=False)
    ranked_humans.to_csv(output_path, index=False)
    print(f"Saved filtered human rankings to {output_path}")
    return

def process_csv_file(file_path, root_dir, output_root):
    relative_path = os.path.relpath(file_path, root_dir)
    relative_base = os.path.splitext(relative_path)[0]
    output_path = os.path.join(output_root, relative_base + '.csv')
    if "COCI" in output_path and "formal" not in output_path:
        return
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        df = pd.read_csv(file_path)
        if 'CF_Rating' not in df.columns:
            print(f"Skipped (no CF_Rating): {file_path}")
            return
        if 'Rank' not in df.columns:
            print(f"Skipped (no Rank): {file_path}")
            return

        filter_and_save(df, output_path)

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def process_all_csvs(root_dir, output_root="Results_filtered"):
    
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith('.csv'):
                file_path = os.path.join(dirpath, filename)
                process_csv_file(file_path, root_dir, output_root)
                
    print(f"Processed {count} CSV files.")


process_all_csvs("Results_sample", "Results_filtered")
