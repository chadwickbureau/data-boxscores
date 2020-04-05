import pathlib

import pandas as pd
import toml

from . import config


def extract_players(games):
    return [{"game": {"key": game['game']['key'],
                      "date": game['game']['datetime']},
             "team": team['name'], "player": player}
            for game in games
            for team in game['team']
            for player in team.get('player', [])]


def main():
    inpath = config.data_path/"toml"
    games = []
    for fn in sorted(inpath.glob("1911/*/*.txt")):
        with fn.open() as f:
            games.append(toml.loads(f.read()))

    df = (
        pd.json_normalize(extract_players(games))
        [['player.source.name.last', 'player.source.name.first',
          'player.source.F_POS',
          'team', 'game.date']]
        .rename(columns={'player.source.name.last': 'name.last',
                         'player.source.name.first': 'name.first',
                         'player.source.F_POS': 'pos'})
        .sort_values(['team', 'name.last', 'game.date'])
    )
    df.to_csv("index.csv", index=False)
    
