# -*- coding: utf-8 -*-
"""
Created on Thu Jul 21 13:17:20 2016

@author: Florian
"""

config = ConfigParser.ConfigParser()
config.read("config/engine.config")
logger = createLogger(config.get('ConfigSettings','logfile_path'))

base_multiplier = 1E8  #Multiplier used for every price in order to avoid floating point issue

logger.info('\n\n\n\n\nStarting engine')
capital_path = config.get('AccountSettings','capital_path')
models = pd.read_csv(config.get('StrategySettings','models_path'), sep=',')
vol_target = float(config.get('AccountSettings','volatility_target'))
slippage = float(config.get('StrategySettings','slippage'))
minimum_btc_trade = float(config.get('StrategySettings','minimum_btc_trade')) * base_multiplier
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