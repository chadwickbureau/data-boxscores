import sys
import os
import glob
import hashlib
import argparse
import warnings

import colorama as clr
import pandas as pd

def person_hash(source, row):
    """Generate hash-based identifier for a person based on the source
    and identifying elements of the person's record (season, name, club).
    """
    def hash_djb2(s):
        hash = 5381
        for x in s:
            hash = (( hash << 5) + hash) + ord(x)
        return "P" + ("%d" % hash)[-7:]
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
        else:
            return int_to_base(n // base) + alphabet[n % base]
    return int_to_base(int(hashlib.sha1(s).hexdigest(), 16))[-7:]


class BoxscoreParserWarning(UserWarning):
    pass

class IdentificationWarning(BoxscoreParserWarning):
    """A warning class on unidentified name.
    """
    def __init__(self, fn, game, message):
        UserWarning.__init__(self,
                             "In file %s,\n   game %s\n  %s" % 
                             (fn, game, message))

class MarkedIdentificationWarning(BoxscoreParserWarning):
    """A warning class on unidentified name which is explicitly marked.
    """
    def __init__(self, fn, game, message):
        UserWarning.__init__(self,
                             "In file %s,\n   game %s\n  %s" % 
                             (fn, game, message))

        
class DuplicatedNameWarning(BoxscoreParserWarning):
    """A warning class for duplicated names.
    """
    def __init__(self, fn, game, message):
        UserWarning.__init__(self,
                             "In file %s,\n   game %s\n  %s" % 
                             (fn, game, message))

        
def _formatwarning(msg, category, *args, **kwargs):
    return str(msg) + '\n'
warnings.formatwarning = _formatwarning


class Game(object):
    _subskeys = [ "*", "+", "^", "&", "$" ]
    # "DI" is used sporadically in Winnipeg paper in 1915 - assuming it is RBI
    _categorymap = { "ab":   "B_AB",
                     "r":    "B_R",
                     "h":    "B_H",
                     "po":   "F_PO",
                     "a":    "F_A",
                     "e":    "F_E",
                     "di":   "B_RBI",
                     "rbi":  "B_RBI" }
    
    @property
    def date(self):  return self.metadata.get("date")
    @property
    def number(self): return self.metadata.get("number")
    @property
    def phase(self):  return self.metadata.get("phase")
    @property
    def away(self):  return self.metadata.get("away")
    @property
    def home(self):  return self.metadata.get("home")

    def __str__(self):
        return "%s[%s]: %s at %s" % (self.date, self.number,
                                     self.away, self.home)

    def _parse_playing_value(self, key, value, clubname, columns):
        if key == "TOTALS":
            name, pos = "TOTALS", None
        else:
            try:
                name, pos = map(lambda x: x.strip(), key.split("@"))
            except ValueError:
                print "In file %s,\n   game %s" % (self.metadata['filename'], self)
                print "  Missing name or position in '%s'" % (key)
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
                print "In file %s,\n   game %s" % (self.metadata['filename'], self)
                print "  Wrong number of names in '%s'" % (name)
                name_last, name_first = name, None
        else:
            name_last, name_first = name, None

        playing = { "name.full": name, "name.last": name_last,
                    "name.first": name_first, "pos": pos,
                    "club.name": clubname, "substitute": subskey }
        stats = filter(lambda x: x.strip() != "", value.split())
        if len(stats) != len(columns):
            print "In file %s,\n   game %s" % (self.metadata['filename'], self)
            print "  Incorrect number of categories in '%s: %s'" % (key, value)
        else:
            for (s, c) in zip(stats, columns):
                if s not in [ "X", "x" ]:
                    playing[c] = s
        return playing

    def _parse_details(self, key, value):
        for entry in [x.strip() for x in value.split(";")]:
            if entry[0] == '~':
                entry = entry[1:]
            if "#" in entry:
                try:
                    name, count = [x.strip() for x in entry.split("#")]
                except ValueError:
                    print "In file %s,\n   game %s" % (self.metadata['filename'], self)
                    print "  Ill-formed details string '%s'" % entry
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
                    warnings.warn(MarkedIdentificationWarning(self.metadata['filename'],
                                                        self,
                                                        "No match on name '??%s' in '%s'" % (name, key)))
                else:
                    warnings.warn(IdentificationWarning(self.metadata['filename'],
                                                        self,
                                                        "No match on name '%s' in '%s'" % (name, key)))

    def _parse_details_XO(self, key, value):
        for entry in [x.strip() for x in value.split(";")]:
            try:
                name, reason = [x.strip() for x in entry.split(",")]
            except ValueError:
                print "In file %s,\n   game %s" % (self.metadata['filename'], self)
                print "  Ill-formed details string '%s'" % entry
                return
            try:
                self.playing[name]['B_XO'] = self.playing[name].get('B_XO', 0)+1
            except KeyError:
                print "In file %s,\n   game %s" % (self.metadata['filename'], self)
                print "  No match on name '%s' in '%s'" % (name, key)
                
    def _parse_dptp(self, key, value):
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

    def _process_linescore(self, value):
        try:
            club, score = map(lambda x: x.strip(), value.split(":"))
        except ValueError:
            print "In file %s,\n   game %s" % (self.metadata['filename'], self)
            print "  Ill-formed linescore string '%s'" % value
            return
        
        if club == self.away:
            prefix = "away.score"
        elif club == self.home:
            prefix = "home.score"
        else:
            print "In file %s,\n   game %s" % (self.metadata['filename'], self)
            print "  No match on club name '%s'" % (club)
            return

        byinning, total = map(lambda x: x.strip(), score.split("-"))
        self.metadata[prefix] = total
        for (inning, s) in enumerate(byinning.split()):
            self.metadata['%s.%d' % (prefix, inning+1)] = s
        
    @classmethod
    def fromtext(cls, gametext, fn):
        """Parse the game input text format."
        """
        self = cls()
        self.metadata = { "key": game_hash(gametext),
                          "filename": fn,
                          "phase": "regular" }
        self.playing = { }
        self.umpiring = [ ]

        clubname = None
        columns = None
        seq = None
        for line in filter(lambda x: x.strip() != "", gametext.split("\n")):
            try:
                key, value = map(lambda x: x.strip(), line.split(":", 1))
            except ValueError:
                print "In file %s,\n   game %s" % (self.metadata['filename'], self)
                print "  Invalid key-value pair '%s'" % line
                continue
                
                
            if clubname is not None:
                playing = self._parse_playing_value(key, value, clubname, columns)
                playing['game.key'] = self.metadata["key"]
                playing['game.date'] = self.date
                playing['game.number'] = self.number
                playing['game.phase'] = self.phase
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
                    clubname = None

            elif key in [ self.away, self.home ]:
                clubname = key
                seq = 1
                columns = filter(lambda x: x.strip() != "", value.split())
                try:
                    columns = [ self._categorymap[c] for c in columns ]
                except KeyError:
                    print "In file %s,\n   game %s" % (self.metadata['filename'], self)
                    print "  Unrecognised category line '%s'" % (value)
                    columns = []

            elif key == "key":
                # Some files had manually set keys - we have deprecated these
                pass
            
            elif key in ["date", "number", "league", "away", "home", "site",
                         "source", "A", "T", "status", "status-reason",
                         "home-manager", "away-manager", "forfeit-to",
                         "outsatend", "phase"]:
                self.metadata[key] = value

            elif key in ["home-batted"]:
                pass
                
            elif key in [ "B_ER", "B_2B", "B_3B", "B_HR", "B_BB", "B_SO",
                          "B_SH", "B_HP",
                          "B_SH", "B_SF", "B_SB",
                          "B_LOB", "B_ROE",
                          "P_GS", "P_GF", "P_W", "P_L", "P_SV",
                          "P_IP", "P_AB", "P_R", "P_ER", "P_H",
                          "P_HP", "P_BB", "P_SO",
                          "P_TBF", "P_WP", "P_BK",
                          "F_SB", "F_PB" ]:
                if value != "":
                    self._parse_details(key, value)

            elif key == "B_XO":
                if value != "":
                    self._parse_details_XO(key, value)

            elif key in [ "F_DP", "F_TP" ]:
                if value != "":
                    self._parse_dptp(key, value)
        
            elif key == "U":
                self.umpiring = [self._parse_umpire(x)
                                 for x in map(lambda x: x.strip(),
                                              value.split(";")) ]

            elif key == "line":
                self._process_linescore(value)

            elif key in self._subskeys:
                # TODO: process pinch-hitting
                pass

            elif key in [ "note" ]:
                # TODO: process notes
                pass

            else:
                print "In file %s,\n   game %s" % (self.metadata['filename'],
                                                   self)
                print "  Unknown record key '%s'" % key

        return self


def iterate_games(fn):
    """Return an iterator over the text of each individual game
    in file `fn'. All extra whitespace is removed within and at the end of
    lines, and lines which are whitespace only are dropped, creating a
    'canonical' representation of the text.
    """
    return iter(filter(lambda x: x.strip() != "",
                       ("\n".join(filter(lambda x: x != "",
                                         [ ' '.join(x.strip().split()) for x in open(fn).readlines() ]))).split("---\n")))

def compile_playing(source, games, gamelist):
    df = pd.concat([ pd.DataFrame(g.playing.values()) for g in gamelist ],
                   ignore_index=True)
    df = pd.merge(df, games[['key', 'league']],
                  left_on='game.key', right_on='key')
    del df['name.full']
    del df['substitute']
    df['league.name'] = df['league'].apply(lambda x: x + " League" if "League" not in x and "Association" not in x else x)
    df['league.year'] = df['game.date'].str.split("-").str[0]
    del df['key']
    del df['league']
    df['ref'] = df.loc[df['name.last']!='TOTALS'].apply(lambda x: person_hash(source, x), axis=1)
    columns = ['game.key', 'league.year', 'league.name',
               'game.date', 'game.number', 'game.phase',
               'ref', 'name.last', 'name.first', 'club.name',
               'pos', 'seq',
               'B_AB', 'B_R', 'B_ER', 'B_H', 'B_2B', 'B_3B', 'B_HR', 'B_RBI',
               'B_BB', 'B_SO',
               'B_HP', 'B_SH', 'B_SF', 'B_SB', 'B_XO', 'B_LOB', 'B_ROE',
               'P_GS', 'P_GF', 'P_W', 'P_L', 'P_SV',
               'P_IP', 'P_TBF', 'P_AB', 'P_R', 'P_ER', 'P_H', 
               'P_BB', 'P_SO', 'P_HP', 'P_WP', 'P_BK',
               'F_PO', 'F_A', 'F_E', 'F_DP', 'F_TP', 'F_PB', 'F_SB' ]
    for col in columns:
        if col not in df:
            df[col] = None
    for col in df:
        if col not in columns:
            print "WARNING: unexpected column %s in playing" % col

    df.sort_values([ 'game.date', 'game.number', 'game.key',
                     'club.name', 'seq' ], inplace=True)
    try:
        os.makedirs("processed/%s" % source)
    except os.error:
        pass
    df = df[columns].copy()
    df.to_csv("processed/%s/playing.csv" % source, index=False)
    return df

def compile_games(source, gamelist):
    df = pd.DataFrame([ g.metadata for g in gamelist ])
    df.sort_values([ 'date', 'league', 'home', 'number' ], inplace=True)
    df.rename(inplace=True,
              columns={ "away-manager": "away.manager",
                        "home-manager": "home.manager",
                        "status-reason": "status.reason",
                        "forfeit-to": "forfeit.to" })
    columns = [ 'key', 'date', 'number', 'league', 'phase', 'site',
                'away', 'away.score', 'away.manager',
                'home', 'home.score', 'home.manager',
                'A', 'T', 'forfeit.to',
                'status', 'status.reason', 'outsatend', 'filename', 'source' ]
    for inning in xrange(100):
        if ('away.score.%d' % inning) in df.columns:
            columns.append('away.score.%d' % inning)
    for inning in xrange(100):
        if ('home.score.%d' % inning) in df.columns:
            columns.append('home.score.%d' % inning)

    for col in columns:
        if col not in df:
            df[col] = None
    for col in df:
        if col not in columns:
            print "WARNING: unexpected column %s in games" % col
    df = df[columns].copy()
    df.to_csv("processed/%s/games.csv" % source, index=False)
    return df

def compile_umpiring(source, games, gamelist):
    df = pd.concat([ pd.DataFrame(g.umpiring) for g in gamelist ],
                   ignore_index=True)
    df = pd.merge(df, games[[ 'key', 'league' ]],
                  left_on='game.key', right_on='key')
    df['league.name'] = df['league'].apply(lambda x: x + " League" if "League" not in x and "Association" not in x else x)
    df['league.year'] = df['game.date'].str.split("-").str[0]
    del df['key']
    del df['league']
    df['club.name'] = 'umpire'
    df['ref'] = df.apply(lambda x: person_hash(source, x), axis=1)
    columns = ['game.key', 'league.year', 'league.name',
               'game.date', 'game.number', 'game.phase',
               'ref', 'name.last', 'name.first']
    df = df[columns].copy()
    df.to_csv("processed/%s/umpiring.csv" % source, index=False)
    return df


def compile_players(source, playing):
    playing['B_G'] = 1
    for pos in ['p', 'c', '1b', '2b', '3b', 'ss', 'lf', 'cf', 'rf']:
        playing['F_%s_G' % pos.upper()] = playing['pos'].apply(lambda x: (1 if pos in x.split("-") else 0) if not pd.isnull(x) else 0)
    playing['F_OF_G'] = playing['F_LF_G'] | playing['F_CF_G'] | \
                        playing['F_RF_G']
    playing['P_G'] = playing['F_P_G']
    playing['name.first'] = playing['name.first'].fillna("")
    playing = playing[playing['name.last']!="TOTALS"]
    grouper = playing.groupby(['league.year', 'league.name', 'game.phase',
                               'name.last', 'name.first', 'club.name', 'ref'])
    df = grouper.sum()
    df = pd.merge(df,
                  grouper[['game.date']].min().rename(columns={'game.date': 'S_FIRST'}),
                  left_index=True, right_index=True)
    df = pd.merge(df,
                  grouper[['game.date']].max().rename(columns={'game.date': 'S_LAST'}),
                  left_index=True, right_index=True)
    df.reset_index(inplace=True)
    
    df.rename(inplace=True,
              columns={'ref':       'person.ref',
                       'name.last':  'person.name.last',
                       'name.first': 'person.name.given',
                       'club.name':  'entry.name',
                       'year':       'league.year',
                       'league':     'league.name',
                       'game.phase':  'league.phase'})
    df = df[['league.year', 'league.name', 'league.phase', 'person.ref',
             'person.name.last', 'person.name.given', 'entry.name',
             'S_FIRST', 'S_LAST', 'B_G', 'P_G',
             'F_1B_G', 'F_2B_G', 'F_3B_G', 'F_SS_G',
             'F_OF_G', 'F_LF_G', 'F_CF_G', 'F_RF_G',
             'F_C_G', 'F_P_G']]
    df.to_csv("processed/%s/players.csv" % source, index=False,
              float_format='%d')


def compile_umpires(source, umpiring):
    umpiring['U_G'] = 1
    umpiring['name.first'] = umpiring['name.first'].fillna("")
    grouper = umpiring.groupby(['league.year', 'league.name', 'game.phase',
                                'name.last', 'name.first', 'ref'])
    df = grouper.sum()
    df = pd.merge(df,
                  grouper[['game.date']].min().rename(columns={'game.date': 'S_FIRST'}),
                  left_index=True, right_index=True)
    df = pd.merge(df,
                  grouper[['game.date']].max().rename(columns={'game.date': 'S_LAST'}),
                  left_index=True, right_index=True)
    df.reset_index(inplace=True)

    df.rename(inplace=True,
              columns={'ref':        'person.ref',
                       'name.last':  'person.name.last',
                       'name.first': 'person.name.given',
                       'year':       'league.year',
                       'league':     'league.name',
                       'game.phase': 'league.phase'})
    df = df[['league.year', 'league.name', 'league.phase', 'person.ref',
             'person.name.last', 'person.name.given',
             'S_FIRST', 'S_LAST', 'U_G']]
    df.to_csv("processed/%s/umpires.csv" % source, index=False,
              float_format='%d')

    
def process_files(source):
    fnlist = [fn for fn in glob.glob("transcript/%s/*.txt" % source)
              if "README.txt" not in fn]
    gamelist = [ Game.fromtext(g, fn)
                 for fn in fnlist for g in iterate_games(fn) ]
    games = compile_games(source, gamelist)
    playing = compile_playing(source, games, gamelist)
    umpiring = compile_umpiring(source, games, gamelist)

    compile_players(source, playing)
    compile_umpires(source, umpiring)


def main():
    parser = argparse.ArgumentParser(description='Parse boxscore files')
    parser.add_argument('source', type=str,
                        help='path to the source collection')
    parser.add_argument('--warn-duplicates', '-D', default=False,
                        action='store_true',
                        help='only warn on duplicate name in game (default is terminate)')
    parser.add_argument('--warn-marked', '-M', default=False,
                        action='store_true',
                        help='warn on marked dubious names (default is ignore)')

    args = parser.parse_args()
    warnings.simplefilter('error', DuplicatedNameWarning)
    warnings.simplefilter('ignore', MarkedIdentificationWarning)
    #warnings.simplefilter('error', IdentificationWarning)
    if args.warn_duplicates:
        warnings.simplefilter('default', DuplicatedNameWarning)
    if args.warn_marked:
        warnings.simplefilter('always', MarkedIdentificationWarning)
        
    try:
        process_files(args.source)
    except DuplicatedNameWarning as e:
        print clr.Fore.RED + str(e) + clr.Fore.RESET
        sys.exit(1)

    
if __name__ == '__main__':
    main()
        
    
    
