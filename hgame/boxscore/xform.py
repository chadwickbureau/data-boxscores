"""Transform data into aggregated packages."""
import pathlib

import pandas as pd
import tabulate


def aggregate_players(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.assign(**{
            'last': lambda x: (
                x['gloss.name.last'].fillna(x['person.name.last']).fillna("")
            ),
            'given': lambda x: (
                x['gloss.name.first'].fillna(x['person.name.first']).fillna("")
            ),
            'date': lambda x: x['key'].str[:8],
            'pos': lambda x: x['pos'].str.split("-"),
            'F_P_G': lambda x: x['pos'].apply(lambda y: 1 if "p" in y else 0),
            'F_C_G': lambda x: x['pos'].apply(lambda y: 1 if "c" in y else 0),
            'F_1B_G': lambda x: x['pos'].apply(lambda y: 1 if "1b" in y else 0),
            'F_2B_G': lambda x: x['pos'].apply(lambda y: 1 if "2b" in y else 0),
            'F_3B_G': lambda x: x['pos'].apply(lambda y: 1 if "3b" in y else 0),
            'F_SS_G': lambda x: x['pos'].apply(lambda y: 1 if "ss" in y else 0),
            'F_LF_G': lambda x: x['pos'].apply(lambda y: 1 if "lf" in y else 0),
            'F_CF_G': lambda x: x['pos'].apply(lambda y: 1 if "cf" in y else 0),
            'F_RF_G': lambda x: x['pos'].apply(lambda y: 1 if "rf" in y else 0),
            'B_G_PH': lambda x: x['pos'].apply(lambda y: 1 if "ph" in y else 0),
            'B_G_PR': lambda x: x['pos'].apply(lambda y: 1 if "pr" in y else 0)
        })
        .groupby(['team.league', 'team.name',
                  'last', 'given', 'date', 'key'])
        .agg(
            F_P_G=pd.NamedAgg(column='F_P_G', aggfunc=max),
            F_C_G=pd.NamedAgg(column='F_C_G', aggfunc=max),
            F_1B_G=pd.NamedAgg(column='F_1B_G', aggfunc=max),
            F_2B_G=pd.NamedAgg(column='F_2B_G', aggfunc=max),
            F_3B_G=pd.NamedAgg(column='F_3B_G', aggfunc=max),
            F_SS_G=pd.NamedAgg(column='F_SS_G', aggfunc=max),
            F_LF_G=pd.NamedAgg(column='F_LF_G', aggfunc=max),
            F_CF_G=pd.NamedAgg(column='F_CF_G', aggfunc=max),
            F_RF_G=pd.NamedAgg(column='F_RF_G', aggfunc=max),
            B_G_PH=pd.NamedAgg(column='B_G_PH', aggfunc=max),
            B_G_PR=pd.NamedAgg(column='B_G_PR', aggfunc=max)
        )
        .reset_index()
        .assign(B_G=1)
        .groupby(['team.league', 'team.name', 'last', 'given'])
        .agg(
            S_FIRST=pd.NamedAgg(column='date', aggfunc=min),
            S_LAST=pd.NamedAgg(column='date', aggfunc=max),
            B_G=pd.NamedAgg(column='B_G', aggfunc=sum),
            F_P_G=pd.NamedAgg(column='F_P_G', aggfunc=sum),
            F_C_G=pd.NamedAgg(column='F_C_G', aggfunc=sum),
            F_1B_G=pd.NamedAgg(column='F_1B_G', aggfunc=sum),
            F_2B_G=pd.NamedAgg(column='F_2B_G', aggfunc=sum),
            F_3B_G=pd.NamedAgg(column='F_3B_G', aggfunc=sum),
            F_SS_G=pd.NamedAgg(column='F_SS_G', aggfunc=sum),
            F_LF_G=pd.NamedAgg(column='F_LF_G', aggfunc=sum),
            F_CF_G=pd.NamedAgg(column='F_CF_G', aggfunc=sum),
            F_RF_G=pd.NamedAgg(column='F_RF_G', aggfunc=sum),
            B_G_PH=pd.NamedAgg(column='B_G_PH', aggfunc=sum),
            B_G_PR=pd.NamedAgg(column='B_G_PR', aggfunc=sum)
        )
        .reset_index()
        .sort_values(['team.league', 'team.name', 'last', 'given'],
                     key=lambda x: x.str.lower())
    )


def generate_report_playing(df: pd.DataFrame, year: int) -> pd.DataFrame:
    outpath = pathlib.Path(f"data/report/{year}")
    outpath.mkdir(exist_ok=True, parents=True)
    df = (
        df.assign(**{
            'player': lambda x: x['last'] + ", " + x['given']
        })
        .rename(columns={
            'team.league': 'league',
            'team.name': 'team',
            'S_FIRST': 'start',
            'S_LAST': 'end',
            'B_G': 'G',
            'F_P_G': 'P',
            'F_C_G': 'C',
            'F_1B_G': '1B',
            'F_2B_G': '2B',
            'F_3B_G': '3B',
            'F_SS_G': 'SS',
            'F_LF_G': 'LF',
            'F_CF_G': 'CF',
            'F_RF_G': 'RF',
            'B_G_PH': 'PH',
            'B_G_PR': 'PR'
        })
        .replace({0: None})
        .reindex(columns=['league', 'team', 'player', 'start', 'end', 'G',
                          'P', 'C', '1B', '2B', 'SS', '3B',
                          'LF', 'CF', 'RF', 'PH', 'PR'])
    )
    with open(outpath/"playing_byclub.txt", "w") as f:
        for ((_league, _team), data) in df.groupby(['league', 'team']):
            print(
                tabulate.tabulate(
                    data,
                    showindex=False, headers='keys'
                ),
                file=f
            )
            print(file=f)
    with open(outpath/"playing_byname.txt", "w") as f:
        print(
            tabulate.tabulate(
                df.sort_values(['player', 'start'],
                               key=lambda x: x.str.lower()),
                showindex=False, headers='keys'
            ),
            file=f
        )
    return df


def main(year: int):
    inpath = pathlib.Path(f"data/index/{year}")
    outpath = pathlib.Path(f"data/processed/{year}")
    outpath.mkdir(exist_ok=True, parents=True)
    (
        pd.concat(
            [pd.read_csv(fn).pipe(aggregate_players)
             for fn in inpath.glob("*/players.csv")],
            ignore_index=True, sort=False
        )
        .sort_values(['team.league', 'team.name', 'last', 'given'])
        .pipe(generate_report_playing, year)
        .to_csv(outpath/"playing.csv", index=False, float_format='%d')
    )
