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
    
def trade_size(signal, capital, vol):
    return round(0.001 * signal * capital / vol)

#'YAHOO/AAPL'
#'CHRIS/CME_CL1'
#plt.plot(data['Open'])