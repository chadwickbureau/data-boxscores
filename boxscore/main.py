import click

from . import parse

@click.group()
def cli():
    pass

@cli.command("parse")
@click.argument("source")
@click.option("--warn-duplicates", "-D", default=False,
              help="only warn on duplicate name in game (default is terminate)")
@click.option("--warn-marked", "-M", default=False,
              help="warn on marked dubious names (default is ignore)")
def do_parse(source, warn_duplicates, warn_marked):
    parse.main(source, warn_duplicates, warn_marked)
