import sys
import datetime
import io
import pathlib

import pandas as pd

from . import config


substitution_keys = ("*", "+", "^", "&", "$")


def process_source(game, value):
    title, d = (x.strip() for x in value.split(",", 1))
    d = datetime.datetime.strptime(d, "%B %d, %Y")
    d = d.strftime("%Y-%m-%d")
    game["source"] = {"title": title, "date": d}
    return game


def process_status(game, status):
    if "," in status:
        status, reason = (x.strip() for x in status.split(","))
    else:
        status, reason = status.strip(), ""
    if status in ["postponed", "completed early", "abandoned"]:
        game["status"]["code"] = status
    else:
        print(f"Unknown status '{status}'")
        sys.exit(1)
    if reason:
        game["status"]["reason"] = reason
    return game


def process_linescore(game: dict, value: str):
    try:
        club, score = (x.strip() for x in value.split(":"))
    except ValueError:
        print(f"ERROR: Ill-formed linescore string '{value}'")
        return

    for team in game["teams"]:
        if club == team["name"]:
            break
    else:
        print(f"Unknown team '{club}' in linescore")
        return
    
    byinning, total = map(lambda x: x.strip(), score.split("-"))
    try:
        int(total)
    except ValueError:
        print(f"ERROR: Ill-formed linescore string '{value}'")

    team["score"] = total
    team["innings"] = [x.lower() for x in byinning.split(" ")]
    return game


def parse_name(text: str) -> dict:
    """Parse out a personal name in form 'last, first'.  Return as a dict."""
    if "," in text:
        return dict(zip(['last', 'first'],
                        (x.strip() for x in text.split(","))))
    else:
        return {'last': text.strip()}


def parse_umpires(game: dict, value: str):
    for name in value.split(";"):
        game["umpires"].append(parse_name(name))


def parse_date(game: dict, value: str):
    game['data']['date'] = value
    game['data']['season'] = value[:4]


def parse_number(game: dict, value: str):
    game['data']['number'] = value


def parse_league(game: dict, value: str):
    if "League" not in value and "Association" not in value:
        value = value + " League"
    game['data']['league'] = value
    for team in game['teams']:
        team['league'] = value


def parse_team(game: dict, align: int, value: str):
    game['teams'][align]['name'] = value


def parse_duration(game: dict, value: str):
    game['data']['duration'] = value


def parse_player_table(team: dict, data):
    while True:
        k, v = next(data)
        if k == "TOTALS":
            break
        name, pos = (x.strip() for x in k.split("@"))
        name = name.split(")")[-1]
        if name.startswith(substitution_keys):
            name = name[1:]
        team['players'].append(dict(
            **parse_name(name),
            **{'pos': pos}
        ))


def extract_pairs(text: str):
    for line in (x.strip() for x in text.split("\n")):
        if not line:
            continue
        yield tuple(x.strip() for x in line.split(":", 1))


def parse_game(text: str) -> dict:
    game = {"data": {},
            "teams":
                 [{'alignment': "away", 'name': None, 'league': None,
                   'players': []},
                  {'alignment': "home", 'name': None, 'league': None,
                   'players': []}],
            "umpires": []
           }
    dispatch = {
        'date': parse_date,
        'number': parse_number,
        'league': parse_league,
        'T': parse_duration,
        'U': parse_umpires,
        'away': lambda g, v: parse_team(g, 0, v),
        'home': lambda g, v: parse_team(g, 1, v),
        'line': process_linescore
    }
    data = extract_pairs(text)
    try:
        while True:
            k, v = next(data)
            for team in game['teams']:
                if k == team['name']:
                    parse_player_table(team, data)
            try:
                fn = dispatch[k]
            except KeyError:
                continue
            fn(game, v)
    except StopIteration:
        pass
    return game


def separate_games(fn: pathlib.Path):
    """Iterate over the games in 'fn' and separate the text of each."""
    game = io.StringIO()
    with fn.open() as f:
        for line in f:
            if line.startswith("---"):
                yield game.getvalue()
                game = io.StringIO()
            else:
                game.write(line)
    value = game.getvalue().strip()
    if value:
        yield value


def process_files(inpath: pathlib.Path):
    fnlist = [fn for fn in sorted(inpath.glob("*.txt"))
              if fn.name.lower() not in ["readme.txt", "notes.txt"]]
    if not fnlist:
        print_error(f"No files found at '{inpath}'")
        sys.exit(1)
    return [
        parse_game(game)
        for fn in fnlist
        for game in separate_games(fn)
    ]


def index_games(games: list) -> pd.DataFrame:
    df = pd.DataFrame(
        [{'game.id': i,
          'key': None,
          'season': game['data']['season'],
          'date': game['data']['date'],
          'number': game['data']['number'],
          'league': game['data']['league']}
        for (i, game) in enumerate(games)]
    )
    return df


def index_teams(games: list) -> pd.DataFrame:
    df = pd.DataFrame([
        {'game.id': i,
         'team.name': team['name'],
         'team.league': team['league'],
         'team.align': team['alignment'][0],
         'team.score': team.get('score', None)}
        for (i, game) in enumerate(games)
        for team in game['teams']
    ])
    return df


def index_players(games: list) -> pd.DataFrame:
    return pd.DataFrame([
        {'game.id': i,
         'team.name': team['name'],
         'team.league': team['league'],
         'person.name.last': player['last'],
         'person.name.first': player.get('first', None),
         'pos': player['pos']}
        for (i, game) in enumerate(games)
        for team in game['teams']
        for player in team['players']
    ])


def identify_teams(df: pd.DataFrame) -> pd.DataFrame:
    index = pd.read_csv("teams.csv")
    return df.merge(index, how='left', on=['team.league', 'team.name'])


def identify_games(df: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    return (
        df
        .merge(teams.query("`team.align` == 'a'")
               [['game.id',
                 'team.name', 'team.align', 'team.score', 'team.key']]
               .rename(columns=lambda x: x.replace('team.', 'team1.')),
                how='left', on='game.id')
        .merge(teams.query("`team.align` == 'h'")
               [['game.id',
                 'team.name', 'team.align', 'team.score', 'team.key']]
               .rename(columns=lambda x: x.replace('team.', 'team2.')),
                how='left', on='game.id')
        .assign(**{
            'key': lambda x: (
                x['date'].str.replace("-", "") + "-" +
                x[['team1.key', 'team2.key']].fillna("").min(axis='columns') +
                "-" +
                x[['team1.key', 'team2.key']].fillna("").max(axis='columns') +
                "-" +
                x['number']
            )
        })
    )


def main(source: str):
    try:
        year, paper = source.split("-")
    except ValueError:
        print_error(f"Invalid source name '{source}'")
        sys.exit(1)

    inpath = config.data_path/"transcript"/year/source
    data = process_files(inpath)
    #teams = pd.read_csv("teams.csv", index_col=['league', 'team'])
    #for game in games:
    #    identify_teams(game, teams)
    games_teams = index_teams(data).pipe(identify_teams)
    games_teams.to_csv("games_teams.csv", index=False, float_format='%d')
    games = index_games(data).pipe(identify_games, games_teams)
    games.to_csv("games.csv", index=False, float_format='%d')
    players = (
        index_players(data)
       .merge(games[['game.id', 'key']], how='left', on='game.id')
       .reindex(columns=['team.league', 'team.name',
                         'key',
                         'person.name',
                         'person.name.last', 'person.name.first', 'pos'])
       .sort_values(['team.league', 'team.name',
                     'person.name.last', 'key'])
    )
    players.to_csv("games_players.csv", index=False, float_format='%d')


