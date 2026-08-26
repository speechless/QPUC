import json, time
from state import game, web_clients, esp_clients, save_current_game, saves_meta, esp_list, log

# ══════════════════════════════════════════════════════════════════════
#  DIFFUSION
# ══════════════════════════════════════════════════════════════════════
async def broadcast_state():
    save_current_game()
    payload = {"type": "state", "game": game.to_dict(),
               "saves_meta": saves_meta(), "server_now": time.time(),
               "esp_list": esp_list()}
    msg = json.dumps(payload)
    try:
        log.info(f"broadcast_state: sending to {len(web_clients)} web clients")
    except: pass
    dead = set()
    success = 0
    for ws in list(web_clients):
        try:
            await ws.send(msg)
            success += 1
        except Exception as e:
            try: log.warning(f"broadcast_state: failed to send to a web client: {e}")
            except: pass
            dead.add(ws)
    if dead:
        web_clients.difference_update(dead)
        try: log.info(f"broadcast_state: removed {len(dead)} dead web clients")
        except: pass
    try: log.info(f"broadcast_state: {success} messages sent")
    except: pass

async def broadcast_esp(data, exclude=None):
    for bid, info in list(esp_clients.items()):
        if bid == exclude: continue
        try: await info["ws"].send(json.dumps(data))
        except: pass

async def send_esp(bid, data):
    info = esp_clients.get(bid)
    if info:
        try: await info["ws"].send(json.dumps(data))
        except: pass