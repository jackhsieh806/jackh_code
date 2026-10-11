"""電腦玩家的決策邏輯。

電腦玩家只會使用「它的身份應該知道的資訊」：
  * 好人：自己的身份、公開發言、票型、公開翻牌（白痴、獵人）；預言家另外知道自己的查驗。
  * 狼人：知道所有狼隊友。
推理重點是「找矛盾」：例如有人跳預言家說我是狼，但我知道自己是好人 → 他一定是假預言家。
"""
from __future__ import annotations

from dataclasses import dataclass

from .engine import ITEMS, Controller, Game, Player, Speech
from .roles import Role


CLAIMABLE = (Role.HUNTER, Role.WITCH, Role.IDIOT, Role.DREAMER, Role.MERCHANT)


@dataclass
class Knowledge:
    good: set[int]                     # 確定是好人
    wolf: set[int]                     # 確定是狼人
    trusted: int | None                # 選擇相信的預言家
    claims: dict[int, dict[int, bool]]  # 所有跳預言家的人與其查驗


class BotController(Controller):
    def __init__(self) -> None:
        self.checks: dict[int, bool] = {}       # 真預言家的查驗
        self.fake_checks: dict[int, bool] = {}  # 悍跳狼編的查驗
        self.fake_days: set[int] = set()
        self.pref: dict[int, float] = {}        # 對每個人的「直覺」，用來打破平手
        self.saved: int | None = None           # 女巫救過的人（銀水）
        self.item: str | None = None            # 幸運兒拿到的道具
        self.traded: tuple[int, str] | None = None  # 奇蹟商人交易紀錄

    # ------------------------------------------------------------ 初始化與推理
    def setup(self, game: Game, me: Player) -> None:
        self.rng = game.rng
        self.pref = {s: self.rng.random() for s in game.players}
        if me.is_wolf and "fake_seer" not in game.wolf_plan:
            bots = [p.seat for p in game.players.values()
                    if p.is_wolf and not game.controllers[p.seat].is_human]
            # 狼隊開局決定要不要派一隻狼悍跳預言家
            game.wolf_plan["fake_seer"] = (
                self.rng.choice(bots) if bots and self.rng.random() < 0.6 else None)

    def analyze(self, game: Game, me: Player) -> Knowledge:
        claims = game.seer_claims()
        if me.is_wolf:
            wolves = {p.seat for p in game.players.values() if p.is_wolf}
            return Knowledge(set(game.players) - wolves, wolves, None, claims)

        revealed = [p for p in game.players.values() if p.revealed]
        good = {me.seat} | {p.seat for p in revealed if not p.is_wolf}
        wolf: set[int] = {p.seat for p in revealed if p.is_wolf}  # 翻牌的狼王
        for t, is_wolf in self.checks.items():  # 預言家或拿到查驗的幸運兒
            (wolf if is_wolf else good).add(t)
        if me.role is Role.SEER:
            wolf |= {c for c in claims if c != me.seat}  # 真預言家只有我一個
        changed = True
        while changed:  # 反覆找矛盾，直到沒有新結論
            changed = False
            for c, checks in claims.items():
                if c in wolf or c in good:
                    continue
                if any((w and t in good) or (not w and t in wolf) for t, w in checks.items()):
                    wolf.add(c)
                    changed = True
        candidates = [c for c in claims if c not in wolf and c != me.seat]
        trusted = None
        if me.role is not Role.SEER and candidates:
            trusted = max(candidates, key=lambda c: self.pref[c])
        return Knowledge(good, wolf, trusted, claims)

    def suspicion(self, game: Game, me: Player, k: Knowledge) -> dict[int, float]:
        today = game.today
        base: dict[int, float] = {}
        for p in game.players.values():
            s = p.seat
            if s == me.seat:
                continue
            v = self.pref[s] * 2
            if s in k.wolf:
                v += 100
            if s in k.good:
                v -= 100
            if k.trusted is not None:
                checks = k.claims.get(k.trusted, {})
                if s in checks:
                    v += 20 if checks[s] else -8
                if s == k.trusted:
                    v -= 15
                elif s in k.claims:
                    v += 10  # 和我相信的預言家對跳
            if game.claimed_role(s) in CLAIMABLE:
                v -= 3
            for d in game.days:  # 看票型與發言：攻擊可信的人很可疑
                for sp in d.speeches:
                    if sp.seat == s and sp.accuse is not None:
                        if sp.accuse in k.good or sp.accuse == k.trusted:
                            v += 5
                        elif sp.accuse in k.wolf:
                            v -= 2
                if d is today:
                    continue
                for votes in (d.votes, d.pk_votes):
                    tgt = votes.get(s)
                    if tgt in k.good or (tgt is not None and tgt == k.trusted):
                        v += 5
                    elif tgt in k.wolf:
                        v -= 3
            base[s] = v

        # 今天的指認：只採信「我不懷疑的人」說的話
        score = {s: v for s, v in base.items() if game.players[s].alive}
        if today:
            for sp in today.speeches:
                if sp.accuse in score and sp.seat != me.seat and base.get(sp.seat, -99) < 8:
                    score[sp.accuse] += 3 if sp.seat == k.trusted else 1.5
        return score

    def _top(self, score: dict[int, float], pool=None) -> int | None:
        pool = [s for s in (pool if pool is not None else score) if s in score]
        return max(pool, key=score.get) if pool else None

    # ------------------------------------------------------------ 夜晚
    def choose_guard(self, game: Game, me: Player) -> int | None:
        options = [s for s in game.alive_seats() if s != game.last_guard]
        if game.night_no == 1:
            return None if self.rng.random() < 0.6 else self.rng.choice(options)
        k = self.analyze(game, me)
        if k.trusted in options and game.players[k.trusted].alive:
            return k.trusted
        witch = [s for s in options if game.claimed_role(s) is Role.WITCH]
        if witch:
            return witch[0]
        return self.rng.choice(options) if options else None

    def choose_kill(self, game: Game, me: Player) -> int | None:
        good = [p.seat for p in game.alive() if not p.is_wolf]
        if not good:
            return None
        hunters = {s for s in good if game.claimed_role(s) is Role.HUNTER}
        claims = game.seer_claims()
        real_seers = [c for c in claims if c in good]
        witches = [s for s in good if game.claimed_role(s) is Role.WITCH]
        golds = [t for c in real_seers for t, w in claims[c].items() if not w and t in good]
        for group in (real_seers, witches, golds):
            group = [s for s in group if s not in hunters]
            if group and self.rng.random() < 0.85:
                return self.rng.choice(group)
        return self.rng.choice([s for s in good if s not in hunters] or good)

    def witch_action(self, game: Game, me: Player, victim: int | None):
        if victim is not None and game.can_witch_save(me, victim):
            k = self.analyze(game, me)
            if (game.night_no == 1 and self.rng.random() < 0.9) or victim == k.trusted \
                    or victim in k.good:
                self.saved = victim
                return "save", None
        if game.poison and game.night_no >= 2:
            k = self.analyze(game, me)
            alive = set(game.alive_seats())
            certain = [s for s in k.wolf if s in alive]
            if certain:
                return "poison", self.rng.choice(certain)
            score = self.suspicion(game, me, k)
            top = self._top(score)
            if top is not None and score[top] >= 20 and self.rng.random() < 0.5:
                return "poison", top
        return None, None

    def choose_check(self, game: Game, me: Player) -> int | None:
        pool = [s for s in game.alive_seats() if s != me.seat and s not in self.checks]
        if not pool:
            return None
        if game.night_no > 1 and self.rng.random() < 0.6:
            score = self.suspicion(game, me, self.analyze(game, me))
            return self._top(score, pool)
        return self.rng.choice(pool)

    def on_check_result(self, game: Game, me: Player, target: int, is_wolf: bool) -> None:
        self.checks[target] = is_wolf

    # ------------------------------------------------------------ 白天
    def speak(self, game: Game, me: Player) -> Speech:
        return self._speech(game, me, last=False)

    def last_words(self, game: Game, me: Player) -> Speech:
        return self._speech(game, me, last=True)

    def _accused_today(self, game: Game, me: Player) -> bool:
        return bool(game.today) and any(sp.accuse == me.seat for sp in game.today.speeches)

    def _speech(self, game: Game, me: Player, last: bool) -> Speech:
        k = self.analyze(game, me)
        if me.is_wolf:
            return self._wolf_speech(game, me, k, last)
        score = self.suspicion(game, me, k)
        top = self._top(score)

        if me.role is Role.SEER:
            already = game.claimed_role(me.seat) is Role.SEER
            if self.checks and (last or already or any(self.checks.values())
                                or k.claims or self.rng.random() < 0.8):
                alive_wolves = [t for t, w in self.checks.items() if w and game.players[t].alive]
                rivals = [c for c in k.claims if c != me.seat and game.players[c].alive]
                accuse = (alive_wolves or rivals or [top])[0]
                text = "對跳的那位是悍跳狼！" if rivals else ""
                return Speech(me.seat, Role.SEER, dict(self.checks), accuse, text)

        if last:
            text = f"請相信 {k.trusted}號 預言家" if k.trusted else "大家加油"
            if me.role is Role.WITCH and self.saved:
                text += f"；我救過 {self.saved}號"
            if me.role is Role.MERCHANT and self.traded:
                text += f"；我把{ITEMS[self.traded[1]]}給了 {self.traded[0]}號"
            return Speech(me.seat, me.role, accuse=top, text=text)

        if self.item == "check" and self.checks:
            t, w = next(iter(self.checks.items()))
            alive_wolves = [x for x, y in self.checks.items() if y and game.players[x].alive]
            return Speech(me.seat, accuse=(alive_wolves or [top])[0],
                          text=f"我是幸運兒，用商人給的查驗驗了 {t}號，他是{'狼人' if w else '好人'}")
        if me.role in (Role.HUNTER, Role.WITCH, Role.MERCHANT, Role.DREAMER) \
                and self._accused_today(game, me):
            text = {Role.HUNTER: "出我的話我會開槍", Role.DREAMER: "我是攝夢人，出我很虧"}.get(me.role, "")
            if me.role is Role.WITCH and self.saved:
                text = f"我救過 {self.saved}號（銀水）"
            if me.role is Role.MERCHANT and self.traded:
                text = f"我把{ITEMS[self.traded[1]]}給了 {self.traded[0]}號"
            return Speech(me.seat, me.role, accuse=top, text=text)

        if k.trusted is not None:
            text = f"我站 {k.trusted}號 預言家的邊"
        elif len(k.claims) >= 2:
            text = "預言家對跳，我還在聽"
        else:
            text = "目前資訊不多"
        return Speech(me.seat, accuse=top, text=text)

    # ------------------------------------------------------------ 狼人白天策略
    def _wolf_speech(self, game: Game, me: Player, k: Knowledge, last: bool) -> Speech:
        good_alive = [p.seat for p in game.alive() if not p.is_wolf]
        if game.wolf_plan.get("fake_seer") == me.seat:
            if game.night_no not in self.fake_days and not (last and self.fake_checks):
                self.fake_days.add(game.night_no)
                self._invent_check(game, me, k, good_alive)
            rivals = [c for c in game.seer_claims() if c != me.seat and game.players[c].alive]
            fake_wolves = [t for t, w in self.fake_checks.items() if w and game.players[t].alive]
            accuse = (fake_wolves or rivals or good_alive or [None])[0]
            text = "我才是真預言家，對跳的是狼" if rivals else ""
            return Speech(me.seat, Role.SEER, dict(self.fake_checks), accuse, text)

        target = self.wolf_target(game, k)
        if last:
            return Speech(me.seat, Role.VILLAGER, accuse=target, text="你們出錯人了")
        if self._accused_today(game, me) and self.rng.random() < 0.25:
            return Speech(me.seat, Role.HUNTER, accuse=target, text="出我的話我會開槍")  # 假跳獵人
        fake = game.wolf_plan.get("fake_seer")
        text = f"我站 {fake}號 預言家" if fake and game.players[fake].alive else "我是平民"
        return Speech(me.seat, accuse=target, text=text)

    def _invent_check(self, game: Game, me: Player, k: Knowledge, good_alive: list[int]) -> None:
        unused = [s for s in good_alive if s not in self.fake_checks and not game.players[s].revealed]
        rivals = [c for c in game.seer_claims() if c in unused]
        mates = [s for s in game.alive_seats()
                 if s in k.wolf and s != me.seat and s not in self.fake_checks]
        roll = self.rng.random()
        if rivals and roll < 0.8:
            self.fake_checks[rivals[0]] = True     # 對真預言家發查殺
        elif mates and roll < 0.35:
            self.fake_checks[self.rng.choice(mates)] = False  # 給狼隊友發金水
        elif unused:
            self.fake_checks[self.rng.choice(unused)] = self.rng.random() < 0.6

    def wolf_target(self, game: Game, k: Knowledge) -> int | None:
        """狼隊白天想推出局的好人。"""
        good_alive = [p.seat for p in game.alive() if not p.is_wolf]
        if not good_alive:
            return None
        claims = game.seer_claims()
        real = [c for c in claims if c in good_alive]
        if real:
            return real[0]
        fake = game.wolf_plan.get("fake_seer")
        fake_wolves = [t for t, w in claims.get(fake, {}).items() if w and t in good_alive]
        if fake_wolves:
            return fake_wolves[0]
        if game.today:
            accused = [sp.accuse for sp in game.today.speeches if sp.accuse in good_alive]
            if accused:
                return max(set(accused), key=accused.count)
        return max(good_alive, key=lambda s: self.pref[s])

    def vote(self, game: Game, me: Player, candidates: list[int]) -> int | None:
        k = self.analyze(game, me)
        if me.is_wolf:
            key = ("vote", game.night_no)
            if game.wolf_plan.get(key) not in candidates:
                game.wolf_plan[key] = self.wolf_target(game, k)
            target = game.wolf_plan[key]
            if target in candidates:
                return target
            good = [c for c in candidates if c not in k.wolf]
            return self.rng.choice(good) if good else None
        score = self.suspicion(game, me, k)
        return self._top(score, [c for c in candidates if c != me.seat])

    def hunter_shoot(self, game: Game, me: Player) -> int | None:
        k = self.analyze(game, me)
        if me.is_wolf:  # 狼王爪：帶走最有威脅的好人
            good = [p.seat for p in game.alive() if not p.is_wolf]
            claims = game.seer_claims()
            threats = [c for c in claims if c in good] + \
                      [s for s in good if game.claimed_role(s) in (Role.WITCH, Role.DREAMER, Role.MERCHANT)]
            return threats[0] if threats else (self.rng.choice(good) if good else None)
        alive = set(game.alive_seats())
        certain = [s for s in k.wolf if s in alive]
        if certain:
            return certain[0]
        score = self.suspicion(game, me, k)
        top = self._top(score)
        if top is not None and score[top] >= 10:
            return top
        return top if self.rng.random() < 0.4 else None

    # ------------------------------------------------------------ 新角色
    def choose_dream(self, game: Game, me: Player) -> int | None:
        options = [s for s in game.alive_seats() if s != me.seat]
        if not options:
            return None
        k = self.analyze(game, me)
        if game.last_dream in k.wolf and game.last_dream in options:
            return game.last_dream               # 連夢兩晚，把確定的狼夢死
        certain = [s for s in k.wolf if s in options]
        if certain and self.rng.random() < 0.5:
            return certain[0]
        fresh = [s for s in options if s != game.last_dream] or options
        if k.trusted in fresh:
            return k.trusted                     # 保護相信的預言家
        return self.rng.choice(fresh)

    def merchant_trade(self, game: Game, me: Player):
        if game.night_no == 1 and self.rng.random() > 0.85:
            return None
        k = self.analyze(game, me)
        options = [s for s in game.alive_seats() if s != me.seat]
        if not options:
            return None
        score = self.suspicion(game, me, k) if game.night_no > 1 else {}
        target = min(options, key=lambda s: score.get(s, self.pref[s]))
        item = self.rng.choices(["check", "poison", "guard"], [0.7, 0.15, 0.15])[0]
        self.traded = (target, item)
        return target, item

    def on_lucky(self, game: Game, me: Player, item: str) -> None:
        self.item = item

    def lucky_action(self, game: Game, me: Player, item: str) -> int | None:
        k = self.analyze(game, me)
        others = [s for s in game.alive_seats() if s != me.seat]
        if item == "check":
            pool = [s for s in others if s not in self.checks and s not in k.good]
            score = self.suspicion(game, me, k)
            return self._top(score, pool) if pool and game.night_no > 1 else \
                (self.rng.choice(pool) if pool else None)
        if item == "guard":
            return k.trusted if k.trusted in others else self.rng.choice(others)
        certain = [s for s in k.wolf if s in others]
        if certain:
            return certain[0]
        score = self.suspicion(game, me, k)
        top = self._top(score)
        return top if top is not None and score[top] >= 20 else None

    def pass_claw(self, game: Game, me: Player) -> int | None:
        mates = [p.seat for p in game.alive() if p.is_wolf and p.seat != me.seat
                 and p.seat not in game.claw_given]
        if not mates or self.rng.random() > 0.5:
            return None
        fake = game.wolf_plan.get("fake_seer")
        return fake if fake in mates else self.rng.choice(mates)
