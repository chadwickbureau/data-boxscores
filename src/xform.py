import sys
import pathlib
from typing import Generator
import datetime
from decimal import Decimal

import yaml
import rich.console

console = rich.console.Console()


def print_error(msg: str):
    console.print(msg, style='red')

def print_warning(msg: str):
    console.print(msg, style='yellow')


def iterate_games(fn: pathlib.Path) -> Generator[str, None, None]:
    """Iterate over the game texts in 'fn'.
    This strips whitespace from the starts/ends of lines, and drops
    all whitespace-only lines.
    As a result, the resulting texts (if the games are well-formatted)
    will all be of the form 'tag: value'
    """
    print(fn)
    with fn.open() as f:
        data = [y
                for y in [x.strip() for x in f.readlines()]
                if y != ""]
    yield from "\n".join(data).lstrip("-").rstrip("-").split("---\n")


def data_pairs(text: str) -> Generator[tuple, None, None]:
    """The data file is essentially a sequence of (key, value) pairs.
    This implements a generator which extracts these.
    """
    for line in text.split("\n"):
        line = line.strip()
        if line == "":
            continue
        try:
            key, value = [x.strip() for x in line.split(":", 1)]
            yield (key, value)
        except ValueError:
            print_error(f"Invalid key-value pair '{line}'")


def process_date(game: dict, key: str, value: str) -> dict:
    game['game']['date'] = datetime.datetime.strptime(value, "%Y-%m-%d").date()
    game['game']['season'] = int(value.split("-")[0])
    return game


def process_number(game: dict, key: str, value: str) -> dict:
    game['game']['number'] = int(value)
    return game

            
def process_league(game: dict, key: str, value: str) -> dict:
    if value.endswith("Assn"):
        value = value.replace("Assn", "Association")
    if "Association" not in value and "League" not in value:
        value = value + " League"
    for team in game['teams']:
        team['league'] = value
    return game


def process_team(game: dict, key: str, value: str) -> dict:
    team = game['teams'][{'away': 0, 'home': 1}[key]]
    team['name'] = value
    team['alignment'] = key
    return game


def process_status(game: dict, key: str, value: str) -> dict:
    if "," in value:
        code, reason = (x.strip() for x in value.split(","))
        game['game']['status']['code'] = code
        game['game']['status']['reason'] = reason
    else:
        game['game']['status']['code'] = value
    return game


def process_status_reason(game: dict, key: str, value: str) -> dict:
    game['game']['status']['reason'] = value
    return game


def process_source(game: dict, key: str, value: str) -> dict:
    game['source']['description'] = value
    return game


def process_attendance(game: dict, key: str, value: str) -> dict:
    game['game']['attendance'] = int(value.replace(",", ""))
    return game


def process_duration(game: dict, key: str, value: str) -> dict:
    if value == "":
        return game
    h, m = value.split(":")
    game['game']['duration'] = 60*int(h) + int(m)
    return game


def process_outsatend(game: dict, key: str, value: str) -> dict:
    if value == "":
        return game
    game['game']['outsatend'] = int(value)
    return game


def process_linescore(game: dict, key: str, value: str) -> dict:
    name, data = (x.strip() for x in value.split(":"))
    team = {team['name']: team for team in game['teams']}[name]
    byinnings, score = (x.strip() for x in data.split("-"))
    team['score'] = {'total': int(score)}
    if byinnings != "":
        team['score']['byinnings'] = [
            None if x == "?" else (
                int(x) if x.lower() != "x" else "x"
            )
            for x in byinnings.split()
        ]
    return game


def process_umpires(game: dict, key: str, value: str) -> dict:
    for name in (x.strip() for x in value.split(";")):
        game['officials'].append({
            'name': name
        })
    return game


def process_substitute(game: dict, key: str, value: str) -> dict:
    game['substitutes'][key] = value
    return game


def process_credits(game: dict, key: str, value: str) -> dict:
    if value == "":
        return game
    game['credits'][key] = []
    for credit in (x.strip() for x in value.split(";")):
        if credit == "":
            continue
        if "#" in credit:
            try:
                name, count = (x.strip() for x in credit.split("#"))
            except ValueError as exc:
                print_error(f"    Unable to split credit {credit}, skipping.")
                continue
        else:
            name, count = credit, 1
        if key != "P_IP":
            game['credits'][key].append({
                'name': name,
                'count': int(count)
            })
        else:
            game['credits'][key].append({
                'name': name,
                'count': str(Decimal(count))
            })
    return game


def transform_team(team: dict, data: Generator[tuple, None, None],
                   key: str, value: str) -> dict:
    def validate_positions(pos: str) -> str:
        if pos == "?":
            return None
        poslist = pos.lower().split("-")
        for pos in poslist:
            if pos not in ["p", "c", "1b", "2b", "3b", "ss", "lf", "cf", "rf",
                           "ph", "pr"]:
                raise ValueError(pos)
        return "-".join(poslist)
                
    columns = [x.strip() for x in value.split()]
    while True:
        key, value = next(data)
        if key == "TOTALS":
            for (col, stat) in zip(columns, value.split()):
                if stat.lower() == "x":
                    stat = None
                else:
                    stat = int(stat)
                team['totals'][col] = stat
            break
        try:
            name, pos = (x.strip() for x in key.split("@"))
        except ValueError as exc:
            print_error(f"    Unable to split name {key}, skipping.")
            continue
        if ")" in name:
            # TODO: Extract sequence information
            name = name.split(")")[1]
        if name.startswith(("*", "+", "$", "^")):
            note = name[0]
            name = name[1:]
        else:
            note = None
        pos = validate_positions(pos)
        player = {
            'name': name,
            'positions': pos
        }
        if note:
            player['note'] = note
        for (col, stat) in zip(columns, value.split()):
            if stat.lower() == "x":
                stat = None
            else:
                stat = int(stat)
            player[col] = stat
        team['players'].append(player)
    return team


def transform_game(source: str, text: str) -> dict:
    game = {
        'source': {'key': source},
        'game': {'date': None, 'number': None, 'season': None,
                 'type': "regular",
                 'status': {'code': "final"}},
        'teams': [{'alignment': None,
                   'name': None,
                   'league': None,
                   'score': {},
                   'totals': {},
                   'players': []}
                   for t in [0, 1]],
        'substitutes': {},
        'credits': {},
        'officials': []
    }
    data = data_pairs(text)
    lookup = {
        "date": process_date,
        "number": process_number,
        "league": process_league,
        "status": process_status,
        "status-reason": process_status_reason,
        "source": process_source,
        "away": process_team,
        "home": process_team,
        "line": process_linescore,
        "U": process_umpires,
        "A": process_attendance,
        "T": process_duration,
        "outsatend": process_outsatend,
        "*": process_substitute,
        "+": process_substitute,
        "$": process_substitute,
        "^": process_substitute,
    }
    credits = [
        "B_LOB", "B_ROE", "B_R", "B_ER", "B_2B", "B_3B", "B_HR",
        "B_SB", "B_SH", "B_SF", "B_HP", "B_XO",
        "P_BB", "P_SO", "P_H", "P_R", "P_IP", "P_WP", "P_BK", "P_HP",
        "P_GS", "P_GF", "P_W", "P_L", "P_SV",
        "F_DP", "F_TP", "F_PB",
    ]
    while True:
        try:
            key, value = next(data)
            if key in lookup:
                game = lookup[key](game, key, value)
                continue
            if key in credits:
                game = process_credits(game, key, value)
                continue
            teams = {team['name']: team for team in game['teams']}
            if key in teams:
                transform_team(teams[key], data, key, value)
                continue
            print_warning(f"   Unknown key {key}")
        except StopIteration:
            break

    print(
        f"  {game['game']['date']} {game['game']['number']} "
        f"{game['teams'][0]['name']} at {game['teams'][1]['name']}"
    )
    return game


def find_files(inpath: pathlib.Path) -> list:
    return [
        fn for fn in sorted(inpath.glob("*.txt"))
        if fn.stem != "README"
    ]

def extract_files(inpath: pathlib.Path):
    with open(f"{inpath.stem}.yml", "w") as f:
        f.write(
            yaml.dump_all(
                (transform_game(inpath.parts[-1], text)
                 for fn in find_files(inpath)
                 for text in iterate_games(fn)),
                sort_keys=False
            )
        )


def main(source: str):
    year, paper = source.split("-")
    inpath = pathlib.Path(f"data/transcript/{year}/{source}")
    data = extract_files(inpath)


if __name__ == '__main__':
    main(sys.argv[1])
