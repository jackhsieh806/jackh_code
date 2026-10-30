"""電腦玩家的五種個性。

同一套推理邏輯，用不同參數控制「多相信直覺還是證據」「多積極發言、投票、用技能」。
"""
from __future__ import annotations

from dataclasses import dataclass

INF = float("inf")


@dataclass(frozen=True)
class Personality:
    key: str
    name: str
    desc: str
    opener: str           # 一般發言的開頭語
    intuition: float      # 直覺（每個人的隨機第一印象）在懷疑度裡的權重
    follow: float         # 採信別人指認的程度
    evidence: float       # 查驗、事實、票型等線索的權重倍數
    vote_bar: float       # 最可疑的人懷疑度低於這個就棄票
    accuse_bar: float     # 發言時懷疑度低於這個就不點名
    claim: float          # 預言家第一天起跳的機率
    poison_bar: float     # 女巫用毒的懷疑度門檻（確定是狼一定毒）
    poison_prob: float    # 超過門檻時真的用毒的機率
    shoot_bar: float      # 獵人有把握開槍的懷疑度門檻
    blind_shoot: float    # 沒把握時仍然開槍的機率
    duel_prob: float      # 騎士在有強烈證據時決鬥的機率
    duel_guess: float     # 騎士只憑懷疑就決鬥的機率
    explode: float        # 狼人自爆機率的倍數
    bluff: float          # 狼人悍跳、假跳身份的傾向倍數
    run_sheriff: float    # 上警機率（真預言家除外）
    tear_bar: float       # 警長死前：最可信的人懷疑度高於這個就撕警徽


PERSONALITIES: dict[str, Personality] = {p.key: p for p in [
    Personality(
        "rational", "理智型", "綜合直覺、證據和大家的意見，每一項都不偏廢，是最平均的玩家。",
        "綜合來看", intuition=3.0, follow=1.5, evidence=1.0, vote_bar=-INF, accuse_bar=-INF,
        claim=0.8, poison_bar=20, poison_prob=0.5, shoot_bar=10, blind_shoot=0.4,
        duel_prob=0.5, duel_guess=0.0, explode=1.0, bluff=1.0, run_sheriff=0.3, tear_bar=5),
    Personality(
        "logical", "邏輯型", "只看查驗、矛盾和票型，幾乎不靠直覺，也不太跟風；沒有理由就不點名。",
        "從邏輯上推", intuition=0.3, follow=0.3, evidence=1.6, vote_bar=-INF, accuse_bar=4,
        claim=0.9, poison_bar=25, poison_prob=0.7, shoot_bar=15, blind_shoot=0.1,
        duel_prob=0.7, duel_guess=0.0, explode=0.8, bluff=0.8, run_sheriff=0.35, tear_bar=3),
    Personality(
        "conservative", "保守型", "習慣跟著多數人和警長的方向走，神職晚一點才跳，技能能省就省。",
        "我先跟著大家的方向", intuition=1.5, follow=4.0, evidence=0.9, vote_bar=10, accuse_bar=8,
        claim=0.6, poison_bar=35, poison_prob=0.3, shoot_bar=20, blind_shoot=0.15,
        duel_prob=0.3, duel_guess=0.0, explode=0.5, bluff=0.5, run_sheriff=0.2, tear_bar=8),
    Personality(
        "safe", "安全保守型", "不確定就棄票、不點名；毒藥、獵槍、決鬥只用在確定的狼身上；當狼也絕不自爆。",
        "資訊不夠，我先不表態", intuition=1.0, follow=2.0, evidence=0.8, vote_bar=20, accuse_bar=18,
        claim=0.4, poison_bar=INF, poison_prob=0.0, shoot_bar=INF, blind_shoot=0.0,
        duel_prob=0.0, duel_guess=0.0, explode=0.0, bluff=0.2, run_sheriff=0.1, tear_bar=0),
    Personality(
        "aggressive", "積極猜測型", "很靠直覺，第一天就敢點名、敢開槍、敢毒人、敢決鬥；當狼最愛悍跳和自爆。",
        "我直覺", intuition=14.0, follow=1.0, evidence=0.8, vote_bar=-INF, accuse_bar=-INF,
        claim=1.0, poison_bar=10, poison_prob=0.9, shoot_bar=0, blind_shoot=1.0,
        duel_prob=0.9, duel_guess=0.4, explode=2.0, bluff=2.0, run_sheriff=0.6, tear_bar=20),
]}

DEFAULT = PERSONALITIES["rational"]
