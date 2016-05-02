def calculate_positions(model, instrument_id, instrument, instrument_type, point_value, logger, config):

    pd.options.mode.chained_assignment = None  # default='warn'

####TEST CONFIG
#    model = 'BTC_TREND_XEM'
#    instrument_id = 'BTC_XEM'
#    instrument = 'BTC_XEM'
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
    
    logger.info('Calculating gearing factor with vol target = '+ str(vol_target) +' instrument_id='+ instrument_id)    
    gearing_factor = calculate_model_gearing(close['pnl'], capital = capital, vol_target = vol_target )
    
    logger.info('Apply gearing factor = '+ str(gearing_factor) +' instrument_id='+ instrument_id)    
    close = apply_model_gearing(close, gearing_factor, instrument, point_value, capital)
    
    close = apply_limits(close, instrument, point_value, slippage, capital, limits)
    
    risk_free_rate = float(config.get('StrategySettings', 'risk_free_rate'))
    
    logger.info('Calculating sharpe ratio instrument_id='+ instrument_id)    
    sharpe_ratio = annualised_sharpe(close['daily_pnl_pct'], risk_free_rate = risk_free_rate)
    logger.info('Sharpe ratio = ' + str(sharpe_ratio) + ' instrument_id='+ instrument_id)    
    
    logger.info('Calculating daily drawdown instrument_id='+ instrument_id)    
    drawdown = daily_drawdown(close['pnl'])
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
    logger.info('Calculating '+str(ma1)+'-day moving average instrument_id='+ instrument_id)
    ma1 = movingaverage(data['close'] , ma1)
    logger.info('Calculating '+str(ma2)+'-day moving average instrument_id='+ instrument_id)
    ma2 = movingaverage(data['close'] , ma2)
    data['ma1'] = pad(ma1, len(data) - ma1.size, float('nan'))
    data['ma2'] = pad(ma2, len(data) - ma2.size, float('nan'))
    
    logger.info('Calculating historical signals instrument_id='+instrument_id)
    data['signal'] = data['ma1'] - data['ma2']
    if use_atr:
        #How many std dev away from the mean
        data['atr_coefficient'] = np.ceil(abs(data.ATR - data.ATR_mean)/data.ATR_std)
        data.ix[abs(data.signal)< (data.ATR * data['atr_coefficient']), 'signal'] = 0
    data['signal'][np.isnan(data['signal'])] = 0
    data['signal'] = np.sign(data['signal'])
    
    return data