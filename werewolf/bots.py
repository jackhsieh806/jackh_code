"""電腦玩家的決策邏輯。

電腦玩家只會使用「它的身份應該知道的資訊」：
  * 好人：自己的身份、公開發言、票型、公開翻牌（白痴、獵人）；預言家另外知道自己的查驗。
  * 狼人：知道所有狼隊友。
推理重點是「找矛盾」：例如有人跳預言家說我是狼，但我知道自己是好人 → 他一定是假預言家。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .engine import ITEMS, Controller, Game, Player, Speech
from .personality import DEFAULT, Personality
from .roles import Role


CLAIMABLE = (Role.HUNTER, Role.WITCH, Role.IDIOT, Role.DREAMER, Role.MERCHANT, Role.KNIGHT,
             Role.VILLAGE_GIRL)


@dataclass
class Knowledge:
    good: set[int]                     # 確定是好人
    wolf: set[int]                     # 確定是狼人
    trusted: int | None                # 選擇相信的預言家
    claims: dict[int, dict[int, bool]]  # 所有跳預言家的人與其查驗
    # 燈影預言家板：兩張預言家牌的查驗都不確定，改用加權的線索
    evidence: dict[int, float] | None = None
    protected: set[int] = field(default_factory=set)   # 看起來是真的兩位預言家
    card_acc: dict = field(default_factory=dict)        # {Role.SEER / Role.LANTERN_SEER: 是否正確查驗}


class BotController(Controller):
    def __init__(self, personality: Personality | None = None) -> None:
        self.personality = personality          # 沒指定時由 Game 開局分配
        self.checks: dict[int, bool] = {}       # 真預言家的查驗
        self.fake_checks: dict[int, bool] = {}  # 悍跳狼編的查驗
        self.fake_days: set[int] = set()
        self.pref: dict[int, float] = {}        # 對每個人的「直覺」，用來打破平手
        self.saved: int | None = None           # 女巫救過的人（銀水）
        self.item: str | None = None            # 幸運兒拿到的道具
        self.traded: tuple[int, str] | None = None  # 奇蹟商人交易紀錄
        self.girl_seen: tuple[int, bool, bool] | None = None  # 村姑：(目標, 看到狼?, 確定準確?)
        self.soft: dict[int, float] = {}        # 不確定的線索（村姑猜測的結果）
        self.raw: dict[int, bool] = {}          # 燈影預言家板：自己看到的查驗（可能是反的）

    # ------------------------------------------------------------ 初始化與推理
    def setup(self, game: Game, me: Player) -> None:
        self.rng = game.rng
        self.P = self.personality or DEFAULT
        self.pref = {s: self.rng.random() for s in game.players}
        self.guess_seer_accurate = self.rng.random() < 0.5   # 推不出來時，猜哪張預言家牌是準的
        if me.is_wolf and "fake_seer" not in game.wolf_plan:
            bots = [p.seat for p in game.players.values()
                    if p.is_wolf and not game.controllers[p.seat].is_human]
            # 狼隊開局決定要不要派一隻狼悍跳預言家：越愛詐唬的狼越可能被派出去
            weights = [getattr(game.controllers[b], "personality", None) or DEFAULT for b in bots]
            weights = [w.bluff for w in weights]
            chance = min(0.95, 0.6 * (sum(weights) / len(weights))) if bots else 0
            game.wolf_plan["fake_seer"] = (
                self.rng.choices(bots, weights=[w + 0.01 for w in weights])[0]
                if bots and self.rng.random() < chance else None)

    def analyze(self, game: Game, me: Player) -> Knowledge:
        claims = game.seer_claims()
        if me.is_wolf:
            wolves = {p.seat for p in game.players.values() if p.is_wolf}
            return Knowledge(set(game.players) - wolves, wolves, None, claims)

        revealed = [p for p in game.players.values() if p.revealed]
        good = {me.seat} | {p.seat for p in revealed if not p.is_wolf} | game.knight_gold
        wolf: set[int] = {p.seat for p in revealed if p.is_wolf}  # 翻牌的狼王
        if game.has_lantern:
            return self._lantern_analyze(game, me, good, wolf, claims)
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

    def _lantern_analyze(self, game: Game, me: Player, good: set[int], wolf: set[int],
                         claims: dict[int, dict[int, bool]]) -> Knowledge:
        """燈影預言家板：兩張預言家牌一張正確、一張反向，用確定的事實反推哪張是準的。"""
        cards = (Role.SEER, Role.LANTERN_SEER)
        mycard = me.role if me.role in cards else None
        for t, w in self.checks.items():          # 幸運兒等其他確定查驗（本板沒有，保留通用性）
            (wolf if w else good).add(t)
        if mycard:                                 # 跳我這張牌的其他人一定是狼
            wolf |= {c for c in game.claims_of(mycard) if c != me.seat}
        holder: dict[Role, int | None] = {}
        reports: dict[Role, dict[int, bool]] = {}
        for card in cards:
            if card is mycard:
                holder[card], reports[card] = me.seat, dict(self.raw)
                continue
            cands = [c for c in game.claims_of(card) if c not in wolf and c != me.seat]
            holder[card] = max(cands, key=lambda c: self.pref[c]) if cands else None
            reports[card] = game.claims_of(card).get(holder[card], {}) if holder[card] else {}
        acc: dict[Role, bool | None] = {c: None for c in cards}
        for card in cards:                         # 報出的結果和確定的事實比對
            for t, shown in reports[card].items():
                if t in good:
                    acc[card] = not shown
                elif t in wolf:
                    acc[card] = shown
        for a, b in (cards, cards[::-1]):          # 一張準，另一張就一定是反的
            if acc[a] is None and acc[b] is not None:
                acc[a] = not acc[b]
        if mycard and acc[mycard] is not None:     # 知道自己準不準 → 自己的查驗變成確定資訊
            for t, shown in self.raw.items():
                (wolf if (shown if acc[mycard] else not shown) else good).add(t)
        evidence: dict[int, float] = {}
        for card in cards:
            if card is mycard and acc[card] is not None:
                continue
            a = acc[card]
            weight = 20 if a is not None else 8
            if a is None:
                a = self.guess_seer_accurate if card is Role.SEER else not self.guess_seer_accurate
            for t, shown in reports[card].items():
                truth = shown if a else not shown
                evidence[t] = evidence.get(t, 0) + (weight if truth else -weight / 2)
        protected = {h for h in holder.values() if h is not None and h != me.seat}
        trusted = holder[Role.SEER] if holder[Role.SEER] != me.seat else None
        return Knowledge(good, wolf, trusted, claims, evidence, protected, acc)

    def suspicion(self, game: Game, me: Player, k: Knowledge) -> dict[int, float]:
        today = game.today
        base: dict[int, float] = {}
        for p in game.players.values():
            s = p.seat
            if s == me.seat:
                continue
            v = self.pref[s] * self.P.intuition
            if s in k.wolf:
                v += 100
            if s in k.good:
                v -= 100
            if k.evidence is not None:            # 燈影預言家板
                v += k.evidence.get(s, 0) * self.P.evidence
                if s in k.protected:
                    v -= 15
                elif game.claimed_role(s) in (Role.SEER, Role.LANTERN_SEER):
                    v += 10                       # 和看起來是真的預言家對跳
            elif k.trusted is not None:
                checks = k.claims.get(k.trusted, {})
                if s in checks:
                    v += (20 if checks[s] else -8) * self.P.evidence
                if s == k.trusted:
                    v -= 15
                elif s in k.claims:
                    v += 10  # 和我相信的預言家對跳
            if game.claimed_role(s) in CLAIMABLE:
                v -= 3
            ev = self.P.evidence
            for d in game.days:  # 看票型與發言：攻擊可信的人很可疑（越重證據的個性越看重）
                for sp in d.speeches:
                    if sp.seat == s and sp.accuse is not None:
                        if sp.accuse in k.good or sp.accuse == k.trusted:
                            v += 5 * ev
                        elif sp.accuse in k.wolf:
                            v -= 2 * ev
                if d is today:
                    continue
                for votes in (d.votes, d.pk_votes):
                    tgt = votes.get(s)
                    if tgt in k.good or (tgt is not None and tgt == k.trusted):
                        v += 5 * ev
                    elif tgt in k.wolf:
                        v -= 3 * ev
            v += self.soft.get(s, 0)
            base[s] = v

        # 今天的指認：只採信「我不懷疑的人」說的話
        score = {s: v for s, v in base.items() if game.players[s].alive}
        if today:
            for sp in today.speeches:
                if sp.accuse in score and sp.seat != me.seat and base.get(sp.seat, -99) < 8:
                    score[sp.accuse] += (3 if sp.seat == k.trusted else 1.5) * self.P.follow / 1.5
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
        real_seers = [c for c in claims if c in good] + \
                     [c for c in game.claims_of(Role.LANTERN_SEER) if c in good]
        witches = [s for s in good if game.claimed_role(s) is Role.WITCH]
        golds = [t for c in real_seers for t, w in game.claims.get(c, {}).get("checks", {}).items()
                 if not w and t in good]
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
            if top is not None and score[top] >= self.P.poison_bar and self.rng.random() < self.P.poison_prob:
                return "poison", top
        return None, None

    def choose_check(self, game: Game, me: Player) -> int | None:
        options = game.check_options(me)   # 可能被虎姑婆誘導限制
        pool = [s for s in options if s not in self.checks and s not in self.raw] or options
        if not pool:
            return None
        if game.night_no > 1 and self.rng.random() < 0.6:
            score = self.suspicion(game, me, self.analyze(game, me))
            return self._top(score, pool)
        return self.rng.choice(pool)

    def on_check_result(self, game: Game, me: Player, target: int, is_wolf: bool) -> None:
        if game.has_lantern and me.role in (Role.SEER, Role.LANTERN_SEER):
            self.raw[target] = is_wolf     # 不知道自己準不準，先記下看到的結果
        else:
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

        if game.has_lantern and me.role in (Role.SEER, Role.LANTERN_SEER) and self.raw:
            acc = k.card_acc.get(me.role)
            alive_wolves = [t for t in k.wolf if game.players[t].alive and t != me.seat]
            if acc is None:
                text = "我不知道自己是正確還是反向查驗，大家一起對資訊"
            else:
                text = "我確定我是正確查驗" if acc else "我是反向查驗，結果要反過來看"
            return Speech(me.seat, me.role, dict(self.raw), (alive_wolves or [top])[0], text)
        if me.role is Role.SEER:
            already = game.claimed_role(me.seat) is Role.SEER
            if self.checks and (last or already or any(self.checks.values())
                                or k.claims or self.rng.random() < self.P.claim):
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

        if me.role is Role.VILLAGE_GIRL and self.girl_seen:
            t, shown, sure = self.girl_seen
            note = "" if sure else "（不確定準不準）"
            alive_wolf = t if (t in k.wolf or (not sure and self.soft.get(t, 0) > 0)) \
                and game.players[t].alive else None
            return Speech(me.seat, Role.VILLAGE_GIRL, accuse=alive_wolf or top,
                          text=f"我驗了 {t}號，看到{'狼人' if shown else '好人'}{note}")
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
        if top is not None and score[top] < self.P.accuse_bar:
            top = None                           # 沒把握就不點名
        return Speech(me.seat, accuse=top, text=f"{self.P.opener}，{text}")

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
        if self._accused_today(game, me) and self.rng.random() < min(1, 0.25 * self.P.bluff):
            return Speech(me.seat, Role.HUNTER, accuse=target, text="出我的話我會開槍")  # 假跳獵人
        fake = game.wolf_plan.get("fake_seer")
        text = f"我站 {fake}號 預言家" if fake and game.players[fake].alive else "我是平民"
        return Speech(me.seat, accuse=target, text=f"{self.P.opener}，{text}")

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
        top = self._top(score, [c for c in candidates if c != me.seat])
        if top is not None and score[top] < self.P.vote_bar:
            return None                          # 沒有夠可疑的人：保守的玩家會棄票
        return top

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
        if top is not None and score[top] >= self.P.shoot_bar:
            return top
        return top if self.rng.random() < self.P.blind_shoot else None

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

    # ------------------------------------------------------------ 警長與自爆
    def run_for_sheriff(self, game: Game, me: Player) -> bool:
        if me.role is Role.SEER and self.checks:
            return self.rng.random() < 0.9          # 真預言家上警拿警徽
        if me.is_wolf and game.wolf_plan.get("fake_seer") == me.seat:
            return True                             # 悍跳狼一定上警搶警徽
        return self.rng.random() < self.P.run_sheriff + (0.05 if me.is_wolf else 0)

    def sheriff_vote(self, game: Game, me: Player, candidates: list[int]) -> int | None:
        k = self.analyze(game, me)
        if me.is_wolf:
            wolves = [c for c in candidates if c in k.wolf]
            if wolves:
                return wolves[0]
            real = set(game.seer_claims())
            safe = [c for c in candidates if c not in real]
            return self.rng.choice(safe) if safe else None
        if k.trusted in candidates:
            return k.trusted
        score = self.suspicion(game, me, k)
        pool = [c for c in candidates if c != me.seat]
        return min(pool, key=lambda c: score.get(c, self.pref[c])) if pool else None

    def pass_badge(self, game: Game, me: Player) -> int | None:
        alive = [s for s in game.alive_seats() if s != me.seat]
        if not alive:
            return None
        k = self.analyze(game, me)
        if me.is_wolf:
            mates = [s for s in alive if s in k.wolf]
            return self.rng.choice(mates) if mates and self.rng.random() < 0.6 else None
        good = [s for s in alive if s in k.good]
        if k.trusted in alive:
            return k.trusted
        if good:
            return good[0]
        score = self.suspicion(game, me, k)
        best = min(alive, key=lambda s: score.get(s, 0))
        return best if score.get(best, 0) < self.P.tear_bar else None   # 沒把握就撕警徽

    def choose_direction(self, game: Game, me: Player) -> str:
        return self.rng.choice(["left", "right"])

    def self_explode(self, game: Game, me: Player) -> bool:
        wolves_alive = sum(p.is_wolf for p in game.alive())
        if wolves_alive < 2 or game.night_no > 1 and self.rng.random() < 0.5:
            return False
        claims = game.seer_claims()
        real = [c for c in claims if not game.players[c].is_wolf]
        if game.phase == "election":
            # 真預言家已經在警上報出查驗，自爆打斷，不讓他拿到警徽
            spoke = {sp.seat for sp in game.today.speeches}
            return any(c in spoke for c in real) and self.rng.random() < 0.2 * self.P.explode
        # 被真預言家查殺、今天很可能被投出去 → 自爆跳過投票，保留隊友
        exposed = any(claims[c].get(me.seat) for c in real if game.players[c].alive)
        return exposed and self.rng.random() < 0.3 * self.P.explode

    # ------------------------------------------------------------ 村姑與虎姑婆
    def choose_model(self, game: Game, me: Player) -> int | None:
        return self.rng.choice([s for s in game.alive_seats() if s != me.seat])

    def choose_charm(self, game: Game, me: Player) -> int | None:
        good = [p.seat for p in game.alive() if not p.is_wolf and p.seat != game.last_charm]
        if not good:
            return None
        claims = game.seer_claims()
        threats = [c for c in claims if c in good] + \
                  [s for s in good if game.claimed_role(s) in (Role.WITCH, Role.KNIGHT, Role.VILLAGE_GIRL)]
        return threats[0] if threats and self.rng.random() < 0.7 else self.rng.choice(good)

    def choose_lure(self, game: Game, me: Player, centers: list[int]) -> int | None:
        if self.rng.random() < 0.2:
            return None
        wolves = {p.seat for p in game.alive() if p.is_wolf}
        best = min(len(game._ring(c) & wolves) for c in centers)
        return self.rng.choice([c for c in centers if len(game._ring(c) & wolves) == best])

    def girl_check(self, game: Game, me: Player, options: list[int]) -> int | None:
        k = self.analyze(game, me)
        pool = [s for s in options if s not in k.good and s not in k.wolf] or options
        score = self.suspicion(game, me, k)
        return self._top(score, pool) if game.night_no > 1 else self.rng.choice(pool)

    def on_girl_result(self, game: Game, me: Player, target: int, shown_wolf: bool) -> None:
        """村姑只知道自己投給誰；投票對象身份確定時才能判斷結果準不準。"""
        k = self.analyze(game, me)
        basis = game.sheriff_votes.get(me.seat)
        via_sheriff = basis is not None
        if not via_sheriff:
            for d in reversed(game.days):
                basis = d.pk_votes.get(me.seat) or d.votes.get(me.seat)
                if basis is not None:
                    break
        if basis in k.good or basis in k.wolf:
            correct = (basis in k.wolf) == via_sheriff
            truth = shown_wolf if correct else not shown_wolf
            self.checks[target] = truth
            self.girl_seen = (target, shown_wolf, True)
        else:
            # 不確定：投票對象多半是好人 → 警長票結果相反、放逐票結果正確
            guess = shown_wolf if not via_sheriff else not shown_wolf
            self.soft[target] = 12 if guess else -6
            self.girl_seen = (target, shown_wolf, False)

    def knight_duel(self, game: Game, me: Player) -> int | None:
        k = self.analyze(game, me)
        alive = set(game.alive_seats()) - {me.seat}
        certain = [s for s in k.wolf if s in alive]
        if certain:
            return certain[0]
        if game.night_no >= 2 and k.evidence is not None:
            strong = [t for t, v in k.evidence.items() if v >= 20 and t in alive]
            if strong and self.rng.random() < self.P.duel_prob:
                return strong[0]
        elif game.night_no >= 2 and k.trusted is not None:
            checked = [t for t, w in k.claims.get(k.trusted, {}).items() if w and t in alive]
            if checked and self.rng.random() < self.P.duel_prob:
                return checked[0]
        if game.night_no >= 2 and self.P.duel_guess and self.rng.random() < self.P.duel_guess:
            score = self.suspicion(game, me, k)
            top = self._top(score, list(alive))
            if top is not None and score[top] >= 12:
                return top                       # 積極型：只憑懷疑也敢決鬥
        return None
