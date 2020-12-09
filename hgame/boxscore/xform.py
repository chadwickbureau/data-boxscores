"""Transform data into aggregated packages."""
import pathlib

import pandas as pd


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
            'F_P_G': lambda x: (x['pos'] == "p").astype(int),
            'F_C_G': lambda x: (x['pos'] == "c").astype(int),
            'F_1B_G': lambda x: (x['pos'] == "1b").astype(int),
            'F_2B_G': lambda x: (x['pos'] == "2b").astype(int),
            'F_3B_G': lambda x: (x['pos'] == "3b").astype(int),
            'F_SS_G': lambda x: (x['pos'] == "ss").astype(int),
            'F_LF_G': lambda x: (x['pos'] == "lf").astype(int),
            'F_CF_G': lambda x: (x['pos'] == "cf").astype(int),
            'F_RF_G': lambda x: (x['pos'] == "rf").astype(int)
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
        )
        .reset_index()
    )


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
        .to_csv(outpath/"playing.csv", index=False, float_format='%d')
    )
