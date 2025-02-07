import json
from collections import defaultdict


def parse_material(material_str):
    parts = material_str.strip().split(" ", 1)
    if len(parts) == 2:
        qty, name = parts
        return int(qty), name
    else:
        return 1, parts[0]


class TreeBuilder:
    def __init__(self):
        with open("core/files/skill2actions.json", "r") as f:
            json_data = json.load(f)

        self.json_data = json_data
        self.materials_dict = defaultdict(dict)

        for _, details in self.json_data.items():
            for item, materials in details["materials"].items():
                self.materials_dict[item] = materials

    def build_tree(self, item, qty, tree_lines, prefix="", is_last=True):
        connector = "└── " if is_last else "├── "
        tree_lines.append(f"{prefix}{connector}{qty} {item.upper()}")

        if is_last:
            new_prefix = prefix + "    "
        else:
            new_prefix = prefix + "│   "

        if item in self.materials_dict and self.materials_dict[item]:
            materials = self.materials_dict[item]
            total = len(materials)
            for idx, mat in enumerate(materials):
                mat_qty, mat_name = parse_material(mat)
                total_qty = qty * mat_qty
                last = idx == total - 1
                self.build_tree(mat_name, total_qty, tree_lines, new_prefix, last)
        else:
            pass

    def generate_build_tree(self, target_item, quantity=1):

        tree_lines = [target_item.upper()]
        if target_item not in self.materials_dict:
            print(f"Item '{target_item}' not found in materials.")
            return "\n".join(tree_lines)

        materials = self.materials_dict[target_item]
        if not materials:
            return "\n".join(tree_lines)

        total = len(materials)
        for idx, mat in enumerate(materials):
            mat_qty, mat_name = parse_material(mat)
            total_qty = quantity * mat_qty
            last = idx == total - 1
            self.build_tree(mat_name, total_qty, tree_lines, "", last)

        return "\n".join(tree_lines)


if __name__ == "__main__":
    target = "a100"
    quantity = 1
    builder = TreeBuilder()
    tree = builder.generate_build_tree(target, quantity)
    print(tree)
