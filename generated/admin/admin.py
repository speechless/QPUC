from state import game, saves, log
import state
from modele import GameState, Player, PHASE_9PTS
from diffusion import broadcast_state, broadcast_esp
from steps.neufPG import nine_start_round, nine_validate, nine_adjust_points
from steps.quatreALaSuite import four_choose_theme, four_start_player, four_answer, four_end_turn
from steps.faceAFace import ff_setup, ff_start_question, ff_answer
from steps.egalite import eq_start, eq_answer

# ══════════════════════════════════════════════════════════════════════
#  COMMANDES ADMIN
# ══════════════════════════════════════════════════════════════════════
async def handle_admin_cmd(data: dict):
    global game
    cmd = data.get("cmd")
    try:
        log.info(f"Admin command received: {cmd} -- payload keys: {list(data.keys())}")
    except: pass

    if cmd == "setup_game":
        # Create a fresh GameState then replace attributes on the existing object
        new_game = GameState()
        for i, pd in enumerate(data.get("players", [])):
            new_game.players.append(Player(f"p{i+1}", pd["name"].strip(), pd.get("buzzer_id","").strip()))
        new_game.themes = data.get("themes", ["","","",""])
        new_game.phase  = PHASE_9PTS
        # Mutate existing game object so other modules keep the same reference
        game.__dict__.clear()
        game.__dict__.update(new_game.__dict__)
        game.themes = data.get("themes", ["","","",""])
        game.phase  = PHASE_9PTS
        game.log("🎮 Nouvelle partie démarrée")
        await broadcast_esp({"cmd": "enable"})
        await broadcast_state()

    elif cmd == "load_game":
        saved = next((s for s in saves if s.get("game_id") == data.get("game_id")), None)
        if saved:
            new_game = GameState.from_dict(saved)
            game.__dict__.clear()
            game.__dict__.update(new_game.__dict__)
            game.log("📂 Partie chargée")
            await broadcast_state()

    # 9 pts
    elif cmd == "nine_start_round":    await nine_start_round()
    elif cmd == "nine_validate":       await nine_validate(data["pid"], bool(data["correct"]))
    elif cmd == "nine_adjust":         await nine_adjust_points(data["pid"], int(data["delta"]))
    elif cmd == "nine_set_mode":
        game.nine_mode = data["mode"]; game.log(f"Mode : {game.nine_mode}")
        await broadcast_state()
    elif cmd == "nine_set_value":
        game.q_value = int(data["value"]); game.log(f"Valeur → {game.q_value}pt")
        await broadcast_state()

    # 4 suite
    elif cmd == "four_choose_theme":   await four_choose_theme(data["pid"], int(data["theme_index"]))
    elif cmd == "four_start":          await four_start_player(data["pid"])
    elif cmd == "four_answer":         await four_answer(bool(data["correct"]))
    elif cmd == "four_end_turn":       await four_end_turn("Arrêt manuel")

    # ff
    elif cmd == "ff_setup":            await ff_setup(data["pid_a"], data["pid_b"])
    elif cmd == "ff_start_question":   await ff_start_question()
    elif cmd == "ff_answer":           await ff_answer(bool(data["correct"]))
    elif cmd == "ff_set_target":
        game.ff_total_target = int(data["target"])
        await broadcast_state()

    # egalite
    elif cmd == "eq_start":            await eq_start(data["pids"])
    elif cmd == "eq_answer":           await eq_answer(bool(data["correct"]))

    # navigation
    elif cmd == "set_phase":
        game.phase = data["phase"]
        game.round_active = False; game.four_timer_running = False; game.ff_timer_running = False
        game.winner_pid = None
        game.log(f"📌 Phase → {game.phase}")
        await broadcast_esp({"cmd": "disable"})
        await broadcast_state()

    elif cmd == "reset_round":
        game.buzzer_order = []; game.buzzed_wrong = []; game.winner_pid = None; game.round_active = False
        # Réactiver les buzzers après un reset
        await broadcast_esp({"cmd": "enable"})
        await broadcast_state()

    elif cmd == "enable_buzzers":
        # Buzzers sont maintenant toujours actifs, cette commande ne fait rien
        pass

    else:
        log.warning(f"Commande inconnue : {cmd}")
