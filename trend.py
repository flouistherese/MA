def calculate_positions(model, quandl_id, instrument, point_value, logger, config):

    pd.options.mode.chained_assignment = None  # default='warn'

####TEST CONFIG
#    model = 'COMMODITY_TREND_TY'
#    quandl_id = 'CHRIS/CME_TY1'
#    instrument = 'TY1'
#    point_value = 1000
#    config.read("config/engine.config")
####
    
    logger.info('Getting Quandl data quandl_id='+quandl_id)
    if live_data_enabled:
        logger.info('Downloading data from Quandl quandl_id='+ quandl_id)
        data = getHistoricalData(quandl_id, logger)    
    else:
        file_path = market_data_dir + instrument +'.csv'
        logger.info('Reading data from '+file_path+' quandl_id='+ quandl_id)
        data = pd.DataFrame.from_csv(file_path)
    
    if store_market_data:
        file_path= market_data_dir + instrument +'.csv'
        logger.info('Storing data to '+file_path+' quandl_id='+ quandl_id)
        data.to_csv(file_path)
        
    data = data['1/1/2005':]
    
    ATR = calculate_average_true_range(data, atr_period)
    
    close = data[['Last']]
    close.columns = ['close']
    
    volatility_window = float(config.get('StrategySettings', 'volatility_window'))
    logger.info('Calculating '+ str(volatility_window) +'-day volatility quandl_id='+quandl_id)
    close.loc[:,('vol')] = calculate_pct_volatility(close.loc[:,('close')], volatility_window)
    close.loc[:,('vol')] = calculate_change_volatility(close.loc[:,('close')], volatility_window)
    
    close.loc[:,('ATR')] = ATR
    close = generate_signal(close, quandl_id)

    logger.info('Calculating historical positions quandl_id='+ quandl_id)
    close['position'] = calculate_historical_positions(close, point_value) 
    
    if store_positions:
        store_positions(close, positions_path, instrument, quandl_id, logger)
        
    close['trade'] = close[['position']].diff()
    
    logger.info('Calculating notional positions quandl_id='+ quandl_id)
    close['notional'] = calculate_notional_positions(close, point_value)

    logger.info('Calculating transaction costs quandl_id='+ quandl_id)
    close['transaction_cost'] = calculate_transaction_costs(close, transaction_cost)
    
    logger.info('Calculating ungeared pnl quandl_id='+ quandl_id)
    close = update_pnl(close, instrument, point_value, slippage, capital)
    
    #plot_pnl(close,instrument)
    
    logger.info('Calculating gearing factor with vol target = '+ str(vol_target) +' quandl_id='+ quandl_id)    
    gearing_factor = calculate_model_gearing(close['pnl'], capital = capital, vol_target = vol_target )
    
    logger.info('Apply gearing factor = '+ str(gearing_factor) +' quandl_id='+ quandl_id)    
    close = apply_model_gearing(close, gearing_factor, instrument, point_value, capital)
    
    risk_free_rate = float(config.get('StrategySettings', 'risk_free_rate'))
    
    logger.info('Calculating sharpe ratio quandl_id='+ quandl_id)    
    sharpe_ratio = annualised_sharpe(close['daily_pnl_pct'], risk_free_rate = risk_free_rate)
    logger.info('Sharpe ratio = ' + str(sharpe_ratio) + ' quandl_id='+ quandl_id)    
    
    logger.info('Calculating daily drawdown quandl_id='+ quandl_id)    
    drawdown = daily_drawdown(close['pnl'])
    #plot_drawdown(drawdown)
    
    
    #plot_pnl(close,model)
    #plot_pnl_atr(close,model)
    date_range = pd.date_range(close.index.min(),close.index.max())
    close = close.reindex(date_range)
    close['close'] = close['close'].fillna(method='pad')
    close['position'] = close['position'].fillna(method='pad')
    close['notional'] = close['notional'].fillna(method='pad')
    close['pnl'] = close['pnl'].fillna(method='pad')
     
    close['model'] = model

    model_run_result = collections.namedtuple('ModelRunResult', ['positions', 'notionals', 'pnl'])
    
    return model_run_result(positions = close[['model', 'position']], notionals = close[['model', 'notional']], pnl = close[['model', 'pnl']])
    
    
def generate_signal(data, quandl_id):
    ma1 = int(config.get('StrategySettings','ma1'))
    ma2 = int(config.get('StrategySettings','ma2'))
    logger.info('Calculating '+str(ma1)+'-day moving average quandl_id='+ quandl_id)
    ma1 = movingaverage(data['close'] , ma1)
    logger.info('Calculating '+str(ma2)+'-day moving average quandl_id='+ quandl_id)
    ma2 = movingaverage(data['close'] , ma2)
    data['ma1'] = pad(ma1, len(data) - ma1.size, float('nan'))
    data['ma2'] = pad(ma2, len(data) - ma2.size, float('nan'))
    
    logger.info('Calculating historical signals quandl_id='+quandl_id)
    data['signal'] = data['ma1'] - data['ma2']
    if use_atr:
        data.ix[abs(data.signal)< (data.ATR * number_atr), 'signal'] = 0
    data['signal'][np.isnan(data['signal'])] = 0
    data['signal'] = np.sign(data['signal'])
    
    return data