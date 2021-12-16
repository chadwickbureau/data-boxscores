Historical minor league baseball boxscores
Prepared and maintained by Chadwick Baseball Bureau (http://www.chadwick-bureau.com)
Contact: Dr T L Turocy (ted.turocy@gmail.com)

## About this data

This package contains transcriptions of historical minor league boxscores.
Please read the description below carefully to be sure you understand what
these data are (and what they aren't).


## Copyright and license

These files are copyright by Chadwick Baseball Bureau.
They are licensed under the Creative Commons Attribution 4.0 International license:
https://creativecommons.org/licenses/by/4.0/

The source code to transform the original transcriptions into standardised formats
(found in the src/ directory) is copyright by T L Turocy and Chadwick Baseball Bureau.
It is licensed under the GNU General Public Licence, version 2.0 (or later, at the
user's discretion):
https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html


## Details

Historically, the published averages for many minor leagues in baseball omitted
players who appeared in only a handful of games ("less-thans"); other leagues
never published complete averages at all.  In these cases, the only way to
document the participation of these players is by capturing a published boxscore.
In addition, there are other reasons why having a compilation of game-level
data for some historical minor leagues may be of interest.

We have developed a simple, text-based format for capturing boxscores efficiently.
This format is similar to the structure of a typical newspaper boxscore,
allowing transcription of the data, with only a minimum of markup required of
the inputter.  These files are organised in the transcript/ directory.
Each source is included in separate subdirectory.  For example, a source might 
consist of all boxscores found in a particular newspaper in a particular year.

There is a parser, implemented in the Python 'boxscore' package
included in this repository, which takes all of the boxscore transcriptions
from a source, and processes the data into CSV files, which are placed into
a corresponding directory under processed/.  This process does not add or interpolate
any new information, but simply extracts and interprets the information found
in the original transcriptions.  The resulting CSV files are then suitable
for further editorial processing.

The objective of these files is to render the content of those sources in a way that
is as faithful as possible to the originals.  It is important to recognise that
THE GUIDES AND OTHER SOURCES CONTAIN ERRORS AND INACCURACIES.  This collection of
files does not attempt to identify and/or propose corrections to those errors.
The scope of this collection is to document the contents of sources in a standard
and systematic way, and therefore provide the inputs required to editors who wish to
produce cleaned, corrected, or improved accounts of the performance data for these
leagues.  The files in this collection therefore provide one essential component
in the chain of evidence required to produce such improved data.

## The file format

The structure of the input files is intended to facilitate transcription from
newspaper boxscores.  It imitates, to the extent possible, the structure of
newspaper boxscores, with the intention that a human can read the transcribed
file and compare it visually with the source.

The best way to understand the file format rules is to look at existing files, as
it is intended that transcription can be done without having to read long
documentation first.

### Preliminary: Type what you see

In preparing files in this format, the key principle is to type what is in the
source.  In doing so, you will inevitably find information which is inconsistent:
player names will be spelled in various ways, statistical totals will not balance,
and so on.  Likewise, there are inferences that can be made from the data in a game.
A common example is if a team uses two pitchers Smith and Jones in a nine-inning game,
a boxscore may list Smith with 8 innings pitched and not mention Jones.  Obviously,
it follows logically that Jones should be credited with one inning pitched.
You should *not* transcribe Jones with one IP in such a case, *unless* the boxscore
explicitly lists him as such.

Keeping a clear distinction between the data-capture and editing stages of
research has many benefits.
It is beyond the scope of this note to list them all.
In short, transcribing sources exactly - warts and all - helps to make every
data value in your dataset traceable back to a source, and therefore makes
the research process fully reproducible.

### Organisation

We collect games by source; one source may contain games from many leagues (especially if
a paper had very extensive baseball coverage), and conversely a league may have games
recorded in many sources.  Organising games by source makes it easier to track which
sources have and have not been consulted and transcribed.

For sources with a large number of games, we usually use one text file per day.
For sources with thinner coverage, it is sometimes convenient to use one file
per week, usually dated with the Monday of that week.

Within a file, games are separated by a line consisting of three dashes, `---`, and nothing
else.

### Structure

The structure of a game transcription is mainly line-oriented; each line in the text
file corresponds to one type of information.
Lines generally are of the form `label: value`.

### Game data

The game-level data fields `date:`, `number:`, `away:`, and `home:` are
required, and have their standard meanings.  The field `source:` is not required,
but encouraged to be included - although the overall source is implied by the file
organisation, this can be used to mark, for example, the edition of the newspaper or
page number.

#### League

The `league:` field indicates the league in which the game was played.
This is omitted if the game was not part of a league regular season or playoff.

#### Status

The `status:` record provides information about the progress of the game.  It is adapted
from the `status` attribute of games used by MLBAM.  A `status` record has the format
`type` or `type, reason`.  Valid values for `type` are:
* `final`: the game completed normally at the end of the scheduled number of innings
  (or extra innings if required).  This is the default; a `status` record does not need
  to be included for this, the most common case.
* `completed early`: an official game completed earlier than the scheduled number of
  innings.  The `reason` attribute should explain why, if known
* `abandoned`: a game was started but terminated before it was considered an official game
  (usually less than 5 innings).  The `reason` attribute should explain why, if known.
* `postponed`: a game was scheduled but did not start.  The `reason` attribute should explain
  why, if known.

Common values for the `reason` field are weather-related such as `rain` or `darkness`.
More detailed reasons can be given where appropriate, such as `by agreement so Springfield could catch train`.


### Lineups

The lineup for a team is started by a line listing the team name (matching either the `away:` or
`home:` record) as the label, and then a list of column headers matching the column headers in the boxscore.
The most common list of headers is `ab r h po a e`, but some sources will have fewer (or more).

Within a team, each line corresponds to one player.  The general format is `name @ pos: stats`.
Where a player's initials or first name are given, `name` should be `surname, firstname`.
The `stats` are separated by whitespace; they do not need to align visually with the column headers
(but inputters are free to do so if they find it helpful).

In the event a statistical value is missing or completely illegible, use an `x` for the value to indicate
missing data.

Where substitutions are indicated (by asterisks, daggers, and the like), the indicator is placed before
the substituting player's name just as in the boxscore, e.g., `*Smith @ ph`.
Acceptable values (so far) for indicators are `*`, `+`, `^`, `&`, and `$`.

Optionally, lineups can be marked up to indicate batting order position.  For example, some boxscores
list the starting nine first, and then substitutes below, while others list the substitutes immediately
following the players they replaced.  Notation for this is placed at the start of the line.
So if Smith pinch-hit for Jones, who was in the 8th spot in the order, you could write
`(~8.1)Jones @ c:` and `(~8.2)Smith @ ph:`.
This again is especially useful if Smith shows up a few lines later in the player list.
Remember, to indicate this, transcribe the players in the order they appear on the page, and use this
markup to connect the batting order slots.

A team's lineup ends with a line with label `TOTALS`.  In the event a boxscore does not provide a totals
line, the `TOTALS` line is still expected; fill the line with `x` for all stats categories to indicate
the data are missing.

### Linescores

Runs by inning are indicated in `line:` records.  These have the format `line: team: scorebyinnings - total`.
The score by innings is whitespace-delimited; if you find it useful to group innings by putting an extra
space e.g. after each group of three innings (as is sometimes done) this is fine.
If a team does not bat in an inning, indicate this with `x`.

Where scores by innings are reported, list them in the order they appear in the source, noting that
in historical sources it is not always the case that the home team (or the last-batting team) is listed last.


### Credits

Most boxscores list statistical credits beside the core stats in text format.  We capture these by
providing a record with one line per type of statistical credit.

The general format for these is `credit: Player1 #count; Player2 #count`.  For example,
`B_2B: Jones #2; Smith` credits Jones with two doubles as a batter, and Smith with one double.
Credits are separated with semicolons.  The `#` notation indicates counts; if the source does not
list a count, it is assumed to be one (and the `#` should not be used; only use `#1` if the source
has an explicit count of one printed).

If a player is listed with an initial, the initial goes before the surname in the credits.
That is, in the player list, you would write `Smith, J. @ cf`, but in the credits you write
`B_2B: J. Smith`.

The most common categories for credits are:
* Batting: `B_LOB`, `B_ROE`, `B_2B`, `B_3B`, `B_HR`, `B_HP`, `B_SH`, `B_SB`
* Pitching: `P_IP`, `P_R`, `P_H`, `P_BB`, `P_SO`, `P_WP`, `P_BK`
* Fielding: `F_PB`, `F_DP`, `F_TP`
* Game: `T`, `U`

### Credits: Double and triple plays

For double and triple plays, separate the names of players in the same play with commas, and
separate different plays (or combinations of players) by semicolons.  So for example,
`F_DP: Tinker, Evers, Chance #2; Russell, Lopes, Garvey` means 2 double plays for Tinker to
Evers to Chance, and one for Russell to Lopes to Garvey.

### Credits: Time of game

The time-of-game credit `T` has the format `H:MM`, e.g. `T: 1:55`.

### Credits: Umpires

Umpires are credited as a semicolon-separated list.  Umpires are the one exception to the rule
about ordering initials; umpire initials should *follow* the surname, e.g., `U: Smith, F.; Davis`.
