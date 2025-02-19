import json
from typing import List, Dict
from pprint import pprint
import copy
import random
import ast


class ActionSimulator:
    SIMULATE_LIMIT = 50

    def __init__(self):
        # action_rules = self.load_action_rules()
        self.action_runner = ActionRunner()
        self.final_action_list = []

    def simulate_single_action(self, action: str, state):
        """
        Simulate the action on the state, return the next state and reward
        """
        args = action.split(" ")
        action_name = args[0]
        action_args = args[1:]
        return self.action_runner.run_action(
            action_name,
            action_args,
            state,
        )

    def simulate(self, action_list, initial_state, market_data):
        """
        Simulate the action list on the initial state, return the final state and reward
        """
        self.action_runner.market_data = market_data
        state = copy.deepcopy(initial_state)
        state["inventory"] = {
            item.lower(): num for item, num in state["inventory"].items()
        }
        state["location"] = ""
        for action in action_list:
            actions = self.simulate_single_action(action, state)
            self.final_action_list.extend(actions)
        self.final_check_location()

        return self.final_action_list[: ActionSimulator.SIMULATE_LIMIT]

    def load_action_rules(self):
        """
        Load the action rules from the config file
        """
        action_rules = json.load(open("core/files/action_rules.json"))
        return action_rules

    def final_check_location(self):
        """
        delete duplicate goto actions
        """
        i = 0
        current_location = ""
        # delete two types of goto actions:
        # 1. consecutive goto actions, delete the first one
        # 2. goto the location where the character is already at, delete the later one
        while i < len(self.final_action_list):
            if self.final_action_list[i].startswith("goto"):
                if self.final_action_list[i].split(" ")[1] == current_location:
                    del self.final_action_list[i]
                else:
                    if i + 1 < len(self.final_action_list) and self.final_action_list[
                        i + 1
                    ].startswith("goto"):
                        del self.final_action_list[i]
                    else:
                        current_location = self.final_action_list[i].split(" ")[1]
                        i += 1
            else:
                i += 1


class ActionRunner:
    def __init__(self):
        self.actions = []
        self.market_data = {}
        self.craft_recipes, self.cost_dict, self.location = self.load_craft_recipes()
        # print(self.location)

    def load_craft_recipes(self):
        """
        Load the craft recipes from the config file
        """
        craft_recipes = json.load(open("core/files/skill2actions.json"))
        final_recipes = {}
        cost_dict = {}

        for _, skill in craft_recipes.items():
            cost = skill["cost"]
            for product, materials in skill["materials"].items():
                final_recipes[product] = materials
                cost_dict[product] = cost

        location_dict = json.load(open("core/files/location.json"))

        return final_recipes, cost_dict, location_dict

    def run_action(self, action_name: str, action_args: List[str], state: Dict):
        """
        Run the action on the state, return the next state and reward
        """
        self.actions = [f"{action_name} {' '.join(action_args)}"]

        if action_name == "goto":
            self.goto(action_args, state)

        if action_name == "sleep":
            self.sleep(action_args, state)

        if action_name == "study":
            self.study(action_args, state)

        if action_name == "seedoctor":
            self.seedoctor(action_args, state)

        if action_name == "work":
            self.actions = self.work(action_args, state)

        if action_name == "use":
            self.use(action_args, state, self.market_data)

        if action_name == "buy":
            self.buy(action_args, state, self.market_data)

        if action_name == "sell":
            self.sell(action_args, state, self.market_data)

        if action_name == "craft":
            self.actions = self.craft(action_args, state, self.market_data)

        if state["hungry"] <= 30:
            if state["hungry"] < 0:
                state["hungry"] = 0
            self.actions = (
                self.craft_or_buy_eating_stuff(
                    state, random.randint(40, 80) - state["hungry"]
                )
                + self.actions
            )

        return self.actions

    def goto(self, action_args: List[str], state: Dict):
        """
        Go to a place
        """
        action_args[0] = action_args[0].lower()
        if action_args[0] not in [
            "school",
            "workshop",
            "home",
            "farm",
            "mall",
            "square",
            "councilhall",
            "hospital",
            "fruit",
            "harvest",
            "fishing",
            "mine",
            "orchard",
            "foodfactory",
            "factory",
            "garden",
            "policestation",
            "library",
            "supermarket",
            "canteen",
        ]:
            # Current: Give up goto
            self.actions = []
            return self.actions

        state["location"] = action_args[0]
        state["hungry"] -= 2
        return self.actions

    def sleep(self, action_args: List[str], state: Dict):
        """
        Sleep to recover energy
        """
        try:
            # test if the args[0] is a number
            hours = int(action_args[0])
        except ValueError:
            # Current: Give up sleep
            self.actions = []
            return self.actions

        if state["location"] != "home":
            # add goto action
            self.actions.insert(0, "goto home")
            state["location"] = "home"
        state["energy"] += hours * 10
        state["hungry"] -= hours * 2
        return self.actions

    def study(self, action_args: List[str], state: Dict):
        """
        Study to achieve a higher degree
        """
        try:
            # test if the args[0] is a number
            hours = int(action_args[0])

        except ValueError:
            # Current: Give up study
            self.actions = []
            return self.actions

        if state["money"] < hours * 100:
            # Current: Give up study
            self.actions = []
            return self.actions

        if state["energy"] < hours * 10:
            lack_energy = (hours * 10 - state["energy"]) // 10 + 1
            self.actions.insert(0, f"sleep {lack_energy}")
            self.actions.insert(0, "goto home")
            state["location"] = "home"

        if state["location"] != "school":
            # add goto action
            self.actions.insert(-1, "goto school")
            state["location"] = "school"

        state["money"] -= hours * 50
        state["energy"] -= hours * 3
        state["hungry"] -= hours * 2
        state["education_experience"] += hours * 5
        return self.actions

    def seedoctor(self, action_args: List[str], state: Dict):
        """
        See a doctor
        """
        try:
            # test if the args[0] is a number
            hours = int(action_args[0])
        except ValueError:
            # Current: Give up see doctor
            self.actions = []
            return self.actions

        if state["money"] < hours * 100:
            # Current: Give up see doctor
            self.actions = []
            return self.actions

        if state["location"] != "hospital":
            # add goto action
            self.actions.insert(-1, "goto hospital")
            state["location"] = "hospital"

        state["money"] -= hours * 50
        state["health"] += hours * 20
        state["hungry"] -= hours * 2
        return self.actions

    def work(self, action_args: List[str], state: Dict):
        """
        Work to earn money
        """
        actions = []
        try:
            # test if the args[0] is a number
            hours = int(action_args[0])
        except ValueError:
            # Current: Give up work
            return []

        if state["occupation"] == "Unemployed":
            # Current: Give up work
            return []
        if hours > 8:
            # Decompose the work action into multiple small actions
            work_actions = []
            for i in range(hours // 8):
                if i == hours // 8 - 1:
                    work_actions.append(self.work([str(hours % 8)], state))
                else:
                    work_actions.append(self.work(["8"], state))

            return work_actions

        state["energy"] -= hours * 10
        state["money"] += hours * self.get_hourly_salary(state["occupation"])
        state["hungry"] -= hours * 2

        if state["energy"] < 0:
            lack_energy = -state["energy"] // 10 + 1
            actions.insert(0, f"sleep {lack_energy}")
            actions.insert(0, "goto home")
            state["location"] = "home"

        if state["location"] != state["work_place"]:
            # add goto action
            actions.insert(len(actions), f"goto {state['work_place']}")
            state["location"] = state["work_place"]

        actions.append(f"work {hours}")

        return actions

    def use(self, action_args: List[str], state: Dict, market_data: Dict):
        """
        Use items in your inventory
        """
        try:
            # test if the args[1] is a number
            item_num = int(action_args[1])
        except ValueError:
            # Current: Give up use
            self.actions = []
            return self.actions

        if action_args[0] not in list(self.craft_recipes.keys()):
            # Current: Give up use
            self.actions = []
            return self.actions

        if (
            action_args[0] not in state["inventory"]
            or state["inventory"][action_args[0]] < item_num
        ):
            actions = self.generate_craft_sequence_and_check(
                state,
                item_type=action_args[0],
                item_num=item_num,
            )
            self.actions = actions + self.actions

        if action_args[0] == "apple":
            state["hungry"] += 10
        elif action_args[0] == "pear":
            state["hungry"] += 15
        elif action_args[0] == "bread":
            state["hungry"] += 25
        elif action_args[0] == "apple_pie":
            state["hungry"] += 20
        elif action_args[0] == "fruit_salad":
            state["hungry"] += 35
        elif action_args[0] == "chicken_salad":
            state["hungry"] += 35
            state["energy"] += 10
        elif action_args[0] == "beef_rice":
            state["hungry"] += 50
            state["energy"] += 5
        elif action_args[0] == "sushi":
            state["hungry"] += 30
        elif action_args[0] == "book":
            state["education_experience"] += 10
        state["inventory"][action_args[0]] -= item_num
        return self.actions

    def buy(self, action_args: List[str], state: Dict, market_data):
        """
        Purchase items
        """
        try:
            # test if the args[1] is a number
            item_num = int(action_args[1])
        except ValueError:
            # Current: Give up use
            self.actions = []
            return self.actions

        if action_args[0] not in list(self.craft_recipes.keys()):
            # Current: Give up use
            self.actions = []
            return self.actions

        cost = self.compute_amm_cost("buy", action_args, market_data)
        if state["money"] < cost:
            # Current: if have occupation, work to earn money
            # Else, Give up buy
            # self.actions = []
            if state["occupation"] != "Unemployed":
                lack_money = cost - state["money"]
                work_hours = lack_money / self.get_hourly_salary(state["occupation"])
                self.actions = self.work([str(work_hours)], state) + [
                    "buy " + " ".join(action_args)
                ]
            return self.actions

        for m_data in market_data:
            if m_data["itemName"] == action_args[0]:
                if item_num > m_data["quantity"]:
                    # Current: Give up buy
                    self.actions = []
                    return self.actions

        state["money"] -= cost
        if action_args[0] not in state["inventory"]:
            state["inventory"][action_args[0]] = 0
        state["inventory"][action_args[0]] += item_num
        return self.actions

    def sell(self, action_args: List[str], state: Dict, market_data):
        """
        Sell items
        """

        try:
            # test if the args[1] is a number
            item_num = int(action_args[1])
        except ValueError:
            # Current: Give up use
            self.actions = []
            return self.actions

        if action_args[0] not in list(self.craft_recipes.keys()):
            # Current: Give up use
            self.actions = []
            return self.actions
        reward = self.compute_amm_cost("sell", action_args, market_data)
        if state["inventory"].get(action_args[0], 0) < item_num:
            # Current: Generate Craft Sequence
            actions = self.generate_craft_sequence_and_check(
                state,
                item_type=action_args[0],
                item_num=item_num - state["inventory"].get(action_args[0], 0),
            )
            self.actions = actions + self.actions
            return self.actions

        state["money"] += reward
        state["inventory"][action_args[0]] -= item_num
        return self.actions

    def craft(self, action_args: List[str], state: Dict, market_data):
        """
        Craft items
        """
        try:
            # test if the args[1] is a number
            item_num = int(action_args[1])
        except ValueError:
            # Current: Give up use
            self.actions = []
            return self.actions

        if action_args[0] not in list(self.craft_recipes.keys()):
            # Current: Give up use
            self.actions = []
            return self.actions

        actions = self.generate_craft_sequence_and_check(
            state, item_type=action_args[0], item_num=item_num
        )

        self.actions = actions
        return self.actions

    def generate_craft_sequence_and_check(
        self, state: Dict, item_type: str, item_num: int
    ):
        actions = self.generate_craft_sequence(state, item_type, item_num)
        actions = self.check_every_craft_action(actions, state)

        return actions

    def generate_craft_sequence(self, state: Dict, item_type: str, item_num: int):
        """
        Generate the craft sequence to craft the item
        """
        actions = []
        if item_type not in self.craft_recipes:
            return actions

        recipe = self.craft_recipes[item_type]
        for material_and_num in recipe:
            material_and_num = material_and_num.split(" ")
            material = material_and_num[1]
            num = int(material_and_num[0]) * item_num
            if (
                material not in state["inventory"]
                or state["inventory"].get(material, 0) < num
            ):
                extended_actions = self.generate_craft_sequence(
                    state, material, num - state["inventory"].get(material, 0)
                )
                actions = extended_actions + actions

        actions.append(f"craft {item_type} {item_num}")
        # Refine: Add Goto and Recover Energy Actions
        # print("before_check_actions: ", actions)
        # actions = self.check_every_craft_action(actions, state)

        return actions

    def check_every_craft_action(self, actions, state):
        """
        compute the energy cost of every craft action
        check if every craft action is valid and add goto and recover energy actions
        """
        # print("actions: ", actions)
        actions = self.decompose_large_craft_actions(actions)
        # print("decomposed_actions: ", actions)
        insert_index_list = []
        for index, action in enumerate(actions):
            args = action.split(" ")
            item_name = args[1]
            item_num = int(args[2])
            current_energy = state["energy"]
            energy_cost = self.cost_dict[item_name] * item_num
            state["energy"] -= energy_cost
            if energy_cost > current_energy:
                sleep_hour = min(
                    (energy_cost - current_energy) // 10 + random.randint(1, 3),
                    (100 - current_energy) // 10 + 1,
                )
                insert_index_list.append(
                    {"index": index, "action": f"sleep {sleep_hour}"}
                )
                state["energy"] = min(100, state["energy"] + sleep_hour * 10)

            state["inventory"][item_name] = (
                state["inventory"].get(item_name, 0) + item_num
            )
            for material_and_num in self.craft_recipes[item_name]:
                material_and_num = material_and_num.split(" ")
                material = material_and_num[1]
                num = int(material_and_num[0])
                state["inventory"][material] -= num * item_num

        # Reverse the insert_index_list to insert the action in the correct order
        for insert_index in insert_index_list[::-1]:
            actions.insert(insert_index["index"], insert_index["action"])

        insert_index_list = []
        current_location = state["location"]
        for index, action in enumerate(actions):
            # check state if the location is right
            if action.startswith("goto"):
                current_location = action.split(" ")[1]

            if action.startswith("craft"):
                item_type = action.split(" ")[1]
                if current_location != self.location[item_type][0]:
                    insert_index_list.append(
                        {
                            "index": index,
                            "action": f"goto {self.location[item_type][0]}",
                        }
                    )
                    current_location = self.location[item_type][0]

            if action.startswith("sleep"):
                if current_location != "home":
                    insert_index_list.append(
                        {
                            "index": index,
                            "action": "goto home",
                        }
                    )
                    current_location = "home"

        for insert_index in insert_index_list[::-1]:
            actions.insert(insert_index["index"], insert_index["action"])

        if actions[0].startswith("sleep"):
            actions.insert(0, "goto home")
        return actions

    def decompose_large_craft_actions(self, actions):
        """
        if craft too many actions in a single time
        decompose it into multiple small actions
        """
        new_actions = []
        for action in actions:
            args = action.split(" ")
            item_name = args[1]
            item_num = int(args[2])
            random_large_limit = random.randint(5, 10)
            if item_num > random_large_limit:
                new_actions.extend(
                    [f"craft {item_name} {random_large_limit}"]
                    * (item_num // random_large_limit)
                    + [f"craft {item_name} {item_num % random_large_limit}"]
                )
            else:
                new_actions.append(action)

        for action in new_actions:
            item_num = int(action.split(" ")[2])
            if item_num == 0:
                new_actions.remove(action)

        # print("decomposed_new_actions: ", new_actions)
        return new_actions

    def compute_amm_cost(self, ttype, action_args: List[str], market_data: Dict):
        """
        Compute the cost of the items in the AMM
        """
        trade_item = action_args[0]
        trade_amount = int(action_args[1])

        # print("trade_item: ", trade_item)
        # print("trade_amount: ", trade_amount)
        # print("market_data: ", market_data)
        item_market_data = next(
            item for item in market_data if item["itemName"].lower() == trade_item
        )
        if ttype == "buy":
            trade_money = (
                item_market_data["k"] / (item_market_data["quantity"] - trade_amount)
                - item_market_data["price"]
            )
        elif ttype == "sell":
            trade_money = item_market_data["price"] - item_market_data["k"] / (
                item_market_data["quantity"] + trade_amount
            )
        else:
            raise ValueError("Invalid trade type")

        return trade_money

    def craft_or_buy_eating_stuff(self, state, recover_hungry):
        # Given the initial hungry value, craft or buy eating stuff
        # 1. select a random eating stuff
        # 2. craft the eating stuff! (if the character has the materials or it doesn't need materials)
        # 3. add the energy recover action and goto home action if needed
        actions = []
        foods = [
            "apple",
            "pear",
            "bread",
            "apple_pie",
            "fruit_salad",
            "chicken_salad",
            "beef_rice",
            "sushi",
        ]
        hungry_dict = {
            "apple": 10,
            "pear": 15,
            "bread": 25,
            "apple_pie": 20,
            "fruit_salad": 35,
            "chicken_salad": 35,
            "beef_rice": 50,
            "sushi": 30,
        }
        choices = ["craft", "buy"]
        choose_to = random.choice(choices)
        food = random.choice(foods)

        num = recover_hungry // hungry_dict[food] + 1
        if choose_to == "craft":
            actions = self.generate_craft_sequence_and_check(
                state,
                item_type=food,
                item_num=num,
            )
        else:
            money = self.compute_amm_cost("buy", [food, num], self.market_data)
            if state["money"] < money:
                actions = self.generate_craft_sequence_and_check(
                    state,
                    item_type=food,
                    item_num=num,
                )
            else:
                actions = [f"buy {food} {num}"]
                state["money"] -= money

        actions.append(f"use {food} {num}")
        state["hungry"] = min(100, state["hungry"] + num * hungry_dict[food])
        return actions

    def get_hourly_salary(self, occupation):
        """
        Get the hourly salary of the occupation
        """
        salary_dict = {
            "Unemployed": 0,
            "Intern": 30,
            "Trainee": 30,
            "Assistant": 50,
            "Programmer": 40,
            "Researcher": 50,
            "Manager": 80,
            "Director": 100,
            "Chief Officer": 150,
            "President": 200,
            "Chairman": 250,
            "Guard": 15,
            "Cleaner": 15,
            "Gardener": 25,
            "Police": 40,
            "Cook": 25,
            "Librarian": 40,
            "Store Clerk": 25,
        }
        return salary_dict[occupation]


if __name__ == "__main__":
    # from core.agent_srv.node_engines
    import core.agent_srv.utils as utils
    import asyncio

    action_simulator = ActionSimulator()
    action_list = [
        "goto home",
        "sleep 10",
        "goto farm",
        "craft rice 6",
        "craft feed 3",
        "craft beef 1",
    ]
    initial_state = asyncio.run(utils.get_initial_state_from_db(790456, "websocket"))[
        "character_stats"
    ]
    initial_state["occupation"] = "Intern"
    initial_state["hungry"] = 0
    print(initial_state)
    market_data = utils.get_amm_data_from_db()
    print("initial_market_data: ", market_data)
    action_simulator.simulate(action_list, initial_state, market_data)
    pprint(action_simulator.final_action_list)
