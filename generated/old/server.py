#!/usr/bin/env python3
"""
QPUC — Serveur principal
========================
pip install websockets
python server.py

Ports :
  8765 → WebSocket  (/esp pour les buzzers ESP8266, /web pour admin+display)
  8080 → HTTP statique (admin.html, display.html)
"""

import asyncio, json, logging, time, http.server, threading, os, uuid
from pathlib import Path
import websockets
from websockets.server import WebSocketServerProtocol

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("qpuc")

SAVE_FILE     = Path("qpuc_saves.json")
FOUR_DURATION = 40
FF_DURATION   = 60

PHASE_SETUP    = "setup"
PHASE_9PTS     = "9pts"
PHASE_4SUITE   = "4suite"
PHASE_FACAFACE = "facaface"
PHASE_EGALITE  = "egalite"
PHASE_FIN      = "fin"


# ══════════════════════════════════════════════════════════════════════
#  MODÈLES
# ══════════════════════════════════════════════════════════════════════
class Player:
    def __init__(self, pid, name, buzzer_id=""):
        self.id         = pid
        self.name       = name
        self.buzzer_id  = buzzer_id
        self.points     = 0
        self.qualified  = False
        self.eliminated = False

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d):
        p = cls(d["id"], d["name"], d.get("buzzer_id", ""))
        p.points     = d.get("points", 0)
        p.qualified  = d.get("qualified", False)
        p.eliminated = d.get("eliminated", False)
        return p


class GameState:
    def __init__(self):
        self.game_id    = str(uuid.uuid4())[:8]
        self.created_at = time.strftime("%Y-%m-%d %H:%M")
        self.phase      = PHASE_SETUP
        self.players    = []
        self.themes     = ["", "", "", ""]
        self.finished   = False
        self.history    = []
        # 9 pts
        self.nine_mode      = "auto"
        self.q_value        = 1
        self.q_count        = 0
        self.round_active   = False
        self.buzzer_order   = []
        self.buzzed_wrong   = []
        self.winner_pid     = None
        # 4 suite
        self.four_current_pid    = None
        self.four_score          = 0
        self.four_timer_end      = 0.0
        self.four_timer_running  = False
        self.four_done_pids      = []
        self.four_theme_index    = 0
        # ff
        self.ff_player_a      = None
        self.ff_player_b      = None
        self.ff_scores        = {}
        self.ff_timer_end     = 0.0
        self.ff_timer_running = False
        self.ff_active_pid    = None
        self.ff_buzzed_pid    = None
        self.ff_wrong_pid     = None
        # egalite
        self.eq_pids         = []
        self.eq_scores       = {}
        self.eq_buzzed_wrong = []

    def unqualified_players(self):
        return [p for p in self.players if not p.qualified and not p.eliminated]

    def qualified_count(self):
        return sum(1 for p in self.players if p.qualified)

    def player_by_id(self, pid):
        return next((p for p in self.players if p.id == pid), None)

    def player_by_buzzer(self, bid):
        return next((p for p in self.players if p.buzzer_id == bid), None)

    def auto_q_value(self):
        n = len(self.unqualified_players())
        if n >= 4: return (self.q_count % 3) + 1
        if n == 3: return 2
        return 3

    def log(self, msg):
        entry = {"t": time.strftime("%H:%M:%S"), "msg": msg}
        self.history.append(entry)
        self.history = self.history[-100:]
        log.info(msg)

    def to_dict(self):
        return {
            "game_id": self.game_id, "created_at": self.created_at,
            "phase": self.phase, "players": [p.to_dict() for p in self.players],
            "themes": self.themes, "finished": self.finished, "history": self.history,
            "nine_mode": self.nine_mode, "q_value": self.q_value,
            "q_count": self.q_count, "round_active": self.round_active,
            "buzzer_order": self.buzzer_order, "buzzed_wrong": self.buzzed_wrong,
            "winner_pid": self.winner_pid,
            "four_current_pid": self.four_current_pid, "four_score": self.four_score,
            "four_timer_end": self.four_timer_end,
            "four_timer_running": self.four_timer_running,
            "four_done_pids": self.four_done_pids,
            "four_theme_index": self.four_theme_index,
            "ff_player_a": self.ff_player_a, "ff_player_b": self.ff_player_b,
            "ff_scores": self.ff_scores, "ff_timer_end": self.ff_timer_end,
            "ff_timer_running": self.ff_timer_running,
            "ff_active_pid": self.ff_active_pid, "ff_buzzed_pid": self.ff_buzzed_pid,
            "ff_wrong_pid": self.ff_wrong_pid,
            "eq_pids": self.eq_pids, "eq_scores": self.eq_scores,
            "eq_buzzed_wrong": self.eq_buzzed_wrong,
        }

    @classmethod
    def from_dict(cls, d):
        g = cls()
        for k in ["game_id","created_at","phase","themes","finished","history",
                  "nine_mode","q_value","q_count","round_active","buzzer_order",
                  "buzzed_wrong","winner_pid","four_current_pid","four_score",
                  "four_timer_end","four_timer_running","four_done_pids",
                  "four_theme_index","ff_player_a","ff_player_b","ff_scores",
                  "ff_timer_end","ff_timer_running","ff_active_pid","ff_buzzed_pid",
                  "ff_wrong_pid","eq_pids","eq_scores","eq_buzzed_wrong"]:
            if k in d: setattr(g, k, d[k])
        g.players = [Player.from_dict(p) for p in d.get("players", [])]
        return g


# ══════════════════════════════════════════════════════════════════════
#  ÉTAT GLOBAL
# ══════════════════════════════════════════════════════════════════════
game: GameState   = GameState()
saves: list       = []
esp_clients: dict = {}
web_clients: set  = set()


def load_saves():
    global saves
    if SAVE_FILE.exists():
        try: saves = json.loads(SAVE_FILE.read_text("utf-8"))
        except: saves = []

def write_saves():
    SAVE_FILE.write_text(json.dumps(saves, ensure_ascii=False, indent=2), "utf-8")

def save_current_game():
    d = game.to_dict()
    for i, s in enumerate(saves):
        if s.get("game_id") == d["game_id"]:
            saves[i] = d; write_saves(); return
    saves.append(d); write_saves()

def saves_meta():
    return [{"game_id": s["game_id"], "created_at": s.get("created_at",""),
             "phase": s.get("phase",""), "finished": s.get("finished", False),
             "players": [p["name"] for p in s.get("players",[])]} for s in saves]


# ══════════════════════════════════════════════════════════════════════
#  DIFFUSION
# ══════════════════════════════════════════════════════════════════════
async def broadcast_state():
    save_current_game()
    payload = {"type": "state", "game": game.to_dict(),
               "saves_meta": saves_meta(), "server_now": time.time()}
    msg = json.dumps(payload)
    dead = set()
    for ws in web_clients:
        try: await ws.send(msg)
        except: dead.add(ws)
    web_clients.difference_update(dead)

async def send_esp(bid, data):
    ws = esp_clients.get(bid)
    if ws:
        try: await ws.send(json.dumps(data))
        except: pass

async def broadcast_esp(data, exclude=None):
    for bid, ws in list(esp_clients.items()):
        if bid == exclude: continue
        try: await ws.send(json.dumps(data))
        except: pass


# ══════════════════════════════════════════════════════════════════════
#  LOGIQUE 9 POINTS
# ══════════════════════════════════════════════════════════════════════
async def nine_start_round():
    game.buzzer_order = []; game.buzzed_wrong = []
    game.winner_pid = None; game.round_active = True
    if game.nine_mode == "auto":
        game.q_value = game.auto_q_value()
    game.log(f"▶ Question — {game.q_value} pt(s)")
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
        remaining = [x for x in game.buzzer_order if x not in game.buzzed_wrong]
        if remaining:
            game.winner_pid = remaining[0]
            game.log(f"🔔 Main à {game.player_by_id(remaining[0]).name}")
        else:
            game.round_active = False; game.winner_pid = None; game.q_count += 1
            await broadcast_esp({"cmd": "disable"})
        await broadcast_state()

async def check_nine_end():
    n = len(game.players)
    if game.qualified_count() >= n - 1:
        game.log("🏁 Manche 9 points terminée !")
        for p in game.players:
            if not p.qualified: p.eliminated = True
        game.phase = PHASE_FIN
    await broadcast_state()

async def nine_manual_add(pid, pts):
    p = game.player_by_id(pid)
    if not p: return
    p.points += pts
    if p.points >= 9 and not p.qualified:
        p.qualified = True
        game.log(f"🏆 {p.name} QUALIFIÉ ! (manuel)")
    else:
        game.log(f"✏️ {p.name} +{pts}pt → {min(p.points,9)}pt")
    await check_nine_end()


# ══════════════════════════════════════════════════════════════════════
#  LOGIQUE 4 À LA SUITE
# ══════════════════════════════════════════════════════════════════════
async def four_start_player(pid):
    p = game.player_by_id(pid)
    if not p: return
    game.four_current_pid   = pid
    game.four_score         = 0
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
        game.log(f"✅ {p.name} : {game.four_score}/4")
        if game.four_score >= 4:
            p.points += 1
            game.log(f"🌟 {p.name} réussit le 4 à la suite ! +1pt → {p.points}pt")
            await four_end_turn("4/4 réussi !"); return
    else:
        game.log(f"❌ {p.name} — fin du tour ({game.four_score}/4)")
        await four_end_turn("Mauvaise réponse"); return
    await broadcast_state()

async def four_end_turn(reason=""):
    game.four_timer_running = False
    pid = game.four_current_pid
    if pid and pid not in game.four_done_pids:
        game.four_done_pids.append(pid)
    if reason: game.log(f"🔚 {reason}")
    game.four_current_pid = None; game.four_score = 0
    game.four_theme_index = (game.four_theme_index + 1) % 4
    await broadcast_state()


# ══════════════════════════════════════════════════════════════════════
#  LOGIQUE FACE À FACE
# ══════════════════════════════════════════════════════════════════════
async def ff_start(pid_a, pid_b):
    pa = game.player_by_id(pid_a); pb = game.player_by_id(pid_b)
    if not pa or not pb: return
    game.ff_player_a = pid_a; game.ff_player_b = pid_b
    game.ff_scores = {pid_a: 0, pid_b: 0}
    game.ff_timer_end = time.time() + FF_DURATION
    game.ff_timer_running = True
    game.ff_active_pid = pid_a; game.ff_buzzed_pid = None; game.ff_wrong_pid = None
    game.log(f"⚔️ Face à face : {pa.name} vs {pb.name}")
    await broadcast_esp({"cmd": "enable"})
    await broadcast_state()

async def ff_buzz_in(pid):
    if game.ff_buzzed_pid: return
    if pid == game.ff_wrong_pid: return
    if pid not in (game.ff_player_a, game.ff_player_b): return
    game.ff_buzzed_pid = pid
    p = game.player_by_id(pid)
    game.log(f"🔔 {p.name} buzze !")
    await broadcast_esp({"cmd": "disable"})
    await broadcast_state()

async def ff_answer(correct: bool):
    pid = game.ff_buzzed_pid
    if not pid: return
    p = game.player_by_id(pid)
    other = game.ff_player_b if pid == game.ff_player_a else game.ff_player_a
    if correct:
        game.ff_scores[pid] = game.ff_scores.get(pid, 0) + 1
        sa = game.ff_scores.get(game.ff_player_a, 0)
        sb = game.ff_scores.get(game.ff_player_b, 0)
        game.log(f"✅ {p.name} marque ({sa}–{sb})")
        game.ff_buzzed_pid = None; game.ff_wrong_pid = None
        game.ff_active_pid = pid
        await broadcast_esp({"cmd": "enable"})
    else:
        game.log(f"❌ {p.name} rate — main à l'adversaire")
        game.ff_wrong_pid = pid; game.ff_buzzed_pid = None
        game.ff_active_pid = other
        await broadcast_esp({"cmd": "enable"})
    await broadcast_state()

async def ff_end():
    game.ff_timer_running = False
    a = game.ff_player_a; b = game.ff_player_b
    sa = game.ff_scores.get(a, 0); sb = game.ff_scores.get(b, 0)
    pa = game.player_by_id(a); pb = game.player_by_id(b)
    if sa > sb:
        pa.points += 1; game.log(f"🏆 {pa.name} gagne ({sa}–{sb}) +1pt")
    elif sb > sa:
        pb.points += 1; game.log(f"🏆 {pb.name} gagne ({sb}–{sa}) +1pt")
    else:
        game.log(f"🤝 Égalité face à face ({sa}–{sb})")
    game.ff_buzzed_pid = None; game.ff_active_pid = None
    await broadcast_esp({"cmd": "disable"})
    await broadcast_state()


# ══════════════════════════════════════════════════════════════════════
#  LOGIQUE ÉGALITÉ
# ══════════════════════════════════════════════════════════════════════
async def eq_start(pids):
    game.eq_pids = pids; game.eq_scores = {p: 0 for p in pids}
    game.eq_buzzed_wrong = []; game.winner_pid = None; game.round_active = True
    names = [game.player_by_id(p).name for p in pids if game.player_by_id(p)]
    game.log(f"⚖️ Départage : {', '.join(names)}")
    await broadcast_esp({"cmd": "enable"})
    await broadcast_state()

async def eq_buzz(pid):
    if pid in game.eq_buzzed_wrong or pid not in game.eq_pids or game.winner_pid: return
    game.winner_pid = pid
    game.log(f"🔔 {game.player_by_id(pid).name} buzze (départage)")
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
            game.phase = PHASE_FIN; game.winner_pid = None
            await broadcast_esp({"cmd": "disable"})
        else:
            game.winner_pid = None; game.eq_buzzed_wrong = []; game.round_active = True
            await broadcast_esp({"cmd": "enable"})
    else:
        game.eq_buzzed_wrong.append(pid); game.winner_pid = None
        if set(game.eq_buzzed_wrong) >= set(game.eq_pids):
            game.eq_buzzed_wrong = []
        await broadcast_esp({"cmd": "enable"})
    await broadcast_state()


# ══════════════════════════════════════════════════════════════════════
#  COMMANDES ADMIN
# ══════════════════════════════════════════════════════════════════════
async def handle_admin_cmd(data: dict):
    cmd = data.get("cmd")
    if cmd == "setup_game":
        global game
        game = GameState()
        for i, pd in enumerate(data.get("players", [])):
            game.players.append(Player(f"p{i+1}", pd["name"].strip(), pd.get("buzzer_id","").strip()))
        game.themes = data.get("themes", ["","","",""])
        game.phase  = PHASE_9PTS
        game.log("🎮 Nouvelle partie démarrée")
        await broadcast_esp({"cmd": "disable"})
        await broadcast_state()
    elif cmd == "load_game":
        saved = next((s for s in saves if s.get("game_id") == data.get("game_id")), None)
        if saved:
            game = GameState.from_dict(saved)
            game.log("📂 Partie chargée")
            await broadcast_state()
    elif cmd == "nine_start_round": await nine_start_round()
    elif cmd == "nine_validate":    await nine_validate(data["pid"], bool(data["correct"]))
    elif cmd == "nine_manual_add":  await nine_manual_add(data["pid"], int(data["pts"]))
    elif cmd == "nine_set_mode":
        game.nine_mode = data["mode"]
        game.log(f"Mode : {game.nine_mode}")
        await broadcast_state()
    elif cmd == "nine_set_value":
        game.q_value = int(data["value"])
        game.log(f"Valeur question → {game.q_value} pt(s)")
        await broadcast_state()
    elif cmd == "four_start":      await four_start_player(data["pid"])
    elif cmd == "four_answer":     await four_answer(bool(data["correct"]))
    elif cmd == "four_end_turn":   await four_end_turn("Arrêt manuel")
    elif cmd == "ff_start":        await ff_start(data["pid_a"], data["pid_b"])
    elif cmd == "ff_answer":       await ff_answer(bool(data["correct"]))
    elif cmd == "ff_end":          await ff_end()
    elif cmd == "eq_start":        await eq_start(data["pids"])
    elif cmd == "eq_answer":       await eq_answer(bool(data["correct"]))
    elif cmd == "set_phase":
        game.phase = data["phase"]
        game.round_active = False; game.four_timer_running = False; game.ff_timer_running = False
        game.winner_pid = None
        game.log(f"📌 Phase → {game.phase}")
        await broadcast_esp({"cmd": "disable"})
        await broadcast_state()
    elif cmd == "reset_round":
        game.buzzer_order = []; game.buzzed_wrong = []; game.winner_pid = None; game.round_active = False
        await broadcast_esp({"cmd": "disable"})
        await broadcast_state()
    elif cmd == "enable_buzzers":
        game.round_active = True
        await broadcast_esp({"cmd": "enable"})
        await broadcast_state()
    else:
        log.warning(f"Commande inconnue : {cmd}")


# ══════════════════════════════════════════════════════════════════════
#  WEBSOCKET
# ══════════════════════════════════════════════════════════════════════
async def esp_handler(ws: WebSocketServerProtocol):
    buzzer_id = None
    try:
        async for raw in ws:
            try: data = json.loads(raw)
            except: continue
            event = data.get("event")
            if event == "hello":
                buzzer_id = data.get("id", f"esp_{id(ws)}")
                esp_clients[buzzer_id] = ws
                game.log(f"📡 ESP connecté : {data.get('name', buzzer_id)} ({buzzer_id})")
                should = ((game.phase == PHASE_9PTS and game.round_active) or
                          (game.phase == PHASE_FACAFACE and game.ff_timer_running) or
                          (game.phase == PHASE_EGALITE and game.round_active))
                await ws.send(json.dumps({"cmd": "enable" if should else "disable"}))
                await broadcast_state()
            elif event == "buzz" and buzzer_id:
                pressed = data.get("state") == "pressed"
                p = game.player_by_buzzer(buzzer_id)
                if not p or not pressed: continue
                if game.phase == PHASE_9PTS and game.round_active:
                    if p.id in game.buzzed_wrong or p.qualified: continue
                    if p.id not in game.buzzer_order: game.buzzer_order.append(p.id)
                    if game.winner_pid is None:
                        game.winner_pid = p.id
                        game.log(f"🔔 {p.name} buzzé en premier !")
                        await broadcast_esp({"cmd": "disable"}, exclude=buzzer_id)
                        await broadcast_state()
                elif game.phase == PHASE_EGALITE and game.round_active:
                    await eq_buzz(p.id)
                elif game.phase == PHASE_FACAFACE and game.ff_timer_running:
                    await ff_buzz_in(p.id)
    except websockets.exceptions.ConnectionClosed: pass
    finally:
        if buzzer_id: esp_clients.pop(buzzer_id, None); game.log(f"📡 ESP déconnecté : {buzzer_id}")
        await broadcast_state()

async def web_handler(ws: WebSocketServerProtocol):
    web_clients.add(ws)
    try:
        payload = {"type": "state", "game": game.to_dict(),
                   "saves_meta": saves_meta(), "server_now": time.time()}
        await ws.send(json.dumps(payload))
    except: pass
    try:
        async for raw in ws:
            try: data = json.loads(raw)
            except: continue
            await handle_admin_cmd(data)
    except websockets.exceptions.ConnectionClosed: pass
    finally: web_clients.discard(ws)

async def router(ws: WebSocketServerProtocol):
    path = ws.request.path

    if path == "/esp": await esp_handler(ws)
    else: await web_handler(ws)


# ══════════════════════════════════════════════════════════════════════
#  TIMER TICK
# ══════════════════════════════════════════════════════════════════════
async def timer_tick():
    while True:
        await asyncio.sleep(1)
        changed = False
        if game.four_timer_running and time.time() > game.four_timer_end:
            p = game.player_by_id(game.four_current_pid)
            game.log(f"⏰ Temps écoulé — {p.name if p else ''} ({game.four_score}/4)")
            await four_end_turn("Temps écoulé"); changed = True
        if game.ff_timer_running and time.time() > game.ff_timer_end:
            await ff_end(); changed = True
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
    log.info("  QPUC — Serveur démarré")
    log.info("  Admin     : http://localhost:8080/admin.html")
    log.info("  Display   : http://localhost:8080/display.html")
    log.info("════════════════════════════════════════════════")
    threading.Thread(target=start_http, daemon=True).start()
    async with websockets.serve(router, "0.0.0.0", 8765):
        await asyncio.gather(asyncio.Future(), timer_tick())

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: log.info("Arrêté.")
