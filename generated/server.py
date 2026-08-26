#!/usr/bin/env python3
"""
QPUC — Serveur v3
=================
pip install websockets
python server.py

/esp  → buzzers ESP8266
/web  → admin + display
:8080 → HTTP statique
"""

import asyncio, json, logging, time, http.server, threading, os, uuid, websockets
from pathlib import Path

from state import game, log, load_saves, saves_meta, esp_list
from modele import *
from steps.neufPG import *
from steps.quatreALaSuite import *
from steps.faceAFace import *
from steps.egalite import *
from admin.admin import *
from websocket import router
from diffusion import broadcast_state










# ══════════════════════════════════════════════════════════════════════
#  TIMER TICK
# ══════════════════════════════════════════════════════════════════════
async def timer_tick():
    while True:
        await asyncio.sleep(0.5)
        changed = False

        # 4 suite
        if game.four_timer_running and time.time() > game.four_timer_end:
            p = game.player_by_id(game.four_current_pid)
            game.log(f"⏰ Temps écoulé — {p.name if p else ''} (record: {game.four_best})")
            await four_end_turn("Temps écoulé"); changed = True

        # ff — mise à jour de la zone de points + timeout question
        if game.ff_timer_running:
            new_pts = game.ff_zone_points()
            if new_pts != game.ff_current_pts:
                game.ff_current_pts = new_pts; changed = True
            if time.time() > game.ff_timer_end:
                await ff_timeout(); changed = True

        if game.four_timer_running or game.ff_timer_running or changed:
            await broadcast_state()


# ══════════════════════════════════════════════════════════════════════
#  HTTP + MAIN
# ══════════════════════════════════════════════════════════════════════
def start_http():
    os.chdir(Path(__file__).parent)
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    http.server.HTTPServer(("", 8080), H).serve_forever()

async def main():
    load_saves()
    log.info("════════════════════════════════════════════════")
    log.info("  QPUC  — Serveur démarré")
    log.info("  Admin     : http://localhost:8080/admin/admin.html")
    log.info("  Display   : http://localhost:8080/display.html")
    log.info("════════════════════════════════════════════════")
    threading.Thread(target=start_http, daemon=True).start()
    async with websockets.serve(router, "0.0.0.0", 8765):
        await asyncio.gather(asyncio.Future(), timer_tick())

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: log.info("Arrêté.")
