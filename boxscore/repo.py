import sys
import shutil
import subprocess
try:
    import pathlib
except ImportError:
    import pathlib2 as pathlib

import click

from . import config

def do_store(source, filenames):
    try:
        year, paper = source.split("-")
    except ValueError:
        click.secho("Invalid source name '%s'" % source, fg='red')
        sys.exit(1)

    path = config.data_path/"transcript"/year/source
    path.mkdir(exist_ok=True, parents=True)

    for fn in filenames:
        if (path/pathlib.Path(fn).name).exists():
            click.secho("Target file already exists", fg='red')
            sys.exit(1)
        shutil.copy(fn, str(path))
    
def do_edit(source):
    try:
        year, paper = source.split("-")
    except ValueError:
        click.secho("Invalid source name '%s'" % source, fg='red')
        sys.exit(1)

    path = config.data_path/"transcript"/year/source
    subprocess.call(config.edit_command + " " + str(path) + "/*.txt", shell=True)
    
def do_add(source):
    try:
        year, paper = source.split("-")
    except ValueError:
        click.secho("Invalid source name '%s'" % source, fg='red')
        sys.exit(1)

    subprocess.call("cd %s && git add transcript/%s/%s/*.txt" %
                    (config.data_path, year, source),
                    shell=True)
    subprocess.call("cd %s && git add processed/%s/%s/*.csv" %
                    (config.data_path, year, source),
                    shell=True)
    subprocess.call("cd %s && git status" % config.data_path, shell=True)

    
