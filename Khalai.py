import sc2
from sc2 import maps
# , Race, Difficulty, UnitTypeId, AbilityId
from sc2.player import Bot, Computer
from sc2.main import run_game
from sc2.data import Race, Difficulty
from sc2.bot_ai import BotAI
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId

import random


class KhalaiStar(BotAI):
    async def on_step(self, iteration: int):
        if iteration == 0:
            await self.chat_send("(glhf)")

        # Attack with all workers if we don't have any nexuses left
        if not self.townhalls.ready:
            for worker in self.workers:
                worker.attack(self.enemy_start_locations[0])
            return
        nexus = self.townhalls.ready.random

        await self.distribute_workers()
        # for nexus in self.units(NEXUS).ready:
        #     await self.handle_chronoboost(nexus)
        await self.build_workers(nexus)

        if not self.supply_cap >= 200:
            await self.build_pylons(nexus)

        # await self.build_assimilators()

        if self.minerals > 400 \
                and self.townhalls.amount < 3 \
                and self.enemy_units.exclude_type({UnitTypeId.OVERLORD, UnitTypeId.DRONE, UnitTypeId.PROBE, UnitTypeId.SCV}).amount == 0:
            await self.expand()

        if self.minerals > 150 and self.townhalls.ready.amount > 1:
            await self.offensive_force_buildings()
        if self.supply_used < 40 or self.townhalls.ready.amount > 1:
            await self.build_offensive_force()
        # if self.supply_army > 40:
        #     await self.handle_upgrades()

        await self.attack()

    async def build_workers(self, nexus):
        if self.supply_workers + self.already_pending(UnitTypeId.PROBE) < self.townhalls.amount * 22 and nexus.is_idle:
            if self.can_afford(UnitTypeId.PROBE):
                nexus.train(UnitTypeId.PROBE)

    async def build_pylons(self, nexus):
        if self.supply_used < 50:
            if self.supply_left < 3 and not self.already_pending(UnitTypeId.PYLON):
                await self.build(UnitTypeId.PYLON, near=nexus, max_distance=40)
        else:
            if self.supply_left < 6 and self.units(UnitTypeId.PYLON).not_ready.amount < 2:
                await self.build(UnitTypeId.PYLON, near=nexus, max_distance=40)

    async def build_assimilators(self):
        for nexus in self.units(UnitTypeId.NEXUS).ready:
            vaspenes = self.state.vespene_geyser.closer_than(15.0, nexus)
            if self.units(ASSIMILATOR).amount >= self.units(NEXUS).amount*2:
                break
            for vaspene in vaspenes:
                if not self.can_afford(UnitTypeId.ASSIMILATOR):
                    break
                worker = self.select_build_worker(vaspene.position)
                if worker is None:
                    break
                if (not self.units(UnitTypeId.ASSIMILATOR).closer_than(1.0, vaspene).exists) and self.units(UnitTypeId.PYLON).amount > 0:
                    await self.do(worker.build(UnitTypeId.ASSIMILATOR, vaspene))

    async def expand(self):
        if self.units(UnitTypeId.NEXUS).amount < 3 and self.can_afford(UnitTypeId.NEXUS):
            await self.expand_now()
        if len(self.workers.idle) > 10 and self.can_afford(UnitTypeId.NEXUS) and not self.already_pending(UnitTypeId.NEXUS):
            await self.expand_now()

    async def handle_chronoboost(self, nexus):
        if nexus.energy >= 50:
            if self.units(CYBERNETICSCORE).ready.exists:
                cy = self.units(CYBERNETICSCORE).first
                if not cy.noqueue and not cy.has_buff(CHRONOBOOSTENERGYCOST):
                    await self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, cy))
                    return
            if self.units(FORGE).ready.exists:
                f = self.units(FORGE).first
                if not f.noqueue and not f.has_buff(CHRONOBOOSTENERGYCOST):
                    await self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, f))
                    return
            if self.units(STARGATE).ready.exists:
                s = self.units(STARGATE).first
                if not s.noqueue and not s.has_buff(CHRONOBOOSTENERGYCOST):
                    await self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, s))
                    return
            if self.units(GATEWAY).ready.exists:
                for g in self.units(GATEWAY).ready:
                    if not g.noqueue and not g.has_buff(CHRONOBOOSTENERGYCOST):
                        await self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, g))
                        return
            if not nexus.has_buff(CHRONOBOOSTENERGYCOST):
                await self.do(nexus(EFFECT_CHRONOBOOSTENERGYCOST, nexus))

    async def offensive_force_buildings(self):
        pylon = self.structures(UnitTypeId.PYLON).ready.random
        if pylon:
            # if self.units(GATEWAY).ready.exists and not self.units(CYBERNETICSCORE).exists:
            #     await self.build(CYBERNETICSCORE, near=pylon)
            #     return
            # if self.units(GATEWAY).ready.exists and not self.units(FORGE).exists:
            #     await self.build(FORGE, near=pylon)
            #     return
            if self.structures(UnitTypeId.GATEWAY).amount < self.structures(UnitTypeId.NEXUS).amount:
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
        for gate in self.structures(UnitTypeId.GATEWAY).ready.idle:
            # if self.can_afford(STALKER) and self.supply_left > 2 and self.units(STALKER).amount < self.units(VOIDRAY).amount + 2:
            #     await self.do(gate.train(STALKER))
            if self.can_afford(UnitTypeId.ZEALOT) and self.supply_left > 1 and self.supply_army < 100:
                gate.train(UnitTypeId.ZEALOT)
            # if self.can_afford(ADEPT) and self.supply_left > 1 and self.units(ADEPT).amount < self.units(ZEALOT).amount\
            #         and self.units(CYBERNETICSCORE).ready.exists:
            #     await self.do(gate.train(ADEPT))
        # for rg in self.units(ROBOTICSFACILITY).ready.idle:
        #     if self.can_afford(OBSERVER) and self.supply_left > 0 and not self.units(OBSERVER).exists:
        #         await self.do(rg.train(OBSERVER))

    async def handle_upgrades(self):
        if self.units(TWILIGHTCOUNCIL).ready.exists:
            twilight = self.units(TWILIGHTCOUNCIL).first
            if twilight.noqueue:
                if await self.has_ability(RESEARCH_CHARGE, twilight):
                    if self.can_afford(RESEARCH_CHARGE):
                        await self.do(twilight(RESEARCH_CHARGE))
                    return
        if self.units(FORGE).ready.exists:
            forge = self.units(FORGE).first
            if forge.noqueue:
                for upgrade_level in range(1, 4):
                    if upgrade_level > 1 and self.supply_used < 100:
                        break
                    upgrade_weapon_id = getattr(sc2.constants,
                                                "FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL" + str(upgrade_level))
                    upgrade_armor_id = getattr(sc2.constants, "FORGERESEARCH_PROTOSSGROUNDARMORLEVEL" + str(upgrade_level))
                    shield_armor_id = getattr(sc2.constants, "FORGERESEARCH_PROTOSSSHIELDSLEVEL" + str(upgrade_level))
                    if await self.has_ability(upgrade_weapon_id, forge):
                        if self.can_afford(upgrade_weapon_id):
                            await self.do(forge(upgrade_weapon_id))
                        return
                    elif await self.has_ability(upgrade_armor_id, forge):
                        if self.can_afford(upgrade_armor_id):
                            await self.do(forge(upgrade_armor_id))
                        return
                    elif await self.has_ability(shield_armor_id, forge):
                        if self.can_afford(shield_armor_id):
                            await self.do(forge(shield_armor_id))
                        return
        elif not self.units(CYBERNETICSCORE).ready.exists:
            return
        cy = self.units(CYBERNETICSCORE).first
        if cy.noqueue and self.units(STARGATE).amount > 0:
            #for upgrade_level in range(1, 4):
            upgrade_level = 1
            upgrade_weapon_id = getattr(sc2.constants,
                                        "CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL" + str(upgrade_level))
            upgrade_armor_id = getattr(sc2.constants,
                                       "CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL" + str(upgrade_level))
            if await self.has_ability(upgrade_weapon_id, cy):
                if self.can_afford(upgrade_weapon_id):
                    await self.do(cy(upgrade_weapon_id))
                return
            elif await self.has_ability(upgrade_armor_id, cy):
                if self.can_afford(upgrade_armor_id):
                    await self.do(cy(upgrade_armor_id))
                return

    async def attack(self):
        army_units = self.units(UnitTypeId.ZEALOT).ready
        targets = (self.enemy_units | self.enemy_structures).filter(lambda unit: unit.can_be_attacked)
        for a in army_units.idle:
            if targets:
                target = targets.closest_to(a)
                a.attack(target)
            elif self.supply_used > 150:
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

    # Check if a unit has an ability available (also checks upgrade costs??)
    async def has_ability(self, ability, unit):
        abilities = await self.get_available_abilities(unit)
        if ability in abilities:
            return True
        else:
            return False


def main():
    run_game(maps.get("AcropolisLE"),
             [Bot(Race.Protoss, KhalaiStar()),
             Computer(Race.Protoss, Difficulty.Medium)],
             realtime=False)
    # run_game(maps.get("AcropolisLE"), [
    #         Human(Race.Zerg),
    #         Bot(Race.Protoss, KhalaiStar())],
    #         realtime=True, save_replay_as="Protoss vs Protoss.SC2Replay")


if __name__ == '__main__':
    main()
