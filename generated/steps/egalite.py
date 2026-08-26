from state import game, log
from modele import PHASE_FACAFACE
from diffusion import broadcast_state, broadcast_esp
from steps.faceAFace import ff_setup

# ══════════════════════════════════════════════════════════════════════
#  ÉGALITÉ (départage 4 à la suite)
# ══════════════════════════════════════════════════════════════════════
async def eq_start(pids):
    game.eq_pids = pids; game.eq_scores = {p: 0 for p in pids}
    game.eq_buzzed_wrong = []; game.winner_pid = None; game.round_active = True
    names = [game.player_by_id(p).name for p in pids if game.player_by_id(p)]
    game.log(f"⚖️ Départage : {', '.join(names)} — premier à 2 points")
    await broadcast_esp({"cmd": "enable"})
    await broadcast_state()

async def eq_buzz(pid):
    if pid in game.eq_buzzed_wrong or pid not in game.eq_pids or game.winner_pid: return
    game.winner_pid = pid
    p = game.player_by_id(pid)
    game.log(f"🔔 {p.name} buzze (départage)")
    await broadcast_esp({"cmd": "disable"})
    await broadcast_state()

async def eq_answer(correct: bool):
    pid = game.winner_pid
    if not pid: return
    p = game.player_by_id(pid)
    if correct:
        game.eq_scores[pid] = game.eq_scores.get(pid, 0) + 1
        game.log(f"✅ {p.name} : {game.eq_scores[pid]}/2")
        if game.eq_scores[pid] >= 2:
            p.qualified = True
            game.log(f"🏆 {p.name} se qualifie au départage !")
            # Éliminer les autres
            for pid2 in game.eq_pids:
                if pid2 != pid:
                    pl = game.player_by_id(pid2)
                    if pl: pl.eliminated = True
            game.phase = PHASE_FACAFACE
            game.winner_pid = None
            await broadcast_esp({"cmd": "disable"})
            # Setup auto du face à face avec les 2 qualifiés
            qpids = [p2.id for p2 in game.players if p2.qualified]
            if len(qpids) == 2:
                await ff_setup(qpids[0], qpids[1])
        else:
            game.winner_pid = None; game.eq_buzzed_wrong = []; game.round_active = True
            await broadcast_esp({"cmd": "enable"})
    else:
        game.eq_buzzed_wrong.append(pid); game.winner_pid = None
        if set(game.eq_buzzed_wrong) >= set(game.eq_pids):
            game.eq_buzzed_wrong = []
        await broadcast_esp({"cmd": "enable"})
    await broadcast_state()

