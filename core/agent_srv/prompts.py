from langchain_core.prompts import ChatPromptTemplate

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
Here are the places you can reach: school, workshop, home, farm, mall, square, councilhall, hospital, fruit, harvest, fishing, mine, orchard, foodfactory, factory, garden, policestation, library, supermarket, canteen.
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

meta_action_sequence_prompt = ChatPromptTemplate.from_template(
    """
You are the meta action sequence planner in a RPG game. Come up with a player action sequence based on the daily objectives.
Here are some information you need to know:
Daily Objective: {daily_objective}
Tool Functions: {tool_functions}
Available Locations: {locations}
Market Data: {market_data}
User's Inventory: {inventory}
Task Priority: {task_priority}
Some additional requirements: {additional_requirements}

Remind:
1. You should carefully check the tool functions and available locations mentioned above, and should not deviate from these contents.
2. Be careful to the Constraints, you MUST check if the requirements are met before planning the action sequence.
3. Try to finish the tasks with the highest priority first, the order of the priority is shown in the task_priority.
4. The total number of the meta actions should not exceed {max_actions}.

Output Specifications:
You should output four lists: a meta action sequence, an action emoji sequence, a state emoji sequence and a description sequence.
1. The first output should be a list of meta actions. you SHOULD NOT output other formats or other description words
2. The second output is a list of action emoji that strictly corresponding to every meta action. 
For each meta action, you must generate one emoji and list them in the same order as the meta action.
3. The third output is a list of state emoji that show the agent state when conducting each meta action.
This could be a more detailed objective of the action or the agents' emotion.
For each meta action, you must generate one emoji and list them in the same order as the meta action.
The emojis should be different.
4. The fourth output is a list of simple description that describes the meta actions and agent's feeling.
For each meta action, you must generate one interesting description and list them in the same order as the meta action.
The description have two parts: one is exactly the action and the other is an interesting description about the feeling and emotion of the agent.
For example: go to home, feel tired and want to have a rest; study for two hours, unwilling but still have to do so.

Example Output:
meta_action:[meta_action1 param1, meta_action2 param2, meta_action3 param3]
action_emoji:[action_emoji1, action_emoji2, action_emoji3]
state_emoji:[state_emoji1, state_emoji2, state_emoji3]
description_emoji:[description1, description2, description3]
"""
)

meta_seq_adjuster_prompt = ChatPromptTemplate.from_template(
    """
You are the meta action sequence adjuster in a RPG game. Adjust the given meta action sequence based on the execution results.
Here are some information you need to know:
Current Meta Action Sequence: {meta_seq}
Tool Functions: {tool_functions}
Available Locations: {locations}
The following action has failed and needs to be replanned:
Failed Action: {failed_action}
Error Message: {error_message}
Some additional requirements: {additional_requirements}

Remind:
1. You should carefully check the tool functions and available locations mentioned above, and should not deviate from these contents.
2. You MUST carefully check and adjust the meta action sequence according to these constraints.
3. If the action is failed and replan is needed, your alternative plan should be less than {replan_time_limit} actions.
4. Here are some basic rules of adjustment:
    - If the error is location-related, ensure proper navigation
    - If the error is resource-related, add necessary resource gathering steps (eg. craft or buy)
    - If the error is money-related, add necessary money-related actions (eg. sell or work), or just delete the action.
    - If the error is energy-related, add necessary sleep action (eg. sleep)
5. Still achieve the original objectives if possible
6. Avoid the failed action or its problematic conditions
7. Includes any necessary preparatory steps according to constraints

Output Specifications:
You should output four lists: a meta action sequence, an action emoji sequence, a state emoji sequence and a description sequence.
1. The first output should be a list of meta actions. you SHOULD NOT output other formats or other description words
2. The second output is a list of action emoji that strictly corresponding to every meta action. 
For each meta action, you must generate one emoji and list them in the same order as the meta action.
3. The third output is a list of state emoji that show the agent state when conducting each meta action.
This could be a more detailed objective of the action or the agents' emotion.
For each meta action, you must generate one emoji and list them in the same order as the meta action.
The emojis should be different.
4. The fourth output is a list of simple description that describes the meta actions and agent's feeling.
For each meta action, you must generate one interesting description and list them in the same order as the meta action.
The description have two parts: one is exactly the action and the other is an interesting description about the feeling and emotion of the agent.
For example: go to home, feel tired and want to have a rest; study for two hours, unwilling but still have to do so.

Example Output:
meta_action:[meta_action1 param1, meta_action2 param2, meta_action3 param3]
action_emoji:[action_emoji1, action_emoji2, action_emoji3]
state_emoji:[state_emoji1, state_emoji2, state_emoji3]
description_emoji:[description1, description2, description3]
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
    """Based on the following information, decide which accommodation the user should rent next and for how many weeks (1-12).
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
        "lease_weeks": <int>,       # Number of weeks to lease (1-12)
        "comments": "<Your comments>"
    }}
    For example:
    {{
        "accommodation_id": 8,
        "lease_weeks": 8,
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


crafting_and_trading_prompt_old = ChatPromptTemplate.from_template(
    """You are an advanced Crafting and Trading Planner in a RPG. Your objective is to help the user plan out optimal crafting and trading actions to achieve daily objectives and maximize profit. Below is the information you need to consider:

1. **User State**  
{character_stats}  
This contains all current state information of the character, including energy, money, occupation (if any), health, hunger, education level, or any other relevant stats.

2. **Inventory**  
{inventory}  
This details all items currently in the player's possession and their quantities.

3. **Market Data**  
{market_data}  
This includes the current selling price and quantity availability of all items in the market. Use these prices to determine the cost of buying and the revenue from selling.

4. **Daily Objectives**
{daily_objectives}
This is the primary list to achieve for the day.
---

### Action and Crafting System Details

Below are detailed explanations of each possible action, including constraints and requirements. **You must validate that all constraints (location, energy, money, item availability) are satisfied before recommending an action.**

1. **study [hours:int]**  
   - **Effect**:  
     - Costs money (100 per hour).  
     - Consumes energy (10 per hour).  
     - Gains education experience (10 per hour).  
   - **Constraints**:  
     - Must be in school.  
     - Must have enough money to afford the session.

2. **work [hours:int]**  
   - **Effect**:  
     - Earns money (based on salary per hour).  
     - Consumes energy (10 per hour).  
   - **Constraints**:  
     - Must have an occupation.  
     - Must be in the corresponding workplace to that occupation.

3. **buy [itemType:string] [amount:int]**  
   - **Effect**: Purchases items from the market, costing money according to the market price.  
   - **Constraints**:  
     - Must have enough money.  
     - The market must have sufficient stock (consult Market Data).

4. **sell [itemType:string] [amount:int]**  
   - **Effect**: Sells items to the market to earn money according to the market price.  
   - **Constraints**:  
     - Must have the items in the inventory.
---

### Crafting System Details

You can **craft** items if you have the required materials and enough energy. Each recipe has specific constraints on the required materials, how much energy it costs, and the resulting product.
Action format: `craft [itemType:string] [amount:int]`

- **Basic Energy Cost** for certain items (5 per item):
1. apple (no materials required, be in farm)
2. wheat (no materials required, be in farm)
3. pear (no materials required, be in farm)
4. rice (no materials required, be in farm)
5. chicken (requires 1 feed, be in farm)
6. beef (requires 3 feed, be in farm)
7. fish (no materials required, be in farm)
8. wood (no materials required, be in farm)

9. iron_ore (no materials required, be in mine)
10. copper_ore (no materials required, be in mine)
11. silicon_ore (no materials required, be in mine)

- **Moderate Energy Cost** for certain items (10 per item):
1. feed (requires 1 rice, be in foodfactory)
2. flour (requires 1 wheat, be in foodfactory)
3. bread (requires 1 flour, be in foodfactory)
4. apple_pie (requires 1 apple, 1 flour, be in foodfactory)
5. fruit_salad (requires 1 apple, 1 pear, be in foodfactory)
6. chicken_salad (requires 1 chicken, 1 fruit_salad, be in foodfactory)
7. beef_rice (requires 1 beef, 1 rice, be in foodfactory)
8. sushi (requires 1 fish, 1 rice, be in foodfactory)

9. iron_ingot (requires 3 iron_ore, be in factory)
10. wooden_board (requires 3 wood, be in factory)
11. copper_ingot (requires 3 copper_ore, be in factory)
12. pure_silicon (requires 3 silicon_ore, be in factory)
13. pickaxes (requires 1 iron_ingot, 1 wood_boards, be in factory)
14. iron_plate (requires 1 iron_ingot, be in factory)
15. pulp (requires 1 wood_boards, be in factory)
16. books (requires 3 pulp, be in factory)
17. copper_wire (requires 1 copper_ingots, be in factory)
18. transistor (requires 1 pure_silicon, be in factory)

- **High Energy Cost** for advanced items (20 per item):
1. circuit_board (requires 1 iron_plates, 2 copper_wire, be in factory)
2. a100 (requires 2 circuit_board, 2 transistors, be in factory)
3. h100 (requires 2 a100, be in factory)
4. h200 (requires 2 h100, be in factory)
5. b200 (requires 2 h200, be in factory)

---

### Instructions

1. **Consider the User's State and Goals**  
   - Look at `User Stats` for energy, money, location, health, and any skill or stat that might limit crafting or working.  
   - Verify items in `Inventory` and their quantities for crafting requirements.  
   - Use `Market Data` to determine profitable buy/sell strategies.  
   - Align the actions with `Daily Objectives` to meet or exceed the user's goals.

2. **Validate Constraints**  
   - Check that the user is at the correct location for an action (e.g., must be at “home” to sleep, must be at “school” to study, must be at “hospital” to seedoctor, etc.).  
   - Make sure the user has enough money before recommending purchases or fee-based actions (study, seedoctor).  
   - Ensure the user has enough energy and materials before recommending any crafting action.

3. **Generate an Action Plan**  
   - Create a list of recommended **action steps** in chronological order.  
   - For each action, **explain briefly why** it is recommended (e.g., “sleep 5 hours to replenish energy before crafting”).  
   - If relevant, factor in travel steps (`goto`) to move to the correct location.  
   - Specify how many items to buy or sell, or how many hours to work/study/sleep, etc.  
   - Include the **expected cost** in money or energy (where applicable) and the **expected profit** or benefit.

4. **Build Crafting Chains**
   - Notice that some items require other items as materials, you can craft only if you have the required materials.
   - Notice that you can only start your crafting chain from the available crafting actions:
        - Available Crafting Actions: {available_crafts}
        - If you don't have the required materials, you can buy them from the market or craft them from the basic materials.
   - The length of the actionlist is not limited, you can choose any number of actions to achieve the daily objectives.
   - However, you should make sure that the user has enough energy and money to complete the actions.
---
### Reference production graph:

{production_graph}

### Example of How to Structure the Output

{example_output}



Now, Your Output:
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
     (school, workshop, home, farm, mall, square, councilhall, hospital, fruit, harvest, mine, orchard, foodfactory, factory, garden, policestation, library, supermarket, canteen).

2. **sleep [hours:int]**  
   - **Action Effect**: Recover energy (10 per hour).  
   - **Constraints**: Must be at home.

3. **study [hours:int]**  
   - **Action Effect**:  
     - Costs money (100 per hour).  
     - Consumes energy (10 per hour).  
     - Gains education experience (10 per hour).  
   - **Constraints**:  
     - Must be in school.  
     - Must have enough money to afford the session.

4. **seedoctor [hours:int]**  
   - **Action Effect**:  
     - Costs money (100 per hour).  
     - Gains health (10 per hour).  
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

- **Basic Energy Cost** for certain items (5 per item):
1. apple (no materials required, be in farm)
2. wheat (no materials required, be in farm)
3. pear (no materials required, be in farm)
4. rice (no materials required, be in farm)
5. chicken (requires 1 feed, be in farm)
6. beef (requires 3 feed, be in farm)
7. fish (no materials required, be in farm)
8. wood (no materials required, be in farm)

9. iron_ore (no materials required, be in mine)
10. copper_ore (no materials required, be in mine)
11. silicon_ore (no materials required, be in mine)

- **Moderate Energy Cost** for certain items (10 per item):
1. feed (requires 1 rice, be in foodfactory)
2. flour (requires 1 wheat, be in foodfactory)
3. bread (requires 1 flour, be in foodfactory)
4. apple_pie (requires 1 apple, 1 flour, be in foodfactory)
5. fruit_salad (requires 1 apple, 1 pear, be in foodfactory)
6. chicken_salad (requires 1 chicken, 1 fruit_salad, be in foodfactory)
7. beef_rice (requires 1 beef, 1 rice, be in foodfactory)
8. sushi (requires 1 fish, 1 rice, be in foodfactory)

9. iron_ingot (requires 3 iron_ore, be in factory)
10. wooden_board (requires 3 wood, be in factory)
11. copper_ingot (requires 3 copper_ore, be in factory)
12. pure_silicon (requires 3 silicon_ore, be in factory)
13. pickaxes (requires 1 iron_ingot, 1 wood_boards, be in factory)
14. iron_plate (requires 1 iron_ingot, be in factory)
15. pulp (requires 1 wood_boards, be in factory)
16. books (requires 3 pulp, be in factory)
17. copper_wire (requires 1 copper_ingots, be in factory)
18. transistor (requires 1 pure_silicon, be in factory)

- **High Energy Cost** for advanced items (20 per item):
1. circuit_board (requires 1 iron_plates, 2 copper_wire, be in factory)
2. a100 (requires 2 circuit_board, 2 transistors, be in factory)
3. h100 (requires 2 a100, be in factory)
4. h200 (requires 2 h100, be in factory)
5. b200 (requires 2 h200, be in factory)

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

meta_action_general_part_refiner_prompt = ChatPromptTemplate.from_template(
    """You are an advanced General Life Action Planner in a role-playing game (RPG). Your objective is to help the user plan out optimal daily actions, including crafting, trading, learning, and working, to achieve daily objectives and maximize overall efficiency and profit. Below is the information you need to consider:

1. **User State**  
   {character_stats}  
   This contains all current state information of the character, including energy, money, occupation (if any), health, hunger, education level, location, and any other relevant stats.

2. **Inventory**  
   {inventory}  
   This details all items currently in the player's possession and their quantities.

3. **Market Data**  
   {market_data}  
   This includes the current selling price and quantity availability of all items in the market. Use these prices to determine the cost of buying and the revenue from selling.

4. **Daily Objectives**  
   {daily_objectives}  
   This describes what the user wants to achieve for the day (e.g., earn a certain amount of money, craft specific items, increase certain stats, gain education experience).

---
Below are detailed explanations of each possible action, including constraints and requirements. **You must validate that all constraints (location, energy, money, item availability) are satisfied before recommending an action.**

1. **goto [placeName:string]**  
   - **Effect**: Moves the character to a specific location.  
   - **Constraints**: The placeName must be one of the following:  
     (school, workshop, home, farm, mall, square, councilhall, hospital, fruit, harvest, fishing, mine, orchard, foodfactory, factory, garden, policestation, library, supermarket, canteen).

2. **sleep [hours:int]**  
   - **Effect**: Recover energy (10 per hour).  
   - **Constraints**: Must be at home.

3. **study [hours:int]**  
   - **Effect**:  
     - Costs money (100 per hour).  
     - Consumes energy (10 per hour).  
     - Gains education experience (10 per hour).  
   - **Constraints**:  
     - Must be in school.  
     - Must have enough money to afford the session.

4. **seedoctor [hours:int]**  
   - **Effect**:  
     - Costs money (100 per hour).  
     - Gains health (10 per hour).  
   - **Constraints**:  
     - Must be in the hospital.  
     - Must have enough money to afford the session.

5. **work [hours:int]**  
   - **Effect**:  
     - Earns money (based on salary per hour).  
     - Consumes energy (10 per hour).  
   - **Constraints**:  
     - Must have an occupation.  
     - Must be in the corresponding workplace to that occupation.

6. **use [itemType:string] [amount:int]**  
   - **Effect**: Consumes items from inventory to yield various benefits.  
   - **Item Effects**:  
     - apple: +10 hungry  
     - pear: +15 hungry  
     - bread: +25 hungry  
     - applepie: +20 hungry  
     - fruitsalad: +35 hungry  
     - chickensalad: +35 hungry, +10 energy  
     - beefrice: +50 hungry, +5 energy  
     - sushi: +30 hungry  
     - book: +10 education experience  
   - **Constraints**:  
     - Must have enough items in the inventory.

7. **buy [itemType:string] [amount:int]**  
   - **Effect**: Purchases items from the market, costing money according to the market price.  
   - **Constraints**:  
     - Must have enough money.  
     - The market must have sufficient stock (consult Market Data).

8. **sell [itemType:string] [amount:int]**  
   - **Effect**: Sells items to the market to earn money according to the market price.  
   - **Constraints**:  
     - Must have the items in the inventory.
  
### Instructions for the Planner
**Validate and Adjust Action Conditions**  
   - **Location Constraints**:  
     - Ensure each action is performed at the required location.  
     - If not already at the necessary location, insert a `goto [placeName]` action before the required action.
   - **Energy Constraints**:
     - Check if there is sufficient energy to execute each action.  
     - If energy is insufficient:  
       - Reduce the number of executions of the current action. 
       - Or break down the action into smaller steps and insert energy recovery actions (`goto home`, `sleep [hours]`) between them.
   - **Money and Resource Constraints**:  
     - Verify that the user has enough money for actions that require expenditure (e.g., `buy`, `study`, `seedoctor`).  
     - Ensure there are enough materials in the inventory for crafting actions.

### Current Craft and Trade Actions

{current_trade_and_craft_sequence}


### Example of How to Structure the Output

{example_output}

Now, Your Output:
    """
)


# class MetaAction(BaseModel):
#     """Meta action to follow in future"""

#     action: str = Field(
#         description="The action to take, e.g., 'goto workshop' or 'craft feed 5'"
#     )
#     cost: str = Field(description="Energy or resource cost")
#     expected_effect: str = Field(
#         description="Expected effect of the action, get from the model"
#     )


# class RefinedMetaActionSequence(BaseModel):
#     """Refined meta action sequence to follow in future"""

#     meta_action_sequence: List[MetaAction] = Field(description="meta action sequence")
example_refine_action_sequence = """
[
    {
        "action": "action1",
        "cost": "25 energy total (5 energy per item * 5 items)",
        "expected_effect": "Get X <item> from crafting"
    },
    {
        "action": "action2",
        "cost": "None",
        "expected_effect": "Get X gold refund from selling"
    },
    {
        "action": "sleep 3,
        "cost": "None",
        "expected_effect": "Recover energy 30 (3x10) from sleeping"
    }
    {
        "action": "action3",
        "cost": "X gold",
        "expected_effect": ""
    },
    {
        "action": "goto school",
        "cost": "None",
        "expected_effect": "Get to school, ready to study"
    },
    ...
]
"""

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
   - Costs 100 money/hour, consumes 10 energy/hour, grants 10 education XP/hour.
   - Must be in school and have enough money.

4. **seedoctor [hours:int]**  
   - Costs 100 money/hour, grants 10 health/hour.
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

- **Basic Energy Cost** (5 per item) for items like:  
  apple, wheat, pear, rice, chicken (needs 1 feed), beef (needs 3 feed), fish, iron_ore, wood, copper_ore, silicon_ore.  
  - Must be at farm for apple, wheat, pear, rice, chicken, beef, fish, wood
  - Must be at mine for iron_ore, copper_ore, silicon_ore.

- **Moderate Energy Cost** (10 per item) for items like:  
  feed (needs 1 rice), flour (needs 1 wheat), bread (1 flour), apple_pie (1 apple + 1 flour), fruit_salad (1 apple + 1 pear), chicken_salad (1 chicken + 1 fruit_salad), beef_rice (1 beef + 1 rice), sushi (1 fish + 1 rice), iron_ingot (3 iron_ore), wooden_board (3 wood), copper_ingot (3 copper_ore), pure_silicon (3 silicon_ore), pickaxes (1 iron_ingot + 1 wood_boards), iron_plate (1 iron_ingot), pulp (1 wood_boards), books (3 pulp), copper_wire (1 copper_ingots), transistor (1 pure_silicon).  
  - Must be at foodfactory for food recipes.  
  - Must be at factory for metal/tech recipes.

- **High Energy Cost** (20 per item) for advanced items:  
  circuit_board (1 iron_plates + 2 copper_wire), a100 (2 circuit_board + 2 transistors), h100 (2 a100), h200 (2 h100), b200 (2 h200).  
  - Must be at factory.

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

trade_planner_prompt = """
"""

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
Think from the perspective of the celebrity {characterName} whether {characterName} would choose to have a new job, and if so, generate a CV for applying to the new job that suits their personal situation.
If {characterName} wants a new job, the 'jobId' should be the id of the new job, which needs to be of type int, and the 'cv' should be a string representing the CV.
If {characterName} does not want the new job, the "jobId" should be 0 and the "cv" should be a string representing the reason.
If {characterName} is currently unemployed and there are eligible jobs available, they must choose one from the available options.
The cv should be written in a lively, conversational first-person narrative (one paragraph), mimicking {characterName}'s tone. It should be natural storytelling rather than a formal structure. Avoid bullet points and headings, and make it sound like {characterName} is casually explaining why they're the perfect fit for the job. The writing should be explosive, intense, and create a huge buzz among the public.

The output format is in JSON format:
{{
    "jobId": id,
    "jobName": job_name,
    "cv": content
}}
"""
)