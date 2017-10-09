#
# These tests stand up a separate client and server instance of 
# networktables and tests the 'real' user API to ensure that it
# works correctly
#

from __future__ import print_function

import pytest

import logging
logger = logging.getLogger('test')


# test defaults
def doc(nt):
    t = nt.getTable('nope')
    
    with pytest.raises(KeyError):
        t.getBoolean('b')
    
    with pytest.raises(KeyError):
        t.getNumber('n')
        
    with pytest.raises(KeyError):
        t.getString('s')
    
    with pytest.raises(KeyError):
        t.getBooleanArray('ba')
    
    with pytest.raises(KeyError):
        t.getNumberArray('na')
        
    with pytest.raises(KeyError):
        t.getStringArray('sa')
        
    with pytest.raises(KeyError):
        t.getValue('v')
    
    assert t.getBoolean('b', True) is True
    assert t.getNumber('n', 1) == 1
    assert t.getString('s', 'sss') == 'sss'
    assert t.getBooleanArray('ba', (True,)) == (True,)
    assert t.getNumberArray('na', (1,)) == (1,)
    assert t.getStringArray('sa', ('ss',)) == ('ss',)
    assert t.getValue('v', 'vvv') == 'vvv'

def do(nt1, nt2, t):
        
    t1 = nt1.getTable(t)
    with nt2.expect_changes(8):
        t1.putBoolean('bool', True)
        t1.putNumber('number1', 1)
        t1.putNumber('number2', 1.5)
        t1.putString('string', 'string')
        t1.putString('unicode', u'\xA9')  # copyright symbol
        t1.putBooleanArray('ba', (True, False))
        t1.putNumberArray('na', (1, 2))
        t1.putStringArray('sa', ('s', 't'))
    
    t2 = nt2.getTable(t)
    assert t2.getBoolean('bool') is True
    assert t2.getNumber('number1') == 1
    assert t2.getNumber('number2') == 1.5
    assert t2.getString('string') == 'string'
    assert t2.getString('unicode') == u'\xA9'  # copyright symbol
    assert t2.getBooleanArray('ba') == (True, False) 
    assert t2.getNumberArray('na') == (1, 2)
    assert t2.getStringArray('sa') == ('s', 't')
    
    # Value testing
    with nt2.expect_changes(6):
        t1.putValue('v_b', False)
        t1.putValue('v_n1', 2)
        t1.putValue('v_n2', 2.5)
        t1.putValue('v_s', 'ssss')
        t1.putValue('v_s2', u'\xA9')
        
        t1.putValue('v_v', 0)
        
    print(t2.getKeys())
    assert t2.getBoolean('v_b') is False
    assert t2.getNumber('v_n1') == 2
    assert t2.getNumber('v_n2') == 2.5
    assert t2.getString('v_s') == 'ssss'
    assert t2.getString('v_s2') == u'\xA9'
    assert t2.getValue('v_v') == 0
    
    # Ensure that updating values work!
    with nt2.expect_changes(8):
        t1.putBoolean('bool', False)
        t1.putNumber('number1', 2)
        t1.putNumber('number2', 2.5)
        t1.putString('string', 'sss')
        t1.putString('unicode', u'\u2122')  # (tm)
        t1.putBooleanArray('ba', (False, True, False))
        t1.putNumberArray('na', (2, 1))
        t1.putStringArray('sa', ('t', 's'))
    
    t2 = nt2.getTable(t)
    assert t2.getBoolean('bool') is False
    assert t2.getNumber('number1') == 2
    assert t2.getNumber('number2') == 2.5
    assert t2.getString('string') == 'sss'
    assert t2.getString('unicode') == u'\u2122'
    assert t2.getBooleanArray('ba') == (False, True, False) 
    assert t2.getNumberArray('na') == (2, 1)
    assert t2.getStringArray('sa') == ('t', 's')
    
    # Try out deletes -- but NT2 doesn't support them
    if nt2.proto_rev == 0x0300:
        if nt1.proto_rev == 0x0300:
            with nt2.expect_changes(1):
                t1.delete('bool')
                
            with pytest.raises(KeyError):
                t2.getBoolean('bool')
        else:
            t1.delete('bool')
            
            with nt2.expect_changes(1):
                t1.putBoolean('ooo', True)
                
            assert t2.getBoolean('bool') is False
            
    else:
        t1.delete('bool')
        
        with nt2.expect_changes(1):
            t1.putBoolean('ooo', True)
                
        assert t2.getBoolean('bool') is False


def test_basic(nt_live):
    
    nt_server, nt_client = nt_live
    
    assert nt_server.isServer()
    assert not nt_client.isServer()
        
    doc(nt_client)
    doc(nt_server)
    
    # server -> client
    do(nt_server, nt_client, 'server2client')
    
    # client -> server
    do(nt_client, nt_server, 'client2server')

    assert nt_client.isConnected()
    assert nt_server.isConnected()
    

def test_reconnect(nt_live):
    
    nt_server, nt_client = nt_live
    
    with nt_server.expect_changes(1):
        ct = nt_client.getTable('t')
        ct.putBoolean('foo', True)
        
    st = nt_server.getTable('t')
    assert st.getBoolean('foo') == True
    
    # Client disconnect testing
    nt_client.shutdown()
    
    logger.info("Shutdown the client")
    
    with nt_client.expect_changes(1):
        nt_client.start_test()
        ct = nt_client.getTable('t')
    
    assert ct.getBoolean('foo') == True
    
    # Server disconnect testing
    nt_server.shutdown()
    logger.info("Shutdown the server")
    
    # synchronization change: if the client doesn't touch the entry locally,
    # then it won't get transferred back to the server on reconnect. Touch
    # it here to ensure that it comes back
    ct.putBoolean('foo', True)
    
    with nt_server.expect_changes(1):
        nt_server.start_test()
        
    st = nt_server.getTable('t')
    assert st.getBoolean('foo') == True

