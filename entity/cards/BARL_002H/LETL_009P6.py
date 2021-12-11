# -*- coding: utf-8 -*-
from hearthstone.entities import Entity

from entity.spell_entity import SpellEntity


class LETL_009P6(SpellEntity):
    """
        旋风斩5
        对所有敌人造成$10点伤害，对你的角色造成$1点伤害。0对所有敌人造成$11点伤害，对你的角色造成$1点伤害。0对所有敌人造成$12点伤害，对你的角色造成$1点伤害。0对所有敌人造成$13点伤害，对你的角色造成$1点伤害。0对所有敌人造成$14点伤害，对你的角色造成$1点伤害。
    """

    def __init__(self, entity: Entity):
        super().__init__(entity)
        self.damage = 0
        self.range = 0

    def play(self, game, hero, target):
        pass

