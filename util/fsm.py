""" fsm.py - simple finite state machine in python """
import threading
import logging
import traceback
import time
import Queue

from tl_logger import TLLog
from common import excTraceback

log = TLLog.getLogger('FSM')

class FSM_State(object):
    def __init__(self, name, fnState, fnEnter=None, fnExit=None, arg=None):
        self.name = name
        self._fnState = fnState
        self._fnEnter = fnEnter
        self._fnExit  = fnExit
        self._arg     = arg

    def executeState(self):
        """ run the state method """
        self._fnState(self._arg)
    
    def __str__(self):
        return self.name
    
class FSM_Event(object):
    def __init__(self, name, dctStates, fnBefore=None, fnAfter=None):
        self.name = name
        self._dctStates = dctStates
        self._fnBefore = fnBefore
        self._fnAfter = fnAfter
       
    def _getNextState(self, fsm):
        """ return the matching _dctStates name for the next state 
            * is a special source that will cause ANY state to match
            return name of necxt state or None if illegal state
        """
        if fsm.fsm_get_state() in self._dctStates:
            return self._dctStates[fsm.fsm_get_state()]
        if '*' in self._dctStates:
            return self._dctStates['*']
        return None
        
    def executeAction(self, fsm):
        """ validate and then execute the event which will cause a state change """
        nextState = self._getNextState( fsm )
        if nextState is None:
            log.warn('Event "%s" not valid in state "%s" ... ignoring' % (self.name, fsm.fsm_get_state()))
        elif nextState == '*':
            log.debug('Event "%s" ignored in state "%s"' % (self.name, fsm.fsm_get_state()))
        else:
            fsm.fsm_set_state( nextState, self )

    def isValidState(self, fsm):
        """ return True if this event is valid for this state """
        return self._getNextState(fsm) is not None

    def __str__(self):
        return self.name
    
class FSM(object):
    """ Finite state machine implementation
    """
    def __init__(self, lstStates, lstActions, initState, fnBeforeEvent=None, fnAfterEvent=None, fnEnterState=None, fnLeaveState=None):
        # create dctStates from lstStates
        self._dctStates = {}
        for state in lstStates:
            self._dctStates[state.name] = state
        # create dctActions from lstActions
        self._dctEvents = {}
        for action in lstActions:
            # add hook to FSM object
            action.fsm = self
            self._dctEvents[action.name] = action
        # set initial state
        self._curState = self._dctStates[initState]
        # set global function callbacks for all events and states
        self._fnBeforeEvent = fnBeforeEvent
        self._fnAfterEvent = fnAfterEvent
        self._fnEnterState = fnEnterState
        self._fnLeaveState = fnLeaveState
        # create queue of State Trans functions is empty
        self._queBeforeFuncs = Queue.Queue()
        self._queAfterFuncs = Queue.Queue()
        
    def fsm_event(self, evtName, execute=False):
        """ Process an action on FSM """
        evt = self._dctEvents[evtName]
        evt.executeAction(self)
        if execute:
            self.fsm_execute()
        
    def fsm_get_state(self):
        """ return the current state name """
        return self._curState.name
    
    def fsm_set_state(self, newStateName, evt=None):
        """ Change the current state
            Add all callbacks to the queue of state trans functions. 
            These will be called on next execute() 
        """
        log.debug('fsm_set_state() - newState:%s oldState:%s evt:%s' % (newStateName, self._curState.name,evt))
        # add event before function if defined 
        if evt and evt._fnBefore:
            self._queBeforeFuncs.put( evt._fnBefore )
        # add the global before event if defined
        if self._fnBeforeEvent:
            self._queBeforeFuncs.put( self._fnBeforeEvent )
        # add current state exit function if defined 
        if self._curState._fnExit:
            self._queBeforeFuncs.put( self._curState._fnExit )
        # add the global exit state if defined
        if self._fnLeaveState:
            self._queBeforeFuncs.put( self._fnLeaveState)

        # change state to new state
        self._curState = self._dctStates[newStateName]

        # add new state enter function if defined 
        if self._curState._fnEnter:
            self._queBeforeFuncs.put( self._curState._fnEnter )
        # add the global enter state if defined
        if self._fnEnterState:
            self._queBeforeFuncs.put( self._fnEnterState)
        # add event after function if defined 
        # TODO after events not working (yet), 
        if evt and evt._fnAfter:
            self._queAfterFuncs.put( evt._fnAfter )
        # add global event after function if defined 
        if self._fnAfterEvent:
            self._queAfterFuncs.put( self._fnAfterEvent )
    
    def fsm_execute(self):
        """ run the function for the current state """
        # process the before queue 
        while not self._queBeforeFuncs.empty():
            func = self._queBeforeFuncs.get()
            func()
        # execute the state function
        self._curState.executeState()
        # process the after queue 
        while not self._queAfterFuncs.empty():
            func = self._queAfterFuncs.get()
            func()

class FSMThread(threading.Thread,FSM):
    """ Thread class that uses the FSM """
    def __init__(self, lstStates, lstActions, initState, fnBeforeEvent=None, fnAfterEvent=None, fnEnterState=None, fnLeaveState=None, name=None):
        # threading base class
        threading.Thread.__init__(self, name=name)
        # FSM base class
        FSM.__init__(self, lstStates, lstActions, initState, fnBeforeEvent, fnAfterEvent, fnEnterState, fnLeaveState)
        # create stop event
        self._evtStop = threading.Event()
        # start the thread
        self.daemon = True
        self.sleepSec = 0#.1    # 100 ms
        self.start()
        
    def stop(self):
        """ set the stop event which will cause thread to exit, no matter what state """
        self._evtStop.set()
        
    def run(self):
        """ Thread method -- will run forever in background """
        log.info( 'FSMThread %s - starting' % self.name)
        try:
            while True:
                if self._evtStop.isSet():
                    break
                # run FSM
                self.fsm_execute()
                time.sleep( self.sleepSec )
                    
        except Exception,err:
            log.error( 'FSMThread error - %s' % err)
            excTraceback(err, log)
        log.info( 'FSMThread %s - exiting' % self.name)

if __name__ == '__main__':
    ST_RED = 'Red'
    ST_GREEN = 'Green'
    ST_YELLOW = 'Yellow'
    ST_NO_POWER = 'No Power'
    
    EVT_GO = 'Go'
    EVT_WARN = 'Warn'
    EVT_STOP = 'Stop'
    EVT_POWER_OFF = 'Power_Off'
    EVT_POWER_ON  = 'Power_On'
    
    lghtLog = TLLog.getLogger( 'light' )
    class StopLightThread(FSMThread):
        """ Test class for the FSMThread """
        
        def __init__(self, name=None):
            # create states and actions
            lstStates = [ FSM_State( ST_GREEN,    self._stGreen, fnEnter=self._greenEnter, fnExit=self._greenExit ),
                          FSM_State( ST_RED,      self._stRed ),
                          FSM_State( ST_YELLOW,   self._stYellow ),
                          FSM_State( ST_NO_POWER, self._stNoPower ),
                        ]
            lstActions = [ FSM_Event(EVT_GO,        { ST_RED      : ST_GREEN }, fnBefore=self._goBefore),
                           FSM_Event(EVT_WARN,      { ST_GREEN    : ST_YELLOW }),
                           FSM_Event(EVT_STOP,      { ST_YELLOW   : ST_RED }),
                           FSM_Event(EVT_POWER_OFF, { '*'         : ST_NO_POWER }),
                           FSM_Event(EVT_POWER_ON,  { ST_NO_POWER : ST_RED, '*' : '*' }),
                          ]
            # FSM base class
            FSMThread.__init__(self, lstStates, lstActions, ST_RED, fnEnterState=self._enterState, name=name) 
            
        def _enterState(self):
            lghtLog.debug('_enterState() - %s' % self._curState.name )
    
        def _logState(self, dct, delay=1.0):
            lghtLog.debug('State:%s dct:%s' % (self.fsm_get_state(), dct) )
            time.sleep(delay)
    
        def _stGreen(self, dct):
            self._logState(dct)
    
        def _stRed(self, dct):
            self._logState(dct)
    
        def _stYellow(self, dct):
            self._logState(dct)
        
        def _stNoPower(self, dct):
            self._logState(dct)
        
        def _greenEnter(self):
            lghtLog.info('_greenEnter()') 

        def _greenExit(self):
            lghtLog.info('_greenExit()') 
    
        def _goBefore(self):
            lghtLog.info('_goBefore()') 

        #def _goAfter(self):
            #lghtLog.info('_goAfter()') 
    
    DEFAULT_LOG_ENABLE = 'FSM,light'

    from tl_logger import TLLog,logOptions
    TLLog.config( 'FSMtest.log', defLogLevel=logging.INFO )
    # build the command line arguments
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option( "-m",  "--logEnable", dest="lstLogEnable", default=DEFAULT_LOG_ENABLE,
                       help='Comma separated list of log modules to enable, * for all. Default is "%s"' % DEFAULT_LOG_ENABLE)
    parser.add_option( "-g",  "--showLogs", action="store_true", dest="showLogs", default=False,
                       help='list all log options.' )
    parser.add_option( "",  "--powerOff", dest="powerOff", default=-1,
                       help='Set a count in seconds before power of light.' )

    #  parse the command line and set values
    (options, args) = parser.parse_args()

    # makes Control-break behave the same as Control-C on windows
    import signal
    signal.signal( signal.SIGBREAK, signal.default_int_handler )

    thrd = None
    poCnt = int(options.powerOff)
    try:
        def monitor(secs, poCnt=10):
            for n in range(secs):
                print '%s' % thrd.fsm_get_state()
                time.sleep(1.0)
                poCnt -= 1
                if poCnt == 0:
                    thrd.fsm_event(EVT_POWER_OFF) 
            return poCnt
        
        # set the main thread name
        thrd = threading.currentThread()
        thrd.setName( 'Main' )

        log.info(80*"*")
        log.info( 'Main - starting' )
        logOptions(options.lstLogEnable, options.showLogs, log=log)

        thrd = StopLightThread(name='LGHT')
        while True:
            thrd.fsm_event(EVT_POWER_ON) 
            poCnt = monitor( 1, poCnt )
            thrd.fsm_event(EVT_GO) 
            poCnt = monitor( 5, poCnt )
            thrd.fsm_event(EVT_WARN)
            poCnt = monitor(1, poCnt)
            thrd.fsm_event(EVT_STOP)
            poCnt = monitor(2, poCnt)
            thrd.fsm_event(EVT_WARN)
            poCnt = monitor(2, poCnt)
            
    except Exception, err:
        s = '%s: %s' % (err.__class__.__name__, err)
        log.error( s )
        print s

        print '-- traceback --'
        traceback.print_exc()
        print
 
    finally:
        # Close the database connection
        if thrd:
            thrd.stop()
            thrd.join()
            
        log.info( 'Main - exiting' )
        TLLog.shutdown()
    
        
        
        
        
