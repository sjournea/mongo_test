""" wlan_api.py - Windows Wlan Native API interface module """
import binascii
import re
import xml.etree.ElementTree as ET

from ctypes import *
from ctypes.wintypes import *

from xml_util import xmlString
from common import hexDump
from tl_logger import TLLog,logOptions

log = TLLog.getLogger( 'wlan' )

class WlanException(Exception):
    pass

def customresize(array, new_size):
    return (array._type_*new_size).from_address(addressof(array))

wlanapi = windll.LoadLibrary('wlanapi.dll')

ERROR_SUCCESS = 0

class GUID(Structure):
    _fields_ = [
        ('Data1', c_ulong),
        ('Data2', c_ushort),
        ('Data3', c_ushort),
        ('Data4', c_ubyte*8),
        ]

WLAN_INTERFACE_STATE = c_uint
(wlan_interface_state_not_ready,
 wlan_interface_state_connected,
 wlan_interface_state_ad_hoc_network_formed,
 wlan_interface_state_disconnecting,
 wlan_interface_state_disconnected,
 wlan_interface_state_associating,
 wlan_interface_state_discovering,
 wlan_interface_state_authenticating) = map(WLAN_INTERFACE_STATE, xrange(0, 8))

dctWlanInterfaceStates = { 
    0 : 'not ready',
    1 : 'connected',
    2 : 'ad_hoc_network_formed',
    3 : 'disconnecting',
    4 : 'disconnected',
    5 : 'associating',
    6 : 'discovering',
    7 : 'authenticating',
}

class WLAN_INTERFACE_INFO(Structure):
    _fields_ = [
        ("InterfaceGuid", GUID),
        ("strInterfaceDescription", c_wchar * 256),
        ("isState", WLAN_INTERFACE_STATE)
        ]

    def desc(self):
        return self.strInterfaceDescription

    def miniDesc(self):
        lst = self.strInterfaceDescription.split()
        return lst[0]
    
    def shortDesc(self):
        lst = self.strInterfaceDescription.split()
        if len(lst) == 0:
            desc = ''
        elif len(lst) == 1:
            desc = lst[0]
        else:
            desc = lst[0] + ' ' + lst[1]
        return desc[0:20]
    
    def getState(self):
        return dctWlanInterfaceStates[self.isState]
    
    def log(self):
        log.debug( 'desc:%s state:%s' % (self.desc(),self.getState()))
    
    def __str__(self):
        return self.shortDesc()

class WLAN_INTERFACE_INFO_LIST(Structure):
    _fields_ = [
        ("NumberOfItems", DWORD),
        ("Index", DWORD),
        ("InterfaceInfo", WLAN_INTERFACE_INFO * 1)
        ]

WLAN_MAX_PHY_TYPE_NUMBER = 0x8
DOT11_SSID_MAX_LENGTH = 32
WLAN_REASON_CODE = DWORD
DOT11_BSS_TYPE = c_uint
(dot11_BSS_type_infrastructure,
 dot11_BSS_type_independent,
 dot11_BSS_type_any) = map(DOT11_BSS_TYPE, xrange(1, 4))
DOT11_PHY_TYPE = c_uint
dot11_phy_type_unknown      = 0
dot11_phy_type_any          = 0
dot11_phy_type_fhss         = 1
dot11_phy_type_dsss         = 2
dot11_phy_type_irbaseband   = 3
dot11_phy_type_ofdm         = 4
dot11_phy_type_hrdsss       = 5
dot11_phy_type_erp          = 6
dot11_phy_type_ht           = 7
dot11_phy_type_IHV_start    = 0x80000000
dot11_phy_type_IHV_end      = 0xffffffff 

DOT11_AUTH_ALGORITHM = c_uint
DOT11_AUTH_ALGO_80211_OPEN         = 1
DOT11_AUTH_ALGO_80211_SHARED_KEY   = 2
DOT11_AUTH_ALGO_WPA                = 3
DOT11_AUTH_ALGO_WPA_PSK            = 4
DOT11_AUTH_ALGO_WPA_NONE           = 5
DOT11_AUTH_ALGO_RSNA               = 6
DOT11_AUTH_ALGO_RSNA_PSK           = 7
DOT11_AUTH_ALGO_IHV_START          = 0x80000000
DOT11_AUTH_ALGO_IHV_END            = 0xffffffff

DOT11_CIPHER_ALGORITHM = c_uint
DOT11_CIPHER_ALGO_NONE            = 0x00
DOT11_CIPHER_ALGO_WEP40           = 0x01
DOT11_CIPHER_ALGO_TKIP            = 0x02
DOT11_CIPHER_ALGO_CCMP            = 0x04
DOT11_CIPHER_ALGO_WEP104          = 0x05
DOT11_CIPHER_ALGO_WPA_USE_GROUP   = 0x100
DOT11_CIPHER_ALGO_RSN_USE_GROUP   = 0x100
DOT11_CIPHER_ALGO_WEP             = 0x101
DOT11_CIPHER_ALGO_IHV_START       = 0x80000000
DOT11_CIPHER_ALGO_IHV_END         = 0xffffffff 

WLAN_AVAILABLE_NETWORK_CONNECTED = 1
WLAN_AVAILABLE_NETWORK_HAS_PROFILE = 2

WLAN_AVAILABLE_NETWORK_INCLUDE_ALL_ADHOC_PROFILES = 0x00000001
WLAN_AVAILABLE_NETWORK_INCLUDE_ALL_MANUAL_HIDDEN_PROFILES = 0x00000002

class DOT11_SSID(Structure):
    _fields_ = [
        ("SSIDLength", c_ulong),
        ("SSID", c_char * DOT11_SSID_MAX_LENGTH)
        ]
    
    def __str__(self):
        return self.SSID[0:self.SSIDLength]
    
class WLAN_AVAILABLE_NETWORK(Structure):
    _fields_ = [
        ("ProfileName", c_wchar * 256),
        ("dot11Ssid", DOT11_SSID),
        ("dot11BssType", DOT11_BSS_TYPE),
        ("NumberOfBssids", c_ulong),
        ("NetworkConnectable", c_bool),
        ("wlanNotConnectableReason", WLAN_REASON_CODE),
        ("NumberOfPhyTypes", c_ulong),
        ("dot11PhyTypes", DOT11_PHY_TYPE * WLAN_MAX_PHY_TYPE_NUMBER),
        ("MorePhyTypes", c_bool),
        ("wlanSignalQuality", c_ulong),
        ("SecurityEnabled", c_bool),
        ("dot11DefaultAuthAlgorithm", DOT11_AUTH_ALGORITHM),
        ("dot11DefaultCipherAlgorithm", DOT11_CIPHER_ALGORITHM),
        ("Flags", DWORD),
        ("Reserved", DWORD)
        ]
    
    def getProfileName(self):
        return self.ProfileName
    
    def getSSID(self):
        return self.dot11Ssid
    
    def getSignalQuality(self):
        """ return signal quality """
        return self.wlanSignalQuality
    
    def getSignalQualityInDBM(self):
        """ return signal quality in dbm.
            wlanSignalQuality is percentage value that represents the signal quality of the network. 
            WLAN_SIGNAL_QUALITY is of type ULONG. This member contains a value between 0 and 100. 
            A value of 0 implies an actual RSSI signal strength of -100 dbm. 
            A value of 100 implies an actual RSSI signal strength of -50 dbm. 
            You can calculate the RSSI signal strength value for wlanSignalQuality values between 1 and 99 
            using linear interpolation."""
        return (float(self.wlanSignalQuality) / 2.0) - 100.0  
    

    def isConnectable(self):
        return self.NetworkConnectable

    def isConnected(self):
        return self.Flags & WLAN_AVAILABLE_NETWORK_CONNECTED

    def hasProfile(self):
        return self.Flags & WLAN_AVAILABLE_NETWORK_HAS_PROFILE
    
    def isSecure(self):
        return self.SecurityEnabled
    
    def log(self):
        log.debug( 'signal:%s (%f dbm)' % (self.getSignalQuality(),self.getSignalQualityInDBM()))
    
    def __str__(self):
        return 'ProfileName:%s ssid:%s bssType:%s' % (self.ProfileName,self.dot11Ssid,self.dot11BssType)
    
class WLAN_AVAILABLE_NETWORK_LIST(Structure):
    _fields_ = [
        ("NumberOfItems", DWORD),
        ("Index", DWORD),
        ("Network", WLAN_AVAILABLE_NETWORK * 1),
        ]

WlanOpenHandle = wlanapi.WlanOpenHandle
WlanOpenHandle.argtypes = (DWORD, c_void_p, POINTER(DWORD), POINTER(HANDLE))
WlanOpenHandle.restype = DWORD

WlanCloseHandle = wlanapi.WlanCloseHandle
WlanCloseHandle.argtypes = (HANDLE,c_void_p)
WlanCloseHandle.restype = DWORD

WlanEnumInterfaces = wlanapi.WlanEnumInterfaces
WlanEnumInterfaces.argtypes = (HANDLE, c_void_p, 
                               POINTER(POINTER(WLAN_INTERFACE_INFO_LIST)))
WlanEnumInterfaces.restype = DWORD

WlanGetAvailableNetworkList = wlanapi.WlanGetAvailableNetworkList
WlanGetAvailableNetworkList.argtypes = (HANDLE, POINTER(GUID), DWORD, c_void_p, 
                                        POINTER(POINTER(WLAN_AVAILABLE_NETWORK_LIST)))
WlanGetAvailableNetworkList.restype = DWORD

WlanFreeMemory = wlanapi.WlanFreeMemory
WlanFreeMemory.argtypes = [c_void_p]

WlanDisconnect = wlanapi.WlanDisconnect
WlanDisconnect.argtypes = (HANDLE, POINTER(GUID), c_void_p)
WlanDisconnect.restype = DWORD

WLAN_CONNECTION_MODE = c_ubyte
wlan_connection_mode_profile = 0
wlan_connection_mode_temporary_profile = 1
wlan_connection_mode_discovery_secure = 2
wlan_connection_mode_discovery_unsecure = 3
wlan_connection_mode_auto = 4
wlan_connection_mode_invalid = 5

class NDIS_OBJECT_HEADER(Structure):
    """ 
    typedef struct _NDIS_OBJECT_HEADER {
      UCHAR  Type;
      UCHAR  Revision;
      USHORT Size;
    } NDIS_OBJECT_HEADER, *PNDIS_OBJECT_HEADER;
    """
    _fields_ = [
        ("Type", c_ubyte),
        ("Revision", c_ubyte),
        ("Size", USHORT),
    ]
    
class DOT11_MAC_ADDRESS(Structure):
    """ 
    typedef UCHAR DOT11_MAC_ADDRESS[6];
    typedef DOT11_MAC_ADDRESS* PDOT11_MAC_ADDRESS;
    """
    _fields_ = [
        ("macAddr", c_ubyte*6),
   ]

class DOT11_BSSID_LIST(Structure):
    """ 
    typedef struct _DOT11_BSSID_LIST {
      NDIS_OBJECT_HEADER Header;
      ULONG              uNumOfEntries;
      ULONG              uTotalNumOfEntries;
      DOT11_MAC_ADDRESS  BSSIDs[1];
    } DOT11_BSSID_LIST, *PDOT11_BSSID_LIST;
    """
    _fields_ = [
        ("Header", NDIS_OBJECT_HEADER),
        ("uNumOfEntries", ULONG),
        ("uTotalNumOfEntries", ULONG),
        ("BSSIDs", DOT11_MAC_ADDRESS * 1),
     ]


class WLAN_CONNECTION_PARAMETERS(Structure):
    """ 
    typedef struct _WLAN_CONNECTION_PARAMETERS {
      WLAN_CONNECTION_MODE wlanConnectionMode;
      LPCWSTR              strProfile;
      PDOT11_SSID          pDot11Ssid;
      PDOT11_BSSID_LIST    pDesiredBssidList;
      DOT11_BSS_TYPE       dot11BssType;
      DWORD                dwFlags;
    } WLAN_CONNECTION_PARAMETERS, *PWLAN_CONNECTION_PARAMETERS;
    """    
    _fields_ = [
        ("wlanConnectionMode", WLAN_CONNECTION_MODE),
        ("strProfile", c_wchar_p),
        ("dot11Ssid", POINTER(DOT11_SSID)),
        ("desiredBssidList", POINTER(DOT11_BSSID_LIST)),
        ("dot11BssType", DOT11_BSS_TYPE),
        ("Flags", DWORD),
        ]

#DWORD WINAPI WlanConnect(
  #_In_        HANDLE hClientHandle,
  #_In_        const GUID *pInterfaceGuid,
  #_In_        const PWLAN_CONNECTION_PARAMETERS pConnectionParameters,
  #_Reserved_  PVOID pReserved
#);
WlanConnect = wlanapi.WlanConnect
WlanConnect.argtypes = (HANDLE, POINTER(GUID), POINTER(WLAN_CONNECTION_PARAMETERS), c_void_p)
WlanConnect.restype = DWORD

#DWORD WINAPI WlanGetProfile(
  #_In_         HANDLE hClientHandle,
  #_In_         const GUID *pInterfaceGuid,
  #_In_         LPCWSTR strProfileName,
  #_Reserved_   PVOID pReserved,
  #_Out_        LPWSTR *pstrProfileXml,
  #_Inout_opt_  DWORD *pdwFlags,
  #_Out_opt_    PDWORD pdwGrantedAccess
#);

WlanGetProfile = wlanapi.WlanGetProfile
WlanGetProfile.argtypes = (HANDLE, POINTER(GUID), c_wchar_p, c_void_p, POINTER(c_wchar_p), POINTER(DWORD), POINTER(DWORD))
WlanGetProfile.restype = DWORD


WlanSetProfile = wlanapi.WlanSetProfile
WlanSetProfile.restype = DWORD              # DWORD WINAPI WlanSetProfile(
WlanSetProfile.argtypes = (HANDLE,          #  _In_         HANDLE hClientHandle,
                           POINTER(GUID),   #  _In_         const GUID *pInterfaceGuid,
                           DWORD,           #  _In_         DWORD dwFlags,
                           c_wchar_p,       #  _In_         LPCWSTR strProfileXml,
                           c_wchar_p,       #  _In_opt_     LPCWSTR strAllUserProfileSecurity,
                           BOOL,            #  _In_         BOOL bOverwrite,
                           c_void_p,        #  _Reserved_   PVOID pReserved,
                           POINTER(DWORD)   #  _Out_        DWORD *pdwReasonCode
                           )                #);

#DWORD WINAPI WlanDeleteProfile(
  #_In_        HANDLE hClientHandle,
  #_In_        const GUID *pInterfaceGuid,
  #_In_        LPCWSTR strProfileName,
  #_Reserved_  PVOID pReserved
#);

WlanDeleteProfile = wlanapi.WlanDeleteProfile
WlanDeleteProfile.restype = DWORD
WlanDeleteProfile.argtypes = (HANDLE, 
                              POINTER(GUID), 
                              c_wchar_p,
                              c_void_p)

class WLAN_RAW_DATA(Structure):
    """
    typedef struct _WLAN_RAW_DATA {
      DWORD dwDataSize;
      BYTE  DataBlob[1];
    } WLAN_RAW_DATA, *PWLAN_RAW_DATA;
    """
    _fields_ = [
        ("dwDataSize", DWORD),
        ("DataBlob ", BYTE * 1),
    ]

#DWORD WINAPI WlanScan(
  #_In_        HANDLE hClientHandle,
  #_In_        const GUID *pInterfaceGuid,
  #_In_opt_    const PDOT11_SSID pDot11Ssid,
  #_In_opt_    const PWLAN_RAW_DATA pIeData,
  #_Reserved_  PVOID pReserved
#);
WlanScan= wlanapi.WlanScan
WlanScan.restype = DWORD
WlanScan.argtypes = (HANDLE, 
                     POINTER(GUID), 
                     POINTER(DOT11_SSID),
                     POINTER(WLAN_RAW_DATA),
                     c_void_p)

#DWORD WlanReasonCodeToString(
  #_In_        DWORD dwReasonCode,
  #_In_        DWORD dwBufferSize,
  #_In_        PWCHAR pStringBuffer,
  #_Reserved_  PVOID pReserved
#);
WlanReasonCodeToString=wlanapi.WlanReasonCodeToString
WlanScan.restype = DWORD
WlanScan.argtypes = (DWORD, 
                     DWORD, 
                     c_wchar_p,
                     c_void_p)

def getWlanReasonCodeString(reasonCode):
    """ return the reason code string """
    rcStr = ''
    try:
        buf = create_unicode_buffer(256)
        bufSize = DWORD(256)
        ret = WlanReasonCodeToString( reasonCode, bufSize, buf, None)
        if ret != ERROR_SUCCESS:
            raise WinError(ret)
        rcStr = buf.value
    except Exception,err:
        print 'getWlanReasonCodeString() fail - err %s' % err
        rcStr = '**'
    return rcStr


WLAN_NOTIFICATION_SOURCE_NONE = 0
WLAN_NOTIFICATION_SOURCE_ONEX = 0x00000004
WLAN_NOTIFICATION_SOURCE_ACM  = 0x00000008
WLAN_NOTIFICATION_SOURCE_MSM  = 0x00000010
WLAN_NOTIFICATION_SOURCE_SECURITY = 0x00000020
WLAN_NOTIFICATION_SOURCE_IHV = 0x00000040
WLAN_NOTIFICATION_SOURCE_HNWK = 0x00000080
WLAN_NOTIFICATION_SOURCE_ALL = 0x0000FFFF

class WLAN_NOTIFICATION_DATA(Structure):
    """
    typedef struct _WLAN_NOTIFICATION_DATA {
      DWORD NotificationSource;
      DWORD NotificationCode;
      GUID  InterfaceGuid;
      DWORD dwDataSize;
      PVOID pData;
    } WLAN_NOTIFICATION_DATA, *PWLAN_NOTIFICATION_DATA;
    """
    _fields_ = [
        ("NotificationSource", DWORD),
        ("NotificationCode", DWORD),
        ("InterfaceGuid", GUID),
        ("dwDataSize", DWORD),
        ("pData", BYTE * 1),
    ]
    
    def __str__(self):
        return 'source:0x%X code:%s InferfaceGuid:%s dwDataSize:%s' % (self.NotificationSource, self.NotificationCode, self.InterfaceGuid, self.dwDataSize)
        

#DWORD WINAPI WlanRegisterNotification(
  #_In_        HANDLE hClientHandle,
  #_In_        DWORD dwNotifSource,
  #_In_        BOOL bIgnoreDuplicate,
  #_In_opt_    WLAN_NOTIFICATION_CALLBACK  funcCallback,
  #_In_opt_    PVOID pCallbackContext,
  #_Reserved_  PVOID pReserved,
  #_Out_opt_   PDWORD pdwPrevNotifSource
#);

NOTIFY_FUNC = CFUNCTYPE(c_voidp, POINTER(WLAN_NOTIFICATION_DATA), POINTER(c_int))
#NOTIFY_FUNC = WINFUNCTYPE(c_voidp, POINTER(WLAN_NOTIFICATION_DATA), POINTER(c_int))

WlanRegisterNotification=wlanapi.WlanRegisterNotification
WlanRegisterNotification.restype = DWORD
WlanRegisterNotification.argtypes = (HANDLE, 
                                     DWORD, 
                                     c_bool,
                                     NOTIFY_FUNC,
                                     c_void_p,
                                     c_void_p,
                                     POINTER(DWORD))

def wlanNotificationCallback(pData, pVoid):
    """ Wlan notification callback """
    msg1 = 'wlanNotificationCallback() pData:%s' % pData.contents
    #msg2 = 'wlanNotificationCallback() pVoid:%s' % pVoid.contents
    log.info( msg1 )
    #log.info( msg2 )
    print msg1
    #print msg2

class WlanMemory(object):
    """ Base class used when the wlanapi returns data that needs to be deleted with WlanFreeMemory() 

        __enter__ and __exit__ have been implemented so that the with statement can be used to 
        automatically free the memory.

        the delete() method will also delete the memory used.
    """
    def __init__(self, pData):
        self._pData = pData
        log.debug('WlanMemory __init__() - pData:%s' % self._pData)
        
    def delete(self):
        if self._pData:
            log.debug('WlanMemory delete()   - pData:%s' % self._pData)
            WlanFreeMemory(self._pData)
            self._pData = None

    def __enter__(self):
        return self
    
    def __exit__(self, type, value, traceback):
        self.delete()
    
    def _custom_resize(self, array, new_size):
        return (array._type_*new_size).from_address(addressof(array))
        
class WlanInterfaceInfoData(WlanMemory):
    def __init__(self, pData):
        WlanMemory.__init__(self, pData)
        self.ifaces = self._custom_resize( self._pData.contents.InterfaceInfo, 
                                           self._pData.contents.NumberOfItems)
    def __len__(self):
        return len(self.ifaces)

    def __getitem__(self, key):
        return self.ifaces[key]

    def getInterface(self, miniDesc):
        """ return an interface using miniDesc name """
        for iface in self.ifaces:
            if iface.miniDesc() == miniDesc:
                return iface
        else:
            raise Exception('Interface with miniDesc "%s" not found' % miniDesc)

    def __iter__(self):
        return iter(self.ifaces)

class WlanAvailableNetworkListData(WlanMemory):
    def __init__(self, pData):
        WlanMemory.__init__(self, pData)
        avail_net_list = self._pData.contents
        self.networks = self._custom_resize( avail_net_list.Network, avail_net_list.NumberOfItems)

    def __len__(self):
        return len(self.networks)

    def __getitem__(self, key):
        return self.networks[key]

    def getProfile(self, profile):
        """ return network with profile name """
        for network in self.networks:
            if network.getProfileName() == profile:
                return network
        else:
            raise Exception('Network with profile name "%s" not found' % profile)

    def getSSID(self, ssid):
        """ return network using ssid """
        for network in self.networks:
            if network.getSSID() == ssid:
                return network
        else:
            raise Exception('Network with SSID "%s" not found' % profile)

    def __iter__(self):
        return iter(self.networks)

class WlanInterface(object):
    """ wraps the wlanapi for all wlan operations 
        Some wlanapi commands return memory that needs to be deleted with a call to WlanFreeMemory()
          enumInterfaces(), getAvailableNetworks()
        The wlan memory used will always be return in a class inherited from WlanMemory
        Use the python 'with' statement to scope the usage and then the memory is free'd automatically
    """
    def __init__(self, openHandle=True, useCallback=False):
        self._useCallback = useCallback
        self._handle = None
        self._lstIfaces = None
        self._prevSources = 0
        self._funcCallback = None

        if openHandle:
            self.openHandle() 
        
    def openHandle(self):
        """ open handle to Wlan """
        NegotiatedVersion = DWORD()
        self._handle = HANDLE()
        log.debug('WlanOpenHandle()')
        ret = WlanOpenHandle(1, None, byref(NegotiatedVersion), byref(self._handle))
        if ret != ERROR_SUCCESS:
            raise WinError(ret)
        if self._useCallback:
            self.createNotificationCallback(sources=WLAN_NOTIFICATION_SOURCE_ALL)
            
    def updateDesc(self, wlanIfData=None):
        """ update the description string """
        if wlanIfData:
            self._lstIfaces = [str(iface) for iface in wlanIfData.ifaces]
        else:
            with self.enumInterfaces() as wlanIfData:
                self._lstIfaces = [str(iface) for iface in wlanIfData.ifaces]
        
    def close(self):
        # free all memory used and close handle
        if self._handle is not None:
            if self._funcCallback is not None:
                self.createNotificationCallback(clearAll=True)
            log.debug('WlanCloseHandle() handle:%s' % self._handle)
            ret = WlanCloseHandle(self._handle, None )
            if ret != ERROR_SUCCESS:
                raise WinError(ret)
            self._handle = None

    def createNotificationCallback(self, sources=WLAN_NOTIFICATION_SOURCE_ALL, ignoreDups=False, clearAll=False):
        log.debug('createNotificationCallback() - sources:0x%X ignoreDups:%s clearAll:%s' % (sources,ignoreDups,clearAll)) 
        if clearAll:
            dwNotifySource = DWORD( WLAN_NOTIFICATION_SOURCE_NONE )
            #funcCallback = None
            self._funcCallback = NOTIFY_FUNC(wlanNotificationCallback)
            pCallbackContext = POINTER(c_int)()
        else:
            dwNotifySource = DWORD( sources )
            self._funcCallback = NOTIFY_FUNC(wlanNotificationCallback)
            pCallbackContext = POINTER(c_int)()

        bIgnoreDups = BOOL(ignoreDups)
        dwPrevSources = DWORD(self._prevSources) 
        ret = WlanRegisterNotification(self._handle, 
                                       dwNotifySource,
                                       bIgnoreDups,
                                       self._funcCallback,
                                       pCallbackContext,
                                       None,
                                       byref(dwPrevSources))
        if ret != ERROR_SUCCESS:
            raise WindowsError(ret)

        self._prevSources = sources
        if clearAll:
            self._funcCallback = None
        
    def enumInterfaces(self):
        # free interface memory if already allocated
        log.debug('WlanInterface enumInterfaces()')
        # find all wireless network interfaces
        _pInterfaceList = pointer(WLAN_INTERFACE_INFO_LIST())
        ret = WlanEnumInterfaces(self._handle, None, byref(_pInterfaceList))
        if ret != ERROR_SUCCESS:
            raise WinError(ret)
        # return to caller
        return WlanInterfaceInfoData(_pInterfaceList)
        
    def getAvailableNetworks(self, iface):
        log.debug('WlanInterface getAvailableNetworks()')

        dwFlags = DWORD(3)
        _pAvailableNetworkList = pointer(WLAN_AVAILABLE_NETWORK_LIST())
        ret = WlanGetAvailableNetworkList( self._handle, 
                                           byref(iface.InterfaceGuid),
                                           dwFlags,
                                           None,
                                           byref(_pAvailableNetworkList))
        if ret != ERROR_SUCCESS:
            raise WinError(ret)

        return WlanAvailableNetworkListData(_pAvailableNetworkList)

    def wlanConnect(self, iface, profile):
        """ connect a wlan interface using a profile """
        log.debug('WlanInterface wlanConnect() - iface:%s profile:"%s"' % (iface.miniDesc(), profile))
        wcp = WLAN_CONNECTION_PARAMETERS()
        wcp.wlanConnectMode = wlan_connection_mode_profile
        wcp.strProfile = profile
        wcp.pDot11Ssid = None # byref(ssid)
        wcp.pDesiredBssidList = None
        wcp.dot11BssType = 1
        wcp.dwFlags = 0
        
        ret = WlanConnect( self._handle, 
                           byref(iface.InterfaceGuid), 
                           byref(wcp),
                           None)
        if ret != ERROR_SUCCESS:
            raise WinError(ret)
    
    def wlanDisconnect(self, iface):
        """ disconnect a wlan interface """
        log.debug('WlanInterface wlanDisconnect() - iface:%s' % (iface.miniDesc()))
        ret = WlanDisconnect( self._handle, 
                              byref(iface.InterfaceGuid), 
                              None)
        if ret != ERROR_SUCCESS:
            raise WinError(ret)
    
    def wlanGetProfile(self, iface, profile, saveToFile=None):
        """ return profile XML for a defined profile """
        log.debug('WlanInterface wlanGetProfile() - profile:"%s" saveToFile:%s' % (profile,saveToFile))
        sProfile = c_wchar_p(profile)
        sProfileXML = c_wchar_p()   # create_unicode_buffer(1024)
        flags = DWORD(0)
        grantedAccess = DWORD()
        ret = WlanGetProfile( self._handle, 
                              byref(iface.InterfaceGuid), 
                              sProfile,
                              None,
                              byref(sProfileXML),
                              byref(flags),
                              byref(grantedAccess))
        if ret != ERROR_SUCCESS:
            raise WinError(ret)
        profileXML = sProfileXML.value
        if saveToFile:
            open(saveToFile,'w').write(profileXML)
        return profileXML
    
    def wlanSetProfile(self, iface, profileXML, overwrite=True):
        """ return profile XML for a defined profile """
        log.debug('WlanInterface wlanSetProfile()')
        flags = DWORD(0)
        sProfileXML = c_wchar_p(profileXML)
        dwReasonCode = DWORD()
        bOverwrite = BOOL(overwrite)
        ret = WlanSetProfile( self._handle, 
                              byref(iface.InterfaceGuid), 
                              flags,
                              sProfileXML,
                              None,
                              bOverwrite,
                              None,
                              byref(dwReasonCode))
        log.debug('wlanSetProfile() reasonCode:%s' % getWlanReasonCodeString( dwReasonCode ))
        if ret != ERROR_SUCCESS:
            raise WinError(ret)
    
    def wlanCopyProfile(self, iface, profile, newProfile, ssid=None, pass_phrase=None, saveOrigProfile=None, saveNewProfile=None):
        """ Create a new profile from an existing profile
            Changes in the new profile:
              change the profile name in <WLANProfile>
              remove the hex element in <SSID>
              if ssid argument is set:
                change the name element in <SSID> to new SSID name
              if pass_phrase argument is set:  
                change the protected element from true to false in <sharedKey>
                change the keyMaterial element to the new pass phrase in <sharedKey>
        """
        sXML = self.wlanGetProfile(iface, profile, saveToFile=saveOrigProfile)
        #print sXML
        reProf = re.compile('<{0}>.*</{0}>'.format('name'))
        reProf2 = re.compile('<{0}>.*</{0}>'.format('name2'))
        reHex  = re.compile('<{0}>.*</{0}>'.format('hex'))
        reProt = re.compile('<{0}>.*</{0}>'.format('protected'))
        reKeyM = re.compile('<{0}>.*</{0}>'.format('keyMaterial'))
        sNewXML = sXML
        # change the name of the profile
        sNewXML = reProf.sub('<{0}>{1}</{0}>'.format( 'name2',newProfile), sNewXML, 1) 
        # remove the hex element in <SSID>
        sNewXML = reHex.sub('', sNewXML, 1)
        if ssid is not None:
            # change the name element in <SSID> to new SSID name
            sNewXML = reProf.sub('<{0}>{1}</{0}>'.format( 'name',ssid), sNewXML, 1) 
        if pass_phrase is not None:    
            # change the protected element from true to false in <sharedKey>
            sNewXML = reProt.sub('<{0}>{1}</{0}>'.format( 'protected','false'), sNewXML, 1) 
            # change the keyMaterial element to the new pass phrase in <sharedKey>
            sNewXML = reKeyM.sub('<{0}>{1}</{0}>'.format( 'keyMaterial', pass_phrase), sNewXML, 1)
        # rename <name2> back to <name>
        sNewXML = reProf2.sub('<{0}>{1}</{0}>'.format( 'name',newProfile), sNewXML, 1) 
        #print sNewXML
        if saveNewProfile is not None:
            open(saveNewProfile,'w').write(sNewXML)
        # set the new profile
        self.wlanSetProfile(iface, sNewXML) 

    def wlanDeleteProfile(self, iface, profile):
        """ Delete a profile """
        log.debug('WlanInterface wlanDeleteProfile() - profile:"%s"' % profile)
        sProfile = c_wchar_p(profile)
        ret = WlanDeleteProfile( self._handle, 
                                 byref(iface.InterfaceGuid), 
                                 sProfile,
                                 None)
        if ret != ERROR_SUCCESS:
            raise WinError(ret)

    def wlanScan(self, iface):
        """ Requests that the native 802.11 Wireless LAN driver scan for available wireless networks. """
        log.debug('WlanInterface wlanScan()')
        ret = WlanScan( self._handle, 
                        byref(iface.InterfaceGuid), 
                        None,None,None)
        if ret != ERROR_SUCCESS:
            raise WinError(ret)

    def __str__(self):
        if self._handle is None:
            return 'Not open'
        if self._lstIfaces:
            s = '%d interfaces : %s' % (len(self._lstIfaces),','.join(self._lstIfaces))
        if self._funcCallback is not None:
            s += ' callback'
        return s
    
def show_wifi_interfaces():
    """ test function """
    log.debug('show_wifi_interfaces')
    NegotiatedVersion = DWORD()
    ClientHandle = HANDLE()
    ret = WlanOpenHandle(1, None, byref(NegotiatedVersion), byref(ClientHandle))
    if ret != ERROR_SUCCESS:
        raise WinError(ret)
    try:
        # find all wireless network interfaces
        pInterfaceList = pointer(WLAN_INTERFACE_INFO_LIST())
        ret = WlanEnumInterfaces(ClientHandle, None, byref(pInterfaceList))
        if ret != ERROR_SUCCESS:
            raise WinError(ret)
        try:
            ifaces = customresize(pInterfaceList.contents.InterfaceInfo,
                                  pInterfaceList.contents.NumberOfItems)
            # find each available network for each interface
            for iface in ifaces:
                print "\nInterface: %s %s\n" % (iface.strInterfaceDescription, iface.isState)
                pAvailableNetworkList = pointer(WLAN_AVAILABLE_NETWORK_LIST())
                ret = WlanGetAvailableNetworkList(ClientHandle, 
                                            byref(iface.InterfaceGuid),
                                            0,
                                            None,
                                            byref(pAvailableNetworkList))
                if ret != ERROR_SUCCESS:
                    # raise WinError(ret)
                    raise WindowsError(ret)
                try:
                    print '%-30s %-4s %s' % ('SSID','Qual','C:Connectable S:Secure P:Profile')
                    print '%-30s %-4s' % ('====','====')
                    avail_net_list = pAvailableNetworkList.contents
                    networks = customresize( avail_net_list.Network, avail_net_list.NumberOfItems)
                    for network in networks:
                        ssid = network.dot11Ssid.SSID[:network.dot11Ssid.SSIDLength]
                        sigQual = network.wlanSignalQuality
                        sConn = ' '
                        sDesc = ''
                        if network.NetworkConnectable:
                            sDesc += 'C'
                        if network.SecurityEnabled:
                            sDesc += 'S'
                        if network.Flags & WLAN_AVAILABLE_NETWORK_CONNECTED:
                            sConn = '*'
                        if network.Flags & WLAN_AVAILABLE_NETWORK_HAS_PROFILE:
                            sDesc += 'P'
                        print "%-30s %3d%% %s %s" % ( ssid, sigQual, sConn, sDesc)
                finally:
                    WlanFreeMemory(pAvailableNetworkList)
        finally:
            WlanFreeMemory(pInterfaceList)
    finally:
        WlanCloseHandle( ClientHandle, None)

from menu import MenuItem, Menu, InputException

xmlTemplate = """
  <?xml version="1.0">
  <WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>$PROFILE_NAME$</name>
    <SSIDConfig>
      <SSID>
        <name>$SSID$</name>
      </SSID>
      <nonBroadcast>false</nonBroadcast>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>manual</connectionMode>
    <autoSwitch>false</autoSwitch>
    <MSM>
      <security>
        <authEncryption>
          <authentication>WPA2PSK</authentication>
          <encryption>AES</encryption>
          <useOneX>false</useOneX>
        </authEncryption>
        <sharedKey>
          <keyType>passPhrase</keyType>
          <protected>false</protected>
          <keyMaterial>$PASS_PHRASE$</keyMaterial>
        </sharedKey>
      </security>
    </MSM>
  </WLANProfile>
"""
uniXmlTemplate = unicode(xmlTemplate)

class WifiMenu(Menu):
    _dctSources = { 'all'  : WLAN_NOTIFICATION_SOURCE_ALL,
                    'acm'  : WLAN_NOTIFICATION_SOURCE_ACM,  
                    'hnwk' : WLAN_NOTIFICATION_SOURCE_HNWK,  
                    'ihv'  : WLAN_NOTIFICATION_SOURCE_IHV,  
                    'msm'  : WLAN_NOTIFICATION_SOURCE_MSM,  
                    'onex' : WLAN_NOTIFICATION_SOURCE_ONEX,  
                    'sec'  : WLAN_NOTIFICATION_SOURCE_SECURITY,  
                   }
    _sources = '|'.join(_dctSources.keys())
    
    def __init__(self, useCallback=False, cmdFile=None):
        Menu.__init__(self, cmdFile, menuSize=80 )
        self.wlan = WlanInterface(useCallback=useCallback)
        self.wlan.updateDesc()
        # add menu items
        self.addMenuItem( MenuItem( 'si', '',                     'Show interfaces' , self._showInterfaces) )
        self.addMenuItem( MenuItem( 'il', '<networks|n>',  'run enumInterfaces() and list' , self._ifList) )
        self.addMenuItem( MenuItem( 'co', 'profile <if=name> <iface=index>',       'Connect to a network' , self._ifConnect) )
        self.addMenuItem( MenuItem( 'di', '<if=name> <iface=index>',              'Disconnect from a network' , self._ifDisconnect) )
        self.addMenuItem( MenuItem( 'gp', 'profile <if=name> <iface=index>',       'Get Profile' , self._ifGetProfile) )
        self.addMenuItem( MenuItem( 'sp', 'profile <ssid=value> <pp=value> <if=name> <iface=index>',       'Set Profile' , self._ifSetProfile) )
        self.addMenuItem( MenuItem( 'cp', 'profile new_profile <if=name> <iface=index> <ssid=ssid> <pp=pass_phrase>',       'Copy Profile' , self._ifCopyProfile) )
        self.addMenuItem( MenuItem( 'dp', 'profile <if=name> <iface=index>',       'Delete a Profile' , self._ifDeleteProfile) )
        self.addMenuItem( MenuItem( 'is', '<if=name> <iface=index>',       'Scan an interface' , self._ifScan) )
        self.addMenuItem( MenuItem( 'cn', '<source=%s> <ignoreDups> <clear>' % WifiMenu._sources,       'Register/Deregister the notification callback' , self._ifRegNotify) )
        self.updateHeader()
        

    def shutdown(self):
        self.wlan.close()

    def updateHeader(self):
        self.header = 'wlan: %s' % self.wlan
        
    def _showInterfaces(self):
        show_wifi_interfaces()

    def _ifList(self):
        """ list all interfaces available """
        bNetworks = False
        for cmd in self.lstCmd[1:]:
            if cmd == 'networks' or cmd == 'n':
                bNetworks = True

        print 'enum interfaces ...'
        with self.wlan.enumInterfaces() as wlanIfData:
            # find each available network for each interface
            # for n,iface in enumerate(wlanIfData.ifaces):
            for n,iface in enumerate(wlanIfData):
                print "%d : %-40s state:%s" % (n,iface.strInterfaceDescription, iface.getState())
                if bNetworks:
                    with self.wlan.getAvailableNetworks(iface) as wlanNetData:
                        print '  %-15s %-30s %-15s %s' % ('Profile', 'SSID','Qual (dbm)','C:Connectable S:Secure P:Profile')
                        print '  %-15s %-30s %-15s' % ('=======', '====','==========')
                        for nw in wlanNetData:
                            sConn = ' '
                            sDesc = ''
                            if nw.isConnectable():
                                sDesc += 'C'
                            if nw.isSecure():
                                sDesc += 'S'
                            if nw.isConnected():
                                sConn = '*'
                            if nw.hasProfile():
                                sDesc += 'P'
                            print '  %-15s %-30s %3d%% %.1f %s %s' % (nw.getProfileName(), nw.getSSID(), nw.getSignalQuality(), nw.getSignalQualityInDBM(), sConn, sDesc)
                
    def _ifConnect(self):
        if len(self.lstCmd) < 2:
            raise InputException( 'Not enough arguments for %s command' % self.lstCmd[0] )
        profile = self.lstCmd[1]
        ifaceIndex = 0 
        ifaceName = None
        for cmd in self.lstCmd[2:]:
            lst = cmd.split('=')
            if lst[0] == 'iface' and len(lst) == 2:
                ifaceIndex = int(lst[1])
            elif lst[0] == 'if' and len(lst) == 2:
                ifaceName = lst[1]
        
        with self.wlan.enumInterfaces() as wlanIfData:
            if ifaceName:
                iface = wlanIfData.getInterface(ifaceName)
            else:
                iface = wlanIfData[ifaceIndex]
            self.wlan.wlanConnect(iface, profile) 
                
    def _ifDisconnect(self):
        ifaceIndex = 0 
        ifaceName = None
        for cmd in self.lstCmd[1:]:
            lst = cmd.split('=')
            if lst[0] == 'iface' and len(lst) == 2:
                ifaceIndex = int(lst[1])
            elif lst[0] == 'if' and len(lst) == 2:
                ifaceName = lst[1]

        with self.wlan.enumInterfaces() as wlanIfData:
            if ifaceName:
                iface = wlanIfData.getInterface(ifaceName)
            else:
                iface = wlanIfData[ifaceIndex]
            self.wlan.wlanDisconnect(iface) 

    def _ifGetProfile(self):
        if len(self.lstCmd) < 2:
            raise InputException( 'Not enough arguments for %s command' % self.lstCmd[0] )

        profile = self.lstCmd[1]
        ifaceIndex = 0
        ifaceName = None
        for cmd in self.lstCmd[2:]:
            lst = cmd.split('=')
            if lst[0] == 'iface' and len(lst) == 2:
                ifaceIndex = int(lst[1])
            elif lst[0] == 'if' and len(lst) == 2:
                ifaceName = lst[1]

        saveToFile = profile + '.prof'
        with self.wlan.enumInterfaces() as wlanIfData:
            if ifaceName:
                iface = wlanIfData.getInterface(ifaceName)
            else:
                iface = wlanIfData[ifaceIndex]
            sXML = self.wlan.wlanGetProfile(iface, profile, saveToFile)
            log.debug(sXML)
            hexDump(sXML, msg='Get', logFunc=log.debug) 
        
        xml = open(saveToFile,'r').read()
        print xml
        
        
    def _ifCopyProfile(self):
        if len(self.lstCmd) < 3:
            raise InputException( 'Not enough arguments for %s command' % self.lstCmd[0] )
        profile = self.lstCmd[1]
        newProfile = self.lstCmd[2]
        ssid = None
        pass_phrase = 'mimosanetworks'
        ifaceIndex = 0 
        ifaceName = None
        for cmd in self.lstCmd[2:]:
            lst = cmd.split('=')
            if lst[0] == 'iface' and len(lst) == 2:
                ifaceIndex = int(lst[1])
            elif lst[0] == 'if' and len(lst) == 2:
                ifaceName = lst[1]
            elif lst[0] == 'ssid' and len(lst) == 2:
                ssid = lst[1]
            elif lst[0] == 'pp' and len(lst) == 2:
                pass_phrase = lst[1]

        saveOrigProfile = profile + '.prof'
        saveNewProfile  = newProfile + '.prof'
        with self.wlan.enumInterfaces() as wlanIfData:
            if ifaceName:
                iface = wlanIfData.getInterface(ifaceName)
            else:
                iface = wlanIfData[ifaceIndex]

            self.wlan.wlanCopyProfile(iface, profile, newProfile, ssid=ssid, pass_phrase=pass_phrase, 
                                          saveNewProfile=saveNewProfile, saveOrigProfile=saveOrigProfile)

    def _ifSetProfile(self):
        if len(self.lstCmd) < 2:
            raise InputException( 'Not enough arguments for %s command' % self.lstCmd[0] )
        profile = self.lstCmd[1]
        ifaceIndex = 0
        passPhrase = 'mimosanetworks'
        ssid = 'mimosaM016'
        ifaceName = None
        for cmd in self.lstCmd[2:]:
            lst = cmd.split('=')
            if lst[0] == 'iface' and len(lst) == 2:
                ifaceIndex = int(lst[1])
            elif lst[0] == 'if' and len(lst) == 2:
                ifaceName = lst[1]
            elif lst[0] == 'ssid' and len(lst) == 2:
                ssid = lst[1]
            elif lst[0] == 'pp' and len(lst) == 2:
                passPhrase = lst[1]

        # get profile XML from template string
        proXML = uniXmlTemplate
        proXML = proXML.replace('$PROFILE_NAME$', profile)
        proXML = proXML.replace('$SSID$', ssid)
        proXML = proXML.replace('$PASS_PHRASE$', passPhrase)
        print proXML
        hexDump( proXML, msg='Set', logFunc=log.debug)
        #print x
        # get profile XML from interface
        with self.wlan.enumInterfaces() as wlanIfData:
            if ifaceName:
                iface = wlanIfData.getInterface(ifaceName)
            else:
                iface = wlanIfData[ifaceIndex]
            self.wlan.wlanSetProfile(iface, proXML)

    def _ifDeleteProfile(self):
        if len(self.lstCmd) < 2:
            raise InputException( 'Not enough arguments for %s command' % self.lstCmd[0] )
        profile = self.lstCmd[1]
        ifaceIndex = 0 
        ifaceName = None
        for cmd in self.lstCmd[2:]:
            lst = cmd.split('=')
            if lst[0] == 'iface' and len(lst) == 2:
                ifaceIndex = int(lst[1])
            elif lst[0] == 'if' and len(lst) == 2:
                ifaceName = lst[1]
        
        with self.wlan.enumInterfaces() as wlanIfData:
            if ifaceName:
                iface = wlanIfData.getInterface(ifaceName)
            else:
                iface = wlanIfData[ifaceIndex]
            self.wlan.wlanDeleteProfile(iface, profile)

    def _ifScan(self):
        ifaceIndex = 0 
        ifaceName = None
        for cmd in self.lstCmd[2:]:
            lst = cmd.split('=')
            if lst[0] == 'iface' and len(lst) == 2:
                ifaceIndex = int(lst[1])
            elif lst[0] == 'if' and len(lst) == 2:
                ifaceName = lst[1]
        
        with self.wlan.enumInterfaces() as wlanIfData:
            if ifaceName:
                iface = wlanIfData.getInterface(ifaceName)
            else:
                iface = wlanIfData[ifaceIndex]
            self.wlan.wlanScan(iface)

    def _ifRegNotify(self):
        """ cn <source=value> <ignoreDups> <clear> """
        source = WLAN_NOTIFICATION_SOURCE_ALL 
        ignoreDups = False
        clear = False
        for cmd in self.lstCmd[1:]:
            lst = cmd.split('=')
            if lst[0] == 'source' and len(lst) == 2:
                lst = lst[1].split('|')
                source = 0
                for src in lst:
                    if src in dctSources:
                        source |= dctSources[src]
                    else:
                        raise Exception( 'source type "%s" not supported' )
            elif lst[0] == 'ignoreDups':
                ignoreDups = True
            elif lst[0] == 'clear':
                clear = True
        
        self.wlan.createNotificationCallback(sources=source, ignoreDups=ignoreDups, clearAll=clear)

if __name__ == '__main__':
    import logging
    from optparse import OptionParser

    TLLog.config( 'wlan_test.log', defLogLevel=logging.INFO )

    DEFAULT_LOG_ENABLE = 'wlan'

    # build the command line arguments
    parser = OptionParser()
    parser.add_option( "-m",  "--logEnable", dest="lstLogEnable", default=DEFAULT_LOG_ENABLE,
                       help='Comma separated list of log modules to enable, * for all. Default is "%s"' % DEFAULT_LOG_ENABLE)
    parser.add_option( '', "--useCallback",  dest="useCallback", action="store_true", default=False,
                       help='Enable usage of the Wlan callback notifications. Default is do not use')

    #  parse the command line and set values
    (options, args) = parser.parse_args()

    # makes Control-break behave the same as Control-C on windows
    import signal
    signal.signal( signal.SIGBREAK, signal.default_int_handler )

    ## for wing IDE object lookup, code does not need to be run
    #if 0:
        #assert isinstance(gga, GPGGA)
        #assert isinstance(gsa, GPGSA)
        #assert isinstance(sat, Satellite)
    
    try:
        log.info( '=================================' )
        log.info( 'wlan_test starting' )
        # update log options
        logOptions(options.lstLogEnable)

        menu = WifiMenu(useCallback=options.useCallback)
        menu.runMenu()
    finally:
        log.info( 'wlan_test exiting' )
        
