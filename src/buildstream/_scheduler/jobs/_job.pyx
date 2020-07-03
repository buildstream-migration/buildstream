from cpython.pystate cimport PyThreadState_SetAsyncExc
from cpython.ref cimport PyObject
from ..._signals import TerminateException


# abort_thread()
#
# Abort a given thread by raising an exception in it.
#
# Args:
#   thread_id (int): the thread id in which to throw the exception
#
def abort_thread(long thread_id):
    res = PyThreadState_SetAsyncExc(thread_id, <PyObject*> TerminateException)
    assert res == 1
