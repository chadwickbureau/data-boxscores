import sys
import pathlib

import pandas as pd
import yaml


def extract_team(team):
    return {
        'name': team['name'],
        'league': team['league'],
        'alignment': team['alignment'],
        'score': team.get('score', {}).get('total', None)
    }

def extract_games(source: str, games: list):
    df = pd.json_normalize([
        {
            'source': game['source'],
            'game': game['game'],
            'team1': extract_team(game['teams'][0]),
            'team2': extract_team(game['teams'][1])
        }
        for game in games
    ])
    df.to_csv(f"{source}-games.csv", index=False)


def extract_players(source: str, games: list):
    df = pd.json_normalize([
        {
            'source': {
                'key': game['source']['key']
            },
            'game': {
                'date': game['game']['date'],
                'number': game['game']['number']
            },
            'team': {
                'name': team['name']
            },
            'player': player
        }
        for game in games
        for team in game['teams']
        for player in team['players']
    ])
    df.to_csv(f"{source}-players.csv", index=False)


def main(source: str):
    games = []
    for fn in sorted(pathlib.Path(".").glob("*.yml")):
        print(fn)
        with fn.open() as f:
            games.extend(list(yaml.safe_load_all(f)))
    extract_games(source, games)
    extract_players(source, games)


if __name__ == '__main__':
    main(sys.argv[1])

    
