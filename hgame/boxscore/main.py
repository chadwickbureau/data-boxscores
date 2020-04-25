import click

from . import parse
from . import repo
from . import tojson
from . import totoml
from . import index


@click.group("boxscore")
def boxscore():
    """Parse newspaper-style boxscores."""
    pass


@boxscore.command("parse")
@click.argument("source")
@click.option("--warn-duplicates", "-D", default=False,
              help=("only warn on duplicate name in game "
                    "(default is terminate)"))
@click.option("--warn-marked", "-M", default=False,
              help="warn on marked dubious names (default is ignore)")
def do_parse(source, warn_duplicates, warn_marked):
    """Parse boxscores to CSV."""
    parse.main(source, warn_duplicates, warn_marked)


@boxscore.command("store")
@click.argument("source")
@click.argument("filenames", nargs=-1)
@click.option("--overwrite/--no-overwrite", default=False)
def do_store(source, filenames, overwrite):
    """Store files to repository."""
    repo.do_store(source, filenames, overwrite)


@boxscore.command("edit")
@click.argument("source")
def do_edit(source):
    """Edit source files."""
    repo.do_edit(source)


@boxscore.command("add")
@click.argument("source")
def do_add(source):
    """Add source files to git repository."""
    repo.do_add(source)


@boxscore.command("json")
@click.argument("source")
def do_json(source):
    """Translate files to JSON."""
    tojson.main(source)


@boxscore.command("toml")
@click.argument("source")
def do_toml(source):
    """Translate files to TOML."""
    totoml.main(source)


@boxscore.command("index")
@click.argument("year", type=int)
def do_index(year: int):
    """Index player names from TOML files."""
    index.main(year)
