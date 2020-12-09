import click

from . import extract
from . import xform

# from . import parse
# from . import repo
# from . import totoml


@click.group("boxscore")
def boxscore():
    """Process newspaper-style boxscores."""
    pass


# @boxscore.command("parse")
# @click.argument("source")
# @click.option("--warn-duplicates", "-D", default=False,
#               help=("only warn on duplicate name in game "
#                     "(default is terminate)"))
# @click.option("--warn-marked", "-M", default=False,
#               help="warn on marked dubious names (default is ignore)")
# def do_parse(source, warn_duplicates, warn_marked):
#     """Parse boxscores to CSV."""
#     parse.main(source, warn_duplicates, warn_marked)


# @boxscore.command("store")
# @click.argument("source")
# @click.argument("filenames", nargs=-1)
# @click.option("--overwrite/--no-overwrite", default=False)
# def do_store(source, filenames, overwrite):
#     """Store files to repository."""
#     repo.do_store(source, filenames, overwrite)


# @boxscore.command("edit")
# @click.argument("source")
# def do_edit(source):
#     """Edit source files."""
#     repo.do_edit(source)


# @boxscore.command("add")
# @click.argument("source")
# def do_add(source):
#     """Add source files to git repository."""
#     repo.do_add(source)


@boxscore.command("extract")
@click.argument("source")
def do_extract(source):
    """Extract data from source files and index."""
    extract.main(source)


@boxscore.command("xform")
@click.argument("year", type=int)
def do_xform(year: int):
    """Transform data to standard package."""
    xform.main(year)


# @boxscore.command("toml")
# @click.argument("source")
# def do_toml(source):
#     """Translate files to TOML."""
#     totoml.main(source)
