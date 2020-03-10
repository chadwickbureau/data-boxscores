import click

from . import parse
from . import repo
from . import tojson
from . import totoml


@click.group()
def cli():
    pass


@cli.command("parse")
@click.argument("source")
@click.option("--warn-duplicates", "-D", default=False,
              help=("only warn on duplicate name in game "
                    "(default is terminate)"))
@click.option("--warn-marked", "-M", default=False,
              help="warn on marked dubious names (default is ignore)")
def do_parse(source, warn_duplicates, warn_marked):
    parse.main(source, warn_duplicates, warn_marked)


@cli.command("store")
@click.argument("source")
@click.argument("filenames", nargs=-1)
@click.option("--overwrite/--no-overwrite", default=False)
def do_store(source, filenames, overwrite):
    repo.do_store(source, filenames, overwrite)


@cli.command("edit")
@click.argument("source")
def do_edit(source):
    repo.do_edit(source)


@cli.command("add")
@click.argument("source")
def do_add(source):
    repo.do_add(source)


@cli.command("json")
@click.argument("source")
def do_json(source):
    tojson.main(source)


@cli.command("toml")
@click.argument("source")
def do_toml(source):
    totoml.main(source)
