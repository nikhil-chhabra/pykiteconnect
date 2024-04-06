###############################################################################
#
# The MIT License (MIT)
#
# Copyright (c) Zerodha Technology Pvt. Ltd.
#
# This example shows how to run KiteTicker in threaded mode.
# KiteTicker runs in seprate thread and main thread is blocked to juggle between
# different modes for current subscribed tokens. In real world web apps
# the main thread will be your web server and you can access WebSocket object
# in your main thread while running KiteTicker in separate thread.
###############################################################################

import logging
import pandas as pd
from datetime import datetime, time
from pymongo import MongoClient
from jugaad_trader import Zerodha
import pyotp
import config


def market_hours():
    # Get current time
    current_time = datetime.now().time()
    # Define start and end times
    start_time = time(9, 0)  # 9:00 AM
    end_time = time(16, 0)   # 4:00 PM
    # Check if current time is between start and end times
    return start_time <= current_time <= end_time


username = config.username
password = config.password
totp = pyotp.TOTP(config.totp_code)


client = MongoClient()


def insert_tick(tick):
    db = client['kite']
    collection = db['tick_data']
    collection.insert_one(tick)


logging.basicConfig(filename = 'log.txt', level=logging.INFO)



kite = Zerodha(user_id=username, password=password, twofa=totp.now())

kite.login()

kws = kite.ticker()

try:
    # Initialise.
    date = datetime.now().strftime("%d_%m_%y")
    df_instruments1 = pd.read_csv(f'files\weighted_final_shortlist_{date}.csv')
    ce_shortlist_df = df_instruments1[(df_instruments1['signal_3_1d'] >= 0) & (df_instruments1['signal_3_7d'] > 0) & (df_instruments1['signal_3_31d'] > 0)]
    pe_shortlist_df = df_instruments1[(df_instruments1['signal_3_1d'] <= 0) & (df_instruments1['signal_3_7d'] < 0) & (df_instruments1['signal_3_31d'] < 0)]

    # RELIANCE BSE
    tokens = ce_shortlist_df['instrument_token'].tolist()


    # Callback for tick reception.
    def on_ticks(ws, ticks):
        dt=datetime.now()
        if market_hours():
            if len(ticks) > 0:
                ts=ticks[0]['exchange_timestamp']
                logging.info(f"[{dt}] - Tick: {ts}")
                for tick in ticks:
                    insert_tick(tick)


    # Callback for successful connection.
    def on_connect(ws, response):
        dt=datetime.now()
        logging.info(f"[{dt}] - Successfully connected. Response: {response}")
        ws.subscribe(tokens)
        ws.set_mode(ws.MODE_FULL, tokens)
        logging.info(f"[{dt}] - Subscribe to tokens in Full mode: {tokens}")


    # Callback when current connection is closed.
    def on_close(ws, code, reason):
        dt=datetime.now()
        logging.info(f"[{dt}] - Connection closed: {code} - {reason}")


    # Callback when connection closed with error.
    def on_error(ws, code, reason):
        dt=datetime.now()
        logging.info(f"[{dt}] - Connection error: {code} - {reason}")


    # Callback when reconnect is on progress
    def on_reconnect(ws, attempts_count):
        dt=datetime.now()
        logging.info(f"[{dt}] - Reconnecting: {attempts_count}")


    # Callback when all reconnect failed (exhausted max retries)
    def on_noreconnect(ws):
        dt=datetime.now()
        logging.info(f"[{dt}] - Reconnect failed.")


    # Assign the callbacks.
    kws.on_ticks = on_ticks
    kws.on_close = on_close
    kws.on_error = on_error
    kws.on_connect = on_connect
    kws.on_reconnect = on_reconnect
    kws.on_noreconnect = on_noreconnect

    # Infinite loop on the main thread.
    # You have to use the pre-defined callbacks to manage subscriptions.
    kws.connect()

except Exception as e:
    dt=datetime.now()
    logging.info(f"[{dt}] - Error : {e}")
