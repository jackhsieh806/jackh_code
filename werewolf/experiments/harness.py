"""好人策略實驗：狼人照原本的打法，只改好人陣營。

在 repo 根目錄執行：python3 werewolf/experiments/harness.py 9 600
（9 = 板子編號，見 roles.PRESETS；600 = 每種打法跑幾局，先用 30 試跑比較快）
"""
import random
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))   # repo 根目錄
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))      # 本資料夾（harness）
from werewolf.engine import Game, deal, Rules
from werewolf.roles import PRESETS, Team, Role
from werewolf.bots import BotController
from werewolf.personality import PERSONALITIES

CARDS = (Role.SEER, Role.LANTERN_SEER)


class GoodBot(BotController):
    """好人電腦，可以開關幾種打法。"""
    def __init__(self, strat, personality=None):
        super().__init__(personality)
        self.s = strat

    def _claimants(self, game):
        return [c for c, cl in game.claims.items() if cl["role"] in CARDS and game.players[c].alive]

    def _doubtful_claimant(self, game, me, k):
        """我最不相信的跳預言家者（不在我認為的真預言家裡）。"""
        cands = [c for c in self._claimants(game) if c != me.seat and c not in k.protected
                 and c not in k.good]
        if not cands:
            return None
        score = self.suspicion(game, me, k)
        return max(cands, key=lambda c: score.get(c, 0))

    def knight_duel(self, game, me):
        if "duel" in self.s:
            k = self.analyze(game, me)
            certain = [s for s in k.wolf if game.players[s].alive and s != me.seat]
            if certain:
                return certain[0]
            t = self._doubtful_claimant(game, me, k)
            if t is not None:
                return t
        return super().knight_duel(game, me)

    def witch_action(self, game, me, victim):
        action, t = super().witch_action(game, me, victim)
        if action is None and "poison" in self.s and game.poison and game.night_no >= 2:
            k = self.analyze(game, me)
            t = self._doubtful_claimant(game, me, k)
            if t is not None:
                return "poison", t
        return action, t

    def choose_guard(self, game, me):
        if "guard" in self.s:
            k = self.analyze(game, me)
            opts = [s for s in k.protected if game.players[s].alive and s != game.last_guard]
            if opts:
                return self.rng.choice(opts)
        return super().choose_guard(game, me)

    def suspicion(self, game, me, k):
        score = super().suspicion(game, me, k)
        if "focus" in self.s:            # 集中票推「不在我認為的真預言家組合裡」的跳預言家者
            for c in self._claimants(game):
                if c in score and c not in k.protected and c not in k.good and c != me.seat:
                    score[c] += 25
        return score


def run(board, strat=(), n=600, good_personality=None, smart=2, race=True, seed0=0):
    roles = PRESETS[board][1]
    good = 0
    for i in range(seed0, seed0 + n):
        seats = deal(roles, random.Random(i))
        ctrls = {}
        for s, r in enumerate(seats, 1):
            if r.team is Team.GOOD and r is not Role.WILD_CHILD:
                ctrls[s] = GoodBot(set(strat), PERSONALITIES[good_personality] if good_personality else None)
        g = Game(seats, ctrls, seed=i, out=lambda _: None,
                 rules=Rules(smart_bots=smart, lantern_claim_race=race))
        good += g.play() is Team.GOOD
    return good / n


if __name__ == "__main__":
    board = sys.argv[1] if len(sys.argv) > 1 else "9"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 600     # 每種打法跑幾局
    trials = [
        ("基準（現在的打法）", (), None, 2),
        ("推理高手 0 位", (), None, 0),
        ("推理高手 4 位", (), None, 4),
        ("好人全員邏輯型", (), "logical", 0),
        ("騎士決鬥對跳的人", ("duel",), None, 2),
        ("女巫毒對跳的人", ("poison",), None, 2),
        ("守衛守真預言家", ("guard",), None, 2),
        ("集中票推對跳", ("focus",), None, 2),
    ]
    for name, strat, pers, smart in trials:
        print(f"{name:14} 好人勝率 {run(board, strat, n=n, good_personality=pers, smart=smart):.0%}", flush=True)
