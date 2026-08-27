import asyncio, logging, http.server, threading, os, websockets
from pathlib import Path

import server.modele as modele
import server.wsEventManager as wsEM

global game
global esp_sessions
global web_sessions
global log

game = modele.GameState() 
esp_sessions: set[modele.ESP_Session] = dict()    # ESP_Session  (une connection / buzzer)
web_sessions: set[modele.Web_Session] = dict()    # Web_Session  (plusieurs connections possibles pour un même affichage web)

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8765

logging.basicConfig(level=logging.INFO,format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("qpuc")

def start_http():
    os.chdir(Path(__file__).parent)
    class H(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    http.server.HTTPServer(("", 8080), H).serve_forever()


async def router(ws):
    path = ws.request.path
    if path == "/esp": 
        await wsEM.esp_handler(ws)
    else:
        await wsEM.web_handler(ws)


async def timer_tick():
    while True:
        await asyncio.sleep(0.5)
        changed = False

        # # 4 suite
        # if game.four_timer_running and time.time() > game.four_timer_end:
        #     p = game.player_by_id(game.four_current_pid)
        #     game.log(f"⏰ Temps écoulé — {p.name if p else ''} (record: {game.four_best})")
        #     await four_end_turn("Temps écoulé"); changed = True

        # # ff — mise à jour de la zone de points + timeout question
        # if game.ff_timer_running:
        #     new_pts = game.ff_zone_points()
        #     if new_pts != game.ff_current_pts:
        #         game.ff_current_pts = new_pts; changed = True
        #     if time.time() > game.ff_timer_end:
        #         await ff_timeout(); changed = True

        # if game.four_timer_running or game.ff_timer_running or changed:
        #     await broadcast_state()
    
async def main():
    log.info("════════════════════════════════════════════════")
    log.info("  QPUC  — Serveur démarré")
    log.info("  Admin     : http://localhost:8080/admin.html")
    log.info("  Display   : http://localhost:8080/display.html")
    log.info("═══════════════════════════════════════════════")
    threading.Thread(target=start_http, daemon=True).start()

    async with websockets.serve(router, SERVER_HOST, SERVER_PORT):
        #asyncio.create_task(timer_tick())
        await asyncio.get_running_loop().create_future()


if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: log.info("Arrêté.")