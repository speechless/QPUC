from server.modele import GameState

def update_deactivated_players(game: GameState):
    for player in game.players:
        if player.buzzer and not player.buzzer.isActivated:
            game.NPG_buzzed_wrong.append(player.pid)
    return game

def toggle_question_mode(game: GameState):
    game.NPG_mode = "manual" if game.NPG_mode == "auto" else "auto"
    return game

def points_next_q_manuel(game: GameState):
    if game.NPG_mode == "auto":
        game.NPG_q_value = (game.NPG_q_value % 3) + 1
    return game

def reset_players(game: GameState):
    for player in game.players:
        player.buzzer.isTalking = False
        player.buzzer.isActivated = True
    return game

def next_question(game: GameState):
    game.NPG_q_count += 1
    points_next_q_manuel(game)
    game.NPG_buzzed_wrong = []
    reset_players(game)
    return game