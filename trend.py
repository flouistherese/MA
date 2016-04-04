def calculate_positions(model, quandl_id, instrument, logger, config):

####TEST CONFIG
#    model = 'EQUITY_TREND_FB'
#    quandl_id = 'YAHOO/QCOM'
#    instrument = 'QCOM'
#    config.read("config/engine.config")
####
    
    logger.info('Getting Quandl data quandl_id='+quandl_id)
    data = getHistoricalData(quandl_id, logger)    
    
    close = data[['Adjusted Close']]['1/1/2005':]
    close.columns = ['close']
    
    volatility_window = float(config.get('StrategySettings', 'volatility_window'))
    logger.info('Calculating '+ str(volatility_window) +'-day volatility quandl_id='+quandl_id)
    close['vol'] = calculate_volatility(close, volatility_window)
    
    close = generate_signal(close, quandl_id)

    logger.info('Calculating historical positions quandl_id='+ quandl_id)
    close['position'] = calculate_historical_positions(close) 
    
    if store_positions:
        store_positions(close, positions_path, instrument, quandl_id, logger)
        
    close['trade'] = close[['position']].diff()
    
    logger.info('Calculating notional positions quandl_id='+ quandl_id)
    close['notional'] = calculate_notional_positions(close)

    logger.info('Calculating transaction costs quandl_id='+ quandl_id)
    close['transaction_cost'] = calculate_transaction_costs(close, transaction_cost)
    
    logger.info('Calculating ungeared pnl quandl_id='+ quandl_id)
    close = update_pnl(close, instrument, slippage, capital)
    
    #plot_pnl(close,instrument)
    
    logger.info('Calculating gearing factor with vol target = '+ str(vol_target) +' quandl_id='+ quandl_id)    
    gearing_factor = calculate_model_gearing(close['pnl'], capital = capital, vol_target = vol_target )
    
    logger.info('Apply gearing factor = '+ str(gearing_factor) +' quandl_id='+ quandl_id)    
    close = apply_model_gearing(close, gearing_factor, instrument, capital)
    
    risk_free_rate = float(config.get('StrategySettings', 'risk_free_rate'))
    
    logger.info('Calculating sharpe ratio quandl_id='+ quandl_id)    
    sharpe_ratio = annualised_sharpe(close['daily_pnl_pct'], risk_free_rate = risk_free_rate)
    logger.info('Sharpe ratio = ' + str(sharpe_ratio) + ' quandl_id='+ quandl_id)    
    
    logger.info('Calculating daily drawdown quandl_id='+ quandl_id)    
    drawdown = daily_drawdown(close['pnl'])
    #plot_drawdown(drawdown)
    
    
    #plot_pnl(close,model)
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
    logger.info('Calculating 20-day moving average quandl_id='+ quandl_id)
    ma50 = movingaverage(data['close'] , 50)
    logger.info('Calculating 50-day moving average quandl_id='+ quandl_id)
    ma100 = movingaverage(data['close'] , 100)
    data['ma50'] = pad(ma50, len(data) - ma50.size, float('nan'))
    data['ma100'] = pad(ma100, len(data) - ma100.size, float('nan'))
    
    logger.info('Calculating historical signals quandl_id='+quandl_id)
    data['signal'] = np.sign(data['ma50'] - data['ma100'])
    data['signal'][np.isnan(data['signal'])] = 0
    
    return data