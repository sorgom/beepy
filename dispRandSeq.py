#   ============================================================
#   display random sequences
#   ============================================================
from beep import RandSeq
from sys import argv

def display(rs:RandSeq):
    dsp = [ [ ' ' for x in range(rs.num) ] for y in range(rs.maxv + 1) ]
    seq = rs.gen()
    for x, s in enumerate(seq):
        for y in range(s.val + 1):
            dsp[y][x] = '#'

    dsp[0] = ['-' for x in range(rs.num) ]        
    dsp.reverse()
    for row in dsp: print(*row)

rs = RandSeq(*argv[1:])
display(rs)
