import sys
import datetime
import io
import pathlib
import tabulate

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
    game = {
        "data": {},
        "teams": [
            {'alignment': "away", 'name': None, 'league': None,
             'players': []},
            {'alignment': "home", 'name': None, 'league': None,
             'players': []}
        ],
        "umpires": []
    }
    dispatch = {
        'date': parse_date,
        'number': parse_number,
        'league': parse_league,
        'T': parse_duration,
        'U': parse_umpires,
        'away': lambda g, val: parse_team(g, 0, val),
        'home': lambda g, val: parse_team(g, 1, val),
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
    if game['teams'][0]['name'] is None or game['teams'][1]['name'] is None:
        print(f"WARNING: Missing team")
        print(f"{game['data']['date']} {game['teams'][0]['name']} at {game['teams'][1]['name']}")
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
        print(f"No files found at '{inpath}'")
        sys.exit(1)
    return [
        parse_game(game)
        for fn in fnlist
        for game in separate_games(fn)
    ]


def index_games(games: list, source: str) -> pd.DataFrame:
    df = pd.DataFrame(
        [{'game.id': i,
          'source': source,
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
         'person.seq': f"{prefix}{j:02d}",
         'person.name.last': player['last'],
         'person.name.first': player.get('first', None),
         'pos': player['pos']}
        for (i, game) in enumerate(games)
        for (prefix, team) in zip(("a", "b"), game['teams'])
        for (j, player) in enumerate(team['players'])
    ])


def identify_teams(df: pd.DataFrame, year: int) -> pd.DataFrame:
    index = pd.read_csv(f"data/support/{year}/teams.csv")
    df = df.merge(index, how='left', on=['team.league', 'team.name'])
    unmatched = (
        df.query("`team.key`.isnull()")
        [['team.league', 'team.name']]
        .drop_duplicates()
        .sort_values(['team.league', 'team.name'])
    )
    if not unmatched.empty:
        print("The following teams were not matched to a key:")
        print(tabulate.tabulate(unmatched, headers='keys', showindex=False))
        sys.exit(1)
    return df


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


def update_player_index(path: pathlib.Path,
                        source: str, league: str,
                        df: pd.DataFrame) -> pd.DataFrame:
    """Update the player index for league with data from source."""
    league = league.replace(" ", "").replace("-", "")
    (path/league).mkdir(exist_ok=True, parents=True)
    dfcols = ['team.league', 'team.key',
              'team.name', 'source',
              'key',
              'gloss.name.last', 'gloss.name.first',
              'person.name.last', 'person.name.first',
              'person.seq', 'pos']
    try:
        index = pd.read_csv(path/league/"players.csv", usecols=dfcols).fillna("")
    except FileNotFoundError:
        index = pd.DataFrame(columns=dfcols)
    df = df.merge(index[['source', 'team.name', 'key',
                         'person.name.last', 'person.name.first',
                         'person.seq',
                         'gloss.name.last', 'gloss.name.first']],
                  how='left',
                  on=['source', 'team.name', 'key',
                      'person.name.last', 'person.name.first',
                      'person.seq'])
    index = (
        pd.concat([index.query(f"source != '{source}'"), df],
                  ignore_index=True, sort=False)
        .reindex(columns=dfcols)
        .fillna("")
        .assign(
            sortlast=lambda x: (
                x['gloss.name.last'].replace("", pd.NA)
                .fillna(x['person.name.last']).fillna("")
            ),
            sortfirst=lambda x: (
                x['gloss.name.first'].replace("", pd.NA)
                .fillna(x['person.name.first']).fillna(""))
        )
        .sort_values(['team.name', 'sortlast', 'sortfirst', 'key', 'source'])
        .drop(columns=['sortlast', 'sortfirst'])
    )
    index.to_csv(path/league/"players.csv", index=False, float_format='%d')
    return index


def main(source: str):
    try:
        year, paper = source.split("-")
    except ValueError:
        print(f"Invalid source name '{source}'")
        sys.exit(1)

    inpath = config.data_path/"transcript"/year/source
    outpath = pathlib.Path(f"data/index/{year}")
    outpath.mkdir(exist_ok=True, parents=True)

    data = process_files(inpath)
    games_teams = index_teams(data).pipe(identify_teams, year)
    # games_teams.to_csv("games_teams.csv", index=False, float_format='%d')
    games = index_games(data, source).pipe(identify_games, games_teams)
    # games.to_csv("games.csv", index=False, float_format='%d')
    players = (
        index_players(data).pipe(identify_teams, year)
        .merge(games[['game.id', 'source', 'key']], how='left', on='game.id')
        .reindex(columns=['team.league', 'team.key', 'team.name',
                          'source', 'key',
                          'gloss.name.last', 'gloss.name.first',
                          'person.name.last', 'person.name.first',
                          'person.seq', 'pos'])
        .sort_values(['team.league', 'team.name',
                      'person.name.last', 'key', 'source'])
    )
    for (league, group) in players.groupby('team.league'):
        print(f"Writing {len(group):5d} players for {league}")
        update_player_index(outpath, source, league, group)


def aggregate_players(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.assign(**{
            'last': lambda x: (
                x['gloss.name.last'].fillna(x['person.name.last']).fillna("")
            ),
            'given': lambda x: (
                x['gloss.name.first'].fillna(x['person.name.first']).fillna("")
            ),
            'date': lambda x: x['key'].str[:8],
            'F_P_G': lambda x: (x['pos'] == "p").astype(int),
            'F_C_G': lambda x: (x['pos'] == "c").astype(int),
            'F_1B_G': lambda x: (x['pos'] == "1b").astype(int),
            'F_2B_G': lambda x: (x['pos'] == "2b").astype(int),
            'F_3B_G': lambda x: (x['pos'] == "3b").astype(int),
            'F_SS_G': lambda x: (x['pos'] == "ss").astype(int),
            'F_LF_G': lambda x: (x['pos'] == "lf").astype(int),
            'F_CF_G': lambda x: (x['pos'] == "cf").astype(int),
            'F_RF_G': lambda x: (x['pos'] == "rf").astype(int)
        })
        .groupby(['team.league', 'team.name',
                  'last', 'given', 'date', 'key'])
        .agg(
            F_P_G=pd.NamedAgg(column='F_P_G', aggfunc=max),
            F_C_G=pd.NamedAgg(column='F_C_G', aggfunc=max),
            F_1B_G=pd.NamedAgg(column='F_1B_G', aggfunc=max),
            F_2B_G=pd.NamedAgg(column='F_2B_G', aggfunc=max),
            F_3B_G=pd.NamedAgg(column='F_3B_G', aggfunc=max),
            F_SS_G=pd.NamedAgg(column='F_SS_G', aggfunc=max),
            F_LF_G=pd.NamedAgg(column='F_LF_G', aggfunc=max),
            F_CF_G=pd.NamedAgg(column='F_CF_G', aggfunc=max),
            F_RF_G=pd.NamedAgg(column='F_RF_G', aggfunc=max),
        )
        .reset_index()
        .assign(B_G=1)
        .groupby(['team.league', 'team.name', 'last', 'given'])
        .agg(
            S_FIRST=pd.NamedAgg(column='date', aggfunc=min),
            S_LAST=pd.NamedAgg(column='date', aggfunc=max),
            B_G=pd.NamedAgg(column='B_G', aggfunc=sum),
            F_P_G=pd.NamedAgg(column='F_P_G', aggfunc=sum),
            F_C_G=pd.NamedAgg(column='F_C_G', aggfunc=sum),
            F_1B_G=pd.NamedAgg(column='F_1B_G', aggfunc=sum),
            F_2B_G=pd.NamedAgg(column='F_2B_G', aggfunc=sum),
            F_3B_G=pd.NamedAgg(column='F_3B_G', aggfunc=sum),
            F_SS_G=pd.NamedAgg(column='F_SS_G', aggfunc=sum),
            F_LF_G=pd.NamedAgg(column='F_LF_G', aggfunc=sum),
            F_CF_G=pd.NamedAgg(column='F_CF_G', aggfunc=sum),
            F_RF_G=pd.NamedAgg(column='F_RF_G', aggfunc=sum),
        )
        .reset_index()
    )


def summary(year: int):
    inpath = pathlib.Path(f"data/index/{year}")
    outpath = pathlib.Path(f"data/processed/{year}")
    outpath.mkdir(exist_ok=True, parents=True)
    (
        pd.concat(
            [pd.read_csv(fn).pipe(aggregate_players)
             for fn in inpath.glob("*/players.csv")],
            ignore_index=True, sort=False
        )
        .sort_values(['team.league', 'team.name', 'last', 'given'])
        .to_csv(outpath/"playing.csv", index=False, float_format='%d')
    )
