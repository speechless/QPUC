from ..server import game, esp_clients, web_clients, log
import json

async def send_web(data):
    try:
        log.info(f"server to web: sending to {len(web_clients)} web clients")
    except: pass

    dead = set()
    success = 0
    for ws in list(web_clients):
        try:
            await ws.send(json.dumps(data))
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

async def send_esp(bid, data):
    info = esp_clients.get(bid)
    if info:
        try: await info["ws"].send(json.dumps(data))
        except: pass

async def broadcast_esp(data, exclude=None):
    for bid, info in list(esp_clients.items()):
        if bid in exclude: continue
        try: await info["ws"].send(json.dumps(data))
        except: pass





# async def sendUpdateGameState(game_state: GameState):
#     payload = {"type": "state", "game": game_state.to_dict(), "phase": game_state.phase, "numPlayers": str(len(game_state.players))}
#     dead = set()
#     for client in list(web_clients):
#         try:
#             await client.send(json.dumps(payload))
#         except Exception as exc:
#             log.exception("Erreur d'envoi de l'état à un client : %s", exc)
#             dead.add(client)
#     if dead:
#         web_clients.difference_update(dead)


# async def sendStateToClient(ws: WebSocketServerProtocol):
#     payload = {"type": "state", "game": game.to_dict(), "phase": game.phase, "numPlayers": str(len(game.players))}
#     try:
#         await ws.send(json.dumps(payload))
#     except Exception as exc:
#         log.warning("Impossible d'envoyer l'état au client reconnecté : %s", exc)