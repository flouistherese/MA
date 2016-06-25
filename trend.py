def calculate_positions(model, instrument_id, instrument, capital_allocated, logger, config):
    pd.options.mode.chained_assignment = None  # default='warn'
    
###TEST CONFIG
#    model = 'BTC_TREND_LTC'
#    instrument_id = 'BTC_LTC'
#    instrument = 'BTC_LTC'
#    instrument_type = 'BTC_PAIR'
#    point_value = 1
    config.read("config/engine.config")
#    capital_allocated = 10
####
    logger.info('Downloading data for instrument_id='+ instrument_id)
    data = getHistoricalData(instrument_id)

    close = data[['Last']]*base_multiplier
    close.columns = ['close']
    close['model'] = model
    close['instrument_id'] = instrument_id
    
    close = generate_signal(close, instrument_id)
    position_today = close.tail(1)
    position_today.loc[:,('position')] = close.tail(1).apply(lambda row: trade_size(row['signal'], capital_allocated, row['close']), axis=1)
    
    return (position_today[['model', 'close', 'instrument_id', 'position']])
