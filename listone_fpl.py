import pandas as pd
import tkinter as tk
from tkinter import filedialog
import math
import unidecode
import re

# Open a tkinter file dialog to select the file
def open_file():
    root = tk.Tk()
    root.attributes("-topmost", True)  # Force the window to be on top
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")], parent=root)
    return file_path


def match_full_name(player_name, name_map):
    # Split the player's full name into first name and last names
    player_name_parts = player_name.split()
    if len(player_name_parts) < 2:
        return False

    first_name = player_name_parts[0]
    last_name_parts = set(player_name_parts[1:])

    # Check if first name exists in the name_map and there's an intersection with last name parts
    return first_name in name_map and not last_name_parts.isdisjoint(name_map[first_name])


# Define the create_dataframe function
def create_dataframe(league_df, all_players_df):
    # Step 1: Create dictionaries mapping first names to sets of last name components and additional columns
    name_map = {}
    element_type_map = {}
    goals_conceded_map = {}
    minutes_map = {}

    for _, row in league_df.iterrows():
        first_name = row['first_name']
        last_name_parts = set(row['second_name'].split())
        name_map[first_name] = name_map.get(first_name, set()).union(last_name_parts)
        element_type_map[first_name] = row['element_type']
        goals_conceded_map[first_name] = row['goals_conceded']
        minutes_map[first_name] = row['minutes']

    # Step 2: Filter all_players_df using the match_full_name function
    filtered_df = all_players_df[all_players_df['Player'].apply(lambda x: match_full_name(x, name_map))]

    # Step 3: Merge the additional columns from league_df into filtered_df
    def get_additional_info(player_name, info_map):
        first_name = player_name.split()[0]
        return info_map.get(first_name)

    filtered_df['element_type'] = filtered_df['Player'].apply(lambda x: get_additional_info(x, element_type_map))
    filtered_df['goals_conceded'] = filtered_df['Player'].apply(lambda x: get_additional_info(x, goals_conceded_map))
    filtered_df['minutes'] = filtered_df['Player'].apply(lambda x: get_additional_info(x, minutes_map))

    return filtered_df

def estimate_clean_sheets(total_minutes, total_goals_conceded, match_duration=90):
    number_of_matches = total_minutes / match_duration
    if number_of_matches == 0:
        return 0

    average_goals_per_match = total_goals_conceded / number_of_matches
    probability_clean_sheet = math.exp(-average_goals_per_match)
    estimated_clean_sheets = probability_clean_sheet * number_of_matches
    return estimated_clean_sheets


def create_xB(filtered_df):
    # Create a new column 'xB' with initial calculations
    def calculate_xB(row):
        # Multipliers based on element_type
        type_multipliers = {
            'GK': 10,
            'DEF': 6,
            'MID': 5,
            'FWD': 4
        }
        multiplier = type_multipliers.get(row['element_type'], 0)

        # Base calculation for xB
        xB = (row['xG'] * multiplier) + (row['xAG'] * 3)

        # Add adjustment based on estimated clean sheets for GK and DEF
        # if row['element_type'] in ['GK', 'DEF']:
        #     est_clean_sheets = estimate_clean_sheets(row['minutes'], row['goals_conceded'])
        #     xB += est_clean_sheets * 4
        # elif row['element_type'] == 'MID':
        #     est_clean_sheets = estimate_clean_sheets(row['minutes'], row['goals_conceded'])
        #     xB += est_clean_sheets * 1

        return xB

    # Apply the calculation to each row and create the 'xB' column
    filtered_df['xB'] = filtered_df.apply(calculate_xB, axis=1)

    return filtered_df


def combined_players(filtered_df):
    # Step 1: Copy the dataframe and keep only the relevant columns
    df_reduced = filtered_df[['Player', 'minutes', 'xB', 'season', 'Min']].copy()

    # Step 2: Group by 'Player' and 'season', summing the numerical columns
    df_summed = df_reduced.groupby(['Player', 'season'], as_index=False).sum()

    # Step 3: Group by 'Player' to average the numerical columns where 'season' entries are identical
    df_combined = df_summed.groupby('Player', as_index=False).agg({
        'minutes': 'mean',
        'Min': 'mean',
        'xB': 'mean',
        'season': 'first'  # Keep the 'season' value as it is, because it's the same for all seasons for each player
    })

    # Step 4: Create xB per 90 minutes column using 'min', out anything below 900 minutes set to 0
    df_combined['xB_p90'] = df_combined['xB'] / df_combined['Min'] * 90
    df_combined.loc[df_combined['Min'] < 900, 'xB_p90'] = 0

    return df_combined

if __name__ == '__main__':
    # Open file dialogs to select the files
    pl_file_path = open_file()
    all_players_file_path = 'combined_2023-2024.csv'
    all_players_file_path_2022_23 = 'combined_2022-2023.csv'

    # Load dataframes
    pl_df = pd.read_csv(pl_file_path)
    all_players_df = pd.read_csv(all_players_file_path)
    all_players_df_2022_23 = pd.read_csv(all_players_file_path_2022_23)

    # Add column season
    all_players_df['season'] = '2023-2024'
    all_players_df_2022_23['season'] = '2022-2023'

    # Merge the two dataframes
    all_players_df = pd.concat([all_players_df, all_players_df_2022_23], ignore_index=True)

    # Create the new dataframe with relevant information
    result_df = create_dataframe(pl_df, all_players_df)

    # Add expected bonus column
    result_df = create_xB(result_df)

    # Merge the players of the same name
    result_df= combined_players(result_df)

    # Save the new dataframe to a CSV file
    result_df.to_csv('fpl_listone.csv', index=False)

