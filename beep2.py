#   ============================================================
#   beeping training enhancer
#   ============================================================
from datetime import datetime
from getopt import getopt
from modBeeper import Beeper
from os.path import isfile
from sys import argv
from threading import Event
import random, re, signal

class Step(object):
    def __init__(self, val:int, min:float):
        self.val = val
        self.sec = int(min * 60)
        self.next = 0

class Time(object):
    def __init__(self):
        self.next = self.now()
    def now(self):
        return datetime.timestamp(datetime.now())


class Sequence(object):
    def __init__(self, beeper:Beeper, time:Time):   
        self.steps = []
        self.next = None
        self.beeper = beeper
        self.time = time

    def setNext(self, next:'Sequence'):
        self.next = next

    def run(self):
        """run the sequence"""
    
    def runStep(self, step:Step, nextVal:int):
        """run the step"""
        pass
    
    def getFirstVal(self, lastVal:int)-> int:
        """get the first value"""
        return 1
    
    def stepOut(self, step:Step, sec:int, nx:bool=False):
        if sec < 0: return
        nstr = ''
        if nx: nstr = '-> %d' % step.next
        print("%4d %s %-20s" % (step.val, self.tStr(sec), nstr), end = '\r')


    def tStr(self, sec):
        min = int(sec / 60)
        hrs = int(min / 60)
        min = min % 60
        sec = sec % 60
        str = f'{min:02d}:{sec:02d}'
        if hrs > 0:
            return f'{hrs:d}:' + str
        return str
