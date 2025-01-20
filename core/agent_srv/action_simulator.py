import json
from typing import List, Dict
from pprint import pprint
import copy
import random
import ast


class ActionSimulator:
    def __init__(self):
        # action_rules = self.load_action_rules()
        self.action_runner = ActionRunner()
        self.final_action_list = []

    def simulate_single_action(self, action: str, state, market_data):
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
            market_data,
        )

    def simulate(self, action_list, initial_state, market_data):
        """
        Simulate the action list on the initial state, return the final state and reward
        """
        state = copy.deepcopy(initial_state)
        state["location"] = ""
        for action in action_list:
            actions = self.simulate_single_action(action, state, market_data)
            # print("action: ", action)
            # print("actions: ", actions)
            # if not actions:
            #     break
            self.final_action_list.extend(actions)
        self.final_check_location()

        return self.final_action_list

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

    def run_action(
        self, action_name: str, action_args: List[str], state: Dict, market_data: Dict
    ):
        """
        Run the action on the state, return the next state and reward
        """
        self.actions = [f"{action_name} {' '.join(action_args)}"]
        if action_name == "goto":
            return self.goto(action_args, state)

        if action_name == "sleep":
            return self.sleep(action_args, state)

        if action_name == "study":
            return self.study(action_args, state)

        if action_name == "seedoctor":
            return self.seedoctor(action_args, state)

        if action_name == "work":
            return self.work(action_args, state)

        if action_name == "use":
            return self.use(action_args, state, market_data)

        if action_name == "buy":
            return self.buy(action_args, state, market_data)

        if action_name == "sell":
            return self.sell(action_args, state, market_data)

        if action_name == "craft":
            # print("before inventory:", state["inventory"])
            # print("before energy:", state["energy"])
            actions = self.craft(action_args, state, market_data)
            # print("after inventory:", state["inventory"])
            # print("after energy:", state["energy"])
            return actions

        return []

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

        state["money"] -= hours * 100
        state["energy"] -= hours * 10
        state["education_experience"] += hours * 10
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

        state["money"] -= hours * 100
        state["health"] += hours * 10
        return self.actions

    def work(self, action_args: List[str], state: Dict):
        """
        Work to earn money
        """
        try:
            # test if the args[0] is a number
            hours = int(action_args[0])
        except ValueError:
            # Current: Give up work
            self.actions = []
            return self.actions

        if state["occupation"] == "Unemployed":
            # Current: Give up work
            self.actions = []
            return self.actions

        if state["location"] != state["work_place"]:
            # add goto action
            self.actions.insert(-1, f"goto {state['work_place']}")
            state["location"] = state["work_place"]

        state["money"] += hours
        state["energy"] -= hours * 10
        return self.actions

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
            # Current: Give up buy
            self.actions = []
            return self.actions

        if state["market_data"][action_args[0]] < item_num:
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
                state, item_type=action_args[0], item_num=item_num
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
        # print("before_check_actions: ", actions)
        actions = self.check_every_craft_action(actions, state)
        # print("after_check_actions: ", actions)
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
            if insert_index["action"].startswith("sleep"):
                actions.insert(insert_index["index"], "goto home")

        insert_index_list = []
        current_location = state["location"]
        for action in actions:
            # check state if the location is right
            if action.startswith("goto"):
                current_location = action.split(" ")[1]

            if action.startswith("craft"):
                item_type = action.split(" ")[1]
                if current_location != self.location[item_type][0]:
                    insert_index_list.append(
                        {
                            "index": actions.index(action),
                            "action": f"goto {self.location[item_type][0]}",
                        }
                    )
                    current_location = self.location[item_type]

        for insert_index in insert_index_list[::-1]:
            actions.insert(insert_index["index"], insert_index["action"])

        # TODO: add hungery and health check mechanism

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
        item_market_data = next(
            item for item in market_data if item["itemName"] == trade_item
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


if __name__ == "__main__":
    action_simulator = ActionSimulator()
    action_list = [
        "goto forest",
        "craft wood 10",
        "goto workshop",
        "craft wooden_board 3",
        "craft pulp 1",
        "craft books 1",
        "goto home",
        "sleep 10",
    ]
    state_str = "{'userid': 432543, 'character_stats': {'health': 100, 'energy': 100, 'hungry': 100, 'education': 'PrimarySchool', 'education_experience': 10, 'money': 100.0, 'occupation': 'Unemployed', 'work_place': 'N/A', 'efficiency': 1.0, 'inventory': {}, 'personality': 'Analytical, creative, and a problem-solver. Passionate about advancing blockchain technology and cross-chain interactions.', 'long_term_goal': 'Develop an interconnected decentralized ecosystem that allows different blockchain systems to work seamlessly together.', 'short_term_goal': 'Research and produce new forms of advanced materials like copper ingots and semiconductors to support blockchain infrastructure.', 'language_style': 'Precise, logical, and technical. Often discusses concepts in a straightforward, matter-of-fact tone.', 'biography': 'Gavin Wood is a leading figure in the blockchain space, co-founding Ethereum and developing Polkadot to address scalability and interoperability challenges.', 'model_type': 'deepseek-chat'}, 'public_data': {'market_data': {'apple': 5.0, 'wheat': 1.5, 'pear': 7.0, 'rice': 2.64236, 'chicken': 10.0, 'beef': 50.0, 'fish': 7.28863, 'feed': 5.04987, 'flour': 8.13802, 'bread': 15.94218, 'apple_pie': 20.0, 'fruit_salad': 12.0, 'chicken_salad': 40.0, 'beef_rice': 60.0, 'sushi': 10.0, 'iron_ore': 2.0, 'wood': 2.23082, 'copper_ore': 2.0, 'silica_ore': 2.0, 'iron_ingot': 10.0, 'wooden_board': 7.5, 'copper_ingot': 10.0, 'pure_silicon': 10.0, 'tools': 30.0, 'iron_plate': 25.0, 'pulp': 20.0, 'books': 120.0, 'copper_wire': 25.0, 'transistor': 25.0, 'circuit_board': 150.0, 'A100': 750.0, 'H100': 3000.0, 'H200': 15000.0, 'B200': 80000.0}}, 'decision': {'need_replan': False, 'action_description': [], 'action_result': [], 'new_plan': [], 'daily_objective': [], 'meta_seq': [], 'reflection': []}}"
    initial_state = ast.literal_eval(state_str)["character_stats"]
    market_data_str = """[
    {
      "id": 1,
      "itemName": "apple",
      "quantity": 100,
      "price": 500,
      "k": 50000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 2,
      "itemName": "wheat",
      "quantity": 100,
      "price": 150,
      "k": 15000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 3,
      "itemName": "pear",
      "quantity": 100,
      "price": 700,
      "k": 70000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 4,
      "itemName": "rice",
      "quantity": 87,
      "price": 229.88506,
      "k": 20000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-18 15:34:13"
    },
    {
      "id": 5,
      "itemName": "chicken",
      "quantity": 100,
      "price": 1000,
      "k": 100000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 6,
      "itemName": "beef",
      "quantity": 100,
      "price": 5000,
      "k": 500000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 7,
      "itemName": "fish",
      "quantity": 98,
      "price": 714.28571,
      "k": 70000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-17 22:18:06"
    },
    {
      "id": 8,
      "itemName": "feed",
      "quantity": 89,
      "price": 449.4382,
      "k": 40000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-18 04:10:46"
    },
    {
      "id": 9,
      "itemName": "flour",
      "quantity": 96,
      "price": 781.25,
      "k": 75000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-18 05:27:05"
    },
    {
      "id": 10,
      "itemName": "bread",
      "quantity": 97,
      "price": 1546.39175,
      "k": 150000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-16 23:08:29"
    },
    {
      "id": 11,
      "itemName": "apple_pie",
      "quantity": 100,
      "price": 2000,
      "k": 200000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 12,
      "itemName": "fruit_salad",
      "quantity": 100,
      "price": 1200,
      "k": 120000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 13,
      "itemName": "chicken_salad",
      "quantity": 100,
      "price": 4000,
      "k": 400000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 14,
      "itemName": "beef_rice",
      "quantity": 100,
      "price": 6000,
      "k": 600000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 15,
      "itemName": "sushi",
      "quantity": 100,
      "price": 1000,
      "k": 100000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 16,
      "itemName": "iron_ore",
      "quantity": 100,
      "price": 200,
      "k": 20000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 17,
      "itemName": "wood",
      "quantity": 82,
      "price": 182.92683,
      "k": 15000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-18 03:58:38"
    },
    {
      "id": 18,
      "itemName": "copper_ore",
      "quantity": 100,
      "price": 200,
      "k": 20000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 19,
      "itemName": "silica_ore",
      "quantity": 100,
      "price": 200,
      "k": 20000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 20,
      "itemName": "iron_ingot",
      "quantity": 100,
      "price": 1000,
      "k": 100000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 21,
      "itemName": "wooden_board",
      "quantity": 100,
      "price": 750,
      "k": 75000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 22,
      "itemName": "copper_ingot",
      "quantity": 100,
      "price": 1000,
      "k": 100000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 23,
      "itemName": "pure_silicon",
      "quantity": 100,
      "price": 1000,
      "k": 100000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 24,
      "itemName": "tools",
      "quantity": 100,
      "price": 3000,
      "k": 300000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 25,
      "itemName": "iron_plate",
      "quantity": 100,
      "price": 2500,
      "k": 250000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 26,
      "itemName": "pulp",
      "quantity": 100,
      "price": 2000,
      "k": 200000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 27,
      "itemName": "books",
      "quantity": 100,
      "price": 12000,
      "k": 1200000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 28,
      "itemName": "copper_wire",
      "quantity": 100,
      "price": 2500,
      "k": 250000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 29,
      "itemName": "transistor",
      "quantity": 100,
      "price": 2500,
      "k": 250000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 30,
      "itemName": "circuit_board",
      "quantity": 100,
      "price": 15000,
      "k": 1500000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 31,
      "itemName": "A100",
      "quantity": 100,
      "price": 75000,
      "k": 7500000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 32,
      "itemName": "H100",
      "quantity": 100,
      "price": 300000,
      "k": 30000000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 33,
      "itemName": "H200",
      "quantity": 100,
      "price": 1500000,
      "k": 150000000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    },
    {
      "id": 34,
      "itemName": "B200",
      "quantity": 100,
      "price": 8000000,
      "k": 800000000,
      "createTime": "2025-01-15 20:02:42",
      "updateTime": "2025-01-15 20:02:42"
    }
]"""
    market_data = json.loads(market_data_str)
    action_simulator.simulate(action_list, initial_state, market_data)
    pprint(action_simulator.final_action_list)
