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
models = pd.read_csv(config.get('StrategySettings','models_path'), sep=',')
vol_target = float(config.get('AccountSettings','volatility_target'))
slippage = float(config.get('StrategySettings','slippage'))
transaction_cost = float(config.get('AccountSettings', 'transaction_cost'))
store_positions = config.getboolean('StrategySettings','store_positions')
positions_path = config.get('StrategySettings','positions_path')
signals_path = config.get('StrategySettings','signals_path')

positions = pd.DataFrame()
notionals = pd.DataFrame()
pnl = pd.DataFrame()
models_reduced = models[1:20]

for index, row in models_reduced.iterrows():
    logger.info('Processing '+ row['model'] +' '+row['instrument_type']+' '+ row['instrument']+' quandl_id='+row['quandl_id'])
    result = calculate_positions(row['model'], row['quandl_id'], row['instrument'], logger, config)
    positions = pd.concat([positions, result.positions])
    notionals = pd.concat([notionals, result.notionals])
    pnl = pd.concat([pnl, result.pnl])
    
plot_pnl_by_model(pnl)
    
plot_total_pnl(pnl)