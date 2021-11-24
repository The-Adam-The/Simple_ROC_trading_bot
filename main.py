from binance.client import Client
import pandas as pd
import asyncio
import websockets
import json
import ta
import os

#binance API details
API_KEY = os.environ['BINANCE_API']
SECRET_KEY = os.environ['BINANCE_SECRET']

#insert trading pair
trading_pair = 'adabusd'
#number of coins to buy
n_coins = 10

# trailing stop value and take_profit express values at decimals e.g 1.002 = t/p 2%
trailing_stop = 0.995
take_profit = 1.002



stream = websockets.connect(f'wss://stream.binance.com:9443/stream?streams={trading_pair}@miniTicker')
client = Client(API_KEY, SECRET_KEY)

async def main():
    df = pd.DataFrame()
    open_position = False
    async with stream as receiver:
        while True:
            data = await receiver.recv()
            data = json.loads(data)['data']
            df = df.append(createframe(data))
            print(df)

            if len(df) > 30:
                if not open_position:
                    if ta.momentum.roc(df.Price, 30).iloc[-1] > 0 and ta.momentum.roc(df.Price, 30).iloc[-2]:
                        order = client.create_order(symbol='ADABUSD',
                                                        side='BUY', type='MARKET', quantity=n_coins)
                        print(order)
                        open_position=True
                        buyprice = float(order['fills'][0]['price'])

                    if open_position:
                        subdf = df[df.Time >= pd.to_datetime(order['transactTime'], unit='ms')]
                        if len(subdf) > 1:
                            subdf['highest'] = subdf.Price.cummax()
                            subdf['trailingstop'] = subdf['highest'] * trailing_stop
                            if subdf.iloc[-1].Price < subdf.iloc[-1].trailingstop or df.iloc[-1] / \
                                    float(order['fills'][0]['price']) > take_profit:
                                order = client.create_order(symbol='ADAUSDT', side='SELL', type='MARKET', quantity=10)
                                print(order)
                                sellprice = float(order['fills'][0]['price'])
                                print(f"You made {sellprice - buyprice} profit")
                                open_position = False

                print(df.iloc[-1])



def createframe(msg):
    df = pd.DataFrame([msg])
    df = df.loc[:, ['s', 'E', 'c']]
    df.columns = ['symbol', 'Time', 'Price']
    df.Price = df.Price.astype(float)
    df.Time = pd.to_datetime(df.Time, unit='ms')
    return df

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
