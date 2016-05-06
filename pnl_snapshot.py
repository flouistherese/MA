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
        
        self.m_total_pnl = self.m_realized_pnl + self.m_unrealized_pnl

    def update_by_marketdata(self, last_price):
        self.m_unrealized_pnl = ( last_price - self.m_avg_open_price ) * self.m_net_position
        self.m_total_pnl = self.m_realized_pnl + self.m_unrealized_pnl