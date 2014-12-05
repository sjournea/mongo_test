""" expression.py - Expression processing  

        Build an expression by creating an equation, example A+B*C
        Paranthesis can be used to alter the order of calculations, example (A+B)*C

        Variables are allowed in expressions. Example (StdDev <= 30e-12).
        All variables used MUST be an Input parameter or a Result parameter in the current test.
        Variables are CASE-SENSITIVE.\r\n"

        Expression results can be used in other expressions BUT the order the expression variable
        is created in the MVP test determines if an expression variable can be used. All expression
        variables displayed before the current expression variable in the MVP AutoDoc Editor could be
        used by the current expression variable.

        Operators available in expressions:
          + - * /     : Basic arithematic operators
          **          : Raise to a power (Ex. 2**4 = 16)

        Built-in functions available in expressions:
          abs(x)                  : absolute value of x
          sqrt(x)                 : square root of x
          exp(x)                  : returns e**x
          sin(x)  cos(x)  tan(x)  : trig functions
          asin(x) acos(x) atan(x) : arc trig functions
          sinh(x) cosh(x) tanh(x) : hyperbolic trig functions
          log(x)                  : natural log of x
          log10(x)                : base 10 log of x
          floor(x)                : returns x to the largest integer not greater then x

        Boolean operators are available to perform boolean expressions, Example (StdDev <= 30e-12). Only ONE boolean operator should be
        used in an expression. The result value of a boolean expression will be 1.0 for true and 0.0 for false.
        Boolean operators available in expressions:
          == : are values equal
          != : are values not equal
          >  : is value greater then
          >= : is value greater then or equal
          <  : is value less then
          <= : is value less then or equal

 """

import math,logging

from ascii import *
from tl_logger import TLLog
log = TLLog.getLogger( 'expr' )

# States for Scanning of expressions
START = 'START'
TOP = 'TOP'
NAME = 'NAME'
NUMBER = 'NUMBER'
NUMBER_EXP = 'NUMBER_EXP'
NUMBER_DEC = 'NUMBER_DEC'
PARAN = 'PARAN'

class ExprException(Exception):
    pass

class Operator(object):
    """ Operator definition class, all public """
    def __init__(self, sID, iPrec, bBO = False):
        self.ID = sID
        self.prec = iPrec
        self.booleanOp = bBO

class Token(object):
    """ base class for all tokens """
    _sValidChars  = '+-*/=!()<>'
    _sUnaryOps    = '+-'
    _dctOperators = { '+'     : Operator( "+", 10, False ), 
                      '-'     : Operator( "-", 10, False ), 
                      '*'     : Operator( "*", 20, False ), 
                      '/'     : Operator( "/", 20, False ), 
                      '**'    : Operator( "**", 22, False ), 
                      'abs'   : Operator( "abs", 25, False ), 
                      'acos'  : Operator( "acos", 25, False ), 
                      'asin'  : Operator( "asin", 25, False ), 
                      'atan'  : Operator( "atan", 25, False ), 
                      'cos'   : Operator( "cos", 25, False ), 
                      'cosh'  : Operator( "cosh", 25, False ), 
                      'exp'   : Operator( "exp", 25, False ), 
                      'log'   : Operator( "log", 25, False ), 
                      'log10' : Operator( "log10", 25, False ), 
                      'sin'   : Operator( "sin", 25, False ), 
                      'sinh'  : Operator( "sinh", 25, False ), 
                      'sqrt'  : Operator( "sqrt", 25, False ), 
                      'tan'   : Operator( "tan", 25, False ), 
                      'tanh'  : Operator( "tanh", 25, False ), 
                      'floor' : Operator( "floor", 25, False ), 
                      '->'    : Operator( "->", 30, False ), 
                      '=='    : Operator( "==", 5, True ), 
                      '!='    : Operator( "!=", 5, True ), 
                      '>='    : Operator( ">=", 5, True ), 
                      '<='    : Operator( "<=", 5, True ), 
                      '>'     : Operator( ">", 5, True ), 
                      '<'     : Operator( "<", 5, True ), 
                      }

    @staticmethod
    def IsValidChar(ch):
        return ch in Token._sValidChars

    @staticmethod
    def IsUnaryOperator(ch):
        return ch in Token._sUnaryOps

    @staticmethod
    def IsOperator(sOP):
        return sOP in Token._dctOperators

    @staticmethod
    def GetOperator(sOP):
        if sOP in Token._dctOperators:
            return Token._dctOperators[sOP]
        raise ExprException( 'Operator \"%s\" not found' % sOP ) 

    def __init__(self, token=None):
        self.token = token

    def isOperand(self):
        return False

    def isOperator(self):
        return False

    def isOK(self):
        return True

    def getVars(self):
        return []

    def show(self, indent, bScanOrParse=False):
        log.info( '%s%-10s : %s' % (indent, self.getType(), self.token))

    def __str__(self):
        return '%-10s : %s' % (self.getType(), self.token)

class OperandToken(Token):
    def __init__( self, token ):
        Token.__init__(self, token)

    def isOperand(self):
        return True

class OperatorToken(Token):
    def __init__( self, token, paramCount=2 ):
        Token.__init__(self, token)
        self.paramCount = paramCount

    def isOperator(self):
        return True

    def getType(self):
        return 'Operator'

    def isBoolean(self):
        op = Token.GetOperator( self.token )
        return op.booleanOp

    def precedence(self):
        op = Token.GetOperator( self.token )
        return op.prec

    def getValue(self, lst):
        if len(lst) != self.paramCount:
            raise ExprException( 'OperatorToken getValue() fail - incorrect parameter count %d (expecting %d) for operator "%s"' % (len(lstParams),self.paramCount,self.token)) 

        value = None
        if self.paramCount == 1:
            # unary operator
            if self.token == '+':
                value = lst[0]
            elif self.token == '-':
                value = -lst[0]
            elif self.token == 'abs':
                value = math.fabs(lst[0])
            elif self.token == 'acos':
                value = math.acos(lst[0])
            elif self.token == 'asin':
                value = math.asin(lst[0])
            elif self.token == 'atan':
                value = math.atan(lst[0])
            elif self.token == 'cos':
                value = math.cos(lst[0])
            elif self.token == 'exp':
                value = math.exp(lst[0])
            elif self.token == 'log':
                value = math.log(lst[0])
            elif self.token == 'log10':
                value = math.log10(lst[0])
            elif self.token == 'sin':
                value = math.sin(lst[0])
            elif self.token == 'sqrt':
                value = math.sqrt(lst[0])
            elif self.token == 'tan':
                value = math.tan(lst[0])
            elif self.token == 'floor':
                value = math.floor(lst[0])
            else:
                raise ExprException( 'OperatorToken getValue() fail - Token "%s" not supported for one parameter' % self.token) 

        elif self.paramCount == 2:
            # 2 parameters 
            if self.token == '+':
                value = lst[1] + lst[0]
            elif self.token == '-':
                value = lst[1] - lst[0]
            elif self.token == '*':
                value = lst[1] * lst[0]
            elif self.token == '/':
                value = lst[1] / lst[0]
            elif self.token == '**':
                value = math.pow( lst[1], lst[0])
            elif self.token == '==':
                value = lst[1] == lst[0]
            elif self.token == '!=':
                value = lst[1] != lst[0]
            elif self.token == '>':
                value = lst[1] > lst[0]
            elif self.token == '>=':
                value = lst[1] >= lst[0]
            elif self.token == '<':
                value = lst[1] < lst[0]
            elif self.token == '<=':
                value = lst[1] <= lst[0]
            else:
                raise ExprException( 'OperatorToken getValue() fail - Token "%s" not supported for 2 parameters' % self.token) 
        else:
            raise ExprException( 'OperatorToken getValue() fail - Token "%s" not supported for %d parameters' % (self.token, len(lst)))
        # return the value
        return value

class VariableToken(OperandToken):
    def __init__(self, token, tstObj):
        OperandToken.__init__(self, token)
        self.tstObj = tstObj

    def getType(self):
        return 'Variable'

    def getValue(self):
        param = self.tstObj.getParameter( self.token )
        if param is None:
            raise ExprException( 'Variable "%s" getValue() fail' % self.token )
        return param.value

    def isOK(self):
        param = self.tstObj.getParameter( self.token )
        if param is None:
            log.error( 'Variable "%s" not found' % self.token )
            return False
        return True

    def getVars(self):
        return [ self.token ]


class ConstantToken(OperandToken):
    def __init__(self, token):
        OperandToken.__init__(self, token)

    def getType(self):
        return 'Constant'

    def getValue(self):
        return self.value

class IntToken(ConstantToken):
    def __init__(self, token):
        ConstantToken.__init__(self, token)
        self.value = int(token)

    def getType(self):
        return 'Int'

class FloatToken(ConstantToken):
    def __init__(self, token):
        ConstantToken.__init__(self, token)
        self.value = float(token)

    def getType(self):
        return 'Float'

class Expression(OperandToken):
    """ Expression processing class """
    def __init__(self, name, tstObj, pData=None, expr=None):
        OperandToken.__init__(self, None)
        self.name = name
        self.tstObj = tstObj
        self.pData = pData
        self.expr = None
        if expr is not None:
            self.setExpression( expr )
        self.clear()

    def __cmp__(self,other):
        if self.isBoolean() and other.isBoolean():
            return 0
        if not self.isBoolean() and other.isBoolean():
            return -1
        if self.isBoolean() and not other.isBoolean():
            return 1

    def setExpression( self, expr):
        self.expr = expr
        self.token = expr

    def getExpression(self):
        return self.expr

    def getType(self):
        return 'Expression'

    def clear(self):
        self.lstTokens = []
        self.lstPostfix = []
        self.hasVariables = False
        self.value = None

    def generate(self):
        """ generate the postfix tokens """ 
        log.debug( 'Expression generate() - Expr "%s"' % self.expr)
        self.clear()
        # scan the infix expression for infix tokens 
        self._scan()
        # log infix tokens
        log.debug( 'Scan Tokens: %d total' % len(self.lstTokens))
        if log.isEnabledFor( logging.DEBUG):
            for tok in self.lstTokens:
                tok.show( ' ', False)
        # generate the postfix tokens from the infix tokens
        self._parse()
        # log infix tokens
        log.debug( 'Postfix Tokens: %d total' % len(self.lstPostfix))
        if log.isEnabledFor( logging.DEBUG):
            for tok in self.lstPostfix:
                tok.show( ' ', True)

    def validate(self):
        log.info( 'Expression validate() - Expr "%s"' % self.expr)
        # Verify all variables exist
        for tok in self.lstPostfix:
            if not tok.isOK():
                return False
        return True

    def getVariables(self):
        pass

    def isOK(self):
        for tok in self.lstPostfix:
            if not tok.isOK():
                return False
        return True

    def getVars(self):
        lst = []
        for tok in self.lstPostfix:
            lst.extend( tok.getVars() )
        return lst

    def isBoolean(self):
        if len(self.lstPostfix) == 0:
            raise ExprException( "IsBoolean() fail -- Generate() has not been performed" )

        if len(self.lstPostfix) == 1:
            # one value MUST be an operand to generate a value
            if not isinstance( self.lstPostfix[0], OperandToken):
                raise ExprException( "IsBoolean() fail -- one token in expression and it is not an Operand" )
            return False

        # more then one postfix token, last token MUST be an operator, check if boolean 
        lastOP = self.lstPostfix[-1]
        if not isinstance( lastOP, OperatorToken):
            raise ExprException( "IsBoolean() fail -- Last token is not an Operator" )
        return lastOP.isBoolean()

    def getValue(self):
        self.updateValue()
        return self.value
    
    def updateValue(self):
        # verify expression has been generated
        if len(self.lstPostfix) == 0:
            raise ExprException( "Expression getValue() fail -- generate() has not been performed" )

        # Verify tstObj exists if expression has variables
        if self.hasVariables and self.tstObj is None:
            raise ExprException( "Expression getValue() fail -- expression has variables and tstObj has not been set" );

        # Evaluate expression
        #   for_each token in postfix expression:
        #      if token is operand:
        #         GetValue and push on stack
        #      if token is operator:
        #         Pop needed values from stack based on how many operator uses
        #         Apply operator using popped values
        #         push result back on stack
        #   when complete return value on stack (should be one)

        stk = []
        for tok in self.lstPostfix:
            if tok.isOperand():
                value = tok.getValue()
                stk.append( value )
            else:
                # Operator
                lstParams = []
                for i in xrange( tok.paramCount):
                    lstParams.append( stk.pop() )
                value = tok.getValue( lstParams )
                stk.append( value )
        # should be one value left on stack
        # return it
        self.value = stk.pop()
        return self.value

    def _scan(self):
        log.debug( 'Expression scan()' )
        state = START
        log.debug( 'expr:%s' % self.expr)
        # remove all whitespace from expression
        # TODO: operators with a space (eg > =) will be packed togather and now legal
        expr = self.expr.translate(None,' ') + '\n'   # Must end with white space

        index = 0
        paranCount = 0
        while True:
            if index == len(expr):
                break

            ch = expr[index]
            index += 1

            if state == START:
                if isspace(ch):
                    break
                if Token.IsUnaryOperator( ch ):
                    self.addOperatorToken( ch, 1 )
                else:
                    index -= 1
                state = TOP

            elif state == TOP:
                if isspace(ch):
                    break

                s = ch
                if isalpha(ch):
                    state = NAME
                elif isdigit(ch):
                    state = NUMBER;
                elif ch == '(':
                    paranCount += 1
                    sParan = ''
                    state = PARAN
                elif ch == '.':
                    # Starts with a period, this is a number starting with a decimal point
                    # start the value string with "0."
                    s = '0.'
                    state = NUMBER_DEC;
                elif Token.IsValidChar( ch ):
                    if (ch == '-' and expr[index] == '>') or (ch == '>' and expr[index] == '=') or (ch == '<' and expr[index] == '=') or (ch == '*' and expr[index] == '*'):
                        s += expr[index]
                        index += 1
                    elif ch == '=' or ch == '!':
                        if expr[index] == '=': 
                            s += expr[index]
                            index += 1
                        else:
                            self.parseError( ch, "TOP" )
                    self.addOperatorToken( s )
                    s = ''
                else:
                    self.parseError( ch, "TOP" )

            elif state == NAME:
                if isalnum(ch) or ch == '_':
                    s += ch
                else:
                    self.addVariableToken( s )
                    s = ''
                    state = TOP
                    index -= 1

            elif state == NUMBER:
                if isdigit(ch):
                    s += ch
                elif ch == '.':
                    s += ch
                    state = NUMBER_DEC
                elif ch in 'eE':
                    s += ch
                    if expr[index] == '-':
                        s += '-'
                        index += 1
                    state = NUMBER_EXP
                elif isspace(ch) or Token.IsValidChar( ch ):
                    self.addNumberToken( s )
                    s = ''
                    state = TOP
                    index -= 1
                else:
                    self.parseError( ch, "NUMBER" )

            elif state == NUMBER_DEC:
                if isdigit(ch):
                    s += ch
                elif ch in 'eE':
                    s += ch
                    if expr[index] == '-':
                        s += '-'
                        index += 1
                    state = NUMBER_EXP
                elif isspace(ch) or Token.IsValidChar( ch ):
                    self.addNumberToken( s )
                    s = ''
                    state = TOP
                    index -= 1
                else:
                    self.parseError( ch, "NUMBER_DEC" )

            elif state == NUMBER_EXP:
                if isdigit(ch):
                    s += ch
                elif isspace(ch) or Token.IsValidChar( ch ):
                    self.addNumberToken( s )
                    s = ''
                    state = TOP
                    index -= 1
                else:
                    self.parseError( ch, "NUMBER_EXP" )

            elif state == PARAN:
                if isspace( ch ):
                    pass
                else:
                    if ch == ')':
                        paranCount -= 1
                        if paranCount == 0:
                            self.addExpressionToken( sParan )
                            state = TOP
                    if ch == '(':
                        paranCount += 1
                    sParan += ch
            else:
                raise ExprException( 'ScanState %d not found' % state )

    def _parse(self):
        """ parse the infix tokens into a postfix expression """
        log.debug( 'Expression parse() - expr "%s"' % self.expr )
        index = 0
        stkTokens = []

        while True:
            if index == len(self.lstTokens):
                break

            tok = self.lstTokens[index]
            index += 1

            if tok.isOperand():
                # operand is always put into postfix list
                self.lstPostfix.append( tok )
                continue

            # Operators
            #   if stack is empty then push into stack
            #   pop all operators with precedence greater then current operator and place int postfix vector
            #   push operator on stack
            while stkTokens:
                # get the top of stack without removing it
                top = stkTokens[-1]
                if tok.precedence() > top.precedence():
                    break
                # Add stack top to list postfix operators and remove from stack
                self.lstPostfix.append( stkTokens.pop() )
            # add token to stack
            stkTokens.append( tok )

        # now pop all remaining items operators from stack
        while stkTokens:
            self.lstPostfix.append( stkTokens.pop() )

    def show(self, indent='', bScanOrParse=False):
        log.info( '%s%-10s : %s' % (indent, self.getType(), self.token ))
        if bScanOrParse:
            for tok in self.lstPostfix:
                tok.show( indent + '  ', bScanOrParse)
        else:
            for tok in self.lstTokens:
                tok.show( indent + '  ', bScanOrParse)

    def addVariableToken(self, token):
        if Token.IsOperator( token ):
            self.lstTokens.append( OperatorToken( token, 1))
        else:
            self.lstTokens.append( VariableToken( token, self.tstObj))
            self.hasVariables = True

    def addNumberToken(self, token):
        for ch in 'eE.':
            if ch in token:
                self.lstTokens.append( FloatToken( token ))
                return 
        self.lstTokens.append( IntToken( token ))

    def addExpressionToken(self, token):
        expr = Expression( token, self.tstObj, self.pData)
        expr.setExpression( token )
        expr.generate()
        self.lstTokens.append( expr )

    def addOperatorToken(self, token, paramCount=2):
        self.lstTokens.append( OperatorToken( token, paramCount))

    def parseError(self, ch, parseState):
        raise ExprException( "Parse error on '%c' 0x%X. State:%s" % (ch, ord(ch), parseState))

if __name__ == '__main__':
    class TestParam(object):
        def __init__(self, name, value):
            self.name = name
            self.value = value

    class TestObj(object):
        def __init__(self, dct):
            self._dct = dct

        def getParameter(self, name):
            """ return a result parameter or None if not found """
            return self._dct.get(name, None)


    import logging
    TLLog.config( '..\\logs\\Expression.log', defLogLevel=logging.INFO )
    TLLog.enable( 'expr' )
    
    print 'Expression Test'
    log.info( 60*'*' )
    lstTestExprs = [ '50.0<55.0', '1+2', '1+5+6*2', '-45.67', '100*sqrt(3.0)','(A+B)*(D+C)','abs(supply12V - 12.0) <= 12.0*0.05']
    #lstTestExprs = [ '(A+B)*(D+C)','100*sqrt(3.0)','abs(supply12V - 12.0) <= 12.0*0.05']

    dct = { 'A' : TestParam('A',10), 
            'B' : TestParam('B',20), 
            'D' : TestParam('D',30), 
            'C' : TestParam( 'C', 40),
            'supply12V' : TestParam('supply12V',12.0 )
            } 
    testObj = TestObj( dct )

    index = 1
    for testExpr in lstTestExprs:
        print 'Expr: %40s ' % (testExpr),
        expr = Expression( 'test%d' % index, testObj, expr=testExpr)
        #expr.setExpression( testExpr )
        expr.generate()
        expr.updateValue()
        value = expr.getValue()
        print 'Value: %s' % (value )
        index += 1
