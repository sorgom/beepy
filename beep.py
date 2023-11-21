from threading import Event
import signal
import re
from os.path import isfile
from sys import argv
from getopt import getopt
from datetime import datetime
import winsound
# winsound.Beep(440, 100)

# class Round(object):
#     def __init__(self, pause, line):
#         self.up = list()
#         self.dn = list()
#         trg = self.up

#   up / down mode standard -s 
#   minutes up, same down + pause
#   R down with 1
#   r add to down
#   r:x all down x min
#   N down with 0 / 1
#   n:x down with 0 / x
#
#   -t x fix time mode, values are levels
#   -x explicit mode level:minutes
#   -r loop from here



class Beep(object):
    def __init__(self):
        self.exit = Event()
        for sig in ('TERM', 'INT'):
            signal.signal(getattr(signal, 'SIG' + sig), self.quit)
        self.rxF = re.compile(r'^\d+(?:\.\d*?)?$')
        self.rxI = re.compile(r'^\d+$')
        self.rxX = re.compile(r'^(\d+):(\d+(?:\.\d*?)?)', re.M)
        self.once = list()
        self.loop = list()
        self.inp  = self.once
        self.pause = 1.0
        self.start = self.now()
        self.mode = 's'
        self.dur  = 1.0

    def sleep(self, min:float):
        for n in range(int(min * 6000)):
            self.exit.wait(0.01)

    def quit(self, signo, *args):
        print('interrupt:', signo)
        self.exit.set()
    
    def now(self):
        return datetime.timestamp(datetime.now())

    def addX(self, args):
        seq = list()
        for c in args:
            mo = self.rxX.match(c)
            if mo:
                seq.append((int(mo.group(1)), float(mo.group(2))))
        if seq: self.inp.append(seq)

    def addS(self, args):
        up = list()
        dn = list()
        pt = up
        gen = False
        for c in args:
            mo = re.match(r'[Rr]:(\d+(?:\.\d*)?)', c)
            if mo:
                dur = float(mo.group(1))
                dn = [dur for n in up]
                gen = True
                break
            mo = re.match(r'[Nn]:(\d+(?:\.\d*)?)', c)
            if mo:
                dur = float(mo.group(1))
                dn = [dur if n else 0.0 for n in up]
                gen = True
                break
            if c == 'R':
                dn = [1.0 for n in up]
                gen = True
                break
            if c == 'N':
                dn = [1.0 if n else 0.0 for n in up]
                gen = True
                break

            if c == 'r':
                pt = dn
            elif self.rxF.match(c):
                pt.append(float(c))
                
        lu = len(up)
        ld = len(dn)
        lm = lu - 1

        if gen:
            dn.pop()
            dn.reverse()
        else:
            cp = up.copy()
            cp.pop()
            cp.reverse()
            for n in range(ld, lm):
                dn.append(cp[n])
            dn = dn[0:lm]

        dn.append(self.pause)

        seq = list()
        for n, v in enumerate(up):
            seq.append((n + 1, float(v)))
        for n, v in enumerate(dn):
            seq.append((lm - n, float(v)))
        
        seq = [(n, v) for n, v in seq if v > 0.0]
        self.inp.append(seq)

    def addF(self, fp):
        with open(fp, 'r') as fh:
            txt = re.sub(r'^#.*\s*', '', fh.read(), flags=re.M)
            txt = re.sub(r'^\s*', '', txt, flags=re.M)
            txt = re.sub(r'\s*$', '', txt)
            print(txt)
            for line in txt.split('\n'):
                self.add(line.split())
        # self.rxCom = re.compile(r'^#.*\s*', re.M)
        print('once')
        for l in self.once: print(l)
        print('loop')
        for l in self.loop: print(l)

    def addT(self, args):
        seq = [(int(c), self.dur) for c in args if self.rxI.match(c)]
        if seq: self.inp.append(seq)

    def add(self, args):
        opts, args = getopt(args, 'p:rst:x')
        for o, v in opts:
            if (o == '-p'):
                self.pause = v
            elif (o == '-r'):
                self.inp = self.loop
            elif (o == '-t'):
                self.mode = 't'
                self.dur = float(v)
            else:
                self.mode = o[1]

        print('mode', self.mode)

        if len(args) == 1 and isfile(args[0]):
            self.addF(args[0])
        elif not args:
            pass
        elif self.mode == 's':
            self.addS(args)
        elif self.mode == 'x':
            self.addX(args)
        elif self.mode == 't':
            self.addT(args)
        
 
if __name__ == '__main__':
    bp = Beep()
    print(bp.start)

    # def testS(data:str):
    #     print('testS:', data)
    #     bp.addS(data.split())    

    # testS('1 2  3 4 5 6')
    # testS('1 2  5 4 r 1 1 2 4')
    # testS('1 2 0 5 4 N')
    # testS('1 2 0 5 4 N:3')

    # def testX(data:str):
    #     print('testX:', data)
    #     bp.addX(data.split())    

    # testX('5:2 6:3 4:1')

    def testA(data:str):
        print('testA:', data)
        bp.add(data.split())    

    # testA('-x 5:2 6:3 4:1')
    testA('-sp 5.5 beepTimes_3.dat')

    # bp.sleep(10.5)