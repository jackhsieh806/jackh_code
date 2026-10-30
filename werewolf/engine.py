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
    "explode": "自爆",
    "charm": "被狼美人迷魅一同出局",
    "reflect": "被虎姑婆反傷",
    "duel": "被騎士決鬥",
    "duel_fail": "決鬥失敗以死謝罪",
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
    # 第一天是否競選警長（警長 1.5 票、決定發言方向、最後發言）
    sheriff: bool = True
    # 狼人可否在白天（含警長競選）自爆
    self_explode: bool = True
    # 電腦個性："mixed" 每個電腦隨機分配，或 personality.py 裡的某個 key 讓全部電腦相同
    bot_personality: str = "mixed"
    # 對局一開始就公開每個電腦的個性（練習看懂不同風格的玩家）
    show_personality: bool = False
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
    exploded: int | None = None   # 今天自爆的狼（自爆後直接天黑）


@dataclass
class Player:
    seat: int
    role: Role
    alive: bool = True
    can_vote: bool = True
    revealed: bool = False      # 身份已被公開證實（白痴翻牌、獵人開槍、狼王發動狼王爪）
    death_cause: str | None = None
    turned: bool = False        # 野孩子已轉入狼隊

    @property
    def is_wolf(self) -> bool:
        """是否以狼人身份行動（知道狼隊、參與夜晚殺人）。"""
        return self.role.team is Team.WOLF or self.turned


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
    def run_for_sheriff(self, game: "Game", me: Player) -> bool: return False
    def sheriff_vote(self, game: "Game", me: Player, candidates: list[int]) -> int | None: return None
    def pass_badge(self, game: "Game", me: Player) -> int | None:
        """警長出局時移交警徽，回傳 None 代表撕掉警徽。"""
        return None
    def choose_direction(self, game: "Game", me: Player) -> str:
        """警長決定發言方向："right" 從警長下一號往大號、"left" 往小號；警長最後發言。"""
        return "right"
    def self_explode(self, game: "Game", me: Player) -> bool:
        """狼人在自己發言前可以選擇自爆。"""
        return False
    def choose_model(self, game: "Game", me: Player) -> int | None: return None
    def on_turn(self, game: "Game", me: Player) -> None:
        """野孩子轉入狼隊時通知。"""
    def choose_charm(self, game: "Game", me: Player) -> int | None: return None
    def choose_lure(self, game: "Game", me: Player, centers: list[int]) -> int | None: return None
    def girl_check(self, game: "Game", me: Player, options: list[int]) -> int | None: return None
    def on_girl_result(self, game: "Game", me: Player, target: int, shown_wolf: bool) -> None: ...
    def knight_duel(self, game: "Game", me: Player) -> int | None: return None


def deal(roles: list[Role], rng: random.Random) -> list[Role]:
    """洗牌發身份，回傳依座位（1 號起）排列的角色。"""
    roles = list(roles)
    rng.shuffle(roles)
    return roles


class Game:
    def __init__(self, roles: list[Role], controllers: dict[int, Controller] | None = None,
                 rules: Rules | None = None, seed: int | None = None,
                 out: Callable[[str], None] = print, god_view: bool = False,
                 pause: Callable[[], None] | None = None, personality_mode: str | None = None):
        """roles 依座位順序排列（roles[0] 是 1 號）。沒指定 controller 的座位由電腦操作。

        personality_mode："mixed" 每個電腦隨機分配五種個性之一，或指定某個個性的 key 讓全部電腦相同。"""
        self.personality_mode = personality_mode or (rules.bot_personality if rules else "mixed")
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
        self.sheriff: int | None = None    # 現任警長
        self.sheriff_log: list[str] = []
        self.badge_from: dict[int, int] = {}   # 新警長 -> 把警徽交給他的前任警長
        self.phase = "night"               # night / election / day
        # 村姑與虎姑婆
        self.wild_model: int | None = None   # 野孩子的榜樣
        self.wild_fixed_good = False         # 榜樣是村姑：永遠是好人
        self.charm: int | None = None        # 狼美人目前迷魅的人
        self.last_charm: int | None = None
        self.lure_range: set[int] | None = None   # 今晚虎姑婆誘導的查驗範圍
        self.last_lure_range: set[int] = set()
        self.last_lure_night: int | None = None
        self.lure_uses = 0
        self.reflect_used = False
        self.girl_used = False
        self.sheriff_votes: dict[int, int | None] = {}
        self.knight_used = False
        self.knight_gold: set[int] = set()   # 騎士決鬥失敗而證實是好人的人（騎金）
        # 燈影預言家：開局由主持人決定哪張預言家牌查驗正確，另一張是反向查驗
        self.has_lantern = any(p.role is Role.LANTERN_SEER for p in self.players.values())
        self.seer_card_accurate = self.rng.random() < 0.5 if self.has_lantern else True
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

    def alignment(self, p: Player) -> Team:
        """目前所屬陣營（野孩子看榜樣與是否轉狼）。"""
        if p.role is Role.WILD_CHILD:
            if p.turned:
                return Team.WOLF
            model = self.players.get(self.wild_model)
            if model and not self.wild_fixed_good and model.role.team is Team.WOLF:
                return Team.WOLF
            return Team.GOOD
        return p.role.team

    def check_result(self, seat: int) -> bool:
        """查驗結果是否為狼。野孩子永遠驗出好人（金水）。"""
        return self.players[seat].role.team is Team.WOLF

    def card_accurate(self, role: Role) -> bool:
        """這張預言家牌的查驗是否正確（只有燈影預言家板會有反向查驗）。"""
        if role is Role.LANTERN_SEER:
            return not self.seer_card_accurate
        return self.seer_card_accurate if role is Role.SEER else True

    def claims_of(self, role: Role) -> dict[int, dict[int, bool]]:
        return {s: dict(c["checks"]) for s, c in self.claims.items() if c["role"] is role}

    def check_options(self, me: Player) -> list[int]:
        """預言家／村姑今晚可以查驗的人（受虎姑婆誘導限制）。

        燈影預言家板：兩位預言家都不能驗翻牌的騎士和騎金，避免用來確認自己是不是反向查驗。"""
        seats = [s for s in self.alive_seats() if s != me.seat]
        if self.has_lantern and me.role in (Role.SEER, Role.LANTERN_SEER):
            seats = [s for s in seats if s not in self.knight_gold
                     and not (self.players[s].role is Role.KNIGHT and self.players[s].revealed)]
        if self.lure_range is not None:
            seats = [s for s in seats if s in self.lure_range]
        return seats

    def check_winner(self) -> Team | None:
        alive = self.alive()
        if not any(p.role.team is Team.WOLF for p in alive):  # 真狼全滅（轉狼的野孩子不用出局）
            return Team.GOOD
        good = [p for p in alive if self.alignment(p) is Team.GOOD]
        if self.rules.win_mode == "all":
            return Team.WOLF if not good else None
        everyone = self.players.values()
        board_has_gods = any(p.role.is_god for p in everyone)
        villager_side = (Role.VILLAGER, Role.LANTERN_SEER)   # 燈影預言家站民坑
        board_has_villagers = any(p.role in villager_side for p in everyone)
        gods_dead = board_has_gods and not any(p.role.is_god for p in good)
        villagers_dead = board_has_villagers and not any(p.role in villager_side for p in good)
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
        if self.has_lantern:
            self.secret("主持人決定：" + ("預言家牌正確查驗、燈影預言家牌反向查驗" if self.seer_card_accurate
                                          else "預言家牌反向查驗、燈影預言家牌正確查驗"))
        from .personality import PERSONALITIES
        keys = list(PERSONALITIES)
        for seat in self.players:   # 先分配個性，狼隊決定誰悍跳時會參考隊友的個性
            ctrl = self.controllers[seat]
            if hasattr(ctrl, "personality") and ctrl.personality is None:
                key = self.personality_mode if self.personality_mode in PERSONALITIES else self.rng.choice(keys)
                ctrl.personality = PERSONALITIES[key]
        for seat in self.players:
            if (pers := self.personality_of(seat)) is not None:
                self.secret(f"{seat}號 電腦個性：{pers.name}")
        if self.rules.show_personality:
            shown = [f"{s}號 {p.name}" for s in self.players if (p := self.personality_of(s))]
            self.say("🎭 電腦個性：" + "、".join(shown))
        for seat, p in self.players.items():
            self.controllers[seat].setup(self, p)

    def personality_of(self, seat: int):
        """電腦玩家的個性；真人回傳 None。"""
        return getattr(self.controllers[seat], "personality", None)

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
        self.phase = "night"
        n = self.night_no
        rec = NightRecord(n)
        self.say(f"\n🌙 ===== 第 {n} 夜 ===== 天黑請閉眼")
        alive = set(self.alive_seats())
        self.lure_range = None

        wild = self.alive_with_role(Role.WILD_CHILD)
        if wild and self.wild_model is None and n == 1:
            t = self.controllers[wild.seat].choose_model(self, wild)
            if t in alive and t != wild.seat:
                self.wild_model = t
                model = self.players[t]
                self.secret(f"野孩子({wild.seat}號) 選 {t}號（{model.role.value}）當榜樣")
                if model.role is Role.VILLAGE_GIRL:
                    self.wild_fixed_good = True
                elif model.role is Role.TIGER_GRANDMA:
                    self._turn_wild(wild)   # 彩蛋：知道所有狼隊位置

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
                    result = self.check_result(t)
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
            if t in alive and self.players[t].role is Role.WOLF_BEAUTY:
                t = None   # 狼美人不能被自刀
            rec.kill = t if t in alive else None
            self.secret(f"狼人({'、'.join(str(w.seat) for w in wolves)}號) 殺 {rec.kill}號"
                        if rec.kill else "狼人空刀")

        beauty = self.alive_with_role(Role.WOLF_BEAUTY)
        if beauty:
            t = self.controllers[beauty.seat].choose_charm(self, beauty)
            if t not in alive or t == beauty.seat or t == self.last_charm:
                t = None
            self.charm = self.last_charm = t
            if t is not None:
                self.secret(f"狼美人({beauty.seat}號) 迷魅 {t}號")

        tiger = self.alive_with_role(Role.TIGER_GRANDMA)
        centers = self.lure_centers() if tiger else []
        if centers:
            c = self.controllers[tiger.seat].choose_lure(self, tiger, centers)
            if c in centers:
                self.lure_range = self._ring(c)
                self.last_lure_range = set(self.lure_range)
                self.last_lure_night = n
                self.lure_uses += 1
                rng = "、".join(map(str, sorted(self.lure_range)))
                self.secret(f"虎姑婆({tiger.seat}號) 誘導 {c}號：今晚只能查驗 {rng}號")

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

        girl_target = None
        girl = self.alive_with_role(Role.VILLAGE_GIRL)
        if girl and not self.girl_used and self.girl_accuracy(girl) is not None:
            options = self.check_options(girl)
            t = self.controllers[girl.seat].girl_check(self, girl, options) if options else None
            if t in options:
                self.girl_used = True
                girl_target = t
                correct = self.girl_accuracy(girl)
                truth = self.check_result(t)
                shown = truth if correct else not truth
                self.controllers[girl.seat].on_girl_result(self, girl, t, shown)
                self.secret(f"村姑({girl.seat}號) 查驗 {t}號 → 看到{'狼人' if shown else '好人'}"
                            f"（{'正確' if correct else '相反'}）")

        seer_target = None
        seer = self.alive_with_role(Role.SEER)
        if seer:
            options = self.check_options(seer)
            t = self.controllers[seer.seat].choose_check(self, seer) if options else None
            if t in options:
                seer_target = t
                truth = self.check_result(t)
                result = truth if self.card_accurate(Role.SEER) else not truth
                rec.check = (t, result)
                self.controllers[seer.seat].on_check_result(self, seer, t, result)
                note = "" if result == truth else "（反向）"
                self.secret(f"預言家({seer.seat}號) 查驗 {t}號 → {'狼人' if result else '好人'}{note}")

        lantern = self.alive_with_role(Role.LANTERN_SEER)
        if lantern:
            options = self.check_options(lantern)
            t = self.controllers[lantern.seat].choose_check(self, lantern) if options else None
            if t in options:
                truth = self.check_result(t)
                result = truth if self.card_accurate(Role.LANTERN_SEER) else not truth
                self.controllers[lantern.seat].on_check_result(self, lantern, t, result)
                note = "" if result == truth else "（反向）"
                self.secret(f"燈影預言家({lantern.seat}號) 查驗 {t}號 → {'狼人' if result else '好人'}{note}")

        reflect_death = None
        tiger = self.alive_with_role(Role.TIGER_GRANDMA)
        if tiger and not self.reflect_used:   # 惡靈反傷：村姑查驗 > 預言家查驗 > 女巫毒
            hit = None
            if girl_target == tiger.seat:
                hit = girl
            elif seer_target == tiger.seat:
                hit = seer
            elif rec.poison == tiger.seat:
                hit = witch
                rec.poison = None
            if hit is not None:
                self.reflect_used = True
                reflect_death = hit.seat
                self.secret(f"虎姑婆({tiger.seat}號) 惡靈反傷 → {hit.role.value}({hit.seat}號) 出局")

        rec.deaths = self.resolve_night(
            rec.kill, rec.guard, rec.saved, rec.poison, self.rules.same_guard_save_dies,
            extra_guard=lucky_guard, extra_poison=lucky_poison, dream=dream,
            dream_repeat=dream_repeat, dreamer=dreamer.seat if dreamer else None,
            trade_death=trade_death)
        if reflect_death is not None:
            rec.deaths.setdefault(reflect_death, "reflect")
        beauty = self.alive_with_role(Role.WOLF_BEAUTY)
        if beauty and beauty.seat in rec.deaths and self.charm in alive and self.charm not in rec.deaths:
            rec.deaths[self.charm] = "charm"
        for seat, cause in rec.deaths.items():
            self._mark_dead(seat, cause)
        self.nights.append(rec)
        return rec

    # ------------------------------------------------------------ 天亮
    def run_dawn(self, rec: NightRecord) -> Team | None:
        n = self.night_no
        day = DayRecord(n)
        self.days.append(day)
        self.say(f"\n☀️  ===== 第 {n} 天 ===== 天亮了")
        if n == 1 and self.rules.sheriff:
            self.run_election()  # 真人局習慣：先競選警長，再公布昨晚死訊
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
        self._badge_check()
        self.pause()
        return None

    # ------------------------------------------------------------ 警長
    def run_election(self) -> None:
        """第一天的警長競選。夜晚死掉的人此時還不知道自己死了，也能上警。"""
        self.phase = "election"
        self.say("\n🎖  ===== 警長競選 =====")
        seats = sorted(self.players)
        running = [s for s in seats if self.controllers[s].run_for_sheriff(self, self.players[s])]
        if not running or len(running) == len(seats):
            self.say("沒有人上警，警徽流失。" if not running else "全員上警，沒有人能投票，警徽流失。")
            self.sheriff_log.append("警徽流失（無人可選）")
            self.phase = "day"
            return
        self.say(f"上警：{'、'.join(map(str, running))}號")
        for seat in running:
            p = self.players[seat]
            if self._try_explode(p):
                self.say("警長競選中有人自爆，警徽流失。")
                self.sheriff_log.append(f"{seat}號 警上自爆，警徽流失")
                self.phase = "day"
                return
            speech = self.controllers[seat].speak(self, p)
            speech.seat = seat
            self._register_speech(speech)
            self.say(f"  🗣  {seat}號（警上）：{speech.render()}")
        voters = [s for s in seats if s not in running]
        self.say("—— 警長投票（警下玩家投票）——")
        votes = self._collect_votes(running, voters, sheriff=True)
        self.sheriff_votes = dict(votes)
        leaders = self._show_votes(votes, weighted=False)
        if len(leaders) > 1:
            self.say(f"⚖️  平票！{'、'.join(map(str, leaders))}號 PK，警下玩家重新投票。")
            votes = self._collect_votes(leaders, voters, sheriff=True)
            self.sheriff_votes.update({v: t for v, t in votes.items() if t is not None})
            leaders = self._show_votes(votes, weighted=False)
        if len(leaders) != 1:
            self.say("沒有人勝出，警徽流失。")
            self.sheriff_log.append("警徽流失（平票）")
        else:
            self.sheriff = leaders[0]
            self.sheriff_log.append(f"第1天 {self.sheriff}號 當選警長")
            self.say(f"🎖  {self.sheriff}號 當選警長！（投票算 1.5 票，決定發言方向並最後發言）")
        self.phase = "day"

    def _badge_check(self) -> None:
        """警長出局時移交或撕掉警徽。"""
        s = self.sheriff
        if s is None or self.players[s].alive:
            return
        p = self.players[s]
        t = self.controllers[s].pass_badge(self, p)
        if t is not None and t != s and t in self.alive_seats():
            self.sheriff = t
            self.badge_from[t] = s
            self.sheriff_log.append(f"第{self.night_no}天 {s}號 把警徽移交給 {t}號")
            self.say(f"🎖  警長 {s}號 把警徽移交給 {t}號。")
        else:
            self.sheriff = None
            self.sheriff_log.append(f"第{self.night_no}天 {s}號 撕掉警徽")
            self.say(f"🎖  警長 {s}號 撕掉了警徽，之後沒有警長。")

    def _try_explode(self, p: Player) -> bool:
        """狼人自爆：立即出局（無遺言），當天剩下的流程跳過。"""
        if not (self.rules.self_explode and p.alive and p.is_wolf) or p.role is Role.WOLF_BEAUTY:
            return False   # 狼美人不能自爆
        if not self.controllers[p.seat].self_explode(self, p):
            return False
        p.revealed = True
        self._kill(p.seat, "explode")
        self.today.exploded = p.seat
        self.today.events.append(f"{p.seat}號 自爆")
        label = p.role.value if p.role is not Role.WEREWOLF else "狼人"
        self.say(f"💣 {p.seat}號 自爆！翻牌【{label}】，今天的發言與投票全部跳過。")
        self._death_trigger(p.seat, "explode")  # 狼王自爆可以帶人
        return True

    # ------------------------------------------------------------ 白天
    def speech_order(self) -> list[int]:
        seats = self.alive_seats()
        if self.sheriff in seats:  # 警長決定方向，自己最後發言
            sp = self.sheriff
            direction = self.controllers[sp].choose_direction(self, self.players[sp])
            ring = sorted(seats, reverse=direction == "left")
            i = ring.index(sp)
            return ring[i + 1:] + ring[:i] + [sp]
        start = (self.night_no - 1) % len(seats)
        return seats[start:] + seats[:start]

    def run_day(self) -> Team | None:
        day = self.today
        if day.exploded is not None:  # 警上自爆 → 直接天黑
            self.phase = "night"
            return None
        self.phase = "day"
        order = self.speech_order()
        self.say(f"\n—— 發言環節（從 {order[0]}號 開始）——")
        for seat in order:
            p = self.players[seat]
            if not p.alive:
                continue
            if self._try_explode(p):
                self._badge_check()
                self.phase = "night"
                w = self.check_winner()
                self.pause()
                return w
            if p.role is Role.KNIGHT:
                duel = self._try_duel(p)
                if duel is not None:
                    self._badge_check()
                    if (w := self.check_winner()) is not None:
                        return w
                    if duel:
                        self.phase = "night"
                        self.pause()
                        return None
                    continue   # 騎士出局，換下一位發言
            speech = self.controllers[seat].speak(self, p)
            speech.seat = seat
            self._register_speech(speech)
            tag = "（警長）" if seat == self.sheriff else ""
            self.say(f"  🗣  {seat}號{tag}：{speech.render()}")
        self.pause()

        self.say("\n—— 投票環節 ——")
        exiled = self._vote_phase()
        self.phase = "night"
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
        self._kill(exiled, "vote")
        if (w := self.check_winner()) is not None:
            return w
        self._last_words(exiled)
        self._death_trigger(exiled, "vote")
        self._badge_check()
        w = self.check_winner()
        self.pause()
        return w

    def _collect_votes(self, candidates: list[int], voters: list[int],
                       sheriff: bool = False) -> dict[int, int | None]:
        votes: dict[int, int | None] = {}
        for v in voters:
            ctrl, me = self.controllers[v], self.players[v]
            t = ctrl.sheriff_vote(self, me, list(candidates)) if sheriff \
                else ctrl.vote(self, me, list(candidates))
            votes[v] = t if (t in candidates and t != v) else None
        return votes

    def vote_weight(self, voter: int) -> float:
        return 1.5 if voter == self.sheriff else 1.0

    def _show_votes(self, votes: dict[int, int | None], weighted: bool = True) -> list[int]:
        """顯示票型並回傳最高票者（可能多人）。警長的票算 1.5 票。"""
        by_target: dict[int, list[int]] = {}
        for voter, t in votes.items():
            if t is not None:
                by_target.setdefault(t, []).append(voter)
        total = {t: sum(self.vote_weight(v) if weighted else 1 for v in vs)
                 for t, vs in by_target.items()}
        for t, voters in sorted(by_target.items(), key=lambda kv: -total[kv[0]]):
            names = "、".join(f"{v}(警長)" if weighted and v == self.sheriff else str(v)
                             for v in voters)
            self.say(f"  {t}號 ← {names}（{total[t]:g} 票）")
        abstain = [v for v, t in votes.items() if t is None]
        if abstain:
            self.say(f"  棄票：{'、'.join(map(str, abstain))}")
        if not by_target:
            return []
        top = max(total.values())
        return sorted(t for t in by_target if total[t] == top)

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
        wild = self.alive_with_role(Role.WILD_CHILD)
        if wild and seat == self.wild_model and not self.wild_fixed_good and not wild.turned:
            self._turn_wild(wild)

    def _kill(self, seat: int, cause: str) -> None:
        """白天的出局：處理狼美人迷魅的連帶出局。"""
        self._mark_dead(seat, cause)
        p = self.players[seat]
        c = self.charm
        # 狼美人被騎士決鬥出局時技能失效
        if p.role is Role.WOLF_BEAUTY and cause != "duel" and c is not None and self.players[c].alive:
            self.say(f"💔 {c}號 被狼美人迷魅，一同出局。")
            self._mark_dead(c, "charm")
            self._death_trigger(c, "charm")

    def _turn_wild(self, wild: Player) -> None:
        wild.turned = True
        self.secret(f"野孩子({wild.seat}號) 轉入狼隊")
        self.controllers[wild.seat].on_turn(self, wild)

    # ------------------------------------------------------------ 虎姑婆、村姑、騎士
    def _ring(self, center: int) -> set[int]:
        n = len(self.players)
        return {(center - 2) % n + 1, center, center % n + 1}

    def lure_centers(self) -> list[int]:
        """虎姑婆今晚可以誘導的號碼；不能用時回傳空串列。"""
        if self.night_no < 2:
            return []
        if self.last_lure_night is not None and self.night_no - self.last_lure_night < 2:
            return []   # 每隔一晚才能用
        wild = next((p for p in self.players.values() if p.role is Role.WILD_CHILD), None)
        if wild and self.alignment(wild) is Team.WOLF and self.lure_uses >= 1:
            return []   # 野孩子入狼隊：誘導整局只能用一次
        return [c for c in self.players if not (self._ring(c) & self.last_lure_range)]

    def girl_accuracy(self, girl: Player) -> bool | None:
        """村姑查驗是否正確；還沒投過票回傳 None。優先看警長票。"""
        t = self.sheriff_votes.get(girl.seat)
        if t is not None:
            return self.players[t].role.team is Team.WOLF        # 警徽投狼 → 正確
        for d in reversed(self.days):
            t = d.pk_votes.get(girl.seat) or d.votes.get(girl.seat)
            if t is not None:
                return self.players[t].role.team is not Team.WOLF  # 出局投好人 → 正確
        return None

    def _try_duel(self, knight: Player) -> bool | None:
        """騎士決鬥。回傳 True 代表狼出局（立刻天黑），False 代表騎士出局，None 代表沒有決鬥。"""
        if self.knight_used:
            return None
        t = self.controllers[knight.seat].knight_duel(self, knight)
        if t is None or t == knight.seat or t not in self.alive_seats():
            return None
        self.knight_used = True
        knight.revealed = True
        target = self.players[t]
        self.today.events.append(f"{knight.seat}號 騎士決鬥 {t}號")
        if target.is_wolf:
            target.revealed = True
            self.say(f"⚔️  {knight.seat}號 翻牌【騎士】決鬥 {t}號：{t}號 是狼人，出局！立刻天黑。")
            self._kill(t, "duel")
            self._death_trigger(t, "duel")
            return True
        self.knight_gold.add(t)
        self.say(f"⚔️  {knight.seat}號 翻牌【騎士】決鬥 {t}號：{t}號 是好人，騎士以死謝罪。")
        self._kill(knight.seat, "duel_fail")
        return False

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
            self._kill(t, cause_t)
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
            day = prev["day"] if prev and prev["role"] is speech.claim else self.night_no
            self.claims[seat] = {"role": speech.claim, "checks": checks, "day": day}   # day：第一次跳這個身份是第幾天
        if speech.checks and self.claimed_role(seat) in (Role.SEER, Role.LANTERN_SEER):
            self.claims[seat]["checks"].update(speech.checks)
        if self.today is not None:
            self.today.speeches.append(speech)
