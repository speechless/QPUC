import json, time, websockets
from websockets.server import WebSocketServerProtocol
from state import game, esp_clients, web_clients, log, saves_meta, esp_list
from modele import PHASE_9PTS, PHASE_FACAFACE, PHASE_EGALITE
from diffusion import broadcast_state, broadcast_esp
from admin.admin import handle_admin_cmd
from steps.egalite import eq_buzz
from steps.faceAFace import ff_buzz_in

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
                name      = data.get("name", buzzer_id)
                esp_clients[buzzer_id] = {"ws": ws, "name": name}
                game.log(f"📡 Buzzer connecté : {name} ({buzzer_id})")
                # Buzzers actifs en 9pts, toujours actifs en facaface/egalite selon le mode
                should_enable = (game.phase == PHASE_9PTS or
                               (game.phase == PHASE_FACAFACE and game.ff_timer_running) or
                               (game.phase == PHASE_EGALITE and game.round_active))
                await ws.send(json.dumps({"cmd": "enable" if should_enable else "disable"}))
                await broadcast_state()
            elif event == "buzz" and buzzer_id:
                pressed = data.get("state") == "pressed"
                if not pressed: continue
                p = game.player_by_buzzer(buzzer_id)
                if not p: continue
                if game.phase == PHASE_9PTS:
                    # Vérifier que le joueur peut buzzer : pas déjà buzzé, pas éliminé, pas qualifié
                    if p.id in game.buzzed_wrong or p.qualified or p.eliminated or game.winner_pid: 
                        continue
                    if p.id not in game.buzzer_order: 
                        game.buzzer_order.append(p.id)
                    if game.winner_pid is None:
                        game.winner_pid = p.id
                        game.log(f"🔔 {p.name} buzzé en premier !")
                        await broadcast_esp({"cmd": "disable"})
                        await broadcast_state()
                elif game.phase == PHASE_EGALITE and game.round_active:
                    await eq_buzz(p.id)
                elif game.phase == PHASE_FACAFACE and game.ff_timer_running:
                    await ff_buzz_in(p.id)
    except websockets.exceptions.ConnectionClosed: pass
    finally:
        if buzzer_id:
            esp_clients.pop(buzzer_id, None)
            game.log(f"📡 Buzzer déconnecté : {buzzer_id}")
        await broadcast_state()

async def web_handler(ws: WebSocketServerProtocol):
    web_clients.add(ws)
    try:
        payload = {"type": "state", "game": game.to_dict(),
                   "saves_meta": saves_meta(), "server_now": time.time(),
                   "esp_list": esp_list()}
        await ws.send(json.dumps(payload))
    except: pass
    try:
        async for raw in ws:
            try: data = json.loads(raw)
            except: continue
            try:
                log.info(f"Web admin message from {getattr(ws, 'remote_address', None)}: {data.get('cmd')}")
            except: pass
            await handle_admin_cmd(data)
    except websockets.exceptions.ConnectionClosed: pass
    finally: web_clients.discard(ws)

async def router(ws: WebSocketServerProtocol):
    path = ws.request.path

    if path == "/esp": await esp_handler(ws)
    else: await web_handler(ws)