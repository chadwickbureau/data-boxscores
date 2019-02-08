import sys
import shutil
import subprocess
try:
    import pathlib
except ImportError:
    import pathlib2 as pathlib

import colorama as clr

from . import config

def do_store(source, filename):
    try:
        year, paper = source.split("-")
    except ValueError:
        print(clr.Fore.RED + ("Invalid source name '%s'" % source) + clr.Fore.RESET)
        sys.exit(1)

    path = config.data_path/"transcript"/year/source
    path.mkdir(exist_ok=True, parents=True)

    if (path/pathlib.Path(filename).name).exists():
        print(clr.Fore.RED + ("Target file already exists") + clr.Fore.RESET)
        sys.exit(1)
    shutil.copy(filename, str(path))
    
def do_edit(source):
    try:
        year, paper = source.split("-")
    except ValueError:
        print(clr.Fore.RED + ("Invalid source name '%s'" % source) + clr.Fore.RESET)
        sys.exit(1)

    path = config.data_path/"transcript"/year/source
    subprocess.call(config.edit_command + " " + str(path) + "/*.txt", shell=True)
    
def do_add(source):
    try:
        year, paper = source.split("-")
    except ValueError:
        print(clr.Fore.RED + ("Invalid source name '%s'" % source) + clr.Fore.RESET)
        sys.exit(1)

    subprocess.call("cd %s && git add transcript/%s/%s/*.txt" %
                    (config.data_path, year, source),
                    shell=True)
    subprocess.call("cd %s && git add processed/%s/%s/*.csv" %
                    (config.data_path, year, source),
                    shell=True)
    subprocess.call("cd %s && git status" % config.data_path, shell=True)

    
