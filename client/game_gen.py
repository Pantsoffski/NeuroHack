import requests
import msvcrt
import os
import sys
from rich.console import Console

console = Console()

# Insert your actual Hugging Face API URL here
HF_API_BASE = "https://pantsoffski-neurohack-backend.hf.space"
MONSTER_CHARS = ['Z', 'G', 'V']

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_ai_map(current_level):
    clear_screen()
    console.print(f"[bold blue]Connecting to Cloud AI to generate LVL {current_level}...[/bold blue]")
    try:
        response = requests.get(f"{HF_API_BASE}/generate-map?level={current_level}", timeout=15)
        if response.status_code == 200:
            return response.json()["map"]
    except Exception as e:
        console.print(f"[red]Server error: {e}[/red]")
        return [list("..........") for _ in range(10)]

def get_monster_move(level, py, px, my, mx, m_char):
    payload = {
        "level": level,
        "py": py, "px": px, 
        "my": my, "mx": mx,
        "m_char": m_char
    }
    
    try:
        response = requests.post(f"{HF_API_BASE}/move-monster", json=payload, timeout=5)
        if response.status_code == 200:
            data = response.json()
            ans = data.get("move", "S").upper()
            taunt = data.get("taunt", "...")
            
            # Dynamic coloring for the taunt log
            color = "green" if m_char == 'Z' else "yellow" if m_char == 'G' else "red"
            name = "Zombie" if m_char == 'Z' else "Goblin" if m_char == 'G' else "Vampire"
            console.print(f"[bold {color}]{name} says: '{taunt}'[/bold {color}]")
            
            if 'W' in ans: return -1, 0
            if 'S' in ans: return 1, 0
            if 'A' in ans: return 0, -1
            if 'D' in ans: return 0, 1
    except Exception as e:
        console.print(f"[red]Connection failed: {e}[/red]")
    
    return 0, 0

def draw_game(level, current_level):
    clear_screen()
    console.print(f"[bold cyan]=== LVL {current_level} ===[/bold cyan]")
    
    # Parse the grid and inject colors dynamically
    for row in level:
        colored_row = ""
        for char in row:
            if char == '@': colored_row += "[bold cyan]@[/bold cyan]"
            elif char == 'X': colored_row += "[bold blue]X[/bold blue]"
            elif char == '#': colored_row += "[dim white]#[/dim white]"
            elif char == 'Z': colored_row += "[bold green]Z[/bold green]"
            elif char == 'G': colored_row += "[bold yellow]G[/bold yellow]"
            elif char == 'V': colored_row += "[bold red]V[/bold red]"
            else: colored_row += char
        console.print(colored_row)
        
    console.print("\n[dim]Enemies: [green]Z[/green]ombie | [yellow]G[/yellow]oblin | [red]V[/red]ampire[/dim]")
    console.print("[yellow]WASD to move | Q to quit[/yellow]")

def play_game():
    current_level = 1
    
    while True:
        level_map = get_ai_map(current_level)
        
        py, px = 1, 1
        monsters = []
        
        # Track monster positions AND their specific characters
        for r in range(10):
            for c in range(10):
                if level_map[r][c] == '@': 
                    py, px = r, c
                elif level_map[r][c] in MONSTER_CHARS: 
                    monsters.append([r, c, level_map[r][c]])

        game_over = False
        
        while not game_over:
            draw_game(level_map, current_level)
            
            key = msvcrt.getch().decode('utf-8').lower()
            if key == 'q': 
                sys.exit(0)
            
            new_py, new_px = py, px
            if key == 'w': new_py -= 1
            if key == 's': new_py += 1
            if key == 'a': new_px -= 1
            if key == 'd': new_px += 1

            moved = False
            if 0 <= new_py < 10 and 0 <= new_px < 10 and level_map[new_py][new_px] != '#':
                level_map[py][px] = '.'
                py, px = new_py, new_px
                
                if level_map[py][px] == 'X':
                    draw_game(level_map, current_level)
                    console.print("[bold green]You found the stairs! Descending deeper...[/bold green]")
                    import time
                    time.sleep(1.5)
                    current_level += 1
                    break 
                    
                level_map[py][px] = '@'
                moved = True
            
            if moved:
                for i in range(len(monsters)):
                    my, mx, m_char = monsters[i]
                    dy, dx = get_monster_move(level_map, py, px, my, mx, m_char)
                    new_my, new_mx = my + dy, mx + dx
                    
                    if 0 <= new_my < 10 and 0 <= new_mx < 10 and level_map[new_my][new_mx] == '.':
                        level_map[my][mx] = '.'
                        monsters[i] = [new_my, new_mx, m_char]
                        level_map[new_my][new_mx] = m_char # Put the correct letter back
                        
                    elif new_my == py and new_mx == px:
                        draw_game(level_map, current_level)
                        console.print(f"[bold red]GAME OVER! A {m_char} consumed you.[/bold red]")
                        sys.exit(0)

if __name__ == "__main__":
    play_game()