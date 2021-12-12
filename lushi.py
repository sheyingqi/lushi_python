# -*- coding: utf-8 -*-
import logging
import random
import traceback

import pyautogui
import cv2
import time
import numpy as np
import argparse
import os
import yaml
import datetime
from PIL import Image
from types import SimpleNamespace

from utils.log_util import LogUtil
from utils.util import find_lushi_window, find_icon_location, restart_game, tuple_add, find_relative_loc, screenshot, find_lushi_raw_window
from utils.images import get_sub_np_array, get_burning_green_circles, get_burning_blue_lines
from utils.battle_ai import BattleAi
import utils.logging_util

logger = logging.getLogger()


class Agent:
    def __init__(self, cfg):
        if cfg['lang'].startswith('EN'):
            self.lang = 'eng'
            self.loc_file = 'config/locs_eng.yaml'
            self.img_folder = 'resource/imgs_eng_1024x768'
            self.title = 'hearthstone'
        elif cfg['lang'].startswith('ZH'):
            self.lang = 'chs'
            self.loc_file = 'config/locs_chs.yaml'
            self.img_folder = "resource/imgs_chs_1600x900"
            self.title = "炉石传说"
        else:
            raise ValueError(f"Language {cfg['lang']} is not supported yet")

        self.debug = False  # TODO check before commit, 什么时候把这个也做到按钮里
        self.icons = {}
        self.treasure_blacklist = {}
        self.heros_whitelist = {}
        self.heros_blacklist = {}
        self.game = None
        self.skill_seq_cache = {}
        self.start_seq = {}
        self.side = None
        self.surprise_in_mid = False
        self.surprise_relative_loc = None
        self.states = ['box', 'mercenaries', 'team_lock', 'travel', 'boss_list', 'team_list', 'map_not_ready',
                       'goto', 'show', 'teleport', 'start_game', 'member_not_ready', 'not_ready_dots', 'battle_ready',
                       'treasure_list', 'treasure_replace', 'destroy', 'blue_portal', 'boom', 'visitor_list',
                       'final_reward', 'final_reward2', 'final_confirm', 'close', 'ok', 'done']

        self.load_config(cfg)
        self.log_util = LogUtil(self.basic.hs_log)

    def read_sub_imgs(self, sub):
        imgs = [img for img in os.listdir(os.path.join(self.img_folder, sub)) if img.endswith('.png')]
        for img in imgs:
            k = img.split('.')[0]
            v = cv2.cvtColor(cv2.imread(os.path.join(self.img_folder, sub, img)), cv2.COLOR_BGR2GRAY)
            x = getattr(self, sub)
            x[k] = v

    def load_config(self, cfg):
        with open(self.loc_file, 'r', encoding='utf-8') as f:
            loc_cfg = yaml.safe_load(f)

        self.locs = SimpleNamespace(**loc_cfg['location'])
        for sub in ['icons', 'treasure_blacklist', 'heros_whitelist', 'heros_blacklist']:
            self.read_sub_imgs(sub)

        hero_info = cfg['hero']
        self.heros = {}
        for k, v in hero_info.items():
            spell_order = [int(x) - 1 for x in v[2].split(',')]
            self.heros[k] = [v[0], v[1], spell_order, v[3]]
            self.skill_seq_cache[k] = v[-2]
        del cfg['hero']
        cfg['hs_log'] = os.path.join(os.path.dirname(cfg['hs_path']), 'Logs', 'Power.log')
        self.basic = SimpleNamespace(**cfg)
        pyautogui.PAUSE = self.basic.delay

    def check_in_screen(self, name, prefix='icons'):

        rect, screen = find_lushi_window(self.title)
        try:
            icon = getattr(self, prefix)[name]
        except:
            return False, None, None
        success, X, Y, conf = find_icon_location(screen, icon, self.basic.confidence)
        del screen
        loc = X, Y
        return success, loc, rect

    # 检查并获取图片
    def check_and_screen(self, name, prefix='icons'):
        rect, screen = find_lushi_window(self.title)
        try:
            icon = getattr(self, prefix)[name]
        except:
            return False, None, None
        success, X, Y, conf = find_icon_location(screen, icon, self.basic.confidence)
        loc = X, Y
        return success, loc, rect, screen

    # 传入图片，匹配子图
    def find_in_image(self, screen, name, prefix='icons'):
        try:
            icon = getattr(self, prefix)[name]
        except:
            return False, None, None
        success, X, Y, conf = find_icon_location(screen, icon, self.basic.confidence)
        del screen
        loc = X, Y
        return success, loc, conf

    def scan_surprise_loc(self, rect, img_name = 'surprise'):
        # time.sleep(5)
        logger.info(f'Scanning surprise, rect: {rect}')
        pyautogui.moveTo(tuple_add(rect, self.locs.scroll))
        tic = time.time()
        while True:
            success, loc, rect = self.check_in_screen(img_name)
            if success:
                logger.info(f"Found surprise at start {loc}")
                return loc
            if self.check_in_screen('start_point')[0]:
                break
            if time.time() - tic > 10:
                return

        screen_images = []
        for i in range(10):
            success, loc, rect, the_img = self.check_and_screen(img_name)
            if 0 == i % 2 or success:
                _, the_img = find_lushi_window(self.title, to_gray=False, raw=True)
                # the_img.save("first_img.png")
                the_map_loc = self.locs.map_location
                sub_img = get_sub_np_array(the_img, the_map_loc[0], the_map_loc[1], the_map_loc[2], the_map_loc[3])  # [230, 80, 810, 620]
                screen_images.append(sub_img)
            if success:
                for _ in range(10):
                    pyautogui.scroll(-60)
                logger.info(f"Found surprise during scrolling {loc}")
                # full_map = images_to_full_map(screen_images)
                # cv2.imwrite("full_map_res3.jpg", full_map) # TODO rmove before submit
                return loc
            
            pyautogui.scroll(60) # 先截图，再滑

        logger.info("Did not found any surprise")
        return None

    def scan_surprise_in_map_loc(self, rect, img_name = 'surprise'):
        # time.sleep(5)
        logger.info(f'Scanning surprise, rect: {rect}')
        pyautogui.moveTo(tuple_add(rect, self.locs.scroll))
        tic = time.time()
        while True:
            success, loc, rect = self.check_in_screen("surprise")
            if success:
                logger.info(f"Found surprise at {loc}")
                return loc
            success, loc, rect = self.check_in_screen("off_surprise")
            if success:
                logger.info(f"Found off surprise at {loc}")
                return loc
            if self.check_in_screen('start_point')[0]:
                break
            if self.check_in_screen('map_not_ready')[0]:
                break
            if time.time() - tic > 10:
                return

        screen_images = []
        for i in range(10):
            success, loc, rect, the_img = self.check_and_screen("surprise")
            if not success:
                success, loc, rect = self.check_in_screen("off_surprise")
            if success:
                logger.info(f"Found off/on surprise at  {loc}")
                return loc
            if 0 == i % 2:
                _, the_img = find_lushi_window(self.title, to_gray=False, raw=True)
                # the_img.save("first_img.png")
                the_map_loc = self.locs.map_location
                sub_img = get_sub_np_array(the_img, the_map_loc[0], the_map_loc[1], the_map_loc[2], the_map_loc[3])  # [230, 80, 810, 620]
                screen_images.append(sub_img)
            if success:
                for _ in range(10):
                    pyautogui.scroll(-60)
                # full_map = images_to_full_map(screen_images)
                # cv2.imwrite("full_map_res2.jpg", full_map) # TODO remove befre commit 
                return loc
            
            pyautogui.scroll(60) # 先截图，再滑

        logger.info("Did not found any surprise")
        return None

    def task_submit(self, rect):

        if self.basic.auto_tasks:
            logger.info('Start submit task...')
            # select Camp Fire
            pyautogui.click(tuple_add(rect, self.locs.campfire))
            pyautogui.click(tuple_add(rect, self.locs.start_game))
            # check if a task finish
            time.sleep(1)
            _, img = find_lushi_window(self.title, to_gray=False, raw=True)
            lines = get_burning_blue_lines(img)
            if None is not lines and 0 < len(lines) :
                logger.info("some task finished ... ")
                for y in self.locs.tasks_y:
                    for x in self.locs.tasks_x:
                        # do task
                        pyautogui.click(tuple_add(rect, (x, y)))
                        pyautogui.click(tuple_add(rect, self.locs.tasks_abandon))
                        pyautogui.click(tuple_add(rect, self.locs.tasks_abandon_cancel))
                        pyautogui.click(tuple_add(rect, self.locs.tasks_abandon_cancel))
                        pyautogui.click(tuple_add(rect, self.locs.campfire_exit))

            # exit the campfire
            pyautogui.click(tuple_add(rect, self.locs.empty))
            # select first first boss of map
            pyautogui.click(tuple_add(rect, self.locs.first_boss))

    def start_battle(self):

        logger.info("Start battle, scanning battlefield")

        rect, screen = find_lushi_window(self.title)

        del self.log_util
        self.log_util = LogUtil(self.basic.hs_log)
        game = self.log_util.parse_game()

        first_x, mid_x, last_x, y = self.locs.heros
        n_my_hero = len(game.my_hero)
        is_even = n_my_hero % 2 == 0
        for i in range(n_my_hero):
            x_offset = (mid_x - first_x) * (-n_my_hero // 2 + i + 1)
            if is_even:
                x_offset -= (mid_x - first_x) // 2
            game.my_hero[i].set_pos(mid_x + x_offset + rect[0], y + rect[1])

        first_x, mid_x, last_x, y = self.locs.enemies
        n_enemy_hero = len(game.enemy_hero)
        is_even = n_enemy_hero % 2 == 0
        for i in range(n_enemy_hero):
            x_offset = (mid_x - first_x) * (-n_enemy_hero // 2 + i + 1)
            if is_even:
                x_offset -= (mid_x - first_x) // 2
            game.enemy_hero[i].set_pos(mid_x + x_offset + rect[0], y + rect[1])

        strategy = BattleAi.battle(game.my_hero, game.enemy_hero)
        pyautogui.click(tuple_add(rect, self.locs.empty))

        for hero_i, h in enumerate(game.my_hero):
            if h.lettuce_has_manually_selected_ability:
                continue

            pyautogui.click(h.pos)
            card_id = h.card_id[:-3]
            if card_id not in self.heros:
                skill_loc = tuple_add(rect, (self.locs.skills[0], self.locs.skills[-1]))
            else:
                skill_loc = None
                skill_seq = self.heros[card_id][-2]
                for skill_id in skill_seq:
                    skill_cooldown_round = h.spell[skill_id].lettuce_current_cooldown
                    if skill_cooldown_round == 0:
                        skill_loc = tuple_add(rect, (self.locs.skills[skill_id], self.locs.skills[-1]))
                        break
            pyautogui.click(skill_loc)
            enemy_id = strategy[hero_i]
            pyautogui.click(game.enemy_hero[enemy_id].pos)
            pyautogui.click(tuple_add(rect, self.locs.empty))

    def select_members(self):
        logger.info("Start select members")
        game = self.log_util.parse_game()
        rect, screen = find_lushi_window(self.title, to_gray=False)
        del screen
        hero_in_battle = [h for h in game.my_hero if h.card_id[:-3] in self.heros]
        if len(hero_in_battle) < 3:
            current_seq = {h.card_id[:-3]: i for i, h in enumerate(game.setaside_hero)}
            heros_sorted = {k: v[-1] for k, v in sorted(
                self.heros.items(), key=lambda item: item[1][-1])}
            card_id_seq = list(heros_sorted.keys())
            card_id_seq = [x for x in card_id_seq if x in current_seq]
            logger.info(f'current_seq {current_seq} card_id_seq {card_id_seq} hero_in_battle {len(hero_in_battle)}')
            for i in range(3 - len(hero_in_battle)):
                if len(card_id_seq) > 0:

                    cards_in_hand = len(card_id_seq)
                    card_id = card_id_seq.pop(0)

                    first_x, last_x, y = self.locs.members
                    mid_x = (first_x + last_x) // 2
                    current_pos = current_seq[card_id]
                    logger.info(f'cards_in_hand {cards_in_hand}')
                    if cards_in_hand > 3:
                        dis = (last_x - first_x) // (cards_in_hand - 1)
                        loc = (first_x + dis * current_pos, y)
                    elif cards_in_hand == 3:
                        logger.info(f'mid_x {mid_x} current_pos {current_pos}')
                        loc = (mid_x, y)
                        #loc = (mid_x + self.locs.members_distance * (current_pos - 1), y)
                    elif cards_in_hand == 2:
                        if current_pos == 0:
                            factor = -1
                        elif current_pos == 1:
                            factor = 1
                        else:
                            raise ValueError("Not possible")
                        loc = (mid_x, y)
                        # loc = (mid_x + self.locs.members_distance // 2 * factor, y)
                    elif cards_in_hand == 1:
                        loc = (mid_x, y)
                    else:
                        raise ValueError("Not possible")
                    logger.info(f'loc {loc} self.locs.dragto {self.locs.dragto}')
                    pyautogui.click(tuple_add(rect, loc))
                    pyautogui.moveTo(tuple_add(rect, self.locs.dragto))
                    pyautogui.click()

                    del current_seq[card_id]
                    for k, v in current_seq.items():
                        if v > current_pos:
                            current_seq[k] = v - 1

    # 从按照黑名单剔除宝藏，返回可选项，如果没有则返回[0], 最多返回：[0,1,2]
    def pick_treasure(self, screen):
        advice_idx = []
        not_advice_idx = []
        for key in self.treasure_blacklist.keys():
            for idx in range(3):
                loc = self.locs.treasures_location[idx]
                one_treasure = get_sub_np_array(screen, loc[0], loc[1], loc[2], loc[3])
                success, X, Y, conf = find_icon_location(one_treasure, self.treasure_blacklist[key],
                                                         self.basic.confidence)
                if success:
                    not_advice_idx.append(idx)
        # 去重
        not_advice_idx = list(set(not_advice_idx))
        logger.info(f'find treasure blacklist: {not_advice_idx}')
        if 2 < len(not_advice_idx) or 1 > len(not_advice_idx):
            return [0, 1, 2]
        else:
            for idx in range(3):
                if idx not in not_advice_idx:
                    advice_idx.append(idx)
            return advice_idx

    # 按照黑白名单选择神秘人选项，白名单命中，则选白名单的。黑名单命中则不选，如果白名单没命中，黑名单全命中，则随机选
    def pick_visitor(self, screen):
        is_in_whitelist = False
        is_in_blacklist = False
        idx_white_list = []
        idx_black_list = []
        for key in self.heros_whitelist.keys():
            success, loc, conf = self.find_in_image(screen, key, prefix='heros_whitelist')
            if success:
                is_in_whitelist = True
                dist = 1024
                the_index = 0
                for idx, v_loc in self.locs.visitors_location.items():
                    new_dist = abs(loc[0] - v_loc[2])
                    if new_dist < dist:  # right_x - right_x
                        the_index = idx
                        dist = new_dist

                idx_white_list.append(the_index)

        # 去重
        idx_white_list = list(set(idx_white_list))
        if is_in_whitelist and 0 < len(idx_white_list):
            logger.info(f'find visitor white list {idx_white_list}')
            return idx_white_list

        for key in self.heros_blacklist.keys():
            success, loc, conf = self.find_in_image(screen, key, prefix='heros_blacklist')
            if success:
                is_in_blacklist = True
                dist = 1024
                the_index = 0
                for idx, v_loc in self.locs.visitors_location.items():
                    new_dist = abs(loc[0] - v_loc[2])
                    if new_dist < dist:  # right_x - right_x
                        the_index = idx
                        dist = new_dist

                idx_black_list.append(the_index)

        # 去重
        idx_black_list = list(set(idx_black_list))

        if is_in_blacklist:
            logger.info(f'find visitor black list {idx_black_list}')
            if 2 < len(idx_black_list) or 1 > len(idx_black_list):
                return [0, 1, 2]
            else:
                advice_idx = []
                for idx in range(3):
                    if idx not in idx_black_list:
                        advice_idx.append(idx)
                return advice_idx

        return [0, 1, 2]  # 兜底返回

    def state_handler(self, state, tic, text):
        success, loc, rect = self.check_in_screen(text)
        '''
        self.states = ['box', 'mercenaries', 'team_lock', 'travel', 'boss_list', 'team_list', 'map_not_ready',
                  'goto', 'show', 'teleport', 'start_game', 'member_not_ready', 'not_ready_dots', 'battle_ready',
                  'treasure_list', 'treasure_replace', 'destroy', 'blue_portal', 'boom', 'visitor_list',
                  'final_reward', 'final_reward2', 'final_confirm', 'ok', 'close', 'done']
        '''
        if success:
            if state != text:
                state = text
                tic = time.time()

            if state in ['mercenaries', 'box', 'team_lock', 'close', 'ok', 'done']:
                logger.info(f'find {state}, try to click')
                pyautogui.click(tuple_add(rect, loc))

            if state == 'travel':
                logger.info(f'find {state}, try to click')
                self.surprise_relative_loc = None # 进地图清空
                pyautogui.click(tuple_add(rect, loc))
                pyautogui.click(tuple_add(rect, self.locs.travel))

            if state == 'boss_list':
                logger.info('find boss list, try to click')
                if self.basic.boss_id > 11:
                    pyautogui.click(tuple_add(rect, self.locs.boss_page_right))
                    time.sleep(0.5)
                    pyautogui.click(tuple_add(rect, self.locs.boss_page_right))
                    pyautogui.click(tuple_add(rect, loc))
                    pyautogui.click(tuple_add(rect, self.locs.start_game))
                elif self.basic.boss_id > 8:
                    the_id = self.basic.boss_id - 6
                    x_id = the_id % 3
                    y_id = the_id // 3
                    loc = (self.locs.boss[x_id], self.locs.boss[3 + y_id])
                    pyautogui.click(tuple_add(rect, self.locs.boss_page_left))
                    time.sleep(0.5)
                    pyautogui.click(tuple_add(rect, self.locs.boss_page_left))
                    time.sleep(0.5)
                    pyautogui.click(tuple_add(rect, self.locs.boss_page_right))
                    pyautogui.click(tuple_add(rect, loc))
                    pyautogui.click(tuple_add(rect, self.locs.start_game))
                elif self.basic.boss_id > 5:
                    id_standard = (self.basic.boss_id - 6) * 2
                    x_id = id_standard % 3
                    y_id = id_standard // 3
                    loc = (self.locs.boss[x_id], self.locs.boss[3 + y_id])

                    pyautogui.click(tuple_add(rect, self.locs.boss_page_left))
                    time.sleep(0.5)
                    pyautogui.click(tuple_add(rect, self.locs.boss_page_left))
                    time.sleep(0.5)
                    pyautogui.click(tuple_add(rect, self.locs.boss_page_right))
                    pyautogui.click(tuple_add(rect, loc))
                    pyautogui.click(tuple_add(rect, self.locs.start_game))
                else:
                    x_id = self.basic.boss_id % 3
                    y_id = self.basic.boss_id // 3
                    loc = (self.locs.boss[x_id], self.locs.boss[3 + y_id])
                    pyautogui.click(tuple_add(rect, self.locs.boss_page_left))
                    time.sleep(0.5)
                    pyautogui.click(tuple_add(rect, self.locs.boss_page_left))
                    time.sleep(0.5)
                    pyautogui.click(tuple_add(rect, loc))
                    pyautogui.click(tuple_add(rect, self.locs.start_game))

            if state == 'team_list':
                logger.info(f'find {state}, try to click')
                x_id = self.basic.team_id % 3
                y_id = self.basic.team_id // 3

                pyautogui.click(tuple_add(rect, (self.locs.teams[x_id], self.locs.teams[3 + y_id])))
                pyautogui.click(tuple_add(rect, self.locs.team_select))
                pyautogui.click(tuple_add(rect, self.locs.team_lock))
                time.sleep(7)  # avoid too low speed of entering map action to skip task_submit and scan_surprise
                self.task_submit(rect)
                # if self.basic.boss_id != 0:
                time.sleep(1)
                surprise_loc = self.scan_surprise_loc(rect)
                self.surprise_relative_loc = surprise_loc

                if surprise_loc is not None:
                    if surprise_loc[0] < self.locs.start_point[0]:
                        self.side = 'left'
                    else:
                        self.side = 'right'
                    first_x, mid_x, last_x, y = self.locs.focus
                    if np.abs(surprise_loc[0] - mid_x) < 100:
                        self.surprise_in_mid = True
                    else:
                        self.surprise_in_mid = False
                    logger.info(f'Surprise side {self.side}, surprise in middile {self.surprise_in_mid}')

            if state == 'map_not_ready':
                logger.info(f'find {state}, try to click next map')
                _, screen = find_lushi_raw_window(self.title)
                the_map_loc = self.locs.map_location # 只选取部分
                screen = get_sub_np_array(screen, the_map_loc[0], the_map_loc[1], the_map_loc[2], the_map_loc[3])  # [230, 80, 810, 620]
                circles = get_burning_green_circles(screen, 55, 110)
                if self.surprise_relative_loc is None : # 找下 漩涡的相对坐标
                    # success, loc, rect, the_img = self.check_and_screen('surprise')
                    surprise_loc = self.scan_surprise_in_map_loc(rect, img_name='off_surprise')
                    self.surprise_relative_loc = surprise_loc
                    # 翻了地图要回来
                    for i in range(-10,10):
                        _, screen = find_lushi_raw_window(self.title)
                        the_map_loc = self.locs.map_location # 只选取部分
                        screen = get_sub_np_array(screen, the_map_loc[0], the_map_loc[1], the_map_loc[2], the_map_loc[3])  # [230, 80, 810, 620]
                        circles = get_burning_green_circles(screen, 55, 110)
                        if circles is not None and len(circles) > 0 :
                            break

                        if i < 0:
                            pyautogui.scroll(-60)
                        else :
                            pyautogui.scroll(60)
                
                if circles is not None and 0 < len(circles):
                    loc = self.surprise_relative_loc
                    min_loc = None
                    if None != loc and 0 < len(loc) :
                        dist = 1024
                        for v_loc in circles[0, :]:  # 遍历矩阵每一行的数据
                            new_dist = abs(loc[0] - (v_loc[0] + the_map_loc[0]))
                            if new_dist < dist:  # right_x - right_x
                                min_loc = v_loc
                                dist = new_dist
                    else :
                        locs = circles[0, :]
                        min_loc = locs[-1]
                    
                    min_loc[1] = min_loc[1] + the_map_loc[1] # sub image y ++
                    min_loc[0] = min_loc[0] + the_map_loc[0]
                    logger.info(f'chose the  {min_loc}, to start game')
                    pyautogui.click(tuple_add(rect, (min_loc[0], min_loc[1])))
                    # check start_game:
                    success, loc, _ = self.check_in_screen("map_not_ready")
                    if success:
                       pyautogui.click(tuple_add(rect, self.locs.map_back))

                else: # 兜底action
                    first_x, mid_x, last_x, y = self.locs.focus
                    if self.side is None:
                        self.side = 'left'
                    if self.side == 'left':
                        if self.surprise_in_mid:
                            x1, x2, x3 = first_x, (first_x + mid_x) // 2, mid_x
                        else:
                            x1, x2, x3 = mid_x, (first_x + mid_x) // 2, first_x
                    else:
                        if self.surprise_in_mid:
                            x1, x2, x3 = last_x, (last_x + mid_x) // 2, mid_x
                        else:
                            x1, x2, x3 = mid_x, (last_x + mid_x) // 2, last_x

                    for x in (x1, x2, x3):
                        pyautogui.click(tuple_add(rect, (x, y)))

            if state in ['goto', 'show', 'teleport', 'start_game']:
                logger.info(f'find {state}, try to click')
                pyautogui.click(tuple_add(rect, self.locs.start_game))

            if state == 'member_not_ready':
                logger.info(f'find {state}, try to click')
                self.select_members()

            if state == 'not_ready_dots':
                logger.info(f'find {state}, try to click')
                self.start_battle()

            if state == 'battle_ready':
                logger.info(f'find {state}, try to click')
                pyautogui.click(tuple_add(rect, self.locs.start_battle))

            if state in ['treasure_list', 'treasure_replace']:
                logger.info(f'find {state}, try to click')
                _, screen = find_lushi_window(self.title)
                advice = self.pick_treasure(screen)

                t_id = random.choice(advice)
                treasure_loc = (self.locs.treasures[t_id], self.locs.treasures[-1])
                logger.info(f"click treasure : {t_id} at locs {treasure_loc}")

                pyautogui.click(tuple_add(rect, treasure_loc))
                # hero treasure screenshot before confirm
                if self.debug or self.basic.screenshot_treasure:
                    screenshot(self.title, f'treasure[{",".join(str(i) for i in advice)}]')
                pyautogui.click(tuple_add(rect, self.locs.treasures_collect))
                del screen

            if state in ['destroy', 'blue_portal', 'boom']:
                logger.info(f'find {state}, try to click')
                if self.basic.early_stop:
                    time.sleep(1)
                    logger.info("Early stopping")
                    pyautogui.click(tuple_add(rect, self.locs.view_team))
                    pyautogui.click(tuple_add(rect, self.locs.give_up))
                    pyautogui.click(tuple_add(rect, self.locs.give_up_cfm))
                else:
                    pyautogui.click(tuple_add(rect, self.locs.start_game))
                self.surprise_relative_loc = None # 漩涡已选择

            if state == 'visitor_list':
                logger.info(f'find {state}, try to click')
                _, screen = find_lushi_window(self.title)
                advice = self.pick_visitor(screen)
                t_id = random.choice(advice)
                visitor_loc = (self.locs.visitors[t_id], self.locs.visitors[-1])
                logger.info(f"click visitor : {t_id} at locs {visitor_loc}")
                pyautogui.click(tuple_add(rect, visitor_loc))

                time.sleep(1) # 多次截屏没有 截住
                # visitor, pick mission record
                if self.debug or self.basic.screenshot_visitor:
                    screenshot(self.title, state)

                pyautogui.click(tuple_add(rect, self.locs.visitors_confirm))

                for _ in range(4):
                    pyautogui.click(tuple_add(rect, self.locs.empty))

                logger.info("Visitors Selected")
                self.surprise_relative_loc = None # 漩涡已选择
                if self.basic.early_stop:
                    # 休眠2秒再退出，免得太卡导致失败
                    time.sleep(2)
                    logger.info("Early stopping")
                    pyautogui.click(tuple_add(rect, self.locs.view_team))
                    pyautogui.click(tuple_add(rect, self.locs.give_up))
                    pyautogui.click(tuple_add(rect, self.locs.give_up_cfm))

            if state in ['final_reward', 'final_reward2']:
                logger.info(f'find {state}, try to click')
                reward_count = self.basic.reward_count_dropdown
                reward_count = int(reward_count) if reward_count.isdigit() else reward_count

                reward_locs = eval(self.locs.rewards[reward_count])  # click all of 3， 4， 5 rewards location
                for loc in reward_locs:
                    pyautogui.moveTo(tuple_add(rect, loc))
                    pyautogui.click()

                if self.basic.screenshot_reward or self.debug:  # record reward by image
                    screenshot(self.title, state)

                pyautogui.moveTo(tuple_add(rect, self.locs.rewards['confirm']))
                pyautogui.click()

            if state == 'final_confirm':
                logger.info(f'find {state}, try to click')
                pyautogui.click(tuple_add(rect, self.locs.final_confirm))

        return success, tic, state, rect

    def run(self):
        if self.basic.auto_restart:
            while True:
                try:
                    self.run_pve()
                except AssertionError as e:
                    logger.error(f'错误：请删除炉石路径下的Logs/Power.log再重新打开!!!!')
                    break
                except Exception as e:
                    logger.error(f'错误：{e}', exc_info=True)
                    try:
                        if self.basic.screenshot_error:
                            screenshot(self.title, 'error')
                    except:
                        pass
                    restart_game(self.lang, self.basic.bn_path, False)
        else:
            self.run_pve()

    def run_pve(self):
        time.sleep(2)
        success, loc, rect = self.check_in_screen('mercenaries')
        tic = time.time()
        state = ""

        while True:
            pyautogui.click(tuple_add(rect, self.locs.empty))
            if time.time() - tic > self.basic.longest_waiting:
                if self.basic.screenshot_error:
                    screenshot(self.title, 'restart')
                if state == 'not_ready_dots' or state == 'member_not_ready':
                    pyautogui.rightClick(tuple_add(rect, self.locs.empty))
                    pyautogui.click(tuple_add(rect, self.locs.options))
                    pyautogui.click(tuple_add(rect, self.locs.surrender))
                elif state == 'map_not_ready':
                    pyautogui.click(tuple_add(rect, self.locs.view_team))
                    pyautogui.click(tuple_add(rect, self.locs.give_up))
                    pyautogui.click(tuple_add(rect, self.locs.give_up_cfm))
                else:
                    restart_game(self.lang, self.basic.bn_path)
                tic = time.time()
            else:
                logger.info(f"Last state {state}, time taken: {time.time() - tic}")

            for state_text in self.states:
                success, tic, state, rect = self.state_handler(state, tic, state_text)
                if success:
                    pyautogui.click(tuple_add(rect, self.locs.empty))


def run_from_gui(cfg):
    logger.debug(cfg)
    if cfg['lang'].startswith('EN'):
        lang = 'eng'
    elif cfg['lang'].startswith('ZH'):
        lang = 'chs'
    else:
        lang = None
    restart_game(lang, cfg['bn_path'], kill_existing=False)
    agent = Agent(cfg=cfg)
    agent.run()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lang', choices=['chs', 'eng'], default='chs', help='Choose Your Hearthstone Language')
    parser.add_argument('--config', default='config/default.yaml', help='launch config filename')
    parser.add_argument('--func', choices=['run', 'coor'], help='Run main function or find coordinates')
    args = parser.parse_args()

    if args.func == 'run':
        with open(args.config, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        if args.lang == 'chs':
            cfg['lang'] = 'ZH-1600x900'
        else:
            cfg['lang'] = 'EN-1024x768'

        run_from_gui(cfg)
    elif args.func == 'coor':
        if args.lang == 'chs':
            title = '炉石传说'
        elif args.lang == 'eng':
            title = 'Hearthstone'
        else:
            title = None
        while True:
            find_relative_loc(title)
            time.sleep(1)


if __name__ == '__main__':
    main()
