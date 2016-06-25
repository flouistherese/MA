class Trader:
    def __init__(self, model_code, instrument_id, api, config):
        self.m_model_code = model_code
        self.m_instrument_id = instrument_id
        self.m_pnl = PnlSnapshot(instrument_id)
        self.m_market_data = pd.DataFrame()
        self.m_trades = pd.DataFrame()
        self.m_positions = pd.DataFrame()
        self.m_api = api
        self.m_volatility_window = float(config.get('StrategySettings', 'volatility_window'))
        self.m_ma1_period = int(config.get('StrategySettings','ma1'))
        self.m_ma2_period = int(config.get('StrategySettings','ma2'))
        self.m_last_price = 0
        self.m_live_ma1 = 0
        self.m_live_ma2 = 0
        self.m_live_vol = 0
    
    def load_market_data(self):
        price_data = p.returnChartData(self.m_instrument_id, start = int(time.time()) - 3600 * 10, period = 300)
        self.m_market_data = price_data[['close']]
        self.m_market_data.loc[:,('vol')] = calculate_pct_volatility(self.m_market_data.loc[:,('close')], self.m_volatility_window)
        
        ma1 = movingaverage(self.m_market_data['close'] , self.m_ma1_period)
        ma2 = movingaverage(self.m_market_data['close'] , self.m_ma2_period)
        self.m_market_data['ma1'] = pad(ma1, len(self.m_market_data) - ma1.size, float('nan'))
        self.m_market_data['ma2'] = pad(ma2, len(self.m_market_data) - ma2.size, float('nan'))
        
    def update_market_data(self):
        ticker_raw = self.m_api.returnTicker()
        ticker = pd.DataFrame.from_dict(ticker_raw, orient = 'index').reset_index()
        self.m_live_price = float(ticker[ticker['index'] == self.m_instrument_id]['last'])
        price_to_remove = self.m_market_data.iloc[-self.m_ma1_period]['close']
        self.m_live_ma1 = self.m_market_data.iloc[-1]['ma1'] + (self.m_live_price)/self.m_ma1_period - price_to_remove/self.m_ma1_period
        self.m_live_ma2 = self.m_market_data.iloc[-1]['ma2'] + (self.m_live_price)/self.m_ma2_period - price_to_remove/self.m_ma2_period
        prices = np.append(self.m_market_data.iloc[-int(self.m_volatility_window):]['close'].values, self.m_live_price)
        self.m_live_vol = float(pd.DataFrame.std(pd.DataFrame.pct_change(pd.DataFrame(prices))))
        #cols = ['close','vol','ma1','ma2']
        #self.m_market_data.append([self.live_price, self.m_live_vol, self.m_live_ma1, self.m_live_ma2])
        print([self.m_live_price, self.m_live_vol, self.m_live_ma1, self.m_live_ma2])