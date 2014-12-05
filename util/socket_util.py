""" Socket utility classes """
import socket,select

from tl_logger import TLLog
log = TLLog.getLogger( 'socket' )

dctSockets = {}

def socketAdd(sock):
    log.info( 'socketAdd() - %s' % sock.name )
    if sock.name in dctSockets:
        raise Exception( 'socketAdd() fail - name "%s" exists' % sock.name )
    dctSockets[ sock.name ] = sock

def socketRemove( sock ):
    log.info( 'socketRemove() - %s' % sock.name )
    if sock.name in dctSockets:
        del dctSockets[sock.name]
        
class BaseSocket(object):
    def __init__(self, name):
        self.name = name
        self.sock = None
        
    def fileno(self):
        """ Used by select() """
        return self.sock.fileno()
    
    def handle_request(self):
        log.warn( 'handle_request() - %s not overloaded' % self.name )
        pass
    
    def handle_write(self):
        log.debug('handle_write()')
        pass

    def close(self):
        log.debug( 'close() - %s' % self.name )
        if self.sock:
            socketRemove( self )
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
            self.sock = None

class TCPServer(BaseSocket):
    def __init__(self, name, host, port, handler):
        BaseSocket.__init__(self, name)
        self.host = host
        self.port = port
        self.handler = handler
        self._listen()
        
    def _listen(self):
        """ bind for listening """
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            log.debug( 'Listening at %s:%d' % (self.host, self.port))
            self.sock.bind((self.host, self.port))
            self.sock.listen(1)
            socketAdd( self )
        except Exception, err:
            log.error( '_listen() fail - %s' % (err))
            raise
        
    def handle_request(self):
        """ have received an accept request """
        conn,addr = self.sock.accept()
        log.info( 'handle_request() - conn:%s addr:%s' % (conn,addr))
        # create the handler
        handler = self.handler( conn, addr )
        # add to sockets to listen on
        socketAdd( handler )

def serveForever(background=None, timeout=None):
    """ run servers forever  """
    log.info( 'serveForever() background:%s timeout:%s' % (background,timeout) )
    if timeout is None:
        timeout = 0.0
        if background:
            timeout = 0.1
            
    while True:
        lstSockets = dctSockets.values()
        lstNames = dctSockets.keys()
        r,w,e = select.select(lstSockets,[],[],timeout)
        log.debug( '%s - r,w,e - %d,%d,%d' % (lstNames,len(r),len(w),len(e)))
        for server in lstSockets:
            if server in r:
                server.handle_request()
        for srv in dctSockets.values():
            srv.handle_write()
        # Perform any background processing
        if background:
            background()

