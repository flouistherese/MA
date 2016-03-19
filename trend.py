def calculate_positions(quandl_id, instrument, logger, config):

    quandl_id = 'YAHOO/FB'
    instrument = 'FB'

    transaction_cost = float(config.get('AccountSettings', 'transaction_cost'))
    logger.info('Getting Quandl data quandl_id='+quandl_id)
    data = getHistoricalData(quandl_id, logger)    
    
    close = data[['Close']]['1/1/2010':]
    logger.info('Calculating percentage changes quandl_id='+ quandl_id)
    close['pct_change'] = close.pct_change()
    logger.info('Calculating volatility quandl_id='+quandl_id)
    close['10d_vol'] = pd.rolling_std(close['pct_change'], 10)
    
    logger.info('Calculating 20-day moving average quandl_id='+ quandl_id)
    ma20 = movingaverage(close['Close'] , 20)
    #ma50 = movingaverage(close['Close'] , 50)
    logger.info('Calculating 50-day moving average quandl_id='+ quandl_id)
    ma100 = movingaverage(close['Close'] , 100)
    #ma200 = movingaverage(close['Close'] , 200)
    close['ma20'] = pad(ma20, len(close) - ma20.size, float('nan'))
    #close['ma50'] = pad(ma50, len(close) - ma50.size, float('nan'))
    close['ma100'] = pad(ma100, len(close) - ma100.size, float('nan'))
    #close['ma200'] = pad(ma200, len(close) - ma200.size, float('nan'))
    
    logger.info('Calculating historical signals quandl_id='+quandl_id)
    close['signal'] = np.sign(close['ma20'] - close['ma100'])
    close['signal'][np.isnan(close['signal'])] = 0
    
    #plot_signals(close)

    logger.info('Calculating historical positions quandl_id='+ quandl_id)
    close['position'] = close.apply(lambda row: trade_size(row['signal'], capital, row['10d_vol'], row['Close']), axis=1)
    close['position'][np.isnan(close['position'])] = 0
    
    if store_positions:
        store_positions(close, positions_path, instrument, quandl_id, logger)
        
    close['trade'] = close[['position']].diff()

    close['notional'] = close.apply(lambda row: abs(row['position'] * row['Close']) , axis=1)

    close['transaction_cost'] = close.apply(lambda row: abs(row['trade'] * transaction_cost) , axis=1)
    
    
    transaction_costs = close['transaction_cost'].values
    
    pnl = calculate_pnl(close,instrument)
    
    close['pnl'] = pad(pnl, len(close) - pnl.size, float(0))
    
    plot_pnl(close)
        