import sys
import functools

import pandas as pd


def assign_games(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.assign(
            **{
                'B_G': 1,
                'player.positions': lambda x: x['player.positions'].fillna("").str.split("-")
            },
            **{
                f'F_{pos}_G'.upper(): functools.partial(
                    lambda x, p: x['player.positions'].apply(lambda y: 1 if p in y else 0),
                    p=pos
                )
                for pos in ['p', 'c', '1b', '2b', '3b', 'ss',
                            'lf', 'cf', 'rf']
            },
            **{
                'B_G_PH': lambda x: x['player.positions'].apply(lambda y: 1 if "ph" in y else 0),
                'B_G_PR': lambda x: x['player.positions'].apply(lambda y: 1 if "pr" in y else 0),
                'F_OF_G': lambda x: (x['F_LF_G'] + x['F_CF_G'] + x['F_RF_G']).clip(0, 1)
            }
        )
    )


def summarise_players(year: int):
    df = (
        pd.read_csv(f"data/normal/{year}-players.csv")
        .pipe(assign_games)
        # A crude way to account for multiple sources for the same game
        .groupby(['game.date', 'game.number', 'team.league', 'team.name', 'player.name'])
        [['B_G', 'F_P_G', 'F_C_G', 'F_1B_G', 'F_2B_G', 'F_3B_G',
          'F_SS_G', 'F_OF_G', 'F_LF_G', 'F_CF_G', 'F_RF_G',
          'B_G_PH', 'B_G_PR']].max()
        .reset_index()
        .groupby(['team.league', 'team.name', 'player.name'])
        .agg(
            **{
                'S_FIRST': pd.NamedAgg(column='game.date', aggfunc='min'),
                'S_LAST': pd.NamedAgg(column='game.date', aggfunc='max'),
                'B_G': pd.NamedAgg(column='B_G', aggfunc='sum'),
            },
            **{
                f'F_{pos}_G': pd.NamedAgg(column=f'F_{pos}_G', aggfunc='sum')
                for pos in ['P', 'C', '1B', '2B', '3B', 'SS',
                            'OF', 'LF', 'CF', 'RF']
            },
            **{
                f'B_G_{pos}': pd.NamedAgg(column=f'B_G_{pos}', aggfunc='sum')
                for pos in ['PH', 'PR']
            }
        )
        .reset_index()
    )
    df.to_csv(f"data/summary/{year}-players.csv",
              index=False, float_format="%d")


def main(year: int):
    summarise_players(year)

if __name__ == '__main__':
    main(int(sys.argv[1]))
