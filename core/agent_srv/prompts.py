from langchain_core.prompts import ChatPromptTemplate

action_detail_rules = """"""
obj_planner_prompt = ChatPromptTemplate.from_template(
    """
You are the daily objectives planner in a RPG game. Come up with a general daily objectives.
Here are some information you need to know:
1. User Profile: It includes the status info of the user.
{character_stats}

2. Past Daily Objectives (can be empty): 
{past_objectives}

3. Life Style: 
{life_style}

4. Past reflection: 
{past_reflection}

5. Graph of production: 
It is the target graph of production, which shows the relationship between different items and the required items to produce them.

{production_graph}
---

Attention: The `inventory` contains all items currently in the player's possession and their quantities. 
Only when the inventory has the specified number of required items, will the next level of product be considered for production.
You need to determine the highest level you have reached and continue to collect the remaining items needed to reach higher levels.

Here are the actions you can plan: go to different places, sleep, study, see a doctor, work, use/buy/sell different items, craft different items.
Here are the places you can reach: school, workshop, home, farm, mall, square, councilhall, hospital, fruit, harvest, fishing, mine, orchard, foodfactory, factory, garden, policestation, library, supermarket, canteen, ranch, forest.
The following are the items that exist in this world:
    - apple, wheat, pear, rice, chicken, beef, fish
    - iron_ore, timber, copper_ore, silicon_ore
    - feed, flour, bread, apple_pie, fruit_salad, chicken_salad, beef_rice, sushi
    - iron_ingots, wooden_boards, copper_ingots, pure_silicon, pickaxes, iron_plates, pulp, books, copper_wire, transistors
    - circuit_board, a100, h100, h200, b200

Remind:
1. Your planning should take into account the above information.
2. For the production graph, you should fully consider what stage you are currently in and what you need to do next.

Output Specifications:
1. The final output consists of two parts.
2. The first part is a string describing the current progress of manufacturing items and what should be considered for the next step.
3. The second part should be a list of daily objectives (arranged in order of importance, craft and trade are generally considered more important).
4. you SHOULD NOT output other formats or other description words
5. There is no limit to the length of the resulting list.
6. Don't copy the examples I give, judge according to the actual situation.

Example Output:
{{
    "progress": "Based on my current inventory items, if I need to go further to the next level, I still need to collect...",
    "objectives": ["Crafting: Craft some copper_ore", "Trading: Buy some fish from the market to use", "General: Sleep to get energy"]
}}

Based on the information above, please generate the daily objectives for the user:
"""
)

generate_character_arc_prompt = ChatPromptTemplate.from_template(
    """
You are a character arc generator in a RPG game. Your job is to generate a character arc for the user.
Here are some information you need to know:
User State: {character_stats}
Character Info: {character_info}
Daily Objectives: {daily_objectives}
Daily Reflection: {daily_reflection}
Daily Action Results: {action_results}

Remind:
1. You should carefully analyze the user's current state, the user's past actions, and any other relevant factors to decide the character arc.
2. Character Arc should include aspects like:
    - belief
    - mood
    - values
    - habits
    - personality

Output Specifications:
1. The final format should be a dictionary with five keys: "belief", "mood", "values", "habits", "personality"
2. You SHOULD NOT output other formats or other description words

Example Output:
{{
    "belief": "I believe that hard work is the key to success",
    "mood": "I feel happy and satisfied with my progress",
    "values": "I value honesty and integrity",
    "habits": "I have developed a habit of studying every day",
    "personality": "I am a friendly and outgoing person"
}}
"""
)

daily_reflection_prompt = ChatPromptTemplate.from_template(
    """
You are a daily reflection generator in a RPG game. Your job is to generate a diary-like daily reflection for the user.
Here are some information you need to know:
Changes in User Status: {status_changes}
Recent Daily Objectives: {daily_objectives}
Recent Action Results: {action_results}
Failed Actions: {failed_actions}
Some additional Requirements: {reflection_ar}
Conversation Memory: {conversation_memory}

Remind:
1. You should summarize the user's changes in status, daily objective, failed actions and conversation in the reflection.
2. You should mainly focus on how to improve future planning.
3. You should focus on these topics in a descending order: {focus_topic}.
4. Depth of reflection: {depth_of_reflection}.
5. The level of detail: {level_of_detail}.

You can have different tone and style for different users based on their actions or stats.Use first person to describe the reflection.

Output Specifications:
1. The final format should be a string of the reflection
2. you SHOULD NOT output other formats or other description words
3. The reflection should be no more than 100 words
4. The tone and style of the words: {tone_and_style}

Example Output:
Today I failed to study for 2 hours. Perhaps before going to school, I should earn enough money to pay the tuition fee.

Based on the information above, please generate the daily reflection for the user:
"""
)

generate_cv_prompt = ChatPromptTemplate.from_template(
    """
You are a CV generator in a RPG game. You should firstly decide if a job change is necessary.
If yes, generate a professional CV for the user based on the candidates' information.
If no, output an empty CV.

Here are some information you need to know:
Available Jobs: {available_public_jobs}
User State: {health}
Experience: {experience}
Education Level: {education}

Remind:
1. User can apply for a job even when he/she doesn't meet all the requirements.
2. A general rule of changing job is the desire to make more money or do something he/she loves, or just for less working hours.

Output Specifications:
1. The final format should be a dictionary with two keys: "jobId" and "cv"
2. If no job change is necessary, the "jobId" should be 0 and the "cv" should be an empty string.
3. If job change is necessary, the "jobId" should be the id of the new job and the "cv" should be a string of the CV.
4. you SHOULD NOT output other formats or other description words

Example Output:
If no job change is necessary:
{{
    "jobId": 0,
    "cv": ""
}}
If job change is necessary:
{{
    "jobId": 1,
    "cv": "I think my knowledge level is good enough to be a student helper and I love this job"
}}
"""
)

mayor_decision_prompt = ChatPromptTemplate.from_template(
    """
You are the mayor of a small town in a RPG game. You need to make a decision on a new job application.
Here are some information you need to know:
CV of the candidate: {cv}
Details of the job: {public_work_info}
Whether the hard conditions are met and the reasons? {meet_requirements}

Remind:
1. You should firstly check if the hard conditions are met, if there's no quota for the job, the decision MUST BE NO!
2. If the hard conditions are met, you should carefully analyze the CV and the job details to decide if the candidate should be offered the job.
3. If the hard conditions are not met, and the reason is not about quota lackness, you can add some randomness to your decision-making process to make the decision results more flexible and random.

Output Specifications:
1. The final format should be a dictionary with two keys: "decision" and "comments"
2. The "decision" should be "yes" or "no"
3. You should give some comments for your decision, explaining your decision in a reasonable way

Example Output:
If the decision is to offer the job:
{{
    "decision": "yes",
    "comments": "The player's previous experience and education level meet the requirements, so he can be given a chance to do this job."
}}
If the decision is not to offer the job:
{{
    "decision": "no",
    "comments": "This job is not suitable for this player because there is too big a gap in education level."
}}
"""
)

accommodation_decision_prompt = ChatPromptTemplate.from_template(
    """Based on the following information, decide which accommodation the user should rent next and for how many weeks (1-4).
# Basic Information:
    User State:
    {character_stats}
    Financial Status:
    {financial_status}
    Current Accommodation:
    {current_accommodation}
    Available Accommodations:
    {available_accommodations}

    Previous failed attempts:
    {failure_reasons}

# Output Format
    Your output should be a JSON object like:
    {{
        "accommodation_id": <int>,  # ID of the chosen accommodation
        "lease_weeks": <int>,       # Number of weeks to lease (1-4)
        "comments": "<Your comments>"
    }}
    For example:
    {{
        "accommodation_id": 8,
        "lease_weeks": 2,
        "comments": "I can afford a Villa now, which would improve my quality of life and help me to get respect from others."
    {{

# Key Considerations for Your Decision:

    Production Efficiency:
        Production Efficiency = Health * Hunger * Energy * Wisdom.
        Better accommodations improve maxHealth, maxEnergy, and maxHunger, boosting overall efficiency and ComputeCoin generation.

    Cost-effectiveness:
        Investing in better accommodations can prevent costly health setbacks and reduce time spent on recovery.
        Improved recovery rates from premium accommodations allow for sustained productivity.

    Risk Management:
        Poor accommodations increase the risk of health deterioration, leading to frequent doctor visits and downtime.
        Ensure the user has sufficient reserves for living expenses and emergencies.

    Game Progress:
        If financially stable, prioritize accommodations that maximize efficiency and align with the ultimate goal of generating ComputeCoins.
        For tight budgets, recommend the best option within financial constraints.
    
# Decision:
    """
)


crafting_and_trading_prompt = ChatPromptTemplate.from_template(
    """You are an advanced Action List Planner in a RPG. Your objective is to help the user plan out a list of actions which fits the following constraints. Here is the information you need to consider below:

1. **User Stats info**  
{character_stats}

2. **Market Data**  
{market_data}

3. **Daily Objectives** (Descent order of priority)
{daily_objectives}
Notice:
- This is the primary list to achieve for the day.
- However, if it's not possible to achieve all objectives, try to prioritize the most important ones.
- Besides, if the daily objectives actions (as well as location) are not available in the following action (or location) list, you can ignore them.
---

### Action System Details
Below are detailed explanations of each possible action, including constraints and requirements. **You must validate that all constraints (location, energy, money, item availability) are satisfied before add an action to list.**

1. **goto [placeName:string]**  
   - **Action Effect**: Moves the character to a specific location, only change the location. 
   - **Constraints**: The placeName must be one of the following:  
     (school, workshop, home, farm, mall, square, councilhall, hospital, fruit, harvest, mine, orchard, foodfactory, factory, garden, policestation, library, supermarket, canteen, ranch, forest).

2. **sleep [hours:int]**  
   - **Action Effect**: Recover energy (10 per hour).  
   - **Constraints**: Must be at home.

3. **study [hours:int]**  
   - **Action Effect**:  
     - Costs money (50 per hour).  
     - Consumes energy (3 per hour).  
     - Gains education experience (5 per hour).  
   - **Constraints**:  
     - Must be in school.  
     - Must have enough money to afford the session.

4. **seedoctor [hours:int]**  
   - **Action Effect**:  
     - Costs money (50 per hour).  
     - Gains health (20 per hour).  
   - **Constraints**:  
     - Must be in the hospital.  
     - Must have enough money to afford the session.

5. **work [hours:int]**  
   - **Action Effect**:  
     - Earns money (based on salary per hour).  
     - Consumes energy (10 per hour).  
   - **Constraints**:  
     - Must have an occupation.  
     - Must be in the corresponding workplace to that occupation.

6. **use [itemType:string] [amount:int]**  
   - **Action Effect**: Consumes items from inventory to yield various benefits.  
   - **Item Effects**:  
     - apple: +10 hungry
     - pear: +15 hungry  
     - bread: +25 hungry  
     - apple_pie: +20 hungry  
     - fruit_salad: +35 hungry  
     - chicken_salad: +35 hungry, +10 energy
     - beef_rice: +50 hungry, +5 energy
     - sushi: +30 hungry
     - books: +10 education experience
   - **Constraints**:  
     - Must have enough items in the inventory.

7. **buy [itemType:string] [amount:int]**  
   - **Action Effect**: Purchases items from the market, costing money according to the market price.  
   - **Constraints**:  
     - Must have enough money.  
     - The market must have sufficient stock (consult Market Data).

8. **sell [itemType:string] [amount:int]**  
   - **Action Effect**: Sells items to the market to earn money according to the market price.  
   - **Constraints**:  
     - Must have the items in the inventory.
     

---

### Crafting System Details

You can **craft** items if you have the required materials and enough energy. Each recipe has specific constraints on the required materials, how much energy it costs, and the resulting product.
Action format: `craft [itemType:string] [amount:int]` (remember, the amount should not exceed 10).
The following is a table of items that can be crafted, along with their energy cost, place, and recipe:

| Item           | Energy Cost | Place        | Recipe                                  |
|----------------|-------------|--------------|-----------------------------------------|
| Apple          | 3           | orchard      | —                                       |
| Wheat          | 2           | farm         | —                                       |
| Pear           | 3           | orchard      | —                                       |
| Rice           | 3           | farm         | —                                       |
| Chicken        | 5           | ranch        | 1 × Feed                                |
| Beef           | 5           | ranch        | 3 × Feed                                |
| Fish           | 3           | fishing      | —                                       |
| Feed           | 5           | forest       | 1 × Rice                                |
| Flour          | 3           | mine         | 1 × Wheat                               |
| Bread          | 3           | mine         | 1 × Flour                               |
| Apple Pie      | 3           | mine         | 1 × Apple, 1 × Flour                      |
| Fruit Salad    | 5           | foodfactory  | 1 × Apple, 1 × Pear                       |
| Chicken Salad  | 10          | foodfactory  | 1 × Chicken, 1 × Fruit Salad              |
| Beef Rice      | 10          | foodfactory  | 1 × Beef, 1 × Rice                        |
| Sushi          | 7           | foodfactory  | 1 × Fish, 1 × Rice                        |
| Iron Ore       | 1           | foodfactory  | —                                       |
| Wood           | 1           | factory      | —                                       |
| Copper Ore     | 1           | factory      | —                                       |
| Silicon Ore    | 1           | factory      | —                                       |
| Iron Ingot     | 5           | minefactory  | 3 × Iron Ore                            |
| Wooden Board   | 5           | factory      | 3 × Wood                                |
| Copper Ingot   | 5           | minefactory  | 3 × Copper Ore                          |
| Pure Silicon   | 5           | minefactory  | 3 × Silicon Ore                         |
| Iron Plate     | 5           | minefactory  | 1 × Iron Ingot                          |
| Pulp           | 5           | factory      | 1 × Wooden Board                        |
| Books          | 10          | factory      | 3 × Pulp                                |
| Copper Wire    | 5           | minefactory  | 1 × Copper Ingot                        |
| Transistor     | 5           | factory      | 1 × Pure Silicon                        |
| Circuit Board  | 20          | factory      | 1 × Iron Plate, 2 × Copper Wire         |
| A100           | 20          | factory      | 2 × Circuit Board, 2 × Transistor       |
| H100           | 25          | factory      | 2 × A100                                |
| H200           | 50          | factory      | 2 × H100                                |
| B200           | 100         | factory      | —                                       |
---

### Reference production graph:

{production_graph}

You should not sell any items in the production graph, as they are required for crafting higher-level items.

### Instructions

1. **Consider the User's State and Goals**  
   - Look at `User Stats Info` for energy, money, location, health, inventory and any skill or stat that might limit crafting or working.  
   - Use `Market Data` to determine profitable buy/sell strategies.  
   - Align the actions with `Daily Objectives` to meet or exceed the user's goals.
   - If the daily objectives are not achievable, prioritize the most important one.

2. **Validate and Adjust Action Conditions**  
   - **Location Constraints**:  
     - Ensure each action is performed at the required location.  
     - If not already at the necessary location, insert a `goto [placeName]` action before the required action.
   - **Energy Constraints**:
     - Check if there is sufficient energy to execute each action. The range of energy status is 0-100.
   - **Money and Resource Constraints**:  
     - Verify that the user has enough money for actions that require expenditure (e.g., `buy`, `study`, `seedoctor`).  
     - Ensure there are enough materials in the inventory for crafting actions. 

3. **Generate an Action Plan**  
   - Create a list of recommended **action steps** in chronological order.  
   - For each action, **explain briefly why** it is recommended (e.g., “sleep 5 hours to replenish energy before crafting”).
   - If cost energy, you should compute the cost of each action and make sure the user has enough energy to complete the actions.  
   - If relevant, factor in travel steps (`goto`) to move to the correct location.  
   - Specify how many items to buy or sell, or how many hours to work/study/sleep, etc.  
   - Include the **expected cost** in money or energy (where applicable) and the **expected profit** or benefit.

4. **Build Crafting Chains**
   - Notice that some items require other items as materials, you can craft only if you have the required materials.
   - If you don't have the required materials, you can buy them from the market or craft them from the basic materials.
   - The length of the actionlist is not limited, you can choose any number of actions to achieve the daily objectives.
---

### Example of How to Structure the Output

{example_output}

{forbidden_example_output}
---
Now, Your Output:
"""
)

here446 = """### Reference Craft routing:
Daily goal: {daily_objectives}

{craft_routing}"""

example_out = """
{
    "result": [
            {
                "action": "craft feed 5",
                "reason": "Reason: Craft feed from rice to prepare for making chicken/beef.",
                "cost": "25 energy total (5 energy per item * 5 items)"
            },
            {
                "action": "craft chicken 2",
                "reason": "Use feed to craft chicken, sells well on the market.",
                "cost": "10 energy total (5 energy per item * 2 items)"
            },
            {
                "action": "sell chicken 2",
                "reason": "Earn profit from selling chickens, which is part of daily objective to raise money.",
                "expected_revenue": "X gold"
            }
        ]
}"""

forbidden_example_out = """
### Forbidden Example Output 1: The latter effect of the action is not allowed (latter energy/money is negative)
>> suppose the current or initial energy is 20, and the action costs 25 energy, the latter energy is -5, which is not allowed.
{
    "result": [
        {
            "action": "craft feed 5",
            "reason": "Reason: Craft feed from rice to prepare for making chicken/beef.",
            "cost": "25 energy total (5 energy per item * 5)"
            "effects: "Current energy is 20/100, the latter energy is -5/100" # This is not allowed!
        }
    ]
}

### Forbidden Example Output 2: Take `craft action` but the user doesn't have enough materials
>> suppose the user current inventory is {apple: 2, rice: 3}, and the action is `craft chicken 2`, which requires 2 feed, but the user doesn't have enough rice.
{
    "result": [
        {
            "action": "craft feed 5",
            "reason": "Reason: Craft feed from rice to prepare for making chicken/beef.",
            "cost": "25 energy total (5 energy per item * 5); 5 rice total (1 rice per item * 5)"
            "effects: "Initail energy is 100/100, the latter energy is 75/100; Initial rice is 2, the latter rice is -3" # This is not allowed!
        }
    ]
}

### Forbidden Example Output 3: Sell items in the `production graph`.
>> suppose the user wants to create an h100, its inventory is {a100: 2, apple 1}, and the action is `sell a100 2`, which is not allowed.
>> because the a100 is the down-level material of h100, it should not be sold.
{
    "result": [
        {
            "action": "sell a100 2",
            "reason": "Reason: Sell a100 to get gold.",
            "cost": "None"
            "effects: "Initail money is 100, the latter money is 900" # This is not allowed!
        }
    ]
}
"""

generate_emoji_sequence_prompt = ChatPromptTemplate.from_template(
    """
You are a monologue generation assistant for inner thoughts. You need to refer to the user's personality traits and event descriptions to generate appropriate monologues for each time point, and 2 corresponding emojis.

The user's personality is `{personality}`. You will receive an input of an array of event lists, and you need to generate a 20-word English inner monologue for each event, which should be as interesting as possible.

The response should be in JSON format. For example, if the input is ["Working", "Go fishing"], you should return {sequence_format}.

Your input action list is: {action_list}

Your output:
"""
)


replanner_prompt = ChatPromptTemplate.from_template(
    """You are an Action List Re-Planner for an RPG. You will receive the following data:

1. **Character Stats**:
{character_stats}

2. **Market Data**:
{market_data}

3. **Current Action List**: 
{current_action_list}

4. **Fail Action Info**:
{fail_action_info}

---

### Your Task

- **Analyze** all the provided information and the reason for the most recent failed action.
- **Identify** any problems (constraint violations) in the **entire** Current Action List.
- **Produce** a **new Action List** that is valid and executable.  
  - Fix or replace any erroneous/infeasible actions.
  - Validate all constraints (energy, money, location, inventory, etc.) before confirming any action.
- **No** action should violate the rules.  

### **Important Constraints to Check**

1. **No Negative Energy/Money**  
   - Actions cannot make energy or money go below zero.

2. **Inventory Requirements**  
   - Must have enough items for use, sell, or craft actions.

3. **Market Requirements**  
   - Must have enough money to buy items.
   - Must ensure the market has enough stock for the intended purchase.

4. **Location Requirements**  
   - Some actions require being at a specific location (e.g., `sleep` at home, `study` at school).
   - Must use `goto [location]` when relocating before an action if needed.

5. **Occupation Requirements**  
   - `work` only if the user has an occupation and is at the occupation's location.

6. **Crafting Limits**  
   - Cannot craft more than **10** of any item per craft action.
   - Must have all required materials in the inventory.
   - Must be in the correct location to craft.
   - Must have enough energy (item's energy cost * quantity).

---

### **Action System & Crafting System Details**  
(Use these rules to validate actions.)

1. **goto [placeName:string]**  
   - Moves the character to `placeName`. Valid places include:  
     (school, workshop, home, farm, mall, square, councilhall, hospital, fruit, harvest, mine, orchard, foodfactory, factory, garden, policestation, library, supermarket, canteen).

2. **sleep [hours:int]**  
   - Recover energy (10 per hour).
   - Must be at home.
   - When you plan to sleep, you'd better sleep enough hours to reach full energy (100).

3. **study [hours:int]**  
   - Costs 50 money/hour, consumes 3 energy/hour, grants 5 education XP/hour.
   - Must be in school and have enough money.

4. **seedoctor [hours:int]**  
   - Costs 50 money/hour, grants 20 health/hour.
   - Must be in hospital and have enough money.

5. **work [hours:int]**  
   - Earns money (based on hourly salary), consumes 10 energy/hour.
   - Must have an occupation and be at its corresponding workplace.

6. **use [itemType:string] [amount:int]**  
   - Consumes items from inventory for benefits:  
     - apple: +10 hungry  
     - pear: +15 hungry  
     - bread: +25 hungry  
     - apple_pie: +20 hungry  
     - fruit_salad: +35 hungry  
     - chicken_salad: +35 hungry, +10 energy  
     - beef_rice: +50 hungry, +5 energy  
     - sushi: +30 hungry  
     - books: +10 education experience  

7. **buy [itemType:string] [amount:int]**  
   - Purchases items from market, costs money according to market price.
   - Must have enough money, and market must have enough stock.

8. **sell [itemType:string] [amount:int]**  
   - Sells items to market, earning money at the market price.
   - Must have those items in the inventory.

#### **Crafting System**

**Action**: `craft [itemType:string] [amount:int]` (max 10 items per action)
The following is a table of items that can be crafted, along with their energy cost, place, and recipe:
| Item           | Energy Cost | Place        | Recipe                                  |
|----------------|-------------|--------------|-----------------------------------------|
| Apple          | 3           | orchard      | —                                       |
| Wheat          | 2           | farm         | —                                       |
| Pear           | 3           | orchard      | —                                       |
| Rice           | 3           | farm         | —                                       |
| Chicken        | 5           | ranch        | 1 × Feed                                |
| Beef           | 5           | ranch        | 3 × Feed                                |
| Fish           | 3           | fishing      | —                                       |
| Feed           | 5           | forest       | 1 × Rice                                |
| Flour          | 3           | mine         | 1 × Wheat                               |
| Bread          | 3           | mine         | 1 × Flour                               |
| Apple Pie      | 3           | mine         | 1 × Apple, 1 × Flour                      |
| Fruit Salad    | 5           | foodfactory  | 1 × Apple, 1 × Pear                       |
| Chicken Salad  | 10          | foodfactory  | 1 × Chicken, 1 × Fruit Salad              |
| Beef Rice      | 10          | foodfactory  | 1 × Beef, 1 × Rice                        |
| Sushi          | 7           | foodfactory  | 1 × Fish, 1 × Rice                        |
| Iron Ore       | 1           | foodfactory  | —                                       |
| Wood           | 1           | factory      | —                                       |
| Copper Ore     | 1           | factory      | —                                       |
| Silicon Ore    | 1           | factory      | —                                       |
| Iron Ingot     | 5           | minefactory  | 3 × Iron Ore                            |
| Wooden Board   | 5           | factory      | 3 × Wood                                |
| Copper Ingot   | 5           | minefactory  | 3 × Copper Ore                          |
| Pure Silicon   | 5           | minefactory  | 3 × Silicon Ore                         |
| Iron Plate     | 5           | minefactory  | 1 × Iron Ingot                          |
| Pulp           | 5           | factory      | 1 × Wooden Board                        |
| Books          | 10          | factory      | 3 × Pulp                                |
| Copper Wire    | 5           | minefactory  | 1 × Copper Ingot                        |
| Transistor     | 5           | factory      | 1 × Pure Silicon                        |
| Circuit Board  | 20          | factory      | 1 × Iron Plate, 2 × Copper Wire         |
| A100           | 20          | factory      | 2 × Circuit Board, 2 × Transistor       |
| H100           | 25          | factory      | 2 × A100                                |
| H200           | 50          | factory      | 2 × H100                                |
| B200           | 100         | factory      | —                                       |

---

### **Forbidden Error Examples**

1. **Negative Energy/Money After Action**  
   - E.g., trying to craft something costing 25 energy when current energy is only 20 → leaves -5 energy (not allowed).

2. **Insufficient Inventory**  
   - E.g., attempting `craft chicken` without enough `feed`, or `use [item]` without having that item in inventory.

3. **Craft More Than 10 Items**  
   - E.g., `craft iron_ore 20` in a single action list is forbidden.
   - You can only craft no more than 10 items per item in a single action list.

---

### **Final Output Requirements**

Output your **corrected** Action List in a structured JSON (or similar) format where **each step** contains:
- **action** (e.g., `"craft feed 5"`)
- **reason** (brief explanation)
- **status_before** (key stats, before the action)
- **status_after** (updated stats, after the action)
- **inventory_before** (current inventory)
- **inventory_after** (updated inventory)

No step should produce invalid states (like negative energy/money, items below zero, or crafting > 10 items). If relocation is needed, include a `goto [location]` step first.  

When you are done, present the final plan in the required format.

**Now:** Carefully validate and re-plan so the user can execute every step without error. Please provide the finalized Action List now.
"""
)


meta_seq_forbidden_example_out = """### Forbidden Example Output 1: The latter effect of the action is not allowed (latter energy/money is negative)
>> suppose the current or initial energy is 20, and the action costs 25 energy, the latter energy is -5, which is not allowed.
{
    "result": [
        {
            "action": "craft feed 5",
            "reason": "Reason: Craft feed from rice to prepare for making chicken/beef.",
            "cost": "25 energy total (5 energy per item * 5)"
            "status_before": "Current energy is 20/100",
            "status_after": "Later energy is -5/100" # This is not allowed!
            "inventory_before": "Current inventory is {apple: 2, rice: 7}",
            "inventory_after": "Later inventory is {apple: 2, rice: 2}"
        }
    ]
}

>> suppose the current or initial money is 20, and the action costs 100 money, the latter money is -80, which is not allowed.
{
    "result": [
        {
            "action": "study 1",
            "reason": "Reason: Study to gain experience.",
            "cost": "100 money total (100 money per item * 1), 10 energy total (10 energy per item * 1)"
            "status_before": "Current money is 20; Current energy is 20/100",
            "status_after": "Later money is -80; Later energy is 10/100" # This is not allowed!
        }
    ]
}

### Forbidden Example Output 2: Take `craft action` but the user doesn't have enough materials
>> suppose the user current inventory is {apple: 2, rice: 3}, and the action is `craft chicken 2`, which requires 2 feed, but the user doesn't have enough rice.
{
    "result": [
        {
            "action": "craft feed 5",
            "reason": "Reason: Craft feed from rice to prepare for making chicken/beef.",
            "cost": "25 energy total (5 energy per item * 5); 5 rice total (1 rice per item * 5)"
            "status_before": "Current energy is 20/100",   
            "status_after": "Later energy is 0/100",
            "inventory_before": "Current inventory is {apple: 2, rice: 3}",
            "inventory_after": "Later inventory is {apple: 2, rice: -2}" # This is not allowed!
        }
    ]
}

### Forbidden Example Output 3: `Craft Action` CAN NOT craft more than ***10 items*** at an action list.
>> suppose the user have enough energy to craft 20 iron_ore. Even in this case, the user can only craft 10 iron_ore at an action list.
{
    "result": [
        {
            "action": "craft iron_ore 20",  # This is not allowed!!
            ...
        }
    ]
}

Remember, you should not output any forbidden situation in the result!
"""

meta_seq_example_out = """
{
    "result": [
            {
                "action": "action1",,
                "cost": "25 energy total (5 energy per item * 5)",
                "status_before": "Current energy is 65/100",
                "status_after": "Later energy is 40/100",
                "reason": "Reason for action1"
            },
            {
                "action": "action2",
                "cost": "10 energy total (5 energy per item * 2)",
                "status_before": "Current energy is 40/100",
                "status_after": "Later energy is 30/100",
                "inventory_before": "Current inventory is {apple: 2, rice: 3}",
                "inventory_after": "Later inventory is {apple: 2, rice: 1}",
                "reason": "Reason for action2"
            },
            {
                "action": "goto home",
                "cost": "None",
                "reason": "Go home to rest and recover energy"
            },
            {
                "action": "sleep 6",
                "cost": "None",
                "status_before": "Current energy is 30/100",
                "status_after": "Later energy is 90/100",
                "reason": "The energy is too low, need to sleep to recover energy"
            },
            {
                "action": "action3",
                "expected_revenue": "23.7 gold",
                "status_before": "Current gold is 100",
                "status_after": "Later gold is 123.7",
                "reason": "Reason for action3"
            },
            ...(more actions)...
        ]
}"""

trade_planner_prompt = ChatPromptTemplate.from_template(
    """
You are the **Daily Trade Objectives Planner** in an RPG game. Your sole focus is on generating a daily plan **centered on trading**. If you determine that trading is not beneficial at this time, you may propose **no objectives**.

Below is the information you have at your disposal:

1. **User Profile**  
   {character_stats}  
   *(Contains the user’s status, including inventory, finances, etc.)*

2. **Past Daily Objectives** (can be empty)  
   {past_objectives}

3. **Past Reflection**  
   {past_reflection}
   *(Any notes or lessons learned from previous actions.)*

4. **Graph of Production**  
   {production_graph}  
   *(A chart outlining item relationships—useful for understanding which items might be in demand or surplus, but do not propose production tasks.)*

---

### Key Points to Consider
1. **Trading Focus Only**: Propose trading actions (buying, selling, bartering) based on the user’s inventory, resources, and needs. **Do not include any production targets.**  
2. **Inventory & Requirements**: Determine which items the user has in surplus (potentially sell) or needs more of (potentially buy).  
3. **When to Trade**: Skip trading if it’s not advantageous, or if the user’s resources (finances or key materials) are insufficient.  
4. **Valid Locations for Trading**:  
   - *school, workshop, home, farm, mall, square, councilhall, hospital, fruit, harvest, fishing, mine, orchard, foodfactory, factory, garden, policestation, library, supermarket, canteen.*  
5. **Available Items**:  
   - Basic crops & livestock: *apple, wheat, pear, rice, chicken, beef, fish.*  
   - Raw materials: *iron_ore, timber, copper_ore, silicon_ore.*  
   - Intermediate goods: *feed, flour, bread, apple_pie, fruit_salad, chicken_salad, beef_rice, sushi.*  
   - Processed materials: *iron_ingots, wooden_boards, copper_ingots, pure_silicon, pickaxes, iron_plates, pulp, books, copper_wire, transistors.*  
   - Advanced items: *circuit_board, a100, h100, h200, b200.*  

---

### Instructions for Output
1. The **final output** must contain two parts in **JSON-like** format.  
2. **First Part: `decision`**  
   - State whether you want to trade (“Yes”) or not (“No”), with a brief explanation.  
   - Examples:  
     - `"decision": "Yes. I want to trade to acquire more wheat."`  
     - `"decision": "No. Because I don't have enough money to buy anything useful today."`  
3. **Second Part: `objectives`**  
   - Provide a list of `"objectives"` focused **only on trading** tasks (buying, selling, or bartering).  
   - You may leave the `"objectives"` list **empty** if no trading actions are recommended.  
4. **Constraints**:  
   - Do **not** include production steps of any kind.  
   - Avoid buying overly expensive items that exceed the user’s budget.  
   - Avoid selling items that are crucial for immediate or near-future needs.  
   - There is **no strict limit** to the number of objectives; list as many (or as few) as needed.  

---

### Example Output 1
```
{{
  "decision": "Yes. I want to trade to restock essential grains.",
  "objectives": [
    "Buy 10 units of wheat at the mall",
    "Sell 5 extra apples at the square"
  ]
}}
```

### Example Output 2
```
{{
  "decision": "No. Because I don't have enough funds to buy anything useful today.",
  "objectives": []
}}
```

---

**Your task**: Use the information from the user’s profile, past objectives, past reflections, and production graph to generate the **best daily plan with a focus on trading only**. If no profitable or useful trades are possible, opt out and provide an empty objectives list.
```

Please generate the **daily trade objectives** based on the information above.
"""
)

prompt_for_cv_new = ChatPromptTemplate.from_template(
    """{characterName} focuses on {industry}. The ultimate goal: {industry_goal_for_cv}.

# Personal Information
Educational Background: {education}
Current Money: {money}
Past Work Experience: {past_work_experience}
Biography: {biography}

{current_job_str}
{eligible_jobs_str}

# require
{characterName}'s current position has expired. Please think from {characterName}'s perspective to determine whether they would want a job. If they do, generate an interesting and personality-driven CV for applying to a suitable position. The CV should be written in the first person, reflecting {characterName}'s unique tone and style. If {characterName} does not want a job, the "jobId" should be 0, and the "cv" should be a reason written in the first person that reflects their personality and reasoning for not wanting a job.

The output format is in JSON format:
{{
    "jobId": id,
    "cv": content (one paragraph)
}}
"""
)

merger_prompt = ChatPromptTemplate.from_template(
    """
You are a daily objective merger in an RPG game. Your goal is to merge the daily objectives of the user to create a concise, organized, and achievable list. Here is the information you need to know:

1. **Past Daily Objectives** (If any):
{past_daily_objectives}

2. **Current Daily Objectives**:
{current_daily_objectives}

3. **Current Trading Objectives**:
{current_trading_objectives}

{additional_info}
---
**Your Task**:
1. Review all the objectives above.
2. Identify any overlaps, redundancies, or dependencies.
3. According to additional information (if provided), add study or work objectives to the list.
4. Generate a concise merged list that preserves essential crafting and trading goals while removing unnecessary duplications.
5. Output your final plan in **JSON format** containing two keys:
   - **"progress"**: a brief summary of the combined objectives and their relevance to the user’s current situation.
   - **"objectives"**: an ordered list of tasks (from highest to lowest priority) that the user should follow.
6. Do not include any other commentary, formatting, or text aside from what is explicitly requested above.

Please merge the daily objectives to create a coherent and efficient plan for the user.
    """
)

correct_format_prompt = ChatPromptTemplate.from_template(
    """You are an AI assistant whose primary responsibility is to provide answers in a strictly defined format. Follow the instructions below carefully:

1. **Required Output Format**:  
   Your final response must adhere exactly to the specified format. For example, if the expected format is JSON, your output must be valid JSON with no additional text, commentary, or formatting deviations.

2. **Final Output Only**:  
   Return only the correctly formatted output. Do not include any extra explanation or notes.

Remember: If your initial output does not match the required format exactly, refine it until it does.

The raw input:
{raw_input}

Your Correctly Formatted Output:"""
)

action_refiner_prompt = ChatPromptTemplate.from_template(
    """
You are an AI assistant responsible for guiding a player in an RPG game. Your task is to refine the available action list based on the following inputs:

1. **Current State:**  
   The player's status is provided as a JSON object with the following properties:
   - **money:** The amount of money the player has.
   - **energy:** The player's current energy level.
   - **inventory:** A dictionary representing items and their quantities.
   - **location:** The current location of the player.

2. **Action List:**  
   A list of possible actions the player can take.

3. **Current Action:**  
   The action that is currently in progress or being considered.

4. **Current Action Rule:**  
   A guideline or rule that the current action should follow.

**Your Objective:**  
Analyze the provided inputs and choose (or refine) an action from the action list that best aligns with the player's current state and the action rule. If needed, update the player's state (for example, adjusting energy or money) based on the selected action. Finally, provide a reason for your choice.

**Output Requirements:**  
Your response must be a valid JSON object that follows the schema below exactly:

```json
{
  "action": "string", 
  "current_state": {
    "money": 0, 
    "energy": 0, 
    "inventory": {
      "item_name": 0
    },
    "location": "string"
  },
  "reason": "string"
}
```

- **action:** A string representing the refined action that the player should perform next.
- **current_state:** An object representing the (possibly updated) current state of the player.
- **reason:** A brief explanation of why you chose this action.

**Example Scenario:**  
Suppose the current state shows that the player has low energy, the current action is `"explore forest"`, and the current action rule advises `"avoid strenuous activities when energy is low"`. In this case, you might choose a less energy-intensive action like `"rest"` or `"visit a healer"`, update the energy level if necessary, and provide a clear reason for this choice.

Now, using the information provided, please output your refined action and updated state in the required JSON format.
    """
)

mayor_decision_prompt = ChatPromptTemplate.from_template(
    """As the mayor of the town, your task is to select up to {number_of_positions} suitable candidates for the "{job_name}" position from the list of applicants.

{public_work_str}
{candidates_str}

# Requirements
The "decision" field should contain a list of the selected candidates' characterIds.
The "comments" field should provide a justification for choosing these candidates.
The number of selected candidates must not exceed {number_of_positions}.

The output format is in JSON format:
{{
    "decision": [1, 2, 3],   
    "comments": "(The comments that justify the selection.)"
}}

Now, please select the most suitable candidates for the "{job_name}" position and provide your reasoning for the decision.
Your output:
"""
)
