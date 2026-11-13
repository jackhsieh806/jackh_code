import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))   # repo 根目錄
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))      # 本資料夾（harness）
import random
from harness import GoodBot
from werewolf.engine import Game, deal, Rules
from werewolf.roles import PRESETS, Team, Role
roles = PRESETS["9"][1]
out = {"成功（決鬥到狼）": [0, 0], "失敗（決鬥到真預言家）": [0, 0], "沒有決鬥（騎士先死等）": [0, 0]}
pair = {"成功（決鬥到狼）": [0, 0], "失敗（決鬥到真預言家）": [0, 0], "沒有決鬥（騎士先死等）": [0, 0]}
for i in range(800):
    seats = deal(roles, random.Random(i))
    ctrls = {s: GoodBot({"duel", "guard"}) for s, r in enumerate(seats, 1) if r.team is Team.GOOD}
    g = Game(seats, ctrls, seed=i, out=lambda _: None, rules=Rules(lantern_claim_race=True))
    res = [None]
    orig = g._try_duel
    def tracked(knight, g=g, orig=orig):
        r = orig(knight)
        if r is not None and res[0] is None:
            res[0] = r
        return r
    g._try_duel = tracked
    orig_dawn = g.run_dawn
    def dawn(rec, g=g, orig_dawn=orig_dawn):
        w = orig_dawn(rec)
        if g.night_no == 3:    # 第三天：好人有沒有找對真預言家
            real = {p.seat for p in g.players.values() if p.role in (Role.SEER, Role.LANTERN_SEER)}
            for p in g.alive():
                if p.is_wolf or p.seat in real: continue
                k = g.controllers[p.seat].analyze(g, p)
                if len(k.protected) == 2:
                    g._pair = getattr(g, "_pair", []) + [k.protected == real]
        return w
    g.run_dawn = dawn
    w = g.play()
    key = "成功（決鬥到狼）" if res[0] is True else "失敗（決鬥到真預言家）" if res[0] is False else "沒有決鬥（騎士先死等）"
    out[key][0] += 1; out[key][1] += w is Team.GOOD
    for ok in getattr(g, "_pair", []):
        pair[key][0] += 1; pair[key][1] += ok
for k, (n, w) in out.items():
    pn, pk = pair[k]
    print(f"{k:14} {n/8:4.0f}% 的局  好人勝率 {w/max(n,1):.0%}  第三天好人找對真預言家 {pk/max(pn,1):.0%}")
