import sc2
# run_game启动游戏 指定游戏参数
# maps选地图 Race选种族 Difficulty选难度
from sc2 import run_game, maps, Race, Difficulty, UnitTypeId, AbilityId
# AI和内置电脑
from sc2.player import Bot, Computer, Human
from sc2.constants import *
import random
import time


class Rush(sc2.BotAI):
    async def on_step(self, iteration: int):
        if iteration == 0:
            await self.chat_send("(glhf)")

        nexus = self.units(NEXUS)
        if not nexus.exists:
            for unit in self.units:
                await self.do(unit.attack(self.enemy_start_locations[0]))
            return
        else:
            nexus = nexus.first

        if self.units(PROBE).amount < 20 and self.can_afford(PROBE) and self.supply_left > 0 and nexus.is_idle:
            if self.units(PYLON).ready.exists or self.units(PROBE).amount < 13:
                await self.do(nexus.build(PROBE))

        # if self.can_afford(PYLON) and self.supply_left < 6 and \
        #         (not self.already_pending(PYLON) or self.units(WARPGATE).amount >= 4):
        if self.supply_left < 5 and self.can_afford(PYLON) and not self.already_pending(PYLON) and\
                (not self.units(PYLON).exists or self.units(PYLON).amount == 3):
            places = self.main_base_ramp.corner_depots
            pos = places.pop()
            probe = self.units(PROBE).closest_to(pos)
            # print("base ramp")
            if await self.can_place(PYLON, pos):
                await self.do(probe.build(PYLON, pos))
            else:
                await self.do(probe.build(PYLON, places.pop()))
        elif self.supply_left < 5 and self.can_afford(PYLON) and not self.already_pending(PYLON) and\
                self.units(PYLON).amount == 1:
            pos = self.game_info.map_center.towards(self.enemy_start_locations[0], 16)
            # print("wild")
            await self.build(PYLON, near=pos)
        elif self.supply_left < 9 and self.can_afford(PYLON) and not self.already_pending(PYLON) and \
                self.units(PYLON).ready.amount > 1 and self.units(PYLON).not_ready.amount < 2:
            probe = self.units(PROBE).closest_to(nexus)
            # print("near base")
            await self.build(PYLON, near=nexus, unit=probe, max_distance=40)

        await self.build_assimilators()
        await self.handle_chronoboost(nexus)
        await self.distribute_workers()
        await self.handle_warp()
        await self.build_army()
        if iteration % 30 == 0:
            await self.attack()

        if self.units(PYLON).ready.exists and self.can_afford(GATEWAY)\
                and self.units(WARPGATE).amount < 4:
            if not self.units(GATEWAY).exists and not self.units(WARPGATE).exists and not self.already_pending(GATEWAY):
                pos = self.main_base_ramp.barracks_in_middle
                probe = self.units(PROBE).closest_to(pos)
                await self.do(probe.build(GATEWAY, pos))
            elif self.units(GATEWAY).amount <= 1 and not self.units(WARPGATE).exists:
                py = self.units(PYLON).ready.closest_to(nexus)
                await self.build(GATEWAY, near=py)
            elif self.units(GATEWAY).ready.amount == 2 and not self.units(WARPGATE).ready.exists and\
                    not self.already_pending(GATEWAY) and self.units(PYLON).ready.amount >= 2:
                pylon = self.units(PYLON).ready.furthest_to(nexus)
                await self.build(GATEWAY, near=pylon)
            elif self.units(WARPGATE).amount >= 2 and not self.already_pending(GATEWAY):
                pylon = self.units(PYLON).ready.closest_to(nexus)
                await self.build(GATEWAY, near=pylon)

        if self.units(PYLON).ready.exists and self.can_afford(CYBERNETICSCORE) and self.units(GATEWAY).ready.exists\
                and not self.units(CYBERNETICSCORE).exists and not self.already_pending(CYBERNETICSCORE):
            bg = self.units(GATEWAY).furthest_to(nexus)
            await self.build(CYBERNETICSCORE, near=bg)

    async def build_assimilators(self):
        if self.units(GATEWAY).amount < 2:
            return
        for nexus in self.units(NEXUS).ready:
            vespenes = self.state.vespene_geyser.closer_than(15.0, nexus)
            if self.units(ASSIMILATOR).amount >= self.units(NEXUS).amount*2:
                break
            for vespene in vespenes:
                if not self.can_afford(ASSIMILATOR):
                    break
                worker = self.select_build_worker(vespene.position)
                if worker is None:
                    break
                if not self.units(ASSIMILATOR).closer_than(1.0, vespene).exists:
                    await self.do(worker.build(ASSIMILATOR, vespene))
                    await self.do(worker.gather(self.state.mineral_field.closest_to(nexus), queue=True))

    async def handle_chronoboost(self, nexus):
        if nexus.energy >= 50:
            if self.units(CYBERNETICSCORE).ready.exists:
                cy = self.units(CYBERNETICSCORE).first
                if not cy.is_idle and not cy.has_buff(CHRONOBOOSTENERGYCOST):
                    await self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, cy))
                    return
            if self.units(WARPGATE).ready.exists:
                for w in self.units(WARPGATE).ready:
                    if not w.is_idle and not w.has_buff(CHRONOBOOSTENERGYCOST):
                        await self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, w))
                        return
            if self.units(GATEWAY).ready.exists:
                for g in self.units(GATEWAY).ready:
                    if not g.is_idle and not g.has_buff(CHRONOBOOSTENERGYCOST):
                        await self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, g))
                        return
            if not nexus.has_buff(CHRONOBOOSTENERGYCOST) and not nexus.is_idle \
                    and not self.units(CYBERNETICSCORE).exists:
                await self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, nexus))

    async def handle_warp(self):
        cy = self.units(CYBERNETICSCORE).ready
        if cy.exists:
            cy = cy.first
        else:
            return
        if self.units(GATEWAY).amount >= 1:
            if await self.has_ability(RESEARCH_WARPGATE, cy) and self.can_afford(RESEARCH_WARPGATE):
                await self.do(cy(RESEARCH_WARPGATE))
        if not await self.has_ability(RESEARCH_WARPGATE, cy) and self.units(GATEWAY).idle.exists:
            for g in self.units(GATEWAY).idle:
                if await self.can_cast(g, MORPH_WARPGATE):
                    await self.do(g(MORPH_WARPGATE))

    async def build_army(self):
        if self.units(GATEWAY).exists:
            for g in self.units(GATEWAY).ready.idle:
                if self.can_afford(STALKER) and self.units(CYBERNETICSCORE).ready.exists and self.supply_left > 1\
                        and self.units(STALKER).amount < 4:
                    await self.do(g.train(STALKER))
        if self.units(WARPGATE).exists:
            pylon = self.units(PYLON).furthest_to(self.start_location)
            for w in self.units(WARPGATE).ready.idle:
                # print("find warpgate")
                pos = pylon.position.to2.random_on_distance(2)
                pos = await self.find_placement(WARPGATETRAIN_STALKER, near=pos, placement_step=1)
                # print("find place")
                if self.can_afford(STALKER) and self.supply_left > 1 and \
                        await self.has_ability(WARPGATETRAIN_STALKER, w):
                    await self.do(w.warp_in(STALKER, pos))
                    # print("success")

    async def attack(self):
        units = self.units.of_type({UnitTypeId.STALKER, UnitTypeId.SENTRY}).ready.idle
        enemies = self.known_enemy_units
        if not enemies.exists and units.amount < 9:
            for a in units:
                await self.do(a.move(self.game_info.map_center))
            for a in self.units.of_type({UnitTypeId.STALKER, UnitTypeId.SENTRY}).ready:
                if a.is_moving and a.distance_to(self.game_info.map_center) < 10:
                    await self.do(a.stop())
            return
        if self.units(STALKER).ready.amount > 8:
            for a in units:
                await self.do(a.attack(self.enemy_start_locations[0]))
        if enemies.not_structure.exists:
            if units.amount < enemies.not_structure.exclude_type({PROBE, DRONE, OVERLORD, SCV}).amount \
                    or units.amount < 4:
                return
            army = self.units.of_type({UnitTypeId.STALKER, UnitTypeId.SENTRY}).ready
            for a in army:
                if a.order_target == self.enemy_start_locations[0]:
                    important = enemies.of_type({STALKER, SENTRY, ROACH, MARAUDER, SIEGETANK})
                    if important.exists:
                        await self.do(a.attack(random.choice(important)))
                    else:
                        await self.do(a.attack(random.choice(enemies).position))

    async def has_ability(self, ability, unit):
        abilities = await self.get_available_abilities(unit)
        if ability in abilities:
            return True
        else:
            return False


def main():
    run_game(maps.get("TritonLE"),
             [Bot(Race.Protoss, Rush()),
             Computer(Race.Protoss, Difficulty.Hard)],
             realtime=True)
    # run_game(maps.get("TritonLE"), [
    #         Human(Race.Zerg),
    #         Bot(Race.Protoss, Rush())],
    #         realtime=True, save_replay_as="ZvP.SC2Replay")


if __name__ == '__main__':
    main()
