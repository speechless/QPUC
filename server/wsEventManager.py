import json, websockets
from main import game, buzzer_sessions, web_sessions, log
from server import modele, wsDiffusion as wsd
from server.phases import setupPhase, npgPhase, qalsPhase

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
                if game.phase == modele.PHASE_SETUP:
                    for index, playerData in enumerate(data.get("players", [])):
                        if not isinstance(playerData, dict):
                            continue
        
                        name = str(playerData.get("name", "") or f"Joueur {index + 1}").strip()
                        buzzer_id = str(playerData.get("buzzer_id", "") or "").strip()
                        esp_s = next((b for b in buzzer_sessions if b.bid == buzzer_id), None)
                        if esp_s != None:
                            setupPhase.add_player_game(game, name, esp_s)
                            log.info(f"Joueur ajouté : {name} (buzzer_id: {buzzer_id})")
                        else:
                            setupPhase.add_player_game(game, name, modele.Buzzer("NON-BUZZER_"+name, "NON-BUZZER_"+name, "", None))
                            log.warning(f"ESP non trouvé pour le buzzer_id : {buzzer_id}")

                    npgPhase.reset_players(game)
                    for themeData in data.get("themes", []):
                        if not isinstance(themeData, dict):
                            continue
        
                        theme = str(themeData.get("theme", "") or "").strip()
                        index = themeData.get("index")
                        if index is None:
                            continue
                        setupPhase.add_theme_game(game, theme, int(index))
        
                    game.phase = modele.PHASE_NPG
                    log.info(game.to_dict())
                    log.info("🎮 Nouvelle partie démarrée")
                    await wsd.sendUpdateGameState(game)

                elif game.phase == modele.PHASE_NPG:
                    npgPhase.stop_players(game)
                    game.phase = modele.PHASE_QALS
                    game.QALS_currentPid = game.NPG_qualified_pids[0]
                    log.info("🎮 Phase NPG terminée, passage à la phase QALS")
                    await wsd.sendUpdateGameState(game)

        
            elif typeCmd == "esp_list_rq":
                await wsd.send_web({
                    "type": "esp_list_rs",
                    "buzzer_sessions": [s.to_dict() for s in buzzer_sessions]
                })

            elif typeCmd == "activate_buzzers":
                buzzers = data.get("buzzers", [])
                for buzzer_id in buzzers:
                    esp_s = next((b for b in buzzer_sessions if b.bid == buzzer_id), None)
                    if esp_s:
                        esp_s.isActivated = True
                        log.info(f"Buzzer activé : {esp_s.bid}")
                npgPhase.update_deactivated_players(game)
                await wsd.sendUpdateGameState(game)

            elif typeCmd == "deactivate_buzzers":
                buzzers = data.get("buzzers", [])
                for buzzer_id in buzzers:
                    esp_s = next((b for b in buzzer_sessions if b.bid == buzzer_id), None)
                    if esp_s:
                        esp_s.isActivated = False
                        esp_s.isTalking = False
                        log.info(f"Buzzer désactivé : {esp_s.bid}")
                npgPhase.update_deactivated_players(game)
                await wsd.sendUpdateGameState(game)


            elif typeCmd == "buzzer_ask_to_talk":
                buzzer_id = data.get("buzzer_id")

                own_player = next((p for p in game.players if p.buzzer and p.buzzer.bid == buzzer_id), None)
                blocking_player = next((p for p in game.players if p.buzzer and p.buzzer.bid != buzzer_id and p.buzzer.isTalking),None)

                if own_player and own_player.buzzer.isTalking:
                    log.info(f"{buzzer_id} a déjà la main")

                elif own_player and not own_player.buzzer.isActivated:
                    log.info(f"{buzzer_id} ne peut pas prendre la main car il est désactivé")

                elif blocking_player:
                    log.info(f"{buzzer_id} ne peut pas prendre la main car {blocking_player.buzzer.name} parle")

                else:
                    esp_s = next((b for b in buzzer_sessions if b.bid == buzzer_id), None)
                    if esp_s:
                        esp_s.isTalking = True
                        log.info(f"Buzzer prend la main : {esp_s.bid}")

                await wsd.sendUpdateGameState(game)

            elif typeCmd == "toggle_question_mode":
                npgPhase.toggle_question_mode(game)
                log.info(f"Mode de question changé : {game.NPG_mode}")
                await wsd.sendUpdateGameState(game)

            elif typeCmd == "points_next_q_manuel":
                npgPhase.points_next_q_manuel(game)
                await wsd.sendUpdateGameState(game)

            elif typeCmd == "npg_modify_player_points":
                if data.get("player_id"):
                    npgPhase.npg_add_points_to_player(game, next((p for p in game.players if p.pid == data.get("player_id")), None), data.get("points",game.NPG_q_value), data.get("is_manual", False))   
                    if not game.NPG_Finished:
                        npgPhase.next_question(game)
                    await wsd.sendUpdateGameState(game)
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
                    esp_s.isConnected = True
                    log.info(f"ESP connecté : {esp_s.name, esp_s.bid}")
                else:
                    new_esp_session = modele.Buzzer(data.get("bid"),data.get("name"),esp_session_id, ws)
                    new_esp_session.isConnected = True
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
                esp_s.isConnected = False
                log.info(f"ESP déconnecté : {esp_s.bid}")
        await wsd.sendUpdateGameState(game)
