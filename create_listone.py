import pandas as pd
import tkinter as tk
from tkinter import filedialog
import unidecode
import re

# Open a tkinter file dialog to select the file
def open_file():
    root = tk.Tk()
    root.attributes("-topmost", True)  # Force the window to be on top
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")], parent=root)
    return file_path


def normalize_name(name):
    # Remove accents
    name = unidecode.unidecode(name)

    # Split the name into segments
    segments = name.strip().split()

    # Determine the relevant segments based on the last segment
    if segments and segments[-1].endswith('.'):
        if len(segments) > 1:
            # Keep the last and second-to-last segments
            relevant_name = f"{segments[-2]} {segments[-1]}"
        else:
            # If there's only one segment and it ends with a period, keep it as is
            relevant_name = segments[-1]
    else:
        # Otherwise, keep only the last segment
        relevant_name = segments[-1]

    # Remove non-alphabetic characters (excluding spaces)
    cleaned_name = re.sub(r'[^a-zA-Z\s]', '', relevant_name)

    return cleaned_name.strip().lower()


def extract_last_name(full_name):
    # Split the full name and take the last part as the last name
    parts = full_name.split()
    return parts[-1]


def make_unique_names(df):
    df['unique_last_name'] = df['Last_name_normalized']
    df['First_name_initial'] = df['Player'].apply(lambda x: ''.join([part[0] for part in x.split()[:-1]]).lower())
    df['First_name_full'] = df['Player'].apply(lambda x: ''.join([part for part in x.split()[:-1]]).lower())

    # Identify rows with the same player name to allow duplicates
    df['player_count'] = df.groupby(['Player']).cumcount() + 1
    df['player_total'] = df.groupby(['Player'])['Player'].transform('count')

    duplicates = (df.duplicated(subset=['unique_last_name'], keep=False) &
                  (df['player_total'] == 1) &
                  (df['First_name_initial'] != ''))

    if duplicates.any():
        # Add a whitespace after the last name to avoid merging with other names
        df.loc[duplicates, 'unique_last_name'] += ' '

    while duplicates.any():
        df.loc[duplicates, 'unique_last_name'] += df.loc[duplicates, 'First_name_full'].str[:1]
        df['First_name_full'] = df['First_name_full'].apply(lambda x: x[1:] if len(x) > 1 else x)
        duplicates = (df.duplicated(subset=['unique_last_name'], keep=False) &
                      (df['player_total'] == 1) &
                      (df['First_name_initial'] != ''))

    return df


def create_dataframe(serie_a_df, all_players_df):
    # Normalize last names in serie_a_df
    serie_a_df['Nome_normalized'] = serie_a_df['Nome'].apply(normalize_name)

    # Extract and normalize last names in all_players_df
    all_players_df['Last_name'] = all_players_df['Player'].apply(extract_last_name)
    all_players_df['Last_name_normalized'] = all_players_df['Last_name'].apply(normalize_name)

    # Ensure unique last names with initials for all_players_df
    all_players_df = make_unique_names(all_players_df)

    # Merge dataframes on normalized last names
    merged_df = pd.merge(serie_a_df, all_players_df, left_on='Nome_normalized', right_on='unique_last_name', how='left')

    # Extract relevant columns
    result_df = merged_df[['Nome', 'Player', 'Min']]
    return result_df


if __name__ == '__main__':
    # Open file dialogs to select the files
    serie_a_file_path = open_file()
    all_players_file_path = './data/big-5-european-leagues_2023-2024_player_stats.csv'

    # Load dataframes
    serie_a_df = pd.read_csv(serie_a_file_path)
    all_players_df = pd.read_csv(all_players_file_path)

    # Create the new dataframe with relevant information
    result_df = create_dataframe(serie_a_df, all_players_df)

