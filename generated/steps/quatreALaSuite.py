import time
from state import game, log
from modele import FOUR_DURATION, PHASE_EGALITE, PHASE_FACAFACE
from diffusion import broadcast_state, broadcast_esp
from steps.egalite import eq_start

# ══════════════════════════════════════════════════════════════════════
#  4 À LA SUITE
# ══════════════════════════════════════════════════════════════════════
async def four_choose_theme(pid, theme_index):
    """Le candidat a choisi son thème."""
    p = game.player_by_id(pid)
    if not p: return
    game.four_theme_chosen = theme_index
    game.log(f"🎯 {p.name} choisit le thème {theme_index+1}")
    await broadcast_state()

async def four_start_player(pid):
    p = game.player_by_id(pid)
    if not p: return
    game.four_current_pid   = pid
    game.four_score         = 0
    game.four_best          = game.four_best_scores.get(pid, 0)
    game.four_theme_chosen  = None
    game.four_timer_end     = time.time() + FOUR_DURATION
    game.four_timer_running = True
    game.log(f"⏱ Tour de {p.name} — 4 à la suite")
    await broadcast_esp({"cmd": "disable"})
    await broadcast_state()

async def four_answer(correct: bool):
    if not game.four_timer_running: return
    if time.time() > game.four_timer_end:
        await four_end_turn("Temps écoulé"); return
    p = game.player_by_id(game.four_current_pid)
    if not p: return
    if correct:
        game.four_score += 1
        if game.four_score > game.four_best:
            game.four_best = game.four_score
        game.log(f"✅ {p.name} : {game.four_score} consécutives (record: {game.four_best})")
        if game.four_score >= 4:
            game.log(f"🌟 {p.name} réussit le 4 à la suite !")
            game.four_best_scores[p.id] = 4
            await four_end_turn("4/4 réussi !"); return
    else:
        game.log(f"❌ {p.name} — repart de 0 (record: {game.four_best})")
        game.four_score = 0   # remet à 0 mais continue le tour !
    await broadcast_state()

async def four_end_turn(reason=""):
    pid = game.four_current_pid
    if pid:
        # Enregistrer le meilleur score de ce tour
        prev = game.four_best_scores.get(pid, 0)
        game.four_best_scores[pid] = max(prev, game.four_best)
        if pid not in game.four_done_pids:
            game.four_done_pids.append(pid)
    game.four_timer_running = False
    if reason: game.log(f"🔚 {reason}")
    game.four_current_pid = None; game.four_score = 0; game.four_best = 0
    game.four_theme_chosen = None
    game.four_theme_index  = (game.four_theme_index + 1) % 4
    # Vérifier si tous ont joué
    active_pids = [p.id for p in game.players if not p.eliminated]
    remaining   = [pid for pid in active_pids if pid not in game.four_done_pids]
    if not remaining:
        game.log("🏁 4 à la suite terminé pour tous — calcul des qualifiés")
        await four_determine_qualifiers()
    else:
        await broadcast_state()

async def four_determine_qualifiers():
    """Détermine les 2 meilleurs pour le face à face."""
    scores = [(pid, game.four_best_scores.get(pid, 0)) for pid in [p.id for p in game.players if not p.eliminated]]
    scores.sort(key=lambda x: -x[1])
    if len(scores) < 2:
        await broadcast_state(); return

    top_score   = scores[0][1]
    second_score = scores[1][1]

    # Trouver égalités à la 2e place
    tied_for_second = [pid for pid, sc in scores[1:] if sc == second_score]

    if len(tied_for_second) > 1:
        # Égalité pour la 2e place → départage
        game.log(f"⚖️ Égalité pour la 2e place → départage")
        # Qualifier le 1er automatiquement
        first_pid = scores[0][0]
        p1 = game.player_by_id(first_pid)
        if p1: p1.qualified = True; game.log(f"✅ {p1.name} qualifié (1er)")
        # Lancer le départage
        game.phase = PHASE_EGALITE
        await eq_start(tied_for_second)
    else:
        # Top 2 clairs
        for i, (pid, sc) in enumerate(scores[:2]):
            p = game.player_by_id(pid)
            if p: p.qualified = True; game.log(f"✅ {p.name} qualifié (score {sc})")
        for pid, sc in scores[2:]:
            p = game.player_by_id(pid)
            if p: p.eliminated = True
        game.phase = PHASE_FACAFACE
        game.log("🏁 Les 2 qualifiés pour le face à face sont déterminés")
        await broadcast_state()