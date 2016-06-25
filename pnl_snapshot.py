class PnlSnapshot:
    def __init__(self, ticker):
        self.m_ticker = ticker
        self.m_net_position = 0
        self.m_avg_open_price = 0
        self.m_net_investment = 0
        self.m_realized_pnl = 0
        self.m_unrealized_pnl = 0
        self.m_total_pnl = 0
        self.m_latest_trade_id = 0
        self.m_number_trades = 0
        self.m_last_price = 0

    # buy_or_sell: 1 is buy, -1 is sell
    def update_by_tradefeed(self, buy_or_sell, traded_price, traded_quantity):
        # buy: positive position, sell: negative position
        quantity_with_direction = traded_quantity if buy_or_sell == 1 else (-1) * traded_quantity
        is_still_open = abs(self.m_net_position + quantity_with_direction) > 0
        # net investment
        self.m_net_investment = max( self.m_net_investment, abs( self.m_net_position * self.m_avg_open_price  ) )
        # realized pnl
        if not is_still_open:
            # Remember to keep the sign as the net position
            self.m_realized_pnl += ( traded_price - self.m_avg_open_price ) * min( abs(quantity_with_direction), abs(self.m_net_position) ) * ( abs(self.m_net_position) / self.m_net_position ) # total pnl
        
        # avg open price
        if is_still_open:
            self.m_avg_open_price = ( ( self.m_avg_open_price * self.m_net_position ) + 
                ( traded_price * quantity_with_direction ) ) / ( self.m_net_position + quantity_with_direction )
        else:
            # Check if it is close-and-open
            if traded_quantity > abs(self.m_net_position):
                self.m_avg_open_price = traded_price
                self.m_unrealized_pnl = 0
        # net position
        self.m_net_position += quantity_with_direction
        self.m_number_trades = self.m_number_trades + 1
        
        self.m_total_pnl = self.m_realized_pnl + self.m_unrealized_pnl

    def update_by_marketdata(self, last_price):
        self.m_unrealized_pnl = ( last_price - self.m_avg_open_price ) * self.m_net_position
        self.m_total_pnl = self.m_realized_pnl + self.m_unrealized_pnl
        self.m_last_price = last_price
        
        
    def to_string(self):
       return "["+self.m_ticker +"]\nNet Position: "+ format(self.m_net_position, '.10f')+"\nAverage Open Price: "+format(self.m_avg_open_price, '.10f')+"\nNumber of Trades: "+str(self.m_number_trades)+"\nLast Price: "+format(self.m_last_price, '.10f')+"\nRealized PnL: "+format(self.m_realized_pnl, '.10f')+"\nUnrealized PnL: "+format(self.m_unrealized_pnl, '.10f')+"\nTotal PnL: "+format(self.m_total_pnl, '.10f')+"\n\n"
       
    def to_data_frame(self):
        d = {'model': [self.m_ticker], 'position': [self.m_net_position], 'avg_open_price': [format(self.m_avg_open_price, '.10f')], 'last_price': [format(self.m_last_price, '.10f')], 'unrealized_pnl': [self.m_unrealized_pnl], 'realized_pnl': [self.m_realized_pnl], 'total_pnl': [self.m_total_pnl]}
        df = pd.DataFrame(data = d)
        df = df[['model', 'position', 'avg_open_price', 'last_price', 'unrealized_pnl', 'realized_pnl', 'total_pnl']]
        return(df)