""" dbmain.py - simple query program for MfgTest database """ 
import sys
import threading
import logging
import traceback

from pymongo import MongoClient

from util.tl_logger import TLLog,logOptions
TLLog.config( 'logs\\DBMain.log', defLogLevel=logging.INFO )

log = TLLog.getLogger( 'DBMain' )

DEFAULT_LOG_ENABLE = 'SQL,DBMain'
DEFAULT_DB_SETUP = 'Mfg'
DEFAULT_HOST = 'localhost'
DEFAULT_PORT = '27017'

if __name__ == '__main__':
    # build the command line arguments
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option( "-m",  "--logEnable", dest="lstLogEnable", default=DEFAULT_LOG_ENABLE,
                       help='Comma separated list of log modules to enable, * for all. Default is "%s"' % DEFAULT_LOG_ENABLE)
    parser.add_option( "-g",  "--showLogs", action="store_true", dest="showLogs", default=False,
                       help='list all log options.' )
    parser.add_option( "-y",  "--runCmdFile", dest="cmdFile", default=None,
                       help="Run a command file at startup.")
    parser.add_option( "",  "--host", dest="host", default=DEFAULT_HOST,
                       help="Host to connect to")
    parser.add_option( "",  "--port", dest="port", default=DEFAULT_PORT,
                       help="Port to connect to")

    #  parse the command line and set values
    (options, args) = parser.parse_args()

    # makes Control-break behave the same as Control-C on windows
    import signal
    signal.signal( signal.SIGBREAK, signal.default_int_handler )

    db = None
    client = None
    try:
        # set the main thread name
        thrd = threading.currentThread()
        thrd.setName( 'DBMain' )

        log.info(80*"*")
        log.info( 'DBMain - starting' )
        logOptions(options.lstLogEnable, options.showLogs, log=log)
        
        # connect to database
        host = options.host
        port = int(options.port)
        log.info( 'Connection to host %s port %d' % (host, port))
        client = MongoClient(host=host, port=port)

    except Exception, err:
        s = '%s: %s' % (err.__class__.__name__, err)
        log.error( s )
        print s

        print '-- traceback --'
        traceback.print_exc()
        print
 
    finally:
        # Close the database connection
        if client:
            client.close()
        log.info( 'DBMain - exiting' )
        TLLog.shutdown()
