# -*- coding: utf-8 -*-
"""
Created on Sat Jun 25 14:57:16 2016

@author: Florian
"""

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

def backtest(model, instrument_id, instrument, instrument_type, point_value, logger, config):
    
    pd.options.mode.chained_assignment = None  # default='warn'

###TEST CONFIG
#    model = 'BTC_TREND_LTC'
#    instrument_id = 'BTC_LTC'
#    instrument = 'BTC_LTC'
#    instrument_type = 'BTC_PAIR'
#    point_value = 1
#    config.read("config/engine.config")
#    use_atr = True
####
    
    logger.info('Getting Quandl data instrument_id='+instrument_id)
    if live_data_enabled:
        logger.info('Downloading data for instrument_id='+ instrument_id)
        data = getHistoricalData(instrument_id, instrument_type, logger)    
    else:
        file_path = market_data_dir + instrument +'.csv'
        logger.info('Reading data from '+file_path+' instrument_id='+ instrument_id)
        data = pd.DataFrame.from_csv(file_path)
    
    if store_market_data:
        file_path= market_data_dir + instrument +'.csv'
        logger.info('Storing data to '+file_path+' instrument_id='+ instrument_id)
        data.to_csv(file_path)
        
    data = data['1/1/2005':]
    
    ATR = calculate_average_true_range(data, atr_period)
    
    close = data[['Last']]
    close.columns = ['close']
    close['model'] = model
    close['instrument_id'] = instrument_id
    
    close = historical_atr_gaussian_fitting(close, ATR)
    
    volatility_window = float(config.get('StrategySettings', 'volatility_window'))
    logger.info('Calculating '+ str(volatility_window) +'-day volatility instrument_id='+instrument_id)
    close.loc[:,('vol')] = calculate_pct_volatility(close.loc[:,('close')], volatility_window)
    #close.loc[:,('vol')] = calculate_change_volatility(close.loc[:,('close')], volatility_window)
    
    close = generate_signal(close, instrument_id)

    logger.info('Calculating historical positions instrument_id='+ instrument_id)
    close['position'] = calculate_historical_positions(close, point_value) 
    
    if store_sim_positions:
        store_sim_positions(close, sim_positions_path, instrument, instrument_id, logger)
        
    close['trade'] = close[['position']].diff()
    
    logger.info('Calculating notional positions instrument_id='+ instrument_id)
    close['notional'] = calculate_notional_positions(close, point_value)

    logger.info('Calculating transaction costs instrument_id='+ instrument_id)
    close['transaction_cost'] = calculate_transaction_costs(close, transaction_cost)
    #close['transaction_cost'] = 0
    
    logger.info('Calculating ungeared pnl instrument_id='+ instrument_id)
    close = update_pnl(close, instrument, point_value, slippage, capital)
    
    #plot_pnl(close,instrument)
    if geared:
        logger.info('Calculating gearing factor with vol target = '+ str(vol_target) +' instrument_id='+ instrument_id)    
        gearing_factor = calculate_model_gearing(close['pnl'], capital = capital, vol_target = vol_target )
        
        logger.info('Apply gearing factor = '+ str(gearing_factor) +' instrument_id='+ instrument_id)    
        close = apply_model_gearing(close, gearing_factor, instrument, point_value, capital)
    
    #close = apply_limits(close, instrument, point_value, slippage, capital, limits)
    
   # risk_free_rate = float(config.get('StrategySettings', 'risk_free_rate'))
    
    #logger.info('Calculating sharpe ratio instrument_id='+ instrument_id)    
    #sharpe_ratio = annualised_sharpe(close['daily_pnl_pct'], risk_free_rate = risk_free_rate)
    #logger.info('Sharpe ratio = ' + str(sharpe_ratio) + ' instrument_id='+ instrument_id)    
    
    #logger.info('Calculating daily drawdown instrument_id='+ instrument_id)    
    #drawdown = daily_drawdown(close['pnl'])
    #plot_drawdown(drawdown)
    
    #plot_pnl(close,model)
    #plot_pnl_atr(close,model)
    date_range = pd.date_range(close.index.min(),close.index.max())
    close = close.reindex(date_range)
    close['close'] = close['close'].fillna(method='pad')
    close['position'] = close['position'].fillna(method='pad')
    close['notional'] = close['notional'].fillna(method='pad')
    close['trade'] = close['trade'].fillna(method='pad')
    close['pnl'] = close['pnl'].fillna(method='pad')
     
    model_run_result = collections.namedtuple('ModelRunResult', ['positions', 'notionals', 'trades', 'pnl'])
    
    return model_run_result(positions = close[['model', 'close', 'instrument_id', 'position']], notionals = close[['model', 'instrument_id', 'notional']], trades = close[['model', 'close', 'instrument_id', 'trade']], pnl = close[['model', 'instrument_id', 'pnl']])
    
    
def generate_signal(data, instrument_id):
    ma1 = int(config.get('StrategySettings','ma1'))
    ma2 = int(config.get('StrategySettings','ma2'))
    logger.debug('Calculating '+str(ma1)+'-day moving average instrument_id='+ instrument_id)
    ma1 = movingaverage(data['close'] , ma1)
    logger.debug('Calculating '+str(ma2)+'-day moving average instrument_id='+ instrument_id)
    ma2 = movingaverage(data['close'] , ma2)
    data['ma1'] = pad(ma1, len(data) - ma1.size, float('nan'))
    data['ma2'] = pad(ma2, len(data) - ma2.size, float('nan'))
    
    logger.debug('Calculating historical signals instrument_id='+instrument_id)
    data['signal'] = data['ma1'] - data['ma2']

    data['signal'][np.isnan(data['signal'])] = 0
    data['signal'] = np.sign(data['signal'])
    
    return data
    
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