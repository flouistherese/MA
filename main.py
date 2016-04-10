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
live_data_enabled = config.getboolean('ConfigSettings','live_data_enabled')
store_market_data = config.getboolean('ConfigSettings','store_market_data')
market_data_dir =  config.get('ConfigSettings','market_data_dir')
use_atr = config.getboolean('StrategySettings','use_atr')
atr_period =  int(config.get('StrategySettings','atr_period'))
number_atr = int(config.get('StrategySettings','number_atr'))

positions = pd.DataFrame()
notionals = pd.DataFrame()
pnl = pd.DataFrame()

for index, row in models.iterrows():
    logger.info('Processing '+ row['model'] +' '+row['instrument_type']+' '+ row['instrument']+' quandl_id='+row['quandl_id'])
    result = calculate_positions(row['model'], row['quandl_id'], row['instrument'], row['point_value'], logger, config)
    positions = pd.concat([positions, result.positions])
    notionals = pd.concat([notionals, result.notionals])
    pnl = pd.concat([pnl, result.pnl])
    
plot_pnl_by_model(pnl)
    
total_pnl = pnl.groupby(pnl.index).sum()
plot_total_pnl(total_pnl)

total_pnl['daily_pnl'] = total_pnl['pnl'].diff()
total_pnl['daily_pnl_pct'] = total_pnl['daily_pnl'] / capital

sharpe_ratio = annualised_sharpe(total_pnl['daily_pnl_pct'], risk_free_rate = 0.0)
    
