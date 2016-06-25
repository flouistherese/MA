import os
os.chdir('H:/Dropbox/Dropbox/Code/Python/strategies/MA/')

execfile('keys.py')
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
capital_path = config.get('AccountSettings','capital_path')
models = pd.read_csv(config.get('StrategySettings','models_path'), sep=',')
vol_target = float(config.get('AccountSettings','volatility_target'))
slippage = float(config.get('StrategySettings','slippage'))
transaction_cost = float(config.get('AccountSettings', 'transaction_cost'))
store_sim_positions = config.getboolean('StrategySettings','store_sim_positions')
long_only = config.getboolean('StrategySettings','long_only')
geared = config.getboolean('StrategySettings','geared')
sim_positions_path = config.get('StrategySettings','sim_positions_path')
order_file_path = config.get('StrategySettings','order_file_path')
pnl_file_path = config.get('StrategySettings','pnl_file_path')
current_positions_file = config.get('StrategySettings','positions_path')
signals_path = config.get('StrategySettings','signals_path')
limits = pd.read_csv(config.get('StrategySettings','limits_path'), sep=',')
live_data_enabled = config.getboolean('ConfigSettings','live_data_enabled')
store_market_data = config.getboolean('ConfigSettings','store_market_data')
market_data_dir =  config.get('ConfigSettings','market_data_dir')
trading_enabled =  config.getboolean('ConfigSettings','trading_enabled')
refresh_frequency = int(config.get('ConfigSettings','refresh_frequency'))
use_atr = config.getboolean('StrategySettings','use_atr')
atr_period =  int(config.get('StrategySettings','atr_period'))
number_atr = int(config.get('StrategySettings','number_atr'))

mail_user = config.get('ConfigSettings','mail_user')
mail_recipients = config.get('ConfigSettings','mail_recipients')

base_multiplier = 1E8
p = poloniex(poloniex_api_key, poloniex_secret)


pnl_dict = create_pnl_dict(models)
order_dict = create_order_dict(models, order_file_path)
update_live_pnl()
schedule.every(30).seconds.do(update_live_pnl)

#Main Loop
while True:
    schedule.run_pending()
    time.sleep(1)

    
def run_model():
    btc_capital = get_capital(capital_path) 
    capital_allocated = btc_capital / len(models)
    for index, row in models.iterrows():
        logger.info('Processing '+ row['model'] +' '+row['instrument_type']+' '+ row['instrument']+' id='+row['id'])
        position_today = calculate_positions(row['model'], row['id'], row['instrument'], capital_allocated, logger, config)
        trades_today = generate_trades(current_positions_file, position_today)    
        logger.info('Trades to be executed : \n'+trades_today.to_string())
        if trading_enabled:
            order_ids, exec_recaps = execute_trades(trades_today)
    
    
    
    send_recap_email(trades_today, exec_recaps, btc_capital, pnl_dict)
    
    
