""" watchfile.py -- watch a file to minotor for updates
    Used for tailing a log file
"""
import os

class WatchFile(object):
    def __init__(self, filename):
        self.filename = filename
        self._fp = None
        self.open()
        
    def open(self):
        try:
            # open file and move to end of file
            self._fp = open( self.filename, 'rb')
            self._fp.seek(0, os.SEEK_END )
        except Exception,err:
            self.close()
            raise

    def close(self):
        if self._fp:
            self._fp.close()
            self._fp = None

    def getLines(self):
        """ return the lines added since the last call """
        lst = []
        while True:
            line = self._fp.readline()
            if not line:
                break
            lst.append( line.rstrip() )
        return lst

    def __str__(self):
        return 'filename:%s _pos:%s tell():%s' % (self.filename,self._pos,self._fp.tell())
         
if __name__ == '__main__':
    import time
    wf = WatchFile( '..\\logs\\wxMfgTest.log' )
    while True:
        print wf
        lst = wf.getLines()
        for line in lst:
            print line
        print 'sleep ...'
        time.sleep( 1.0 )
    