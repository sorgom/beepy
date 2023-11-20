from threading import Event
import signal
import re
from os.path import isfile
from sys import argv
from getopt import getopt
from datetime import datetime

class Round(object):
    def __init__(self, pause, line):
        self.up = list()
        self.dn = list()
        trg = self.up



class Beep(object):
    def __init__(self):
        self.exit = Event()
        for sig in ('TERM', 'INT'):
            signal.signal(getattr(signal, 'SIG' + sig), self.quit)
        self.rxMin = re.compile(r'^\d+(?:\.\d+?)')
        self.rxCom = re.compile(r'^#.*\n?', re.M)
        self.once = list()
        self.loop = list()
        self.inp  = self.loop
        self.pause = 1
        self.start = self.now()

    def sleep(self, min:float):
        for n in range(int(min * 6000)):
            self.exit.wait(0.01)

    def quit(self, signo, *args):
        print('interrupt:', signo)
        self.exit.set()
    
    def now(self):
        return datetime.timestamp(datetime.now())

    def addSched(self, args):
        opts, args = getopt(args, 'p:r')
        line = list
        for o, v in opts:
            if (o == '-p'):
                self.pause = v
            elif (o == '-r'):
                self.inp = self.loop
        if len(args) == 1 and isfile(args[0]):
            self.addFile(args[0])
            return
        for c in args:
            if self.rxMin.match(c):
                line.append(float(c))
            elif isfile(c):
                self.addFile(c)

    def addFile(self, fp):

        
 
if __name__ == '__main__':
    bp = Beep()
    print(bp.start)
    # bp.sleep(10.5)