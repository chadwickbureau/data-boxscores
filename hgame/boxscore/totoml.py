import colorama as clr
import json
import toml

from . import config


substitution_keys = ["*", "+", "^", "&", "$"]


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


class GameData:
    def __init__(self, data):
        self._data = data

    @property
    def datetime(self):
        return self._data["datetime"]

    @datetime.setter
    def datetime(self, value):
        self._data["datetime"] = value
        self._data["season"] = value.split("-")[0]

    @property
    def number(self):
        return self._data["number"]

    @number.setter
    def number(self, value):
        if value == "0":
            self._data["number"] = "1"
            self._data["double_header"] = "N"
        elif value == "1":
            self._data["number"] = "1"
            self._data["double_header"] = "Y"
        elif value == "2":
            self._data["number"] = "2"
            self._data["double_header"] = "Y"
        else:
            print_warning(f"Unknown game number '{value}'")


class GameTeams:
    def __init__(self, data):
        self._data = data

    def __contains__(self, key):
        return key in self._data
        
    def add(self, name, alignment):
        self._data[name] = {
            "alignment": alignment,
            "name": name,
            "league": "",
            "score": "",
            "innings": [],
            "totals": {},
            "players": {}
        }

        
class Game:
    def __init__(self):
        self._data = {
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
            "teams": {},
            "substitution": [],
            "credit": [],
            "umpire": []
        }

    @property
    def teams(self):
        return GameTeams(self._data["teams"])

    @property
    def game(self):
        return GameData(self._data["game"])
        
    @staticmethod
    def _serialise_team(team):
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

    def serialise(self):
        """Dump game to TOML format, with depth-first recursion on tables.
        There are pull requests in the toml library to do this, but it is
        not as yet supported in the released version.
        """
        s = ""
        for key in ["source", "game", "venue", "status"]:
            s += toml.dumps({key: self._data[key]}) + "\n"
        for ump in self._data["umpire"]:
            s += toml.dumps({"umpire": [ump]}) + "\n"
        for (key, team) in self._data["teams"].items():
            s += self._serialise_team(team) + "\n"
        s += (
            toml.dumps({"credit": self._data["credit"]})
            .replace("[credit]\n", "")
            .replace(",]", " ]") + "\n"
        )
        return s


def process_substitution(game, key, value):
    return game


def process_date(game, value):
    game.game.datetime = value
    return game


def process_number(game, value):
    game.game.number = value
    return game


def process_team(game, value, alignment):
    game.teams.add(value, alignment)
    return game


def transform_game(txt):
    game = Game()
    lines = data_pairs(txt)
    lookup = {
        "date": process_date,
        "number": process_number,
        "away": lambda g, v: process_team(g, v, "away"),
        "home": lambda g, v: process_team(g, v, "home"),
    }
    while True:
        try:
            key, value = next(lines)
        except StopIteration:
            break
        if key in game.teams:
            #process_player_list(game, game["teams"][key], value, lines)
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
    txt = "---\n\n".join(game.serialise() for game in games)
    with open("games.toml", "w") as f:
        f.write(txt)
    print(txt)


def main(source):
    try:
        year, paper = source.split("-")
    except ValueError:
        print_error(f"Invalid source name '{source}'")
        sys.exit(1)

    inpath = config.data_path/"transcript"/year/source
    process_files(year + "/" + source, inpath)
