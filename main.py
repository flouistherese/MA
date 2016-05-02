import os
os.chdir('H:/Dropbox/Dropbox/Code/Python/strategies/MA/')

execfile('imports.py')
execfile('poloniex_api.py')
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
store_sim_positions = config.getboolean('StrategySettings','store_sim_positions')
long_only = config.getboolean('StrategySettings','long_only')
sim_positions_path = config.get('StrategySettings','sim_positions_path')
current_positions_file = config.get('StrategySettings','positions_path')
signals_path = config.get('StrategySettings','signals_path')
limits = pd.read_csv(config.get('StrategySettings','limits_path'), sep=',')
live_data_enabled = config.getboolean('ConfigSettings','live_data_enabled')
store_market_data = config.getboolean('ConfigSettings','store_market_data')
market_data_dir =  config.get('ConfigSettings','market_data_dir')
trading_enabled =  config.getboolean('ConfigSettings','trading_enabled')
use_atr = config.getboolean('StrategySettings','use_atr')
atr_period =  int(config.get('StrategySettings','atr_period'))
number_atr = int(config.get('StrategySettings','number_atr'))

positions = pd.DataFrame()
notionals = pd.DataFrame()
pnl = pd.DataFrame()
trades = pd.DataFrame()
p = poloniex(poloniex_api_key, poloniex_secret)

update_positions(current_positions_file)


for index, row in models.iterrows():
    logger.info('Processing '+ row['model'] +' '+row['instrument_type']+' '+ row['instrument']+' id='+row['id'])
    result = calculate_positions(row['model'], row['id'], row['instrument'], row['instrument_type'],row['point_value'], logger, config)
    positions = pd.concat([positions, result.positions])
    notionals = pd.concat([notionals, result.notionals])
    trades = pd.concat([trades, result.trades])
    pnl = pd.concat([pnl, result.pnl])
    
balances_raw = p.returnBalances()
btc_capital = float(balances_raw['BTC'])
trades_today = generate_trades(current_positions_file, positions, capital, btc_capital)
logger.info('Trades to be executed : \n'+trades_today.to_string())
if trading_enabled:
    execute_trades(trades_today)
    
plot_pnl_by_model(pnl)
    
total_pnl = pnl.groupby(pnl.index).sum()
plot_total_pnl(total_pnl)

total_pnl['daily_pnl'] = total_pnl['pnl'].diff()
total_pnl['daily_pnl_pct'] = total_pnl['daily_pnl'] / capital

sharpe_ratio = annualised_sharpe(total_pnl['daily_pnl_pct'], risk_free_rate = 0.0)
    
