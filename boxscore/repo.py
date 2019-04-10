import sys
import shutil
import subprocess
import pathlib

import click

from . import config

def do_store(source, filenames, overwrite):
    try:
        year, paper = source.split("-")
    except ValueError:
        click.secho("Invalid source name '%s'" % source, fg='red')
        sys.exit(1)

    path = config.data_path/"transcript"/year/source
    path.mkdir(exist_ok=True, parents=True)

    for fn in filenames:
        target = path/pathlib.Path(fn).name
        if target.exists() and not overwrite:
            click.secho("Target file %s already exists" % target, fg='red')
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

    
