api_key = "JyPzgcScbDfyY5H-mVhM"

def createLogger(logfile_path):
    logger = logging.getLogger('myapp')
    hdlr = logging.FileHandler(logfile_path)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr) 
    logger.setLevel(logging.INFO)
    return logger
    
def getHistoricalData(ticker, instrument_type, logger, period = 'daily'):  
    if instrument_type == 'FUTURE':
        try:
            return Quandl.get(ticker, collapse=period, authtoken = api_key)
        except Exception as e:
            logger.exception("message")
    elif instrument_type == 'BTC_PAIR' :
        data = p.returnChartData(currencyPair = ticker)
        data.columns = ['Last', 'High', 'Low','Open','quoteVolume', 'volume', 'weightedAverage']
        return data
    
def movingaverage (values, window):
    weights = np.repeat(1.0, window)/window
    sma = np.convolve(values, weights, 'valid')
    return sma
    
def pad(array, width, value):
    return np.lib.pad(array, (width,0), mode = 'constant', constant_values= value)
    
def trade_size(signal, capital, vol, price, point_value):
    return round(0.001 * signal * capital / (vol*point_value))
    
def store_positions(close, positions_path, instrument, instrument_id, logger):
    positions_directory_path = positions_path + strftime("%Y-%m-%d")
    if not os.path.exists(positions_directory_path):
        os.makedirs(positions_directory_path)
    positions_file_path = positions_directory_path + '/' + instrument + '_' + strftime("%Y-%m-%d_%H-%M-%S") + '.csv'
    logger.info('Storing positions to '+positions_file_path+' instrument_id='+ instrument_id)
    close[['close','position']].to_csv(positions_file_path,mode  = 'w+')


#def plot_pnl(close, model):
#    plt.figure()
#    plt.ion()
#    
#    plt.subplot(411)
#    plt.plot(close['close'], ls = '-')
#    plt.plot(close['ma1'], ls = '-')
#    plt.plot(close['ma2'], ls = '-')
#    plt.title(model)
#    plt.ylabel('Price')
#    plt.subplot(412)
#    plt.plot(close['pnl'])
#    plt.ylabel('PnL')
#    plt.subplot(413)
#    plt.plot(close['notional'])
#    plt.ylabel('Notional')
#    plt.subplot(414)
#    plt.plot(close['vol'])
#    plt.ylabel('vol')
#    plt.show()
    
def plot_pnl(close, model):
    plt.ion()
    f, (ax1, ax2, ax3,ax4) = plt.subplots(4, 1, sharex=True)
    ax1.plot(close['close'], ls = '-')
    ax1.plot(close['ma1'], ls = '-')
    ax1.plot(close['ma2'], ls = '-')
    ax1.set_title(model)
    ax1.set_ylabel('Price')
    ax2.plot(close['pnl'])
    ax2.set_ylabel('PnL')
    ax3.plot(close['notional'])
    ax3.set_ylabel('Notional')
    ax4.plot(close['vol'])
    ax4.set_ylabel('vol')
    plt.show()

    
def calculate_pnl(close, instrument, point_value, slippage):
    pnl = np.array([])
    first_position = close[close['position'] != 0].index[0]
    positions = close[first_position:][ - np.isnan(close['vol'])]
    pnl_snapshot = PnlSnapshot(instrument, np.sign(positions.ix[0].trade), positions.ix[0].close, abs(positions.ix[0].trade * point_value))
    row_number = 0
    for index, row in positions.iterrows():
        if row_number > 0:
            fill_price = row['close'] + np.sign(row['trade']) * row['close'] * slippage
            if abs(row['trade'] ) > 0:
                pnl_snapshot.update_by_tradefeed(np.sign(row['trade']), fill_price , abs(row['trade'] * point_value))
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
    
def apply_model_gearing(close, gearing_factor, instrument, point_value, capital):
    close['position'] = close['position'] * gearing_factor
    close['trade'] = close['trade'] * gearing_factor
    close['notional'] = calculate_notional_positions(close, point_value)
    close['transaction_cost'] = close.apply(lambda row: abs(row['trade'] * row['close']* transaction_cost) , axis=1)
    
    close = update_pnl(close, instrument, point_value, slippage, capital)
    return close
    
def update_pnl(close, instrument, point_value, slippage = 0.005, capital = 100E6):
    pnl = calculate_pnl(close, instrument, point_value, slippage)
    close['pnl'] = pad(pnl, len(close) - pnl.size, float('nan'))
    close['daily_pnl'] = close['pnl'].diff()
    close['daily_pnl_pct'] = close['daily_pnl'] / capital
    
    return close

def calculate_pct_volatility(price, window):
    pct_change = price.pct_change()
    return pd.rolling_std(pct_change, window)

def calculate_change_volatility(price, window):
    change = price.diff()
    return pd.rolling_std(change, window)
    
def calculate_historical_positions(data, point_value):
    positions = data.apply(lambda row: trade_size(row['signal'], capital, row['vol'], row['close'], point_value), axis=1)
    positions[np.isnan(positions)] = 0
    return positions

def calculate_notional_positions(data, point_value):
    return data.apply(lambda row: row['position'] * row['close'] * point_value , axis=1)
    
def calculate_transaction_costs(data, transaction_cost):
    return data.apply(lambda row: abs(row['trade'] * row['close'] * transaction_cost) , axis=1)
    
def plot_pnl_by_model(pnl):
    fig, ax = plt.subplots(figsize=(8,6))
    for label, df in pnl.groupby('model'):
        df.pnl.plot( ax=ax, label=label)
    plt.title('PnL by model')
    plt.ylabel('PnL in USD')
    plt.legend()
    
def plot_total_pnl(total_pnl):
    plt.figure()
    plt.title('Total PnL')
    plt.ylabel('PnL in USD')
    plt.plot(total_pnl)
    
def calculate_average_true_range (data, period):
    ATR1 = abs (data.loc[:,('High')] - data.loc[:,('Low')])
    ATR2 = abs (data.loc[:,('High')] - data.loc[:,('Last')].shift())
    ATR3 = abs (data.loc[:,('Low')] - data.loc[:,('Last')].shift())
    TR = pd.concat([ATR1, ATR2, ATR3], axis = 1)
    true_range = TR[[0,1, 2]].max(axis=1)
    
    ATR = np.concatenate((np.repeat(float('nan'), period -1), [np.mean(true_range[0:period])]))
    for index in range(period, len(data)):
        latest_atr = (ATR[index - 1] * (period -1) + true_range[index])/ period
        ATR= np.append(ATR, latest_atr)
    
    return ATR
    
def print_full(x):
    pd.set_option('display.max_rows', len(x))
    print(x)
    pd.reset_option('display.max_rows')
    
def atr_gaussian_fitting(ATR, display = False):
    ATR_clean = ATR[- np.isnan(ATR)]
    (mu, sigma) = norm.fit(ATR_clean)
    if display:
        n, bins, patches = plt.hist(ATR_clean, 60, normed=1, facecolor='green', alpha=0.75)
        y = mlab.normpdf( bins, mu, sigma)
        l = plt.plot(bins, y, 'r--', linewidth=2)
        plt.xlabel('ATR')
        plt.ylabel('Probability')
        plt.title(r'$\mathrm{Histogram\ of\ ATR:}\ \mu=%.3f,\ \sigma=%.3f$' %(mu, sigma))
        plt.grid(True)
        plt.show()
    return (mu, sigma)
    

    
#'YAHOO/AAPL'
#'CHRIS/CME_CL1'
#plt.plot(data['Open'])