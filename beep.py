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
#   -l loop from here
#   -r random object maxv, dur, num


class Step(object):
    def __init__(self, val:int, min:float):
        self.val = val
        self.sec = int(min * 60)
        self.next = -1

class RandSeq(object):
    def __init__(self, maxv, dur, num):
        random.seed()
        self.num = max(5, int(num))
        self.dur = float(dur)
        self.sec = int(self.dur * 60)
        self.maxv = int(maxv)
        self.next = 0
        self.val = min(2, self.maxv)
        self.vals = list()
        for n in range(self.maxv + 1):
            for t in range(n + 1):
                self.vals.append(n)

    def rndList(self):
        v = self.val
        l = [v]
        while len(l) < self.num:
            nx = random.choice(self.vals)
            if nx != v and abs(nx - v) < 4:
                v = nx
                l.append(v)
        return l

    def gen(self):
        res = []
        while not res:
            ok = False
            l1 = self.rndList()
            l2 = self.rndList()
            l2.reverse()
            src = l1
            for p in range(self.num):
                if l2[p] == l1[p]:
                    src = l2
                    ok = True
                res.append(src[p])

            ok = ok and self.maxv in res
            if not ok: res.clear()
        
        ts = [random.uniform(1, 2) for n in range(self.num)]
        fk = self.dur / sum(ts)
        ts = [t * fk for t in ts]
        seq = [ Step(*v) for v in zip(res, ts)]
        df = self.sec - sum([s.sec for s in seq])
        s = seq[-1]
        s.sec += df
        s.next = self.next
        s.val = min(3, self.maxv)
        if s.val == seq[-2].val and s.val < self.maxv:
            s.val += 1
        for p in range(self.num - 1):
            seq[p].next = seq[p + 1].val
        return seq

class Beep(object):
    def __init__(self):
        self.exit = Event()
        self.beeper = Beeper()
        for sig in ('TERM', 'INT'):
            signal.signal(getattr(signal, 'SIG' + sig), self.quit)
        self.rxF = re.compile(r'^\d+(?:\.\d*?)?$')
        self.rxI = re.compile(r'^\d+$')
        self.rxX = re.compile(r'^(\d+):(\d+(?:\.\d*)?)', re.M)
        self.once = list()
        self.loop = list()
        self.inp  = self.once
        self.pause = 1.0
        self.next = self.now()
        self.mode = 's'
        self.dur  = 1.0
        self.stats = list()
        self.info = False
        self.preview = False

    def sleep(self, sec:float=1):
        for n in range(int(sec * 100)):
            self.exit.wait(0.01)

    def quit(self, *args):
        self.exit.set()
        if self.statsAdded():
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
        opts, args = getopt(args, 'ilp:rst:xSP')
        for o, v in opts:
            if (o == '-p'):
                self.pause = v
            elif (o == '-l'):
                self.inp = self.loop
            elif (o == '-t'):
                self.mode = 'x'
                self.dur = float(v)
            elif (o == '-i'):
                self.info = True
            elif (o == '-r'):
                self.inp.append([RandSeq(*args)])
                return
            elif (o == '-S'):
                self.dumpStats()
                exit()
            elif (o == '-P'):
                self.preview = True
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
        s0 = seq[0]
        if type(s0) == RandSeq:
            self.runSeq(s0.gen(), False)
        else:
            for step in seq: self.runStep(step)

    def runStep(self, step:Step):
        if self.preview:
            self.stepOut(step, step.sec, True)
            print()
            return
        self.next += step.sec
        beeped = False
        dt = step.sec
        self.stepOut(step, dt)
        self.beeper.play('c', 400)
        while dt > 0:
            if (dt <= 16 and not beeped):
                if step.next > step.val:
                    self.beeper.play('DG', 200)
                elif step.next < step.val:
                    self.beeper.play('FD', 200)
                beeped = True
            self.stepOut(step, dt, beeped)
            self.sleep(0.2)
            dt = self.next - self.now()
        self.stats[step.val] += step.sec
        self.stepOut(step, step.sec, False)
        print()

    def stepOut(self, step:Step, sec:int, nx:bool=False):
        if sec < 0: return
        nstr = ''
        if nx: nstr = '-> %d' % step.next
        print("%4d %s %-20s" % (step.val, self.tStr(sec), nstr), end = '\r')

    def seqOut(self, seq:list, pref='>'):
        sec = 0
        vals = []
        s0 = seq[0]
        if type(s0) == RandSeq:
            vals = ['rnd', s0.maxv]
            sec = s0.sec
        else:
            sec = sum([s.sec for s in seq])
            vals = [s.val for s in seq]
        print('%s %8s' % (pref, self.tStr(sec)), *vals, '     ')
        return sec

    def tStr(self, sec):
        min = int(sec / 60)
        hrs = int(min / 60)
        min = min % 60
        sec = sec % 60
        if hrs > 0:
            return '%d:%02d:%02d' % (hrs, min, sec)
        return '%2d:%02d' % (min, sec)

    def maxVal(self, seq):
        s0 = seq[0]
        if type(s0) == RandSeq:
            return s0.maxv
        else:
            return max([s.val for s in seq])

    def allOut(self, show=True):
        ma = 0
        sec = 0
        for seq in [*self.once, *self.loop]:
            ma = max(ma, self.maxVal(seq))
            sec += sum([s.sec for s in seq])
        if show:
            print('< %8s mx %d >' % (self.tStr(sec), ma))
        return ma

    def statsAdded(self):
        return self.stats.count(0) < len(self.stats)

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

        print('tt:%5d:%02d' % (int(tmin / 60), tmin % 60))
        if self.statsAdded():
            with open(file, 'w') as fh:
                fh.write(' '.join([str(n) for n in c]))

    def outPart(self, part, name):
        if not part: return
        print(name)
        sec = 0
        for seq in part:
            sec += self.seqOut(seq, ' ')
        if len(part) > 1:
            print('  %8s' % self.tStr(sec) )

    def outInfo(self):
        self.outPart(self.once, 'once')
        self.outPart(self.loop, 'loop')
        exit()

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
        if self.info:
            self.outInfo()

        self.stats = [0 for n in range(ma + 1)]
        if l1 == 1:
            self.seqOut(self.once[0])
        for seq in self.once: self.runSeq(seq, l1 > 1)
        if l2 == 1:
            self.seqOut(self.loop[0])
        while l2 > 0:
            for seq in self.loop: self.runSeq(seq, l2 > 1)
            if self.preview: break

if __name__ == '__main__':
    Beep().run(argv[1:])
