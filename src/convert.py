import os
import glob
import uuid

import pandas as pd


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

    @staticmethod
    def _parse_playing_value(key, value, clubname, columns):
        if key == "TOTALS":
            name, pos = "TOTALS", None
        else:
            name, pos = map(lambda x: x.strip(), key.split("@"))
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
        assert len(stats) == len(columns)
        for (s, c) in zip(stats, columns):
            playing[c] = s
        return playing

    def _parse_details(self, key, value):
        for entry in map(lambda x: x.strip(), value.split(";")):
            if "#" in entry:
                name, count = map(lambda x: x.strip(), entry.split("#"))
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
            for name in map(lambda x: x.strip(), names.split(",")):
                try:
                    playing = self.playing[name]
                except KeyError:
                    print "In file %s,\n   game %s" % (self.metadata['filename'], self)
                    print "  No match on name '%s' in '%s'" % (name, key)
                    continue
                playing[key] = str(int(playing.get(key, 0)) + count)
                
            
    def _process_linescore(self, value):
        club, score = map(lambda x: x.strip(), value.split(":"))
        if club == self.away:
            prefix = "away.score"
        elif club == self.home:
            prefix = "home.score"
        else:
            print "In file %s,\n   game %s" % (self.metadata['filename'], self)
            print "  No match on club name '%s' in '%s'" % (name, club)
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
            key, value = map(lambda x: x.strip(), line.split(":", 1))

            if clubname is not None:
                playing = self._parse_playing_value(key, value, clubname, columns)
                playing['game.key'] = self.metadata["key"]
                playing['game.date'] = self.date
                playing['game.number'] = self.number
                if key != "TOTALS":
                    playing['seq'] = seq
                    seq += 1
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
            
            elif key in [ "date", "number", "league", "away", "home",
                          "source", "A", "T", "status", "status-reason" ]:
                self.metadata[key] = value

            elif key in [ "B_2B", "B_3B", "B_HR", "B_SH", "B_HP",
                          "B_SH", "B_SF", "B_SB",
                          "B_LOB", "B_ROE",
                          "P_IP", "P_H", "P_HP", "P_BB", "P_SO", "P_WP", "P_BK",
                          "F_PB" ]:
                if value != "":
                    self._parse_details(key, value)

            elif key in [ "F_DP", "F_TP" ]:
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


def games(fn):
    """Return an iterator over the text of each individual game
    in file `fn'. All extra whitespace is removed within and at the end of
    lines, and lines which are whitespace only are dropped, creating a
    'canonical' representation of the text.
    """
    return iter(filter(lambda x: x.strip() != "",
                       ("\n".join(filter(lambda x: x != "",
                                         [ ' '.join(x.strip().split()) for x in open(fn).readlines() ]))).split("---\n")))

def process_files(source):
    fnlist = glob.glob("transcript/%s/boxes/*.txt" % source)
    gamelist = [ Game.fromtext(g, fn)
                 for fn in fnlist for g in games(fn) ]

    df = pd.concat([ pd.DataFrame(g.playing.values()) for g in gamelist ],
                   ignore_index=True)
    del df['name.full']
    del df['substitute']
    columns = [ 'game.key', 'game.date', 'game.number',
                'name.last', 'name.first', 'club.name',
                'pos', 'seq', 'substitute',
                'B_AB', 'B_R', 'B_H', 'B_2B', 'B_3B', 'B_HR',
                'B_HP', 'B_SH', 'B_SF', 'B_SB', 'B_LOB', 'B_ROE',
                'P_IP', 'P_H', 'P_BB', 'P_SO', 'P_HP', 'P_WP', 'P_BK',
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
    df[columns].to_csv("processed/%s/playing.csv" % source, index=False)

    df = pd.DataFrame([ g.metadata for g in gamelist ])
    df.sort_values([ 'date', 'league', 'home', 'number' ], inplace=True)
    columns = [ 'key', 'date', 'number', 'league',
                'away', 'away.score', 'home', 'home.score', 'A', 'T',
                'status', 'status-reason', 'filename', 'source' ]
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
        
    df[columns].to_csv("processed/%s/games.csv" % source, index=False)
                                  
    df = pd.concat([ pd.DataFrame(g.umpiring) for g in gamelist ],
                   ignore_index=True)
    columns = [ 'game.key', 'game.date', 'game.number', 'name.full' ]
    df[columns].to_csv("processed/%s/umpiring.csv" % source, index=False)
                                  
                                      
if __name__ == '__main__':
    import sys
    import glob

    source = sys.argv[1]
    
    process_files(source)
        
    
    
