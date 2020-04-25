import pathlib

import pandas as pd
import toml

from . import config


def extract_players(games):
    return [{"game": {"source": game['meta']['source']['title'],
                      "key": game['game']['key'],
                      "date": game['game']['datetime'],
                      "league": game['game']['league']},
             "team": team['name'], "player": player}
            for game in games
            for team in game['team']
            for player in team.get('player', [])]


def main(year: int):
    inpath = config.data_path/"toml"
    games = []
    for fn in sorted(inpath.glob(f"{year}/*/*.txt")):
        with fn.open() as f:
            games.append(toml.loads(f.read()))

    df = (
        pd.json_normalize(extract_players(games))
        [['player.source.name.last', 'player.source.name.first',
          'player.source.F_POS',
          'game.league', 'team', 'game.date', 'game.source']]
        .rename(columns={'player.source.name.last': 'name.last',
                         'player.source.name.first': 'name.first',
                         'player.source.F_POS': 'pos',
                         'game.league': 'league',
                         'game.source': 'source'})
        .sort_values(['league', 'team', 'name.last', 'game.date', 'source'])
    )
    df.to_csv(f"index-{year}.csv", index=False)
    
