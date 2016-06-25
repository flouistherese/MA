api_key = "JyPzgcScbDfyY5H-mVhM"

def createLogger(logfile_path):
    logger = logging.getLogger('myapp')
    hdlr = logging.FileHandler(logfile_path)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr) 
    logger.setLevel(logging.INFO)
    return logger
    
def getHistoricalData(ticker):  
    data = p.returnChartData(currencyPair = ticker, start = int(time.time()) - 3600 * 24 *365)
    data.columns = ['Last', 'High', 'Low','Open','quoteVolume', 'volume', 'weightedAverage']
    return data
    
def movingaverage (values, window):
    weights = np.repeat(1.0, window)/window
    sma = np.convolve(values, weights, 'valid')
    return sma
    
def pad(array, width, value):
    return np.lib.pad(array, (width,0), mode = 'constant', constant_values= value)
    
def trade_size(signal, capital, price):
    #return round(0.001 * signal * capital / (vol*point_value))
    #return round(signal * capital / (vol*point_value))
    return(round( (signal * capital / price) * base_multiplier))
    
def store_positions(close, positions_path, instrument, instrument_id, logger):
    positions_directory_path = positions_path + strftime("%Y-%m-%d")
    if not os.path.exists(positions_directory_path):
        os.makedirs(positions_directory_path)
    positions_file_path = positions_directory_path + '/' + instrument + '_' + strftime("%Y-%m-%d_%H-%M-%S") + '.csv'
    logger.info('Storing positions to '+positions_file_path+' instrument_id='+ instrument_id)
    close[['close','position']].to_csv(positions_file_path,mode  = 'w+')


def calculate_pct_volatility(price, window):
    pct_change = price.pct_change()
    return pd.rolling_std(pct_change, window)

def calculate_change_volatility(price, window):
    change = price.diff()
    return pd.rolling_std(change, window)
    
def calculate_historical_positions(data, point_value):
    positions = data.apply(lambda row: trade_size(row['signal'], capital, row['vol'], row['close'], point_value, nb_models), axis=1)
    positions[np.isnan(positions)] = 0
    return positions

def calculate_notional_positions(data, point_value):
    return data.apply(lambda row: row['position'] * row['close'] * point_value , axis=1)
    
def calculate_transaction_costs(data, transaction_cost):
    return data.apply(lambda row: abs(row['trade'] * row['close'] * transaction_cost) , axis=1)
    
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

def generate_trades(current_positions_file, position_today):
    current_positions = pd.DataFrame.from_csv(current_positions_file,index_col = None)
    position_today.columns = ['model', 'price', 'instrument_id', 'target_position']
    position_today = position_today.merge(current_positions, how='left', on = 'model' )
    position_today['trade'] = position_today.target_position - position_today.current_position
    if(long_only):
        position_today['trade'] = np.where(position_today.trade + position_today.current_position < 0 , -1 * position_today.current_position , position_today.trade)
    return(position_today)
    
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
        price = round(trades_to_execute['price'][index] * 1/base_multiplier,8)
        amount = round(trades_to_execute['trade'][index] * 1/base_multiplier,8)
        order_id, log_order = place_order(trades_to_execute['model'][index], trades_to_execute['instrument_id'][index], price, amount)
        order_ids.append(order_id)
        order_dict[trades_to_execute['model'][index]].append(order_id)
        recaps.append(log_order)    
    
    return(order_ids, recaps)
        
def place_order(model, currency_pair, rate, amount):
    if(amount > 0):
        amount = round(amount,8)
        orderResult = p.buy(currency_pair,rate,amount)
        logger.info(orderResult)
        log_msg = 'ORDER PLACED: ID= '+ str(int(orderResult['orderNumber']))+'  [BUY '+currency_pair+' '+format(amount, '.10f')+' @ '+format(rate, '.10f')+' ]'
        logger.info(log_msg)
    else:
        amount = round(amount,8)
        orderResult = p.sell(currency_pair,rate,abs(amount))
        logger.info(orderResult)
        log_msg = 'ORDER PLACED: ID= '+ str(int(orderResult['orderNumber']))+'  [SELL '+currency_pair+' '+format(amount, '.10f')+' @ '+format(rate, '.10f')+' ]'
        logger.info(log_msg)
    print "Received: "+pd.DataFrame.from_dict(orderResult).to_string()
    add_to_order_file(model, int(orderResult['orderNumber']), currency_pair, rate, amount)
    return(int(orderResult['orderNumber']), log_msg)

def update_positions():
    balances_raw = p.returnBalances()
    balances = pd.DataFrame.from_dict(balances_raw, orient = 'index').reset_index()
    balances.columns = ['currency', 'current_position']
    balances['model'] = "BTC_TREND_" + balances.currency
    balances = balances.sort_values(by = 'currency')
    balances = balances[['model','currency','current_position']]
    balances = balances[balances['model'].isin(models['model'])]
    balances['current_position'] = balances['current_position'].values.astype(np.float) * base_multiplier
    balances.to_csv(current_positions_file, index = False)
    print "Positions file updated"
    
def send_recap_email(trades_today, exec_recaps, capital, pnl_dict):
    
    recap = "Capital: "+ format(capital, '.10f') +" BTC \n\nModel Result:\n\n"
    recap = recap + trades_today.to_string()
    recap = recap + '\n\nExecution Recap:\n\n' + "\n".join(item for item in exec_recaps)
    recap = recap + "\n\n"
    for model in pnl_dict:
        recap = recap + pnl_dict[model].to_string() + "\n\n"
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
        pnl_dict[row['model']].update_by_marketdata(float(row['last']) * base_multiplier)
        #print row['model'] + " updated with price "+row['last']
    #print "\n\n"
    return (ticker_last)
    
def create_pnl_dict(models):
    pnl_dict = {}
    for index, row in models.iterrows():
        pnl_dict[row['model']] = PnlSnapshot(row['model'])
    return(pnl_dict)
    
def create_order_dict(models, order_file_path):
    order_dict = {}
    previous_orders = pd.DataFrame.from_csv(order_file_path)
    for index, row in models.iterrows():
        previous_model_orders = previous_orders[previous_orders['model'] == row['model']]
        order_dict[row['model']] = previous_model_orders['order_number'].tolist()

    return(order_dict)

def update_trades():
    #Get trade history from exchange
    trade_history = p.returnTradeHistory(currencyPair = 'all')
    for index, row in models.iterrows():
        model_order_ids = order_dict[row['model']]
        if row['id'] in trade_history: #Get trades who have matching instrument
            trades_exchange = pd.DataFrame.from_dict(trade_history[row['id']]).reset_index()
            trades_exchange['orderNumber'] = pd.to_numeric(trades_exchange['orderNumber'])
            trades_exchange['globalTradeID'] = pd.to_numeric(trades_exchange['globalTradeID'])
            #print "Trades exchange " + trades_exchange.to_string()
            model_trades_exchange = trades_exchange.loc[trades_exchange['orderNumber'].isin(model_order_ids)] #Get trades which have an orderNumber matching an order entered for this model
            latest_trade_id = pnl_dict[row['model']].m_latest_trade_id #Get last trade added to Pnl Calculation
            trades_to_add = model_trades_exchange[model_trades_exchange['globalTradeID'] > latest_trade_id].sort_values('globalTradeID') #Get trades that occured later that latest added trade
            trades_to_add['amount'] = trades_to_add['amount'].values.astype(np.float) * base_multiplier
            trades_to_add['rate'] = trades_to_add['rate'].values.astype(np.float) * base_multiplier
            if len(trades_to_add) > 0:
                print "Trades to add: \n" + trades_to_add.to_string()+"\n\n"
            for index_trade, row_trade in trades_to_add.iterrows():
                direction = 0
                amount_after_fee = round(row_trade['amount'])
                rate_after_fee = round(row_trade['rate'])
                if(row_trade['type'] == 'buy'):
                    direction = 1
                    amount_after_fee = round(amount_after_fee * (1.0 - float(row_trade['fee'])))
                elif(row_trade['type'] == 'sell'):   
                    direction = -1
                    rate_after_fee = round(rate_after_fee * (1.0 - float(row_trade['fee'])))
                pnl_dict[row['model']].update_by_tradefeed(direction, rate_after_fee, amount_after_fee) #Add each of those trades to PnL
                pnl_dict[row['model']].m_latest_trade_id = row_trade['globalTradeID'] #Update last trade id
                print row['model']+" PnL updated with "+row_trade['type']+" "+format(amount_after_fee, '.20f')+" @ "+ str(rate_after_fee)
                print row['model']+" net position = " + format(pnl_dict[row['model']].m_net_position, '.20f')+"\n"

def update_live_pnl():
    update_trades()
    update_live_prices()
    update_positions()
    pnl_dataframes = []
    for key in pnl_dict:  
        pnl_dataframes.append(pnl_dict[key].to_data_frame())
        actual_pnl = round(pnl_dict[key].m_total_pnl / (base_multiplier * base_multiplier), 8) 
        print "PnL "+key+": "+ str(actual_pnl)+" BTC"
    print "\n"   
    pnl = pd.concat(pnl_dataframes)
    pnl.to_csv(pnl_file_path, index = False)
    
    
def add_to_order_file(model, order_number, currency_pair, rate, amount):
    orders = pd.DataFrame.from_csv(order_file_path,index_col = None)
    new_order = pd.DataFrame(np.array([[time.strftime("%Y-%m-%d %H:%M:%S"), model, str(order_number), currency_pair, format(rate, '.10f'), format(amount, '.10f')]]), columns=['time', 'model', 'order_number', 'instrument_id', 'price', 'amount'])
    orders = orders.append(new_order)
    orders.to_csv(order_file_path, index = False)

def remove_from_order_file(order_number):
    orders = pd.DataFrame.from_csv(order_file_path,index_col = None)
    orders = orders[orders.order_number != order_number]
    orders.to_csv(order_file_path, index = False)
    
    
def get_capital(capital_path):
    balances_raw = p.returnBalances()
    btc_cash = float(balances_raw['BTC']) * base_multiplier 
    btc_assets = 0
    for key in pnl_dict:    
        btc_assets = btc_assets + (pnl_dict[key].m_net_position * pnl_dict[key].m_avg_open_price)
    btc_capital = btc_cash + btc_assets
#    capitals = pd.DataFrame.from_csv(capital_path)
    return (btc_capital)
    
def withdraw_open_orders():
    open_orders = p.returnOpenOrders()
    currencies = dict( (key, value) for (key, value) in open_orders.items() if len(value) > 0 ).keys()
    for currencyPair in currencies:
        orders = pd.DataFrame.from_dict(open_orders[currencyPair])
        for orderNumber in orders['orderNumber']:
            result = p.cancel(currencyPair, int(orderNumber))
            if result['success'] != 1:
                logger.info("Failed to cancel order "+str(orderNumber)+", received result: "+result.to_string()+"\n")
            else:
                remove_from_order_file(int(orderNumber))
                logger.info("Order "+orderNumber+" successfully cancelled\n")
                
                
def close_all_positions():
    update_live_pnl()
    withdraw_open_orders()
    current_positions = pd.DataFrame.from_csv(current_positions_file,index_col = None)
    raw_ticker = p.returnTicker()
    ticker = pd.DataFrame.from_dict(raw_ticker, orient = 'index')
    for index, row in current_positions.iterrows():
        
        if row['current_position'] > 0.0001:
            currencyPair = models.loc[models.model == row['model']].reset_index()['instrument'][0]
            if row['current_position'] > 0:
                price = float(ticker.loc[str(currencyPair)]['highestBid'])
            else:
                price = float(ticker.loc[str(currencyPair)]['lowestAsk'])
            amount = round(row['current_position'] * 1/base_multiplier,8)
            print row['model'] + "cur = "+str(row['current_position'])+" price = "+str(price)+" pos = "+ str(amount)
            order_id, log_order = place_order(row['model'], currencyPair, price, -1 * amount)
            order_dict[row['model']].append(order_id)
    
    
    
    
    
    