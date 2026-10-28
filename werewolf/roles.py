"""角色、陣營與板子（配置）定義。"""
from __future__ import annotations

from enum import Enum


class Team(Enum):
    GOOD = "好人陣營"
    WOLF = "狼人陣營"


class Role(Enum):
    WEREWOLF = "狼人"
    WOLF_KING = "狼王"
    AWAKENED_WOLF_KING = "覺醒狼王"
    WOLF_BEAUTY = "狼美人"
    TIGER_GRANDMA = "虎姑婆"
    WILD_CHILD = "野孩子"
    SEER = "預言家"
    LANTERN_SEER = "燈影預言家"
    WITCH = "女巫"
    HUNTER = "獵人"
    GUARD = "守衛"
    IDIOT = "白痴"
    DREAMER = "攝夢人"
    MERCHANT = "奇蹟商人"
    KNIGHT = "騎士"
    VILLAGE_GIRL = "村姑"
    VILLAGER = "平民"

    @property
    def team(self) -> Team:
        """開局陣營。野孩子的陣營會隨榜樣改變，要用 Game.alignment() 判斷。"""
        return Team.WOLF if self in WOLVES else Team.GOOD

    @property
    def is_god(self) -> bool:
        """神職：預言家、女巫、獵人、守衛、白痴、攝夢人、奇蹟商人、騎士。

        村姑和野孩子既不是神職也不是平民，屠邊時不算任何一邊；燈影預言家站民坑，算在平民那一邊。"""
        return self in GODS


# 「真狼」：好人要把這些全部放逐才算贏（轉狼的野孩子不用出局）
WOLVES = frozenset({Role.WEREWOLF, Role.WOLF_KING, Role.AWAKENED_WOLF_KING,
                    Role.WOLF_BEAUTY, Role.TIGER_GRANDMA})
GODS = frozenset({Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD, Role.IDIOT,
                  Role.DREAMER, Role.MERCHANT, Role.KNIGHT})

ROLE_DESCRIPTIONS = {
    Role.WEREWOLF: "每晚與狼隊友商量殺一個人。白天要隱藏身份，可以假冒神職（悍跳）。",
    Role.WOLF_KING: "狼人的一員。被放逐或晚上出局時可以發動狼王爪帶走一人；被毒死、夢遊出局則不能。",
    Role.AWAKENED_WOLF_KING: "狼人的一員，有兩次狼王爪。晚上可以「親傳」一爪給狼隊友（每晚一次、每位隊友最多一次），"
                             "隊友出局時可帶走一人；留在自己身上的爪子出局時全部可用。被毒死、夢遊出局則不能發動。",
    Role.SEER: "每晚查驗一名玩家，得知他是『好人』或『狼人』。是好人陣營的資訊核心。"
               "（燈影預言家板：拿到預言家牌的人站神坑，但查驗可能是反的。）",
    Role.LANTERN_SEER: "站民坑的另一位預言家，每晚也能查驗。開局時主持人決定預言家牌和燈影預言家牌哪一張查驗正確，"
                       "另一張就是反向查驗，兩人都不知道自己是哪一種。不能驗自己、翻牌的騎士和騎士驗出的好人（騎金）。",
    Role.WITCH: "有一瓶解藥、一瓶毒藥，各用一次；同一晚不能兩瓶都用。解藥用掉後就看不到刀口。",
    Role.HUNTER: "被狼殺或被放逐時，可以開槍帶走一人；被女巫毒死則不能開槍。",
    Role.GUARD: "每晚守護一人使其不被狼殺，不能連續兩晚守同一人。被守又被救（同守同救）仍會死亡。",
    Role.IDIOT: "白天被投票放逐時翻牌免死，但之後失去投票權；晚上被殺則正常死亡。",
    Role.DREAMER: "每晚必須選一人當夢遊者（不能選自己），夢遊者當晚免疫狼刀與毒藥。"
                  "連續兩晚選同一人，他會夢遊出局；攝夢人晚上死亡時，夢遊者也一起出局。",
    Role.MERCHANT: "整局一次：晚上把「查驗／毒藥／守護」其中一個技能交給一名玩家（幸運兒），幸運兒當晚就能使用一次。"
                   "如果交給的是狼人，對方拿不到技能，商人天亮時出局。",
    Role.WOLF_BEAUTY: "狼人的一員。每晚可以迷魅一名玩家（不能連續兩晚迷魅同一人）；"
                      "狼美人出局時，被迷魅的玩家一同出局。狼美人不能自爆、不能被狼隊自刀；"
                      "被騎士決鬥出局時技能失效，被迷魅的人不會出局。",
    Role.TIGER_GRANDMA: "狼人的一員。【誘導】第二晚起每隔一晚可用：選一個號碼，當晚預言家和村姑只能查驗這個號碼"
                        "和左右兩人；新的範圍不能和上一次重疊。野孩子入狼隊時誘導整局只能用一次。"
                        "【惡靈反傷】整局一次：被村姑查驗、預言家查驗或女巫毒時，技能使用者出局"
                        "（順序：村姑 > 預言家 > 女巫；反彈女巫時虎姑婆不會被毒死）。",
    Role.WILD_CHILD: "首夜選一名玩家當榜樣。榜樣是狼就屬於狼人陣營（但不知道狼是誰）；榜樣是好人就屬於好人陣營。"
                     "榜樣出局後野孩子轉入狼隊。榜樣是村姑則永遠是好人；榜樣是虎姑婆則立刻知道所有狼隊友。"
                     "被查驗永遠是好人（金水），轉狼後好人也不需要把他放逐就能獲勝。",
    Role.KNIGHT: "白天輪到自己發言時可以翻牌決鬥一名玩家（整局一次）：對方是狼就出局並立刻天黑；"
                 "對方是好人則騎士自己出局。",
    Role.VILLAGE_GIRL: "整局一次查驗，投過票後的夜晚才能用。結果準不準要看她投的票（優先看警長票）："
                       "警長票投狼人或放逐票投好人 → 結果正確；警長票投好人或放逐票投狼人 → 結果相反。",
    Role.VILLAGER: "沒有特殊能力，靠發言、聽邏輯、投票找出狼人。",
}


def _board(wolves: list[Role], gods: list[Role], villagers: int) -> list[Role]:
    return wolves + gods + [Role.VILLAGER] * villagers


W, WK, AWK = Role.WEREWOLF, Role.WOLF_KING, Role.AWAKENED_WOLF_KING
WB, TG, WC, KN, VG = (Role.WOLF_BEAUTY, Role.TIGER_GRANDMA, Role.WILD_CHILD, Role.KNIGHT,
                      Role.VILLAGE_GIRL)
S, WI, H, G, I, D, M = (Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD, Role.IDIOT,
                        Role.DREAMER, Role.MERCHANT)

# key -> (說明, 角色列表)
PRESETS: dict[str, tuple[str, list[Role]]] = {
    "1": ("9 人局：3 狼 + 預言家、女巫、獵人 + 3 平民", _board([W] * 3, [S, WI, H], 3)),
    "2": ("12 人「預女獵白」：4 狼 + 預言家、女巫、獵人、白痴 + 4 平民", _board([W] * 4, [S, WI, H, I], 4)),
    "3": ("12 人「預女獵守」：4 狼 + 預言家、女巫、獵人、守衛 + 4 平民", _board([W] * 4, [S, WI, H, G], 4)),
    "4": ("12 人「狼王守衛」：狼王 + 3 狼 + 預言家、女巫、獵人、守衛 + 4 平民", _board([WK] + [W] * 3, [S, WI, H, G], 4)),
    "5": ("12 人「攝夢人」：狼王 + 3 狼 + 預言家、女巫、獵人、攝夢人 + 4 平民", _board([WK] + [W] * 3, [S, WI, H, D], 4)),
    "6": ("12 人「奇蹟商人」：狼王 + 3 狼 + 預言家、女巫、獵人、奇蹟商人 + 4 平民", _board([WK] + [W] * 3, [S, WI, H, M], 4)),
    "7": ("12 人「覺醒狼王」：覺醒狼王 + 3 狼 + 預言家、女巫、守衛、攝夢人 + 4 平民", _board([AWK] + [W] * 3, [S, WI, G, D], 4)),
    "8": ("15 人「村姑與虎姑婆」：狼美人、虎姑婆、2 小狼、野孩子 + 預言家、女巫、騎士、守衛、村姑 + 5 平民",
          _board([WB, TG, W, W, WC], [S, WI, KN, G, VG], 5)),
    # 海報配置寫 5 平民（合計 16 人），但標題是 15 人、獲勝條件是「四民 + 燈影預」，這裡採用 4 平民
    "9": ("15 人「燈影預言家」：狼王、狼美人、3 小狼 + 預言家、女巫、騎士、守衛、獵人 + 燈影預言家 + 4 平民",
          _board([WK, WB, W, W, W], [S, WI, KN, G, H, Role.LANTERN_SEER], 4)),
}
