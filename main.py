

execfile('H:/Dropbox/Dropbox/Code/Python/strategies/MA/imports.py')
execfile('H:/Dropbox/Dropbox/Code/Python/strategies/MA/common.py')
execfile('H:/Dropbox/Dropbox/Code/Python/strategies/MA/trend.py')
%matplotlib qt

config = ConfigParser.ConfigParser()
config.read("H:/Dropbox/Dropbox/Code/Python/strategies/MA/config/engine.config")
logger = createLogger(config.get('ConfigSettings','logfile_path'))

logger.info('\n\n\n\n\nStarting engine')
capital = float(config.get('AccountSettings','capital'))
markets = pd.read_csv(config.get('StrategySettings','markets_path'), sep=',')
positions_path = config.get('StrategySettings','positions_path')

for index, row in markets.iterrows():
    logger.info('Processing '+row['instrument_type']+' '+ row['instrument']+' quandl_id='+row['quandl_id'])
    calculate_positions(row['quandl_id'], row['instrument'], logger)

