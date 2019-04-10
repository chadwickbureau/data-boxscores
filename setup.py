from setuptools import setup, find_packages

setup(name='boxscore',
      version='0.1',
      packages=find_packages(),
      install_package_data=True,
      python_requires=">=3.7",
      install_requires=[
          'click', 'colorama', 'pandas', 'tabulate'
      ],
      entry_points="""
         [console_scripts]
         boxscore=boxscore.main:cli
      """
      )
