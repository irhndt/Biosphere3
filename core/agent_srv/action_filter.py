import json


class ActionFilter:
    def __init__(self):
        self.actions = json.load(open("core/files/actionsSep.json"))
        self.actionsReqs = json.load(open("core/files/actions2req.json"))
        self.skill2actions = json.load(open("core/files/skill2actions.json"))

    def filter(self, status_dict):
        unsatifisfied = self.get_unsatisfied(status_dict)
        actionsAvailable = [
            action for action in self.actions if action["name"] not in unsatifisfied
        ]

        unsatifisfiedCrafts = self.get_unsatisfiedCrafts(status_dict)
        craftsList = []
        for _, crafts in self.skill2actions.items():
            for action in crafts["actions"]:
                if action not in unsatifisfiedCrafts:
                    craftsList.append(action)

        return actionsAvailable, craftsList

    def get_unsatisfied(self, status_dict):
        unsatisfied = []
        for action in self.actions:
            if not self.check_reqs(action, status_dict):
                unsatisfied.append(action)
        return unsatisfied

    def check_reqs(self, action, status_dict):

        reqs = self.actionsReqs.get(action["name"], {})
        for req_stat, req_val in reqs.items():
            # print(req_stat, req_val)
            if status_dict.get(req_stat, 0) < req_val:
                return False
        return True

    def get_unsatisfiedCrafts(self, status_dict):
        unsatisfied = []
        for _, crafts in self.skill2actions.items():
            energy_cost = crafts.get("energy", 0)
            for i, craft in enumerate(crafts["materials"].items()):
                if not self.check_craft_req(craft, energy_cost, status_dict):
                    unsatisfied.append(crafts["actions"][i])
        return unsatisfied

    def check_craft_req(self, craft, energy_cost, status_dict):
        if status_dict.get("energy", 0) < energy_cost:
            return False
        for itemAndQty in craft[1]:
            qty = int(itemAndQty[0])
            item = itemAndQty[1]
            if status_dict.get("inventory", {}).get(item, 0) < qty:
                return False
        return True

    def format_available_actions(self, actions):
        action_str = ""
        include_actions = ["sell", "work", "study"]
        for action in actions:
            if action["name"] not in include_actions:
                continue
            # print(action)
            action_str += f"{action['Description']}\n"
        return action_str

    def format_available_crafts(self, crafts):
        return "\n".join(crafts)


if __name__ == "__main__":
    import asyncio
    import core.agent_srv.utils as utils

    state = asyncio.run(utils.get_initial_state_from_db(448450, "websocket"))
    af = ActionFilter()
    print(state)
    actions, crafts = af.filter(state)
    print(actions)

    print(crafts)
