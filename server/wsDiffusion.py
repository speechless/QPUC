from main import buzzer_sessions, web_sessions, log
import json

async def send_web(data):
    try:
        log.info(f"server to web: sending to {len(web_sessions)} web sessions")
    except: pass

    success = 0
    for web_session in web_sessions.values():
        for ws in list(web_session.ws_sessions):
            try:
                await ws.send(json.dumps(data))
                success += 1
            except Exception as e:
                try: log.warning(f"broadcast_state: failed to send to a web client: {e}")
                except: pass

        try: log.info(f"broadcast_state: {success} messages sent")
        except: pass

async def send_esp(ws_session_id, data):
    for esp_s in buzzer_sessions:
        if esp_s["ws_session"] == ws_session_id:
            try: await esp_s["ws"].send(json.dumps(data))
            except: log(f"ESP not found to this address : {ws_session_id}")

async def broadcast_esp(data):
    for esp_s in buzzer_sessions:
        try: await esp_s["ws"].send(json.dumps(data))
        except: log(f"ESP not found to this address : {esp_s["ws"]}")

async def sendUpdateGameState(game_state):
    payload = {"type": "state", "game": game_state.to_dict()}
    await send_web(payload)

async def sendInitBuzzer(buzzer):
    pass
    
