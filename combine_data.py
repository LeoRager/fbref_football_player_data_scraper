"""
Scans through the data folder and combines all the CSV files that contain the same years in the same dataframe.
I.e. if the file name contains 2022-2023, combine all the files that contain 2022-2023 in the file name.
"""

import os
import pandas as pd


def combine_csv_files(data_folder):
    # Initialize empty dataframes for each year range
    combined_dataframes = {
        "2022-2023": pd.DataFrame(),
        "2023-2024": pd.DataFrame()
    }

    # Scan through the data folder
    for filename in os.listdir(data_folder):
        # Check if the file is a CSV
        if filename.endswith(".csv"):
            # Determine which year range the file belongs to
            if "2022-2023" in filename:
                year_range = "2022-2023"
            elif "2023-2024" in filename:
                year_range = "2023-2024"
            else:
                continue

            # Read the CSV file and concatenate it to the corresponding dataframe
            file_path = os.path.join(data_folder, filename)
            df = pd.read_csv(file_path)
            combined_dataframes[year_range] = pd.concat([combined_dataframes[year_range], df], ignore_index=True)

    return combined_dataframes


# Example usage
data_folder = './data'
combined_dfs = combine_csv_files(data_folder)

# Access the combined dataframes
df_2022_2023 = combined_dfs.get("2022-2023")
df_2023_2024 = combined_dfs.get("2023-2024")

# Optionally, save the combined dataframes to new CSV files
if not df_2022_2023.empty:
    df_2022_2023.to_csv("combined_2022-2023.csv", index=False)
if not df_2023_2024.empty:
    df_2023_2024.to_csv("combined_2023-2024.csv", index=False)
