from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os
import time
import config
from jugaad_trader import Zerodha
import pyotp
from pymongo import MongoClient
from tqdm import tqdm


import requests
import json

def send_alert(message):
    url = "https://api.telegram.org/bot7160202236:AAEXpCcvVl434EQEJK-iwlR5iUsaR5h3EUM/sendMessage"

    payload = json.dumps({
    "chat_id": "-1002114890478",
    "text": str(message)
    })
    headers = {
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    return response

def login_kite():
    username = config.username
    password = config.password
    totp = pyotp.TOTP(config.totp_code)
    kite = Zerodha(user_id=username, password=password, twofa=totp.now())
    kite.login()
    return kite


def get_candle_fig(instrument_code, start, end, interval):
    kite = login_kite()
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


def get_candle(instrument_code, start, end, interval,kite):
    df_historical = pd.DataFrame(kite.historical_data(instrument_code, start, end, interval))
    if len(df_historical) > 0:
        return (df_historical)
    else:
        return (pd.DataFrame())

def last_n_weekdays(n):
    # Initialize an empty list to store the result
    result = []
    
    # Get today's date
    current_date = datetime.now()
    
    # Iterate until we collect n weekdays
    while len(result) < n:
        # Subtract one day from the current date
        current_date -= timedelta(days=1)
        
        # Check if the current day is a Saturday or Sunday
        if current_date.weekday() in [5, 6]:  # Saturday is 5, Sunday is 6
            continue  # Skip if it's a weekend
        
        # Add the current date to the result
        result.append(current_date.strftime('%Y-%m-%d'))
    
    # Return the result in reverse order (last to first)
    return result[::-1]

def get_candle_signal(instrument_code, sample_size, interval,  kite ,today=1,):
    start = min(last_n_weekdays(sample_size)) + " 09:00:00"
    end = max(last_n_weekdays(sample_size)) + " 16:00:00"
    df_historical = get_candle(instrument_code, start, end, interval, kite=kite)
    if len(df_historical) > 0:
        df_historical['change'] = (df_historical['close'] - df_historical['open'])
        df_historical['candle_type'] = df_historical['change'].apply(lambda x: 1 if x > 0 else -1)
        df_historical['candle_weight'] = df_historical['change'].abs() / df_historical['change'].abs().max()
        df_historical['candle_strength'] = df_historical['candle_type'] * df_historical['candle_weight']
        candle_ratio = sum(df_historical['candle_strength'])
        return (candle_ratio / sample_size)
    else:
        return 0


def insert_tick(tick):
    with MongoClient() as client:
        db = client['kite']
        collection = db['tick_data']
        collection.insert_one(tick)

def sleep_computer():
    time.sleep(5)
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

def shortlist_scrips(interval,kite):
    date = datetime.now().strftime("%d_%m_%y")
    filename = f'files//weighted_final_shortlist_{date}.csv'
    if os.path.basename(filename) not in os.listdir('files'):
        df_instruments1 = pd.read_excel('files//final_instruments.xlsx')
        for i in tqdm(range(len(df_instruments1))):
            df_instruments1.loc[i,'signal_1d']=get_candle_signal(df_instruments1.loc[i,'instrument_token'],1,interval,kite=kite)
            df_instruments1.loc[i,'signal_7d']=get_candle_signal(df_instruments1.loc[i,'instrument_token'],7,interval,kite=kite)
            df_instruments1.loc[i,'signal_31d']=get_candle_signal(df_instruments1.loc[i,'instrument_token'],31,interval,kite=kite)
        df_instruments1 = df_instruments1.sort_values(by="signal_31d", ascending=False).reset_index(drop=True)
        df_instruments1.to_csv(filename, index=False)
    df_instruments1 = pd.read_csv(filename)
    buy_shortlist_df = df_instruments1[(df_instruments1['signal_1d'] >= 0) & (df_instruments1['signal_7d'] > 0) & (df_instruments1['signal_31d'] > 0)].sort_values(by="signal_7d", ascending=False).head(20)
    sell_shortlist_df = df_instruments1[(df_instruments1['signal_1d'] <= 0) & (df_instruments1['signal_7d'] < 0) & (df_instruments1['signal_31d'] < 0)].sort_values(by="signal_7d", ascending=True).head(20)
    df_instruments_final=pd.concat([buy_shortlist_df,sell_shortlist_df])
    df_instruments_final=df_instruments_final[['instrument_token','tradingsymbol']]
    df_instruments_dict=df_instruments_final.to_dict(orient="records")
    return df_instruments_dict


def get_latest_tick(instrument_token):
    with MongoClient() as client:
        db = client['kite']
        collection = db['tick_data']
        record = collection.find({'instrument_token': instrument_token}).sort({'exchange_timestamp': -1}).limit(1)
        return record



