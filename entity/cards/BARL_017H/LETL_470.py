# -*- coding: utf-8 -*-
from hearthstone.entities import Entity

from entity.spell_entity import SpellEntity


class LETL_470(SpellEntity):
    """
        塞纳里奥波动5
        造成$10点伤害。下回合你的角色的自然技能速度值加快（3）点。
    """

    def __init__(self, entity: Entity):
        super().__init__(entity)
        self.damage = 0
        self.range = 0

    def play(self, game, hero, target):
        pass

