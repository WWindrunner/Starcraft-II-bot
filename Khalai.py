import sc2
from sc2 import maps
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

import random


class KhalaiStar(BotAI):
    def __init__(self):
        pass

    async def on_start(self):
        self.client.game_step = 3

    async def on_step(self, iteration: int):
        if iteration == 0:
            await self.chat_send("(glhf)")

        # Attack with all workers no nexuses left
        if not self.townhalls.ready:
            for worker in self.workers:
                worker.attack(self.enemy_start_locations[0])
            return
        nexus = self.townhalls.ready.random

        # Manage gathering, building, and expand
        await self.distribute_workers()
        await self.handle_chronoboost(nexus)
        await self.build_workers(nexus)
        await self.build_assimilators()
        if not self.supply_cap >= 200:
            await self.build_pylons(nexus)
        await self.expand()

        # Manage army and tech
        if self.townhalls.ready.amount > 1:
            await self.offensive_force_buildings()
        if self.supply_used < 40 or self.townhalls.ready.amount > 1:
            await self.handle_upgrade()
            await self.build_offensive_force()
        await self.attack()

    async def build_workers(self, nexus):
        if self.supply_workers + self.already_pending(UnitTypeId.PROBE) < self.townhalls.amount * 22 and nexus.is_idle:
            if self.can_afford(UnitTypeId.PROBE):
                nexus.train(UnitTypeId.PROBE)

    async def build_pylons(self, nexus):
        map_center = self.game_info.map_center
        position = nexus.position.towards(map_center, distance=8)
        if self.supply_used < 50:
            if self.supply_left < 4 and not self.already_pending(UnitTypeId.PYLON):
                await self.build(UnitTypeId.PYLON, near=position, placement_step=5)
        else:
            if self.supply_left < 10 and not self.already_pending(UnitTypeId.PYLON):
                await self.build(UnitTypeId.PYLON, near=position, placement_step=5)

    async def build_assimilators(self):
        for nexus in self.townhalls.ready:
            vaspenes = self.vespene_geyser.closer_than(15, nexus)
            for vaspene in vaspenes:
                if not self.can_afford(UnitTypeId.ASSIMILATOR):
                    break
                worker = self.select_build_worker(vaspene.position)
                if worker is None:
                    break
                if not self.gas_buildings or not self.gas_buildings.closer_than(1, vaspene):
                    worker.build_gas(vaspene)
                    worker.stop(queue=True)

    async def expand(self):
        # Expand when we have less than 2 bases
        if self.structures(UnitTypeId.NEXUS).amount < 2 and self.can_afford(UnitTypeId.NEXUS):
            await self.expand_now()
        # Expand when we have idle workers
        if len(self.workers.idle) > 10 \
                and self.can_afford(UnitTypeId.NEXUS) and not self.already_pending(UnitTypeId.NEXUS):
            await self.expand_now()

    async def handle_chronoboost(self, nexus):
        if nexus.energy >= 50:
            if self.structures(UnitTypeId.CYBERNETICSCORE).ready.exists:
                cy = self.structures(UnitTypeId.CYBERNETICSCORE).first
                if not cy.is_idle and not cy.has_buff(BuffId.CHRONOBOOSTENERGYCOST):
                    nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, cy)
                    return
            # if self.structures(UnitTypeId.FORGE).ready.exists:
            #     f = self.structures(UnitTypeId.FORGE).first
            #     if not f.is_idle and not f.has_buff(CHRONOBOOSTENERGYCOST):
            #         await self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, f))
            #         return
            # if self.structures(UnitTypeId.STARGATE).ready.exists:
            #     s = self.structures(UnitTypeId.STARGATE).first
            #     if not s.noqueue and not s.has_buff(CHRONOBOOSTENERGYCOST):
            #         await self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, s))
            #         return
            if not nexus.is_idle and not nexus.has_buff(BuffId.CHRONOBOOSTENERGYCOST):
                nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus)

    async def offensive_force_buildings(self):
        pylon = self.structures(UnitTypeId.PYLON).ready.random
        if pylon:
            if self.structures(UnitTypeId.GATEWAY).ready:
                # If we have no cyber core, build one
                if not self.structures(UnitTypeId.CYBERNETICSCORE):
                    if (
                            self.can_afford(UnitTypeId.CYBERNETICSCORE)
                            and self.already_pending(UnitTypeId.CYBERNETICSCORE) == 0
                    ):
                        await self.build(UnitTypeId.CYBERNETICSCORE, near=pylon)

            # Build up to 4 gates
            if (
                    self.can_afford(UnitTypeId.GATEWAY)
                    and self.structures(UnitTypeId.WARPGATE).amount + self.structures(UnitTypeId.GATEWAY).amount < 4
            ):
                await self.build(UnitTypeId.GATEWAY, near=pylon)
            # if self.units(CYBERNETICSCORE).ready.exists and not self.units(TWILIGHTCOUNCIL).exists:
            #     await self.build(TWILIGHTCOUNCIL, near=pylon)
            #     return
            # if self.units(CYBERNETICSCORE).ready.exists:
            #     if self.units(STARGATE).amount < self.units(NEXUS).amount:
            #         if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
            #             await self.build(STARGATE, near=pylon)
            #     if self.units(ROBOTICSFACILITY).amount < 1 and self.units(STARGATE).ready.exists:
            #         if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
            #             await self.build(ROBOTICSFACILITY, near=pylon)

    async def build_offensive_force(self):
        # for sg in self.units(STARGATE).ready.idle:
        #     if self.can_afford(VOIDRAY) and self.supply_left > 2:
        #         await self.do(sg.train(VOIDRAY))
        # Train gateway units
        for gate in self.structures(UnitTypeId.GATEWAY).ready.idle:
            if self.can_afford(UnitTypeId.ZEALOT) and self.supply_left > 1 and self.supply_army < 10:
                gate.train(UnitTypeId.ZEALOT)

        # Warp units
        for warpgate in self.structures(UnitTypeId.WARPGATE).ready:
            abilities = await self.get_available_abilities(warpgate)
            pylon = self.structures(UnitTypeId.PYLON).closest_to(self.enemy_start_locations[0])
            pos = pylon.position.to2.random_on_distance(4)
            if AbilityId.WARPGATETRAIN_STALKER in abilities\
                    and self.can_afford(UnitTypeId.STALKER):
                placement = await self.find_placement(AbilityId.WARPGATETRAIN_STALKER, pos, placement_step=1)
                if placement:
                    warpgate.warp_in(UnitTypeId.STALKER, placement)
            if AbilityId.TRAINWARP_ADEPT in abilities\
                    and self.can_afford(UnitTypeId.ADEPT):
                placement = await self.find_placement(AbilityId.TRAINWARP_ADEPT, pos, placement_step=1)
                if placement:
                    warpgate.warp_in(UnitTypeId.ADEPT, placement)
            if AbilityId.WARPGATETRAIN_ZEALOT in abilities\
                    and self.can_afford(UnitTypeId.ZEALOT):
                placement = await self.find_placement(AbilityId.WARPGATETRAIN_ZEALOT, pos, placement_step=1)
                if placement:
                    warpgate.warp_in(UnitTypeId.ZEALOT, placement)

    async def handle_upgrade(self):
        if (
                self.structures(UnitTypeId.CYBERNETICSCORE).ready and self.can_afford(AbilityId.RESEARCH_WARPGATE)
                and self.already_pending_upgrade(UpgradeId.WARPGATERESEARCH) == 0
        ):
            ccore = self.structures(UnitTypeId.CYBERNETICSCORE).ready.first
            ccore.research(UpgradeId.WARPGATERESEARCH)

        for gateway in self.structures(UnitTypeId.GATEWAY).ready.idle:
            if self.already_pending_upgrade(UpgradeId.WARPGATERESEARCH) == 1:
                gateway(AbilityId.MORPH_WARPGATE)

        # if self.units(TWILIGHTCOUNCIL).ready.exists:
        #     twilight = self.units(TWILIGHTCOUNCIL).first
        #     if twilight.noqueue:
        #         if await self.has_ability(RESEARCH_CHARGE, twilight):
        #             if self.can_afford(RESEARCH_CHARGE):
        #                 await self.do(twilight(RESEARCH_CHARGE))
        #             return
        # if self.units(FORGE).ready.exists:
        #     forge = self.units(FORGE).first
        #     if forge.noqueue:
        #         for upgrade_level in range(1, 4):
        #             if upgrade_level > 1 and self.supply_used < 100:
        #                 break
        #             upgrade_weapon_id = getattr(sc2.constants,
        #                                         "FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL" + str(upgrade_level))
        #             upgrade_armor_id = getattr(sc2.constants, "FORGERESEARCH_PROTOSSGROUNDARMORLEVEL" + str(upgrade_level))
        #             shield_armor_id = getattr(sc2.constants, "FORGERESEARCH_PROTOSSSHIELDSLEVEL" + str(upgrade_level))
        #             if await self.has_ability(upgrade_weapon_id, forge):
        #                 if self.can_afford(upgrade_weapon_id):
        #                     await self.do(forge(upgrade_weapon_id))
        #                 return
        #             elif await self.has_ability(upgrade_armor_id, forge):
        #                 if self.can_afford(upgrade_armor_id):
        #                     await self.do(forge(upgrade_armor_id))
        #                 return
        #             elif await self.has_ability(shield_armor_id, forge):
        #                 if self.can_afford(shield_armor_id):
        #                     await self.do(forge(shield_armor_id))
        #                 return
        # elif not self.units(CYBERNETICSCORE).ready.exists:
        #     return
        # cy = self.structures(UnitTypeId.CYBERNETICSCORE).first
        # if cy.noqueue and self.units(STARGATE).amount > 0:
        #     #for upgrade_level in range(1, 4):
        #     upgrade_level = 1
        #     upgrade_weapon_id = getattr(sc2.constants,
        #                                 "CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL" + str(upgrade_level))
        #     upgrade_armor_id = getattr(sc2.constants,
        #                                "CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL" + str(upgrade_level))
        #     if await self.has_ability(upgrade_weapon_id, cy):
        #         if self.can_afford(upgrade_weapon_id):
        #             await self.do(cy(upgrade_weapon_id))
        #         return
        #     elif await self.has_ability(upgrade_armor_id, cy):
        #         if self.can_afford(upgrade_armor_id):
        #             await self.do(cy(upgrade_armor_id))
        #         return

    async def attack(self):
        army_units = self.units.of_type({UnitTypeId.ZEALOT, UnitTypeId.STALKER, UnitTypeId.ADEPT})
        targets = (self.enemy_units | self.enemy_structures).filter(lambda unit: unit.can_be_attacked)
        for a in army_units.idle:
            if targets:
                target = targets.closest_to(a)
                a.attack(target)
            elif self.supply_used > 100:
                a.attack(self.enemy_start_locations[0])

    # def find_target(self, unit):
    #     if len(self.known_enemy_units) > 0:
    #         return self.known_enemy_units.closest_to(unit.position).position
    #     elif len(self.known_enemy_structures) > 0:
    #         return self.known_enemy_structures.closest_to(unit.position).position
    #     elif self.known_enemy_units.closer_than(40, self.enemy_start_locations[0]):
    #         return self.enemy_start_locations[0]
    #     else:
    #         return random.choice(self.enemy_start_locations)


def main():
    run_game(maps.get("AcropolisLE"),
             [Bot(Race.Protoss, KhalaiStar()),
             Computer(Race.Protoss, Difficulty.Hard)],
             realtime=False)
    # run_game(maps.get("AcropolisLE"), [
    #         Human(Race.Zerg),
    #         Bot(Race.Protoss, KhalaiStar())],
    #         realtime=True, save_replay_as="ZvP.SC2Replay")


if __name__ == '__main__':
    main()
