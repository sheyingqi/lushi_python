# -*- coding: utf-8 -*-
from hearthstone.entities import Entity

from entity.spell_entity import SpellEntity


class LETL_319_M(SpellEntity):
    """
        坚韧光环5
        获得<b>嘲讽</b>2回合。在本回合中，你的角色的速度值加快（4）点。0获得<b>嘲讽</b>2回合。在本回合中，你的角色的速度值加快（4）点。此佣兵的下一个技能速度值加快（1）点。0获得<b>嘲讽</b>2回合。在本回合中，你的角色的速度值加快（4）点。此佣兵的下一个技能速度值加快（2）点。0获得<b>嘲讽</b>2回合。在本回合中，你的角色的速度值加快（4）点。此佣兵的下一个技能速度值加快（3）点。
    """

    def __init__(self, entity: Entity):
        super().__init__(entity)
        self.damage = 0
        self.range = 0
        self.speed = -4

    def play(self, game, hero, target):
        hero.taunt = 1
        # 因为是本回合，所以需要在代码中写出来，下回合的增益就不用写了。
        # 加速
        action_list = game.get_action_list(hero.own())
        for act in action_list:
            act.spell.cost += self.speed
