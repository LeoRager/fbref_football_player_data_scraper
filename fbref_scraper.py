from bs4 import BeautifulSoup as soup
import requests
import pandas as pd
import time
import re
from functools import reduce
import sys
from urllib.error import HTTPError

'''
This program will get summary player data for each game played in the top 5 
European football leagues from the website fbref.com
'''

def get_data_info():
    # all possible leagues and seasons
    leagues = ['Premier League', 'La Liga', 'Serie A', 'Ligue 1', 'Bundesliga', 'Big5', 'Eredivisie']

    while True:
        # select league [Premier League / La Liga / Serie A / Ligue 1 / Bundesliga]
        league = input('Select League (Premier League / La Liga / Serie A / Ligue 1 / Bundesliga / Big5): ')

        # check if input valid
        if league not in leagues:
            print('League not valid, try again')
            continue

        # assign url names and id's
        if league == 'Premier League':
            league = 'Premier-League'
            league_id = '9'

        if league == 'La Liga':
            league = 'La-Liga'
            league_id = '12'

        if league == 'Serie A':
            league = 'Serie-A'
            league_id = '11'

        if league == 'Ligue 1':
            league = 'Ligue-1'
            league_id = '13'

        if league == 'Bundesliga':
            league = 'Bundesliga'
            league_id = '20'

        if league == 'Big5':
            league = 'Big-5-European-Leagues'
            league_id = 'Big5'

        if league == 'Eredivisie':
            league = 'Eredivisie'
            league_id = '23'

        break

    while True:
        # select season after 2017 as XG only available from 2017,
        season = input('Select Season: ')

        # check if input valid
        if not re.match(r'^20\d{2}-20\d{2}$', season):
            print('Season not valid, try again')
            continue
        break

    url = f'https://fbref.com/en/comps/{league_id}/{season}/schedule/{season}-{league}-Scores-and-Fixtures'
    player_url = f'https://fbref.com/en/comps/{league_id}/{season}/stats/players/{season}-{league}-Stats'
    return url, player_url, league, season


def get_fixture_data(url, league, season):
    print('Getting fixture data...')
    # create empty data frame and access all tables in url
    fixturedata = pd.DataFrame([])
    tables = pd.read_html(url)

    # get fixtures
    fixtures = tables[0][['Wk', 'Day', 'Date', 'Time', 'Home', 'Away', 'xG', 'xG.1', 'Score']].dropna()
    fixtures['season'] = url.split('/')[6]
    fixturedata = pd.concat([fixturedata,fixtures])

    # assign id for each game
    fixturedata["game_id"] = fixturedata.index

    # export to csv file
    fixturedata.reset_index(drop=True).to_csv(f'{league.lower()}_{season.lower()}_fixture_data.csv',
        header=True, index=False, mode='w')
    print('Fixture data collected...')


def get_match_links(url, league):
    print('Getting player data...')
    # access and download content from url containing all fixture links
    match_links = []
    html = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    links = soup(html.content, "html.parser").find_all('a')

    # filter list to return only needed links
    key_words_good = ['/en/matches/', f'{league}']
    for l in links:
        href = l.get('href', '')
        if all(x in href for x in key_words_good):
            if 'https://fbref.com' + href not in match_links:
                match_links.append('https://fbref.com' + href)
    return match_links

def my_player_data(player_url, league, season):
    print('Getting player data from the stats page...')
    try:
        # Request the HTML page content
        response = requests.get(player_url, headers={'User-Agent': 'Mozilla/5.0'})
        response.raise_for_status()  # Raise an HTTPError for bad responses

        # Parse the page content
        print('Parsing the page content...')
        page_soup = soup(response.content, "html.parser")

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
        player_data = player_data[player_data['Rk'].str.isnumeric()]

        # Set 'Rk' column as the index
        player_data.set_index('Rk', inplace=True)

        # Drop the 'Matches' column
        player_data.drop('Matches', axis=1, inplace=True)

        # Add the suffix 'p90' to the last 10 columns headers
        player_data.columns = player_data.columns[:-10].tolist() + [col + '_p90' for col in player_data.columns[-10:]]

        # Save the DataFrame to a CSV file
        player_data.to_csv(f'{league.lower()}_{season.lower()}_player_stats.csv', header=True, index=False)

        print(f'Player data for {season} season in {league} collected successfully.')
    except Exception as e:
        print(f'An error occurred while fetching player data: {e}')


def player_data(match_links, league, season):
    # loop through all fixtures
    player_data = pd.DataFrame([])
    for count, link in enumerate(match_links):
        try:
            tables = pd.read_html(link)
            for table in tables:
                try:
                    table.columns = table.columns.droplevel()
                except Exception:
                    continue

            # get player data
            def get_team_1_player_data():
                # outfield and goal keeper data stored in seperate tables
                data_frames = [tables[3], tables[9]]

                # merge outfield and goal keeper data
                df = reduce(lambda left, right: pd.merge(left, right,
                    on=['Player', 'Nation', 'Age', 'Min'], how='outer'), data_frames).iloc[:-1]

                # assign a home or away value
                return df.assign(home=1, game_id=count)

            # get second teams  player data
            def get_team_2_player_data():
                data_frames = [tables[10], tables[16]]
                df = reduce(lambda left, right: pd.merge(left, right,
                    on=['Player', 'Nation', 'Age', 'Min'], how='outer'), data_frames).iloc[:-1]
                return df.assign(home=0, game_id=count)

            # combine both team data and export all match data to csv
            t1 = get_team_1_player_data()
            t2 = get_team_2_player_data()
            player_data = pd.concat([player_data, pd.concat([t1,t2]).reset_index()])

            print(f'{count+1}/{len(match_links)} matches collected')
            player_data.to_csv(f'{league.lower()}_{season.lower()}_player_data.csv',
                header=True, index=False, mode='w')
        except:
            print(f'{link}: error')
        # sleep for 3 seconds after every game to avoid IP being blocked
        time.sleep(3)


# main function
def main():
    url, player_url, league, season = get_data_info()
    # get_fixture_data(url, league, season)
    # match_links = get_match_links(url, league)
    my_player_data(player_url, league, season)

    # checks if user wants to collect more data
    print('Data collected!')
    while True:
        answer = input('Do you want to collect more data? (yes/no): ')
        if answer == 'yes':
            main()
        if answer == 'no':
            sys.exit()
        else:
            print('Answer not valid')
            continue


if __name__ == '__main__':
    try:
        main()
    except HTTPError:
        print('The website refused access, try again later')
        time.sleep(5)


