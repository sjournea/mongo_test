""" db.py """
import MySQLdb
import sys
import datetime

from common import flatten,excTraceback
from tl_logger import TLLog

log = TLLog.getLogger( 'db' )
sqlLog = TLLog.getLogger( 'SQL' )
sesLog = TLLog.getLogger( 'DBSess' )

class DBException(Exception):
    """ all database exceptions use this as a base class """
    def __init__(self,msg):
        Exception.__init__(self, msg)

class DBField(object):
    """ Abstract class for field definition for database table """
    def __init__(self, name, attr=None):
        self.name = name
        self.attr = attr
        self._units = None
        self._validate()

    def getType(self):
        return self.__class__.__name__

    def getUnits(self):
        if self._units is not None:
            return self._units
        else:
            return self.getType()
    
    def setUnits(self, units):
        # TODO should validate units
        self._units = units

    def _validate(self):
        """ validate the DBField is correct, raise DBException if not valid """ 
        pass

    def _typeDef(self):
        """ Return the column definiton for this field """
        s = '%s' % self.__class__.__name__
        if hasattr( self, 'length') and self.length is not None:
            s += '(%s' % self.length
            if  hasattr( self, 'decimals') and self.decimals is not None:
                s += ',%s' % self.decimals
            s += ')'
        if self.attr:
            s += ' %s' % self.attr
        return s

    def ColumnDefinition(self):
        """ Return the column definiton for this field """
        s = '%s %s' % (self.name, self._typeDef() )
        return s

    def formatValue(self, value):
        return '%s' % value
    
class VARCHAR(DBField):
    """ VARCHAR field, must define length """
    def __init__(self, name, length, attr=None):
        DBField.__init__(self, name, attr)
        self.length = int(length)

    def formatValue(self, value):
        return "'%s'" % value
    
class CHAR(DBField):
    """ CHAR field, default length = 1 """
    def __init__(self, name, length=None, attr=None):
        DBField.__init__(self, name, attr)
        self.length = length
        
    def formatValue(self, value):
        return "'%s'" % value
    
class BINARY(DBField):
    def __init__(self, name, length=None, attr=None):
        DBField.__init__(self, name, attr)
        self.length = length

class INT(DBField):
    """ INT field """
    def __init__(self, name, length=None, attr=None):
        DBField.__init__(self, name, attr)
        self.length = length
        
class BIGINT(DBField):
    """ BIGINT field """
    def __init__(self, name, length=None, attr=None):
        DBField.__init__(self, name, attr)
        self.length = length
        
class FLOAT(DBField):
    """ FLOAT field """
    def __init__(self, name, length=None ,decimals=None, attr=None):
        DBField.__init__(self, name, attr)
        self.length = length
        self.decimals = decimals
        
class DOUBLE(DBField):
    """ DOUBLE field """
    def __init__(self, name, length=None, decimals=None, attr=None):
        DBField.__init__(self, name, attr)
        self.length = length
        self.decimals = decimals

class TIMESTAMP(DBField):
    """ TIMESTAMP field """
    def __init__(self, name, attr=None):
        DBField.__init__(self, name, attr)

class DBTable(object):
    """ database table definition """
    def __init__(self, tableName, lstFields,lstConstraints=None):
        self.tableName = tableName
        self.lstFields = lstFields
        self.lstConstraints = lstConstraints
        self._dctFields = {}
        for field in lstFields:
            if field.name in self._dctFields:
                raise DBException( 'DBTable() fail - Duplicate field "%s"' % field.name )
            self._dctFields[field.name] = field

    def isField(self, name):
        return name in self._dctFields
    
    def createTableSQL(self, ifNotExists=True):
        """ retrun the SQL statement to create this table """
        lstColumns = ['\n  ' + field.ColumnDefinition() for field in self.lstFields]
        sExists = ''
        if ifNotExists:
            sExists = 'IF NOT EXISTS'
        sql =   'CREATE TABLE %s %s (' % (sExists,self.tableName)
        sql += '%s' % (','.join( lstColumns))
        if self.lstConstraints:
            lstCons = ['\n  ' + cons for cons in self.lstConstraints]
            sql += ',%s' % ','.join( lstCons)
        sql += '\n);'
        return sql
            
    def insertSQL(self, rec, db=None):
        """ return the SQL INSERT statement to add a record to this table """
        lstFields = []
        lstValues = []

        # build sFields and sValues for all parameters
        for fld in self.lstFields:
            newValue = getattr(rec,fld.name, None)
            if newValue is not None:
                lstFields.append( fld.name )
                lstValues.append( fld.formatValue( newValue ))

        sql = 'INSERT INTO %s ' % self.tableName
        sql += ' ( %s ) ' % ','.join(lstFields)
        sql += ' VALUES ( %s )' % ','.join( lstValues )
        if db:
            db.execute( sql, commit=True )
        else:
            return sql
        
    def insertSQLParams(self, rec, db):
        """ insert into database using db.insert() """
        lstFields = []
        lstValues = []

        # build sFields and sValues for all parameters
        for fld in self.lstFields:
            newValue = getattr(rec, fld.name, None)
            if newValue is not None:
                lstFields.append( fld.name )
                lstValues.append( newValue )
        tup = tuple(lstValues)
        db.insert( self.tableName, lstFields, tup )

    def __str__(self):
        lst = ['%s:%s' % (fld.name, getattr(self, fld.name, None)) for fld in self.lstFields]
        return ' '.join(lst)
    
class DBRec(object):
    def __init__(self, tbl ):
        self.tbl = tbl

    def getTableName(self):
        return self.tbl.tableName
    
    def insertSQL( self, db=None ):
        return self.tbl.insertSQL( self, db )
    
    def insertSQLParams( self, db ):
        self.tbl.insertSQLParams( self, db )

    def __str__(self):
        s = ''
        lst = ['%s:%s' % (fld.name,getattr(self, fld.name,None)) for fld in self.tbl.lstFields]
        return ' '.join( lst )

class DBSession(object):
    """ creates a connection to a MySQL database """
    
    def __init__(self, dbDef):
        self.dbDef = dbDef
        self._conn = None
        self.cur = None
        
    def create(self):
        """ create a session into the database """
        if self._conn:
            self.close()
        self._conn = self.dbDef.connect()

        # Set autocommit to True seems to prevent MySQL database lockups
        if self.dbDef.autoCommit:
            self.autoCommitEnable()
        # 
        self.cur = self._conn.cursor()
        #try:
            #log.info( 'connect() - host:%s port:%s user:%s passwd:**** database:%s' % (self.host, self.port, self.user, self.database))
            #if self.connType == 'MySQL':
                #con = MySQLdb.connect( host=self.host, port=self.port, user=self.user, passwd=self.passwd, db=self.database)
                #return DBSession(con)
            #else:
                #raise DBException( 'connection type "%s" not supported' % self.connType )
        #except MySQLdb.Error,e:
            #log.error( 'MDB Error : %s' % e )
            #raise DBException( str(e) )
            
    def autoCommitEnable(self):
        log.warn('autoCommit is ON')
        self._conn.autocommit(True)

    def autoCommitDisable(self):
        log.warn('autoCommit is OFF')
        self._conn.autocommit(False)


    def close(self):
        sesLog.debug( 'close()' )
        if self._conn:
            self._conn.close()
            self._conn = None
            self.cur = None

    def isConnected(self):
        return self._conn != None
    
    def insert(self, sTbl, lstFields, tupParams, commit=True):
        """ format a SQL insert command """
        lst = [ '%s' for _ in range(len(lstFields))]
        sSQL = "INSERT INTO %s (%s) VALUES (%s)" % (sTbl, ','.join(lstFields), ','.join(lst))
        self.execute(sSQL, commit=commit, params=tupParams)

    def execute(self, sSQL, commit=False, fetch=False, params=None):
        try:
            sqlLog.debug( '%s' % sSQL)
            # send data to defined callbacks
            for func in self.dbDef.lstExeCallbacks:
                func(sSQL,params)
            # execute SQL
            if params:
                sqlLog.debug( 'params:%s' % str(params))
                self.cur.execute( sSQL, params )
            else:
                self.cur.execute( sSQL )
            # check commit and fetch
            if commit:
                self.commit()
            if fetch:
                return self.fetchall()
        except Exception,err:
            excTraceback(err, log, raiseErr=False)
            #log.error( 'execute() fail - %s' % err)
            raise DBException( err )
        
    def fetchone(self):
        lst = self.cur.fetchone()
        log.debug( 'fetchone() - %s' % lst )
        return lst
    
    def fetchall(self):
        lst = self.cur.fetchall()
        log.debug( 'fetchall() - %s' % str(lst) )
        return lst
    
    def columns(self):
        desc = self.cur.description
        lst = [tup[0] for tup in desc]
        return lst
    
    def insertId(self):
        self.execute( 'SELECT LAST_INSERT_ID();' )
        lst = self.fetchone()
        lst = flatten(lst)
        return lst[0]
    
    def commit(self):
        if not self.dbDef.autoCommit:
            sqlLog.debug('COMMIT')
            self._conn.commit()
        
    def showTables(self, like=None):
        sql = 'SHOW TABLES'
        if like:
            sql += " LIKE '%s'" % like
        self.execute( sql )
        lst = flatten(self.fetchall())
        log.debug( 'showTables() - %s' % lst )
        return lst
    
    def getDBServerTime(self):
        """ Return the current time on the database server """
        lst = self.execute( 'SELECT NOW()', fetch=True )
        return lst[0][0]

DEF_CONN_TYPE = 'MySQL'
DEF_HOST = 'localhost'
DEF_PORT = 3306
DEF_USER = 'root'
DEF_PASSWD = 'database'
DEF_AUTOCOMMIT = True

class DB(object):
    """ manages the access to the MySQL database """
    def __init__(self, host=DEF_HOST, user=DEF_USER, passwd=DEF_PASSWD, port=DEF_PORT, connType=DEF_CONN_TYPE, database=None, autoCommit=DEF_AUTOCOMMIT):
        self.host = host
        self.user = user
        self.passwd = passwd
        self.port = port
        self.database = database
        self.connType = connType
        self.autoCommit = autoCommit

        self.dctTables = {}
        self.lstExeCallbacks = []
        
    def ExecuteCallbackAdd(self, func):
        """ add a callback when DBSession execute() is called """
        self.lstExeCallbacks.append(func) 

    def ExecuteCallbackRemove(self, func):
        """ add a callback when DBSession execute() is called """
        self.lstExeCallbacks.remove(func)

    def setup(self,dct):
        """ connect setup parameters from a dictionary """
        self.connType = dct.get( 'connType', DEF_CONN_TYPE )
        self.host = dct.get( 'host', DEF_HOST )
        self.port = int(dct.get( 'port', DEF_PORT ))
        self.user = dct.get( 'user', DEF_USER )
        self.passwd = dct.get( 'passwd', DEF_PASSWD )
        self.database = dct.get( 'database', None )
        self.autoCommit = dct.get( 'autocommit', DEF_AUTOCOMMIT )
 
    def getParams(self):
        """ return setup parameters for database in a dict """
        dct = {}
        dct['connType'] = self.connType
        dct['host'] = self.host
        dct['port'] = self.port
        dct['user'] = self.user
        dct['passwd'] = self.passwd
        dct['database'] = self.database
        dct['autocommit'] = self.autoCommit
        return dct

    def createTable( self, tableName, lstFields, lstConstraints=None ):
        """ create a DBTable object """
        if tableName in self.dctTables:
            # TODO Should validate the fields and constraints are the same 
            log.warn('table "%s" already exists ... returning' % tableName)
            tbl = self.dctTables[ tableName ]
            return tbl
        # new table needs to be created and added to dictionary
        tbl = DBTable( tableName, lstFields, lstConstraints)
        self.dctTables[ tableName ] = tbl
        return tbl
        
    def getTable( self, tableName ):
        """ get a DBTable """
        if tableName not in self.dctTables:
            raise DBException( 'table "%s" not found' % tableName)
        return self.dctTables[ tableName ]

    def isTableDefined( self, tableName ):
        """ has a DBTable been created by name """
        return tableName in self.dctTables
        
    def createRecDict( self, tableName, dct ):
        """ create a record for a DBTable object """
        if tableName not in self.dctTables:
            raise DBException( 'createRec() fail - tableName "%s" not found' % tableName)
        tbl = self.dctTables[tableName]
        rec = DBRec( tbl )
        for name in dct.keys():
            if not tbl.isField(name):
                raise DBException( 'createRec() fail - name "%s" is not a defined field for table "%s"' % (name, tableName))
            setattr( rec, name, dct[name] )
        return rec

    def createRec( self, tableName, **kwargs ):
        """ create a record for a DBTable object using keyword arguments """
        return self.createRecDict( tableName, kwargs )

    def connect(self):
        """ create a session into the database """
        try:
            log.info( 'connect() - host:%s port:%s user:%s passwd:**** database:%s' % (self.host, self.port, self.user, self.database))
            if self.connType == 'MySQL':
                con = MySQLdb.connect( host=self.host, port=self.port, user=self.user, passwd=self.passwd, db=self.database)
                return con
            else:
                raise DBException( 'connection type "%s" not supported' % self.connType )
        except MySQLdb.Error,e:
            log.error( 'MDB Error : %s' % e )
            raise DBException( str(e) )
            
    def close(self):
        log.debug( 'close()' )
        pass

if __name__ == '__main__':
    import logging
    TLLog.config( '..\\logs\\dbTest.log', defLogLevel=logging.INFO )

    db = None
    session = None
    #host = '192.168.100.250'
    #user='mfgtest'
    #passwd='mimosa'
    #database='developtest'
    host = 'localhost'
    user='root'
    passwd='database'
    database='mfgtest'
    
    try:
        db = DB( host=host, user=user, passwd=passwd, database=database)
        session = DBSession( db )
        session.create()
        session.execute("SELECT VERSION()")
        data = session.fetchone()
        print "Database version : %s " % data


        #sJobIdTbl    = "JobIdTbl"
        #lstFields = [ INT( 'id', attr='UNSIGNED NOT NULL AUTO_INCREMENT' ),
                      #INT( 'job_id', attr='UNSIGNED NOT NULL' ),
                      #VARCHAR( 'string1', length=10),
                      #VARCHAR( 'string2', length=132),
                      #FLOAT( 'float1'),
                      #DOUBLE( 'double1'),
                      #CHAR( 'char1' ),
                      #CHAR( 'char2', length=64),
                      #]
        #lstConstraints = [
            #'PRIMARY KEY (id)',
            #'INDEX (job_id)',
            ##'FOREIGN KEY (job_id) REFERENCES ' + sJobIdTbl + '(job_id) ON DELETE CASCADE ON UPDATE CASCADE',
            #]
        
        #tblName = 'test_fields'
        #db.execute( 'DROP TABLE IF EXISTS %s' % tblName, commit=True)
        ## test creating a table
        #tbl = db.createTable( tblName, lstFields, lstConstraints)
        #sql = tbl.createTableSQL()
        #print 'create : %s' % sql
        #db.execute( sql, commit=True)
        ## test adding a record
        #rec = db.createRec( tblName, job_id=1, string1='ABCD', string2='ABCDEFGHIJ', float1=45.0, double1=43e6, char1='C', char2='ABCD' )
        #print 'rec:%s' % rec
        #sql = rec.insertSQL()
        #print 'insertSQL: %s' % sql
        #db.execute( sql, commit=True )
        
        
        #print "Verifying/Creating the database tables for this MfgTest job"
        ## Tables 
        #sJobIdTbl    = "JobIdTbl"
        #sInstTbl     = "InstTbl"
        #sInstAttrTbl = "InstAttrTbl"
        #sSummTbl     = "SummTbl"
        #sTestTbl     = "TestTbl"
            
         ## Create table JobIdTbl
         ##   fields: job_id, job_started
            
        #sSQL = "CREATE TABLE IF NOT EXISTS " + sJobIdTbl + " " 
        #sSQL += "( job_id INT UNSIGNED NOT NULL AUTO_INCREMENT"
        #sSQL += ", job_started DATETIME NOT NULL"
        #sSQL += ", PRIMARY KEY (job_id)"
        #sSQL += " )"
        #db.execute( sSQL );

        ## Now add a record to the JobIdTbl for this MVP job
        #sSQL = "INSERT INTO " + sJobIdTbl + " (job_started) VALUES ( NOW() )"
        #db.execute( sSQL )
            
        ## Get the last job_id and save 
        #dbJobId = db.insertId()
        #print "MfgTest Job Id = %d" % dbJobId
        
        #db.commit()

        ## Show tables in database
        #print '\nSelect tests'
        #lstSelects = ["Show Tables" ,"select * from JobIdTbl"]
        #for select in lstSelects:
            #print 'select:%s' % select
            #db.execute( select )
            #lst = db.fetchall()
            #for rec in lst:
                #print rec
            #print
        
    except MySQLdb.Error, e:
        print "Error %d: %s" % (e.args[0],e.args[1])
    finally:
        if session:
            session.close()

                                   