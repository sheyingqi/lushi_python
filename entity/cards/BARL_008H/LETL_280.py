# -*- coding: utf-8 -*-
from hearthstone.entities import Entity

from entity.spell_entity import SpellEntity


class LETL_280(SpellEntity):
    """
        吞噬攻击5
        <b>攻击</b>一个敌人。<b>击杀：</b>获得目标的攻击力。
    """

    def __init__(self, entity: Entity):
        super().__init__(entity)
        self.damage = 0
        self.range = 0

    def play(self, game, hero, target):
        pass

