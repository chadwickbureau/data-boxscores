import os
import glob
import uuid

import pandas as pd

import fuzzy

class Game(object):
    _subskeys = [ "*", "+", "^" ]
    _categorymap = { "ab":   "B_AB",
                     "r":    "B_R",
                     "h":    "B_H",
                     "po":   "F_PO",
                     "a":    "F_A",
                     "e":    "F_E" }
    
    @property
    def date(self):  return self.metadata.get("date")
    @property
    def number(self): return self.metadata.get("number")
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
                
        if name[0] in Game._subskeys:
            subskey = name[0]
            name = name[1:]
        else:
            subskey = None
        if "," in name:
            name_last, name_first = map(lambda x: x.strip(), name.split(","))
            name = name_first + " " + name_last
        else:
            name_last, name_first = name, None

        playing = { "name.full": name, "name.last": name_last,
                    "name.first": name_first, "pos": pos,
                    "club.name": clubname, "substitute": subskey }
        stats = filter(lambda x: x.strip() != "", value.split())
        if len(stats) != len(columns):
            print "In file %s,\n   game %s" % (self.metadata['filename'], self)
            print "  Column mismatch in stat line '%s'" % value
            return

        for (s, c) in zip(stats, columns):
            if s not in [ "X", "x" ]:
                playing[c] = s
        return playing

    def _parse_details(self, key, value):
        for entry in map(lambda x: x.strip(), value.split(";")):
            if "#" in entry:
                try:
                    name, count = map(lambda x: x.strip(), entry.split("#"))
                except ValueError:
                    print "In file %s,\n   game %s" % (self.metadata['filename'], self)
                    print "  Ill-formed details string '%s'" % entry
                    return
                    
            else:
                name, count = entry, "1"
            try:
                self.playing[name][key] = count
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
                try:
                    playing = self.playing[name]
                except KeyError:
                    print "In file %s,\n   game %s" % (self.metadata['filename'], self)
                    print "  No match on name '%s' in '%s'" % (name, key)
                    continue
                playing[key] = str(int(playing.get(key, 0)) + int(count))
            
    def _process_linescore(self, value):
        club, score = map(lambda x: x.strip(), value.split(":"))
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
        self.metadata = { "key": uuid.uuid5(uuid.NAMESPACE_DNS, gametext),
                          "filename": fn }
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
                if key != "TOTALS":
                    playing['seq'] = str(seq)
                    seq += 1
                    # TODO: Warn on name clashes!
                    self.playing[playing["name.full"]] = playing
                else:
                    self.playing[clubname] = playing
                    clubname = None

            elif key in [ self.away, self.home ]:
                clubname = key
                seq = 1
                columns = filter(lambda x: x.strip() != "", value.split())
                columns = [ self._categorymap[c] for c in columns ]

            elif key == "key":
                # Some files had manually set keys - we have deprecated these
                pass
            
            elif key in [ "date", "number", "league", "away", "home", "site",
                          "source", "A", "T", "status", "status-reason",
                          "home-manager", "away-manager", "forfeit-to" ]:
                self.metadata[key] = value

            elif key in [ "B_ER", "B_2B", "B_3B", "B_HR", "B_BB", "B_SO",
                          "B_SH", "B_HP",
                          "B_SH", "B_SF", "B_SB",
                          "B_LOB", "B_ROE",
                          "P_IP", "P_R", "P_H", "P_HP", "P_BB", "P_SO",
                          "P_WP", "P_BK",
                          "F_PB" ]:
                if value != "":
                    self._parse_details(key, value)

            elif key in [ "F_DP", "F_TP" ]:
                if value != "":
                    self._parse_dptp(key, value)
        
            elif key == "U":
                self.umpiring = [ { "game.key": self.metadata["key"],
                                    "game.date": self.date,
                                    "game.number": self.number,
                                    "name.full": x }
                                     for x in map(lambda x: x.strip(),
                                                  value.split(";")) ]
            elif key in [ "line" ]:
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

def compile_playing(source, gamelist):
    df = pd.concat([ pd.DataFrame(g.playing.values()) for g in gamelist ],
                   ignore_index=True)
    del df['name.full']
    del df['substitute']
    columns = [ 'game.key', 'game.date', 'game.number',
                'name.last', 'name.first', 'club.name',
                'pos', 'seq',
                'B_AB', 'B_R', 'B_ER', 'B_H', 'B_2B', 'B_3B', 'B_HR',
                'B_BB', 'B_SO',
                'B_HP', 'B_SH', 'B_SF', 'B_SB', 'B_LOB', 'B_ROE',
                'P_IP', 'P_R', 'P_H', 'P_BB', 'P_SO', 'P_HP', 'P_WP', 'P_BK',
                'F_PO', 'F_A', 'F_E', 'F_DP', 'F_TP', 'F_PB' ]
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
    columns = [ 'key', 'date', 'number', 'league', 'site',
                'away', 'away.score', 'away.manager',
                'home', 'home.score', 'home.manager',
                'A', 'T', 'forfeit.to',
                'status', 'status.reason', 'filename', 'source' ]
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

def compile_umpiring(source, gamelist):
    df = pd.concat([ pd.DataFrame(g.umpiring) for g in gamelist ],
                   ignore_index=True)
    columns = [ 'game.key', 'game.date', 'game.number', 'name.full' ]
    df = df[columns].copy()
    df.to_csv("processed/%s/umpiring.csv" % source, index=False)
    return df

def compile_people(source, playing, games):
    playing = pd.merge(playing, games[[ 'key', 'league' ]],
                       left_on='game.key', right_on='key')
    playing['league'] = playing['league'].apply(lambda x: x + " League" if "League" not in x and "Association" not in x else x)
    playing['year'] = playing['game.date'].str.split("-").str[0]
    playing['B_G'] = 1
    for pos in [ 'p', 'c', '1b', '2b', '3b', 'ss', 'lf', 'cf', 'rf' ]:
        playing['F_%s_G' % pos.upper()] = playing['pos'].apply(lambda x: (1 if pos in x.split("-") else 0) if not pd.isnull(x) else 0)
    playing['F_OF_G'] = playing['F_LF_G'] | playing['F_CF_G'] | \
                        playing['F_RF_G']
    playing['P_G'] = playing['F_P_G']
    playing['name.first'] = playing['name.first'].fillna("")
    playing = playing[playing['name.last']!="TOTALS"]
    grouper = playing.groupby([ 'year', 'league',
                                'name.last', 'name.first', 'club.name' ])
    df = grouper.sum()
    df = pd.merge(df, grouper[[ 'game.date' ]].min().rename(columns={ 'game.date': 'S_FIRST' }),
                  left_index=True, right_index=True)
    df = pd.merge(df, grouper[[ 'game.date' ]].max().rename(columns={ 'game.date': 'S_LAST' }),
                  left_index=True, right_index=True)
    df.reset_index(inplace=True)

    df['metaphone'] = df['name.last'].apply(lambda x: fuzzy.DMetaphone()(x.split("[")[0])[0].ljust(4, 'Z'))
    df['metaseq'] = df.groupby([ 'year', 'league', 'metaphone' ]).cumcount() + 1
    df['metacount'] = df.groupby([ 'year', 'league', 'metaphone' ])['metaseq'].transform('count')
    df['person.ref'] = df.apply(lambda x: "%s%02d%02d" %
                                  (x.metaphone, x.metaseq, x.metacount),
                                  axis=1)
    df.rename(inplace=True,
              columns={ 'name.last':  'person.name.last',
                        'name.first': 'person.name.given',
                        'club.name':  'entry.name',
                        'year':       'league.year',
                        'league':     'league.name' })
    df = df[[ 'league.year', 'league.name', 'person.ref',
              'person.name.last', 'person.name.given', 'entry.name',
              'S_FIRST', 'S_LAST', 'B_G', 'P_G',
              'F_1B_G', 'F_2B_G', 'F_3B_G', 'F_SS_G',
              'F_OF_G', 'F_LF_G', 'F_CF_G', 'F_RF_G',
              'F_C_G', 'F_P_G' ]]
    df.to_csv("processed/%s/people.csv" % source, index=False,
              float_format='%d')

    
def process_files(source):
    fnlist = glob.glob("transcript/%s/boxes/*.txt" % source)
    gamelist = [ Game.fromtext(g, fn)
                 for fn in fnlist for g in iterate_games(fn) ]
    playing = compile_playing(source, gamelist)
    games = compile_games(source, gamelist)
    umpiring = compile_umpiring(source, gamelist)

    compile_people(source, playing, games)
                                  
                                  
                                      
if __name__ == '__main__':
    import sys
    import glob

    source = sys.argv[1]
    
    process_files(source)
        
    
    
