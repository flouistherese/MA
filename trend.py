def calculate_positions(quandl_id, instrument, logger):
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
    
    close
    
    plt.ion()
    plt.plot(close['Close'], ls = '-')
    plt.plot(close['ma20'], ls = '-')
    #plt.plot(close['ma50'], ls = '-')
    plt.plot(close['ma100'], ls = '-')
    #plt.plot(close['ma200'], ls = '-')
    plt.plot(close['signal'], ls='-')
    plt.show()
    
    logger.info('Calculating historical positions quandl_id='+ quandl_id)
    close['position'] = close.apply(lambda row: trade_size(row['signal'], capital, row['10d_vol']), axis=1)
    
    positions_directory_path = positions_path + strftime("%Y-%m-%d")
    if not os.path.exists(positions_directory_path):
        os.makedirs(positions_directory_path)
    close.to_csv(positions_directory_path + '/' + instrument + '_' + strftime("%Y-%m-%d_%H-%M-%S") + '.csv',mode  = 'w+')