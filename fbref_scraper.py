from bs4 import BeautifulSoup as soup
import requests
import pandas as pd
import time
import re
from functools import reduce
import sys
from urllib.error import HTTPError
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

'''
This program will get summary player data for each game played in the top 5 
European football leagues from the website fbref.com
'''

def get_data_info():
    # all possible leagues and seasons
    leagues = ['Big5', 'Eredivisie', 'Primeira Liga', 'Serie B']

    while True:
        # Populate input for league naming what leagues are available
        str_leagues = ', '.join(leagues)
        league = input(f'Select League: {str_leagues}\n')

        # check if input valid
        if league not in leagues:
            print('League not valid, try again')
            continue

        # assign url names and id's
        if league == 'Big5':
            league = 'Big-5-European-Leagues'
            league_id = 'Big5'
            country = None

        if league == 'Eredivisie':
            league = 'Eredivisie'
            league_id = '23'
            country = 'ne'

        if league == 'Primeira Liga':
            league = 'Primeira-Liga'
            league_id = '32'
            country = 'pt'

        if league == 'Serie B':
            league = 'Serie-B'
            league_id = '18'
            country = 'it'

        break

    while True:
        # select season after 2017 as XG only available from 2017,
        season = input('Select Season: ')

        # check if input valid
        if not re.match(r'^20\d{2}-20\d{2}$', season):
            print('Season not valid, try again')
            continue
        break

    # url = f'https://fbref.com/en/comps/{league_id}/{season}/schedule/{season}-{league}-Scores-and-Fixtures'
    player_url = f'https://fbref.com/en/comps/{league_id}/{season}/stats/players/{season}-{league}-Stats'
    return player_url, league, season, country


def player_data(player_url, league, season, country):
    print('Getting player data from the stats page...')
    try:
        # Set up the Selenium WebDriver
        driver = webdriver.Chrome()  # Or use webdriver.Firefox() for Firefox
        driver.get(player_url)

        # Wait until the specific element (table container) is loaded
        try:
            element_present = EC.presence_of_element_located((By.ID, 'div_stats_standard'))
            WebDriverWait(driver, 10).until(element_present)
        except TimeoutException:
            print("Timed out waiting for page to load")
            driver.quit()
            return

        # Get the page source after JavaScript has loaded content
        html_content = driver.page_source

        # Parse the page content with BeautifulSoup
        print('Parsing the page content...')
        page_soup = soup(html_content, "html.parser")

        # Find the table with the id 'stats_standard'
        table = page_soup.find('table', id='stats_standard')

        # Use pandas to read the HTML table into a DataFrame
        print('Reading the HTML table into a DataFrame...')
        player_data = pd.read_html(str(table))[0]

        # Drop multi-level column indexing if it exists
        if isinstance(player_data.columns, pd.MultiIndex):
            player_data.columns = player_data.columns.droplevel()

        # Clean up DataFrame: remove unwanted rows and columns if necessary
        # For example, removing rows where Player column is NaN
        player_data = player_data[player_data['Player'].notna()]

        # Drop all rows where 'Rk' is not a number
        player_data = player_data[player_data['Rk'].astype(str).str.isnumeric()]

        # Set 'Rk' column as the index
        player_data.set_index('Rk', inplace=True)

        # Drop the 'Matches' column if it exists
        if 'Matches' in player_data.columns:
            player_data.drop('Matches', axis=1, inplace=True)

        # Add the suffix 'p90' to the last 10 columns headers
        player_data.columns = player_data.columns[:-10].tolist() + [col + '_p90' for col in player_data.columns[-10:]]

        # If the 'Comp' column does not exist, insert it in position 4 and populate it with f'{country} {league}'
        if 'Comp' not in player_data.columns:
            player_data.insert(4, 'Comp', f'{country} {league}')

        # Save the DataFrame to a CSV file
        player_data.to_csv(f'./data/{league.lower()}_{season.lower()}_player_stats.csv', header=True, index=False)

        print(f'Player data for {season} season in {league} collected successfully.')
    except Exception as e:
        print(f'An error occurred while fetching player data: {e}')
    finally:
        # Close the Selenium WebDriver
        driver.quit()


# main function
def main():
    player_url, league, season, country = get_data_info()
    player_data(player_url, league, season,country)

    print('Data collected!')

    return


if __name__ == '__main__':
    try:
        main()
    except HTTPError:
        print('The website refused access, try again later')
        time.sleep(5)


