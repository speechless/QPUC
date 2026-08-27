import json, time, websockets
from ..server import game, esp_clients, web_clients, web_sessions, log
import modele


# ══════════════════════════════════════════════════════════════════════
#  WEBSOCKET
# ══════════════════════════════════════════════════════════════════════
# async def esp_handler(ws: WebSocketServerProtocol):
#     buzzer_id = None
#     try:
#         async for raw in ws:
#             try: data = json.loads(raw)
#             except: continue
#             event = data.get("event")
#             if event == "hello":
#                 buzzer_id = data.get("id", f"esp_{id(ws)}")
#                 name      = data.get("name", buzzer_id)
#                 esp_clients[buzzer_id] = {"ws": ws, "name": name}
#                 game.log(f"📡 Buzzer connecté : {name} ({buzzer_id})")
#                 # Buzzers actifs en 9pts, toujours actifs en facaface/egalite selon le mode
#                 should_enable = (game.phase == "PHASE_9PTS" or
#                                (game.phase == ""PHASE_EGALITE"" and game.ff_timer_running) or
#                                (game.phase == PHASE_EGALITE and game.round_active))
#                 await ws.send(json.dumps({"cmd": "enable" if should_enable else "disable"}))
#                 await broadcast_state()
#             elif event == "buzz" and buzzer_id:
#                 pressed = data.get("state") == "pressed"
#                 if not pressed: continue
#                 p = game.player_by_buzzer(buzzer_id)
#                 if not p: continue
#                 if game.phase == "PHASE_9PTS":
#                     # Vérifier que le joueur peut buzzer : pas déjà buzzé, pas éliminé, pas qualifié
#                     if p.id in game.buzzed_wrong or p.qualified or p.eliminated or game.winner_pid: 
#                         continue
#                     if p.id not in game.buzzer_order: 
#                         game.buzzer_order.append(p.id)
#                     if game.winner_pid is None:
#                         game.winner_pid = p.id
#                         game.log(f"🔔 {p.name} buzzé en premier !")
#                         await broadcast_esp({"cmd": "disable"})
#                         await broadcast_state()
#                 elif game.phase == PHASE_EGALITE and game.round_active:
#                     await eq_buzz(p.id)
#                 elif game.phase == """PHASE_EGALITE""" and game.ff_timer_running:
#                     await ff_buzz_in(p.id)
#     except websockets.exceptions.ConnectionClosed: pass
#     finally:
#         if buzzer_id:
#             esp_clients.pop(buzzer_id, None)
#             game.log(f"📡 Buzzer déconnecté : {buzzer_id}")
#         await broadcast_state()


async def web_handler(ws):
    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except:
                continue
            
            if data.get("isAdmin") == True:
                await handle_admin_cmd(data)

            elif data.get("type") == "hello":
                client_session_id = data.get("client_id")

                if client_session_id in web_sessions["web_session_id"]:
                    web_sessions[client_session_id].ws_sessions.append(ws)
                else:
                    new_web_session = modele.Web_Session(client_session_id,ws)
                    web_sessions.add(new_web_session)

            # elif ... :
    
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if client_session_id:
            web_sessions[client_session_id].ws_sessions.remove(ws)


async def handle_admin_cmd(data: dict):
    typeCmd = data.get("type")
#     if typeCmd == "PHASE_SETUP":
#         game = GameState()

#         for index, playerData in enumerate(data.get("players", [])):
#             if not isinstance(playerData, dict):
#                 continue

#             name = str(playerData.get("name", "") or f"Joueur {index + 1}").strip()
#             buzzer_id = str(playerData.get("buzzer_id", "") or "").strip()
#             buzzer = Buzzer(buzzer_id, name)
#             addPlayerGame(game, name, buzzer)

#         for themeData in data.get("themes", []):
#             if not isinstance(themeData, dict):
#                 continue

#             theme = str(themeData.get("theme", "") or "").strip()
#             index = themeData.get("index")
#             if index is None:
#                 continue
#             addThemeGame(game, theme, int(index))

#         game.phase = "PHASE_NPG"
#         log.info(game.to_dict())
#         await sendUpdateGameState(game)

#         log.info("🎮 Nouvelle partie démarrée")
#     else:
        # log.warning(f"Commande inconnue : {typeCmd}")

