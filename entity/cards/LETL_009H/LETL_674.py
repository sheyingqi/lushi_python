# -*- coding: utf-8 -*-
from hearthstone.entities import Entity

from entity.spell_entity import SpellEntity


class LETL_674(SpellEntity):
    """
        休止饰带4
        惊愕猛击造成的伤害增加5点。
    """

    def __init__(self, entity: Entity):
        super().__init__(entity)

    def equip(self, hero):
        pass

            