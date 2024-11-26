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
import utils
from datetime import datetime

date = datetime.now().strftime("%d_%m_%y")

def market_hours():
    # Get current time
    current_time = datetime.now().time()
    # Define start and end times
    start_time = time(8, 45)  # 8:45 AM
    end_time = time(16, 0)   # 4:00 PM
    # Check if current time is between start and end times
    return start_time <= current_time <= end_time

logging.basicConfig(filename = f'kite_logs/log_{date}.txt', level=logging.INFO)
kite = utils.login_kite()
kws = kite.ticker()

try:
    scrips = utils.shortlist_scrips('5minute', kite=kite)
    tokens = [i['instrument_token'] for i in scrips]
    symbols = [i['tradingsymbol'] for i in scrips]
    token_count=len(tokens)
    dt=datetime.now()
    logging.info(f"[{dt}] - {token_count} tokens found.")


    # Callback for tick reception.
    def on_ticks(ws, ticks):
        dt=datetime.now()
        if market_hours():
            if len(ticks) > 0:
                ts=ticks[0]['exchange_timestamp']
                if ts.year==datetime.now().year:
                    logging.info(f"[{dt}] - Tick: {ts}")
                    for tick in ticks:
                        utils.insert_tick(tick)
                else:
                    message_close=f"[{dt}] - Market is closed due to holiday. Stopping the script"
                    logging.info(message_close)
                    utils.send_alert(message_close)
                    ws.close()
        else:
            message_close=f"[{dt}] - Market is closed. Stopping the script"
            logging.info(message_close)
            utils.send_alert(message_close)
            ws.close()
            utils.sleep_computer()


    # Callback for successful connection.
    def on_connect(ws, response):
        dt=datetime.now()
        message_connect = f"[{dt}] - Successfully connected."
        logging.info(message_connect)
        utils.send_alert(message_connect)
        ws.subscribe(tokens)
        ws.set_mode(ws.MODE_FULL, tokens)
        message_tokens = f"[{dt}] - Subscribe to tokens in Full mode: {symbols}"
        logging.info(message_tokens)
        utils.send_alert(message_tokens)


    # Callback when current connection is closed.
    def on_close(ws, code, reason):
        dt=datetime.now()
        if code:
            logging.info(f"[{dt}] - Connection closed: {code} - {reason}")
        else:
            logging.info(f"[{dt}] - Connection closed: Closure due to non market hours.")
        ws.stop()


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
