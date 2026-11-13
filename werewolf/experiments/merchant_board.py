import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))   # repo 根目錄
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))      # 本資料夾（harness）
from harness import GoodBot, run
from werewolf.roles import Role

base_trade = GoodBot.merchant_trade
def trade_to_claimed_seer(self, game, me):      # 商人第二晚把「守護」交給相信的預言家
    if game.night_no == 1:
        return None
    k = self.analyze(game, me)
    if k.trusted is not None and game.players[k.trusted].alive:
        self.traded = (k.trusted, "guard")
        return k.trusted, "guard"
    return base_trade(self, game, me)
def trade_check_night1(self, game, me):         # 商人第一晚一定交易查驗
    opts = [s for s in game.alive_seats() if s != me.seat]
    t = min(opts, key=lambda s: self.pref[s])
    self.traded = (t, "check")
    return t, "check"

trials = [("基準（現在的打法）", (), None, 2), ("推理高手 4 位", (), None, 4), ("好人全員邏輯型", (), "logical", 0),
          ("女巫毒對跳的人", ("poison",), None, 2), ("集中票推對跳", ("focus",), None, 2)]
for name, strat, pers, smart in trials:
    print(f"{name:16} 好人勝率 {run('6', strat, good_personality=pers, smart=smart):.0%}", flush=True)
GoodBot.merchant_trade = trade_check_night1
print(f"{'商人首夜必給查驗':16} 好人勝率 {run('6'):.0%}", flush=True)
GoodBot.merchant_trade = trade_to_claimed_seer
print(f"{'商人把守護交給預言家':16} 好人勝率 {run('6'):.0%}", flush=True)
GoodBot.merchant_trade = base_trade
