""" xml_util.py -- XML utility functions """
from xml.etree import ElementTree as ET

from ascii import *
from tl_logger import TLLog

log = TLLog.getLogger( 'xml_util' )

def boolValue( data ):
    """ if input is string is 'on','true','yes' or non-zero number then return True """ 
    b = False
    if data is not None:
        if data.isdigit():
            i = int(data)
            if i != 0:
                b = True
        else:
            data = data.lower()
            if data in ['yes','true','on']:
                b = True
    return b

class XMLReceiveQueue(object):
    """ Process all XML messages. """
    def __init__(self, lstTags):
        self.lstCompTags = lstTags
        if len(self.lstCompTags) == 0:
            log.error( 'XMLReceiveQueue lstCompTags is empty -- NO XML ELEMENTS WILL BE PROCESSED' )
        self.xmlData = ''
        self.stkTags = []
        self.stateFunc = self._waitForFirstStartTag

    def parseXMLMessage( self, xmlData ):
        """ overload to convert completed XML message into specific object for queue """
        log.error( 'parseXMLMessage() not overloaded -- ALL XML DATA IS IGNORED' )

    def processData(self, binData):
        """ process the received data """
        log.debug( 'processData - binData size=%d' % len(binData) )
        for ch in binData:
            self.stateFunc( ch )

    def _waitForFirstStartTag(self, ch):
        log.debug('_waitForFirstStartTag() - ch=%c 0x%02.x' % (ch, ord(ch)))
        if ch == '<':
            self.stateFunc = self._waitForStartTagName
            self.xmlData = ch

    def _waitForStartTag(self, ch):
        log.debug('_waitForStartTag() - ch=%c 0x%02.x' % (ch, ord(ch)))
        self.xmlData += ch
        if ch == '<':
            self.stateFunc = self._waitForStartTagName

    def _waitForStartTagName(self, ch):
        log.debug('_waitForStartTagName() - ch=%c 0x%02.x' % (ch, ord(ch)))
        self.xmlData += ch
        if isalpha(ch):
            self.stateFunc = self._waitForStartTagNameFinish
            self.startTag = ch
        elif ch == '/':
            self.stateFunc = self._waitForEndTagName

    def _waitForStartTagNameFinish(self, ch):
        log.debug('_waitForStartTagNameFinish() - ch=%c 0x%02.x' % (ch, ord(ch)))
        self.xmlData += ch
        if isspace(ch):
            self.stateFunc = self._waitForStartTagClose
        elif ch == '>':
            log.debug( 'startTag:%s' % self.startTag )
            self.stkTags.append( self.startTag )
            self.stateFunc = self._waitForStartTag
        else:
            self.startTag += ch

    def _waitForStartTagClose(self, ch):
        log.debug('_waitForStartTagClose() - ch=%c 0x%02.x' % (ch, ord(ch)))
        self.xmlData += ch
        if ch == '>':
            if self.xmlData[-2] == '/':
                log.debug( 'startTag / close:%s' % self.startTag )
                if self.startTag in self.lstCompTags:
                    self._completeXML()
            else:
                log.debug( 'startTag:%s' % self.startTag )
                self.stkTags.append( self.startTag )
            self.stateFunc = self._waitForStartTag

    def _waitForEndTagClose(self, ch):
        log.debug('_waitForEndTagClose() - ch=%c 0x%02.x' % (ch, ord(ch)))
        self.xmlData += ch
        if ch == '/':
            self.stateFunc = self._waitForEndTagName
        elif not isspace(ch):
            self.stateFunc = self._waitForEndTag

    def _waitForEndTagName(self, ch):
        log.debug('_waitForEndTagName() - ch=%c 0x%02.x' % (ch, ord(ch)))
        self.xmlData += ch
        if isalpha(ch):
            self.stateFunc = self._waitForEndTagNameFinish
            self.endTag = ch

    def _waitForEndTagNameFinish(self, ch):
        log.debug('_waitForEndTagNameFinish() - ch=%c 0x%02.x' % (ch, ord(ch)))
        self.xmlData += ch
        if isspace(ch) or ch == '>':
            log.debug( 'endTag:%s pop:%s' % (self.endTag, self.stkTags.pop()) )
            if ch == '>':
                self.stateFunc = self._waitForStartTag
                if self.endTag in self.lstCompTags:
                    self._completeXML()
            else:
                self.stateFunc = self._waitForEndTagClose
        else:
            self.endTag += ch

    def _waitForEndTagNameClose(self, ch):
        log.debug('_waitForEndTagNameClose() - ch=%c 0x%02.x' % (ch, ord(ch)))
        self.xmlData += ch
        if ch == '>':
            self.stateFunc = self._waitForStartTag
            if self.endTag in self.lstCompTags:
                self._completeXML()

    def _completeXML( self ):
        log.debug( '_completeXML() XML={%s}' % self.xmlData )
        self.parseXMLMessage( self.xmlData )
        self.xmlData = ''
        self.stateFunc = self._waitForFirstStartTag


class BaseXML(object):
    """ base class for XML objects """
    def __init__(self, tagName, dctEle=None, dctXML=None, xmlData=None):
        self.tagName = tagName
        self.xmlData = xmlData
        self.dctEle = {}
        self.dctXML = {}
        if dctEle is not None:
            self.dctEle = dctEle
        if dctXML is not None:
            self.dctXML = dctXML
        self.initialize()
        
    def initialize(self):
        if self.dctEle: 
            for element in self.dctEle.keys():
                setattr( self, element, None)

    def parseXML(self, eleRoot):
        for ele in eleRoot:
            if self.dctEle and ele.tag in self.dctEle:
                setattr( self, ele.tag, self.dctEle[ele.tag]( ele.text ))
            elif self.dctXML and ele.tag in self.dctXML:
                eventFunc = self.dctXML[ele.tag]
                if eventFunc is None:
                    x = ele.tag
                else:
                    x = eventFunc()
                    x.parseXML( ele )
                setattr( self, ele.tag, x)

    def toXMLString(self):
        s = '<%s>' % self.tagName
        for element in self.dctEle.keys():
            value = getattr(self, element)
            if value is not None:
                s += '<%s>%s</%s>' % (element, value, element)
        for element in self.dctXML.keys():
            if hasattr(self,element):
                value = getattr(self, element)
                if value is not None:
                    s += value.toXMLString()
        s += '</%s>' % self.tagName
        return s

    def toXML(self):
        xmlRoot = ET.Element(self.tagName)
        for element in self.dctEle.keys():
            value = getattr(self, element)
            if value is not None:
                x = ET.SubElement( xmlRoot, element )
                x.text = str(value)
        for element in self.dctXML.keys():
            if hasattr(self,element):
                value = getattr(self, element)
                if value is not None:
                    ele = value.toXML()
                    xmlRoot.append( ele )
        return xmlRoot

    def __str__(self):
        s = '%-6s -' % self.tagName 
        for element in self.dctEle.keys():
            s += ' %s:%s' % (element,getattr(self,element))
        return s


lstXMLSpecialChars = [ ('&','&amp;'), # must be first
                       ('<','&lt;'),
                       ('>','&gt;'),
                       ("'",'&apos'),
                       ('"', '&quot'),
                     ]
def xmlReplaceEscapeChars(text):
    """ replace all special characters in XML """
    for tup in lstXMLSpecialChars:
        text = text.replace( tup[0],tup[1] )
    return text

XML_INDENT = '  '
def xmlString(eleRoot, level=0):
    """ Create a string of XML element """
    
    s = level*XML_INDENT+ '<%s' % eleRoot.tag
    # attributes
    for name,value in eleRoot.items():
        s += ' %s="%s"' % (name,xmlReplaceEscapeChars(value))
    if len(eleRoot):
        # nested elements
        s += '>\n'  
        for ele in eleRoot:
            s += xmlString(ele, level+1)
        s += level*XML_INDENT + '</%s>\n' % eleRoot.tag
    else:
        # simple element
        if eleRoot.text:
            s += '>' + xmlReplaceEscapeChars(eleRoot.text) + '</%s>\n' % eleRoot.tag
        else:
            s += ' />\n'
    return s

if __name__ == '__main__':
    print 'xml_util tests'
    lstXML = [ '<event></event>',
               '<event>Data</event>',
               '<event />',
               '<event>     Data     </event>',
               '<event><d1>Data</d1><!-- Comment --><d2></d2></event>',
               '<event>Data &lt; 5</event>',
               ]
    for xml in lstXML:
        print 'XML:%s' % xml
        ele = ET.XML( xml )
        print xmlString( ele )
    