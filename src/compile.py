import sys
import os
import os.path
import collections

import numpy as np
import pandas as pd

def compute_stints(playing):
    playing.sort_values(['person.key', 'S_FIRST'], inplace=True)
    playing['S_STINT'] = playing.groupby('person.key').cumcount()+1
    playing['nstint'] = playing.groupby('person.key')['S_STINT'].transform(max)
    playing.loc[playing['nstint']==1, 'S_STINT'] = 0
    del playing['nstint']
    return playing

def totalize(playing):
    playing = playing[playing['S_STINT']!=0]
    playing = playing[['person.key', 'S_FIRST', 'S_LAST'] +
                      [c for c in playing.columns if
                       c.startswith('B_') or c.startswith('P_') or
                       c.startswith('F_')]]
    aggs = collections.OrderedDict()
    aggs['S_FIRST'] = 'min'
    aggs['S_LAST'] = 'max'
    for col in playing:
        if col.startswith('B_') or col.startswith('P_') or \
           col.startswith('F_'):
            aggs[col] = 'sum'
    playing = playing.groupby('person.key').aggregate(aggs)
    playing.reset_index(inplace=True)
    playing['entry.name'] = "#TOTAL"
    playing['S_STINT'] = 'T'
    return playing

def main():
    year, league = sys.argv[1], sys.argv[2]
    leaguefile = league.replace(" ", "").replace("-", "")
    gameident = pd.read_csv(os.path.expanduser("~/git/identlink/games/%s/%s%s.csv" % (year, year, leaguefile)),
                            dtype=str)
    sources = gameident['source'].str.split("/").str[1:].str.join("/").unique()

    dflist = [pd.read_csv(os.path.expanduser("~/git/boxscores/processed/%s/playing.csv" % s))
              for s in sources]
    for (df, source) in zip(dflist, sources):
        df['source'] = "boxscores/"+source
    playing = pd.concat(dflist, ignore_index=True)
    playing = playing[playing['name.last']!="TOTALS"]
    playing.rename(inplace=True,
                   columns={'name.last': 'person.name.last',
                            'name.first': 'person.name.given',
                            'club.name': 'entry.name'})
    
    peopleident = pd.read_csv(os.path.expanduser("~/git/identlink/leagues/%s/%s%s.csv" % (year, year, leaguefile)),
                              dtype=str)
    
    peopleident['person.name.given'] = peopleident['person.name.given'].fillna("")
    playing['person.name.given'] = playing['person.name.given'].fillna("")
    playing = pd.merge(playing,
                       peopleident[['source',
                                    'person.name.last', 'person.name.given',
                                    'entry.name', 'ident']], how='left',
                       on=['source',
                           'person.name.last', 'person.name.given',
                           'entry.name'])
    # TODO: Check for unmatched records
    playing.rename(inplace=True,
                   columns={'ident': 'person.key'})

    playing.rename(inplace=True,
                   columns={'game.key': 'game.ref'})
    playing = pd.merge(playing,
                       gameident[['ident', 'game.ref']],
                       how='left',
                       on='game.ref')
    playing.rename(inplace=True,
                   columns={'ident': 'game.key'})

    playing['source'] = playing['source'].str.split("/").str[-1]
    playing['B_G'] = 1
    for pos in ['P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF']:
        playing['F_%s_G' % pos] = playing['pos'].str.split('-').apply(lambda x: pos.lower() in x).astype(int)
    playing['F_OF_G'] = (playing['F_LF_G'] + playing['F_CF_G'] +
                         playing['F_RF_G'] >= 1).astype(int)
    playing = playing[['source', 'entry.name', 'person.key', 'game.key',
                       'game.date',
                       'B_G',
                       'F_P_G', 'F_C_G', 'F_1B_G', 'F_2B_G', 'F_3B_G', 'F_SS_G',
                       'F_OF_G', 'F_LF_G', 'F_CF_G', 'F_RF_G',
                       'B_AB', 'B_R', 'B_H', 'B_2B', 'B_3B', 'B_HR', 'B_SB']]

    playing = pd.melt(playing,
                      id_vars=['person.key', 'game.key', 'entry.name',
                               'source'])
    playing.set_index(['person.key', 'game.key', 'entry.name',
                       'variable', 'source'], inplace=True)
    playing = playing.unstack(level=-1)
    playing.columns = playing.columns.droplevel(0)

    playing['lb'] = playing.min(axis=1)
    playing['ub'] = playing.max(axis=1)

    playing.reset_index(inplace=True)
    playing.set_index(['person.key', 'game.key', 'entry.name', 'variable'],
                      inplace=True)
    playing = playing[['ub']]
    playing = playing.unstack(level=-1)
    playing.columns = playing.columns.droplevel(0)

    playing.reset_index(inplace=True)

    aggs = collections.OrderedDict()
    aggs['game.date'] = ['min', 'max']
    for col in ['B_G', 'B_AB', 'B_R', 'B_H', 'B_2B', 'B_3B', 'B_HR', 'B_SB']:
        aggs[col] = 'sum'
    for pos in ['P', 'C', '1B', '2B', '3B', 'SS', 'OF', 'LF', 'CF', 'RF']:
        aggs['F_%s_G' % pos] = 'sum'
    playing = playing.groupby(['person.key', 'entry.name']).aggregate(aggs)
    playing.columns = ['S_FIRST', 'S_LAST',
                       'B_G', 'B_AB', 'B_R', 'B_H',
                       'B_2B', 'B_3B', 'B_HR', 'B_SB',
                       'F_P_G', 'F_C_G', 'F_1B_G', 'F_2B_G', 'F_3B_G',
                       'F_SS_G', 'F_OF_G', 'F_LF_G', 'F_CF_G', 'F_RF_G']

    playing.reset_index(inplace=True)
    playing = compute_stints(playing)
    playing = pd.concat([playing, totalize(playing)], ignore_index=True)
    playing.sort_values(['person.key', 'S_STINT'], inplace=True)
    
    playing.insert(0, 'league.year', year)
    playing.insert(1, 'league.name', league)
    playing.rename(inplace=True, columns={'person.key': 'ident'})
    playing['phase.name'] = 'regular'

    yearfile = pd.read_csv(os.path.expanduser("~/git/identlink/seasons/%s.csv" %
                                              year),
                            dtype=str)
    yearfile = yearfile[['league.key', 'league.name.full']].copy()
    yearfile.columns = ['namespace', 'league.name']
    playing = pd.merge(playing, yearfile, how='left', on='league.name')
    playing['ident'] = playing['namespace'] + ':' + playing['ident']
    del playing['namespace']
    
    try:
        os.makedirs("compiled/%s/%s%s" % (year, year, leaguefile))
    except os.error:
        pass

    playing = playing[['league.year', 'league.name', 'ident',
                       'phase.name', 'entry.name',
                       'S_STINT', 'S_FIRST', 'S_LAST',
                       'B_G', 'B_AB', 'B_R', 'B_H', 'B_2B', 'B_3B', 'B_HR',
                       'B_SB',
                       'F_P_G', 'F_C_G', 'F_1B_G', 'F_2B_G', 'F_3B_G',
                       'F_SS_G', 'F_OF_G', 'F_LF_G', 'F_CF_G', 'F_RF_G']]
    
    playing.to_csv("compiled/%s/%s%s/playing_individual.csv" %
                   (year, year, leaguefile),
                   float_format='%d', index=False)



if __name__ == '__main__':
    main()
