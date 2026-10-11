import random
import unittest

from werewolf.bots import BotController
from werewolf.engine import DayRecord, Game, Rules, Speech, deal
from werewolf.roles import PRESETS, Role, Team


class Scripted(BotController):
    """可以覆寫特定決策的電腦玩家，方便寫測試。"""

    def __init__(self, **overrides):
        super().__init__()
        for name, fn in overrides.items():
            setattr(self, name, fn)


def quiet_game(roles, controllers=None, rules=None, seed=0):
    return Game(roles, controllers or {}, rules=rules, seed=seed, out=lambda _: None)


W, S, WI, H, G, I, V = (Role.WEREWOLF, Role.SEER, Role.WITCH, Role.HUNTER,
                       Role.GUARD, Role.IDIOT, Role.VILLAGER)
# 座位：1-3 狼、4 預言家、5 女巫、6 獵人、7 守衛、8 白痴、9-10 平民
BOARD = [W, W, W, S, WI, H, G, I, V, V]


def never(*_):
    raise AssertionError("不該被呼叫")


class ResolveNightTest(unittest.TestCase):
    def test_plain_kill(self):
        self.assertEqual(Game.resolve_night(5, None, False, None), {5: "wolf"})

    def test_guard_blocks(self):
        self.assertEqual(Game.resolve_night(5, 5, False, None), {})

    def test_save_blocks(self):
        self.assertEqual(Game.resolve_night(5, None, True, None), {})

    def test_same_guard_and_save_dies(self):
        self.assertEqual(Game.resolve_night(5, 5, True, None), {5: "wolf"})
        self.assertEqual(Game.resolve_night(5, 5, True, None, same_guard_save_dies=False), {})

    def test_guard_cannot_stop_poison(self):
        self.assertEqual(Game.resolve_night(None, 3, False, 3), {3: "poison"})

    def test_empty_kill(self):
        self.assertEqual(Game.resolve_night(None, None, False, None), {})


class WinConditionTest(unittest.TestCase):
    def test_all_wolves_dead(self):
        g = quiet_game(BOARD)
        for s in (1, 2, 3):
            g.players[s].alive = False
        self.assertIs(g.check_winner(), Team.GOOD)

    def test_side_kill_villagers(self):
        g = quiet_game(BOARD)
        for s in (9, 10):
            g.players[s].alive = False
        self.assertIs(g.check_winner(), Team.WOLF)

    def test_side_kill_gods(self):
        g = quiet_game(BOARD)
        for s in (4, 5, 6, 7, 8):
            g.players[s].alive = False
        self.assertIs(g.check_winner(), Team.WOLF)
        g.rules.win_mode = "all"
        self.assertIsNone(g.check_winner())

    def test_game_continues(self):
        self.assertIsNone(quiet_game(BOARD).check_winner())


class NightFlowTest(unittest.TestCase):
    def test_poisoned_hunter_cannot_shoot(self):
        ctrls = {1: Scripted(choose_kill=lambda g, m: 9),
                 5: Scripted(witch_action=lambda g, m, v: ("poison", 6)),
                 6: Scripted(hunter_shoot=never)}
        g = quiet_game(BOARD, ctrls)
        g.setup()
        rec = g.run_night()
        self.assertEqual(rec.deaths, {9: "wolf", 6: "poison"})
        g.run_dawn(rec)
        self.assertEqual(len(g.alive()), 8)

    def test_hunter_killed_by_wolves_shoots(self):
        ctrls = {1: Scripted(choose_kill=lambda g, m: 6),
                 5: Scripted(witch_action=lambda g, m, v: (None, None)),
                 7: Scripted(choose_guard=lambda g, m: None),
                 6: Scripted(hunter_shoot=lambda g, m: 2)}
        g = quiet_game(BOARD, ctrls)
        g.setup()
        g.run_dawn(g.run_night())
        self.assertFalse(g.players[2].alive)
        self.assertEqual(g.players[2].death_cause, "shot")
        self.assertTrue(g.players[6].revealed)

    def test_witch_cannot_use_both_potions(self):
        ctrls = {1: Scripted(choose_kill=lambda g, m: 9),
                 5: Scripted(witch_action=lambda g, m, v: ("save", None)),
                 7: Scripted(choose_guard=lambda g, m: None)}
        g = quiet_game(BOARD, ctrls)
        g.setup()
        rec = g.run_night()
        self.assertTrue(rec.saved)
        self.assertEqual(rec.deaths, {})
        self.assertFalse(g.antidote)
        self.assertTrue(g.poison)

    def test_witch_self_save_rules(self):
        g = quiet_game(BOARD, rules=Rules(witch_self_save="first_night"))
        witch = g.players[5]
        g.night_no = 1
        self.assertTrue(g.can_witch_save(witch, 5))
        g.night_no = 2
        self.assertFalse(g.can_witch_save(witch, 5))
        self.assertTrue(g.can_witch_save(witch, 9))
        g.rules.witch_self_save = "never"
        g.night_no = 1
        self.assertFalse(g.can_witch_save(witch, 5))

    def test_guard_cannot_repeat(self):
        ctrls = {7: Scripted(choose_guard=lambda g, m: 9),
                 1: Scripted(choose_kill=lambda g, m: 9),
                 5: Scripted(witch_action=lambda g, m, v: (None, None))}
        g = quiet_game(BOARD, ctrls)
        g.setup()
        g.last_guard = 9          # 前一晚已經守 9 號
        rec = g.run_night()
        self.assertIsNone(rec.guard)
        self.assertEqual(rec.deaths, {9: "wolf"})

    def test_seer_gets_correct_result(self):
        ctrls = {4: Scripted(choose_check=lambda g, m: 2)}
        g = quiet_game(BOARD, ctrls)
        g.setup()
        rec = g.run_night()
        self.assertEqual(rec.check, (2, True))
        self.assertEqual(ctrls[4].checks, {2: True})


class DayFlowTest(unittest.TestCase):
    def _day_game(self, vote_target):
        ctrls = {s: Scripted(vote=lambda g, m, c: vote_target if m.seat != vote_target else 1,
                             choose_kill=lambda g, m: None,
                             witch_action=lambda g, m, v: (None, None))
                 for s in range(1, 11)}
        g = quiet_game(BOARD, ctrls)
        g.setup()
        g.run_dawn(g.run_night())
        return g

    def test_idiot_survives_vote_once(self):
        g = self._day_game(8)
        g.run_day()
        idiot = g.players[8]
        self.assertTrue(idiot.alive and idiot.revealed)
        self.assertFalse(idiot.can_vote)
        g.days.append(DayRecord(2))
        g.run_day()
        self.assertFalse(idiot.alive)

    def test_exile(self):
        g = self._day_game(1)
        g.run_day()
        self.assertEqual(g.today.exiled, 1)
        self.assertEqual(g.players[1].death_cause, "vote")

    def test_tie_then_no_exile(self):
        g = quiet_game(BOARD)
        g.days.append(DayRecord(1))
        votes = {s: (1 if s % 2 else 2) for s in range(3, 11)}
        for s, t in votes.items():
            g.controllers[s] = Scripted(vote=lambda g_, m, c, t=t: t if t in c else None)
        g.controllers[1] = Scripted(vote=lambda *_: None)
        g.controllers[2] = Scripted(vote=lambda *_: None)
        self.assertIsNone(g._vote_phase())


class ClaimsTest(unittest.TestCase):
    def test_seer_claim_checks_accumulate(self):
        g = quiet_game(BOARD)
        g.days.append(DayRecord(1))
        g._register_speech(Speech(4, Role.SEER, {2: True}))
        g._register_speech(Speech(4, Role.SEER, {9: False}))
        self.assertEqual(g.seer_claims(), {4: {2: True, 9: False}})

    def test_good_bot_catches_liar(self):
        """有人說我是狼，但我是好人 → 他是假預言家。"""
        g = quiet_game(BOARD)
        g.setup()
        g.days.append(DayRecord(1))
        g._register_speech(Speech(1, Role.SEER, {9: True}))
        g._register_speech(Speech(4, Role.SEER, {1: True}))
        k = g.controllers[9].analyze(g, g.players[9])
        self.assertIn(1, k.wolf)
        self.assertEqual(k.trusted, 4)


WK, AWK, D, M = Role.WOLF_KING, Role.AWAKENED_WOLF_KING, Role.DREAMER, Role.MERCHANT
# 座位：1 狼王、2 覺醒狼王、3 狼、4 預言家、5 女巫、6 獵人、7 攝夢人、8 奇蹟商人、9-10 平民
NEW_BOARD = [WK, AWK, W, S, WI, H, D, M, V, V]


def idle(**extra):
    base = dict(choose_kill=lambda g, m: None, witch_action=lambda g, m, v: (None, None),
                choose_dream=lambda g, m: None, merchant_trade=lambda g, m: None,
                pass_claw=lambda g, m: None, choose_check=lambda g, m: None)
    base.update(extra)
    return base


class DreamResolveTest(unittest.TestCase):
    def test_dream_blocks_kill_and_poison(self):
        self.assertEqual(Game.resolve_night(5, None, False, None, dream=5), {})
        self.assertEqual(Game.resolve_night(None, None, False, 5, dream=5), {})

    def test_dream_twice_dies(self):
        self.assertEqual(Game.resolve_night(None, None, False, None, dream=5, dream_repeat=True),
                         {5: "dream"})

    def test_dreamer_death_takes_sleeper(self):
        self.assertEqual(Game.resolve_night(7, None, False, None, dream=5, dreamer=7),
                         {7: "wolf", 5: "dream"})

    def test_lucky_guard_and_poison(self):
        self.assertEqual(Game.resolve_night(5, None, False, None, extra_guard=5), {})
        self.assertEqual(Game.resolve_night(None, None, False, None, extra_poison=3), {3: "poison"})


class NewRolesFlowTest(unittest.TestCase):
    def game(self, ctrls):
        g = quiet_game(NEW_BOARD, ctrls)
        g.setup()
        return g

    def test_merchant_trades_with_wolf_dies(self):
        g = self.game({s: Scripted(**idle()) for s in range(1, 11)} |
                      {8: Scripted(**idle(merchant_trade=lambda g, m: (3, "check")))})
        rec = g.run_night()
        self.assertEqual(rec.deaths, {8: "trade"})
        self.assertIsNone(g.lucky)

    def test_lucky_checks_same_night(self):
        lucky = Scripted(**idle(lucky_action=lambda g, m, item: 2))
        g = self.game({s: Scripted(**idle()) for s in range(1, 11)} |
                      {8: Scripted(**idle(merchant_trade=lambda g, m: (9, "check"))), 9: lucky})
        g.run_night()
        self.assertEqual(lucky.checks, {2: True})
        self.assertTrue(g.lucky["used"])

    def test_lucky_poison_ignores_guard_but_not_dream(self):
        g = self.game({s: Scripted(**idle()) for s in range(1, 11)} |
                      {8: Scripted(**idle(merchant_trade=lambda g, m: (9, "poison"))),
                       9: Scripted(**idle(lucky_action=lambda g, m, item: 3)),
                       7: Scripted(**idle(choose_dream=lambda g, m: 4))})
        rec = g.run_night()
        self.assertEqual(rec.deaths, {3: "poison"})

    def test_wolf_king_claws_when_exiled(self):
        ctrls = {s: Scripted(**idle(vote=lambda g, m, c: 1 if m.seat != 1 else 9))
                 for s in range(1, 11)}
        ctrls[1] = Scripted(**idle(vote=lambda g, m, c: 9, hunter_shoot=lambda g, m: 4))
        g = self.game(ctrls)
        g.run_dawn(g.run_night())
        g.run_day()
        self.assertEqual(g.players[4].death_cause, "claw")
        self.assertTrue(g.players[1].revealed)

    def test_poisoned_wolf_king_cannot_claw(self):
        ctrls = {s: Scripted(**idle()) for s in range(1, 11)}
        ctrls[5] = Scripted(**idle(witch_action=lambda g, m, v: ("poison", 1)))
        ctrls[1] = Scripted(**idle(hunter_shoot=never))
        g = self.game(ctrls)
        g.run_dawn(g.run_night())
        self.assertEqual(g.players[1].death_cause, "poison")

    def test_dreamed_twice_hunter_cannot_shoot(self):
        ctrls = {s: Scripted(**idle()) for s in range(1, 11)}
        ctrls[7] = Scripted(**idle(choose_dream=lambda g, m: 6))
        ctrls[6] = Scripted(**idle(hunter_shoot=never))
        g = self.game(ctrls)
        g.run_dawn(g.run_night())
        g.days.append(DayRecord(1))
        rec = g.run_night()
        self.assertEqual(rec.deaths, {6: "dream"})
        g.run_dawn(rec)

    def test_awakened_passes_claw(self):
        ctrls = {s: Scripted(**idle()) for s in range(1, 11)}
        ctrls[2] = Scripted(**idle(pass_claw=lambda g, m: 3))
        g = self.game(ctrls)
        g.run_night()
        self.assertEqual(g.claws[2], 1)
        self.assertEqual(g.claws[3], 1)
        g.run_night()                 # 同一隊友不能拿兩次
        self.assertEqual(g.claws[3], 1)
        self.assertEqual(g.claws[2], 1)

    def test_awakened_exiled_takes_two(self):
        targets = iter([4, 5])
        ctrls = {s: Scripted(**idle(vote=lambda g, m, c: 2)) for s in range(1, 11)}
        ctrls[2] = Scripted(**idle(vote=lambda g, m, c: 9, hunter_shoot=lambda g, m: next(targets)))
        g = self.game(ctrls)
        g.run_dawn(g.run_night())
        g.run_day()
        self.assertEqual([g.players[s].death_cause for s in (2, 4, 5)], ["vote", "claw", "claw"])
        self.assertEqual(g.claws[2], 0)

    def test_wolf_kings_count_as_wolves(self):
        g = self.game({})
        self.assertTrue(all(g.players[s].is_wolf for s in (1, 2, 3)))
        for s in (3, 2):
            g.players[s].alive = False
        self.assertIsNone(g.check_winner())
        g.players[1].alive = False
        self.assertIs(g.check_winner(), Team.GOOD)


class SimulationTest(unittest.TestCase):
    def test_many_bot_games_finish(self):
        rng = random.Random(42)
        results = {Team.GOOD: 0, Team.WOLF: 0, None: 0}
        for key, (_, roles) in PRESETS.items():
            for _ in range(150):
                seed = rng.randrange(1 << 30)
                g = Game(deal(roles, random.Random(seed)), seed=seed, out=lambda _: None)
                results[g.play()] += 1
        self.assertGreater(results[Team.GOOD], 0)
        self.assertGreater(results[Team.WOLF], 0)


if __name__ == "__main__":
    unittest.main()
