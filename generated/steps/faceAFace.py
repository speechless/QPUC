import time
from state import game, log
from modele import FF_DURATION, PHASE_FIN
from diffusion import broadcast_state, broadcast_esp

# ══════════════════════════════════════════════════════════════════════
#  FACE À FACE
# ══════════════════════════════════════════════════════════════════════
async def ff_start_question():
    """Lance le chrono d'une nouvelle question."""
    game.ff_timer_end     = time.time() + FF_DURATION
    game.ff_timer_running = True
    game.ff_buzzed_pid    = None
    game.ff_current_pts   = 4
    game.log(f"▶ Nouvelle question face à face")
    await broadcast_esp({"cmd": "enable"})
    await broadcast_state()

async def ff_setup(pid_a, pid_b):
    """Initialise le face à face avec les 2 finalistes."""
    pa = game.player_by_id(pid_a); pb = game.player_by_id(pid_b)
    if not pa or not pb: return
    game.ff_player_a   = pid_a; game.ff_player_b = pid_b
    game.ff_scores     = {pid_a: 0, pid_b: 0}
    game.ff_active_pid = pid_a; game.ff_buzzed_pid = None
    game.ff_timer_running = False
    game.log(f"⚔️ Face à face : {pa.name} vs {pb.name} — objectif {game.ff_total_target} pts")
    await broadcast_state()

async def ff_buzz_in(pid):
    if game.ff_buzzed_pid: return
    if pid not in (game.ff_player_a, game.ff_player_b): return
    if not game.ff_timer_running: return
    game.ff_buzzed_pid    = pid
    game.ff_current_pts   = game.ff_zone_points()
    game.ff_timer_running = False   # pause chrono pendant la réponse
    p = game.player_by_id(pid)
    game.log(f"🔔 {p.name} buzze ! ({game.ff_current_pts} pts si correct)")
    await broadcast_esp({"cmd": "disable"})
    await broadcast_state()

async def ff_answer(correct: bool):
    pid = game.ff_buzzed_pid
    if not pid: return
    p = game.player_by_id(pid)
    other = game.ff_player_b if pid == game.ff_player_a else game.ff_player_a
    if correct:
        pts = game.ff_current_pts
        game.ff_scores[pid] = game.ff_scores.get(pid, 0) + pts
        sa = game.ff_scores.get(game.ff_player_a, 0)
        sb = game.ff_scores.get(game.ff_player_b, 0)
        game.log(f"✅ {p.name} +{pts}pts → ({sa}–{sb})")
        game.ff_buzzed_pid  = None
        game.ff_active_pid  = pid
        # Vérifier victoire
        winner_score = game.ff_scores[pid]
        if winner_score >= game.ff_total_target:
            game.log(f"🏆 {p.name} remporte le face à face !")
            p.points += winner_score
            game.phase = PHASE_FIN
            await broadcast_esp({"cmd": "disable"})
            await broadcast_state()
            return
        # Nouvelle question
        await ff_start_question()
    else:
        game.log(f"❌ {p.name} — main à l'adversaire (chrono continue)")
        game.ff_buzzed_pid  = None
        game.ff_active_pid  = other
        # Reprendre le chrono là où il en était (ne pas le réinitialiser)
        game.ff_timer_running = True
        await broadcast_esp({"cmd": "enable"})
        await broadcast_state()

async def ff_timeout():
    """Temps écoulé sur la question en cours — on passe à la suivante."""
    game.ff_timer_running = False
    game.ff_buzzed_pid    = None
    game.log("⏰ Temps écoulé sur la question")
    # Alterner la main
    other = game.ff_player_b if game.ff_active_pid == game.ff_player_a else game.ff_player_a
    game.ff_active_pid = other
    await broadcast_state()