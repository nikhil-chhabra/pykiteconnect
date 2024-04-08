from datetime import datetime
from dateutil import parser
import utils


def sl_multiplier_strategy(instrument_token,multiplier):
    '''
    The strategy is to read the latest available candle(reference candle/RC) 
    (Probably 9:15-9:20 AM or 9:15-9:30 AM) and place the order in the second candle based on following logics:
    
    1. Order Price: Price at which we enter the market with buy or sell order. 
    The order price is equal to the closing price of RC. 

    2. Order Type: It is either buy/sell. If the RC is green, we create a buy order or if it's red we create a sell order.

    3. Stop Loss: It is equal to the low of the RC.

    4. Target Price: Exit point of trade. It is [('multiplier' x (order price - stoploss) in case of buy order)/('multiplier' x (stoploss - order price ) in case of sell order)]
    
    '''
    start=((datetime.now()).strftime("%Y-%m-%d"))+" 09:15:00"
    end=((datetime.now()).strftime("%Y-%m-%d"))+" 15:30:00"
    interval="5minute"
    df_candle=utils.get_candle(instrument_token,start,end,interval)
    df_candle['date']=df_candle['date'].apply(lambda x: parser.parse(str(x).replace('+05:30','')))
    df_candle['day']=df_candle['date'].apply(lambda x: x.date())
    df_candle['change']=df_candle['close']-df_candle['open']
    order_price=df_candle.loc[len(df_candle)-1,'close']
    order_type="buy"
    stop_loss=df_candle.loc[len(df_candle)-1,'low']
    target_price=order_price+((order_price-stop_loss)*multiplier)
    order = {'instrument_code':instrument_token,
            'order_price':order_price,
            'order_type':order_type,    
            'stop_loss':stop_loss,
            'target_price':target_price}
    return order
