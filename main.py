import os
os.chdir('H:/Dropbox/Dropbox/Code/Python/strategies/MA/')

execfile('keys.py')
execfile('imports.py')
execfile('poloniex_api.py')
execfile('common.py')
execfile('backtest.py')
execfile('trend.py')
execfile('pnl_snapshot.py')
execfile('load_config.py')

p = poloniex(poloniex_api_key, poloniex_secret) #Connection to Poloniex API

pnl_dict = create_pnl_dict(models) # pnl_dict['BTC_TREND_SC'] return matching PnlSnapshot object
order_dict = create_order_dict(models, order_file_path)
update_live_pnl()

def run_model():
    update_live_pnl()
    withdraw_open_orders()
    btc_capital = get_capital(capital_path) 
    capital_allocated = btc_capital / len(models) #Capital equally allocated to each model
    for index, row in models.iterrows():
        logger.info('Processing '+ row['model'])
        position_today = calculate_positions(row['model'], row['id'], row['instrument'], capital_allocated, logger, config)
        trades_today = generate_trades(current_positions_file, position_today)    
        logger.info('Trades to be executed : \n'+trades_today.to_string())
        if trading_enabled:
            order_ids, exec_recaps = execute_trades(trades_today)
            
            
schedule.every(10).minutes.do(update_live_pnl)
schedule.every(15).minutes.do(run_model)

#Main Loop
run_model()
while True:
    schedule.run_pending()
    time.sleep(1)
            
    
    
    
#send_recap_email(trades_today, exec_recaps, btc_capital, pnl_dict)
    
    
