"""角色、陣營與板子（配置）定義。"""
from __future__ import annotations

from enum import Enum


class Team(Enum):
    GOOD = "好人陣營"
    WOLF = "狼人陣營"


class Role(Enum):
    WEREWOLF = "狼人"
    SEER = "預言家"
    WITCH = "女巫"
    HUNTER = "獵人"
    GUARD = "守衛"
    IDIOT = "白痴"
    VILLAGER = "平民"

    @property
    def team(self) -> Team:
        return Team.WOLF if self is Role.WEREWOLF else Team.GOOD

    @property
    def is_god(self) -> bool:
        """神職：預言家、女巫、獵人、守衛、白痴。"""
        return self in GODS


GODS = frozenset({Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD, Role.IDIOT})

ROLE_DESCRIPTIONS = {
    Role.WEREWOLF: "每晚與狼隊友商量殺一個人。白天要隱藏身份，可以假冒神職（悍跳）。",
    Role.SEER: "每晚查驗一名玩家，得知他是『好人』或『狼人』。是好人陣營的資訊核心。",
    Role.WITCH: "有一瓶解藥、一瓶毒藥，各用一次；同一晚不能兩瓶都用。解藥用掉後就看不到刀口。",
    Role.HUNTER: "被狼殺或被放逐時，可以開槍帶走一人；被女巫毒死則不能開槍。",
    Role.GUARD: "每晚守護一人使其不被狼殺，不能連續兩晚守同一人。被守又被救（同守同救）仍會死亡。",
    Role.IDIOT: "白天被投票放逐時翻牌免死，但之後失去投票權；晚上被殺則正常死亡。",
    Role.VILLAGER: "沒有特殊能力，靠發言、聽邏輯、投票找出狼人。",
}


def _board(wolves: int, gods: list[Role], villagers: int) -> list[Role]:
    return [Role.WEREWOLF] * wolves + gods + [Role.VILLAGER] * villagers


# key -> (說明, 角色列表)
PRESETS: dict[str, tuple[str, list[Role]]] = {
    "1": ("9 人局：3 狼 + 預言家、女巫、獵人 + 3 平民",
          _board(3, [Role.SEER, Role.WITCH, Role.HUNTER], 3)),
    "2": ("12 人局「預女獵白」：4 狼 + 預言家、女巫、獵人、白痴 + 4 平民",
          _board(4, [Role.SEER, Role.WITCH, Role.HUNTER, Role.IDIOT], 4)),
    "3": ("12 人局「預女獵守」：4 狼 + 預言家、女巫、獵人、守衛 + 4 平民",
          _board(4, [Role.SEER, Role.WITCH, Role.HUNTER, Role.GUARD], 4)),
}
