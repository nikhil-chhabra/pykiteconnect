from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
import config
from jugaad_trader import Zerodha
import pyotp
from pymongo import MongoClient

def login_kite():
    username = config.username
    password = config.password
    totp = pyotp.TOTP(config.totp_code)
    kite = Zerodha(user_id=username, password=password, twofa=totp.now())
    kite.login()
    return kite


def get_candle_fig(instrument_code, start, end, interval):
    kite=login_kite()
    df_historical = pd.DataFrame(kite.historical_data(instrument_code, start, end, interval))
    if len(df_historical) > 0:
        fig = go.Figure(data=[go.Candlestick(x=df_historical['date'],
                        open=df_historical['open'],
                        high=df_historical['high'],
                        low=df_historical['low'],
                        close=df_historical['close'])])
        return (fig)
    else:
        return (None)


def get_candle(instrument_code, start, end, interval):
    kite=login_kite()
    df_historical = pd.DataFrame(kite.historical_data(instrument_code, start, end, interval))
    if len(df_historical) > 0:
        return (df_historical)
    else:
        return (pd.DataFrame())


def get_candle_signal(instrument_code, sample_size):
    try:
        df_summary = pd.DataFrame()
        for i in range(sample_size + 1):
            start = ((datetime.now() + timedelta(days=-i)).strftime("%Y-%m-%d")) + " 09:00:00"
            end = ((datetime.now() + timedelta(days=-i)).strftime("%Y-%m-%d")) + " 16:00:00"
            interval = "5minute"
            df_historical = get_candle(instrument_code, start, end, interval)

            if len(df_historical) > 0:
                df_historical['change'] = df_historical['close'] - df_historical['open']
                df_historical['candle_type'] = df_historical['change'].apply(lambda x: 'green' if x > 0 else 'red')
                try:
                    candle_ratio = ((df_historical['candle_type'].value_counts()['green']) / (df_historical['candle_type'].count()))
                except:
                    candle_ratio = 0
                df_summary_dict = {'day': end,
                                   'candle_ratio': candle_ratio}
                df_temp = pd.DataFrame([df_summary_dict])
                df_summary = pd.concat([df_summary, df_temp])
        return ((sum(df_summary['candle_ratio']) * 2) / sample_size)
    except:
        return 0


def get_candle_signal_2(instrument_code, sample_size):
    try:
        df_summary = pd.DataFrame()
        for i in range(sample_size + 1):
            start = ((datetime.now() + timedelta(days=-i)).strftime("%Y-%m-%d")) + " 09:00:00"
            end = ((datetime.now() + timedelta(days=-i)).strftime("%Y-%m-%d")) + " 16:00:00"
            interval = "5minute"
            df_historical = get_candle(instrument_code, start, end, interval)

            if len(df_historical) > 0:
                df_historical['change'] = df_historical['close'] - df_historical['open']
                df_historical['candle_type'] = df_historical['change'].apply(lambda x: 'green' if x > 0 else 'red')
                try:
                    candle_ratio = ((df_historical['candle_type'].value_counts()['green']) / (df_historical['candle_type'].count()))
                except:
                    candle_ratio = 0
                df_summary_dict = {'day': end,
                                   'candle_ratio': candle_ratio}
                df_temp = pd.DataFrame([df_summary_dict])
                df_summary = pd.concat([df_summary, df_temp])
        return (len(df_summary[df_summary['candle_ratio'] > 0.5]) / len(df_summary))
    except:
        return 0


def get_candle_signal_3(instrument_code, sample_size, interval):
    try:
        df_summary = pd.DataFrame()
        for i in range(sample_size + 1):
            start = ((datetime.now() + timedelta(days=-i)).strftime("%Y-%m-%d")) + " 09:00:00"
            end = ((datetime.now() + timedelta(days=-i)).strftime("%Y-%m-%d")) + " 16:00:00"
            df_historical = get_candle(instrument_code, start, end, interval)

            if len(df_historical) > 0:
                df_historical['change'] = df_historical['close'] - df_historical['open']
                df_historical['candle_type'] = df_historical['change'].apply(lambda x: 1 if x > 0 else -1)
                df_historical['candle_weight'] = df_historical['change'].abs() / df_historical['change'].abs().max()
                df_historical['candle_strength'] = df_historical['candle_type'] * df_historical['candle_weight']
                try:
                    candle_ratio = sum(df_historical['candle_strength'])
                except:
                    candle_ratio = 0
                df_summary_dict = {'day': end,
                                   'candle_ratio': candle_ratio}
                df_temp = pd.DataFrame([df_summary_dict])
                df_summary = pd.concat([df_summary, df_temp])
        return ((sum(df_summary['candle_ratio'])) / sample_size)
    except:
        return 0


def shortlist_scrips(interval):
    date = datetime.now().strftime("%d_%m_%y")
    filename = f'files\weighted_final_shortlist_{date}.csv'
    if filename not in os.listdir():
        df_instruments1 = pd.read_excel('final_instruments.xlsx')
        df_instruments1['signal_3_1d'] = df_instruments1['instrument_token'].apply(lambda x: get_candle_signal_3(x, 1, interval))
        df_instruments1['signal_3_7d'] = df_instruments1['instrument_token'].apply(lambda x: get_candle_signal_3(x, 7, interval))
        df_instruments1['signal_3_31d'] = df_instruments1['instrument_token'].apply(lambda x: get_candle_signal_3(x, 31, interval))
        df_instruments1 = df_instruments1.sort_values(by="signal_3_31d", ascending=False).reset_index(drop=True)
        df_instruments1.to_csv(filename, index=False)
    df_instruments1 = pd.read_csv(filename)
    buy_shortlist_df = df_instruments1[(df_instruments1['signal_3_1d'] >= 0) & (df_instruments1['signal_3_7d'] > 0) & (df_instruments1['signal_3_31d'] > 0)]
    sell_shortlist_df = df_instruments1[(df_instruments1['signal_3_1d'] <= 0) & (df_instruments1['signal_3_7d'] < 0) & (df_instruments1['signal_3_31d'] < 0)]
    return (buy_shortlist_df, sell_shortlist_df)


def get_latest_tick(instrument_token):
    with MongoClient() as client:
        db = client['kite']
        collection = db['tick_data']
        record = collection.find({'instrument_token': instrument_token}).sort({'exchange_timestamp': -1}).limit(1)
        return record
