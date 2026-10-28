"""真人玩家（鍵盤輸入）的 Controller。"""
from __future__ import annotations

from .engine import ITEMS, Controller, Game, Player, Speech
from .roles import ROLE_DESCRIPTIONS, Role


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        print("\n再見！")
        raise SystemExit(0)


def ask_seat(prompt: str, valid: list[int], allow_none: bool = True) -> int | None:
    """輸入座位號碼；0 或空白代表不選（若允許）。"""
    hint = "、".join(map(str, valid))
    while True:
        raw = ask(f"{prompt}（可選：{hint}{'；0=不選' if allow_none else ''}）> ")
        if allow_none and raw in ("", "0"):
            return None
        if raw.isdigit() and int(raw) in valid:
            return int(raw)
        print("  ⚠️ 輸入不正確，請再試一次。")


def ask_yes(prompt: str) -> bool:
    return ask(f"{prompt}（y/n）> ").lower() in ("y", "yes", "是", "1")


class HumanController(Controller):
    is_human = True

    def __init__(self) -> None:
        self.checks: dict[int, bool] = {}

    def setup(self, game: Game, me: Player) -> None:
        print("\n" + "=" * 50)
        print(f"🎴 你是 {me.seat}號，身份：【{me.role.value}】（{me.role.team.value}）")
        print(f"   {ROLE_DESCRIPTIONS[me.role]}")
        if me.is_wolf:
            mates = [p.seat for p in game.players.values() if p.is_wolf and p.seat != me.seat]
            print(f"   你的狼隊友：{'、'.join(map(str, mates)) or '無'}號")
            kings = [f"{p.seat}號({p.role.value})" for p in game.players.values()
                     if p.is_wolf and p.role is not Role.WEREWOLF and p.seat != me.seat]
            if kings:
                print(f"   隊友中的特殊狼：{'、'.join(kings)}")
        print("=" * 50)

    def _alive_hint(self, game: Game) -> None:
        if game.phase != "election":
            print(f"  存活玩家：{'、'.join(map(str, game.alive_seats()))}")

    # ------------------------------------------------------------ 夜晚
    def choose_guard(self, game: Game, me: Player) -> int | None:
        print(f"\n🛡  守衛請睜眼。上一晚守護：{game.last_guard or '無'}")
        options = [s for s in game.alive_seats() if s != game.last_guard]
        return ask_seat("今晚要守護誰", options)

    def choose_kill(self, game: Game, me: Player) -> int | None:
        mates = [p.seat for p in game.alive() if p.is_wolf and p.seat != me.seat]
        print(f"\n🐺 狼人請睜眼。存活的狼隊友：{'、'.join(map(str, mates)) or '只剩你'}")
        return ask_seat("今晚要殺誰（0=空刀）", game.alive_seats())

    def witch_action(self, game: Game, me: Player, victim: int | None):
        print(f"\n🧪 女巫請睜眼。解藥：{'有' if game.antidote else '已用'}，"
              f"毒藥：{'有' if game.poison else '已用'}")
        if game.antidote:
            if victim is None:
                print("  今晚狼人空刀，沒有人被殺。")
            else:
                print(f"  今晚被狼人殺的是 {victim}號。")
                if game.can_witch_save(me, victim):
                    if ask_yes("  要使用解藥嗎"):
                        return "save", None
                else:
                    print("  （依規則你現在不能自救）")
        else:
            print("  你的解藥已經用掉，看不到今晚的刀口。")
        if game.poison:
            t = ask_seat("  要對誰使用毒藥（0=不使用）", game.alive_seats())
            if t is not None:
                return "poison", t
        return None, None

    def choose_check(self, game: Game, me: Player) -> int | None:
        label = "燈影預言家" if me.role is Role.LANTERN_SEER else "預言家"
        print(f"\n🔮 {label}請睜眼。", end="")
        if self.checks:
            print("你之前的查驗：" + "、".join(
                f"{t}號={'狼' if w else '好'}" for t, w in self.checks.items()))
        else:
            print()
        options = game.check_options(me)
        if game.lure_range is not None:
            print(f"  ⚠️ 虎姑婆的誘導生效：今晚只能查驗 {'、'.join(map(str, sorted(game.lure_range)))}號")
        if game.has_lantern:
            print("  （不能驗自己、翻牌的騎士和騎金）")
        if not options:
            print("  今晚沒有可以查驗的人。")
            return None
        return ask_seat("今晚要查驗誰", options, allow_none=False)

    def on_check_result(self, game: Game, me: Player, target: int, is_wolf: bool) -> None:
        self.checks[target] = is_wolf
        note = ""
        if game.has_lantern and me.role in (Role.SEER, Role.LANTERN_SEER):
            note = "（你不知道自己是正確還是反向查驗，結果可能是反的）"
        print(f"  👉 {target}號 是 {'🐺 狼人' if is_wolf else '😇 好人'}{note}")

    # ------------------------------------------------------------ 白天
    def speak(self, game: Game, me: Player) -> Speech:
        print(f"\n🎤 輪到你（{me.seat}號）發言。")
        return self._compose(game, me)

    def last_words(self, game: Game, me: Player) -> Speech:
        print(f"\n🕯  你（{me.seat}號）出局了，請發表遺言。")
        return self._compose(game, me)

    def _compose(self, game: Game, me: Player) -> Speech:
        self._alive_hint(game)
        roles = list(Role)
        print("  要宣稱身份嗎？ 0=不宣稱  " +
              "  ".join(f"{i}={r.value}" for i, r in enumerate(roles, 1)))
        raw = ask("  > ")
        claim = roles[int(raw) - 1] if raw.isdigit() and 1 <= int(raw) <= len(roles) else None
        checks: dict[int, bool] = {}
        if claim is Role.SEER:
            print("  報查驗：格式「號碼 狼/好」，多個用逗號分隔，例如：5 狼, 3 好（Enter 略過）")
            for item in ask("  > ").replace("，", ",").split(","):
                bits = item.split()
                if len(bits) == 2 and bits[0].isdigit() and bits[1] in ("狼", "好"):
                    checks[int(bits[0])] = bits[1] == "狼"
        # 警長競選時昨晚死訊還沒公布，所有座位都能選，避免洩漏死訊
        pool = list(game.players) if game.phase == "election" else game.alive_seats()
        accuse = ask_seat("  要指認（歸票）誰", [s for s in pool if s != me.seat])
        text = ask("  補充發言（可空白）> ")
        return Speech(me.seat, claim, checks, accuse, text)

    def vote(self, game: Game, me: Player, candidates: list[int]) -> int | None:
        options = [c for c in candidates if c != me.seat]
        return ask_seat(f"\n🗳  {me.seat}號 請投票（0=棄票）", options)

    def hunter_shoot(self, game: Game, me: Player) -> int | None:
        others = [s for s in game.alive_seats() if s != me.seat]
        if me.role is Role.HUNTER:
            print("\n🔫 你是獵人，可以開槍帶走一名玩家。")
            return ask_seat("要開槍帶走誰（0=不開槍）", others)
        left = game.claws.get(me.seat, 0)
        print(f"\n🐾 你可以發動狼王爪帶走一名玩家（剩 {left} 次）。")
        return ask_seat("要帶走誰（0=不發動）", others)

    def hunter_poisoned(self, game: Game, me: Player) -> None:
        cause = "被女巫毒死" if me.death_cause == "poison" else "夢遊出局"
        print(f"\n☠️  你{cause}，不能發動技能。")

    def choose_dream(self, game: Game, me: Player) -> int | None:
        print(f"\n💤 攝夢人請睜眼。上一晚的夢遊者：{game.last_dream or '無'}"
              "（連續兩晚選同一人會讓他出局）")
        return ask_seat("今晚讓誰夢遊", [s for s in game.alive_seats() if s != me.seat],
                        allow_none=False)

    def merchant_trade(self, game: Game, me: Player):
        print("\n🎁 奇蹟商人請睜眼。整局只能交易一次；交給狼人的話你會出局。")
        t = ask_seat("要和誰交易（0=今晚不交易）", [s for s in game.alive_seats() if s != me.seat])
        if t is None:
            return None
        while True:
            raw = ask("  給什麼？ 1=查驗 2=毒藥 3=守護 > ")
            if raw in ("1", "2", "3"):
                return t, ["check", "poison", "guard"][int(raw) - 1]

    def on_lucky(self, game: Game, me: Player, item: str) -> None:
        print(f"\n🍀 你成為幸運兒！奇蹟商人給了你【{ITEMS[item]}】，可以使用一次（今晚就能用）。")

    def lucky_action(self, game: Game, me: Player, item: str) -> int | None:
        others = [s for s in game.alive_seats() if s != me.seat]
        verb = {"check": "查驗", "poison": "毒", "guard": "守護"}[item]
        print(f"\n🍀 幸運兒請睜眼，你的道具：{ITEMS[item]}（一次性）")
        return ask_seat(f"今晚要{verb}誰（0=先不用）", others)

    def pass_claw(self, game: Game, me: Player) -> int | None:
        mates = [p.seat for p in game.alive() if p.is_wolf and p.seat != me.seat
                 and p.seat not in game.claw_given]
        if not mates:
            return None
        print(f"\n🐾 覺醒狼王：你還有 {game.claws.get(me.seat, 0)} 次狼王爪，可以親傳一次給隊友。")
        return ask_seat("要親傳給誰（0=不傳）", mates)

    def on_claw(self, game: Game, me: Player) -> None:
        print("\n🐾 覺醒狼王把一次狼王爪親傳給你！出局時（被毒、夢遊除外）可以帶走一人。")

    # ------------------------------------------------------------ 警長與自爆
    def run_for_sheriff(self, game: Game, me: Player) -> bool:
        print("\n🎖  警長競選開始。")
        return ask_yes(f"{me.seat}號 要上警（競選警長）嗎")

    def sheriff_vote(self, game: Game, me: Player, candidates: list[int]) -> int | None:
        return ask_seat(f"\n🎖  {me.seat}號 請投警長票（0=棄票）", candidates)

    def pass_badge(self, game: Game, me: Player) -> int | None:
        print("\n🎖  你是警長，出局前要把警徽交給誰？")
        return ask_seat("移交警徽給（0=撕掉警徽）", [s for s in game.alive_seats() if s != me.seat])

    def choose_direction(self, game: Game, me: Player) -> str:
        seats = game.alive_seats()
        print(f"\n🎖  你是警長，決定今天的發言方向（你最後發言）。存活：{'、'.join(map(str, seats))}")
        raw = ask("  1=往大號（警右） 2=往小號（警左）> ")
        return "left" if raw == "2" else "right"

    def self_explode(self, game: Game, me: Player) -> bool:
        where = "警上發言" if game.phase == "election" else "發言"
        return ask_yes(f"\n💣 輪到你{where}。要自爆嗎？（自爆後立即出局，今天直接天黑）")

    # ------------------------------------------------------------ 村姑與虎姑婆
    def choose_model(self, game: Game, me: Player) -> int | None:
        print("\n🧒 野孩子請睜眼，選一名玩家當你的榜樣。榜樣出局後你會轉入狼隊。")
        return ask_seat("要選誰當榜樣", [s for s in game.alive_seats() if s != me.seat], allow_none=False)

    def on_turn(self, game: Game, me: Player) -> None:
        mates = [p.seat for p in game.alive() if p.is_wolf and p.seat != me.seat]
        print(f"\n🐺 你（野孩子）轉入狼隊了！狼隊友：{'、'.join(map(str, mates)) or '無'}號。"
              "從下一晚起和狼人一起行動。")

    def choose_charm(self, game: Game, me: Player) -> int | None:
        print(f"\n💋 狼美人：上一晚迷魅 {game.last_charm or '無'}（不能連續兩晚同一人）。你出局時被迷魅的人會一起出局。")
        return ask_seat("今晚要迷魅誰（0=不迷魅）",
                        [s for s in game.alive_seats() if s != me.seat and s != game.last_charm])

    def choose_lure(self, game: Game, me: Player, centers: list[int]) -> int | None:
        print("\n🐯 虎姑婆：可以使用【誘導】。選一個號碼，今晚預言家和村姑只能查驗這個號碼和左右兩人。")
        if game.last_lure_range:
            print(f"   上次的範圍：{'、'.join(map(str, sorted(game.last_lure_range)))}號（新範圍不能重疊）")
        return ask_seat("要誘導哪個號碼（0=今晚不用）", centers)

    def girl_check(self, game: Game, me: Player, options: list[int]) -> int | None:
        print("\n👧 村姑請睜眼。你整局有一次查驗，結果準不準取決於你的投票（優先看警長票）：")
        print("   警長票投狼人／放逐票投好人 → 正確；警長票投好人／放逐票投狼人 → 相反")
        if game.lure_range is not None:
            print(f"  ⚠️ 虎姑婆的誘導生效：今晚只能查驗 {'、'.join(map(str, sorted(game.lure_range)))}號")
        return ask_seat("要查驗誰（0=先不用）", options)

    def on_girl_result(self, game: Game, me: Player, target: int, shown_wolf: bool) -> None:
        print(f"  👉 你看到 {target}號 是 {'🐺 狼人' if shown_wolf else '😇 好人'}（可能是反的，想想你投給了誰）")

    def knight_duel(self, game: Game, me: Player) -> int | None:
        print("\n⚔️  你是騎士，可以在發言前翻牌決鬥（整局一次）：對方是狼就出局並立刻天黑，是好人你就出局。")
        return ask_seat("要決鬥誰（0=不決鬥，正常發言）", [s for s in game.alive_seats() if s != me.seat])
