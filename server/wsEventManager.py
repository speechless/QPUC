import json, websockets
from main import game, esp_sessions, web_sessions, log
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

            if data.get("isAdmin") == True:
                await handle_admin_cmd(data)

            elif data.get("type") == "hello":
                client_session_id = data.get("client_session_id")

                if client_session_id in web_sessions:
                    web_sessions[client_session_id].ws_sessions.append(ws)
                else:
                    new_web_session = modele.Web_Session(client_session_id, ws)
                    web_sessions[client_session_id] = new_web_session

                await wsd.sendUpdateGameState(game)
            # elif ... :
    
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
                if esp_session_id in esp_sessions:
                    esp_sessions[esp_session_id].ws_session = ws
                else:
                    new_esp_session = modele.ESP_Session(esp_session_id, ws)
                    esp_sessions[esp_session_id] = new_esp_session
                log.info(f"ESP connecté : {esp_session_id}")

    except websockets.exceptions.ConnectionClosed: 
        log.info(f"Connection perdue : {esp_session_id}")
    finally:
        if esp_session_id and esp_session_id in esp_sessions:
            esp_sessions[esp_session_id].ws_session = None
            log.info(f"ESP déconnecté : {esp_session_id}")
        await wsd.sendUpdateGameState(game)



async def handle_admin_cmd(data: dict):
    typeCmd = data.get("type")
    if typeCmd == "end_init":
        #game = modele.GameState()

        for index, playerData in enumerate(data.get("players", [])):
            if not isinstance(playerData, dict):
                continue

            name = str(playerData.get("name", "") or f"Joueur {index + 1}").strip()
            buzzer_id = str(playerData.get("buzzer_id", "") or "").strip()
            buzzer = modele.Buzzer(buzzer_id, name)
            initPhase.add_player_game(game, name, buzzer)

        for themeData in data.get("themes", []):
            if not isinstance(themeData, dict):
                continue

            theme = str(themeData.get("theme", "") or "").strip()
            index = themeData.get("index")
            if index is None:
                continue
            initPhase.add_theme_game(game, theme, int(index))

        game.phase = "PHASE_NPG"
        log.info(game.to_dict())
        await wsd.sendUpdateGameState(game)

        log.info("🎮 Nouvelle partie démarrée")

    elif typeCmd == "esp_list_rq":
        await wsd.send_web({
            "type": "esp_list_rs",
            "esp_sessions": [s.to_dict() for s in esp_sessions.values()]
        })
    
    else:
        log.warning(f"Commande inconnue : {typeCmd}")