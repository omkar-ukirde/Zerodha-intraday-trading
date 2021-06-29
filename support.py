import zrd_login
import datetime
import pandas as pd
import pdb
import requests
from bs4 import BeautifulSoup



kite = zrd_login.kite



def get_data(name, segment, delta, interval):
	try:
		token = kite.ltp([segment + name])[segment + name]['instrument_token']
		to_date = datetime.datetime.now().date()
		from_date = to_date - datetime.timedelta(days=delta)
		data = kite.historical_data(instrument_token=token, from_date=from_date, to_date=to_date, interval=interval, continuous=False, oi=False)
		df = pd.DataFrame(data)
		return df
	except Exception as e:
		print(f"Error in get_data {e}")
		raise 

def resample_to_week(df):
	df = df.set_index(df['date'])
	logic = {'open':'first','high':'max','low':'min','close':'last','volume':'sum'}
	resample_week = df.resample('W-FRI').agg(logic)
	resample_week.reset_index(inplace = True)
	resample_week['date'] = resample_week['date'] - datetime.timedelta(days=4)
	resample_week.set_index('date', inplace=True)
	resample_week['pre_high'] = resample_week['high'].shift(1)
	resample_week['pre_low'] = resample_week['low'].shift(1)
	return resample_week

def get_live_date(name):
	try:
		df15 = get_data(name=name, segment='NSE:', delta=5, interval='15minute')
		dfday = get_data(name=name, segment='NSE:', delta=5, interval='day')
		#dfweek = resample_to_week(dfday)
		dfday['pre_high'] = dfday['high'].shift(1)
		dfday['pre_low'] = dfday['low'].shift(1)
		dfday.set_index('date', inplace=True)
		df15.set_index('date', inplace=True)
		return df15, dfday
	except Exception as e:
		print(f"get_live_date {e}")
		raise

def check_entry(df15, name, dfday, completed_candle, ctime):
	try:
		#buy condition
		row = df15.loc[completed_candle]
		#quote = kite.quote(['NSE:'+name])
		#buy_condition = (row['open'] < dfday['pre_high'][-1] < row['close']) and (quote['NSE:'+name]['buy_quantity'] > quote['NSE:'+name]['sell_quantity'])
		buy_condition = (row['open'] < dfday['pre_high'][-1] < row['close']) and ctime.time() < datetime.time(2, 50)
		#buy_condition = (row['open'] < dfday['pre_high'][-1] < row['close'])
		#sell condition
		#sell_condition = (row['open'] > dfday['pre_low'][-1] > row['close']) and (quote['NSE:'+name]['buy_quantity'] < quote['NSE:'+name]['sell_quantity'])
		sell_condition = (row['open'] > dfday['pre_low'][-1] > row['close']) and ctime.time() > datetime.time(2, 50) 
		#sell_condition = False
		#sell_condition = (row['open'] > dfday['pre_low'][-1] > row['close'])
		return buy_condition, sell_condition
	except Exception as e:
		print(f"error in check_entry {e}")
		raise

def placeMarketOrder(symbol,buy_sell,quantity):    
    # Place an intraday market order on NSE
    if buy_sell == "buy":
        t_type=kite.TRANSACTION_TYPE_BUY
    elif buy_sell == "sell":
        t_type=kite.TRANSACTION_TYPE_SELL
    kite.place_order(tradingsymbol=symbol,
                    exchange=kite.EXCHANGE_NSE,
                    transaction_type=t_type,
                    quantity=quantity,
                    order_type=kite.ORDER_TYPE_MARKET,
                    product=kite.PRODUCT_MIS,
                    variety=kite.VARIETY_REGULAR)
    
def CancelOrder(order_id):    
    kite.cancel_order(order_id=order_id,variety=kite.VARIETY_REGULAR)  

def exit_funct():
	# Close all open position
	orderbook = kite.orders()
	for order in orderbook:
		try:
			kite.cancel_order(variety=order['variety'], order_id=order['order_id'])
		except Exception as e:
			continue
	print(f"All Open Orders are closed ")
	
	pos_df = pd.DataFrame(kite.positions()["day"])
	for i in range(len(pos_df)):
	    ticker = pos_df["tradingsymbol"].values[i]
	    if pos_df["quantity"].values[i] >0:
	        quantity = pos_df["quantity"].values[i]
	        placeMarketOrder(ticker,"sell", quantity)
	    if pos_df["quantity"].values[i] <0:
	        quantity = abs(pos_df["quantity"].values[i])
	        placeMarketOrder(ticker,"buy", quantity)						
	print("All Open Positions are closed")        

def get_stocks(url):
    res = []
    response = requests.get(url, headers={'User-Agent': 'Custom'})
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table",{"class":"table table-bordered table-striped table-hover"})    
    table_rows = table.find_all('tr')
    lo = []
    for tr in table_rows:
        td = tr.find_all('td')
        row = [tr.text for tr in td]
        lo.append(row)
    df = pd.DataFrame(lo, columns=["Name", "symbol", "Sector","Current Price","Trending for Days","Average Volume in thousands"])
    watchlist = df['symbol'].to_list()
    for val in watchlist:
        if val != None :
            res.append(val)    
    return res
