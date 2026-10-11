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
    SEER = "預言家"
    WITCH = "女巫"
    HUNTER = "獵人"
    GUARD = "守衛"
    IDIOT = "白痴"
    DREAMER = "攝夢人"
    MERCHANT = "奇蹟商人"
    VILLAGER = "平民"

    @property
    def team(self) -> Team:
        return Team.WOLF if self in WOLVES else Team.GOOD

    @property
    def is_god(self) -> bool:
        """神職：預言家、女巫、獵人、守衛、白痴、攝夢人、奇蹟商人。"""
        return self in GODS


WOLVES = frozenset({Role.WEREWOLF, Role.WOLF_KING, Role.AWAKENED_WOLF_KING})
GODS = frozenset({Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD, Role.IDIOT,
                  Role.DREAMER, Role.MERCHANT})

ROLE_DESCRIPTIONS = {
    Role.WEREWOLF: "每晚與狼隊友商量殺一個人。白天要隱藏身份，可以假冒神職（悍跳）。",
    Role.WOLF_KING: "狼人的一員。被放逐或晚上出局時可以發動狼王爪帶走一人；被毒死、夢遊出局則不能。",
    Role.AWAKENED_WOLF_KING: "狼人的一員，有兩次狼王爪。晚上可以「親傳」一爪給狼隊友（每晚一次、每位隊友最多一次），"
                             "隊友出局時可帶走一人；留在自己身上的爪子出局時全部可用。被毒死、夢遊出局則不能發動。",
    Role.SEER: "每晚查驗一名玩家，得知他是『好人』或『狼人』。是好人陣營的資訊核心。",
    Role.WITCH: "有一瓶解藥、一瓶毒藥，各用一次；同一晚不能兩瓶都用。解藥用掉後就看不到刀口。",
    Role.HUNTER: "被狼殺或被放逐時，可以開槍帶走一人；被女巫毒死則不能開槍。",
    Role.GUARD: "每晚守護一人使其不被狼殺，不能連續兩晚守同一人。被守又被救（同守同救）仍會死亡。",
    Role.IDIOT: "白天被投票放逐時翻牌免死，但之後失去投票權；晚上被殺則正常死亡。",
    Role.DREAMER: "每晚必須選一人當夢遊者（不能選自己），夢遊者當晚免疫狼刀與毒藥。"
                  "連續兩晚選同一人，他會夢遊出局；攝夢人晚上死亡時，夢遊者也一起出局。",
    Role.MERCHANT: "整局一次：晚上把「查驗／毒藥／守護」其中一個技能交給一名玩家（幸運兒），幸運兒當晚就能使用一次。"
                   "如果交給的是狼人，對方拿不到技能，商人天亮時出局。",
    Role.VILLAGER: "沒有特殊能力，靠發言、聽邏輯、投票找出狼人。",
}


def _board(wolves: list[Role], gods: list[Role], villagers: int) -> list[Role]:
    return wolves + gods + [Role.VILLAGER] * villagers


W, WK, AWK = Role.WEREWOLF, Role.WOLF_KING, Role.AWAKENED_WOLF_KING
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
}
