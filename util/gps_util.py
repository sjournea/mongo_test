""" gps_util.py - parsing of GPS messages """
import datetime,traceback,logging,time,sys,math
from common import UTC,excTraceback,hexDump,parseTimeString
from tl_logger import TLLog,logOptions

log = TLLog.getLogger( 'gps' )
logGPSD = TLLog.getLogger( 'GPSD' )
logGpsData = TLLog.getLogger( 'gpsdata' )

class Satellite(object):

    _lstValidGPS = range(1,65)          # 1  .. 64
    _lstValidGLONASS = range(65,86)     # 66 .. 85

    @staticmethod
    def isGPS(prn):
        return prn in Satellite._lstValidGPS

    @staticmethod
    def isGLONASS(prn):
        return prn in Satellite._lstValidGLONASS

    def __init__(self, prn, ele, azi, snr, used=None):
        self.prn = self._int(prn)
        self.ele = self._int(ele)
        self.azi = self._int(azi)
        self.snr = self._int(snr)
        if self.snr == None:
            self.snr = 0
        self.used = used

    def _int(self,val):
        try:
            return int(val)
        except:
            return None

    def desc(self):
        s = '%4s %4s %4s %4s' % (self.prn, self.ele, self.azi, self.snr)
        if self.used:
            s += ' **'
        return s

    def __str__(self):
        return 'prn:%s ele:%s azi:%s snr:%s used:%s' % (self.prn, self.ele, self.azi, self.snr, self.used )

class GPS(object):
    """ base class for all GPS messages """
    def __init__(self, msg):
        lst = msg.split('*')
        assert len(lst) == 2
        self.msg = lst[0]
        self.checksum = int(lst[1], 16)
        #
        chk = self._checksum()
        if self.checksum != chk:
            log.warn('GPS message checksum FAIL')
            print('**** GPS message checksum FAIL ****')
        #
        self.lst = self.msg.split(',')

    def _checksum(self):
        val = 0
        for ch in self.msg[1:]:
            val ^= ord(ch)
        return val

    def getMsgType(self):
        return self.lst[0][1:]

    def __str__(self):
        return '%5s - %s' % ('GPS', ','.join(self.lst))

class GSV(GPS):
    """ Abstract 
    === GSV - Satellites in view ===

    These sentences describe the sky position of a UPS satellite in view.
    Typically they're shipped in a group of 2 or 3.

    ------------------------------------------------------------------------------
            1 2 3 4 5 6 7     n
            | | | | | | |     |
     $--GSV,x,x,x,x,x,x,x,...*hh<CR><LF>
    ------------------------------------------------------------------------------

    Field Number: 

    1. total number of GSV messages to be transmitted in this group
    2. 1-origin number of this GSV message  within current group
    3. total number of satellites in view (leading zeros sent)
    4. satellite PRN number (leading zeros sent)
    5. elevation in degrees (00-90) (leading zeros sent)
    6. azimuth in degrees to true north (000-359) (leading zeros sent)
    7. SNR in dB (00-99) (leading zeros sent)
       more satellite info quadruples like 4-7
       n) checksum

    Example:
        $GPGSV,3,1,11,03,03,111,00, 04,15,270,00, 06,01,010,00, 13,06,292,00*74
        $GPGSV,3,2,11,14,25,170,00,16,57,208,39,18,67,296,40,19,40,246,00*74
        $GPGSV,3,3,11,22,42,067,42,24,14,311,43,27,05,244,00,,,,*4D

    Some GPS receivers may emit more than 12 quadruples (more than three
    GPGSV sentences), even though NMEA-0813 doesn't allow this.  (The
    extras might be WAAS satellites, for example.) Receivers may also
    report quads for satellites they aren't tracking, in which case the
    SNR field will be null; we don't know whether this is formally allowed
    or not.
    """
    def __init__(self, msg):
        GPS.__init__(self, msg)
        self.totGSV = int(self.lst[1])
        self.curGSV = int(self.lst[2])
        self.totSatView = int(self.lst[3])
        self.lstSats = []
        for i in range( 4, len(self.lst), 4):
            satPRN = self.lst[i]
            satEle = self.lst[i+1]
            satAzi = self.lst[i+2]
            satSNR = self.lst[i+3]
            sat = Satellite(satPRN,satEle,satAzi,satSNR)
            log.debug('GSV sat:%s' % sat)
            self.lstSats.append( sat )

    def __str__(self):
        return '%5s - %s' % ('--GSV', ','.join(self.lst))

class GPGSV(GSV):
    """ === GSV - GPS Satellites in view ===
    """
    lstSatellites = []
    _lstTempSats = []

    @staticmethod
    def getSatellite(PRN):
        """ return satellite from lstSatellites with matching PRN """
        lst = [sat for sat in GPGSV.lstSatellites if sat.prn == PRN]
        if len(lst) == 1:
            return lst[0]
        if len(lst) == 0:
            return None
        if len(lst) > 1:
            print 'getSatellite() ERROR - PRN exists for 2 satellites ... return 1st only'
            return lst[0]

    def __init__(self, msg):
        GSV.__init__(self, msg)
        self.process()

    def process(self):
        if self.totSatView == 0:
            GPGSV.lstSatellites = []
            GPGSV._lstTempSats = []
        else:
            GPGSV._lstTempSats.extend( self.lstSats )
            if self.curGSV == self.totGSV:
                GPGSV.lstSatellites = [sat for sat in GPGSV._lstTempSats]
                GPGSV._lstTempSats = []
        log.debug( 'totGSV:%s curGSV:%s' % (self.totGSV,self.curGSV))
        log.debug( 'lstSatellites:%d' % len(GPGSV.lstSatellites))
        log.debug( '_lstTempSats:%d' % len(GPGSV._lstTempSats))

    def __str__(self):
        return '%5s - %s' % ('GPGSV', ','.join(self.lst))

class GLGSV(GSV):
    """ === GSV - GPS Satellites in view ===
    """
    lstGLONASSSats = []
    _lstTempGLONASSSats = []
    
    @staticmethod
    def getSatellite(PRN):
        """ return satellite from lstSatellites with matching PRN """
        lst = [sat for sat in GLGSV.lstGLONASSSats if sat.prn == PRN]
        if len(lst) == 1:
            return lst[0]
        if len(lst) == 0:
            return None
        if len(lst) > 1:
            print 'getSatellite() ERROR - PRN exists for 2 satellites ... return 1st only'
            return lst[0]

    def __init__(self, msg):
        GSV.__init__(self, msg)
        self.process()

    def process(self):
        if self.totSatView == 0:
            GLGSV.lstGLONASSSats = []
            GLGSV._lstTempGLONASSSats= []
        else:
            GLGSV._lstTempGLONASSSats.extend( self.lstSats )
            if self.curGSV == self.totGSV:
                GLGSV.lstGLONASSSats = [sat for sat in GLGSV._lstTempGLONASSSats]
                GLGSV._lstTempGLONASSSats = []
        log.debug( 'totGSV:%s curGSV:%s' % (self.totGSV,self.curGSV))
        log.debug( 'lstGLONASSSats:%d' % len(GLGSV.lstGLONASSSats))
        log.debug( '_lstTempGLONASSSats:%d' % len(GLGSV._lstTempGLONASSSats))

    def __str__(self):
        return '%5s - %s' % ('GLGSV', ','.join(self.lst))

class GSA(GPS):
    """ Abstract class
	=== GSA - GPS DOP and active satellites ===

	------------------------------------------------------------------------------
		    1 2 3                        14 15  16  17  18
		    | | |                         |  |   |   |   |
	 $--GSA,a,a,x,x,x,x,x,x,x,x,x,x,x,x,x,x,x.x,x.x,x.x*hh<CR><LF>
	------------------------------------------------------------------------------

	Field Number: 

	1. Selection mode: M=Manual, forced to operate in 2D or 3D, A=Automatic, 3D/2D
	2. Mode (1 = no fix, 2 = 2D fix, 3 = 3D fix)
	3. ID of 1st satellite used for fix
	4. ID of 2nd satellite used for fix
	5. ID of 3rd satellite used for fix
	6. ID of 4th satellite used for fix
	7. ID of 5th satellite used for fix
	8. ID of 6th satellite used for fix
	9. ID of 7th satellite used for fix
	10. ID of 8th satellite used for fix
	11. ID of 9th satellite used for fix
	12. ID of 10th satellite used for fix
	13. ID of 11th satellite used for fix
	14. ID of 12th satellite used for fix
	15. PDOP
	16. HDOP
	17. VDOP
	18. Checksum        
    """
    def __init__(self, msg):
        GPS.__init__(self, msg)
        self.selMode = self.lst[1]
        self.mode = self.lst[2]
        self.lstSatIDs = []
        for val in self.lst[3:15]:
            try:
                prn = int(val)
                self.lstSatIDs.append(prn)
            except:
                pass
        log.debug('GSA - lstSatIDs:%s' % self.lstSatIDs)
        self.PDOP = self.lst[15]
        self.HDOP = self.lst[16]
        self.VDOP = self.lst[17]

    def __str__(self):
        return '%5s - %s' % ('--GSA', ','.join(self.lst))

class GPGSA(GSA):
    """ GPS satellites used only """
    def __init__(self, msg):
        GSA.__init__(self, msg)
        
    def __str__(self):
        return '%5s - %s' % ('GPGSA', ','.join(self.lst))

class GLGSA(GSA):
    """ GLONASS satellites used only """
    def __init__(self, msg):
        GSA.__init__(self, msg)
        
    def __str__(self):
        return '%5s - %s' % ('GLGSA', ','.join(self.lst))

class GNGSA(GSA):
    """ GPS/GLONASS active satellites 
        When both GPS and GLONASS satellite are used together in the position solution, 
        the talker identifier will be GN. In the third case, the receiver creates two 
        GSA sentences for every epoch. The first GNGSA sentence is used for GPS satellites 
        while the second one is for the GLONASS satellites. In the GSA message, the satellite 
        ID number of the GLONASS satellite is 64+ satellite slot number.
    """
    # We need to make sure we know the current 
    _GPS = None
    _GLONASS = None

    def __init__(self, msg):
        GSA.__init__(self, msg)
        # GNGSA will send 2 records; GPS followed by GLONASS
        if self._isGPS():
            self.gpsType = 'GPS'
            GNGSA._GPS = self
        else:
            self.gpsType = 'GLONASS'
            GNGSA._GLONASS = self

    def _isGPS(self):
        for satId in self.lstSatIDs:
            if Satellite.isGPS(satId):
                return True
            if Satellite.isGLONASS(satId):
                return False
        # should not get here
        s = 'GNGSA _isGPS() fail - could not determine GPS or GLONASS message type from Sat IDs *****'
        log.error(s)
        print '***** Error ' * s

    def __str__(self):
        return '%5s - %7s - %s' % ('GNGSA', self.gpsType, ','.join(self.lst))

class GPGGA(GPS):
    """ === GSA - Global positioning system fix data ===

        Time, Position and fix related data for a GPS receiver.

        ------------------------------------------------------------------------------
                                                              11
                1         2       3 4        5 6 7  8   9  10 |  12 13  14   15
                |         |       | |        | | |  |   |   | |   | |   |    |
         $--GGA,hhmmss.ss,llll.ll,a,yyyyy.yy,a,x,xx,x.x,x.x,M,x.x,M,x.x,xxxx*hh<CR><LF>
        ------------------------------------------------------------------------------

        Field Number: 

        1. Universal Time Coordinated (UTC)
        2. Latitude
        3. N or S (North or South)
        4. Longitude
        5. E or W (East or West)
        6. GPS Quality Indicator,
             - 0 - fix not available,
             - 1 - GPS fix,
             - 2 - Differential GPS fix
                   (values above 2 are 2.3 features)
             - 3 = PPS fix
             - 4 = Real Time Kinematic
             - 5 = Float RTK
             - 6 = estimated (dead reckoning)
             - 7 = Manual input mode
             - 8 = Simulation mode
        7. Number of satellites in view, 00 - 12
        8. Horizontal Dilution of precision (meters)
        9. Antenna Altitude above/below mean-sea-level (geoid) (in meters)
        10. Units of antenna altitude, meters
        11. Geoidal separation, the difference between the WGS-84 earth
             ellipsoid and mean-sea-level (geoid), "-" means mean-sea-level
             below ellipsoid
        12. Units of geoidal separation, meters
        13. Age of differential GPS data, time in seconds since last SC104
             type 1 or 9 update, null field when DGPS is not used
        14. Differential reference station ID, 0000-1023
        15. Checksum
    """
    def __init__(self, msg):
        GPS.__init__(self, msg)
        self.UTC = self.lst[1]
        self.latitude = self.lst[2]
        self.NorS = self.lst[3]
        self.longitude = self.lst[4]
        self.EorW = self.lst[5]
        self.GPSQual = self.lst[6]
        self.numSatsView = int(self.lst[7])
        #if self.numSatsView > 12:
            #log.warn( 'GPGGA() -- numSatsView = %d -- Max is 12, setting to Max' % self.numSatsView)
            #self.numSatsView = 12

    def __str__(self):
        return '%5s - %s' % ('GPGGA', ','.join(self.lst))

class RMC(GPS):
    """ Abstract class
    === RMC - Recommended Minimum Navigation Information ===

    ------------------------------------------------------------------------------
                                                              12
            1         2 3       4 5        6  7   8   9    10 11|  13
            |         | |       | |        |  |   |   |    |  | |   |
     $--RMC,hhmmss.ss,A,llll.ll,a,yyyyy.yy,a,x.x,x.x,xxxx,x.x,a,m,*hh<CR><LF>
    ------------------------------------------------------------------------------

    Field Number:

    1. UTC Time
    2. Status, V=Navigation receiver warning A=Valid
    3. Latitude
    4. N or S
    5. Longitude
    6. E or W
    7. Speed over ground, knots
    8. Track made good, degrees true
    9. Date, ddmmyy
    10. Magnetic Variation, degrees
    11. E or W
    12. FAA mode indicator (NMEA 2.3 and later)
    13. Checksum

    A status of V means the GPS has a valid fix that is below an internal
    quality threshold, e.g. because the dilution of precision is too high 
    or an elevation mask test failed.
    """
    def __init__(self, msg):
        GPS.__init__(self, msg)
        self.UTC = self.lst[1]
        self.status = self.lst[2]
        self.latitude = self.lst[3]
        self.NorS = self.lst[4]
        self.longitude = self.lst[5]
        self.EorW = self.lst[6]
        self.speed = self.lst[7]
        self.track = self.lst[8]
        self.date = self.lst[9]

    def getUTC(self):
        """ return the UTC time as a python datetime. """ 
        # get date/time
        try:
            year = int(self.date[4:6]) + 2000
            month = int(self.date[2:4])
            day = int(self.date[0:2])
            hour = int(self.UTC[0:2])
            minute = int(self.UTC[2:4])
            second = int(self.UTC[4:6])
            return datetime.datetime(year=year,month=month,day=day,hour=hour,minute=minute,second=second, tzinfo=UTC() )
        except Exception,err:
            log.error( 'getUTC() fail - %s'  % err)
            return None

    def __str__(self):
        return '%5s - %s' % ('--RMC', ','.join(self.lst))
        #return '%5s - date:%s time:%s UTC:%s' % ('GPRMC', self.date, self.UTC, self.getUTC())

class GPRMC(RMC):
    """ GPS RMS message """
    def __init__(self, msg):
        RMC.__init__(self, msg)

    def __str__(self):
        return '%5s - %s' % ('GPRMC', ','.join(self.lst))
        #return '%5s - date:%s time:%s UTC:%s' % ('GPRMC', self.date, self.UTC, self.getUTC())

class GNRMC(RMC):
    """ GPS/GLONASS RMS message """
    def __init__(self, msg):
        RMC.__init__(self, msg)

    def __str__(self):
        return '%5s - %s' % ('GNRMC', ','.join(self.lst))
        #return '%5s - date:%s time:%s UTC:%s' % ('GPRMC', self.date, self.UTC, self.getUTC())

class GLL(GPS):
    """ Abstract base class for GLL - Geographic Position - Latitude/Longitude ===
	------------------------------------------------------------------------------
		1       2 3        4 5         6 7   8
		|       | |        | |         | |   |
	 $--GLL,llll.ll,a,yyyyy.yy,a,hhmmss.ss,a,m,*hh<CR><LF>
	------------------------------------------------------------------------------
	Field Number: 

	1. Latitude
	2. N or S (North or South)
	3. Longitude
	4. E or W (East or West)
	5. Universal Time Coordinated (UTC)
	6. Status A - Data Valid, V - Data Invalid
	7. FAA mode indicator (NMEA 2.3 and later)
	8. Checksum
    """
    def __init__(self, msg):
        GPS.__init__(self, msg)
        self.latitude = self.lst[1]
        self.NorS = self.lst[2]
        self.longitude = self.lst[3]
        self.EorW = self.lst[4]
        self.UTC = self.lst[5]

    def __str__(self):
        return '%5s - %s' % ('--GLL', ','.join(self.lst))

class GPGLL(GLL):
    """ GPS Geographic Position - Latitude/Longitude """
    def __init__(self, msg):
        GLL.__init__(self, msg)

    def __str__(self):
        return '%5s - %s' % ('GPGLL', ','.join(self.lst))

class GNGLL(GLL):
    """ GPS/GLONASS Geographic Position - Latitude/Longitude """
    def __init__(self, msg):
        GLL.__init__(self, msg)

    def __str__(self):
        return '%5s - %s' % ('GNGLL', ','.join(self.lst))

_dctNMEA = {
  'GPGSV' : GPGSV,  # GPS messages
  'GPGSA' : GPGSA,
  'GPGGA' : GPGGA,
  'GPRMC' : GPRMC,
  'GPGLL' : GPGLL,

  'GNGLL' : GNGLL,   # GPS/GLONASS messages
  'GNGSA' : GNGSA,
  'GNRMC' : GNRMC,

  'GLGSA' : GLGSA,   # GLONASS messages
  'GLGSV' : GLGSV,
 }

def parseGPSMessages( lstMsgs ):
    lstGPSRecs = []
    for msg in lstMsgs:
        try:
            lst = msg.split(',')
            if len(lst) > 1 and len(lst[0]) > 1 and lst[0][0] == '$':
                nmea = lst[0][1:]
                if nmea in _dctNMEA:
                    rec = _dctNMEA[nmea](msg)
                else:
                    rec = GPS( msg )
                lstGPSRecs.append( rec )
        except Exception,err:
            log.error( 'GPS parse fail - %s' % err)
            log.error( 'msg:%s' % msg )
    return lstGPSRecs

class GPSData(object):
    """
       Create GPS data object from gpsdata file. Expected format:
       GGA:2014.01.07-14:11:40,223900.000,3717.1137,N,12156.6299,W,2
       DOP:3,1.84,1.02,1.52,3.825,3.825,8.74,8.74
       SAT:^\31,56,137,46
       SAT:^\32,51,314,51
       SAT:^\11,48,262,51
       SAT:^\01,45,303,46
       SAT:^\14,42,045,48
       SAT:^\46,39,143,44
       SAT:^\22,26,100,33
       SAT:^\20,16,299,45
       SAT:^\19,15,228,49
       SAT:^\25,06,077,
       SAT:^\23,05,244,40
    """
    _dctGGAFix  = { 0:'invalid', 1:'GPS', 2:'DGPS' }
    _dctDOPMode = { 1:'invalid', 2:'2-D', 3:'3-D' }

    def __init__(self, lstData):
        self.lstData = lstData
        self.lstSats = []
        for line in self.lstData:
            # remove the ^\
            line = line.replace( '\x1c','')
            logGpsData.debug( line )
            if line[0:4] == 'SAT:':
                lst = line[4:].split(',')
                if lst:
                    prn = lst[0]
                    ele = None
                    azi = None
                    snr = None
                    if len(lst) > 1: ele = lst[1]
                    if len(lst) > 2: azi = lst[2]
                    if len(lst) > 3: snr = lst[3]
                    if prn:
                        sat = Satellite( prn, ele, azi, snr)
                        self.lstSats.append( sat )
            elif line[0:4] == 'GGA:':
                lst = line[4:].split(',')
                if len(lst) in [6,7,8]:
                    curTime = lst[0].replace('-','_')
                    curTime = curTime.replace('.','-')
                    self.curTime = parseTimeString( curTime )
                    self.fix = self._dctGGAFix.get( int(lst[5]), lst[5])
                    self.longitude = None
                    self.latitude = None
                    self.NorS = None
                    self.EorW = None
                    if lst[1] and lst[3] and self.fix:
                        self.longitude = self._convToDeg(float(lst[1]) / 100)
                        self.NorS = lst[2]
                        self.latitude = self._convToDeg(float(lst[3]) / 100)
                        self.EorW = lst[4]
            elif line[0:4] == 'DOP:':
                self.dctDOP = {}
                lst = line[4:].split(',')
                if len(lst) == 8:
                    mode = int(lst[0])
                    self.dctDOP['mode'] = self._dctDOPMode.get( mode, lst[0])
                    if mode > 1:
                        self.dctDOP['PDOP'] = float(lst[1])
                        self.dctDOP['HDOP'] = float(lst[2])
                        self.dctDOP['VDOP'] = float(lst[3])
                        self.dctDOP['epx']  = float(lst[4])
                        self.dctDOP['epy']  = float(lst[5])
                        self.dctDOP['epv']  = float(lst[6])
                        self.dctDOP['epe']  = float(lst[7])

    def _convToDeg(self, value):
        """ The fractional part is in minutes [0.0-59.9], convert to degrees [0.0-99.9] """
        frac,num = math.modf(value)
        return num + frac / 60.0



def processGPSData(lst):
    """ process the lines from reading the gpsdata file on DUT 
        return a GPSData object
    """
    pass


import socket
class TelnetConn(object):
    _TIMEOUT = 0.5
    _HOST = 'localhost'
    _PORT = 23
    _PROMPT = 'quantenna #'

    def __init__(self, dct):
        self.host = dct.get( 'host', TelnetConn._HOST) 
        self.port = int(dct.get( 'port', TelnetConn._PORT))
        self.timeout = float(dct.get( 'timeout', TelnetConn._TIMEOUT))
        self.prompt = dct.get( 'prompt', TelnetConn._PROMPT) 
        self.sock = None
        self._resp = ''

    def connect(self):
        """ Perform all setup operations for communicating with the simulator. """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('Connecting to %s:%d' % (self.host, self.port))
        self.sock.settimeout( self.timeout )
        self.sock.connect((self.host, self.port))

    def close(self):
        """ Disconnect from the simulator. """
        if self.sock:
            self.sock.close()
            self.sock = None

    def recv(self):
        """ Receive data from socket. """
        try:
            recv = self.sock.recv(8*1024)
            return recv
        except socket.timeout, err:
            return None

    def send(self, binData):
        """ Write data to the socket. """
        self.sock.send(binData)

    def readUntil(self, timeout=5.0):
        """ read until prompt is returned """
        # make a timeout
        dtTimeout = datetime.datetime.now() + datetime.timedelta( seconds=timeout)
        while True:
            resp = self.recv()
            if resp is not None:
                self._resp += resp
                index = self._resp.find( self.prompt )
                if index != -1:
                    index += len(self.prompt)
                    resp = self._resp[0:index]
                    self._resp = self._resp[index+1:]
                    return resp
            if datetime.datetime.now() > dtTimeout:
                print 'readUntil() fail -- timeout after %s seconds' % timeout
                return ''


import serial
class SerialConn(object):
    """ Uses a serial port for all communication """ 
    _BAUDRATE = 115200
    _TIMEOUT  = 0.5
    _PORT = 6
    _PROMPT = 'quantenna #'

    def __init__(self, dct ):
        self.port = int(dct.get( 'port', SerialConn._PORT))
        self.timeout = float(dct.get( 'timeout', SerialConn._TIMEOUT))
        self.baudrate = int(dct.get( 'baudrate', SerialConn._BAUDRATE))
        self.ser = None
        self._resp = ''

    def connect(self):
        """ Perform all setup operations for communicating with the simulator. """
        print('Connecting to COM%d' % (self.port))
        self.ser = serial.Serial(self.port-1)
        self.ser.timeout = self.timeout
        self.ser.baudrate = self.baudrate

    def close(self):
        """ Disconnect from the simulator. """
        if self.ser:
            self.ser.close()
            self.ser = None

    def send(self, cmd):
        self.ser.write(cmd)

    def recv(self):
        """ Read data from the serial port """
        dtTimeout = datetime.datetime.now() + datetime.timedelta(seconds=self.ser.timeout)
        while True:
            if self.ser.inWaiting() > 0:
                recv = self.ser.read(self.ser.inWaiting())
                return recv
            if datetime.datetime.now() > dtTimeout:
                return None
            time.sleep( 0.05 )

    def readUntil(self, timeout=5.0):
        """ read until prompt is returned """
        # make a timeout
        dtTimeout = datetime.datetime.now() + datetime.timedelta( seconds=timeout)
        while True:
            resp = self.recv()
            if resp is not None:
                self._resp += resp
                index = self._resp.find( self.prompt )
                if index != -1:
                    index += len(self.prompt)
                    resp = self._resp[0:index]
                    self._resp = self._resp[index+1:]
                    return resp
            if datetime.datetime.now() > dtTimeout:
                print 'readUntil() fail -- timeout after %s seconds' % timeout
                return ''

class FileConn(object):
    _FILENAME = 'gps_input.txt'

    def __init__(self, dct):
        self.filename = dct.get( 'filename', FileConn._FILENAME) 
        self._fp = None

    def connect(self):
        """ Perform all setup operations for communicating with the simulator. """
        print('Opening file %s' % (self.filename))
        self._fp = open(self.filename)

    def close(self):
        """ Disconnect from the simulator. """
        if self._fp:
            self._fp.close()
            self._fp = None

    def recv(self):
        """ Receive data from socket. """
        recv = self._fp.readline()
        if recv == '':
            raise Exception('No more lines in file %s' % self.filename)
        log.debug('recv:%s' % recv)
        return recv

    def send(self, binData):
        """ Write data to the socket. """
        raise Exception( 'WE SHOULD NOT BE WRITING HERE' )

class GPSD(object):
    """ base class for all GPSD JSON messages """
    def __init__(self, json):
        self.json = json
        
    def getMsgType(self):
        return self.json['class']
    
    def __str__(self):
        return 'GPSD %s' % (self.getMsgType())

class GPSD_SKY(GPSD):
    """ SKY messages """
    def __init__(self, json):
        GPSD.__init__(self, json)
        self.lstSats = []
        for key,value in self.json.items():
            if key == 'satellites':
                self.lstSats = [Satellite( dct['PRN'], dct['el'], dct['az'], dct['ss'], dct['used']) for dct in value]
            else:
                setattr( self, key, value )
        
    def __str__(self):
        return 'SKY - sats:%d' % (len(self.lstSats))

class GPSD_TPV(GPSD):
    """ SKY messages """
    def __init__(self, json):
        GPSD.__init__(self, json)
        for key,value in self.json.items():
            if key == 'time':
                #  Expect format 2013-09-01T00:34:02.000Z
                year = value[0:4]
                month = value[5:7]
                day = value[8:10]
                hour = value[11:13]
                minute = value[14:16]
                second = value[17:19]
                self.time = datetime.datetime(year=int(year),month=int(month),day=int(day),
                                              hour=int(hour),minute=int(minute),second=int(second), tzinfo=UTC() )
            else:
                setattr( self, key, value )

    def __str__(self):
        return 'TPV - time:%s' % getattr( self, 'time', None)

import json
class GPSDConn(object):
    """ Use a socket to communicate with gpsd process """
    _TIMEOUT = 0.5
    _HOST = '192.168.1.100'
    _PORT = 2947

    def __init__(self, dct):
        self.host = dct.get( 'host', GPSDConn._HOST) 
        self.port = int(dct.get( 'port', GPSDConn._PORT))
        self.timeout = float(dct.get( 'timeout', GPSDConn._TIMEOUT))
        self.sock = None
        self._resp = ''

    def connect(self):
        """ Perform all setup operations for communicating with the simulator. """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        logGPSD.info( 'Connecting to %s:%d' % (self.host, self.port))
        self.sock.settimeout( self.timeout )
        self.sock.connect((self.host, self.port))

    def close(self):
        """ Disconnect from the simulator. """
        if self.sock:
            self.sock.close()
            self.sock = None

    def recv(self):
        """ Receive data from socket. """
        try:
            recv = self.sock.recv(8*1024)
            hexDump( recv, msg='recv', logFunc=logGPSD.debug )
            return recv
        except socket.timeout, err:
            return None

    def send(self, binData):
        """ Write data to the socket. """
        hexDump( binData, msg='send', logFunc=logGPSD.debug )
        self.sock.send(binData)

    def enableJSONData(self):
        # send command to start receiving the data
        self.send( '?WATCH={"enable":true,"json":true}\n' )

    def disableJSONData(self):
        # send command to start receiving the data
        self.send( '?WATCH={"enable":false,"json":true}\n' )

    def readMsgs(self, timeout=5.0):
        """ read and parse into messages """
        # make a timeout
        dtTimeout = datetime.datetime.now() + datetime.timedelta( seconds=timeout)
        while True:
            resp = self.recv()
            if resp is not None:
                #self._resp += resp
                #lst = self._resp.split( '\r\n' )
                lst = resp.split( '\r\n' )
                if lst:
                    for n,msg in enumerate(lst):
                        #print 'Msg %d : length=%d' % (n,len(msg))
                        hexDump( msg, msg='msg %d' % n, logFunc=logGPSD.debug )
                    # remove 0 length messages
                    lst = [msg for msg in lst if len(msg) > 0]
                    lstJS = []
                    for msg in lst:
                        try:
                            dct = json.loads( msg )
                            js = self._parseGPSJson( dct )
                            lstJS.append( js )
                        except Exception,err:
                            #print '\nEXCEPTION : %s' % err
                            logGPSD.error( 'readMsgs() fail - %s' % err )
                    return lstJS
            if datetime.datetime.now() > dtTimeout:
                logGPSD.warn('readMsgs() fail -- timeout after %s seconds .. return empty list' % timeout)
                return []

    def _parseGPSJson( self, js ):
        rec = None
        try:
            if js['class'] == 'SKY':
                rec = GPSD_SKY( js ) 
            elif js['class'] == 'TPV':
                rec = GPSD_TPV( js )
            else:
                rec = GPSD( js )
        except Exception,err:
            logGPSD.error( '_parseGPSJson() fail - %s' % err)
        return rec

def dumpResp( lst, decode=True ):
    print( '\nlst:%s' % lst )
    for gpsdMsg in lst:
        print( 'gpsdMsg:%s' % gpsdMsg )
        if gpsdMsg.getMsgType() == 'SKY':
            for n,sat in enumerate(gpsdMsg.lstSats):
                print('  %2d : %s' % (n+1, sat))
        elif gpsdMsg.getMsgType() == 'TPV':
            for key,value in gpsdMsg.json.items():
                print '    %-15s : %s' % (key,value)

def testGPSDComm(host=None, port=None):
    """ testing GPSDComm """
    dct = {}
    if host is not None:
        dct['host'] = host
    if port is not None:
        dct['port'] = port
    gpsd = None
    try:
        gpsd = GPSDConn( dct )
        gpsd.connect()
        print
        lst = gpsd.readMsgs()
        dumpResp( lst )
        print
        # send command to start receiving the data
        gpsd.enableJSONData()
        lst = gpsd.readMsgs()
        dumpResp( lst )
        while True:
            lst = gpsd.readMsgs()
            if lst:
                dumpResp( lst )
            else:
                time.sleep( 0.5 )

    finally:
        if gpsd:
            gpsd.disableJSONData()
            gpsd.close()


def getStatus(conn2):
    # Now send the status
    cmd = 'gpsdoctl2 ST'
    #print '\nsending %s to conn2' % cmd
    conn2.send( '%s\n' % cmd )
    time.sleep( 0.1 )
    recv = conn2.readUntil()
    #print 'recv: %s' % recv
    if recv == '':
        print '***** Error -- no data in response'
        return None
    # parse to get last byte
    lst = str(recv).split('\n')
    lst = [line.strip() for line in lst]
    #print 'lst:%s' % lst
    if lst[2] == 'quantenna #' and lst[0] == cmd:
        lst2 = lst[1].split()
        if len(lst2) != 7:
            print '***** Error parsing the %s response -- length != 7' % cmd
            return None
        return lst2
    else:
        print '***** Error parsing the %s response' % cmd
        return None

def dumpResults(csv2File, gga, gsa, los, los2, lstGpsSNR, lstGlonassSNR, lstUsedSats ):
    """ dump results to CSV file and stdout """
    # calc averages
    snrGPS     = 0.0
    snrGLONASS = 0.0
    snrAvg     = 0.0

    if lstGpsSNR:
        snrGPS     = sum(lstGpsSNR) / len(lstGpsSNR)
    if lstGlonassSNR:
        snrGLONASS = sum(lstGlonassSNR) / len(lstGlonassSNR)
    lstSNR     = lstGpsSNR + lstGlonassSNR
    if lstSNR:
        snrAvg     = sum(lstSNR) / len(lstSNR)

    # build CSV output
    line2 = '%s,%s,%s,%s' % (gga.UTC, gsa.mode, los, los2)
    line2 += ',%s'   % (len(GPGSV.lstSatellites) + len(GLGSV.lstGLONASSSats))     # total sats in sky
    line2 += ',%s'   % (len(lstSNR))                                              # total sats used
    line2 += ',%.1f' % (snrAvg)                                                   # SNR for all sats used
    line2 += ',%s'   % (len(lstGpsSNR))                                           # total GPS sats used
    line2 += ',%.1f' % (snrGPS)                                                   # SNR for GPS sats used
    line2 += ',%s'   % (len(lstGlonassSNR))                                       # total GLONASS sats used
    line2 += ',%.1f' % (snrGLONASS)                                               # SNR for GLONASS sats used
    for sat in lstUsedSats:
        line2 += ',%s,%s' % (sat.prn, sat.snr)
    csv2File.write( line2 + '\n' )
    # dump to stdout 
    print '  los:%s los2:%s' % (los,los2)
    print '  GPS sats %d' % len(GPGSV.lstSatellites)
    for sat in GPGSV.lstSatellites:
        print '    %-7s : %s' % ('GPS',sat.desc())
    print '  GLONASS sats %d' % len(GLGSV.lstGLONASSSats)
    for sat in GLGSV.lstGLONASSSats:
        print '    %-7s : %s' % ('GLONASS',sat.desc())
    print
    print '  Sats %-7s : %5d (%2d)' % ('GPS',len(GPGSV.lstSatellites), len([sat for sat in GPGSV.lstSatellites if sat.used]))
    print '  Sats %-7s : %5d (%2d)' % ('GLONASS',len(GLGSV.lstGLONASSSats), len([sat for sat in GLGSV.lstGLONASSSats if sat.used]))
    print '  SNR  %-7s : %.2f (%2d) ' % ('GPS', snrGPS, len(lstGpsSNR))
    print '  SNR  %-7s : %.2f (%2d) ' % ('GLONASS', snrGLONASS, len(lstGlonassSNR))
    print '  SNR  %-7s : %.2f (%2d) ' % ('All', snrAvg, len(lstSNR))

def processGPSMessages(dctRecs, conn2, gpsFile, csvFile, csv2File):
    """ """
    try:
        gga = dctRecs['GPGGA']
        gsa = dctRecs['GPGSA']
    except KeyError,err:
        print 'Missing GPGGA or GPGSA. Skipping ...'
        return

    lstStatus = []
    los = 'x'
    if conn2:
        # Now send the status
        lstStatus = getStatus( conn2 )
        if lstStatus:
            los = lstStatus[6][-1]

    if gpsFile:
        gpsFile.write( 'PICStatus : %s\n' % ','.join( lstStatus) )

    print '  PROCESS GPS only'
    s = 'UTC:%s mode:%s los:%s numsats:%s' % (gga.UTC, gsa.mode, los, len(GPGSV.lstSatellites))
    line  = '%s,%s,%s,%s' % (gga.UTC, gsa.mode, los, len(GPGSV.lstSatellites))

    for sat in GPGSV.lstSatellites:
        s += ' [%s,%s]' % (sat.prn, sat.snr)
        line += ',%s,%s' % (sat.prn, sat.snr)
    #print '  ', s
    #print '  ', line
    if csvFile:
        csvFile.write( line + '\n' )

    # for 2nd CSV output file
    if csv2File:
        if los != 'x' and int( los, 16) > 7:
            los2 = 1
        else:
            los2 = 0
        lstUsedSats = []
        lstSNR = []
        for n in range(gga.numSatsView):
            PRN = gsa.lstSatIDs[n]
            sat = GPGSV.getSatellite( PRN )
            sat.used = True
            lstUsedSats.append( sat )
            if sat.snr is not None:
                lstSNR.append( float(sat.snr))
            else:
                logError( 'sat has no SNR - skipping for calculation - %s' % sat)
        #
        dumpResults(csv2File, gga, gsa, los, los2, lstSNR, [], lstUsedSats )

        #snrAvg = sum(lstSNR) / len(lstSNR)
        #line2 = '%s,%s,%s,%s,%s,%s,%.1f' % (gga.UTC, gsa.mode, los, los2, len(GPGSV.lstSatellites), gga.numSatsView, snrAvg)
        #for sat in lstUsedSats:
            #line2 += ',%s,%s' % (sat.prn, sat.snr)
        #csv2File.write( line2 + '\n' )

def logError( msg ):
    log.error(msg) 
    print '***** ERROR - ' + msg

def processGPSGLONASSMessages(dctRecs, conn2, gpsFile, csvFile, csv2File):
    """ Process GPS/GLONASS combined messages """
    sat = None
    gga = None
    gsa = None
    if 0:
        assert isinstance(gga, GPGGA)
        assert isinstance(gsa, GNGSA)
        assert isinstance(sat, Satellite)

    try:
        gga = dctRecs['GPGGA']
        gsa = dctRecs['GNGSA']
    except KeyError,err:
        logError( 'Process GPS/GLONASS fail -- Missing GPGGA or GNGSA -- Skipping ...')
        return

    lstStatus = []
    los = 'x'
    if conn2:
        # Now send the status
        lstStatus = getStatus( conn2 )
        if lstStatus:
            los = lstStatus[6][-1]

    if gpsFile:
        gpsFile.write( 'PICStatus : %s\n' % ','.join( lstStatus) )

    print '\n  PROCESSING GPS/GLONASS...'
    s = 'UTC:%s mode:%s los:%s numsats:%s' % (gga.UTC, gsa.mode, los, len(GPGSV.lstSatellites)+len(GLGSV.lstGLONASSSats))
    line  = '%s,%s,%s,%s' % (gga.UTC, gsa.mode, los, len(GPGSV.lstSatellites)+len(GLGSV.lstGLONASSSats))
    # GPS sats
    for sat in GPGSV.lstSatellites:
        s += ' [%s,%s]' % (sat.prn, sat.snr)
        line += ',%s,%s' % (sat.prn, sat.snr)
    # add the GLONASS sats
    for sat in GLGSV.lstGLONASSSats:
        s += ' [%s,%s]' % (sat.prn, sat.snr)
        line += ',%s,%s' % (sat.prn, sat.snr)
    #print '  ', s
    #print '  ', line
    if csvFile:
        csvFile.write( line + '\n' )

    # for 2nd CSV output file
    if csv2File:
        if los != 'x' and int( los, 16) > 7:
            los2 = 1
        else:
            los2 = 0
        lstUsedSats = []
        lstGpsSNR = []
        lstGlonassSNR = []
        # GPS sats
        for PRN in gsa._GPS.lstSatIDs:
            sat = GPGSV.getSatellite( PRN )
            sat.used = True
            lstUsedSats.append( sat )
            if sat.snr is not None:
                lstGpsSNR.append( float(sat.snr))
            else:
                logError( 'sat has no SNR - skipping for calculation - %s' % sat)

        # GLONASS sats
        for PRN in gsa._GLONASS.lstSatIDs:
            sat = GLGSV.getSatellite( PRN )
            sat.used = True
            lstUsedSats.append( sat )
            if sat.snr is not None:
                lstGlonassSNR.append( float(sat.snr))
            else:
                logError( 'sat has no SNR - skipping for SNR calculation - %s' % sat)
        #
        dumpResults(csv2File, gga, gsa, los, los2, lstGpsSNR, lstGlonassSNR, lstUsedSats )

if __name__ == '__main__':
    TLLog.config( 'gps_test.log', defLogLevel=logging.INFO )

    import time
    from optparse import OptionParser

    DEF_PORT = 1
    DEF_OUTPUT_CSV_FILE = 'output.txt'
    DEF_OUTPUT2_CSV_FILE = 'output2.txt'
    DEF_OUTPUT_GPS_FILE = 'gps.txt'
    DEF_BAUDRATE = 9600
    DEF_TIMEOUT = 0.5
    DEF_IPADDR = '192.168.1.100'
    DEFAULT_LOG_ENABLE = 'gps'

    # build the command line arguments

    parser = OptionParser()
    parser.add_option( "-p",  "--port", dest="port", default=DEF_PORT,
                       help="set the com port to read GPS messages. Default is %d" % DEF_PORT)
    parser.add_option( "-f",  "--outputCSVFile", dest="outputCSVFile", default=DEF_OUTPUT_CSV_FILE,
                       help='Set the output CSV file. Default is %s' % DEF_OUTPUT_CSV_FILE )
    parser.add_option( '',  "--output2CSVFile", dest="output2CSVFile", default=DEF_OUTPUT2_CSV_FILE,
                       help='Set the output CSV file fro the 2nd CSV file. Default is %s' % DEF_OUTPUT2_CSV_FILE )
    parser.add_option( "-b",  "--baudrate", dest="baudrate", default=DEF_BAUDRATE,
                       help='Set the serial port baudrate. Default is %d' % DEF_BAUDRATE)
    parser.add_option( "-t",  "--timeout", dest="timeout", default=DEF_TIMEOUT,
                       help='Set the serial port timeout. Default is %s sec' % DEF_TIMEOUT)
    parser.add_option( "-g",  "--outputGPSFile", dest="outputGPSFile", default=DEF_OUTPUT_GPS_FILE,
                       help='Set the output GPS file. Default is %s' % DEF_OUTPUT_GPS_FILE )
    parser.add_option( "-a",  "--ipaddr", dest="ipaddr", default=DEF_IPADDR,
                       help='Set the IP address for the telnet connection. Default is %s sec' % DEF_IPADDR)
    parser.add_option( "",  "--gpsdTest", action="store_true", dest="gpsdTest", default=False,
                       help='Perform testing using the gpsd daemon on board. Default is False' )
    parser.add_option( "-m",  "--logEnable", dest="lstLogEnable", default=DEFAULT_LOG_ENABLE,
                       help='Comma separated list of log modules to enable, * for all. Default is "%s"' % DEFAULT_LOG_ENABLE)
    parser.add_option( "",  "--gpsTestFile", dest="gpsTestFile", default=None,
                       help='Set a file to input test GPS NMEA messages.' )

    #  parse the command line and set values
    (options, args) = parser.parse_args()

    # makes Control-break behave the same as Control-C on windows
    import signal
    signal.signal( signal.SIGBREAK, signal.default_int_handler )

    port = int(options.port)
    outputCSVFile = options.outputCSVFile
    output2CSVFile = options.output2CSVFile
    outputGPSFile = options.outputGPSFile
    baudrate = int(options.baudrate)
    timeout = float(options.timeout)
    ipaddr = options.ipaddr

    ser = None
    csvFile = None
    gsvFile = None
    csv2File = None
    gga = None
    gsa = None
    conn = None
    conn2 = None
    sat = None
    gpsFile = None
    parseMessages = True
    # for wing IDE object lookup, code does not need to be run
    if 0:
        assert isinstance(gga, GPGGA)
        assert isinstance(gsa, GPGSA)
        assert isinstance(sat, Satellite)

    try:
        log.info( '*********************************************' )
        log.info( 'GPS test starting .....' )
        # update log options
        logOptions(options.lstLogEnable)

        if options.gpsdTest:
            log.info( 'GPSD testing only .....' )
            testGPSDComm()

        if options.gpsTestFile:
            log.info( 'Using GPS input file %s ...' % options.gpsTestFile )
            dct = { 'filename' : options.gpsTestFile }  
            conn = FileConn( dct  )
            conn.connect()
        else:
            # use telnet 
            dct = { 'host' : ipaddr }  
            print 'Connecting telnet to %s for GPS ...' % ipaddr
            conn = TelnetConn( dct  )
            conn.connect()
            time.sleep(0.2)
            resp = conn.recv()
            print 'resp:%s' % resp
            conn.send( 'root\n' )
            time.sleep(0.2)
            resp = conn.readUntil()
            #resp = conn.recv()
            print 'resp:%s' % resp

            print 'Connecting telnet to %s for status ...' % ipaddr
            conn2 = TelnetConn( dct  )
            conn2.connect()
            time.sleep(0.2)
            resp = conn2.recv()
            print 'resp:%s' % resp
            conn2.send( 'root\n' )
            time.sleep(0.2)
            resp = conn2.readUntil()
            #resp = conn2.recv()
            print 'resp:%s' % resp
            # start the messages
            conn.send( 'cat /dev/ttyS1\n' )

        # open files append
        csvFile = open( outputCSVFile, 'a')
        gpsFile = open( outputGPSFile, 'a' )
        csv2File = open( output2CSVFile, 'a')

        #conn = SerialConn( port=port, baudrate=baudrate, timeout=timeout)

        respData = ''
        dctRecs = {}
        while True:
            recv = conn.recv()
            if recv is not None:
                try:
                    #print 'recv:%s' % recv
                    #print
                    if gpsFile:
                        gpsFile.write( recv )

                    # process the data
                    respData += recv
                    lst = respData.split('\n')
                    #print 'lst:%s' % lst
                    #print
                    respData = lst[-1]
                    lstRecs = parseGPSMessages( lst[:-1] )
                    for rec in lstRecs:
                        print '%s - %s' % (datetime.datetime.now() , rec)
                        if parseMessages:
                            dctRecs[ rec.getMsgType() ] = rec
                            if rec.getMsgType() == 'GPGLL':
                                processGPSMessages(dctRecs, conn2, gpsFile, csvFile, csv2File)
                            elif rec.getMsgType() == 'GNGLL':
                                processGPSGLONASSMessages(dctRecs, conn2, gpsFile, csvFile, csv2File)
                except Exception,err:
                    excTraceback( err, log, raiseErr=False)
                    #s = '%s: %s' % (err.__class__.__name__, err)
                    #log.error( s )
                    #print s

                    #print '-- traceback --'
                    #traceback.print_exc()
                    #print

                print
            time.sleep( 0.05 )

    except Exception, err:
        excTraceback( err, log, raiseErr=False)
        #s = '%s: %s' % (err.__class__.__name__, err)
        #log.error( s )
        #print s

        #print '-- traceback --'
        #traceback.print_exc()
        #print
 
    finally:
        if ser:
            ser.close()
        if gpsFile:
            gpsFile.close()
        if csvFile:
            csvFile.close()
        if csv2File:
            csv2File.close()
        log.info( 'gps_test exiting' )
