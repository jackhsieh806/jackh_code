"""狼人殺核心遊戲邏輯。

這個模組只負責「規則」與「流程」，不直接讀取鍵盤輸入；
每個座位的決策交給 Controller（電腦 BotController 或真人 HumanController）。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable

from .roles import Role, Team

DEATH_CAUSES = {
    "wolf": "被狼人殺害",
    "poison": "被女巫毒死",
    "vote": "被投票放逐",
    "shot": "被獵人帶走",
    "claw": "被狼王爪帶走",
    "dream": "夢遊出局",
    "trade": "交易失敗出局",
}

ITEMS = {"check": "查驗", "poison": "毒藥", "guard": "守護"}


@dataclass
class Rules:
    # 女巫自救："never" 全程不可自救 / "first_night" 僅首夜可自救 / "always" 任何時候都可自救
    witch_self_save: str = "first_night"
    # 同守同救是否死亡（多數線上與線下規則：會死）
    same_guard_save_dies: bool = True
    # 勝利條件："side" 屠邊（殺光所有平民或所有神職）/ "all" 屠城（殺光所有好人）
    win_mode: str = "side"
    # 首夜死亡者是否有遺言
    first_night_last_words: bool = True
    # 防止無限循環的回合上限
    max_rounds: int = 30


@dataclass
class Speech:
    seat: int
    claim: Role | None = None              # 宣稱的身份
    checks: dict[int, bool] = field(default_factory=dict)  # 宣稱的查驗：號碼 -> 是否為狼
    accuse: int | None = None              # 指認 / 歸票對象
    text: str = ""
    last_words: bool = False

    def render(self) -> str:
        parts = []
        if self.claim:
            parts.append(f"我是{self.claim.value}")
        if self.checks:
            items = "、".join(
                f"{t}號{'是狼人（查殺）' if w else '是好人（金水）'}"
                for t, w in self.checks.items())
            parts.append(f"查驗結果：{items}")
        if self.text:
            parts.append(self.text)
        if self.accuse is not None:
            parts.append(f"我認為 {self.accuse}號 是狼，歸票 {self.accuse}號")
        return "；".join(parts) if parts else "過。"


@dataclass
class NightRecord:
    night: int
    guard: int | None = None
    kill: int | None = None
    saved: bool = False
    poison: int | None = None
    check: tuple[int, bool] | None = None
    dream: int | None = None
    deaths: dict[int, str] = field(default_factory=dict)


@dataclass
class DayRecord:
    day: int
    speeches: list[Speech] = field(default_factory=list)
    votes: dict[int, int | None] = field(default_factory=dict)
    pk_votes: dict[int, int | None] = field(default_factory=dict)
    exiled: int | None = None
    events: list[str] = field(default_factory=list)


@dataclass
class Player:
    seat: int
    role: Role
    alive: bool = True
    can_vote: bool = True
    revealed: bool = False      # 身份已被公開證實（白痴翻牌、獵人開槍、狼王發動狼王爪）
    death_cause: str | None = None

    @property
    def is_wolf(self) -> bool:
        return self.role.team is Team.WOLF


class Controller:
    """座位的決策介面。預設實作都是「不行動」。"""

    is_human = False

    def setup(self, game: "Game", me: Player) -> None: ...
    def choose_guard(self, game: "Game", me: Player) -> int | None: return None
    def choose_kill(self, game: "Game", me: Player) -> int | None: return None
    def witch_action(self, game: "Game", me: Player, victim: int | None) -> tuple[str | None, int | None]:
        return None, None
    def choose_check(self, game: "Game", me: Player) -> int | None: return None
    def on_check_result(self, game: "Game", me: Player, target: int, is_wolf: bool) -> None: ...
    def speak(self, game: "Game", me: Player) -> Speech: return Speech(me.seat)
    def last_words(self, game: "Game", me: Player) -> Speech: return Speech(me.seat)
    def vote(self, game: "Game", me: Player, candidates: list[int]) -> int | None: return None
    def hunter_shoot(self, game: "Game", me: Player) -> int | None:
        """獵人開槍、狼王（含覺醒狼王、親傳隊友）發動狼王爪時都會呼叫，回傳要帶走的人。"""
        return None
    def hunter_poisoned(self, game: "Game", me: Player) -> None:
        """有開槍／狼王爪能力，但因被毒或夢遊出局而不能發動時通知。"""
    def choose_dream(self, game: "Game", me: Player) -> int | None: return None
    def merchant_trade(self, game: "Game", me: Player) -> tuple[int, str] | None: return None
    def on_lucky(self, game: "Game", me: Player, item: str) -> None: ...
    def lucky_action(self, game: "Game", me: Player, item: str) -> int | None: return None
    def pass_claw(self, game: "Game", me: Player) -> int | None: return None
    def on_claw(self, game: "Game", me: Player) -> None: ...


def deal(roles: list[Role], rng: random.Random) -> list[Role]:
    """洗牌發身份，回傳依座位（1 號起）排列的角色。"""
    roles = list(roles)
    rng.shuffle(roles)
    return roles


class Game:
    def __init__(self, roles: list[Role], controllers: dict[int, Controller] | None = None,
                 rules: Rules | None = None, seed: int | None = None,
                 out: Callable[[str], None] = print, god_view: bool = False,
                 pause: Callable[[], None] | None = None):
        """roles 依座位順序排列（roles[0] 是 1 號）。沒指定 controller 的座位由電腦操作。"""
        from .bots import BotController

        self.rng = random.Random(seed)
        self.rules = rules or Rules()
        self.out = out
        self.god_view = god_view
        self.pause = pause or (lambda: None)
        self.players: dict[int, Player] = {i + 1: Player(i + 1, r) for i, r in enumerate(roles)}
        controllers = dict(controllers or {})
        self.controllers: dict[int, Controller] = {
            s: controllers.get(s) or BotController() for s in self.players}

        self.night_no = 0
        self.antidote = True
        self.poison = True
        self.last_guard: int | None = None
        self.last_dream: int | None = None
        self.trade_used = False
        self.lucky: dict | None = None      # 幸運兒：{"seat", "item", "used"}
        self.claws: dict[int, int] = {      # 剩餘的狼王爪次數
            p.seat: (2 if p.role is Role.AWAKENED_WOLF_KING else 1)
            for p in self.players.values() if p.role in (Role.WOLF_KING, Role.AWAKENED_WOLF_KING)}
        self.claw_given: set[int] = set()  # 曾被親傳狼王爪的狼
        self.claims: dict[int, dict] = {}   # 公開宣稱：seat -> {"role": Role, "checks": {t: is_wolf}}
        self.nights: list[NightRecord] = []
        self.days: list[DayRecord] = []
        self.god_log: list[str] = []
        self.wolf_plan: dict = {}           # 狼隊共享的戰術（只有狼可以讀）
        self.winner: Team | None = None
        self._setup_done = False

    # ------------------------------------------------------------ 查詢工具
    def alive(self) -> list[Player]:
        return [p for p in self.players.values() if p.alive]

    def alive_seats(self) -> list[int]:
        return [p.seat for p in self.alive()]

    def alive_with_role(self, role: Role) -> Player | None:
        return next((p for p in self.alive() if p.role is role), None)

    @property
    def today(self) -> DayRecord | None:
        return self.days[-1] if self.days else None

    def claimed_role(self, seat: int) -> Role | None:
        return self.claims.get(seat, {}).get("role")

    def seer_claims(self) -> dict[int, dict[int, bool]]:
        """所有跳過預言家的人及其宣稱的查驗（包含已死亡的人）。"""
        return {s: dict(c["checks"]) for s, c in self.claims.items() if c["role"] is Role.SEER}

    def can_witch_save(self, witch: Player, victim: int | None) -> bool:
        if victim is None or not self.antidote:
            return False
        if victim != witch.seat:
            return True
        mode = self.rules.witch_self_save
        return mode == "always" or (mode == "first_night" and self.night_no == 1)

    def check_winner(self) -> Team | None:
        alive = self.alive()
        if not any(p.is_wolf for p in alive):
            return Team.GOOD
        good = [p for p in alive if not p.is_wolf]
        if self.rules.win_mode == "all":
            return Team.WOLF if not good else None
        everyone = self.players.values()
        board_has_gods = any(p.role.is_god for p in everyone)
        board_has_villagers = any(p.role is Role.VILLAGER for p in everyone)
        gods_dead = board_has_gods and not any(p.role.is_god for p in good)
        villagers_dead = board_has_villagers and not any(p.role is Role.VILLAGER for p in good)
        return Team.WOLF if (gods_dead or villagers_dead or not good) else None

    @staticmethod
    def resolve_night(kill: int | None, guard: int | None, saved: bool, poison: int | None,
                      same_guard_save_dies: bool = True, *, extra_guard: int | None = None,
                      extra_poison: int | None = None, dream: int | None = None,
                      dream_repeat: bool = False, dreamer: int | None = None,
                      trade_death: int | None = None) -> dict[int, str]:
        """結算夜晚死亡：回傳 {座位: 死因}。

        守衛擋不住毒藥；夢遊者免疫狼刀與毒藥，但連續兩晚被攝夢會出局；
        攝夢人晚上死亡時，夢遊者跟著出局。extra_guard / extra_poison 是幸運兒的道具。
        """
        deaths: dict[int, str] = {}
        if kill is not None:
            guarded = kill in (guard, extra_guard)
            if guarded and saved:
                if same_guard_save_dies:
                    deaths[kill] = "wolf"
            elif not (guarded or saved):
                deaths[kill] = "wolf"
        for p in (poison, extra_poison):
            if p is not None:
                deaths[p] = "poison"
        if dream is not None and not dream_repeat:
            deaths.pop(dream, None)
        if trade_death is not None:
            deaths.setdefault(trade_death, "trade")
        if dream is not None and (dream_repeat or (dreamer is not None and dreamer in deaths)):
            deaths[dream] = "dream"
        return deaths

    # ------------------------------------------------------------ 輸出
    def say(self, msg: str) -> None:
        self.out(msg)

    def secret(self, msg: str) -> None:
        line = f"[第{self.night_no}輪] {msg}"
        self.god_log.append(line)
        if self.god_view:
            self.out(f"    👁  {msg}")

    # ------------------------------------------------------------ 主流程
    def setup(self) -> None:
        if self._setup_done:
            return
        self._setup_done = True
        for seat, p in self.players.items():
            self.controllers[seat].setup(self, p)

    def play(self) -> Team | None:
        self.setup()
        counts: dict[Role, int] = {}
        for p in self.players.values():
            counts[p.role] = counts.get(p.role, 0) + 1
        board = "、".join(f"{r.value}×{n}" for r, n in counts.items())
        self.say(f"本局 {len(self.players)} 人，板子：{board}")
        winner = None
        while True:
            record = self.run_night()
            winner = self.run_dawn(record)
            if winner is None:
                winner = self.run_day()
            if winner is not None or self.night_no >= self.rules.max_rounds:
                break
        return self.finish(winner)

    def finish(self, winner: Team | None) -> Team | None:
        self.winner = winner
        if winner is None:
            self.say("\n⌛ 回合數到達上限，本局平手。")
        else:
            self.say(f"\n🏁 遊戲結束！{winner.value}獲勝！")
        return winner

    # ------------------------------------------------------------ 夜晚
    def run_night(self) -> NightRecord:
        self.night_no += 1
        n = self.night_no
        rec = NightRecord(n)
        self.say(f"\n🌙 ===== 第 {n} 夜 ===== 天黑請閉眼")
        alive = set(self.alive_seats())

        dream, dream_repeat = None, False
        dreamer = self.alive_with_role(Role.DREAMER)
        if dreamer:
            t = self.controllers[dreamer.seat].choose_dream(self, dreamer)
            if t in alive and t != dreamer.seat:
                dream, dream_repeat = t, t == self.last_dream
                self.secret(f"攝夢人({dreamer.seat}號) 讓 {t}號 夢遊" + ("（連續兩晚）" if dream_repeat else ""))
            self.last_dream = dream
        rec.dream = dream

        trade_death = None
        merchant = self.alive_with_role(Role.MERCHANT)
        if merchant and not self.trade_used:
            deal_ = self.controllers[merchant.seat].merchant_trade(self, merchant)
            if deal_ and deal_[0] in alive and deal_[0] != merchant.seat and deal_[1] in ITEMS:
                t, item = deal_
                self.trade_used = True
                if self.players[t].is_wolf:
                    trade_death = merchant.seat
                    self.secret(f"奇蹟商人({merchant.seat}號) 把{ITEMS[item]}交給 {t}號，但他是狼 → 交易失敗")
                else:
                    self.lucky = {"seat": t, "item": item, "used": False}
                    self.secret(f"奇蹟商人({merchant.seat}號) 把{ITEMS[item]}交給 {t}號（幸運兒）")
                    self.controllers[t].on_lucky(self, self.players[t], item)

        lucky_guard = lucky_poison = None
        lk = self.lucky
        if lk and not lk["used"] and self.players[lk["seat"]].alive:
            lp = self.players[lk["seat"]]
            t = self.controllers[lp.seat].lucky_action(self, lp, lk["item"])
            if t in alive and t != lp.seat:
                lk["used"] = True
                if lk["item"] == "check":
                    result = self.players[t].is_wolf
                    self.controllers[lp.seat].on_check_result(self, lp, t, result)
                    self.secret(f"幸運兒({lp.seat}號) 查驗 {t}號 → {'狼人' if result else '好人'}")
                elif lk["item"] == "guard":
                    lucky_guard = t
                    self.secret(f"幸運兒({lp.seat}號) 守護 {t}號")
                else:
                    lucky_poison = t
                    self.secret(f"幸運兒({lp.seat}號) 毒了 {t}號")

        guard = self.alive_with_role(Role.GUARD)
        if guard:
            t = self.controllers[guard.seat].choose_guard(self, guard)
            if t is not None and (t not in alive or t == self.last_guard):
                t = None  # 不合法的守護視為空守
            rec.guard = t
            self.last_guard = t
            self.secret(f"守衛({guard.seat}號) 守護 {t}號" if t else f"守衛({guard.seat}號) 空守")

        wolves = [p for p in self.alive() if p.is_wolf]
        if wolves:
            leader = next((w for w in wolves if self.controllers[w.seat].is_human), wolves[0])
            t = self.controllers[leader.seat].choose_kill(self, leader)
            rec.kill = t if t in alive else None
            self.secret(f"狼人({'、'.join(str(w.seat) for w in wolves)}號) 殺 {rec.kill}號"
                        if rec.kill else "狼人空刀")

        awk = self.alive_with_role(Role.AWAKENED_WOLF_KING)
        if awk and self.claws.get(awk.seat, 0) > 0:
            t = self.controllers[awk.seat].pass_claw(self, awk)
            mate = self.players.get(t)
            if mate and mate.alive and mate.is_wolf and t != awk.seat and t not in self.claw_given:
                self.claws[awk.seat] -= 1
                self.claw_given.add(t)
                self.claws[t] = self.claws.get(t, 0) + 1
                self.secret(f"覺醒狼王({awk.seat}號) 親傳狼王爪給 {t}號")
                self.controllers[t].on_claw(self, mate)

        witch = self.alive_with_role(Role.WITCH)
        if witch:
            victim = rec.kill if self.antidote else None
            action, target = self.controllers[witch.seat].witch_action(self, witch, victim)
            if action == "save" and self.can_witch_save(witch, rec.kill):
                rec.saved = True
                self.antidote = False
                self.secret(f"女巫({witch.seat}號) 使用解藥救了 {rec.kill}號")
            elif action == "poison" and self.poison and target in alive:
                rec.poison = target
                self.poison = False
                self.secret(f"女巫({witch.seat}號) 毒了 {target}號")

        seer = self.alive_with_role(Role.SEER)
        if seer:
            t = self.controllers[seer.seat].choose_check(self, seer)
            if t in alive and t != seer.seat:
                result = self.players[t].is_wolf
                rec.check = (t, result)
                self.controllers[seer.seat].on_check_result(self, seer, t, result)
                self.secret(f"預言家({seer.seat}號) 查驗 {t}號 → {'狼人' if result else '好人'}")

        rec.deaths = self.resolve_night(
            rec.kill, rec.guard, rec.saved, rec.poison, self.rules.same_guard_save_dies,
            extra_guard=lucky_guard, extra_poison=lucky_poison, dream=dream,
            dream_repeat=dream_repeat, dreamer=dreamer.seat if dreamer else None,
            trade_death=trade_death)
        for seat, cause in rec.deaths.items():
            self._mark_dead(seat, cause)
        self.nights.append(rec)
        return rec

    # ------------------------------------------------------------ 天亮
    def run_dawn(self, rec: NightRecord) -> Team | None:
        n = self.night_no
        self.days.append(DayRecord(n))
        self.say(f"\n☀️  ===== 第 {n} 天 ===== 天亮了")
        if not rec.deaths:
            self.say("昨晚是平安夜，沒有人死亡。")
        else:
            dead = "、".join(f"{s}號" for s in sorted(rec.deaths))
            self.say(f"昨晚死亡的是：{dead}")
        if (w := self.check_winner()) is not None:
            return w
        for seat in sorted(rec.deaths):
            if n == 1 and self.rules.first_night_last_words:
                self._last_words(seat)
            self._death_trigger(seat, rec.deaths[seat])
            if (w := self.check_winner()) is not None:
                return w
        self.pause()
        return None

    # ------------------------------------------------------------ 白天
    def speech_order(self) -> list[int]:
        seats = self.alive_seats()
        start = (self.night_no - 1) % len(seats)
        return seats[start:] + seats[:start]

    def run_day(self) -> Team | None:
        day = self.today
        order = self.speech_order()
        self.say(f"\n—— 發言環節（從 {order[0]}號 開始）——")
        for seat in order:
            p = self.players[seat]
            if not p.alive:
                continue
            speech = self.controllers[seat].speak(self, p)
            speech.seat = seat
            self._register_speech(speech)
            self.say(f"  🗣  {seat}號：{speech.render()}")
        self.pause()

        self.say("\n—— 投票環節 ——")
        exiled = self._vote_phase()
        if exiled is None:
            return None
        p = self.players[exiled]
        if p.role is Role.IDIOT and not p.revealed:
            p.revealed = True
            p.can_vote = False
            day.events.append(f"{exiled}號 翻牌白痴")
            self.say(f"🃏 {exiled}號 翻牌【白痴】！免於出局，但從此失去投票權。")
            return None
        day.exiled = exiled
        self.say(f"🚪 {exiled}號 被放逐出局。")
        self._mark_dead(exiled, "vote")
        if (w := self.check_winner()) is not None:
            return w
        self._last_words(exiled)
        self._death_trigger(exiled, "vote")
        w = self.check_winner()
        self.pause()
        return w

    def _collect_votes(self, candidates: list[int], voters: list[int]) -> dict[int, int | None]:
        votes: dict[int, int | None] = {}
        for v in voters:
            t = self.controllers[v].vote(self, self.players[v], list(candidates))
            votes[v] = t if (t in candidates and t != v) else None
        return votes

    def _show_votes(self, votes: dict[int, int | None]) -> list[int]:
        """顯示票型並回傳最高票者（可能多人）。"""
        by_target: dict[int, list[int]] = {}
        for voter, t in votes.items():
            if t is not None:
                by_target.setdefault(t, []).append(voter)
        for t, voters in sorted(by_target.items(), key=lambda kv: -len(kv[1])):
            self.say(f"  {t}號 ← {'、'.join(map(str, voters))}（{len(voters)} 票）")
        abstain = [v for v, t in votes.items() if t is None]
        if abstain:
            self.say(f"  棄票：{'、'.join(map(str, abstain))}")
        if not by_target:
            return []
        top = max(len(v) for v in by_target.values())
        return sorted(t for t, v in by_target.items() if len(v) == top)

    def _vote_phase(self) -> int | None:
        day = self.today
        candidates = self.alive_seats()
        voters = [s for s in candidates if self.players[s].can_vote]
        day.votes = self._collect_votes(candidates, voters)
        leaders = self._show_votes(day.votes)
        if not leaders:
            self.say("無人得票，今天沒有人出局。")
            return None
        if len(leaders) > 1:
            self.say(f"⚖️  平票！{'、'.join(map(str, leaders))}號 上 PK 台，由其他人重新投票。")
            pk_voters = [v for v in voters if v not in leaders]
            day.pk_votes = self._collect_votes(leaders, pk_voters)
            leaders = self._show_votes(day.pk_votes)
            if len(leaders) != 1:
                self.say("再次平票（或無人投票），今天沒有人出局。")
                return None
        return leaders[0]

    # ------------------------------------------------------------ 死亡處理
    def _mark_dead(self, seat: int, cause: str) -> None:
        p = self.players[seat]
        p.alive = False
        p.death_cause = cause

    def _death_trigger(self, seat: int, cause: str) -> None:
        """獵人開槍、狼王／覺醒狼王／親傳隊友發動狼王爪。"""
        p = self.players[seat]
        shots = 1 if p.role is Role.HUNTER else self.claws.get(seat, 0)
        if shots <= 0:
            return
        ctrl = self.controllers[seat]
        if cause in ("poison", "dream"):
            ctrl.hunter_poisoned(self, p)
            self.secret(f"{seat}號 因{DEATH_CAUSES[cause]}，不能發動技能")
            return
        hunter = p.role is Role.HUNTER
        for _ in range(shots):
            t = ctrl.hunter_shoot(self, p)
            if t is None or t == seat or t not in self.alive_seats():
                if not p.revealed:
                    self.secret(f"{seat}號 選擇不發動技能")
                return
            if not hunter:
                self.claws[seat] -= 1
            label = p.role.value if p.role is not Role.WEREWOLF else "狼人（親傳狼王爪）"
            p.revealed = True
            action = "開槍" if hunter else "發動狼王爪"
            if self.today:
                self.today.events.append(f"{seat}號 {label}{action}帶走 {t}號")
            self.say(f"💥 {seat}號 翻牌【{label}】，{action}帶走了 {t}號！")
            cause_t = "shot" if hunter else "claw"
            self._mark_dead(t, cause_t)
            if self.check_winner() is not None:
                return
            self._last_words(t)
            self._death_trigger(t, cause_t)  # 被帶走的獵人／狼王也能發動
            if self.check_winner() is not None:
                return

    def _last_words(self, seat: int) -> None:
        p = self.players[seat]
        speech = self.controllers[seat].last_words(self, p)
        speech.seat = seat
        speech.last_words = True
        self._register_speech(speech)
        self.say(f"  🕯  {seat}號 遺言：{speech.render()}")

    def _register_speech(self, speech: Speech) -> None:
        seat = speech.seat
        valid = set(self.players)
        speech.checks = {t: bool(w) for t, w in speech.checks.items() if t in valid and t != seat}
        if speech.accuse not in valid:
            speech.accuse = None
        if speech.claim is not None:
            prev = self.claims.get(seat)
            checks = dict(prev["checks"]) if prev and prev["role"] is speech.claim else {}
            self.claims[seat] = {"role": speech.claim, "checks": checks}
        if speech.checks and self.claimed_role(seat) is Role.SEER:
            self.claims[seat]["checks"].update(speech.checks)
        if self.today is not None:
            self.today.speeches.append(speech)
