import sc2
# run_game启动游戏 指定游戏参数
# maps选地图 Race选种族 Difficulty选难度
from sc2 import run_game, maps, Race, Difficulty, UnitTypeId, AbilityId
# AI和内置电脑
from sc2.player import Bot, Computer
from sc2.constants import *
import random


class TheEmpire(sc2.BotAI):
    async def on_step(self, iteration: int):
        await self.distribute_workers()
        await self.build_workers()
        await self.build_supply()
        await self.depots_control()
        await self.build_refinery()
        if self.minerals > 400 and len(self.known_enemy_units) < 1:
            await self.expand()
        if self.minerals > 150 and self.units(COMMANDCENTER).amount > 1:
            await self.offensive_force_buildings()
        if self.supply_used < 40 or self.units(COMMANDCENTER).amount > 1:
            await self.build_offensive_force()
        if len(self.known_enemy_units) > 0:
            await self.attack()

    async def build_workers(self):
        num = 0
        for n in self.units(COMMANDCENTER).ready:
            num += n.ideal_harvesters
        if len(self.units(REFINERY).ready)*3 + num > len(self.units(SCV)) and self.units(SCV).amount < 60:
            for nexus in self.units(COMMANDCENTER).ready.idle:
                if self.can_afford(SCV):
                    await self.do(nexus.train(SCV))

    async def build_supply(self):
        center = self.units(COMMANDCENTER)
        if not center.exists:
            return
        else:
            center = center.random
        depot_placement_positions = self.main_base_ramp.corner_depots
        if self.supply_used < 60:
            if self.supply_left < 5 and not self.already_pending(SUPPLYDEPOT) and self.can_afford(SUPPLYDEPOT):
                if self.units(SUPPLYDEPOT).amount < 2:
                    scv = self.units(SCV).random
                    pos = depot_placement_positions.pop()
                    if await self.can_place(SUPPLYDEPOT, pos):
                        await self.do(scv.build(SUPPLYDEPOT, pos))
                    else:
                        await self.do(scv.build(SUPPLYDEPOT, depot_placement_positions.pop()))
                else:
                    await self.build(SUPPLYDEPOT, near=center, max_distance=40)
        elif self.supply_left < 7 and self.units(SUPPLYDEPOT).not_ready.amount < 2 and self.can_afford(SUPPLYDEPOT):
                await self.build(SUPPLYDEPOT, near=center, max_distance=40)

    async def depots_control(self):
        for depo in self.units(SUPPLYDEPOT).ready:
            for unit in self.known_enemy_units.not_structure:
                if unit.position.to2.distance_to(depo.position.to2) < 15:
                    break
            else:
                await self.do(depo(MORPH_SUPPLYDEPOT_LOWER))
        if self.known_enemy_units.exists:
            for depo in self.units(SUPPLYDEPOTLOWERED).ready:
                for unit in self.known_enemy_units.not_structure:
                    if unit.position.to2.distance_to(depo.position.to2) < 10:
                        await self.do(depo(MORPH_SUPPLYDEPOT_RAISE))
                        break

    async def build_refinery(self):
        for center in self.units(COMMANDCENTER).ready:
            vaspenes = self.state.vespene_geyser.closer_than(15.0, center)
            if self.units(REFINERY).amount >= self.units(COMMANDCENTER).amount * 2:
                break
            for vaspene in vaspenes:
                if not self.can_afford(REFINERY):
                    break
                worker = self.select_build_worker(vaspene.position)
                if worker is None:
                    break
                if (not self.units(REFINERY).closer_than(1.0, vaspene).exists) and self.units(SUPPLYDEPOT).amount > 0:
                    await self.do(worker.build(REFINERY, vaspene))

    async def expand(self):
        if self.units(COMMANDCENTER).amount < 3 and self.can_afford(COMMANDCENTER):
            await self.expand_now()
        if len(self.workers.idle) > 10 and self.can_afford(COMMANDCENTER) and not self.already_pending(COMMANDCENTER):
            await self.expand_now()

    async def offensive_force_buildings(self):
        barracks_placement_position = self.main_base_ramp.barracks_correct_placement
        if self.units(BARRACKS).amount < self.units(COMMANDCENTER).amount + 1:
            center = self.units(COMMANDCENTER).first
            if self.units(BARRACKS).amount < 1:
                scv = self.units(SCV).random
                await self.do(scv.build(BARRACKS, barracks_placement_position))
            else:
                p = center.position.towards_with_random_angle(self.game_info.map_center, 8)
                await self.build(BARRACKS, near=p, max_distance=70)
        for b in self.units(BARRACKS).ready.idle:
            if not b.has_add_on:
                await self.build_addon(b)

    async def build_addon(self, building):
        if building.has_add_on:
            return
        name = getattr(sc2.constants, (str(building.type_id))[11:] + "TECHLAB")
        # if not await self.can_cast(building, "BUILD_TECHLAB_")

        if self.units(name).amount < 2:
            await self.do(building.build(name))
            return
        name = getattr(sc2.constants, (str(building.type_id))[11:] + "REACTOR")
        await self.do(building.build(name))

    async def build_offensive_force(self):
        for b in self.units(BARRACKS).idle:
            if not b.has_add_on:
                break
            if self.can_afford(MARAUDER) and self.supply_left > 1 \
                    and self.units(MARAUDER).amount < self.units(MARINE).amount - 2:
                await self.do(b.train(MARAUDER))
            if self.can_afford(MARINE) and self.supply_left > 0 and b.noqueue:
                await self.do(b.train(MARINE))

    async def attack(self):
        army = self.units.of_type({UnitTypeId.MARINE, UnitTypeId.MARAUDER}).idle
        for a in army:
            if len(self.known_enemy_units) > 0:
                await self.do(a.attack(random.choice(self.known_enemy_units).position))
            elif self.supply_used > 150:
                if self.known_enemy_units.closer_than(40, self.enemy_start_locations[0]).amount > 0:
                    await self.do(a.attack(self.enemy_start_locations[0]))
                else:
                    await self.do(a.attack(random.choice(self.enemy_start_locations)))




    async def has_ability(self, ability, unit):
        abilities = await self.get_available_abilities(unit)
        if ability in abilities:
            return True
        else:
            return False

def main():
    run_game(maps.get("TritonLE"),
             [Bot(Race.Terran, TheEmpire()),
              Computer(Race.Protoss, Difficulty.Hard)],
             realtime = True)


if __name__ == '__main__':
    main()
