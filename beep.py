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

class Beeper(object):
    def __init__(self):
        self.freq = {
            'c': 523,
            'd': 587,
            'e': 659,
            'f': 698,
            'g': 740,
            'a': 880,
            'h': 988
        }
    def play(self, mel:str, ms=200):
        for c in mel:
            fr = self.freq.get(c)
            if fr:
                winsound.Beep(fr, ms)

class Step(object):
    def __init__(self, val:int, min:float):
        self.val = val
        self.sec = int(min * 60 + 0.5)
        self.next = -1
    def __str__(self):
        return "%d %d:%02d %d" % (self.val, int(self.sec / 60), self.sec % 60, self.next)

class Beep(object):
    def __init__(self):
        self.exit = Event()
        self.beeper = Beeper()
        for sig in ('TERM', 'INT'):
            signal.signal(getattr(signal, 'SIG' + sig), self.quit)
        self.rxF = re.compile(r'^\d+(?:\.\d*?)?$')
        self.rxI = re.compile(r'^\d+$')
        self.rxX = re.compile(r'^(\d+):(\d+(?:\.\d*?)?)', re.M)
        self.once = list()
        self.loop = list()
        self.inp  = self.once
        self.pause = 1.0
        self.next = self.now()
        self.mode = 's'
        self.dur  = 1.0

    def sleep(self, sec:float=1):
        for n in range(int(sec * 100)):
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
                seq.append(Step(int(mo.group(1)), float(mo.group(2))))
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
        
        seq = [Step(n, v) for n, v in seq if v > 0.0]
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

    def addT(self, args):
        seq = list()
        for c in args:
            if self.rxI.match(c):
                s = Step(int(c), self.dur)
                if len(seq) > 0 and s.val == seq[-1].val:
                    seq[-1].sec += s.sec
                else:
                    seq.append(s)
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

    def connect(self, seqs:list):
        lseqs = len(seqs)
        for nseq, seq in enumerate(seqs):
            lseq = len(seq)
            for nstp, stp in enumerate(seq):
                nxt = (nstp + 1) % lseq
                stp.next = seq[nxt].val

            nxs = (nseq + 1) % lseqs
            seq[-1].next = seqs[nxs][0].val
                
    def runStep(self, step:Step):
        self.next += step.sec
        beeped = False
        print()
        dt = step.sec
        self.stepOut(step, dt)
        self.beeper.play('hh')
        while dt > 0:
            if (dt <= 16 and not beeped):
                if step.next > step.val:
                    self.beeper.play('ceg')
                elif step.next < step.val:
                    self.beeper.play('ge')
                beeped = True
            self.sleep(0.25)
            dt = self.next - self.now()
            self.stepOut(step, dt, beeped)

    def stepOut(self, step:Step, sec:int, nx:bool=False):
        min = int(sec / 60)
        sec = int(sec % 60)
        print("%2d %2d:%02d" % (step.val, min, sec), end = '')
        if nx:
            print(" ->%3d" % step.next, end = '')
        print(end = '\r')


    def run(self, args):
        self.add(args)
        self.connect(self.once)
        self.connect(self.loop)
        if self.once and self.loop:
            self.once[-1][-1].next = self.loop[0][0].val

        print('once')
        for l in self.once: print(*[str(s) for s in l])
        print('loop')
        for l in self.loop: print(*[str(s) for s in l])

    def tInfo(self, curr:int, sec, next:int):
        min = int(sec / 60)
        sec = int(sec % 60)
        print("%2d %2d:%02d ->%3d" % (curr, min, sec, next), end = '\r')



if __name__ == '__main__':
    bp = Beep()
    print(bp.next)

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

    def testR(data:str):
        print('testA:', data)
        bp.run(data.split())    

    # testA('-x 5:2 6:3 4:1')
    # testR('-sp 5.5 beepTimes_3.dat')

    # bp.tInfo(2, 125, 8)
    # print()
    # bp.sleep(10.5)

    s = Step(2, 0.4)
    s.next = 8
    bp.runStep(s)
    s.next = 1
    bp.runStep(s)

    # bpr = Beeper()
    # bpr.play('ceg')
    # bp.sleep(1)
    # bpr.play('gec')
    # bp.sleep(1)
    # bpr.play('hh')