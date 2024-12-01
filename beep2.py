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
from collections import Counter

class Step(object):
    def __init__(self, val:int, sec:int):
        self.val = val
        self.sec = sec
        self.next = 0
    def __str__(self):
        return f'({self.val} {self.sec} {self.next})'

class Base(object):
    def __init__(self):
        self.beeper = Beeper()
        self.next = self.now()
        self.exit = Event()
        self.stats = Counter()
        self.counted = False
        for sig in ('TERM', 'INT'):
            signal.signal(getattr(signal, 'SIG' + sig), self.quit)
    
    def now(self):
        return datetime.timestamp(datetime.now())

    def moveNext(self, sec:int):
        self.next += sec

    def beepUp(self):
        self.beeper.play('DG', 200)
    def beepDown(self):
        self.beeper.play('FD', 200)
    def beepStart(self):
        self.beeper.play('c', 200)

    def sleep(self, sec:float=1):
        for n in range(int(sec * 100)):
            self.exit.wait(0.01)
    
    def count(self, step:Step):
        self.counted = True 
        self.stats[step.val] += step.sec

    def quit (self, *args):
        self.exit.set()
        if self.counted:
            self.dumpStats()
        exit()

    @staticmethod
    def tStr(sec:int)->str:
        min = int(sec / 60)
        hrs = int(min / 60)
        min = min % 60
        sec = int(sec % 60)
        return f'{hrs:d}:{min:02d}:{sec:02d}' if hrs > 0 else f'{min:2d}:{sec:02d}'

    @staticmethod
    def statStr(sec:int):
        min = int(sec / 60)
        hrs = int(min / 60)
        min = min % 60
        return f'{hrs:3d}:{min:02d}'

    def dumpStats(self):
        file = __file__ + '.stats'
        if isfile(file):
            with open(file, 'r') as fh:
                a = [int(c) for c in fh.read().split()]
                for v, s in enumerate(a):
                    self.stats[v] += s
        a = [self.stats[v] for v in range(max(self.stats.keys()) + 1)]
        with open(file, 'w') as fh:
            fh.write(' '.join([str(s) for s in a]))
        print('statistics')
        total = 0
        for v, s in enumerate(a):
            print(f'{v:3d}:', self.statStr(s))
            total += s
        print('sum:', self.statStr(total))
        
class Sequence(object):
    def __init__(self, base:Base):   
        self.steps = []
        self.next = None
        self.base = base

    def setNext(self, next:'Sequence'):
        self.next = next

    def canStart(self) -> tuple:
        return (1, 1)

    def announce(self, pref='>'):
        sec = sum([s.sec for s in self.steps])
        vals = [s.val for s in self.steps]
        print('%s %8s' % (pref, self.base.tStr(sec)), *vals, '     ') 
        return sec

    def gen(self):
        pass

    def connect(self):
        last = len(self.steps) - 1
        for n, s in enumerate(self.steps):
            if n < last:
                s.next = self.steps[n+1].val
            else:
                s.next = self.next.getFirstVal(s.val) if self.next else 1

    def run(self):
        self.gen()
        self.announce('>')
        self.connect()
        for s in self.steps:
            self.runStep(s)

    def preview(self):
        self.gen()
        sec = self.announce('>')
        self.connect()
        for s in self.steps:
            self.stepOut(s, s.sec, True)
            print()
        return sec

    def runStep(self, step:Step):
        beeped = False
        dt = step.sec
        self.stepOut(step, dt)
        self.base.moveNext(step.sec)
        self.base.beepStart()
        while dt > 0:
            if dt < 16 and not beeped:
                if step.next > step.val:
                    self.base.beepUp()
                elif step.next < step.val:
                    self.base.beepDown()
                beeped = True
            self.stepOut(step, dt, beeped)    
            self.base.sleep(0.2)
            dt = self.base.next - self.base.now()
        self.base.count(step)
        self.stepOut(step, step.sec, False)
        print()
    
    def getFirstVal(self, lastVal:int)-> int:
        return 1
    
    def stepOut(self, step:Step, sec:int, nx:bool=False):
        if sec < 0: return
        nstr = ''
        if nx: nstr = '-> %d' % step.next
        print(f'{step.val:4d} {self.base.tStr(sec)} {nstr}{' ':20s}', end = '\r')


class SeqTime(Sequence):
    def __init__(self, base:Base, mins, *args):
        super().__init__(base)
        self.steps.clear()
        # $1 val int
        # $2 min float
        mins = float(mins)
        rx = re.compile(r'^(\d+)(?::(\d*(?:\.\d+)?))?$')
        for n in args:
            m = rx.match(n)
            if m:
                cval, cmin = m.groups()
                val = int(cval)
                min = float(cmin) if cmin and cmin != '.' else mins
                sec = int(min * 60)
                self.steps.append(Step(val, sec))    

    def canStart(self) -> tuple:
        if self.steps:
            val = self.steps[0].val
            return (val, val)
        return super().canStart()
    
    def getFirstVal(self, lastVal:int)-> int:
        if self.steps:
            return self.steps[0].val
        return super().getFirstVal(lastVal)

class SeqRand(Sequence):
    def __init__(self, base:Base, maxv, dur, num, minv=0, ffak=1, fav=-1):
        super().__init__(base)
        maxv = int(maxv)
        minv = int(minv)
        fav = int(fav)
        num = max(5, int(num))
        vals = list(range(maxv + 1))
        self.vals = vals[minv:]
        fav = fav if fav in self.vals else maxv
        ffak = max(0.2, float(ffak))
        ratio = (1 / ffak) ** (1 / max(fav, maxv - fav))
        self.tfaks = [ ratio ** abs(fav - v) for v in vals]

        self.dur = float(dur)
        self.sec = int(self.dur * 60)
        self.num = int(num)
        self.maxv = maxv
        self.minv = minv
        self.fav = fav
        self.xav = max(1, num / (maxv + 1 - minv))
        self.iav = int(self.xav)
        self.firstVal = self.minv
        self.lowest = 1 / 3

    def follows(self, v1, v2):
        return v1 != v2 and abs(v1 - v2) < 3

    def nval(self, val, minv):
        tmin = max(minv, val - 2)
        tmax = min(self.maxv, val + 2) + 1
        sel = [v for v in range(tmin, tmax) if v != val]
        return random.choice(sel)

    def vol(self, a:list) -> float:
        if not a: return 0
        c = list()
        for v in self.vals:
            if v != self.fav and v in a:
                c.append(a.count(v))
        if not c: return 0    
        return a.count(self.fav) * len(c) * min(c) / max(c)

    def canStart(self) -> tuple:
        return (self.minv, self.maxv)

    def getFirstVal(self, lastVal:int)-> int:
        self.firstVal = self.nval(lastVal, min(self.minv, max(0, lastVal -1)))
        return self.firstVal

    def rndList(self, val):
        v = val
        l = [v]
        while len(l) < self.num:
            if v < self.minv:
                v += random.choice([1, 2])
            else:
                v = self.nval(v, self.minv)
            l.append(v)
        return l

    def gen(self):
        res = []
        nfd = 0
        lastv = 1
        if self.next:
            vmin, vmax = self.next.canStart()
            if vmin != vmax:
                lastv = random.randint(vmin, min(vmax, self.maxv))
            else:
                lastv = self.nval(vmin, self.minv)
  
        while True:
            ok = False
            l1 = self.rndList(self.firstVal)
            l2 = self.rndList(lastv)
            l2.reverse()
            src = l1
            last = None
            tmp = []
            for p in range(self.num):
                if not ok:
                    if (last is not None) and self.follows(last, l2[p]):
                        src = l2
                        ok = True
                    else:
                        last = l1[p]
                tmp.append(src[p])

            if ok and self.fav in tmp and self.maxv in tmp:
                nfd += 1
                if self.vol(tmp) > self.vol(res):
                    res = tmp.copy()
            if res and nfd > 4:
                # print('vol: %0.1f' % self.vol(res))
                break
        
        ts = [random.uniform(1, 2) for n in range(self.num)]
        fk =  max(1.0, self.xav / res.count(self.fav))
        for n, v in enumerate(res):
            if v == self.fav:
                ts[n] *= fk
            else:
                ts[n] = max(self.lowest, ts[n] * self.tfaks[v])

        fk = self.dur / sum(ts)
        ts = [t * fk for t in ts]
        tx = min(ts[0], 1.0)
        ts[0] = tx
        ts[-1] = tx
        ts = [int(t * 60) for t in ts]

        self.steps = [ Step(*v) for v in zip(res, ts)]
        df = self.sec - sum([s.sec for s in self.steps])
        self.steps[int(self.num / 2)].sec += df

    def announce(self, pref='>'):
        print('%s %8s %s' % (pref, self.base.tStr(self.sec), f'rnd {self.minv} .. {self.maxv}')) 
        return self.sec

class Runtime(Base):
    def __init__(self):
        super().__init__()
        self.pLoop = None
        self.back = None
        self.seqs = list()
        self.preview = False
        self.info = False
        self.lo = False
        self.fs = 0
        self.mins = 1.0
        self.pStart = 0

    def addF(self, fp):
        self.fs += 1
        with open(fp, 'r') as fh:
            for line in fh:
                if not (line.startswith('#') or re.match(r'^\s*$', line)): 
                    self.add(line.split())
        self.fs -= 1

    def add(self, args):
        opts, args = getopt(args, 'SPIB:Llrt:')
        if (args and isfile(args[0])):
            self.addF(args[0])
            args.clear()

        if opts:
            for o, v in opts:
                # stats only
                if (o == '-S'):
                    self.dumpStats()
                    exit()
                # preview only
                elif (o == '-P'):
                    self.preview = True
                # info only
                elif (o == '-I'):
                    self.info = True
                # loop only
                elif (o == '-L'):
                    self.lo = True
                # backward loop
                elif (o == '-B'):
                    self.back = int(v)
                # loop announcement
                elif (o == '-l'):
                    if self.pLoop is None and self.fs < 2:
                        self.pLoop = len(self.seqs)
                elif (o == '-r'):
                    self.seqs.append(SeqRand(self, *args))
                    args.clear()
                elif (o == '-t'):
                    self.mins = float(v)

        if args:
            self.seqs.append(SeqTime(self, self.mins, *args))

    def connect(self) -> bool:
        if not self.seqs:
            return False
        last = len(self.seqs) - 1
        if self.back:
            self.pStart = max(0, len(self.seqs) - self.back)
        elif self.pLoop is None:
            self.pLoop = last
        for n, seq in enumerate(self.seqs):
            if n < last:
                seq.setNext(self.seqs[n+1])
            else:
                seq.setNext(self.seqs[self.pLoop])
        return True
    
    def run(self):
        self.add(argv[1:])
        if not self.connect():
            return
        rangePre = [] if self.lo else list(range(self.pStart,self.pLoop))
        if self.pStart > self.pLoop:
            rangePre = list(range(self.pStart, len(self.seqs)))
        if self.preview:
            for p in rangePre:
                self.seqs[p].preview()
            for seq in self.seqs[self.pLoop:]:
                seq.preview()
        elif self.info:
            secp = 0
            secl = 0
            if rangePre:
                print('pre:')
                for p in rangePre:
                    secp += self.seqs[p].announce()
                print(self.tStr(secp))
            print('loop:')
            for seq in self.seqs[self.pLoop:]:
                secl += seq.announce()
            print(self.tStr(secl))
            if rangePre:
                print('total:')
                print(self.tStr(secp + secl))
        else:
            for p in rangePre:
                self.seqs[p].run()
            while True:
                for seq in self.seqs[self.pLoop:]:
                    seq.run()

if __name__ == '__main__':
    rt = Runtime()
    rt.run()
    # base = Base()
    # seq1 = SeqRand(base, *'4 20 11 1 2.5'.split())
    # seq2 = SeqTime(base, *'2.5 3:1.5 4 5'.split())
    # seq3 = SeqRand(base, *'5 20 11 2 2.5'.split())
    # seq1.setNext(seq2)
    # seq2.setNext(seq3)
    # seq3.setNext(seq1)
    # seq1.preview()
    # seq2.preview()
    # seq3.preview()
    # seq1.preview()
