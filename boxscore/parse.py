import sys
import os
import glob
import hashlib
import warnings
import pathlib
    
import colorama as clr
import pandas as pd

from . import config

def person_hash(source, row):
    """Generate hash-based identifier for a person based on the source
    and identifying elements of the person's record (season, name, club).
    """
    def hash_djb2(s):
        hashval = 5381
        for x in s:
            hashval = ((hashval << 5) + hashval) + ord(x)
        return "P" + ("%d" % hashval)[-7:]
    return hash_djb2(",".join([source,
                               row['league.year'], row['league.name'],
                               row['name.last'],
                               row['name.first'] if not pd.isnull(row['name.first']) else "",
                               row['club.name']]))

def game_hash(s):
    """Generate hash-based identifier for a game account based on the
    text of the game.
    """
    def int_to_base(n):
        alphabet = "BCDFGHJKLMNPQRSTVWXYZ"
        base = len(alphabet)
        if n < base:
            return alphabet[n]
        return int_to_base(n // base) + alphabet[n % base]
    return int_to_base(int(hashlib.sha1(s.encode('utf-8')).hexdigest(), 16))[-7:]


class BoxscoreParserWarning(UserWarning):
    pass

class IdentificationWarning(BoxscoreParserWarning):
    """A warning class on unidentified name.
    """
    def __init__(self, fn, game, message):
        super(IdentificationWarning, self).__init__(
                                       "In file %s,\n   game %s\n  %s" %
                                       (fn, game, message))


class MarkedIdentificationWarning(BoxscoreParserWarning):
    """A warning class on unidentified name which is explicitly marked.
    """
    def __init__(self, fn, game, message):
        super(MarkedIdentificationWarning, self).__init__(
                             "In file %s,\n   game %s\n  %s" %
                             (fn, game, message))


class DuplicatedNameWarning(BoxscoreParserWarning):
    """A warning class for duplicated names.
    """
    def __init__(self, fn, game, message):
        super(DuplicatedNameWarning, self).__init__(
                             "In file %s,\n   game %s\n  %s" %
                             (fn, game, message))

class DetailParseWarning(BoxscoreParserWarning):
    """A warning class for parse errors in detail strings.
    """
    def __init__(self, fn, game, message):
        super(DetailParseWarning, self).__init__(
                             "In file %s,\n   game %s\n  %s" %
                             (fn, game, message))
    

        
def _formatwarning(msg, category, *args, **kwargs):
    return str(msg) + '\n'
warnings.formatwarning = _formatwarning




class Game(object):
    _subskeys = ["*", "+", "^", "&", "$"]

    @property
    def date(self): return self.metadata.get("date")
    @property
    def number(self): return self.metadata.get("number")
    @property
    def phase(self): return self.metadata.get("phase")
    @property
    def away(self): return self.metadata.get("away")
    @property
    def home(self): return self.metadata.get("home")

    def __str__(self):
        return "%s[%s]: %s at %s" % (self.date, self.number,
                                     self.away, self.home)

    def _parse_details(self, key, value):
        if value == "": return
        for entry in [x.strip() for x in value.split(";")]:
            if entry[:1] == '~':
                entry = entry[1:]
            if "#" in entry:
                try:
                    name, count = [x.strip() for x in entry.split("#")]
                except ValueError:
                    print("In file %s,\n   game %s" % (self.metadata['filename'], self))
                    print("  Ill-formed details string '%s'" % entry)
                    return
            else:
                name, count = entry, "1"
            is_marked = name.startswith("??")
            if is_marked:
                name = name[2:]
            try:
                self.playing[name][key] = count
            except KeyError:
                if is_marked:
                    warnings.warn(
                        MarkedIdentificationWarning(
                                    self.metadata['filename'],
                                    self,
                                    "No match on name '??%s' in '%s'" %
                                         (name, key)))
                else:
                    warnings.warn(IdentificationWarning(self.metadata['filename'],
                                                        self,
                                                        "No match on name '%s' in '%s'" % (name, key)))

    def _parse_details_XO(self, key, value):
        if value == "": return
        for entry in [x.strip() for x in value.split(";")]:
            try:
                name, reason = [x.strip() for x in entry.split(",")]
            except ValueError:
                warnings.warn(DetailParseWarning(
                                  self.metadata['filename'],
                                  self,
                                  "Ill-formed details string '%s'" % entry))
                continue
            try:
                self.playing[name]['B_XO'] = self.playing[name].get('B_XO', 0)+1
            except KeyError:
                warnings.warn(IdentificationWarning(self.metadata['filename'],
                                                    self,
                                                    "No match on name '%s' in '%s'" % (name, key)))

    def _parse_dptp(self, key, value):
        if value == "":  return
        for entry in map(lambda x: x.strip(), value.split(";")):
            if "#" in entry:
                names, count = map(lambda x: x.strip(), entry.split("#"))
            else:
                names, count = entry, 1

            # TODO: Should do sanity check that all players are on same team!
            # Team should then be credited with a double play/triple play
            for name in map(lambda x: x.strip(), names.split(",")):
                is_marked = name.startswith("??")
                if is_marked:
                    name = name[2:]
                try:
                    playing = self.playing[name]
                except KeyError:
                    if is_marked:
                        warnings.warn(MarkedIdentificationWarning(self.metadata['filename'],
                                                            self,
                                                            "No match on name '??%s' in '%s'" % (name, key)))
                    else:
                        warnings.warn(IdentificationWarning(self.metadata['filename'],
                                                            self,
                                                            "No match on name '%s' in '%s'" % (name, key)))
                    continue
                playing[key] = str(int(playing.get(key, 0)) + int(count))

    def _parse_umpire(self, value):
        if "," in value:
            name_last, name_first = map(lambda x: x.strip(), value.split(","))
        else:
            name_last, name_first = value, None
        return {"game.key": self.metadata["key"],
                "game.date": self.date,
                "game.number": self.number,
                "game.phase": self.phase,
                "name.last": name_last,
                "name.first": name_first}

    def _parse_umpires(self, key, value):
        self.umpiring = [self._parse_umpire(x)
                         for x in map(lambda x: x.strip(),
                                      value.split(";"))]
        return True

    def _process_linescore(self, value):
        try:
            club, score = map(lambda x: x.strip(), value.split(":"))
        except ValueError:
            print("In file %s,\n   game %s" % (self.metadata['filename'], self))
            print("  Ill-formed linescore string '%s'" % value)
            return

        if club == self.away:
            prefix = "away.score"
        elif club == self.home:
            prefix = "home.score"
        else:
            print("In file %s,\n   game %s" % (self.metadata['filename'], self))
            print("  No match on club name '%s'" % (club))
            return

        byinning, total = map(lambda x: x.strip(), score.split("-"))
        self.metadata[prefix] = total
        for (inning, s) in enumerate(byinning.split()):
            self.metadata['%s.%d' % (prefix, inning+1)] = s
  

    def update_metadata(self, key, value):  return self.metadata.update({key: value})
    do_date = update_metadata
    do_number = update_metadata
    do_league = update_metadata
    do_phase = update_metadata
    do_away = update_metadata
    do_home = update_metadata
    do_site = update_metadata
    do_source = update_metadata
    do_A = update_metadata
    do_T = update_metadata
    do_away_manager = update_metadata
    do_home_manager = update_metadata
    do_forfeit_to = update_metadata
    do_outsatend = update_metadata
    do_U = _parse_umpires
    def do_home_batted(self, key, value):  return True

    def do_status(self, key, value):
        if "," in value:
            status, reason = (v.strip() for v in value.split(","))
        else:
            status, reason = value.strip(), None
        status = status.lower()
        if status not in ['final', 'completed early', 'abandoned',
                          'postponed']:
            print(f"In file {self.metadata['filename']},\n   game {self}")
            print(f"  Unknown status '{status}'")
        else:
            self.metadata['status'] = status
            self.metadata['status-reason'] = reason
        
        
    def do_line(self, key, value):   return self._process_linescore(value)

    do_B_ER = _parse_details
    do_B_R = _parse_details
    do_B_2B = _parse_details
    do_B_3B = _parse_details
    do_B_HR = _parse_details
    do_B_BB = _parse_details
    do_B_SO = _parse_details
    do_B_HP = _parse_details
    do_B_SH = _parse_details
    do_B_SF = _parse_details
    do_B_SB = _parse_details
    do_B_LOB = _parse_details
    do_B_ROE = _parse_details
    do_B_XO = _parse_details_XO

    do_P_GS = _parse_details
    do_P_GF = _parse_details
    do_P_W = _parse_details
    do_P_L = _parse_details
    do_P_SV = _parse_details
    do_P_IP = _parse_details
    do_P_TBF = _parse_details
    do_P_AB = _parse_details
    do_P_R = _parse_details
    do_P_ER = _parse_details
    do_P_H = _parse_details
    do_P_BB = _parse_details
    do_P_SO = _parse_details
    do_P_HP = _parse_details
    do_P_WP = _parse_details
    do_P_BK = _parse_details

    do_F_SB = _parse_details
    do_F_PB = _parse_details
    do_F_DP = _parse_dptp
    do_F_TP = _parse_dptp

    def do_note(self, key, value):   return True

    def parse_playing_value(self, key, value, clubname, columns):
        if key == "TOTALS":
            name, pos = "TOTALS", None
        else:
            try:
                name, pos = map(lambda x: x.strip(), key.split("@"))
                for p in pos.split("-"):
                    if p not in ["p", "c", "1b", "2b", "3b", "ss", "lf", "cf", "rf",
                                "ph", "pr", "?"]:
                        print(f"In file {self.metadata['filename']},\n   game {self}")
                        print(f"  Unknown position in '{key}'")
            except ValueError:
                print(f"In file {self.metadata['filename']},\n   game {self}")
                print(f"  Missing name or position in '{key}'")
                name, pos = key, None
                
        if name[0] == '(':
            slot, name = [x.strip() for x in name[1:].split(")")]
            slot = slot.replace("~", "")
            slot, seq = slot.split(".")
            # TODO: Save slot information

        if name[0] in Game._subskeys:
            subskey = name[0]
            name = name[1:]
        else:
            subskey = None
        if "," in name:
            try:
                name_last, name_first = map(lambda x: x.strip(), name.split(","))
                name = name_first + " " + name_last
            except ValueError:
                print("In file %s,\n   game %s" % (self.metadata['filename'], self))
                print("  Wrong number of names in '%s'" % (name))
                name_last, name_first = name, None
        else:
            name_last, name_first = name, None

        playing = {"name.full": name, "name.last": name_last,
                   "name.first": name_first, "pos": pos,
                   "club.name": clubname, "substitute": subskey}
        stats = [x for x in value.split() if x.strip() != ""]
        if len(stats) != len(columns):
            print("In file %s,\n   game %s" % (self.metadata['filename'], self))
            print("  Incorrect number of categories in '%s: %s'" % (key, value))
        else:
            for (s, c) in zip(stats, columns):
                if s not in ["X", "x"]:
                    playing[c] = s
        return playing

    def process_player_list(self, clubname, header, lines):
        seq = 1
        # "DI" is used sporadically in Winnipeg paper in 1915 - assuming it is RBI
        categorymap = {"ab": "B_AB", "r": "B_R", "h": "B_H",
                       "di": "B_RBI", "rbi": "B_RBI",
                       "sh": "B_SH", "sb": "B_SB",
                       "po": "F_PO", "a": "F_A", "e": "F_E"}
        try:
            columns = [categorymap[c]
                       for c in [x for x in header.split() if x.strip() != ""]]
        except KeyError:
            print("In file %s,\n   game %s" % (self.metadata['filename'], self))
            print("  Unrecognised category line '%s'" % (header))
            columns = []

        while True:
            try:
                key, value = next(lines)
            except StopIteration:
                print("In file %s,\n   game %s" % (self.metadata['filename'], self))
                print("  Unexpected end of game when parsing team '%s'" % clubname)
                return
            playing = self.parse_playing_value(key, value, clubname, columns)
            playing.update({'game.key':    self.metadata['key'],
                            'game.date':   self.date,
                            'game.number': self.number,
                            'game.phase':  self.phase})
            if key != "TOTALS":
               playing['seq'] = str(seq)
               seq += 1
               if playing['name.full'] in self.playing:
                   warnings.warn(DuplicatedNameWarning(self.metadata['filename'],
                                                       self,
                                                       "Duplicated name '%s'" % key))
               elif playing['name.full'] in [self.away, self.home]:
                   warnings.warn(DuplicatedNameWarning(self.metadata['filename'],
                                                       self,
                                                       "Player name '%s' clashes with club name" % key))
               else:
                   self.playing[playing["name.full"]] = playing
            else:
                self.playing[clubname] = playing
                return
            
    def data_pairs(self, text):
        """The data file is essentially a sequence of (key, value) pairs.
        This implements a generator which extracts these.
        """
        for line in text.split("\n"):
            line = line.strip()
            if line == "": continue
            try:
                key, value = [x.strip() for x in line.split(":", 1)]
                yield (key, value)
            except ValueError:
                print("In file %s,\n   game %s" % (self.metadata['filename'], self))
                print("  Invalid key-value pair '%s'" % line)


    @classmethod
    def fromtext(cls, gametext, fn):
        """Parse the game input text format."
        """
        self = cls()
        self.metadata = {"key": game_hash(gametext),
                         "filename": "/".join(fn.parts[-3:]),
                         "phase": "regular",
                         "status": "final"}
        self.playing = {}
        self.umpiring = []
        
        lines = self.data_pairs(gametext)
        while True:
            try:
                key, value = next(lines)
            except StopIteration:
                break
            if key in [self.away, self.home]:
                self.process_player_list(key, value, lines)
            elif key in self._subskeys:
                # TODO: process pinch-hitting
                pass
            else:
                try:
                    func = getattr(self, 'do_' + key.replace("-", "_"))
                except AttributeError:
                    print("In file %s,\n   game %s" % (self.metadata['filename'],
                                                       self))
                    print("  Unknown record key '%s'" % key)
                    continue
                func(key, value)
        return self


def to_csv(df, *args, **kwargs):
    """Pipe-able version of to_csv."""
    df.to_csv(*args, **kwargs)
    return df
    
def iterate_games(fn):
    """Return an iterator over the text of each individual game
    in file `fn'. All extra whitespace is removed within and at the end of
    lines, and lines which are whitespace only are dropped, creating a
    'canonical' representation of the text.
    """
    return iter(filter(lambda x: x.strip() != "",
                       ("\n".join(filter(lambda x: x != "",
                                         [' '.join(x.strip().split()) for x in fn.open().readlines()]))).split("---\n")))

def compile_playing(source, games, gamelist, outpath):
    df = pd.concat([pd.DataFrame(list(g.playing.values())) for g in gamelist],
                   sort=False, ignore_index=True)
    if len(df) == 0:
        return pd.DataFrame(columns=['game.key'])
    df = df.merge(games[['key', 'league']], left_on='game.key', right_on='key') \
           .drop(columns=['name.full', 'substitute'])
    df['league.name'] = df['league'].apply(lambda x: x + " League" if "League" not in x and "Association" not in x else x)
    df = df.assign(**{'league.year': df['game.date'].str.split("-").str[0]}) \
           .drop(columns=['key', 'league']) 
    df['ref'] = df.loc[df['name.last'] != 'TOTALS'].apply(lambda x: person_hash(source, x), axis=1)
    columns = pd.Index(['game.key', 'league.year', 'league.name',
                        'game.date', 'game.number', 'game.phase',
                        'ref', 'name.last', 'name.first', 'club.name',
                        'pos', 'seq',
                        'B_AB', 'B_R', 'B_ER', 'B_H', 'B_2B', 'B_3B', 'B_HR', 'B_RBI',
                        'B_BB', 'B_SO',
                        'B_HP', 'B_SH', 'B_SF', 'B_SB', 'B_XO', 'B_LOB', 'B_ROE',
                        'P_GS', 'P_GF', 'P_W', 'P_L', 'P_SV',
                        'P_IP', 'P_TBF', 'P_AB', 'P_R', 'P_ER', 'P_H', 
                        'P_BB', 'P_SO', 'P_HP', 'P_WP', 'P_BK',
                        'F_PO', 'F_A', 'F_E', 'F_DP', 'F_TP', 'F_PB', 'F_SB'])
    df = df.reindex(pd.Index(columns).union(df.columns), axis=1) \
           .sort_values(['game.date', 'game.number', 'game.key',
                         'club.name', 'seq'])
    for col in df:
        if col not in columns:
            print("WARNING: unexpected column %s in playing" % col)

    return df[columns].pipe(to_csv, outpath/"playing.csv", index=False)

def compile_games(source, gamelist, outpath):
    df = pd.DataFrame([g.metadata for g in gamelist]) \
           .sort_values(['date', 'league', 'home', 'number']) \
           .rename(columns={"away-manager": "away.manager",
                            "home-manager": "home.manager",
                            "status-reason": "status.reason",
                            "forfeit-to": "forfeit.to"})
    columns = ['key', 'date', 'number', 'league', 'phase', 'site',
               'away', 'away.score', 'away.manager',
               'home', 'home.score', 'home.manager',
               'A', 'T', 'forfeit.to',
               'status', 'status.reason', 'outsatend', 'filename', 'source']
    for inning in range(100):
        if ('away.score.%d' % inning) in df.columns:
            columns.append('away.score.%d' % inning)
    for inning in range(100):
        if ('home.score.%d' % inning) in df.columns:
            columns.append('home.score.%d' % inning)

    for col in columns:
        if col not in df:
            df[col] = None
    for col in df:
        if col not in columns:
            print("WARNING: unexpected column %s in games" % col)
    return df[columns].pipe(to_csv, outpath/"games.csv", index=False)

def compile_umpiring(source, games, gamelist, outpath):
    df = pd.concat([pd.DataFrame(g.umpiring) for g in gamelist],
                   sort=False, ignore_index=True)
    if len(df) == 0:
        return pd.DataFrame(columns=['game.key'])
    df = pd.merge(df, games[['key', 'league']],
                  left_on='game.key', right_on='key')
    df['league.name'] = df['league'].apply(lambda x: x + " League" if "League" not in x and "Association" not in x else x)
    df['league.year'] = df['game.date'].str.split("-").str[0]
    df = df.drop(columns=['key', 'league'])
    df['club.name'] = 'umpire'
    df['ref'] = df.apply(lambda x: person_hash(source, x), axis=1)
    columns = ['game.key', 'league.year', 'league.name',
               'game.date', 'game.number', 'game.phase',
               'ref', 'name.last', 'name.first']
    return df[columns].pipe(to_csv, outpath/"umpiring.csv", index=False)


def compile_players(source, playing, outpath):
    if len(playing) == 0:
        return
    playing['B_G'] = 1
    for pos in ['p', 'c', '1b', '2b', '3b', 'ss', 'lf', 'cf', 'rf']:
        playing['F_%s_G' % pos.upper()] = playing['pos'].apply(lambda x: (1 if pos in x.split("-") else 0) if not pd.isnull(x) else 0)
    playing['F_OF_G'] = playing['F_LF_G'] | playing['F_CF_G'] | \
                        playing['F_RF_G']
    playing['P_G'] = playing['F_P_G']
    playing['name.first'] = playing['name.first'].fillna("")
    playing = playing[playing['name.last'] != "TOTALS"]
    grouper = playing.groupby(['league.year', 'league.name', 'game.phase',
                               'name.last', 'name.first', 'club.name', 'ref'])
    df = grouper.sum()
    df = df.join(grouper[['game.date']].min().rename(columns={'game.date': 'S_FIRST'})) \
           .join(grouper[['game.date']].max().rename(columns={'game.date': 'S_LAST'})) \
           .reset_index() \
           .rename(columns={'ref':       'person.ref',
                            'name.last':  'person.name.last',
                            'name.first': 'person.name.given',
                            'club.name':  'entry.name',
                            'year':       'league.year',
                            'league':     'league.name',
                            'game.phase':  'league.phase'}) \
           [['league.year', 'league.name', 'league.phase', 'person.ref',
             'person.name.last', 'person.name.given', 'entry.name',
             'S_FIRST', 'S_LAST', 'B_G', 'P_G',
             'F_1B_G', 'F_2B_G', 'F_3B_G', 'F_SS_G',
             'F_OF_G', 'F_LF_G', 'F_CF_G', 'F_RF_G',
             'F_C_G', 'F_P_G']] \
           .to_csv(outpath/"players.csv", index=False, float_format='%d')


def compile_umpires(source, umpiring, outpath):
    if len(umpiring) == 0:
        return
    umpiring['U_G'] = 1
    umpiring['name.first'] = umpiring['name.first'].fillna("")
    grouper = umpiring.groupby(['league.year', 'league.name', 'game.phase',
                                'name.last', 'name.first', 'ref'])
    df = grouper.sum()
    df = df.join(grouper[['game.date']].min().rename(columns={'game.date': 'S_FIRST'})) \
           .join(grouper[['game.date']].max().rename(columns={'game.date': 'S_LAST'})) \
           .reset_index() \
           .rename(columns={'ref':        'person.ref',
                            'name.last':  'person.name.last',
                            'name.first': 'person.name.given',
                            'year':       'league.year',
                            'league':     'league.name',
                            'game.phase': 'league.phase'}) \
           [['league.year', 'league.name', 'league.phase', 'person.ref',
             'person.name.last', 'person.name.given',
             'S_FIRST', 'S_LAST', 'U_G']] \
           .to_csv(outpath/"umpires.csv", index=False, float_format='%d')

    
def process_files(source, inpath, outpath):
    fnlist = [fn for fn in sorted(inpath.glob("*.txt"))
              if fn.name.lower() not in ["readme.txt", "notes.txt"]]
    if len(fnlist) == 0:
        print(clr.Fore.RED + ("No files found at '%s'" % inpath) +
              clr.Fore.RESET)
        sys.exit(1)
    gamelist = [Game.fromtext(g, fn)
                for fn in fnlist for g in iterate_games(fn)]

    games = compile_games(source, gamelist, outpath)
    playing = compile_playing(source, games, gamelist, outpath)
    umpiring = compile_umpiring(source, games, gamelist, outpath)
    compile_players(source, playing, outpath)
    compile_umpires(source, umpiring, outpath)


def main(source, warn_duplicates, warn_marked):
    warnings.simplefilter('error', DuplicatedNameWarning)
    warnings.simplefilter('ignore', MarkedIdentificationWarning)
    #warnings.simplefilter('error', IdentificationWarning)
    if warn_duplicates:
        warnings.simplefilter('default', DuplicatedNameWarning)
    if warn_marked:
        warnings.simplefilter('always', MarkedIdentificationWarning)

    try:
        year, paper = source.split("-")
    except ValueError:
        print(clr.Fore.RED + ("Invalid source name '%s'" % source) + clr.Fore.RESET)
        sys.exit(1)
        
    inpath = config.data_path/"transcript"/year/source
    outpath = config.data_path/"processed"/year/source
    outpath.mkdir(exist_ok=True, parents=True)
        
    try:
        process_files(year + "/" + source, inpath, outpath)
    except DuplicatedNameWarning as exc:
        print(clr.Fore.RED + str(exc) + clr.Fore.RESET)
        sys.exit(1)

