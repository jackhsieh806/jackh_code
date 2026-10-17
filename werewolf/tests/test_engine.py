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
    """預設關閉警長與自爆，讓舊的流程測試保持確定性。"""
    rules = rules or Rules(sheriff=False, self_explode=False)
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
                pass_claw=lambda g, m: None, choose_check=lambda g, m: None,
                choose_guard=lambda g, m: None)
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


class SheriffTest(unittest.TestCase):
    def election_game(self, running, votes, extra=None):
        extra = extra or {}
        ctrls = {}
        for s in range(1, 11):
            ctrls[s] = Scripted(**idle(run_for_sheriff=lambda g, m: m.seat in running,
                                       sheriff_vote=lambda g, m, c: votes.get(m.seat),
                                       self_explode=lambda g, m: False, **extra.get(s, {})))
        g = quiet_game(BOARD, ctrls, rules=Rules(sheriff=True, self_explode=True))
        g.setup()
        return g

    def test_election_winner(self):
        g = self.election_game({4, 9}, {s: 4 for s in range(1, 11)})
        g.run_dawn(g.run_night())
        self.assertEqual(g.sheriff, 4)

    def test_candidates_cannot_vote(self):
        g = self.election_game({4, 9}, {9: 4, 4: 9, 1: 9, 2: 9, 3: 4, 5: 4, 6: 4})
        g.run_dawn(g.run_night())
        self.assertEqual(g.sheriff, 4)   # 4 號拿 3 票，9 號只拿 2 票（4 號自己的票不算）

    def test_tie_twice_loses_badge(self):
        g = self.election_game({4, 9}, {1: 4, 2: 9})
        g.run_dawn(g.run_night())
        self.assertIsNone(g.sheriff)

    def test_sheriff_vote_counts_one_and_half(self):
        g = quiet_game(BOARD)
        g.sheriff = 4
        g.days.append(DayRecord(1))
        self.assertEqual(g._show_votes({4: 1, 5: 2, 6: 1, 7: 2}), [1])   # 2.5 對 2

    def test_dead_sheriff_passes_badge(self):
        g = self.election_game({4}, {s: 4 for s in range(1, 11)},
                               {1: {"choose_kill": lambda g, m: 4},
                                4: {"pass_badge": lambda g, m: 9}})
        g.run_dawn(g.run_night())   # 4 號第一晚被殺，但已經當選警長
        self.assertFalse(g.players[4].alive)
        self.assertEqual(g.sheriff, 9)

    def test_sheriff_speaks_last(self):
        g = quiet_game(BOARD)
        g.setup()
        g.night_no = 1
        g.sheriff = 5
        g.controllers[5] = Scripted(choose_direction=lambda g, m: "right")
        self.assertEqual(g.speech_order(), [6, 7, 8, 9, 10, 1, 2, 3, 4, 5])
        g.controllers[5] = Scripted(choose_direction=lambda g, m: "left")
        self.assertEqual(g.speech_order(), [4, 3, 2, 1, 10, 9, 8, 7, 6, 5])


class SelfExplodeTest(unittest.TestCase):
    def game(self, board, exploder, extra=None):
        ctrls = {s: Scripted(**idle(run_for_sheriff=lambda g, m: False,
                                    self_explode=lambda g, m: m.seat == exploder,
                                    vote=lambda g, m, c: never())) for s in range(1, 11)}
        for s, ex in (extra or {}).items():
            ctrls[s] = Scripted(**idle(run_for_sheriff=lambda g, m: False,
                                       self_explode=lambda g, m: m.seat == exploder,
                                       vote=lambda g, m, c: never(), **ex))
        g = quiet_game(board, ctrls, rules=Rules(sheriff=False, self_explode=True))
        g.setup()
        g.run_dawn(g.run_night())
        return g

    def test_explode_skips_vote(self):
        g = self.game(BOARD, 1)
        self.assertIsNone(g.run_day())          # vote 被呼叫就會失敗
        self.assertEqual(g.players[1].death_cause, "explode")
        self.assertEqual(g.today.exploded, 1)

    def test_good_player_cannot_explode(self):
        ctrl = Scripted(self_explode=lambda g, m: True)
        g = quiet_game(BOARD, {9: ctrl}, rules=Rules(sheriff=False, self_explode=True))
        g.days.append(DayRecord(1))
        self.assertFalse(g._try_explode(g.players[9]))

    def test_wolf_king_explode_claws(self):
        g = self.game(NEW_BOARD, 1, {1: {"hunter_shoot": lambda g, m: 4}})
        g.run_day()
        self.assertEqual(g.players[4].death_cause, "claw")

    def test_explode_in_election_loses_badge(self):
        ctrls = {s: Scripted(**idle(run_for_sheriff=lambda g, m: m.seat in (1, 4),
                                    self_explode=lambda g, m: m.seat == 1,
                                    sheriff_vote=lambda g, m, c: never())) for s in range(1, 11)}
        g = quiet_game(BOARD, ctrls, rules=Rules(sheriff=True, self_explode=True))
        g.setup()
        g.run_dawn(g.run_night())
        self.assertIsNone(g.sheriff)
        self.assertEqual(g.players[1].death_cause, "explode")
        self.assertIsNone(g.run_day())          # 警上自爆 → 當天直接天黑


WB, TG, WC, KN, VG = (Role.WOLF_BEAUTY, Role.TIGER_GRANDMA, Role.WILD_CHILD, Role.KNIGHT,
                      Role.VILLAGE_GIRL)
# 座位：1 狼美人、2 虎姑婆、3-4 小狼、5 野孩子、6 預言家、7 女巫、8 騎士、9 守衛、10 村姑、11-15 平民
TIGER_BOARD = [WB, TG, W, W, WC, S, WI, KN, G, VG, V, V, V, V, V]


def tiger_game(overrides=None, rules=None):
    ctrls = {s: Scripted(**idle(choose_model=lambda g, m: 11, choose_charm=lambda g, m: None,
                                choose_lure=lambda g, m, c: None, girl_check=lambda g, m, o: None,
                                knight_duel=lambda g, m: None, self_explode=lambda g, m: False))
             for s in range(1, 16)}
    for seat, ex in (overrides or {}).items():
        base = dict(choose_model=lambda g, m: 11, choose_charm=lambda g, m: None,
                    choose_lure=lambda g, m, c: None, girl_check=lambda g, m, o: None,
                    knight_duel=lambda g, m: None, self_explode=lambda g, m: False)
        base.update(ex)
        ctrls[seat] = Scripted(**idle(**base))
    g = quiet_game(TIGER_BOARD, ctrls, rules=rules)
    g.setup()
    return g


class WildChildTest(unittest.TestCase):
    def test_always_checked_good(self):
        g = tiger_game()
        g.players[5].turned = True
        self.assertFalse(g.check_result(5))
        self.assertTrue(g.players[5].is_wolf)

    def test_turns_when_model_dies(self):
        g = tiger_game({1: {"choose_kill": lambda g, m: 11}})
        g.run_night()
        self.assertTrue(g.players[5].turned)
        self.assertIs(g.alignment(g.players[5]), Team.WOLF)

    def test_wolf_model_means_wolf_side_without_knowing(self):
        g = tiger_game({5: {"choose_model": lambda g, m: 3}})
        g.run_night()
        self.assertFalse(g.players[5].turned)
        self.assertIs(g.alignment(g.players[5]), Team.WOLF)

    def test_village_girl_model_stays_good(self):
        g = tiger_game({5: {"choose_model": lambda g, m: 10}, 1: {"choose_kill": lambda g, m: 10}})
        g.run_night()
        self.assertFalse(g.players[10].alive)
        self.assertFalse(g.players[5].turned)
        self.assertIs(g.alignment(g.players[5]), Team.GOOD)

    def test_tiger_model_joins_wolves(self):
        g = tiger_game({5: {"choose_model": lambda g, m: 2}})
        g.run_night()
        self.assertTrue(g.players[5].turned)

    def test_good_wins_without_exiling_turned_child(self):
        g = tiger_game()
        g.players[5].turned = True
        for s in (1, 2, 3, 4):
            g.players[s].alive = False
        self.assertIs(g.check_winner(), Team.GOOD)


class TigerGrandmaTest(unittest.TestCase):
    def test_reflect_priority_girl_before_seer(self):
        g = tiger_game({10: {"girl_check": lambda g, m, o: 2}, 6: {"choose_check": lambda g, m: 2}})
        g.sheriff_votes = {10: 11}
        rec = g.run_night()
        self.assertEqual(rec.deaths, {10: "reflect"})
        self.assertTrue(g.reflect_used)

    def test_reflect_poison_saves_tiger(self):
        g = tiger_game({7: {"witch_action": lambda g, m, v: ("poison", 2)}})
        rec = g.run_night()
        self.assertEqual(rec.deaths, {7: "reflect"})
        self.assertTrue(g.players[2].alive)

    def test_reflect_only_once(self):
        g = tiger_game({6: {"choose_check": lambda g, m: 2}})
        self.assertEqual(g.run_night().deaths, {6: "reflect"})
        g = tiger_game({6: {"choose_check": lambda g, m: 2}})
        g.reflect_used = True
        self.assertEqual(g.run_night().deaths, {})

    def test_lure_limits_checks_and_alternates(self):
        g = tiger_game({2: {"choose_lure": lambda g, m, c: 3},
                        6: {"choose_check": lambda g, m: 8}})
        g.run_night()                                   # 第一晚不能誘導
        self.assertIsNone(g.lure_range)
        rec = g.run_night()
        self.assertEqual(g.lure_range, {2, 3, 4})
        self.assertIsNone(rec.check)                    # 8 號不在範圍內，查驗無效
        self.assertEqual(g.lure_centers(), [])          # 隔一晚才能再用
        g.night_no = 4
        centers = g.lure_centers()
        self.assertNotIn(5, centers)                    # 4、5、6 和上次重疊
        self.assertIn(6, centers)
        self.assertIn(15, centers)                      # 14、15、1 不重疊

    def test_lure_once_when_child_joined_wolves(self):
        g = tiger_game()
        g.players[5].turned = True
        g.night_no, g.lure_uses, g.last_lure_night = 5, 1, 2
        self.assertEqual(g.lure_centers(), [])


class WolfBeautyTest(unittest.TestCase):
    def test_charmed_dies_with_beauty_at_night(self):
        g = tiger_game({1: {"choose_charm": lambda g, m: 12},
                        7: {"witch_action": lambda g, m, v: ("poison", 1)}})
        self.assertEqual(g.run_night().deaths, {1: "poison", 12: "charm"})

    def test_charmed_dies_when_beauty_exiled(self):
        ctrls = {s: {"vote": lambda g, m, c: 1 if m.seat != 1 else 11} for s in range(1, 16)}
        ctrls[1]["choose_charm"] = lambda g, m: 12
        g = tiger_game(ctrls)
        g.run_dawn(g.run_night())
        g.run_day()
        self.assertEqual(g.players[12].death_cause, "charm")

    def test_cannot_charm_same_player_twice_in_a_row(self):
        g = tiger_game({1: {"choose_charm": lambda g, m: 12}})
        g.run_night()
        g.run_night()
        self.assertIsNone(g.charm)

    def test_beauty_cannot_explode(self):
        g = tiger_game({1: {"self_explode": lambda g, m: True}},
                       rules=Rules(sheriff=False, self_explode=True))
        g.days.append(DayRecord(1))
        self.assertFalse(g._try_explode(g.players[1]))


class KnightAndGirlTest(unittest.TestCase):
    def day_game(self, duel_target):
        ctrls = {s: {"vote": lambda g, m, c: never()} for s in range(1, 16)}
        ctrls[8] = {"knight_duel": lambda g, m: duel_target, "vote": lambda g, m, c: None}
        g = tiger_game(ctrls)
        g.run_dawn(g.run_night())
        return g

    def test_duel_wolf_ends_day(self):
        g = self.day_game(3)
        self.assertIsNone(g.run_day())                  # 投票沒有被呼叫
        self.assertEqual(g.players[3].death_cause, "duel")
        self.assertTrue(g.players[8].alive)

    def test_duel_good_kills_knight(self):
        g = self.day_game(11)
        for s in range(1, 16):
            g.controllers[s].vote = lambda g_, m, c: None
        g.run_day()
        self.assertEqual(g.players[8].death_cause, "duel_fail")
        self.assertTrue(g.players[11].alive)

    def test_girl_accuracy_rules(self):
        g = tiger_game()
        girl = g.players[10]
        self.assertIsNone(g.girl_accuracy(girl))        # 還沒投票不能用
        g.sheriff_votes = {10: 3}
        self.assertTrue(g.girl_accuracy(girl))          # 警長票投狼 → 正確
        g.sheriff_votes = {10: 11}
        self.assertFalse(g.girl_accuracy(girl))         # 警長票投好人 → 相反
        g.sheriff_votes = {}
        g.days.append(DayRecord(1, votes={10: 3}))
        self.assertFalse(g.girl_accuracy(girl))         # 放逐票投狼 → 相反
        g.days.append(DayRecord(2, votes={10: 11}))
        self.assertTrue(g.girl_accuracy(girl))          # 看最近一次：投好人 → 正確

    def test_girl_sees_reversed_result(self):
        seen = []
        g = tiger_game({10: {"girl_check": lambda g, m, o: 3,
                             "on_girl_result": lambda g, m, t, w: seen.append((t, w))}})
        g.sheriff_votes = {10: 11}                      # 警長票投好人 → 相反
        g.run_night()
        self.assertEqual(seen, [(3, False)])            # 3 號是狼，卻看到好人
        self.assertTrue(g.girl_used)

    def test_side_kill_ignores_girl_and_child(self):
        g = tiger_game()
        for s in range(11, 16):
            g.players[s].alive = False
        self.assertIs(g.check_winner(), Team.WOLF)      # 五民全滅，村姑還活著也一樣


class SimulationTest(unittest.TestCase):
    def test_many_bot_games_finish(self):
        rng = random.Random(42)
        results = {Team.GOOD: 0, Team.WOLF: 0, None: 0}
        for key, (_, roles) in PRESETS.items():
            for _ in range(150):
                seed = rng.randrange(1 << 30)
                rules = Rules(sheriff=rng.random() < 0.7, self_explode=rng.random() < 0.7)
                g = Game(deal(roles, random.Random(seed)), rules=rules, seed=seed, out=lambda _: None)
                results[g.play()] += 1
        self.assertGreater(results[Team.GOOD], 0)
        self.assertGreater(results[Team.WOLF], 0)


if __name__ == "__main__":
    unittest.main()
