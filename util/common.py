""" common.py - shared functions used in the project. """
import os, fnmatch, datetime, traceback, pytz, sys
from ascii import *
from tl_logger import TLLog

log = TLLog.getLogger( 'common' )

def toInt(sData):
    """ check for 0x prefix for hex """
    try:
        if type(sData) == type(str()):
            if sData[0:2] == '0x':
                return int( sData[2:], 16)
        return int(float(sData)) #float conversion first to handle exponents
    except Exception,err:
        log.error('toInt() fail - "%s" - %s - returning minimum integer' % (sData,err))
        return -sys.maxint - 1

def singleton(object, instantiated=[]):
    """Raise an exception if an object of this class has been instantiated before.
       not thread-safe"""
    assert object.__class__ not in instantiated, \
           "%s is a Singleton class but is already instantiated" % object.__class__
    instantiated.append(object.__class__)


def locate(pattern, root=os.getcwd()):
    """ Returns a list of all matching files found below the root directory.

    pattern -- file mask to match with, contains wildcards recognoized by system
    root -- directory to start the search. default is current directory
    """
    for path, dirs, files in os.walk(os.path.abspath(root)):
        for filename in fnmatch.filter(files, pattern):
            yield os.path.join(path, filename)

def flatten(x):
    """ flatten(sequence) -> list

    Returns a single, flat list which contains all elements retrieved
    from the sequence and all recursively contained sub-sequences
    (iterables).

    Examples:
    >>> [1, 2, [3,4], (5,6)]
    [1, 2, [3, 4], (5, 6)]
    >>> flatten([[[1,2,3], (42,None)], [4,5], [6], 7, MyVector(8,9,10)])
    [1, 2, 3, 42, None, 4, 5, 6, 7, 8, 9, 10]
    """

    result = []
    for el in x:
        #if isinstance(el, (list, tuple)):
        if hasattr(el, "__iter__") and not isinstance(el, basestring):
            result.extend(flatten(el))
        else:
            result.append(el)
    return result

def printf( msg ):
    try:
        print msg
    except IOError,err:
        log.error( 'IOError in printf() -- ignoring' )
        
def hexDump( data, msg=None, logFunc=printf ):
    """ dump data in hex format """
    hex = ''
    str = ''
    index = 0
    offset = 0
    CHARS_PER_LINE = 16
    hdr = ''
    if msg:
        hdr = msg + ' - '
    for ch in data:
        hex += '%02X ' % ord(ch)
        if isprint(ch):
            str += ch
        else:
            str += '.'
        index += 1
        if index % CHARS_PER_LINE == 0:
            logFunc( '%s%3d : %-48s %s' % (hdr, offset, hex, str))
            hex = ''
            str = ''
            offset += CHARS_PER_LINE
    if hex != '':
        logFunc( '%s%3d : %-48s %s' % (hdr, offset, hex, str) )

def parseTimeString(timeStr):
    """ return a datetime object from input string
        Formats supported are:
            YYYY-MM-DD_HH:MM:SS	- Full time
            HH:MM:SS            - Uses today's date and set time
            YYYY-MM-DD  	- Set date and use midnight
    """
    log.debug( 'parseTimeString() - timeStr:%s' % timeStr )
    dtStr = None
    tmStr = None
    if timeStr.find('_') != -1:
        # both date and time
        lst = timeStr.split('_')
        dtStr = lst[0]
        tmStr = lst[1]
    elif timeStr.find('-') != -1:
        # date string only
        dtStr = timeStr
        # Use midnight
        tm = datetime.time(0,0,0)
    elif timeStr.find(':') != -1:
        # time string only
        tmStr = timeStr
        # Use UTC now for date
        dtUTC = datetime.datetime.utcnow()
        dt = dtUTC.date()
    else:
        raise Exception( 'Bad time string format. Expecting YYYY-MM-DD_HH:MM:SS, HH:MM:SS, or YYYY-MM-DD' )

    if dtStr:
        # Format is YYYY-MM-DD
        lst = dtStr.split('-')
        year = int(lst[0])
        mon  = int(lst[1])
        day  = int(lst[2])
        dt = datetime.date(year,mon,day)

    if tmStr:
        utc = pytz.UTC
        # Format is HH:MM:SS
        lst = tmStr.split(':')
        hour = int(lst[0])
        min  = int(lst[1])
        sec  = int(lst[2])
        tm = datetime.time(hour,min,sec,tzinfo=utc)

    return datetime.datetime( dt.year, dt.month, dt.day, tm.hour, tm.minute, tm.second, tzinfo=UTC() )

def dictFromString( src, seperator=',' ):
    """ Convert a string deliminated by separator into a dictionary of value/pairs """
    lst = src.split(',')
    dct = {}
    name = None
    for val in lst:
        if name is None:
            name = val
        else:
            dct[name] = val
            name = None
    return dct

tracebackToStdout = True

def setTracebackToStdout( value ):
    log.info( 'setTracebackToStdout() - %s' % value )
    global tracebackToStdout
    tracebackToStdout = value

def excTraceback(err, lg, msg=None, raiseErr=True):
    """ log an exception with full traceback. When complete raise the exception again.
        After logging the traceback, add the member _tracebackLogged to the exception so that
        tracebacks for any exception are only logged once on multiple catches of the same exception.
    """
    global tracebackToStdout
    sTraceback = None
    try:
        s = '%s : %s' % (err.__class__.__name__, err)
        if msg:
            s = '%s : %s' % (msg, s)
        if not hasattr( err, '_tracebackLogged'):
            if tracebackToStdout:
                print '-- traceback --'
                traceback.print_exc()
                print
            sTraceback = traceback.format_exc()
            lg.error( 'trackback: %s' % sTraceback )
            err._tracebackLogged = 1
        if tracebackToStdout:
            print s
        lg.error( s )
    except Exception,err:
        pass

    # raise exception if requested
    if raiseErr:
        raise err
    return sTraceback

ZERO = datetime.timedelta(0)
HOUR = datetime.timedelta(hours=1)

# A UTC class.

class UTC(datetime.tzinfo):
    """UTC tzinfo class -- used with datetime constructor to set UTC zone """
    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

def timeString(value,decimal=3):
    """ take a float time value and return string with engineering units """
    try:
        value = float(value)
        units = 's'

        if value >= 1.0 or value == 0.0:
            pass
        elif value >= 1e-3:
            value *= 1e3
            units = 'ms'
        elif value >= 1e-6:
            value *= 1e6
            units = 'us'
        elif value >= 1e-9:
            value *= 1e9
            units = 'ns'
        else:
            value *= 1e12
            units = 'fs'
        fmt = '%%.%df %s' % (decimal,units)
        s = fmt % value
    except Exception,ex:
        log.error( 'timeString() fail - %s' % ex )
        s = '****'
    return s

def freqString(value,decimal=3):
    """ take a float time value and return sting with engineering units """
    try:
        value = float(value)
        units = 'Hz'

        if value < 1e3 or value == 0.0:
            pass
        elif value < 1e6:
            value /= 1e3
            units = 'kHz'
        elif value < 1e9:
            value /= 1e6
            units = 'MHz'
        elif value < 1e12:
            value /= 1e9
            units = 'GHz'
        else:
            value /= 1e12
            units = 'THz'
        fmt = '%%3.%df %s' % (decimal,units)
        s = fmt % value
    except Exception,ex:
        log.error( 'freqString() fail - %s' % ex )
        s = '****'
    return s

def bitrateString(value,decimal=3):
    """ take a float value and return sting with engineering units """
    try:
        value = float(value)
        units = 'bps'

        if value < 1e3 or value == 0.0:
            pass
        elif value < 1e6:
            value /= 1e3
            units = 'kbps'
        elif value < 1e9:
            value /= 1e6
            units = 'Mbps'
        else:
            value /= 1e9
            units = 'Gbps'
        fmt = '%%3.%df %s' % (decimal,units)
        s = fmt % value
    except Exception,ex:
        log.error( 'bitrateString() fail - %s' % ex )
        s = '****'
    return s

def luxString(value,decimal=3):
    """ take a float value and return Lux string with engineering units """
    try:
        value = float(value)
        units = 'lux'
        
        fmt = '%%3.%df %s' % (decimal,units)
        s = fmt % value
    except Exception, ex:
        log.error('luxstring() fail - %s' % ex)
    return s

def psiString(value,decimal=3):
    """ take a float value and return PSI string with engineering units """
    try:
        value = float(value)
        units = 'psi'

        fmt = '%%3.%df %s' % (decimal,units)
        s = fmt % value
    except Exception,ex:
        log.error( 'psiString() fail - %s' % ex )
        s = '****'
    return s

def dbmString(value,decimal=2):
    """ take a float value and return DBM string with engineering units """
    try:
        value = float(value)
        units = 'dBm'

        fmt = '%%.%df %s' % (decimal,units)
        s = fmt % value
    except Exception,ex:
        log.error( 'dbmString() fail - %s' % ex )
        s = '****'
    return s

def dbString(value,decimal=2):
    """ take a float value and return DBM string with engineering units """
    try:
        value = float(value)
        units = 'dB'

        fmt = '%%.%df %s' % (decimal,units)
        s = fmt % value
    except Exception,ex:
        log.error( 'dbString() fail - %s' % ex )
        s = '****'
    return s

def currentString(value,decimal=3):
    """ take a float value and return PSI string with engineering units """
    try:
        value = float(value)
        units = 'A'

        fmt = '%%3.%df %s' % (decimal,units)
        s = fmt % value
        
    except Exception,ex:
        log.error( 'currentString() fail - %s' % ex )
        s = '****'
    return s

def voltString(dVoltValue, uDecimalLen=2):
    """ Return a string with value and units for the requested length
    Volt units are V, mV """
    try:
        # make voltage always positive
        dVolt = abs(float(dVoltValue))
        if dVolt < 1.0:
            fmt = '%%.%df mV' % uDecimalLen
            s = fmt % (dVoltValue * 1.0e3)
        else:
            fmt = '%%.%df V' % uDecimalLen
            s = fmt % (dVoltValue)
    except Exception,ex:
        log.error( 'voltString() fail - %s' % ex )
        s = '****'
    return s


def percentString(dPctValue, uDecimalLen=2):
    """ Return a string as a percentage, ramge [0.0 .. 1.0] """
    try:
        dPct = float(dPctValue)
        dPct = max( dPct, 0.0)
        dPct = min( dPct, 100.0)
        fmt = '%%.%df %%%%' % uDecimalLen
        s = fmt % dPct
    except Exception,ex:
        log.error( 'percentString() fail - %s' % ex )
        s = '****'
    return s


def addSysPath(new_path):
    """ addSysPath(new_path): add a directory to Python's sys.path

       Does not add the directory if it does not exist or it's already on
       the sys.path. Returns 1 of OK, -1 if does not exist and 0 if it was already on
       the path.

       From Python Cookbook -- Dynamically changing the python search path
       """
    import sys, os

    # Avoid adding nonexsitent paths
    if not os.path.exists(new_path):
        return -1

    # Standardize the path, windows is case insensitive so lower all paths
    new_path = os.path.abspath(new_path)
    if sys.platform == 'win32':
        new_path = new_path.lower()

    # Check against available paths
    for x in sys.path:
        x = os.path.abspath(x)
        if sys.platform == 'win32':
            x = x.lower()
        if new_path in (x, x + os.sep):
            return 0

    # add the new path
    sys.path.append( new_path )
    return 1


def floatprint(a, fmt='%.2f'):
    return ', '.join(map(lambda b: fmt % b, a))

def split_string(msg, size):
    """ break a string into a list """
    lst = []
    start = 0
    end   = 0
    while end < len(msg):
        end += size
        lst.append( msg[start:end] )
        start += size
    return lst

def makeTimeDurationString(timeDelta):
    """ take a timeDelta and return a string 'MM:SS' """
    totSecs = timeDelta.total_seconds()
    minutes = timeDelta.seconds / 60
    seconds = int(totSecs - minutes*60 + 0.5)
    log.debug('makeTimeDurationString() - timeDelta.seconds:%s totSecs:%s minutes:%s seconds:%s' % (timeDelta.seconds,totSecs, minutes,seconds))
    return '%.02d:%.02d' % (minutes,seconds)

if __name__ == '__main__':
    print
    
    msg = '0123456789'
    msg += msg
    msg += msg
    msg += msg
    
    size = 132
    lst = split_string( msg, size )
    print 'msg',msg
    print 'size',size
    for n,ms in enumerate(lst):
        print '%2d : %s' % (n,ms)
    
    
    #lstTimeStrings = [ '2011-01-01', '01:00:00', '2012-02-01_14:00:00']
    #for ts in lstTimeStrings:
        #dt = parseTimeString( ts )
        #print 'time string: %-25s parsed: %s' % (ts, dt)
    #print
    #lstTimeValues = [ 0, 1, 0.1, 0.01, 0.001, 0.0001, 0.000001, 3e-6, 3e-7, 3e-5,0.0001997 ]
    #for val in lstTimeValues:
        #s = timeString(val)
        #print 'val:%10g eng:%s' % (val,s) 
    #print
    #lstFreqValues = [ 0, 1, 10, 100, 1e3, 1e4, 20.123e4, 3e6, 3e7, 3e5 ]
    #for val in lstFreqValues:
        #s = freqString(val)
        #print 'val:%10g eng:%s' % (val,s) 
    #lstVoltValues = [ 0, 1, 10, 100, 0.1, 0.43, 0.006 ]
    #for val in lstVoltValues:
        #s = voltString(val)
        #print 'val:%10g eng:%s' % (val,s) 
    #lstPctValues = [ 0, 1, 0.1, 0.15, -2.0, 1000.0, 0.9, 0.75 ]
    #for val in lstPctValues:
        #s = percentString(val)
        #print 'val:%10g eng:%s' % (val,s) 
