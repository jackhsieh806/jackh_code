import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))   # repo 根目錄
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))      # 本資料夾（harness）
import harness
from harness import GoodBot, run

orig = GoodBot.knight_duel
def late_duel(self, game, me):          # 第二天以後才決鬥
    if game.night_no < 2:
        return None
    return orig(self, game, me)

trials = [
    ("騎士第1天決鬥", ("duel",)),
    ("騎士決鬥＋守衛守真預言家", ("duel", "guard")),
    ("騎士決鬥＋集中票推", ("duel", "focus")),
    ("騎士決鬥＋守衛＋集中票推", ("duel", "guard", "focus")),
]
for name, strat in trials:
    print(f"{name:18} 好人勝率 {run('9', strat):.0%}", flush=True)
GoodBot.knight_duel = late_duel
print(f"{'騎士第2天才決鬥':18} 好人勝率 {run('9', ('duel',)):.0%}", flush=True)
GoodBot.knight_duel = orig
print(f"{'各報各的牌＋騎士決鬥':18} 好人勝率 {run('9', ('duel',), race=False):.0%}（基準 {run('9', (), race=False):.0%}）", flush=True)
