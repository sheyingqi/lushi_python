# -*- coding: utf-8 -*-
from hearthstone.entities import Entity
from hearthstone.enums import GameTag, SpellSchool

from entity.spell_entity import SpellEntity


class LETL_030P4_M(SpellEntity):
    """
        地狱火
        对所有敌人造成8点伤害。火焰连击：再造成8点伤害。
    """

    def __init__(self, entity: Entity):
        super().__init__(entity)
        self.damage = 8
        self.combo_damage = 8
        self.range = 7

    def play(self, game, hero, target):
        # aoe或者随机不需要指定target
        power = game.get_spell_power(self.spell_school, hero.own)
        # 获取技能列表
        action_list = game.get_action_list(hero.own)
        action_list.sort()
        combo = game.can_combo(self, SpellSchool.FIRE, hero.own)
        combo_damage = (self.combo_damage + power) * combo
        hero_list = game.get_hero_list(not hero.own())
        for h in hero_list:
            h.got_damage(game, (self.damage + combo_damage + power) * self.damage_advantage[self.lettuce_role][
                h.lettuce_role])
