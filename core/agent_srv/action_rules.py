rules = {
    "goto": """**goto [placeName:string]**  
   - Moves the character to `placeName`. Valid places include:  
     (school, workshop, home, farm, mall, square, councilhall, hospital, fruit, harvest, mine, orchard, foodfactory, factory, garden, policestation, library, supermarket, canteen).
""",
    "sleep": """**sleep [hours:int]**
   - Recover energy (10 per hour).
   - Must be at home.
   - When you plan to sleep, you'd better sleep enough hours to reach full energy (100).
""",
    "study": """**study [hours:int]**
   - Costs 100 money/hour, consumes 10 energy/hour, grants 10 education XP/hour.
   - Must be in school and have enough money.
""",
    "seedoctor": """**seedoctor [hours:int]**
   - Costs 100 money/hour, grants 10 health/hour.
   - Must be in hospital and have enough money.
""",
    "work": """**work [hours:int]**
   - Earns money (based on hourly salary), consumes 10 energy/hour.
   - Must have an occupation and be at its corresponding workplace.
""",
    "use": """**use [itemType:string] [amount:int]**
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
""",
    "buy": """**buy [itemType:string] [amount:int]**
   - Purchases items from market, costs money according to market price.
   - Must have enough money, and market must have enough stock.
""",
    "sell": """**sell [itemType:string] [amount:int]**
   - Sells items to market, earning money at the market price.
   - Must have those items in the inventory.
""",
}
