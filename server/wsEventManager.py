import json, websockets
from main import game, buzzer_sessions, web_sessions, log
from server import modele, wsDiffusion as wsd
from server.phases import initPhase

async def web_handler(ws):
    client_session_id = None
    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except:
                continue

            typeCmd = data.get("type")

            if typeCmd == "hello":
                client_session_id = data.get("client_session_id")

                if client_session_id in web_sessions:
                    web_sessions[client_session_id].ws_sessions.append(ws)
                else:
                    new_web_session = modele.Web_Session(client_session_id, ws)
                    web_sessions[client_session_id] = new_web_session

                await wsd.sendUpdateGameState(game)

            elif typeCmd == "end_phase":
                if game.phase == modele.PHASE_INIT:
                    for index, playerData in enumerate(data.get("players", [])):
                        if not isinstance(playerData, dict):
                            continue
        
                        name = str(playerData.get("name", "") or f"Joueur {index + 1}").strip()
                        buzzer_id = str(playerData.get("buzzer_id", "") or "").strip()
                        esp_s = next((b for b in buzzer_sessions if b.bid == buzzer_id), None)
                        if esp_s != None:
                            initPhase.add_player_game(game, name, esp_s)
                            log.info(f"Joueur ajouté : {name} (buzzer_id: {buzzer_id})")
                        else:
                            log.warning(f"ESP non trouvé pour le buzzer_id : {buzzer_id}")
        
                    for themeData in data.get("themes", []):
                        if not isinstance(themeData, dict):
                            continue
        
                        theme = str(themeData.get("theme", "") or "").strip()
                        index = themeData.get("index")
                        if index is None:
                            continue
                        initPhase.add_theme_game(game, theme, int(index))
        
                    game.phase = modele.PHASE_NPG
                    log.info(game.to_dict())
                    await wsd.sendUpdateGameState(game)
        
                    log.info("🎮 Nouvelle partie démarrée")
        
            elif typeCmd == "esp_list_rq":
                await wsd.send_web({
                    "type": "esp_list_rs",
                    "buzzer_sessions": [s.to_dict() for s in buzzer_sessions]
                })

            
            else:
                log.warning(f"Commande inconnue : {typeCmd}")

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        if client_session_id and client_session_id in web_sessions:
            web_sessions[client_session_id].ws_sessions.remove(ws)


async def esp_handler(ws):
    esp_session_id = None
    try:
        async for raw in ws:
            try: 
                data = json.loads(raw)
            except: 
                continue
            event = data.get("event")

            if event == "hello":
                esp_session_id = data.get("client_session_id")
                esp_s = next((b for b in buzzer_sessions if b.esp_session_id == esp_session_id), None)
                if esp_s != None:
                    esp_s.ws_session = ws
                    log.info(f"ESP connecté : {esp_s.name, esp_s.bid}")
                else:
                    new_esp_session = modele.Buzzer(data.get("bid"),data.get("name"),esp_session_id, ws)
                    buzzer_sessions.add(new_esp_session)
                    log.info(f"ESP connecté : {new_esp_session.name, new_esp_session.bid}")
                await wsd.sendUpdateGameState(game)

    except websockets.exceptions.ConnectionClosed: 
        log.info(f"Connection perdue : {data.get("bid")}")
    finally:
        if esp_session_id :
            esp_s = next((b for b in buzzer_sessions if b.esp_session_id == esp_session_id), None)
            if esp_s:
                esp_s.ws_session = None
                log.info(f"ESP déconnecté : {esp_s.bid}")
        await wsd.sendUpdateGameState(game)
