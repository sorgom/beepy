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
        # return
        for c in mel:
            fr = self.freq.get(c)
            if fr:
                winsound.Beep(fr, ms)

class Step(object):
    def __init__(self, val:int, min:float):
        self.val = val
        self.sec = int(min * 60)
        self.next = -1

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
        self.stats = list()

    def sleep(self, sec:float=1):
        for n in range(int(sec * 100)):
            self.exit.wait(0.01)

    def quit(self, *args):
        self.exit.set()
        self.dumpStats()
        exit()
    
    def now(self):
        return datetime.timestamp(datetime.now())

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
            for line in txt.split('\n'):
                self.add(line.split())

    def addX(self, args):
        seq = list()
        for c in args:
            s = None
            mo = self.rxX.match(c)
            if mo:
                s = Step(int(mo.group(1)), float(mo.group(2)))
            elif self.rxI.match(c):
                s = Step(int(c), self.dur)
            if s:
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
                self.mode = 'x'
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

    def connect(self, seqs:list):
        lseqs = len(seqs)
        for nseq, seq in enumerate(seqs):
            lseq = len(seq)
            for nstp, stp in enumerate(seq):
                nxt = (nstp + 1) % lseq
                stp.next = seq[nxt].val

            nxs = (nseq + 1) % lseqs
            seq[-1].next = seqs[nxs][0].val
                
    def runSeq(self, seq, out=False):
        if out: self.seqOut(seq)
        for step in seq: self.runStep(step)

    def runStep(self, step:Step):
        self.next += step.sec
        beeped = False
        dt = step.sec
        self.stepOut(step, dt)
        self.beeper.play('h', 400)
        while dt > 0:
            if (dt <= 16 and not beeped):
                if step.next > step.val:
                    self.beeper.play('eg')
                elif step.next < step.val:
                    self.beeper.play('ge')
                beeped = True
            self.stepOut(step, dt, beeped)
            self.sleep(0.2)
            dt = self.next - self.now()
        self.stats[step.val] += step.sec
        # print()

    def stepOut(self, step:Step, sec:int, nx:bool=False):
        if sec < 0: return
        min = int(sec / 60)
        sec = sec % 60
        nstr = ''
        if nx: nstr = '-> %d' % step.next
        print("%4d %2d:%02d %-20s" % (step.val, min, sec, nstr), end = '\r')

    def seqOut(self, seq:list):
        ma  = max([s.val for s in seq])
        sec = sum([s.sec for s in seq])
        min = int(sec / 60)
        sec = sec % 60
        print('%2d:%02d max: %d               ' % (min, sec, ma))

    def allOut(self, show=True):
        ma = 0
        sec = 0
        for seq in [*self.once, *self.loop]:
            ma = max([ma, *[s.val for s in seq]])
            sec += sum([s.sec for s in seq])
        mis = int(sec / 60)
        hrs = int(mis / 60)
        mis = mis % 60
        sec = sec % 60
        if show:
            if hrs > 0:
                print('%d:%02d:%02d max: %d' % (hrs, mis, sec, ma))
            else:
                print('%2d:%02d max: %d' % (mis, sec, ma))
        return ma

    def dumpStats(self):
        file = __file__ + '.stats'
        a = list()
        if isfile(file):
            with open(file, 'r') as fh:
                a = [int(c) for c in fh.read().split()]
        b = self.stats
        c = [0 for n in range(max(len(a), len(b)))]
        for n, v in enumerate(a): c[n] += v
        for n, v in enumerate(b): c[n] += v
        tmin = 0
        print()
        print('statistics')
        for n, sec in enumerate(c):
            min = int((sec + 30) / 60)
            tmin += min
            hrs = int(min / 60)
            min = min % 60
            print('%2d:%5d:%02d' % (n, hrs, min))

        print('tt:%5d:%02d' % (tmin / 60, tmin % 60))
        if b.count(0) == len(b): return
        with open(file, 'w') as fh:
            fh.write(' '.join([str(n) for n in c]))

    def run(self, args):
        self.add(args)
        if self.once and not self.loop:
            self.loop.append(self.once.pop())

        self.connect(self.once)
        self.connect(self.loop)
        if self.once and self.loop:
            self.once[-1][-1].next = self.loop[0][0].val

        l1 = len(self.once)
        l2 = len(self.loop)

        ma = self.allOut((l1 + l2) > 1)
        self.stats = [0 for n in range(ma + 1)]
        if l1 == 1:
            self.seqOut(self.once[0])
        for seq in self.once: self.runSeq(seq, l1 > 1)
        if l2 == 1:
            self.seqOut(self.loop[0])
        while True:
            for seq in self.loop: self.runSeq(seq, l2 > 1)

if __name__ == '__main__':
    Beep().run(argv[1:])
