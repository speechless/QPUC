from state import game, log
from modele import PHASE_FIN
from diffusion import broadcast_esp, broadcast_state

# ══════════════════════════════════════════════════════════════════════
#  9 POINTS
# ══════════════════════════════════════════════════════════════════════
async def nine_start_round():
    game.buzzer_order = []; game.buzzed_wrong = []
    game.winner_pid = None; game.round_active = True
    if game.nine_mode == "auto":
        game.q_value = game.auto_q_value()
    game.log(f"▶ Question — {game.q_value} pt(s)")
    # Réinitialiser l'état des buzzers puis les activer pour la nouvelle question
    await broadcast_esp({"cmd": "reset"})
    await broadcast_esp({"cmd": "enable"})
    await broadcast_state()

async def nine_validate(pid, correct: bool):
    p = game.player_by_id(pid)
    if not p: return
    if correct:
        p.points += game.q_value
        if p.points >= 9 and not p.qualified:
            p.qualified = True
            game.log(f"🏆 {p.name} QUALIFIÉ !")
        else:
            game.log(f"✅ {p.name} +{game.q_value}pt → {min(p.points,9)}pt")
        game.round_active = False; game.winner_pid = None; game.q_count += 1
        await broadcast_esp({"cmd": "disable"})
        await check_nine_end()
    else:
        game.buzzed_wrong.append(pid)
        game.log(f"❌ {p.name} — faux")
        # Trouver les suivants dans l'ordre des buzzers qui n'ont pas encore
        # répondu faux.
        remaining = [x for x in game.buzzer_order if x not in game.buzzed_wrong]
        if remaining:
            # Il reste quelqu'un dans l'ordre des buzzers : main à lui
            game.winner_pid = remaining[0]
            next_p = game.player_by_id(remaining[0])
            game.log(f"🔔 Main à {next_p.name}")
            await broadcast_esp({"cmd": "enable"})
        else:
            # Aucun dans l'ordre des buzzers — vérifier s'il existe des joueurs
            # éligibles qui n'ont pas encore buzzé (donc potentiellement
            # capables de prendre la main)
            eligible_unbuzzed = [pl.id for pl in game.players
                                 if pl.id not in game.buzzed_wrong
                                 and not pl.qualified and not pl.eliminated
                                 and pl.id not in game.buzzer_order]
            if eligible_unbuzzed:
                game.winner_pid = None
                game.log("🔔 Main libre — autres joueurs peuvent buzzer")
                await broadcast_esp({"cmd": "enable"})
            else:
                game.winner_pid = None
                game.log("⚠️ Tous ont répondu faux")
                await broadcast_esp({"cmd": "disable"})
        await broadcast_state()

async def nine_adjust_points(pid, delta):
    """delta = +1..+3 ou -1..-3"""
    p = game.player_by_id(pid)
    if not p: return
    p.points = max(0, p.points + delta)
    if p.points >= 9 and not p.qualified:
        p.qualified = True
        game.log(f"🏆 {p.name} QUALIFIÉ !")
    elif p.qualified and p.points < 9:
        p.qualified = False
        game.log(f"↩️ {p.name} déqualifié ({p.points}pt)")
    else:
        sign = "+" if delta > 0 else ""
        game.log(f"✏️ {p.name} {sign}{delta}pt → {min(p.points,9)}pt")
    await check_nine_end()

async def check_nine_end():
    n = len(game.players)
    if game.qualified_count() >= n - 1:
        game.log("🏁 Manche 9 points terminée !")
        for p in game.players:
            if not p.qualified: p.eliminated = True
        game.phase = PHASE_FIN
    await broadcast_state()