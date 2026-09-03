from server.modele import GameState
from main import log

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

def stop_players(game: GameState):
    for player in game.players:
        player.buzzer.isTalking = False
        player.buzzer.isActivated = False
    return game

def next_question(game: GameState):
    game.NPG_q_count += 1
    points_next_q_manuel(game)
    game.NPG_buzzed_wrong = []
    reset_players(game)
    return game

def npg_add_points_to_player(game: GameState, player: str, points: int, is_manual: bool = False):
    new_score = max(0, min(player.scoreNPG + points, 9))  # Ensure score is between 0 and 9
    if is_manual:
        log.info(f"Points manuels : {player.name} (score: {player.scoreNPG} -> {new_score})")
    else:
        log.info(f"Points automatiques : {player.name} (score: {player.scoreNPG} -> {new_score})")
    player.scoreNPG = new_score

    if player.scoreNPG >= 9 :
        if player.pid not in game.NPG_qualified_pids:
            player.isQualifiedNPG = True
            player.isActivated = False
            game.NPG_qualified_pids.append(player.pid)
            game.NPG_qualified_count += 1
            log.info(f"Joueur qualifié : {player.name} (score: {player.scoreNPG})")
            if game.NPG_qualified_count >= 3:
                log.info("3 joueurs qualifiés, fin de la manche")
                game.NPG_Finished = True
    else:
        if player.pid in game.NPG_qualified_pids:
            game.NPG_qualified_pids.remove(player.pid)
            game.NPG_qualified_count -= 1
            player.isQualifiedNPG = False
            log.info(f"Joueur disqualifié : {player.name} (score: {player.scoreNPG})")
    return game