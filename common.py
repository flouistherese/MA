api_key = "JyPzgcScbDfyY5H-mVhM"

def createLogger(logfile_path):
    logger = logging.getLogger('myapp')
    hdlr = logging.FileHandler(logfile_path)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr) 
    logger.setLevel(logging.INFO)
    return logger
    
def getHistoricalData(ticker, logger, period = 'daily'):  
    try:
        return Quandl.get(ticker, collapse=period, authtoken = api_key)
    except Exception as e:
        logger.exception("message")
    
def movingaverage (values, window):
    weights = np.repeat(1.0, window)/window
    sma = np.convolve(values, weights, 'valid')
    return sma
    
def pad(array, width, value):
    return np.lib.pad(array, (width,0), mode = 'constant', constant_values= value)
    
def trade_size(signal, capital, vol, price):
    return round(0.001 * signal * capital / (vol*price))
    
def store_positions(close, positions_path, instrument, quandl_id, logger):
    positions_directory_path = positions_path + strftime("%Y-%m-%d")
    if not os.path.exists(positions_directory_path):
        os.makedirs(positions_directory_path)
    positions_file_path = positions_directory_path + '/' + instrument + '_' + strftime("%Y-%m-%d_%H-%M-%S") + '.csv'
    logger.info('Storing positions to '+positions_file_path+' quandl_id='+ quandl_id)
    close[['Close','position']].to_csv(positions_file_path,mode  = 'w+')

def plot_signals(close):
    plt.figure()
    plt.ion()
    plt.plot(close['Close'], ls = '-')
    plt.plot(close['ma20'], ls = '-')
    #plt.plot(close['ma50'], ls = '-')
    plt.plot(close['ma100'], ls = '-')
    #plt.plot(close['ma200'], ls = '-')
    plt.plot(close['signal'], ls='-')
    plt.show()

def plot_pnl(close,instrument):
    plt.figure()
    plt.ion()
    
    plt.subplot(411)
    plt.plot(close['Close'], ls = '-')
    plt.plot(close['ma20'], ls = '-')
    #plt.plot(close['ma50'], ls = '-')
    plt.plot(close['ma100'], ls = '-')
    #plt.plot(close['ma200'], ls = '-')
    plt.plot(close['signal'], ls='-')
    plt.title(instrument)
    plt.ylabel('Price')
    plt.subplot(412)
    plt.plot(close['pnl'])
    plt.ylabel('PnL')
    plt.subplot(413)
    plt.plot(close['position'])
    plt.ylabel('Position')
    plt.subplot(414)
    plt.plot(close['10d_vol'])
    plt.ylabel('vol')
    plt.show()
    
def calculate_pnl(close, instrument):
    pnl = np.array([])
    positions = close[close['signal'] != 0]
    pnl_snapshot = PnlSnapshot(instrument, np.sign(positions.ix[0].trade), positions.ix[0].Close, abs(positions.ix[0].trade))
    row_number = 0
    for index, row in positions.iterrows():
        if row_number > 0:
            pnl_snapshot.update_by_tradefeed(np.sign(row['trade']), row['Close'], abs(row['trade']))
            pnl_snapshot.update_by_marketdata(row['Close'])
            pnl = np.append(pnl, pnl_snapshot.m_total_pnl - row['transaction_cost'])
        row_number += 1
    return pnl

#'YAHOO/AAPL'
#'CHRIS/CME_CL1'
#plt.plot(data['Open'])