api_key = "JyPzgcScbDfyY5H-mVhM"

def createLogger(logfile_path):
    logger = logging.getLogger('myapp')
    hdlr = logging.FileHandler(logfile_path)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr) 
    logger.setLevel(logging.INFO)
    return logger
    
def getHistoricalData(ticker, logger, period = 'daily'):  
    try:
        return Quandl.get(ticker, collapse=period, authtoken = api_key)
    except Exception as e:
        logger.exception("message")
    
def movingaverage (values, window):
    weights = np.repeat(1.0, window)/window
    sma = np.convolve(values, weights, 'valid')
    return sma
    
def pad(array, width, value):
    return np.lib.pad(array, (width,0), mode = 'constant', constant_values= value)
    
def trade_size(signal, capital, vol, price):
    return round(0.001 * signal * capital / (vol*price))
    
def store_positions(close, positions_path, instrument, quandl_id, logger):
    positions_directory_path = positions_path + strftime("%Y-%m-%d")
    if not os.path.exists(positions_directory_path):
        os.makedirs(positions_directory_path)
    positions_file_path = positions_directory_path + '/' + instrument + '_' + strftime("%Y-%m-%d_%H-%M-%S") + '.csv'
    logger.info('Storing positions to '+positions_file_path+' quandl_id='+ quandl_id)
    close[['close','position']].to_csv(positions_file_path,mode  = 'w+')

def plot_signals(close):
    plt.figure()
    plt.ion()
    plt.plot(close['close'], ls = '-')
    plt.plot(close['ma20'], ls = '-')
    plt.plot(close['ma100'], ls = '-')
    plt.show()

def plot_pnl(close, model):
    plt.figure()
    plt.ion()
    
    plt.subplot(411)
    plt.plot(close['close'], ls = '-')
    plt.plot(close['ma50'], ls = '-')
    plt.plot(close['ma100'], ls = '-')
    plt.title(model)
    plt.ylabel('Price')
    plt.subplot(412)
    plt.plot(close['pnl'])
    plt.ylabel('PnL')
    plt.subplot(413)
    plt.plot(close['notional'])
    plt.ylabel('Notional')
    plt.subplot(414)
    plt.plot(close['vol'])
    plt.ylabel('vol')
    plt.show()
    
def calculate_pnl(close, instrument, slippage):
    pnl = np.array([])
    positions = close[close['signal'] != 0][ - np.isnan(close['vol'])]
    pnl_snapshot = PnlSnapshot(instrument, np.sign(positions.ix[0].trade), positions.ix[0].close, abs(positions.ix[0].trade))
    row_number = 0
    for index, row in positions.iterrows():
        if row_number > 0:
            fill_price = row['close'] + np.sign(row['trade']) * slippage
            pnl_snapshot.update_by_tradefeed(np.sign(row['trade']), fill_price , abs(row['trade']))
            pnl_snapshot.update_by_marketdata(row['close'])
            pnl = np.append(pnl, pnl_snapshot.m_total_pnl - row['transaction_cost'])
        row_number += 1
    return pnl
    
def annualised_sharpe(returns, risk_free_rate = 0.02, N=252):
    excess_returns = returns - (risk_free_rate/N)
    
    #TODO: Returns = daily pnl as percentage return on capital, daily percentage change in total USD pnl?
    return np.sqrt(N) * (excess_returns.mean()) / excess_returns.std()
    
def daily_drawdown(pnl_usd, window = 252):
    # Calculate the max drawdown in the past window days for each day in the series.
    # Use min_periods=1 if you want to let the first 252 days data have an expanding window
    Roll_Max = pd.rolling_max(pnl_usd, window, min_periods=1)
    Daily_Drawdown = pnl_usd - Roll_Max
    Daily_Drawdown_Pct = (pnl_usd - Roll_Max)/Roll_Max
    
    #TODO: Drawdown in USD or in percentage drop since peak?
    
    return Daily_Drawdown
    
def plot_drawdown(drawdown):
    plt.figure()
    plt.plot(drawdown)
    plt.ylabel('Drawdown')
    plt.title('Drawdown')
    plt.show()
    
def calculate_model_gearing(pnl, capital = 100E6, vol_target = 0.15, window = 252):
    annualized_usd_vol = np.sqrt(252)*pnl.std()
    gearing_factor = (vol_target * capital) / annualized_usd_vol
    
    return gearing_factor
    
def apply_model_gearing(close, gearing_factor, instrument, capital):
    close['position'] = close['position'] * gearing_factor
    close['trade'] = close['trade'] * gearing_factor
    close['notional'] = calculate_notional_positions(close)
    close['transaction_cost'] = close.apply(lambda row: abs(row['trade'] * transaction_cost) , axis=1)
    
    close = update_pnl(close, instrument, slippage, capital)
    return close
    
def update_pnl(close, instrument, slippage = 0.005, capital = 100E6):
    pnl = calculate_pnl(close, instrument, slippage)
    close['pnl'] = pad(pnl, len(close) - pnl.size, float(0))
    close['daily_pnl'] = close['pnl'].diff()
    close['daily_pnl_pct'] = close['daily_pnl'] / capital
    
    return close

def calculate_volatility(data, window):
    pct_change = data.pct_change()
    return pd.rolling_std(pct_change, window)
    
def calculate_historical_positions(data):
    positions = data.apply(lambda row: trade_size(row['signal'], capital, row['vol'], row['close']), axis=1)
    positions[np.isnan(positions)] = 0
    return positions

def calculate_notional_positions(data):
    return data.apply(lambda row: row['position'] * row['close'] , axis=1)
    
def calculate_transaction_costs(data, transaction_cost):
    return data.apply(lambda row: abs(row['trade'] * transaction_cost) , axis=1)
    
def plot_pnl_by_model(pnl):
    fig, ax = plt.subplots(figsize=(8,6))
    for label, df in pnl.groupby('model'):
        df.pnl.plot( ax=ax, label=label)
    plt.title('PnL by model')
    plt.ylabel('PnL in USD')
    plt.legend()
    
def plot_total_pnl(pnl):
    total_pnl = pnl.groupby(pnl.index).sum()
    plt.figure()
    plt.title('Total PnL')
    plt.ylabel('PnL in USD')
    plt.plot(total_pnl)
#'YAHOO/AAPL'
#'CHRIS/CME_CL1'
#plt.plot(data['Open'])