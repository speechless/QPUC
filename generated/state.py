import logging, json, time, uuid
from pathlib import Path
from modele import GameState, Player

# ══════════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════════
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("qpuc")

# ══════════════════════════════════════════════════════════════════════
#  ÉTAT GLOBAL
# ══════════════════════════════════════════════════════════════════════
SAVE_FILE     = Path("qpuc_saves.json")
game: GameState   = GameState()
saves: list       = []
esp_clients: dict = {}   # buzzer_id → {ws, name}
web_clients: set  = set()

# ══════════════════════════════════════════════════════════════════════
#  FONCTIONS D'ACCÈS À L'ÉTAT
# ══════════════════════════════════════════════════════════════════════
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

def esp_list():
    """Liste des buzzers connectés pour l'admin."""
    return [{"id": bid, "name": info["name"]} for bid, info in esp_clients.items()]
