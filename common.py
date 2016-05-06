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
    #return round(0.001 * signal * capital / (vol*point_value))
    return round(signal * capital / (vol*point_value))
    
def store_positions(close, positions_path, instrument, instrument_id, logger):
    positions_directory_path = positions_path + strftime("%Y-%m-%d")
    if not os.path.exists(positions_directory_path):
        os.makedirs(positions_directory_path)
    positions_file_path = positions_directory_path + '/' + instrument + '_' + strftime("%Y-%m-%d_%H-%M-%S") + '.csv'
    logger.info('Storing positions to '+positions_file_path+' instrument_id='+ instrument_id)
    close[['close','position']].to_csv(positions_file_path,mode  = 'w+')

    
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
    pnl_snapshot = PnlSnapshot(instrument)
    for index, row in positions.iterrows():
        fill_price = row['close'] + np.sign(row['trade']) * row['close'] * slippage
        if abs(row['trade'] ) > 0:
            pnl_snapshot.update_by_tradefeed(np.sign(row['trade']), fill_price , abs(row['trade'] * point_value))
        pnl_snapshot.update_by_marketdata(row['close'])
        pnl = np.append(pnl, pnl_snapshot.m_total_pnl - row['transaction_cost'])
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
    
def historical_atr_gaussian_fitting(data, ATR, display = False):
    data.loc[:,('ATR')] = ATR
    data.loc[:,('ATR_mean')] = float('nan')
    data.loc[:,('ATR_std')] = float('nan')
    for index in range(0, len(data)):
        if(np.isnan(ATR[index])):
            data['ATR_mean'][index] = float('nan')
            data['ATR_std'][index] = float('nan')
        else:
            (ATR_mean, ATR_std_dev) = atr_gaussian_fitting(ATR[0:index], display = False)
            data['ATR_mean'][index] =ATR_mean
            data['ATR_std'][index] =ATR_std_dev
    return(data)

def generate_trades(current_positions_file, base_positions, base_capital, real_capital):
    current_positions = pd.DataFrame.from_csv(current_positions_file,index_col = None)
    #positions_today = base_positions[time.strftime("%m/%d/%Y")]
    positions_today = base_positions["05/05/2016"]
    positions_today.columns = ['model', 'price', 'instrument_id', 'target_position']
    positions_today['target_position'] = positions_today.target_position * real_capital/float(base_capital)
    positions_today = positions_today.merge(current_positions, how='left', on = 'model' )
    positions_today['trade'] = positions_today.target_position - positions_today.current_position
    if(long_only):
        #If model wants to go short, flatten the position
        positions_today['trade'] = np.where(positions_today.trade + positions_today.current_position < 0 , -1 * positions_today.current_position , positions_today.trade)
    return(positions_today)
    
def apply_limits(close, instrument, point_value, slippage, capital, limits):
    close = close.reset_index().merge(limits, how='left', on = 'model' ).set_index('date')
    close['limit_scaling'] = np.where(abs(close.notional) > close.limit, np.sign(close.notional)*close.limit/close.notional, 1 )
    close['position'] = close.position * close.limit_scaling
    close['trade'] = close.trade * close.limit_scaling
    close['notional'] = close.notional * close.limit_scaling
    close['transaction_cost'] = close.transaction_cost * close.limit_scaling
    close = update_pnl(close, instrument, point_value, slippage, capital)
    return(close)
    
def execute_trades(trades):
    execution_recap = collections.namedtuple('ExecutionRecap', ['order_numbers', 'recaps'])
    order_ids = []
    recaps = []
    trades_to_execute = trades[trades['trade'] != 0].reset_index()
    
    for index in range(0, len(trades_to_execute)):
        order_id, log_order = place_order(trades_to_execute['instrument_id'][index], trades_to_execute['price'][index], trades_to_execute['trade'][index])
        order_ids.append(order_id)
        order_dict[trades_to_execute['model'][index]].append(order_id)
        recaps.append(log_order)    
    
    return(order_ids, recaps)
        
def place_order(currency_pair, rate, amount):
    if(amount > 0):
        amount = round(amount,5)
        orderId = p.buy(currency_pair,rate,amount)
        log_msg = 'ORDER PLACED: ID= '+ str(int(orderId['orderNumber']))+'  [BUY '+currency_pair+' '+format(amount, '.10f')+' @ '+format(rate, '.10f')+' ]'
        logger.info(log_msg)
    else:
        amount = round(amount,5)
        orderId = p.sell(currency_pair,rate,amount)
        log_msg = 'ORDER PLACED: ID= '+ str(int(orderId['orderNumber']))+'  [SELL '+currency_pair+' '+format(amount, '.10f')+' @ '+format(rate, '.10f')+' ]'
        logger.info(log_msg)
    return(int(orderId['orderNumber']), log_msg)

def update_positions(current_positions_file):
    balances_raw = p.returnBalances()
    balances = pd.DataFrame.from_dict(balances_raw, orient = 'index').reset_index()
    balances.columns = ['currency', 'current_position']
    balances['model'] = "BTC_TREND_" + balances.currency
    balances = balances.sort_values(by = 'currency')
    balances = balances[['model','currency','current_position']]
    balances.to_csv(current_positions_file, index = False)
    print"Positions file updated"
    
def send_recap_email(trades_today, exec_recaps, capital):
    
    recap = "Capital: "+ format(capital, '.10f') +" BTC \n\nModel Result:\n\n"
    recap = recap + trades_today.to_string()
    recap = recap + '\n\nExecution Recap:\n\n' + "\n".join(item for item in exec_recaps)
    
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.ehlo()
    server.starttls()
    server.login(mail_user, gmail_pwd)
    
    msg = MIMEText(recap)
    
    msg['Subject'] = 'Trading Recap '+ time.strftime("%Y-%m-%d %H:%M:%S")
    msg['From'] = mail_user
    msg['To'] = ", ".join(mail_recipients)
    
    server.sendmail(mail_user, mail_recipients, msg.as_string())
    server.quit()
    
def update_live_prices():
    raw_ticker = p.returnTicker()
    ticker = pd.DataFrame.from_dict(raw_ticker, orient = 'index').reset_index()
    ticker_last = ticker[['index', 'last']]
    ticker_last.columns = ['id', 'last']
    
    models_price = models.merge(ticker_last, how = 'left', on = 'id')
    for index, row in models_price.iterrows():
        pnl_dict[row['model']].update_by_marketdata(float(row['last']))
        print row['model'] + "Updated with price "+row['last']
    print "\n\n\n\n"
    return (ticker_last)
    
def create_pnl_dict(models):
    pnl_dict = {}
    for index, row in models.iterrows():
        pnl_dict[row['model']] = PnlSnapshot(row['instrument'])
    return(pnl_dict)
    
def create_order_dict(models):
    order_dict = {}
    for index, row in models.iterrows():
        order_dict[row['model']] = list()
    return(order_dict)

def update_trades():
    trade_history = p.returnTradeHistory(currencyPair = 'all')
    for index, row in models.iterrows():
        model_order_ids = order_dict[row['model']]
        if row['id'] in trade_history:
            trades_exchange = pd.DataFrame.from_dict(trade_history[row['id']]).reset_index()
            trades_exchange['orderNumber'] = pd.to_numeric(trades_exchange['orderNumber'])
            trades_exchange['globalTradeID'] = pd.to_numeric(trades_exchange['globalTradeID'])
            print "Trades exchange " + trades_exchange.to_string()
            model_trades_exchange = trades_exchange.loc[trades_exchange['orderNumber'].isin(model_order_ids)]
            latest_trade_id = pnl_dict[row['model']].m_latest_trade_id
            trades_to_add = model_trades_exchange[model_trades_exchange['globalTradeID'] > latest_trade_id].sort_values('globalTradeID')
            print "Trades to add" + trades_to_add.to_string()
            for index_trade, row_trade in trades_to_add.iterrows():
                direction = 0
                if(row_trade['type'] == 'buy'):
                    direction = 1
                elif(row_trade['type'] == 'sell'):   
                     direction = -1
                pnl_dict[row['model']].update_by_tradefeed(direction, float(row_trade['rate']), float(row_trade['amount']))
                pnl_dict[row['model']].m_latest_trade_id = row_trade['globalTradeID']
                print row['model']+" PnL updated with "+row_trade['type']+" "+row_trade['amount']+" @ "+ row_trade['rate']

def update_live_pnl():
    update_trades()
    update_live_prices()
        
    
    