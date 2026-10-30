"""文字介面主選單：遊玩、觀戰、測驗、規則速查。"""
from __future__ import annotations

import random

from .engine import DEATH_CAUSES, Game, Rules, deal
from .guide import CHEATSHEET, run_quiz
from .human import HumanController, ask, ask_yes
from .personality import PERSONALITIES
from .roles import PRESETS, Role, Team


def choose_preset() -> list[Role]:
    print("\n請選擇板子：")
    for key, (desc, _) in PRESETS.items():
        print(f"  {key}. {desc}")
    print("  0. 自訂板子")
    key = ask("> ")
    if key == "0":
        return custom_board()
    return list(PRESETS.get(key, PRESETS["1"])[1])


def custom_board() -> list[Role]:
    """依真人局的配置自己決定每個角色幾張。"""
    print("\n輸入每個角色的數量（Enter = 0）：")
    while True:
        roles: list[Role] = []
        for r in Role:
            raw = ask(f"  {r.value} × ")
            n = int(raw) if raw.isdigit() else 0
            if r not in (Role.WEREWOLF, Role.VILLAGER) and n > 1:
                print("  （這個角色最多 1 張）")
                n = 1
            roles += [r] * n
        wolves = sum(r.team is Team.WOLF for r in roles)
        if wolves and len(roles) - wolves and 5 <= len(roles) <= 18:
            print(f"✅ 共 {len(roles)} 人，其中狼人陣營 {wolves} 人。")
            return roles
        print("⚠️ 需要 5～18 人，且至少要有 1 個狼人陣營、1 個好人陣營。請重新輸入。")


def review(game: Game, human_seat: int | None = None) -> None:
    """賽後復盤：公開所有身份、夜晚行動與票型。"""
    print("\n" + "=" * 50 + "\n📋 復盤\n" + "=" * 50)
    print("\n身份：")
    for p in game.players.values():
        status = "存活" if p.alive else DEATH_CAUSES[p.death_cause]
        me = " ← 你" if p.seat == human_seat else ""
        role = p.role.value
        if p.role is Role.WILD_CHILD:
            role += "（轉狼）" if p.turned else f"（{game.alignment(p).value}）"
        pers = game.personality_of(p.seat)
        pers = f"［{pers.name}］" if pers else ""
        print(f"  {p.seat:>2}號 {role:<4} {status}{me} {pers}")

    if game.has_lantern:
        right = Role.SEER if game.seer_card_accurate else Role.LANTERN_SEER
        print(f"\n🏮 本局查驗正確的是【{right.value}】牌，另一張是反向查驗。")

    print("\n上帝視角（夜晚行動）：")
    for line in game.god_log:
        print(f"  {line}")

    def mark(t):
        return "🐺" if game.players[t].is_wolf else "😇"

    print("\n票型（🐺=投到狼  😇=投到好人）：")
    for d in game.days:
        if not d.votes:
            continue
        line = "  ".join(f"{v}→{t}{mark(t)}" if t else f"{v}→棄" for v, t in d.votes.items())
        print(f"  第{d.day}天：{line}")
        if d.pk_votes:
            line = "  ".join(f"{v}→{t}{mark(t)}" if t else f"{v}→棄" for v, t in d.pk_votes.items())
            print(f"     PK：{line}")

    if game.sheriff_log:
        print("\n警長：")
        for line in game.sheriff_log:
            print(f"  {line}")

    claims = game.seer_claims()
    if claims:
        print("\n預言家宣稱：")
        for c in claims:
            real = game.players[c].role is Role.SEER
            print(f"  {c}號 跳預言家 → {'✅ 真預言家' if real else '❌ 假的（' + game.players[c].role.value + '）'}")

    if human_seat is not None:
        me = game.players[human_seat]
        mine = [d.votes.get(human_seat) for d in game.days] + \
               [d.pk_votes.get(human_seat) for d in game.days]
        mine = [t for t in mine if t is not None]
        if mine:
            hit = sum(game.players[t].is_wolf for t in mine)
            good_side = game.alignment(me) is Team.GOOD
            print(f"\n你的投票：共 {len(mine)} 票，投中狼 {hit} 票、投到好人 {len(mine) - hit} 票。")
            if good_side and len(mine) - hit > hit:
                print("  💡 你常投到好人。回頭看看：那些人是被誰帶節奏推出去的？誰的查驗跟事實矛盾？")
            elif good_side:
                print("  👍 投票準確度不錯！")


def play_game(rules: Rules, spectate: bool = False) -> None:
    roles = choose_preset()
    rng = random.Random()
    seats = deal(roles, rng)
    controllers = {}
    human_seat = None
    if not spectate:
        print("\n想扮演哪個身份？ 0=隨機  " +
              "  ".join(f"{i}={r.value}" for i, r in enumerate(dict.fromkeys(roles), 1)))
        options = list(dict.fromkeys(roles))
        raw = ask("> ")
        human_seat = rng.randint(1, len(seats))
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            wanted = options[int(raw) - 1]
            j = seats.index(wanted)
            seats[j], seats[human_seat - 1] = seats[human_seat - 1], seats[j]
        controllers[human_seat] = HumanController()
        god_view = False
    else:
        god_view = ask_yes("要開啟上帝視角嗎（看得到夜晚行動）")

    def pause():
        ask("（按 Enter 繼續）")

    game = Game(seats, controllers, rules=rules, god_view=god_view,
                seed=rng.randrange(1 << 30), pause=pause)
    winner = game.play()
    if human_seat is not None and winner is not None:
        mine = game.alignment(game.players[human_seat])
        print("🎉 你贏了！" if mine is winner else "😢 你輸了，再接再厲！")
    if ask_yes("\n要看復盤嗎"):
        review(game, human_seat)


def settings(rules: Rules) -> None:
    modes = {"1": "never", "2": "first_night", "3": "always"}
    names = {"never": "全程不可自救", "first_night": "僅首夜可自救", "always": "隨時可自救"}
    print(f"\n目前設定：女巫 {names[rules.witch_self_save]}、"
          f"同守同救{'會死' if rules.same_guard_save_dies else '不會死'}、"
          f"{'屠邊' if rules.win_mode == 'side' else '屠城'}、"
          f"{'有' if rules.sheriff else '無'}警長、{'可' if rules.self_explode else '不可'}自爆")
    raw = ask("女巫自救：1=全程不可 2=僅首夜 3=隨時（Enter 不變）> ")
    rules.witch_self_save = modes.get(raw, rules.witch_self_save)
    raw = ask("同守同救：1=會死 2=不會死（Enter 不變）> ")
    if raw in ("1", "2"):
        rules.same_guard_save_dies = raw == "1"
    raw = ask("勝利條件：1=屠邊 2=屠城（Enter 不變）> ")
    if raw in ("1", "2"):
        rules.win_mode = "side" if raw == "1" else "all"
    raw = ask("警長競選：1=有 2=沒有（Enter 不變）> ")
    if raw in ("1", "2"):
        rules.sheriff = raw == "1"
    raw = ask("狼人自爆：1=可以 2=不可以（Enter 不變）> ")
    if raw in ("1", "2"):
        rules.self_explode = raw == "1"
    keys = ["mixed", *PERSONALITIES]
    print("電腦個性：" + "  ".join(
        f"{i}={'隨機混合' if k == 'mixed' else PERSONALITIES[k].name}" for i, k in enumerate(keys, 1)))
    for k, p in PERSONALITIES.items():
        print(f"   {p.name}：{p.desc}")
    raw = ask(f"（目前：{'隨機混合' if rules.bot_personality == 'mixed' else PERSONALITIES[rules.bot_personality].name}，Enter 不變）> ")
    if raw.isdigit() and 1 <= int(raw) <= len(keys):
        rules.bot_personality = keys[int(raw) - 1]
    raw = ask("開局就公開每個電腦的個性：1=公開 2=不公開，復盤時才看（Enter 不變）> ")
    if raw in ("1", "2"):
        rules.show_personality = raw == "1"
    print("✅ 設定已更新。")


def main() -> None:
    rules = Rules()
    while True:
        print("""
🐺 ====== 狼人殺邏輯練習器 ====== 🐺
  1. 開始一局（你和電腦玩家一起玩）
  2. 觀戰模式（全電腦對戰，可開上帝視角）
  3. 規則測驗
  4. 規則、術語與實戰建議
  5. 規則設定
  0. 離開""")
        choice = ask("> ")
        if choice == "1":
            play_game(rules)
        elif choice == "2":
            play_game(rules, spectate=True)
        elif choice == "3":
            run_quiz()
        elif choice == "4":
            print(CHEATSHEET)
        elif choice == "5":
            settings(rules)
        elif choice == "0":
            print("祝你真人局順利！🍀")
            return

