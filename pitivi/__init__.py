"""
Main Pitivi package
"""

from ctypes import cdll
x11 = cdll.LoadLibrary('libX11.so')
x11.XInitThreads()
