from setuptools import setup

setup(name='hgame-boxscore',
      version='0.1',
      packages=['hgame.boxscore'],
      install_package_data=True,
      python_requires=">=3.7",
      install_requires=[
          'click', 'colorama', 'pandas', 'tabulate'
      ],
      entry_points="""
         [console_scripts]
         hgame-boxscore=hgame.boxscore.main:cli
      """
      )
