def calculate_positions(quandl_id, instrument, logger, config):

####TEST CONFIG
    quandl_id = 'YAHOO/VRX'
    instrument = 'VRX'
    config.read("config/engine.config")
####
    
    
    transaction_cost = float(config.get('AccountSettings', 'transaction_cost'))
    logger.info('Getting Quandl data quandl_id='+quandl_id)
    data = getHistoricalData(quandl_id, logger)    
    
    close = data[['Close']]['1/1/2010':]
    logger.info('Calculating percentage changes quandl_id='+ quandl_id)
    close['pct_change'] = close.pct_change()
    
    volatility_window = float(config.get('StrategySettings', 'volatility_window'))
    logger.info('Calculating '+ str(volatility_window) +'-day volatility quandl_id='+quandl_id)
    close['vol'] = pd.rolling_std(close['pct_change'], volatility_window)
    
    logger.info('Calculating 20-day moving average quandl_id='+ quandl_id)
    ma20 = movingaverage(close['Close'] , 20)
    logger.info('Calculating 50-day moving average quandl_id='+ quandl_id)
    ma100 = movingaverage(close['Close'] , 100)
    close['ma20'] = pad(ma20, len(close) - ma20.size, float('nan'))
    close['ma100'] = pad(ma100, len(close) - ma100.size, float('nan'))
    
    logger.info('Calculating historical signals quandl_id='+quandl_id)
    close['signal'] = np.sign(close['ma20'] - close['ma100'])
    close['signal'][np.isnan(close['signal'])] = 0

    logger.info('Calculating historical positions quandl_id='+ quandl_id)
    close['position'] = close.apply(lambda row: trade_size(row['signal'], capital, row['vol'], row['Close']), axis=1)
    close['position'][np.isnan(close['position'])] = 0
    
    if store_positions:
        store_positions(close, positions_path, instrument, quandl_id, logger)
        
    close['trade'] = close[['position']].diff()

    close['notional'] = close.apply(lambda row: abs(row['position'] * row['Close']) , axis=1)

    close['transaction_cost'] = close.apply(lambda row: abs(row['trade'] * transaction_cost) , axis=1)
    
    transaction_costs = close['transaction_cost'].values
    
    close = update_pnl(close, instrument, slippage, capital)
    plot_pnl(close,instrument)
    
    risk_free_rate = float(config.get('StrategySettings', 'risk_free_rate'))
    
    logger.info('Calculating sharpe ratio quandl_id='+ quandl_id)    
    sharpe_ratio = annualised_sharpe(close['daily_pnl_pct'], risk_free_rate = risk_free_rate)
    logger.info('Sharpe ratio = ' + str(sharpe_ratio) + ' quandl_id='+ quandl_id)    
    
    #logger.info('Calculating daily drawdown quandl_id='+ quandl_id)    
    #drawdown = daily_drawdown(close['pnl'])
    #plt.figure()
    #plt.plot(drawdown)
    
    logger.info('Calculating gearing factor with vol target = '+ str(vol_target) +' quandl_id='+ quandl_id)    
    gearing_factor = calculate_model_gearing(close['pnl'], capital = capital, vol_target = vol_target )
    
    logger.info('Apply gearing factor = '+ str(gearing_factor) +' quandl_id='+ quandl_id)    
    close = apply_model_gearing(close, gearing_factor, instrument, capital)
    
    plot_pnl(close,instrument)
    
    
    
        