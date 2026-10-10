"""真人玩家（鍵盤輸入）的 Controller。"""
from __future__ import annotations

from .engine import Controller, Game, Player, Speech
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
        print("=" * 50)

    def _alive_hint(self, game: Game) -> None:
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
        print("\n🔮 預言家請睜眼。", end="")
        if self.checks:
            print("你之前的查驗：" + "、".join(
                f"{t}號={'狼' if w else '好'}" for t, w in self.checks.items()))
        else:
            print()
        options = [s for s in game.alive_seats() if s != me.seat]
        return ask_seat("今晚要查驗誰", options, allow_none=False)

    def on_check_result(self, game: Game, me: Player, target: int, is_wolf: bool) -> None:
        self.checks[target] = is_wolf
        print(f"  👉 {target}號 是 {'🐺 狼人' if is_wolf else '😇 好人'}")

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
        others = [s for s in game.alive_seats() if s != me.seat]
        accuse = ask_seat("  要指認（歸票）誰", others)
        text = ask("  補充發言（可空白）> ")
        return Speech(me.seat, claim, checks, accuse, text)

    def vote(self, game: Game, me: Player, candidates: list[int]) -> int | None:
        options = [c for c in candidates if c != me.seat]
        return ask_seat(f"\n🗳  {me.seat}號 請投票（0=棄票）", options)

    def hunter_shoot(self, game: Game, me: Player) -> int | None:
        print("\n🔫 你是獵人，可以開槍帶走一名玩家。")
        return ask_seat("要開槍帶走誰（0=不開槍）", [s for s in game.alive_seats() if s != me.seat])

    def hunter_poisoned(self, game: Game, me: Player) -> None:
        print("\n☠️  你被女巫毒死了，獵人不能開槍。")
