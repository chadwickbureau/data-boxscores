import sys
import json
import collections
import string
import datetime

import colorama as clr
import toml

from . import config


substitution_keys = ["*", "+", "^", "&", "$"]


def find_alignment(game, align):
    for team in game["teams"].values():
        if team["alignment"] == align:
            return team
    return None



def print_error(game, msg):
    print(f"In [{game['game']['datetime']}] "
          f"{find_alignment(game, 'away')['team']['name']} at "
          f"{find_alignment(game, 'home')['team']['name']}")
    print(clr.Fore.RED + msg + clr.Fore.RESET)

def print_warning(msg):
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
            print_warning("\n".join([f"In file {self.metadata['file']},",
                                     f"  Invalid key-value pair '{line}'"]))


def process_date(game, value):
    game["game"]["datetime"] = value
    game["game"]["season"] = value.split("-")[0]
    return game


def process_number(game, value):
    if value == "0":
        game["game"]["number"] = 1
        game["game"]["double_header"] = "N"
    elif value == "1":
        game["game"]["number"] = 1
        game["game"]["double_header"] = "Y"
    elif value == "2":
        game["game"]["number"] = 2
        game["game"]["double_header"] = "Y"
    else:
        print_warning(f"Unknown game number '{value}'")
    return game


def process_league(game, value):
    game["game"]["league"] = value
    return game


def add_entity(game, value, entity_type):
    if value in game["entities"]:
        print(f"ERROR: Duplicate entity {value}")
        sys.exit(1)
    game["entities"][value] = entity_type
    return game
    

def process_away(game, value):
    game["teams"][value] = {
        "alignment": "away",
        "name": value,
        "league": "",
        "score": "",
        "innings": [],
        "totals": {},
        "players": {}
    }
    return add_entity(game, value, "team")


def process_home(game, value):
    game["teams"][value] = {
        "alignment": "home",
        "name": value,
        "league": "",
        "score": "",
        "innings": [],
        "totals": {},
        "players": {}
    }
    return add_entity(game, value, "team")


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
        print_error(f"Unknown status '{status}'")
        sys.exit(1)
    if reason:
        game["status"]["reason"] = reason
    return game


def process_attendance(game, value):
    if value != "":
        game["venue"]["attendance"] = value.replace(",", "")
    return game


def process_duration(game, value):
    if value != "":
        game["game"]["duration"] = value.replace(",", "")
    return game
    

def process_linescore(game, text):
    try:
        club, score = (x.strip() for x in text.split(":"))
    except ValueError:
        print("In file %s,\n   game %s" % (self.metadata['filename'],
                                        self))
        print("  Ill-formed linescore string '%s'" % value)
        return

    for team in game["teams"].values():
        if club == team["name"]:
            break
    else:
        print_warning(f"Unknown team '{club}'")
        return
    
    byinning, total = map(lambda x: x.strip(), score.split("-"))
    try:
        int(total)
    except ValueError:
        print("\n".join([
                f"In file {self.metadata['filename']},",
                f"   game {self}",
                f"  Invalid linescore total runs '{total}'"]
                )
            )
        total = ""

    team["score"] = int(total)
    team["innings"] = [int(x) if x.lower() != "x" else "x"
                       for x in byinning.split()]
    return game


def process_umpires(game, value):
    for name in value.split(";"):
        umpire = {"last": None}
        game["umpire"].append(umpire)
        if "," in name:
            umpire["last"], umpire["first"] = (
                map(lambda x: x.strip(), name.split(","))
            )
        else:
            umpire["last"] = value.strip()
    return game

            
def process_player(key, value, columns):
    player = {"full": None, "last": None, "first": None,
              "F_POS": None}
    try:
        name, player["F_POS"] = map(lambda x: x.strip(), key.split("@"))
        for p in player["F_POS"].split("-"):
            if p not in ["p", "c", "1b", "2b", "3b", "ss",
                         "lf", "cf", "rf", "ph", "pr", "?"]:
                print("\n".join([
                    f"In file {self.metadata['filename']},",
                    f"   game {self}",
                    f"  Unknown position in '{key}'"]
                            )
                          )
        player["F_POS"] = player["F_POS"].upper()
    except ValueError:
        print(f"In file {self.metadata['filename']},\n   game {self}")
        print(f"  Missing name or position in '{key}'")
        name = key

    if "," in name:
        last, first = (x.strip() for x in name.split(","))
        player["full"] = first + " " + last
        player["last"] = last
        player["first"] = first
    else:
        player["full"] = name
        player["last"] = name
        del player["first"]

    for (col, stat) in zip(columns, value.split()):
        if stat.lower() != "x":
            player[col] = int(stat.strip())
    if player["last"][0] in substitution_keys:
        player["substitution"] = player["last"][0]
        player["last"] = player["last"][1:]
    return player
        

def process_totals(key, value, columns):
    totals = {}
    for (col, stat) in zip(columns, value.split()):
        if stat.lower() != "x":
            totals[col] = int(stat.strip())
    return totals


def process_player_list(game, team, header, lines):
    # "DI" is used sporadically in Winnipeg paper in 1915;
    # we assume it is RBI
    categorymap = {"ab": "B_AB", "r": "B_R", "h": "B_H",
                   "di": "B_RBI", "rbi": "B_RBI",
                   "sh": "B_SH", "sb": "B_SB",
                   "po": "F_PO", "a": "F_A", "e": "F_E"}

    try:
        columns = [categorymap[c]
                   for c in [x for x in header.split() if x.strip() != ""]]
    except KeyError:
        print_warning(f"  Unrecognised category line '{header}'")
        columns = []

    while True:
        try:
            key, value = next(lines)
        except StopIteration:
            print_warning(
                f"Unexpected end of game when parsing team '{team['name']}'"
            )
            return
        if key != "TOTALS":
            player = process_player(key, value, columns)
            team["players"][player["full"]] = player
            game = add_entity(game, player["full"],
                              "player")
            del player["full"]
        if key == "TOTALS":
            team["totals"] = process_totals(key, value, columns)
            break


def process_credit(game, key, value):
    if value == "":
        return game
    if key not in game["credits"]:
        game["credits"][key] = []
    for entry in [x.strip() for x in value.split(";")]:
        if entry[:1] == '~':
            entry = entry[1:]
        if "#" in entry:
            try:
                name, count = [x.strip() for x in entry.split("#")]
                # This will also trigger a value error if count not number
                float(count)
            except ValueError:
                print(f"ERROR: Ill-formed details string {value}")
                sys.exit(1)
        else:
            name, count = entry, "1"
        is_marked = name.startswith("??")
        if is_marked:
            name = name[2:]
        game["credits"][key].append({determine_entity(game, name): name,
                                     "count": str(count)})
    return game
                                

def determine_entity(game, name):
    if name not in game["entities"]:
        print_warning(f"Unmatched name {name}")
        return "player"
    return game["entities"][name]


def determine_team(game, names):
    for (key, team) in game["teams"].items():
        for name in names:
            if name not in team["players"]:
                break
        else:
            return key
    print_error(game,
                f"{names} does not match a unique team.")
    sys.exit(1)

    
def process_double_play(game, value):
    if value == "":
        return game
    if "F_DP" not in game["credits"]:
        game["credits"]["F_DP"] = []
    for entry in [x.strip() for x in value.split(";")]:
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
        namelist = []
        for name in [x.strip() for x in names.split(",")]:
            if name not in game["entities"]:
                print(f"WARNING: Unmatched name {name}")
            namelist.append(name)
        game["credits"]["F_DP"].append({
            "team": determine_team(game, namelist),
            "players": namelist,
            "count": str(count)
        })
    return game


def process_substitution(game, key, value):
    if key in game["substitutions"]:
        print(f"ERROR: duplicate substitution key {key}")
        sys.exit(1)
    game["substitutions"].append(value)
    return game


def postprocess_game(game):
    for (key, team) in game["teams"].items():
        team["league"] = game["game"]["league"]
    try:
        del game["game"]["league"]
    except KeyError:
        pass
    del game["entities"]
    return game


def dump_team(team):
    s = "[[team]]\n"
    for (key, value) in team.items():
        if key not in ["players", "totals"]:
            s += f'{key} = {json.dumps(value)}\n'
    s += "\n"
    for player in team["players"].values():
        s += "[[team.player]]\n"
        for (k, v) in player.items():
            s += f'{k} = {json.dumps(v)}\n'
        s += "\n"
    if team["totals"]:
        s += "[team.totals]\n"
        for (k, v) in team["totals"].items():
            s += f'{k} = {json.dumps(v)}\n'
        s += "\n"
    return s

        
def toml_dumps(game):
    """Dump game to TOML format, with depth-first recursion on tables.
    There are pull requests in the toml library to do this, but it is
    not as yet supported in the released version.
    """
    s = ""
    for key in ["source", "game", "venue", "status"]:
        s += toml.dumps({key: game[key]}) + "\n"
    for ump in game["umpire"]:
        s += toml.dumps({"umpire": [ump]}) + "\n"
    for (key, team) in game["teams"].items():
        s += dump_team(team) + "\n"
    s += (
        toml.dumps({"credits": game["credits"]})
        .replace("[credits]\n", "")
        .replace(",]", " ]") + "\n"
    )
    return s
    

def transform_game(txt):
    game = {
        "source": None,
        "game": {
            "type": "R",
            "number": "1",
            "double_header": "N",
            "season": "",
            "datetime": "",
            "duration": "",
        },
        "venue": {
            "name": "",
            "attendance": "",
        },
        "status": {
            "code": "final",
            "reason": "game over"
        },
        "entities": {},
        "teams": {},
        "substitutions": [],
        "credits": {},
        "umpire": []
    }

    lookup = {
        "date":      process_date,
        "number":    process_number,
        "league":    process_league,
        "away":      process_away,
        "home":      process_home,
        "source":    process_source,
        "status":    process_status,
        "a":         process_attendance,
        "t":         process_duration,
        "u":         process_umpires,
        "line":      process_linescore,
        "b_2b":      lambda g, v: process_credit(g, "B_2B", v),
        "b_3b":      lambda g, v: process_credit(g, "B_3B", v),
        "b_hr":      lambda g, v: process_credit(g, "B_HR", v),
        "b_sh":      lambda g, v: process_credit(g, "B_SH", v),
        "b_sf":      lambda g, v: process_credit(g, "B_SF", v),
        "b_hp":      lambda g, v: process_credit(g, "B_HP", v),
        "b_sb":      lambda g, v: process_credit(g, "B_SB", v),
        "b_roe":     lambda g, v: process_credit(g, "B_ROE", v),
        "b_lob":     lambda g, v: process_credit(g, "B_LOB", v),
        "b_er":      lambda g, v: process_credit(g, "B_ER", v),
        "p_ip":      lambda g, v: process_credit(g, "P_IP", v),
        "p_h":       lambda g, v: process_credit(g, "P_H", v),
        "p_bb":      lambda g, v: process_credit(g, "P_BB", v),
        "p_so":      lambda g, v: process_credit(g, "P_SO", v),
        "p_hp":      lambda g, v: process_credit(g, "P_HP", v),
        "p_wp":      lambda g, v: process_credit(g, "P_WP", v),
        "p_bk":      lambda g, v: process_credit(g, "P_BK", v),
        "f_dp":      process_double_play,
        "f_pb":      lambda g, v: process_credit(g, "F_PB", v),
    }
    lines = data_pairs(txt)
    while True:
        try:
            key, value = next(lines)
        except StopIteration:
            break
        if key in game["teams"]:
            process_player_list(game, game["teams"][key], value, lines)
            continue
        if key in substitution_keys:
            process_substitution(game, key, value)
            continue
        try:
            fn = lookup[key.lower()]
        except KeyError:
            print_warning(f"Unknown record key '{key}'")
            continue
        game = fn(game, value)
    game = postprocess_game(game)
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
        yield transform_game(txt)


def process_files(source, inpath):
    fnlist = [fn for fn in sorted(inpath.glob("*.txt"))
              if fn.name.lower() not in ["readme.txt", "notes.txt"]]
    if not fnlist:
        print_error(f"No files found at '{inpath}'")
        sys.exit(1)
    games = [game
             for fn in fnlist
             for game in iterate_games(fn)]
    txt = "---\n\n".join(toml_dumps(game) for game in games)
    with open("games.toml", "w") as f:
        f.write(txt)
        
    
def main(source):
    try:
        year, paper = source.split("-")
    except ValueError:
        print_error(f"Invalid source name '{source}'")
        sys.exit(1)

    inpath = config.data_path/"transcript"/year/source
    process_files(year + "/" + source, inpath)

