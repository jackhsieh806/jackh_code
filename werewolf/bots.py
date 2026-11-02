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
    sheriff_doubt: float = 0.0                          # 我懷疑現任警長是假的程度（0～1）
    sheriff_why: list[str] = field(default_factory=list)  # 懷疑警長的理由
    hints: dict[int, float] = field(default_factory=dict)   # 推理高手公開的漏洞帶來的懷疑
    hint_why: dict[int, str] = field(default_factory=dict)
    hint_from: dict[int, int] = field(default_factory=dict)  # 是哪位推理高手指出的


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
        self.reasons: dict[int, list[tuple[float, str]]] = {}  # 最近一次推理：懷疑每個人的理由

    # ------------------------------------------------------------ 初始化與推理
    def setup(self, game: Game, me: Player) -> None:
        self.rng = game.rng
        self.P = self.personality or DEFAULT
        self.pref = {s: self.rng.random() for s in game.players}
        self.guess_seer_accurate = self.rng.random() < 0.5   # 推不出來時，猜哪張預言家牌是準的
        if me.is_wolf and "fake_seer" not in game.wolf_plan:
            bots = [p.seat for p in game.players.values()
                    if p.is_wolf and not game.controllers[p.seat].is_human]
            # 狼隊開局決定悍跳人選：越愛詐唬的狼越可能被派出去
            weights = [getattr(game.controllers[b], "personality", None) or DEFAULT for b in bots]
            weights = [w.bluff + 0.01 for w in weights]
            fakes: list[int] = []
            if game.claim_race:            # 燈影板四人搶警：固定派兩隻狼悍跳
                pool, w = list(bots), list(weights)
                while pool and len(fakes) < 2:
                    pick = self.rng.choices(pool, weights=w)[0]
                    i = pool.index(pick)
                    fakes.append(pool.pop(i))
                    w.pop(i)
            else:
                chance = min(0.95, 0.6 * (sum(weights) / len(weights))) if bots else 0
                if bots and self.rng.random() < chance:
                    fakes.append(self.rng.choices(bots, weights=weights)[0])
            game.wolf_plan["fake_seers"] = fakes
            game.wolf_plan["fake_seer"] = fakes[0] if fakes else None

    def analyze(self, game: Game, me: Player) -> Knowledge:
        """自己的推理：先整理確定的資訊，再獨立評估警長是不是假的。"""
        k = self._analyze_base(game, me)
        if me.is_wolf:
            return k
        self._absorb_findings(game, me, k)
        k.sheriff_doubt, k.sheriff_why = self._sheriff_doubt(game, me, k)
        sheriff = game.sheriff
        if k.sheriff_doubt >= 0.5 and sheriff is not None:
            k.protected.discard(sheriff)
            if k.trusted == sheriff:   # 不再站警長的邊，改信其他跳預言家的人（或誰都不信）
                others = [c for c in k.claims if c not in k.wolf and c not in (me.seat, sheriff)]
                k.trusted = max(others, key=lambda c: self.pref[c]) if others else None
        return k

    # ------------------------------------------------------------ 推理高手
    def _absorb_findings(self, game: Game, me: Player, k: Knowledge) -> None:
        """參考推理高手公開的漏洞：公開事實推得出來的直接採信，其他的依信任程度參考。"""
        for f in game.findings:
            speaker = f["speaker"]
            if speaker == me.seat or speaker in k.wolf:
                continue
            if f["certain"] and f["public"]:
                if f["liar"] not in k.good:        # 任何人都能自己驗證的邏輯
                    k.wolf.add(f["liar"])
                continue
            trust = 1.0 if speaker in k.good else 0.6
            trust *= 0.6 + 0.25 * self.P.follow    # 越願意聽別人意見的個性越會參考
            weight = (25 if f["certain"] else 12) * trust
            for s in f["suspects"]:
                if s in k.good or s == me.seat:
                    continue
                k.hints[s] = k.hints.get(s, 0) + weight / len(f["suspects"]) * (2 if f["certain"] else 1)
                k.hint_why.setdefault(s, f"推理高手 {speaker}號 指出：{f['text']}")
                k.hint_from.setdefault(s, speaker)

    def find_loopholes(self, game: Game, me: Player, k: Knowledge) -> list[dict]:
        """找出說法裡的邏輯漏洞。public=只靠公開資訊就能驗證；certain=一定有人說謊。"""
        out: list[dict] = []
        players = game.players.values()
        known_good = {p.seat for p in players if p.revealed and not p.is_wolf} | game.knight_gold
        known_wolf = {p.seat for p in players if p.revealed and p.is_wolf}
        cards = (Role.SEER, Role.LANTERN_SEER)

        def add(liar, suspects, text, certain, public=True):
            out.append({"liar": liar, "suspects": tuple(suspects), "text": text,
                        "certain": certain, "public": public})

        for c, cl in game.claims.items():
            if c in known_wolf or c == me.seat:
                continue
            role, checks = cl["role"], cl["checks"]
            if role in cards:                       # 查驗和確定的事實比對
                bad = [(t, w) for t, w in checks.items()
                       if (w and t in known_good) or (not w and t in known_wolf)]
                fine = [(t, w) for t, w in checks.items()
                        if (w and t in known_wolf) or (not w and t in known_good)]
                if bad:
                    t, w = bad[0]
                    said = f"{c}號 說 {t}號 是{'狼' if w else '好人'}，但 {t}號 已經證實是{'好人' if w else '狼'}"
                    if not game.has_lantern:
                        add(c, (c,), said + "，他的查驗是編的", True)
                    elif fine:
                        add(c, (c,), said + "，可是他其他查驗又是準的，時準時反一定是假預言家", True)
                    else:
                        add(None, (c,), said + "，他要嘛是反向查驗，要嘛是假的", False)
                mine = checks.get(me.seat)
                if mine and not game.has_lantern:   # 只有我自己知道的矛盾
                    add(c, (c,), f"{c}號 查殺我，但我是好人，他是假預言家", True, public=False)
                elif mine and game.has_lantern:
                    add(None, (c,), f"{c}號 說我是狼，我是好人，他要嘛是反向查驗要嘛是假的", False, public=False)
            elif role not in (Role.VILLAGER, Role.WEREWOLF):
                real = [p.seat for p in players if p.revealed and p.role is role and p.seat != c]
                if real:                            # 搶已經翻牌的身份
                    add(c, (c,), f"真的{role.value}已經翻牌是 {real[0]}號，{c}號 卻說自己是{role.value}", True)
                if role is Role.HUNTER and not game.players[c].alive \
                        and game.players[c].death_cause in ("vote", "wolf") and not game.players[c].revealed:
                    add(None, (c,), f"{c}號 說自己是獵人，出局時卻沒有開槍", False)

        unique = [r for r in Role if r not in (Role.WEREWOLF, Role.VILLAGER, *cards)]
        for role in unique:                         # 兩個人搶同一個唯一身份
            who = sorted(c for c, cl in game.claims.items() if cl["role"] is role and c != me.seat)
            if len(who) >= 2:
                add(None, who, f"{'、'.join(map(str, who))}號 都說自己是{role.value}，至少有一個在說謊", False)

        if game.has_lantern:                        # 兩張牌驗同一人結果一定相反
            seers, lanterns = game.claims_of(Role.SEER), game.claims_of(Role.LANTERN_SEER)
            for a, ra in seers.items():
                for b, rb in lanterns.items():
                    same = [t for t, w in ra.items() if t in rb and rb[t] == w]
                    if same and me.seat not in (a, b):
                        add(None, (a, b), f"{a}號（預言家）和 {b}號（燈影預言家）驗 {same[0]}號 結果一樣，"
                                          "兩張牌的結果一定相反，他們至少一個是假的", False)

        if game.sheriff is not None and game.badge_from.get(game.sheriff) in known_wolf:
            src = game.badge_from[game.sheriff]
            add(None, (game.sheriff,), f"警長 {game.sheriff}號 的警徽是狼（{src}號）交給他的", False)

        for p in game.alive():                      # 票型：每次都和翻牌的狼投同一個人
            if p.seat == me.seat or p.seat in known_wolf:
                continue
            together = total = 0
            for d in game.days:
                mine = d.votes.get(p.seat)
                wolf_targets = {d.votes.get(w) for w in known_wolf if d.votes.get(w) is not None}
                if mine is not None and wolf_targets:
                    total += 1
                    together += mine in wolf_targets
            if total >= 2 and together == total:
                add(None, (p.seat,), f"{p.seat}號 每次都和已翻牌的狼投同一個人", False)

        told = {(f["text"]) for f in game.findings}
        return [f for f in out if f["text"] not in told]

    def _add_findings(self, game: Game, me: Player, speech: Speech) -> None:
        """推理高手在發言裡公開新發現的漏洞（一次最多兩個），並歸票確定說謊的人。"""
        k = self.analyze(game, me)
        found = self.find_loopholes(game, me, k)
        found.sort(key=lambda f: (not f["certain"], not f["public"]))
        found = found[:2]
        if not found:
            return
        speech.findings = found
        speech.text += "；我發現邏輯漏洞：" + "；".join(f["text"] for f in found)
        liars = [f["liar"] for f in found if f["certain"] and f["liar"] is not None
                 and game.players[f["liar"]].alive]
        if liars:
            speech.accuse = liars[0]

    def _sheriff_doubt(self, game: Game, me: Player, k: Knowledge) -> tuple[float, list[str]]:
        """獨立評估現任警長是假的（狼）的可能性，回傳 (0～1 的懷疑度, 理由)。"""
        s = game.sheriff
        if s is None or s == me.seat or not game.players[s].alive:
            return 0.0, []
        if s in k.wolf:
            return 1.0, ["他已經確定是狼"]
        if s in k.good:
            return 0.0, []
        doubt, why = 0.0, []
        claim = game.claimed_role(s)
        if claim is not None:
            rivals = [c for c, cl in game.claims.items() if c != s and cl["role"] is claim]
            if rivals:
                doubt += 0.25
                why.append(f"{rivals[0]}號 和他對跳{claim.value}")
        if claim in (Role.SEER, Role.LANTERN_SEER):
            for t, w in game.claims[s]["checks"].items():
                if (w and t in k.good) or (not w and t in k.wolf):
                    doubt += 0.3 if game.has_lantern else 0.6
                    why.append(f"他說 {t}號 是{'狼' if w else '好人'}，但 {t}號 其實是{'好人' if w else '狼'}"
                               + ("（也可能只是反向查驗）" if game.has_lantern else ""))
            claimed_day = game.claims[s].get("day", game.night_no)
            quiet = game.night_no - claimed_day
            if quiet >= 2:                      # 真預言家通常很快被刀
                doubt += min(0.3, 0.1 * (quiet - 1))
                why.append(f"他跳預言家 {quiet} 晚都沒被狼刀")
        hits = set()
        for d in game.days:
            for sp in d.speeches:
                if sp.seat == s and sp.accuse in k.good:   # 包含點名我自己
                    hits.add(sp.accuse)
            for votes in (d.votes, d.pk_votes):
                if votes.get(s) in k.good:
                    hits.add(votes[s])
        if hits:
            doubt += min(0.45, 0.2 * len(hits))
            who = "我" if hits == {me.seat} else "、".join(f"{h}號" for h in sorted(hits))
            why.append(f"他點名或投票給確定的好人（{who}）")
        backers = [v for v, t in game.sheriff_votes.items() if t == s]
        wolf_backers = [v for v in backers if v in k.wolf]
        if wolf_backers:
            doubt += 0.1 + 0.4 * len(wolf_backers) / len(backers)
            why.append(f"投他當警長的人裡有確定的狼（{'、'.join(map(str, wolf_backers))}號）")
        if game.badge_from.get(s) in k.wolf:
            doubt += 0.5
            why.append(f"他的警徽是狼（{game.badge_from[s]}號）交給他的")
        # 個性：邏輯型最看證據、保守型比較相信警長；直覺強的人會多一點「說不上來的懷疑」
        doubt = doubt * self.P.evidence / (1 + 0.15 * max(0.0, self.P.follow - 1.5))
        doubt += self.pref[s] * 0.03 * self.P.intuition
        return min(doubt, 1.0), why

    def _analyze_base(self, game: Game, me: Player) -> Knowledge:
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
        """燈影預言家板：兩位真預言家一位正確、一位反向查驗，可能還有狼悍跳。

        列舉「哪兩個人是真預言家（每張牌各一人）、哪一位是準的」的所有組合，
        用確定的事實排除不可能的，再挑最可能的一組。四人搶警時每張牌都有一真一假。"""
        cards = (Role.SEER, Role.LANTERN_SEER)
        mycard = me.role if me.role in cards else None
        for t, w in self.checks.items():          # 幸運兒等其他確定查驗（本板沒有，保留通用性）
            (wolf if w else good).add(t)
        reports = {c: dict(cl["checks"]) for c, cl in game.claims.items()
                   if cl["role"] in cards and c != me.seat}
        card_of = {c: game.claims[c]["role"] for c in reports}
        if mycard:
            reports[me.seat], card_of[me.seat] = dict(self.raw), mycard
            wolf |= {c for c in reports if c != me.seat and card_of[c] is mycard}   # 跳我這張牌的一定是狼
        acc_p: dict[int, bool] = {}                # 從事實推出某人「準 / 反」
        for c, rep in reports.items():
            flags = {(not shown) if t in good else shown for t, shown in rep.items() if t in good or t in wolf}
            if len(flags) == 2 and c != me.seat:
                wolf.add(c)                        # 有時準、有時反 → 不可能是真預言家
            elif flags:
                acc_p[c] = flags.pop()
        cands = [c for c in reports if c not in wolf]

        hypotheses = []                            # (分數, a, b, a 是否準確)
        for i, a in enumerate(cands):
            for b in cands[i + 1:]:
                if mycard and me.seat not in (a, b):
                    continue                       # 我自己一定是真預言家之一
                if card_of[a] is card_of[b]:
                    continue                       # 兩張牌各一人
                if any(t in reports[b] and reports[b][t] == w for t, w in reports[a].items()):
                    continue                       # 真的兩位驗同一個人，結果一定相反
                # 假設 a、b 是真的：他們是好人，其他跳預言家的人都是狼
                implied = {c: c not in (a, b) for c in reports}
                for acc_a in (True, False):
                    if acc_p.get(a, acc_a) != acc_a or acc_p.get(b, not acc_a) != (not acc_a):
                        continue
                    fits = 0
                    for m, acc in ((a, acc_a), (b, not acc_a)):
                        for t, shown in reports[m].items():
                            if t in implied:       # 準的人驗狼看到狼、反的人看到好人；不符就排除
                                fits += 1 if shown == (implied[t] if acc else not implied[t]) else -100
                    if fits < 0:
                        continue
                    night_dead = sum(not game.players[m].alive and game.players[m].death_cause
                                     in ("wolf", "poison", "dream") for m in (a, b))
                    score = (self.pref[a] + self.pref[b] + 3 * fits + 3 * night_dead
                             + (10 if a in acc_p or b in acc_p else 0))
                    seer_card_acc = acc_a if card_of[a] is Role.SEER else not acc_a
                    if seer_card_acc == self.guess_seer_accurate:
                        score += 0.5               # 推不出來時，照自己的猜測
                    hypotheses.append((score, a, b, acc_a))
        holders: dict[int, bool | None] = {}       # 我認為的真預言家 -> 是否準確（None = 不確定）
        if hypotheses:
            _, a, b, acc_a = max(hypotheses)
            known = a in acc_p or b in acc_p
            holders = {a: acc_a, b: not acc_a}
            if len({frozenset(h[1:3]) for h in hypotheses}) == 1:
                wolf |= {c for c in cands if c not in holders}   # 只剩這一組可能 → 其他跳預言家的都是狼
            certain = {a: known, b: known}
        else:                                      # 只有一個人（或沒有人）可能是真的
            for c in cands:
                guess = self.guess_seer_accurate if card_of[c] is Role.SEER else not self.guess_seer_accurate
                holders[c] = acc_p.get(c, guess)
            certain = {c: c in acc_p for c in cands}
        if mycard and holders.get(me.seat) is not None and certain.get(me.seat):
            for t, shown in self.raw.items():      # 確定自己準不準 → 自己的查驗變成確定資訊
                (wolf if (shown if holders[me.seat] else not shown) else good).add(t)
        evidence: dict[int, float] = {}
        for c, acc in holders.items():
            if c == me.seat and certain.get(c):
                continue
            weight = 20 if certain.get(c) else 8
            for t, shown in reports[c].items():
                truth = shown if acc else not shown
                evidence[t] = evidence.get(t, 0) + (weight if truth else -weight / 2)
        acc_card: dict = {}
        for c, acc in holders.items():             # 換算成「哪張牌準」：自己的牌一定知道是哪張
            if certain.get(c):
                acc_card[card_of[c]] = acc
                acc_card[cards[1] if card_of[c] is cards[0] else cards[0]] = not acc
        protected = {c for c in holders if c != me.seat}
        accurate = [c for c, acc in holders.items() if acc and c != me.seat]
        trusted = (accurate or sorted(protected) or [None])[0]
        return Knowledge(good, wolf, trusted, claims, evidence, protected, acc_card)

    def suspicion(self, game: Game, me: Player, k: Knowledge) -> dict[int, float]:
        """每個人的懷疑度；同時把主要理由記在 self.reasons，發言時說出來。"""
        today = game.today
        base: dict[int, float] = {}
        self.reasons = {}

        def why(seat: int, weight: float, text: str) -> None:
            if weight > 0:
                self.reasons.setdefault(seat, []).append((weight, text))

        for p in game.players.values():
            s = p.seat
            if s == me.seat:
                continue
            v = self.pref[s] * self.P.intuition
            why(s, v * 0.5, "直覺覺得他怪怪的")
            if s in k.wolf:
                v += 100
                why(s, 100, "他已經確定是狼")
            if s in k.good:
                v -= 100
            if k.evidence is not None:            # 燈影預言家板
                e = k.evidence.get(s, 0) * self.P.evidence
                v += e
                why(s, e, "預言家的查驗對他不利（不確定哪張牌準）")
                if s in k.protected:
                    v -= 15
                elif game.claimed_role(s) in (Role.SEER, Role.LANTERN_SEER):
                    v += 10                       # 和看起來是真的預言家對跳
                    why(s, 10, "他和我比較相信的預言家對跳")
            elif k.trusted is not None:
                checks = k.claims.get(k.trusted, {})
                if s in checks:
                    v += (20 if checks[s] else -8) * self.P.evidence
                    if checks[s]:
                        why(s, 20 * self.P.evidence, f"{k.trusted}號 預言家查殺他")
                if s == k.trusted:
                    v -= 15
                elif s in k.claims:
                    v += 10  # 和我相信的預言家對跳
                    why(s, 10, f"他和 {k.trusted}號 預言家對跳")
            if s == game.sheriff and k.sheriff_doubt:
                v += k.sheriff_doubt * 40
                why(s, k.sheriff_doubt * 40,
                    "他這個警長很可疑" + (f"（{k.sheriff_why[0]}）" if k.sheriff_why else ""))
            if game.claimed_role(s) in CLAIMABLE:
                v -= 3
            ev = self.P.evidence
            pattern = 0.0
            for d in game.days:  # 看票型與發言：攻擊可信的人很可疑（越重證據的個性越看重）
                for sp in d.speeches:
                    if sp.seat == s and sp.accuse is not None:
                        if sp.accuse in k.good or sp.accuse == k.trusted:
                            pattern += 5 * ev
                        elif sp.accuse in k.wolf:
                            pattern -= 2 * ev
                if d is today:
                    continue
                for votes in (d.votes, d.pk_votes):
                    tgt = votes.get(s)
                    if tgt in k.good or (tgt is not None and tgt == k.trusted):
                        pattern += 5 * ev
                    elif tgt in k.wolf:
                        pattern -= 3 * ev
            v += pattern
            why(s, pattern, "他的發言和票型一直針對可信的人")
            v += self.soft.get(s, 0)
            why(s, self.soft.get(s, 0), "村姑查驗的線索指向他")
            v += k.hints.get(s, 0)
            why(s, k.hints.get(s, 0), k.hint_why.get(s, ""))
            base[s] = v

        # 今天的指認：只採信「我不懷疑的人」說的話
        score = {s: v for s, v in base.items() if game.players[s].alive}
        if today:
            for sp in today.speeches:
                if sp.accuse in score and sp.seat != me.seat and base.get(sp.seat, -99) < 8:
                    w = (3 if sp.seat == k.trusted else 1.5) * self.P.follow / 1.5
                    score[sp.accuse] += w
                    why(sp.accuse, w, "不少我信得過的人也點他")
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
        detectives = sorted({f["speaker"] for f in game.findings if f["speaker"] in good})
        for group in (real_seers, detectives, witches, golds):   # 公開找漏洞的推理高手也很危險
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
        if game.claim_race:                 # 四人搶警：優先驗和自己對跳的人
            rivals = [c for c in pool if game.claimed_role(c) in (Role.SEER, Role.LANTERN_SEER)]
            if rivals:
                return self.rng.choice(rivals)
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
        speech = self._speech(game, me, last=False)
        if self.P.detective and not me.is_wolf:
            self._add_findings(game, me, speech)
        return speech

    def last_words(self, game: Game, me: Player) -> Speech:
        speech = self._speech(game, me, last=True)
        if self.P.detective and not me.is_wolf:
            self._add_findings(game, me, speech)
        return speech

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
        text = f"{self.P.opener}，{text}"
        if top is not None:
            text += f"；我懷疑 {top}號：{self.explain(top)}"
            if top in k.hint_from and not self.P.detective and k.hint_why[top] not in text:
                text += f"（我參考了推理高手 {k.hint_from[top]}號 的分析）"
        text += self._sheriff_comment(game, k, top)
        return Speech(me.seat, accuse=top, text=text)

    def explain(self, seat: int, n: int = 2) -> str:
        """說出懷疑某人的主要理由（最多 n 個）。"""
        items = sorted(self.reasons.get(seat, []), reverse=True)
        texts = [t for w, t in items if w >= 3][:n] or [t for _, t in items[:1]]
        return "、".join(texts) if texts else "說不上來，先聽聽大家"

    def _sheriff_comment(self, game: Game, k: Knowledge, accused: int | None) -> str:
        s = game.sheriff
        if s is None or s == accused or not game.players[s].alive or not k.sheriff_why:
            return ""
        if k.sheriff_doubt >= 0.5:
            return f"；我懷疑警長 {s}號 是假的：{'、'.join(k.sheriff_why[:2])}"
        if k.sheriff_doubt >= 0.3:
            return f"；警長 {s}號 我還在觀察：{k.sheriff_why[0]}"
        return ""

    # ------------------------------------------------------------ 狼人白天策略
    def _wolf_speech(self, game: Game, me: Player, k: Knowledge, last: bool) -> Speech:
        good_alive = [p.seat for p in game.alive() if not p.is_wolf]
        fakes = game.wolf_plan.get("fake_seers", ())
        if me.seat in fakes:
            # 四人搶警：第一隻悍跳預言家、第二隻悍跳燈影預言家，每張牌都有人對跳
            card = Role.LANTERN_SEER if game.claim_race and fakes.index(me.seat) == 1 else Role.SEER
            if game.night_no not in self.fake_days and not (last and self.fake_checks):
                self.fake_days.add(game.night_no)
                self._invent_check(game, me, k, good_alive, card)
            rivals = [c for c in game.claims_of(card) if c != me.seat and game.players[c].alive]
            fake_wolves = [t for t, w in self.fake_checks.items() if w and game.players[t].alive]
            others = [s for s in good_alive if s not in self.fake_checks]   # 不點自己發的金水
            accuse = (fake_wolves or rivals or others or [None])[0]
            text = f"我才是真的{card.value}，對跳的是狼" if rivals else ""
            return Speech(me.seat, card, dict(self.fake_checks), accuse, text)

        target = self.wolf_target(game, k)
        if last:
            return Speech(me.seat, Role.VILLAGER, accuse=target, text="你們出錯人了")
        if self._accused_today(game, me) and self.rng.random() < min(1, 0.25 * self.P.bluff):
            return Speech(me.seat, Role.HUNTER, accuse=target, text="出我的話我會開槍")  # 假跳獵人
        fake = game.wolf_plan.get("fake_seer")
        text = f"我站 {fake}號 預言家" if fake and game.players[fake].alive else "我是平民"
        return Speech(me.seat, accuse=target, text=f"{self.P.opener}，{text}")

    def _invent_check(self, game: Game, me: Player, k: Knowledge, good_alive: list[int],
                      card: Role = Role.SEER) -> None:
        unused = [s for s in good_alive if s not in self.fake_checks and not game.players[s].revealed]
        rivals = [c for c in game.claims_of(card) if c in unused]   # 對同一張牌的真預言家發查殺
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
        if game.claim_race and me.role in (Role.SEER, Role.LANTERN_SEER) and self.raw:
            return True                             # 四人搶警：兩位真預言家一定上警
        if me.role is Role.SEER and self.checks:
            return self.rng.random() < 0.9          # 真預言家上警拿警徽
        if me.is_wolf and me.seat in game.wolf_plan.get("fake_seers", ()):
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
            if game.claim_race:
                return False                     # 四人搶警：讓兩隻悍跳狼完整跟真預言家對跳
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
