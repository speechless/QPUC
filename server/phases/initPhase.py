import uuid
from .. import modele as m

def addPlayerGame(game_state : m.GameState, name : str, buzzer : m.Buzzer):
    player = m.Player(pid=str(uuid.uuid4())[:4], name=name, buzzer=buzzer)
    
    # Add the player to the game state
    game_state.players.append(player)
    return game_state

def addThemeGame(game_state : m.GameState, theme : str, index : int):
    if 0 <= index < 4:
        game_state.themes[index] = theme
    return game_state