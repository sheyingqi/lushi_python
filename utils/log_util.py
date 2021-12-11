import logging
from hearthstone.enums import CardType, Zone, GameTag
from hslog import LogParser, packets
from hslog.export import EntityTreeExporter
from entity.game_entity import GameEntity
from entity.hero_entity import HeroEntity
from entity.spell_entity import SpellEntity

# import entity.cards as ecards

logger = logging.getLogger()


class LogUtil:
    def __init__(self, log_path):
        self.log_path = log_path
        self.parser = LogParser()
        self.game = None
        # parse 完后可直接拿来用
        self.game_entity = None

    def read_log(self):
        with open(self.log_path, encoding='utf-8') as f:
            self.parser.read(f)
        self.parser.flush()
        # 最近一场战斗
        packet_tree = self.parser.games[-1]
        exporter = EntityTreeExporter(packet_tree, player_manager=self.parser.player_manager)
        ee = exporter.export()
        self.game = ee.game

    def parse_game(self) -> GameEntity:
        self.read_log()
        for e in self.game.entities:
            # 以下为游戏状态
            if e.type == CardType.GAME:

                # print(e, e.tags, end='\n\n\n')
                # player = e.players
                # for p in player:
                #     print(p.tags, end='\n\n')
                self.game_entity = GameEntity(e)
                pass
            elif e.type == CardType.MINION:
                minion = HeroEntity(e)
                # print(e, e.tags, end='\n\n\n')
                self.game_entity.add_hero(minion)
                pass
            # 佣兵技能信息
            elif e.type == CardType.LETTUCE_ABILITY:
                # print(e, e.tags, end='\n\n\n')
                owner = e.tags.get(GameTag.LETTUCE_ABILITY_OWNER)
                # print(e.card_id)
                if owner in self.game_entity.hero_entities.keys():
                    # hcid = self.game_entity.hero_entities[owner].card_id[:-3]
                    # cid = e.card_id[:-3]
                    # cname = 'ecards.' + hcid + '.' + cid + '.' + cid + '(e)'
                    # print(cname)
                    # try:
                    #     spell_entity = eval(cname)
                    # except Exception as ex:
                    #     logger.warning(ex)
                    spell_entity = SpellEntity(e)
                    # spell_entity = SpellEntity(e)
                    self.game_entity.hero_entities[owner].add_spell(spell_entity)
                pass
            # 对战技能记录
            elif e.type == CardType.SPELL:
                # print(e, e.tags, end='\n\n\n')
                pass

        # for h in self.game_entity.my_hero:
        #     if h.card_id[:-3] not in HEROS.keys():
        #         continue
        #     hd = HEROS[h.card_id[:-3]]
        #     for i, s in enumerate(h.spell):
        #         if i > 2:
        #             break
        #         s.read_from_config(hd[3][i])

        return self.game_entity

    pass


if __name__ == '__main__':
    path = "C:/var/Hearthstone/Logs/Power.log"
    hs_log = LogUtil(path)
    game_entity = hs_log.parse_game()
    for i in game_entity.my_hero:
        print(i)

    for i in game_entity.enemy_hero:
        print(i)

    pass
