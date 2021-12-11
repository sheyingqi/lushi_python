# -*- coding: utf-8 -*-
import random

from hearthstone.entities import Entity
from hearthstone.enums import SpellSchool

from entity.spell_entity import SpellEntity


class LETL_452_M(SpellEntity):
    """
        火球风暴5
        随机对一个敌人施放火球术5。在本回合中你每施放过一个火焰技能，重复一次。0随机对两个敌人施放火球术5。在本回合中你每施放过一个火焰技能，重复一次。
    """

    def __init__(self, entity: Entity):
        super().__init__(entity)
        self.damage = 12
        self.range = -1

    def play(self, game, hero, target):
        power = game.get_spell_power(self.spell_school, hero.own)
        # 获取技能列表
        action_list = game.get_action_list(hero.own)
        action_list.sort()
        # 获取之前用过的技能类型次数
        cnt = game.combo_count(SpellSchool.FIRE, hero.own())
        for _ in range(cnt):
            # 假设每次只打最高血量的佣兵
            h = game.find_max_health(not hero.own())
            h.got_damage(game, (self.damage + power) * self.damage_advantage[self.lettuce_role][h.lettuce_role])
