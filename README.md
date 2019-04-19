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
documentation first.  The source code of the parser can also be used to
understand what the rules of the format are.

Here we also provide some selected documentation on some finer or less-common points.

### Game metadata

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
