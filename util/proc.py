""" proc.py - simple process control with python class """ 
import os,traceback,time,subprocess,sys

def osCmd(cmd):
    print 'Execute %s' % cmd
    #os.system( cmd )
    try:
        retcode = subprocess.call(cmd, shell=True)
        if retcode < 0:
            print >> sys.stderr, "Child was terminated by signal", -retcode
        else:
            print >> sys.stderr, "Child returned", retcode
    except OSError as e:
        print >> sys.stderr, "Execution failed:", e
        
class Proc(object):
    """ Create process using subprocess.call method (same as os.system) 
        uses the window title to identify the process (not very good)    
    """
    def __init__(self, title, path, exe, args='/min'):
        self.title = title
        self.path = path
        self.exe = exe
        self.args = args
        self._setPath()
        self.state = 'not running'
        
    def _setPath(self):
        self.path = os.path.join( os.getcwd(), self.path)
        
    def start(self, args=''):
        osCmd( 'start "%s" /D "%s" %s %s %s' % (self.title,self.path, self.args, self.exe, args))
        self.state = 'started'
        
    def kill(self):
        osCmd( 'taskkill /fi "windowtitle eq %s"' % self.title )

    def terminate(self):
        self.kill()
            
    def monitor(self):
        pass

    def __str__(self):
        return '%-12s - %s' % (self.title, self.state)
    
class Proc2(Proc):
    """ Create process using subprocess.Popen method and save the process instance """
    def __init__(self, title, path, exe, args=''):
        Proc.__init__(self, title, path, exe, args)
        self.proc = None

    def start(self, args=''):
        cmd = self.exe
        print 'Starting %s' % self.title
        print '  cmd:%s' % cmd
        print '  cwd:%s' % self.path
        self.proc = subprocess.Popen( cmd, cwd=self.path) #, shell=True)
        print '  proc:%s' % self.proc

    def terminate(self):
        if self.proc:
            print 'Terminate %s' % self.title
            print ' proc:%s' % self.proc
            poll = self.proc.poll() 
            print ' before proc.poll():%s' % poll
            self.proc.terminate()
            poll = self.proc.poll() 
            print ' after proc.poll():%s' % poll
            
    def monitor(self):
        #print 'Monitor %s' % self.title
        #print ' proc:%s' % self.proc
        if self.proc:
            if self.proc.poll():
                print ' Process %s pid:%s has terminated' % (self.title, self.proc.pid)

    def __str__(self):
        if self.proc:
            return '%-12s - pid:%s' % (self.title, self.proc.pid)
        else:
            return '%-12s - not running' % (self.title)
            
if __name__ == '__main__':
    import subprocess
    resp = None
    try:
        iperfIPAddr = '10.0.1.36'
        iperfTime = 5
        lstCmds = ['c:\\iperf\\iperf.exe', '-c', iperfIPAddr, '-t', str(iperfTime), '-y', 'C']
        
        resp = subprocess.check_output(lstCmds,stderr=subprocess.STDOUT)
        lst = resp.split(',')
        dct = {}
        dct['time'] = lst[0]
        dct['local_ipAddr'] = lst[1]
        dct['local_port'] = int(lst[2])
        dct['ipaddr'] = lst[3]
        dct['port'] = int(lst[4])
        dct['client_id'] = int(lst[5])
        dct['interval'] = lst[6]
        dct['transfer'] = float(lst[7])
        dct['bandwidth'] = float(lst[8])
        print dct
    
    except Exception,err:
        print 'Exception %s' % err
        if resp:
            print 'resp:%s' % resp
            
    