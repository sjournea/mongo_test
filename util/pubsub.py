""" pubsub.py -- simple Publish/Subscribe implementation """
from tl_logger import TLLog
log = TLLog.getLogger( 'pubsub' )

class PubSub(object):
    """ Simple Publish/Subscribe implementation 
    """
    def __init__(self, name='pubsub'):
        self.name = name
        self._dctSubEvents = {}
        self._lstAllEvents = []
        
    def subscribe(self, eventType, cbFunc):
        """ subscribe to an event """
        log.debug('subscribe() %s - eventType:%s cbFunc:%s' % (self.name,eventType,cbFunc))
        if eventType in self._dctSubEvents:
            lst = self._dctSubEvents[eventType]
            # check if callback already exists 
            if cbFunc in lst:
                log.warn('subscribe() - eventType:%s - callback already defined' % eventType)
            else:    
                lst.append( cbFunc )
        else:
            # no callbacks for this event -- add new entry to dict
            lst = [cbFunc]
            self._dctSubEvents[eventType] = lst
            
    def subscribeList(self, lstEvents, cbFunc):
        """ subscribe to a list of events """
        for event in lstEvents:
            self.subscribe(event, cbFunc)
            
    def subscribeAll(self, cbFunc):
        """ subscribe to all events """
        self._lstAllEvents.append(cbFunc)
            
    def unsubscribeAll(self, cbFunc):
        """ unsubscribe to all events """
        self._lstAllEvents.remove(cbFunc)
            
    def unsubscribe(self, eventType, cbFunc):
        """ unsubscribe to an event """
        log.debug('unsubscribe() %s - eventType:%s cbFunc:%s' % (self.name,eventType,cbFunc))
        if eventType in self._dctSubEvents:
            lst = self._dctSubEvents[eventType]
            if cbFunc in lst:
                lst.remove(cbFunc)
            else:
                log.warn('unsubscribe() - eventType:%s - callback was not subscribed' % eventType)
        else:
            log.warn('unsubscribe() - eventType:%s - has not subscriptions' % eventType)

    def unsubscribeList(self, lstEvents, cbFunc):
        """ unsubscribe to an event """
        for event in lstEvents:
            self.unsubscribe(event, cbFunc)

    def publish(self, event):
        """ publist an event, call all subscribers """
        log.debug('publish() %s - event:%s' % (self.name,event))
        # send to all event subscribers
        for cbFunc in self._lstAllEvents:
            cbFunc(event)
            
        # Use event type to send to callbacks
        evtType = event.evtType
        if evtType in self._dctSubEvents:
            lst = self._dctSubEvents[evtType]
            for cbFunc in lst:
                cbFunc(event)
        
    def __str__(self):
        return '%s _dctSubEvents:%s' % (self.name,self._dctSubEvents)

if __name__ == '__main__':

    class TestPubSub(object):
        def cb_1(self,event):
            print 'cb_1 - evt:%s' % event
    
        def cb_2(self,event):
            print 'cb_2 - evt:%s' % event
            
        def cb_3(self,event):
            print 'cb_3 - evt:%s' % event

    EVT_1 = 'One'
    EVT_2 = 'Two'
    EVT_3 = 'Three'
    EVT_4 = 'Four'
    lstEvents = [EVT_1,EVT_2,EVT_3, EVT_4]

    pbsb = PubSub()
    obj = TestPubSub()

    print pbsb
    for event in lstEvents:
        pbsb.publish(event)
    print
    
    pbsb.subscribe(EVT_1, obj.cb_1)
    print pbsb
    for event in lstEvents:
        pbsb.publish(event)
    print

    pbsb.subscribe(EVT_2, obj.cb_2)
    print pbsb
    for event in lstEvents:
        pbsb.publish(event)
    print

    pbsb.subscribeList([EVT_3,EVT_4], obj.cb_3)
    print pbsb
    for event in lstEvents:
        pbsb.publish(event)
    print

    pbsb.unsubscribe(EVT_1, obj.cb_1)
    print pbsb
    for event in lstEvents:
        pbsb.publish(event)
    print

    pbsb.unsubscribeList([EVT_3,EVT_4], obj.cb_3)
    print pbsb
    for event in lstEvents:
        pbsb.publish(event)
    print
        
    
    