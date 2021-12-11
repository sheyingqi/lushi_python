# -*- coding: utf-8 -*-
from hearthstone.entities import Entity

from entity.spell_entity import SpellEntity


class LETL_302(SpellEntity):
    """
        毁灭之雨5
        随机对一个敌人造成$14点伤害。在本回合中，你每施放过一个邪能技能，重复一次。0随机对一个敌人造成$15点伤害。在本回合中，你每施放过一个邪能技能，重复一次。0随机对一个敌人造成$16点伤害。在本回合中，你每施放过一个邪能技能，重复一次。0随机对一个敌人造成$17点伤害。在本回合中，你每施放过一个邪能技能，重复一次。0随机对一个敌人造成$18点伤害。在本回合中，你每施放过一个邪能技能，重复一次。
    """

    def __init__(self, entity: Entity):
        super().__init__(entity)
        self.damage = 0
        self.range = 0

    def play(self, game, hero, target):
        pass

