try:
    import pathlib
except ImportError:
    import pathlib2 as pathlib
try:
    import configparser
except ImportError:
    import ConfigParser as configparser


config = configparser.ConfigParser()
config.read([str(pathlib.Path("~/.hgamerc").expanduser())])
data_path = pathlib.Path(config.get("boxscores", "data_path",
                                    vars={"data_path": "data/boxscores"})).expanduser()
edit_command = config.get("boxscores", "edit_command")


