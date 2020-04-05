import setuptools


setuptools.setup(
    name='hgame-boxscore',
    description='Parser for newspaper-style boxscores',
    version='0.1',
    packages=['hgame.boxscore'],
    install_package_data=True,
    python_requires=">=3.7",
    install_requires=[
        'hgame-cmdline',
        'colorama', 'pandas', 'tabulate', 'toml', 'marshmallow'
    ],
    entry_points="""
        [hgame.cli_plugins]
        boxscore=hgame.boxscore.main:boxscore
    """,
)
