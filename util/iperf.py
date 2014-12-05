""" iperf.py - use iperf.exe to perform network throughput analysis """
import subprocess

def iperf_local_client( ipaddr, testTime=5, port=None, interval=None, iperfExe='c:\\iperf\\iperf.exe'):
    """ use local iperf to test network speed """ 
    resp = None
    dct = {}
    try:
        # add required commands to command line
        lstCmds = [iperfExe, 
                   '-c', ipaddr,
                   '-t', str(testTime), 
                   '-y', 'C'] 
        # add optional commands
        if port is not None:
            lstCmds.extend( ['-p', str(port)])
        if interval is not None:
            lstCmds.extend( ['-i', str(interval)])
            
        # launch a process to run iperf, map stderr to stdout
        # check_output() return all stdout when process is complete
        resp = subprocess.check_output(lstCmds,stderr=subprocess.STDOUT)
        dct['resp'] = resp
        lst = resp.split(',')
        dct['time'] = lst[0]
        dct['local_ipAddr'] = lst[1]
        dct['local_port'] = int(lst[2])
        dct['ipaddr'] = lst[3]
        dct['port'] = int(lst[4])
        dct['client_id'] = int(lst[5])
        dct['interval'] = lst[6]
        dct['transfer'] = float(lst[7])
        dct['bandwidth'] = float(lst[8])
    
    except Exception,err:
        print 'Exception %s' % err
        if resp:
            print 'resp:%s' % resp
            
    return dct

def ping( ipaddr, count=5):
    """ use subprocess to run ping """ 
    resp = None
    dct = {}
    exe = 'ping.exe'
    try:
        # add required commands to command line
        lstCmds = [exe, ipaddr,'-n', str(count)]
        # launch a process to run pingmap stderr to stdout
        # check_output() return all stdout when process is complete
        resp = subprocess.check_output(lstCmds,stderr=subprocess.STDOUT)
        dct['resp'] = resp
        if lstResp[-1].find( 'round-trip') != -1:
            # ping worked
            lst = lstResp[-2].split()
            dct['pkt_trans'] = int( lst[0] )
            dct['pkt_recv' ] = int( lst[3] )
            dct['pkt_loss' ] = lst[6]
            lst = lstResp[-1].split()
            lst2 = lst[3].split('/')
            dct['round-trip_min'] = float(lst2[0]) 
            dct['round-trip_avg'] = float(lst2[1]) 
            dct['round-trip_max'] = float(lst2[2])
        else:
            dct['ping_fail'] = lstResp[-1]
    
    except Exception,err:
        print 'Exception %s' % err
        if resp:
            print 'resp:%s' % resp
            
    return dct

class IperfServer( object ):
    """ control an iperf server running in a separate process """
    def __init__(self, port=5001, iperfExe='c:\\iperf\\iperf.exe'):
        self.port = port
        self.iperfExe = iperfExe
        self.svr = None
    
    def startServer(self):
        """ start the server """ 
        resp = None
        lst = [self.iperfExe,
               '-s',
               '-p', str(self.port),
              ]
        self.svr = subprocess.Popen( lst ) 
    
    def stopServer(self):
        if self.svr:
            self.svr.terminate()
            #while self.svr.poll():
                #time.sleep( 0.5 )
            self.svr = None

if __name__ == '__main__':
    # start a iperf server and client locally
    import time
    from common import bitrateString
    server = None
    try:
        # create an iPerf server and start 
        #server = IperfServer()
        #server.startServer()
        ## small delay
        #time.sleep( 0.5 )
        ## launch client process
        #dct = iperf_local_client( 'localhost' )
        #for key,value in dct.items():
            #print '  %-20s : %s' % (key,value)
        #print '  %-20s : %s' % ('bitrate', bitrateString(dct['bandwidth']))

        iperfTestTime = 5
        GOLD_PC = '192.168.1.11'
        print( 'Running iperf ... %s seconds' % iperfTestTime)
        dct = iperf_local_client( ipaddr=GOLD_PC, testTime=iperfTestTime)
        for key,value in dct.items():
            print '  %-20s : %s' % (key,value)
        print
        print('  %-20s : %s' % ('bitrate', bitrateString(dct['bandwidth'])))
    finally:
        if server:
            server.stopServer()
            