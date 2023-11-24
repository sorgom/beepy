#   ============================================================
#   beep device
#   ============================================================
import winsound

class Beeper(object):
    def __init__(self):
        self.freq = {
            'C': 523,
            'D': 587,
            'E': 659,
            'F': 698,
            'G': 740,
            'A': 880,
            'H': 988,
            'c': 1047
        }
    def play(self, mel:str, ms=200):
        # return
        for c in mel:
            fr = self.freq.get(c)
            if fr:
                winsound.Beep(fr, int(ms))

if __name__ == '__main__':
    from sys import argv
    if len(argv) > 1:
        Beeper().play(*argv[1:])
