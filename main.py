import os
os.chdir('H:/Dropbox/Dropbox/Code/Python/strategies/MA/')

execfile('imports.py')
execfile('common.py')
execfile('trend.py')
execfile('pnl_snapshot.py')
%matplotlib qt

config = ConfigParser.ConfigParser()
config.read("config/engine.config")
logger = createLogger(config.get('ConfigSettings','logfile_path'))

logger.info('\n\n\n\n\nStarting engine')
capital = float(config.get('AccountSettings','capital'))
markets = pd.read_csv(config.get('StrategySettings','markets_path'), sep=',')
vol_target = float(config.get('AccountSettings','volatility_target'))
slippage = float(config.get('StrategySettings','slippage'))
store_positions = config.getboolean('StrategySettings','store_positions')
positions_path = config.get('StrategySettings','positions_path')
signals_path = config.get('StrategySettings','signals_path')

for index, row in markets.iterrows():
    logger.info('Processing '+row['instrument_type']+' '+ row['instrument']+' quandl_id='+row['quandl_id'])
    calculate_positions(row['quandl_id'], row['instrument'], logger, config)

