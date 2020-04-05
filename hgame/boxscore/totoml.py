import sys
import datetime
from collections import OrderedDict
import pprint
import hashlib

import colorama as clr
import json
import toml

from . import config
from . import schema


substitution_keys = ["*", "+", "^", "&", "$"]


def print_error(msg: str):
    print(clr.Fore.RED + msg + clr.Fore.RESET)

def print_warning(msg: str):
    print(clr.Fore.YELLOW + msg + clr.Fore.RESET)

def data_pairs(text):
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


def process_key(key, value):
    return {"game.key": value}


def process_source(key, value):
    title, d = (x.strip() for x in value.split(",", 1))
    for fmt in ["%B %d, %Y", "%b %d, %Y"]:
        try:
            d = datetime.datetime.strptime(d, fmt)
            d = d.strftime("%Y-%m-%d")
            return {
                "meta.source.title": title,
                "meta.source.date": d
            }
        except ValueError:
            pass
    print_error(f"Invalid date {d} in source")
    return {"meta.source.title": value}


def process_status(key, status):
    if "," in status:
        status, reason = (x.strip() for x in status.split(","))
    else:
        status, reason = status.strip(), ""
    data = {}
    if status in ["postponed", "completed early", "abandoned"]:
        data["outcome.status"] = status
    else:
        print_error(f"Unknown status '{status}'")
        sys.exit(1)
    if reason:
        data["outcome.reason"] = reason
    return data


def process_status_reason(key, reason):
    return {"outcome.reason": reason}


def process_outsatend(key, value):
    if value == "":
        return {}
    return {"outcome.outsatend": value.replace("#", "")}


def process_attendance(game, value):
    if value != "":
        return {"venue.attendance": value.replace(",", "")}
    return {}


def process_duration(game, value):
    if value != "":
        return {"game.duration": value}
    return {}


def process_umpires(key, value):
    data = OrderedDict()
    for (index, name) in enumerate(value.split(";")):
        if "," in name:
            last, first = map(lambda x: x.strip(), name.split(","))
            data[f"umpire.umpire{index+1:02}.name__last"] = last
            data[f"umpire.umpire{index+1:02}.name__first"] = first
        else:
            data[f"umpire.umpire{index+1:02}.name__last"] = name.strip()
    return data


def process_substitution(key, value):
    prefix = f"substitution.sub{substitution_keys.index(key)+1}"
    return {f"{prefix}.key": key,
            f"{prefix}.text": value}


def process_league(key, value):
    if value.endswith("Assn"):
        value = value.replace("Assn", "Association")
    if "Association" not in value and "League" not in value:
        value = value + " League"
    return {"game.league": value}


def process_date(key, value):
    return {
        "game.datetime": value,
        "game.season": value.split("-")[0]
    }    


def process_number(key, value):
    if value == "0":
        return {
            "game.number": "1",
            "game.double_header": "N"
        }
    elif value == "1":
        return {
            "game.number": "1",
            "game.double_header": "Y"
        }
    elif value == "2":
        return {
            "game.number": "2",
            "game.double_header": "Y"
        }
    print_warning(f"Unknown game number '{value}'")
    return ""
        

def process_team(game, value, alignment):
    return {
        f"team.{alignment}.name": value,
        f"team.{alignment}.alignment": alignment
    }


def process_player(key, value, columns):
    player = OrderedDict({"name__last": None, "name__first": None})
    try:
        name, player["source__F_POS"] = map(lambda x: x.strip(), key.split("@"))
        player["source__F_POS"] = player["source__F_POS"].upper()
    except ValueError:
        print_error(f"Missing name or position in '{key}'")
        name = key

    if "," in name:
        last, first = (x.strip() for x in name.split(","))
        player[f"source__name__last"] = last
        player[f"source__name__first"] = first
    else:
        player[f"source__name__last"] = name
    for (col, stat) in zip(columns, value.split()):
        if stat.lower() != "x":
            player[col] = int(stat.strip())
    if player["source__name__last"].startswith("("):
        slot, player["source__name__last"] = (
            player["source__name__last"][1:].split(")")
        )
        slot = slot.replace("~", "")
        slot, seq = (x.strip() for x in slot.split("."))
        player["infer__batorder"] = str(100*int(slot) + int(seq))
    if player["source__name__last"][0] in substitution_keys:
        player["source__substitution"] = player["source__name__last"][0]
        player["source__name__last"] = player["source__name__last"][1:]
    for key in substitution_keys:
        if key in player["source__name__last"]:
            print_warning(f"Mis-formatted player name {name}")
    return OrderedDict({k: v
                        for k, v in player.items() if v is not None})
        

def process_totals(alignment, value, columns):
    totals = {}
    for (col, stat) in zip(columns, value.split()):
        if stat.lower() != "x":
            totals[f"team.{alignment}.totals.{col}"] = (
                int(stat.strip())
            )
    return totals


def process_player_list(alignment, header, lines):
    # "DI" is used sporadically in Winnipeg paper in 1915;
    # we assume it is RBI
    categorymap = {"ab": "source__B_AB",
                   "r": "source__B_R",
                   "h": "source__B_H",
                   "di": "source__B_RBI",
                   "rbi": "source__B_RBI",
                   "sh": "source__B_SH",
                   "sb": "source__B_SB",
                   "po": "source__F_PO",
                   "a": "source__F_A",
                   "e": "source__F_E"}

    try:
        columns = [categorymap[c]
                   for c in [x for x in header.split() if x.strip() != ""]]
    except KeyError:
        print_warning(f"  Unrecognised category line '{header}'")
        columns = []

    data = OrderedDict()
    index = 1
    while True:
        try:
            key, value = next(lines)
        except StopIteration:
            print_warning(
                f"Unexpected end of game when parsing team '{team['name']}'"
            )
            return
        if key == "TOTALS":
            data.update(process_totals(alignment, value, columns))
            break
        data.update({f"team.{alignment}.player.player{index:02}.{k}": v
                     for k, v in
                     process_player(key, value, columns).items()})
        index += 1

    return data


def process_linescore(teams, text):
    try:
        club, score = (x.strip() for x in text.split(":"))
    except ValueError:
        print_error(f"Ill-formed linescore string '{value}'")
        return

    try:
        alignment = teams[club]
    except KeyError:
        print_error(f"Unknown club {club} in linescore")
        return {}
    byinning, total = map(lambda x: x.strip(), score.split("-"))
    data = {}
    if total != "?":
        data[f"team.{alignment}.score"] = total
    for (inning, value) in enumerate(byinning.split()):
        data[f"team.{alignment}.inning.inning{inning+1:02}"] = value.lower()
    return data


def process_credit(key, value):
    data = OrderedDict()
    if value == "":
        return data
    for (index, entry) in enumerate([x.strip() for x in value.split(";")]):
        if "#" in entry:
            try:
                name, count = [x.strip() for x in entry.split("#")]
                # This will also trigger a value error if count not number
                float(count)
            except ValueError:
                print_error(f"Ill-formed details string {value} for {key}")
                continue
        else:
            name, count = entry, "1"
        if name == "":
            print_warning(f"Empty name in list for {key}")
            continue
        if name[0] == "~":
            name = name[1:]
            stat_type = "infer"
        else:
            stat_type = "source"
        data[f"credits.{key}_credit{index+1:02}.source__name"] = name
        data[f"credits.{key}_credit{index+1:02}.{stat_type}__{key}"] = str(count)
    return data


def process_xo(key, value):
    data = {}
    if value == "":
        return data
    for (index, entry) in enumerate([x.strip() for x in value.split(";")]):
        try:
            name, reason = (x.strip() for x in entry.split(","))
        except ValueError:
            print_error(f"Ill-formed details string {entry} for B_XO")
            continue
        if name[0] == "~":
            name = name[1:]
            stat_type = "infer"
        else:
            stat_type = "source"
        data[f"credits.{key}_credit{index+1:02}.source__name"] = name
        data[f"credits.{key}_credit{index+1:02}.{stat_type}__B_XO"] = "1"
        data[f"credits.{key}_credit{index+1:02}.{stat_type}__note"] = reason
    return data


def process_dp_tp(key, value):
    data = OrderedDict()
    if value == "":
        return data
    for (index, entry) in enumerate([x.strip() for x in value.split(";")]):
        if "#" in entry:
            try:
                names, count = [x.strip() for x in entry.split("#")]
                # This will also trigger a value error if count not number
                float(count)
            except ValueError:
                print(f"ERROR: Ill-formed details string {value}")
                sys.exit(1)
        else:
            names, count = entry, "1"
        namelist = [x.strip() for x in names.split(",")]
        for (j, name) in enumerate(namelist):
            data[f"credits.{key}_credit{index+1:02}.source__name.name{j+1:02}"] = name
        data[f"credits.{key}_credit{index+1:02}.source__{key}"] = str(count)
    return data


def transform_game(txt):
    game = OrderedDict({'game.key': None,
                        'outcome.status': "final"})
    lines = data_pairs(txt)
    lookup = {
        "key": process_key,
        "source": process_source,
        "date": process_date,
        "number": process_number,
        "league": process_league,
        "status": process_status,
        "status-reason": process_status_reason,
        "outsatend": process_outsatend,
        "t": process_duration,
        "a": process_attendance,
        "away": lambda g, v: process_team(g, v, "away"),
        "home": lambda g, v: process_team(g, v, "home"),
        "u": process_umpires,
        "b_lob": process_credit,
        "b_er": process_credit,
        "b_2b": process_credit,
        "b_3b": process_credit,
        "b_hr": process_credit,
        "b_bb": process_credit,
        "b_hp": process_credit,
        "b_sh": process_credit,
        "b_sf": process_credit,
        "b_sb": process_credit,
        "b_roe": process_credit,
        "b_xo": process_xo,
        "p_gs": process_credit,
        "p_gf": process_credit,
        "p_w": process_credit,
        "p_l": process_credit,
        "p_sv": process_credit,
        "p_ip": process_credit,
        "p_ab": process_credit,
        "p_r": process_credit,
        "p_h": process_credit,
        "p_bb": process_credit,
        "p_so": process_credit,
        "p_hp": process_credit,
        "p_wp": process_credit,
        "p_bk": process_credit,
        "f_dp": process_dp_tp,
        "f_tp": process_dp_tp,
        "f_pb": process_credit,
    }
    while True:
        try:
            key, value = next(lines)
        except StopIteration:
            break
        if key == game.get("team.away.name", ""):
            game.update(process_player_list("away", value, lines))
            continue
        if key == game.get("team.home.name", ""):
            game.update(process_player_list("home", value, lines))
            continue
        if key == "line":
            game.update(process_linescore(
                {game.get("team.away.name"): "away",
                 game.get("team.home.name"): "home"},
                 value
                ))
            continue
        if key in substitution_keys:
            game.update(process_substitution(key, value))
            continue
        if key.lower() in lookup:
            fn = lookup[key.lower()]
            game.update(fn(key, value))
        else:
            print_warning(f"Unknown record '{key}: {value}'")
    return game


def flat_serialise(game):
    """Create a flat TOML representation of the 'internal' representation.
    """
    return "\n".join([f'{key} = "{value}"'
                      for key, value in game.items()])


def validate_game(doc_schema, doc):
    result = doc_schema.validate(doc, partial=False)
    if result:
        print()
        pprint.pprint(doc)
        print("Found the following validation errors:")
        pprint.pprint(result)
        print()
        sys.exit(1)


def canonical_toml_team(team: dict, subs: dict):
    """Create a canonical TOML representation of a team."""
    txt = "[[team]]\n"
    txt += toml.dumps({k: v
                       for k, v in team.items()
                       if k not in ["inning", "totals", "player"]})
    if "inning" in team:
        txt += (
            toml.dumps({"inning": team['inning'].values()})
            .replace(",]", " ]")
        )
    if "totals" in team:
        txt += "\n"
        txt += (
            toml.dumps({"team__totals": team['totals']})
            .replace("__", ".") + "\n"
        )
    for player in team.get("player", {}).values():
        if "substitution" in player:
            player["substitution"] = subs[player["substitution"]]
        txt += (
            toml.dumps({"team__player": [player]})
            .replace("__", ".")
        )
    return txt

        
def canonical_toml(game: dict):
    """Create a canonical TOML representation of the game."""
    txt = (
        toml.dumps({"meta__source": game['meta']['source']})
        .replace("__", ".") + "\n"
    )
    for key in ['game', 'venue', 'outcome']:
        if key in game:
            txt += toml.dumps({key: game[key]}) + "\n"
    for umpire in game.get("umpire", {}).values():
        txt += (
            toml.dumps({"umpire": [umpire]})
            .replace("__", ".") + "\n"
        )
    subs = {x['key']: x['text']
            for x in game.get('substitution', {}).values()}
    for team in game['team'].values():
        txt += canonical_toml_team(team, subs) + "\n"
    for credit in game.get('credits', {}).values():
        if isinstance(credit['source__name'], dict):
            credit['source__name'] = credit['source__name'].values()
            txt += (
                toml.dumps({"credit__event": [credit]})
                .replace("__", ".").replace(",]", " ]")
            )
            continue
        if credit['source__name'] in [t['name'] for t in game['team'].values()]:
            txt += (
                toml.dumps({"credit__team": [credit]})
                .replace("__", ".")
            )
        else:
            txt += (
                toml.dumps({"credit__player": [credit]})
                .replace("__", ".")
            )
    validate_game(schema.BoxscoreSchema(), toml.loads(txt))
    return txt


def assign_key(game):
    if game['game']['key'] != "None":
        return game
    
    slug = (
        (game['game']['league'].replace(" ", "") + ":" +
         game['game']['datetime'] + ":" +
         game['team']['away']['name'].replace(" ", "") + "@" +
         game['team']['home']['name'].replace(" ", "") +
         "#" + game['game']['number'])
    )
    game['game']['key'] = (
        game['game']['datetime'][:10].replace("-", "") + "_" +
        (
            game['team']['home']['name']
            .replace(" ", "").replace(".", "").upper()[:3]
        ) + "_" +
        hashlib.sha1(slug.encode('utf-8')).hexdigest()[:4]
    )
    return game


def assign_scores(game):
    """Cleanup games without linescores to include team score
    based on team totals."""
    for team in game['team'].values():
        if 'score' not in team and 'totals' in team:
            team['score'] = team['totals']['source__B_R']
    return game

    
def iterate_games(fn):
    """Return an iterator over the text of each individual game
    in file `fn'. All extra whitespace is removed within and at the end of
    lines, and lines which are whitespace only are dropped, creating a
    'canonical' representation of the text.
    """
    print(f"Processing games in {fn}")
    for txt in filter(lambda x: x.strip() != "",
                      ("\n".join(filter(lambda x: x != "",
                                 [' '.join(x.strip().split())
                                  for x in fn.open().readlines()])))
                      .rstrip("-").split("---\n")):
        game = transform_game(txt)
        game = toml.loads(flat_serialise(game))
        game = assign_key(game)
        game = assign_scores(game)
        print(f"[{game['game']['key']}] "
              f"{game['game']['datetime']} {game['game']['number']} "
              f"{game['team']['away']['name']:<15} @ "
              f"{game['team']['home']['name']:<15}")
        yield (game['game']['key'], canonical_toml(game))



def process_files(source, inpath, outpath):
    fnlist = [fn for fn in sorted(inpath.glob("*.txt"))
              if fn.name.lower() not in ["readme.txt", "notes.txt"]]
    if not fnlist:
        print_error(f"No files found at '{inpath}'")
        sys.exit(1)
    for fn in fnlist:
        for (key, game) in iterate_games(fn):
            outfile = outpath/f"{key}.txt"
            if outfile.exists():
                print(f"ERROR: Duplicate game key {key}")
                sys.exit(1)
            with (outpath/f"{key}.txt").open("w") as f:
                f.write(game)
    

def main(source):
    try:
        year, paper = source.split("-")
    except ValueError:
        print_error(f"Invalid source name '{source}'")
        sys.exit(1)

    inpath = config.data_path/"transcript"/year/source
    outpath = config.data_path/"toml"/year/source
    outpath.mkdir(parents=True, exist_ok=True)
    for fn in outpath.glob("*.txt"):
        fn.unlink()
    process_files(year + "/" + source, inpath, outpath)
