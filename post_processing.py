import numpy as np
import pandas as pd


def post_process_courses(df: pd.DataFrame) -> pd.DataFrame:
    df_ = df.rename(
        columns={
            'Kurskod': 'Course code',
            'Kursnamn': 'Course name',
            'Omfattning': 'hp',
            'Utbildningsnivå': 'Level',
        }
    ).drop(columns=['Ethical approach'])
    df_.hp = df_.hp.str.replace('fup', '').str.replace('hp', '').astype(float)
    df_['School'] = [x[: np.where([c.isnumeric() for c in x])[0][0]] for x in df_['Course code']]
    df_['Course web'] = 'https://www.kth.se/social/course/' + df_['Course code']

    # remove examensarbeten
    df_ = df_[~df_['Course name'].str.lower().str.contains('examensarbete')]

    return df_


def post_process_course_offerings(df: pd.DataFrame) -> pd.DataFrame:
    df_ = df.rename(columns={'For course offering': 'Year'})
    # df_[['Term', 'Year']] = df_.Year.str.extract(r'(Autumn|Spring)\s(\d{4})\s')
    # df_.Year = df_.Year.astype(int)
    # df_.loc[df_.Term == 'Spring', 'Year'] -= 1
    # df_['Year'] = df_['Year'].astype(str) + '/' + (df_['Year'] + 1).astype(str)

    df_.loc[df_.Periods.apply(lambda x: isinstance(x, list)), 'Periods'] = df_.loc[
        df_.Periods.apply(lambda x: isinstance(x, list)), 'Periods'
    ].str.join(', ')

    signs_to_remove = ["'", ' hp', ' fup', 'Autumn', 'Spring', ':']
    for sign in signs_to_remove:
        df_.Periods = df_.Periods.str.replace(sign, '', regex=False)

    for period in ['P1', 'P2', 'P3', 'P4']:
        df_[period] = df_.Periods.str.extract(fr'(?<=(?:{period}\s\())(.+?)(?=\))').astype(float)

    df_ = df_.drop(columns='Periods')
    return df_
