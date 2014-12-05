""" tl_logger.py - custom logging using the python logging module """
import logging,sys

LOG_DISABLE_LEVEL = logging.INFO
LOG_ENABLE_LEVEL  = logging.DEBUG

class LogModule(object):
    def __init__(self, name):
        self._log = logging.getLogger( name )
        self.name = name
        
    def getLog(self):
        return self._log

    def isEnabled(self):
        level = self._log.getEffectiveLevel()
        if level < LOG_DISABLE_LEVEL:
            return True
        return False
    
    def enable(self):
        print( 'log %-10s -- ENABLED' % self.name )
        self._log.setLevel( LOG_ENABLE_LEVEL )
    
    def disable(self):
        print( 'log %-10s -- DISABLED' % self.name )
        self._log.setLevel( LOG_DISABLE_LEVEL )

    # Overloads for log modules
    def info( self, msg):
        self._log.info( msg )
        
    def error( self, msg):
        self._log.error( msg )
        
    def debug( self, msg):
        self._log.debug( msg )
        
    def warn( self, msg):
        self._log.warn( msg )
        
    def warning( self, msg):
        self._log.warning( msg )
        
    def critical( self, msg):
        self._log.critical( msg )
        
    def isEnabledFor(self, lvl):
        return self._log.isEnabledFor(lvl)
    
    def __cmp__(self,other):
        return self.name < other.name

class TLLog(object):
    # create logging formatters 
    FORMAT  = '%(asctime)s %(name)-8s [%(threadName)-4s] %(levelname)-8s %(message)s'
    DATEFMT = None  # '%Y-%m-%d %H:%M:%S'
    fmt = logging.Formatter( fmt=FORMAT, datefmt=DATEFMT)
    
    # create console handler with a higher log level
    hdlStream = logging.StreamHandler()
    hdlStream.setLevel(logging.ERROR)
    hdlStream.setFormatter(fmt)
    
    # list of all handlers
    _lstLogHandlers = [hdlStream]
    #_lstLogHandlers = []

    # dict of all loggers added with getLogger
    _dctLoggers = {}

    # dict of all loggers that are enabled, used 
    _dctEnabledLoggers = {}

    # loggers that are auto set to level INFO 
    _lstAutoEnabled = []

    _defLogLevel = LOG_DISABLE_LEVEL

    # main file handle
    _hdlMainFile = None

    # dictionary of log files
    _dctLogFiles = {}
    
    @staticmethod
    def getLogger(name):
        """ register the module and add to dctLogModules """
        lm = LogModule(name)
        log = lm.getLog()
        if not TLLog._dctLoggers.has_key( name ):
            #print 'getLogger() -- adding "%s"' % name
            log.propagate = False
            # add all of the log handlers
            for hdl in TLLog._lstLogHandlers:
                log.addHandler(hdl)
            # set the log level
            level = TLLog._defLogLevel
            if name in TLLog._dctEnabledLoggers and TLLog._dctEnabledLoggers[name]:
                level = LOG_ENABLE_LEVEL
            log.setLevel( level )
            # save the logger locally 
            TLLog._dctLoggers[ name ] = lm
        return lm 
        
    @staticmethod
    def getLoggers():
        """ Return all Loggers created """
        return TLLog._dctLoggers

    @staticmethod
    def getEnabledLoggers():
        """ Returns a dictionary with logger name and enabled """
        dct = {}
        for key,lm in TLLog._dctLoggers.items():
            dct[key] = lm.isEnabled() 
        return dct
        
    @staticmethod
    def config(filename, lstAutoEnabled=None,defLogLevel=None):
        if lstAutoEnabled is not None:
            TLLog._lstAutoEnabled = lstAutoEnabled
        if defLogLevel is not None:
            TLLog._defLogLevel = defLogLevel
        # create file handler which logs even debug messages
        TLLog._hdlMainFile = logging.FileHandler( filename )
        TLLog._hdlMainFile.setLevel(logging.DEBUG)
        TLLog._hdlMainFile.setFormatter(TLLog.fmt)
        TLLog._lstLogHandlers.append( TLLog._hdlMainFile )
        # add the new handler to all existing loggers
        for lm in TLLog._dctLoggers.values():
            lm._log.addHandler(TLLog._hdlMainFile)
        # set new auto enabled
        if lstAutoEnabled is not None:
            for name in TLLog._lstAutoEnabled:
                # add to dct of enabled loggers
                TLLog._dctEnabledLoggers[ name ] = True
                if TLLog._dctLoggers.has_key( name ):
                    TLLog._dctLoggers[name].enable()
            
    @staticmethod
    def logFileOpen(filename,log=None, stopMainLog=True):
        """ open a log file  """
        try:
            # create file handler which logs even debug messages
            hdlFile = logging.FileHandler( filename, mode='w' )
            hdlFile.setLevel(logging.DEBUG)
            hdlFile.setFormatter(TLLog.fmt)
            TLLog._lstLogHandlers.append( hdlFile )
            # add the new handler to all existing loggers
            for lm in TLLog._dctLoggers.values():
                lm._log.addHandler(hdlFile)
            # add to dict of log files
            TLLog._dctLogFiles[filename] = hdlFile
            if log:
                log.info('Log file "%s" Starting' % filename)
            # stop main log
            if stopMainLog and TLLog._hdlMainFile:
                for lm in TLLog._dctLoggers.values():
                    lm._log.removeHandler(TLLog._hdlMainFile)
            
        except Exception,err:
            print 'logFileOpen() fail - filename:\"%s\" - %s' % (filename, err)

    @staticmethod
    def logFileClose(filename, log=None):
        """ close an open log file """
        try:
            # add main log back
            if TLLog._hdlMainFile:
                for lm in TLLog._dctLoggers.values():
                    lm._log.addHandler(TLLog._hdlMainFile)
            # get handle to log file
            hdlFile = TLLog._dctLogFiles[filename]
            # close log file
            hdlFile.close()
            # remove from list of log handlers
            TLLog._lstLogHandlers.remove( hdlFile )
            # remove handle from existing loggers
            for lm in TLLog._dctLoggers.values():
                lm._log.removeHandler(hdlFile)
            # remove from dict of log files
            del TLLog._dctLogFiles[filename]
            if log:
                log.info('Log file "%s" Closing' % filename) 
            
        except Exception,err:
            print 'logFileClose() fail - filename:\"%s\" - %s' % (filename, err)

    @staticmethod
    def isEnabled( name ):
        try:
            lm = TLLog._dctLoggers[name]
            return lm.isEnabled()
        except:
            return False
    
    @staticmethod
    def enable( name ):
        try:
            # add to dct of enabled loggers
            TLLog._dctEnabledLoggers[ name ] = True
            # if already defined then enable
            lm = TLLog._dctLoggers[name]
            lm.enable()
        except:
            pass
    
    @staticmethod
    def disable( name ):
        try:
            # add to dct of enabled loggers
            TLLog._dctEnabledLoggers[ name ] = False
            lm = TLLog._dctLoggers[name]
            lm.disable()
        except:
            pass

    @staticmethod
    def shutdown():
        """ shutdown the logging system """
        logging.shutdown()

    @staticmethod
    def setConsoleHandlerLevel(level=logging.INFO):
        # set the log level for console handler 
        TLLog.hdlStream.setLevel( level )

def logOptions(lstLogEnable, showLogs=False, log=None):
    """ process all log options from the command line """
    # if list logs then list and exit 
    dctLogMods = TLLog._dctLoggers
    if showLogs:
        lst = dctLogMods.keys()
        lst.sort()
        if log:
            log.info( 'Logs available - %s' % lst)
        print 'Logs available:'
        for name in lst:
            print '  %s' % name
        sys.exit(-1)
        
    # enable logs 
    if lstLogEnable == '*':
        # enable all logs
        lstLogEnables = dctLogMods.keys()
    else:
        # log to enable are in list comma delimited
        lstLogEnables = lstLogEnable.split(',')

    for key,lm in dctLogMods.items():
        if key in lstLogEnables:
            lm.enable()
        else:
            lm.disable()

    # print the enabled logs    
    dctLogMods = TLLog._dctLoggers
    lst = [key for key,lm in dctLogMods.items() if lm.isEnabled()]  
    if log:
        log.info( 'Enable logs - %s' % lst)

