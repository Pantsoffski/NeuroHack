from fastapi import FastAPI
from pydantic import BaseModel
import os
import random
from groq import Groq

app = FastAPI()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Dictionary defining our new enemy roster
MONSTER_TYPES = {'Z': 'Zombie', 'G': 'Goblin', 'V': 'Vampire'}

class MoveRequest(BaseModel):
    level: list[list[str]]
    py: int
    px: int
    my: int
    mx: int
    m_char: str # We now receive the specific monster character

@app.get("/")
def read_root():
    return {"status": "AI Dungeon Master is online"}

@app.get("/generate-map")
def generate_map(level: int = 1):
    prompt = f"""Generate a strictly 10x10 grid map. 
    Only use '#' for walls and '.' for floors.
    There must be exactly one '@' (player), one 'X' (exit), and exactly {level} 'M' (monster).
    Make mostly empty floors ('.') and few walls ('#').
    Output exactly 10 lines of 10 characters."""
    
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    
    raw_text = completion.choices[0].message.content
    valid_chars = [c for c in raw_text if c in ['#', '.', '@', 'X', 'M']]
    
    while len(valid_chars) < 100: valid_chars.append('.')
    grid = [valid_chars[i*10 : (i+1)*10] for i in range(10)]
    
    # Validation logic - mutating 'M' into Z, G, or V
    p_found, x_found = False, False
    m_count = 0
    for r in range(10):
        for c in range(10):
            char = grid[r][c]
            if char == '@':
                if p_found: grid[r][c] = '.'
                else: p_found = True
            elif char == 'X':
                if x_found: grid[r][c] = '.'
                else: x_found = True
            elif char == 'M':
                if m_count >= level: 
                    grid[r][c] = '.'
                else: 
                    # Assign a random specific monster type
                    grid[r][c] = random.choice(list(MONSTER_TYPES.keys()))
                    m_count += 1
            # Ensure we don't delete our mutated monsters if they already exist
            elif char not in ['#', '.', '@', 'X'] + list(MONSTER_TYPES.keys()):
                grid[r][c] = '.'

    if not p_found: grid[1][1] = '@'
    if not x_found: grid[8][8] = 'X'
    
    # Fill missing monsters
    while m_count < level:
        r, c = random.randint(0, 9), random.randint(0, 9)
        if grid[r][c] == '.':
            grid[r][c] = random.choice(list(MONSTER_TYPES.keys()))
            m_count += 1
            
    # Path carver (guarantees winnable map)
    py, px = next(((r, c) for r, row in enumerate(grid) for c, val in enumerate(row) if val == '@'), (1,1))
    xy, xx = next(((r, c) for r, row in enumerate(grid) for c, val in enumerate(row) if val == 'X'), (8,8))
    
    step_x = 1 if xx > px else -1
    if px != xx:
        for c in range(px, xx + step_x, step_x):
            if grid[py][c] == '#': grid[py][c] = '.'
            
    step_y = 1 if xy > py else -1
    if py != xy:
        for r in range(py, xy + step_y, step_y):
            if grid[r][xx] == '#': grid[r][xx] = '.'

    return {"map": grid}

@app.post("/move-monster")
def move_monster(req: MoveRequest):
    # BFS Pathfinding
    queue = [(req.my, req.mx, [])]
    visited = set([(req.my, req.mx)])
    best_move = "S" 
    
    while queue:
        y, x, path = queue.pop(0)
        
        if y == req.py and x == req.px:
            if path: best_move = path[0]
            break
            
        for dy, dx, move in [(-1,0,'W'), (1,0,'S'), (0,-1,'A'), (0,1,'D')]:
            ny, nx = y + dy, x + dx
            # Treat walls AND other monsters as obstacles to prevent stacking
            if 0 <= ny < 10 and 0 <= nx < 10 and req.level[ny][nx] not in ['#'] + list(MONSTER_TYPES.keys()) and (ny, nx) not in visited:
                visited.add((ny, nx))
                queue.append((ny, nx, path + [move]))

    # Generative AI - Dynamic flavor text based on the monster type!
    distance = abs(req.py - req.my) + abs(req.px - req.mx)
    monster_name = MONSTER_TYPES.get(req.m_char, "Monster")
    
    prompt = f"You are a terrifying {monster_name} hunting a player in a dungeon. The player is {distance} steps away. Give me a 1-sentence, extremely short and creepy taunt specific to your {monster_name} nature."
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        taunt = completion.choices[0].message.content.replace('"', '').strip()
    except:
        taunt = "*Growls loudly in the darkness...*"

    return {"move": best_move, "taunt": taunt}