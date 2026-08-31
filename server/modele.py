import time, uuid

QALS_DURATION = 40      # en seconde
FAF_DURATION   = 20     # en seconde. Par question face à face, divisé en 4 zones égales

PHASE_SETUP = "Setup"
PHASE_NPG = "9 point gagnants"
PHASE_QALS = "4 à la suite"
PHASE_TIEBREAK = "Tiebreak"
PHASE_FAF = "Face à face"


# Zones du face à face : 4 pts dans la première zone, puis 3, 2, 1
FAF_ZONES = [4, 3, 2, 1]      # points par zone
FAF_ZONE_DUR = FAF_DURATION / len(FAF_ZONES)  # secondes par zone

class Web_Session:
    def __init__(self, web_session_id : str, ws):
        self.web_session_id = web_session_id
        self.ws_sessions = [ws]

    def add_web_device(self, web_device):
        self.ws_sessions.append(web_device)


class Buzzer:
    def __init__(self, bid : str, name : str, esp_session_id : str, ws = None):
        self.bid = bid
        self.name = name
        self.esp_session_id = esp_session_id
        self.ws_session = ws
        self.isConnected = False # connection établie entre serveur et esp
        self.isActivated = False # n'est pas bloqué, peut buzzer
        self.isTalking = False # a buzzé, a la main
        self.batteryLevel = -1

    def to_dict(self):
        return {
            "bid": self.bid,
            "name": self.name,
            "esp_session_id": self.esp_session_id,
            "isConnected": self.isConnected,
            "isActivated": self.isActivated,
            "isTalking": self.isTalking,
            "batteryLevel": self.batteryLevel
        }


class Player:
    def __init__(self, pid : str, name : str, buzzer : Buzzer = None):
        self.pid = pid
        self.name = name
        self.buzzer = buzzer
        self.scoreNPG = 0
        self.isQualifiedNPG = False
        self.scoreQALS = 0
        self.isQualifiedQALS = False
        self.scoreTiebreak = 0
        self.isQualifiedTieBreak = False
        self.scoreFAF = 0
        self.isWinner = False
    
    def to_dict(self):
        return {
            "pid": self.pid,
            "name": self.name,
            "buzzer_id": self.buzzer.bid if self.buzzer else None,
            "buzzer_name": self.buzzer.name if self.buzzer else None,
            "buzzer_esp_session_id": self.buzzer.esp_session_id if self.buzzer else None,
            "buzzer_batteryLevel": self.buzzer.batteryLevel if self.buzzer else -1,
            "scoreNPG": self.scoreNPG,
            "isQualifiedNPG": self.isQualifiedNPG,
            "scoreQALS": self.scoreQALS,
            "isQualifiedQALS": self.isQualifiedQALS,
            "scoreTiebreak": self.scoreTiebreak,
            "isQualifiedTieBreak": self.isQualifiedTieBreak,
            "scoreFAF": self.scoreFAF,
            "isWinner": self.isWinner
        }


class GameState:
    def __init__(self, players = None, themes = None):
        self.game_id    = str(uuid.uuid4())[:8]
        self.created_at = time.strftime("%Y-%m-%d %H:%M")
        self.phase      = PHASE_SETUP
        self.players    = players if players is not None else []
        self.themes     = themes if themes is not None else ["", "", "", ""]
        self.finished   = False
        self.history    = []

# 9 points gagnants
        self.NPG_mode      = "auto"
        self.NPG_q_value        = 1
        self.NPG_q_count        = 0
        self.NPG_round_active   = False
        self.NPG_buzzed_wrong   = []
        self.NPG_qualified_pids   = []    # pids des joueurs qualifiés pour la manche suivante
        self.NPG_qualified_count = 0


# 4 à la suite
        self.QALS_currentPid    = None
        self.QALS_score          = 0    # bonnes réponses consécutives actuelles
        self.QALS_best           = 0    # meilleur score consécutif du tour en cours

        self.QALS_timer_end      = 0.0
        self.QALS_timer_running  = False

        self.QALS_theme_count   = 0 # nombre de thèmes déjà passés
        self.QALS_theme_chosen   = 0 # thème choisi par le candidat actuel
        self.QALS_themes_taken   = []   # indices de thèmes déjà utilisés

        self.QALS_done_pids      = []
        self.QALS_best_scores    = {}   # {pid: meilleur_score}
        

# Tiebreak
        self.TB_pids         = []
        self.TB_scores       = {}
        self.TB_buzzed_wrong = []
        self.TB_winner_pid    = None


# Face à face
        self.FAF_player_a       = None
        self.FAF_player_b       = None
        self.FAF_scores         = {}    # {pid: points cumulés}
        self.FAF_winner_pid      = None
        self.FAF_timer_end      = 0.0   # fin du chrono 20s courant
        self.FAF_timer_running  = False
        self.FAF_active_pid     = None
        self.FAF_buzzed_pid     = None
        self.FAF_current_pts    = 4     # valeur actuelle selon zone chrono
        self.FAF_max_pts    = 21    # points à atteindre pour gagner le face à face


    def to_dict(self):
        return {
            "game_id": self.game_id,
            "created_at": self.created_at,
            "phase": self.phase,
            "players": [p.to_dict() for p in self.players],
            "themes": self.themes,
            "finished": self.finished,
            "history": self.history,
            "NPG_mode": self.NPG_mode,
            "NPG_q_value": self.NPG_q_value,
            "NPG_q_count": self.NPG_q_count,
            "NPG_round_active": self.NPG_round_active,
            "NPG_buzzed_wrong": self.NPG_buzzed_wrong,
            "NPG_qualified_pids": self.NPG_qualified_pids,
            "NPG_qualified_count": self.NPG_qualified_count,
            "QALS_currentPid": self.QALS_currentPid,
            "QALS_score": self.QALS_score,
            "QALS_best": self.QALS_best,
            "QALS_timer_end": self.QALS_timer_end,
            "QALS_timer_running": self.QALS_timer_running,
            "QALS_theme_count": self.QALS_theme_count,
            "QALS_theme_chosen": self.QALS_theme_chosen,
            "QALS_themes_taken": self.QALS_themes_taken,
            "QALS_done_pids": self.QALS_done_pids,
            "QALS_best_scores": self.QALS_best_scores,
            "TB_pids": self.TB_pids,
            "TB_scores": self.TB_scores,
            "TB_buzzed_wrong": self.TB_buzzed_wrong,
            "TB_winner_pid": self.TB_winner_pid,
            "FAF_player_a": self.FAF_player_a,
            "FAF_player_b": self.FAF_player_b,
            "FAF_scores": self.FAF_scores,
            "FAF_winner_pid": self.FAF_winner_pid,
            "FAF_timer_end": self.FAF_timer_end,
            "FAF_timer_running": self.FAF_timer_running,
            "FAF_active_pid": self.FAF_active_pid,
            "FAF_buzzed_pid": self.FAF_buzzed_pid,
            "FAF_current_pts": self.FAF_current_pts,
            "FAF_max_pts": self.FAF_max_pts
        }


    def player_by_id(self, pid):
        return next((p for p in self.players if p.pid == pid), None)

    def player_by_buzzer(self, bid):
        return next((p for p in self.players if p.buzzer and p.buzzer.bid == bid), None)
    
#--- Fonctions pour le mode 9 points gagnants
    def NPG_auto_q_value(self):
        n = 4 - len(self.NPG_qualified_count())
        if n == 4: return (self.NPG_q_count % 3) + 1
        if n == 3: return 2
        return 3
    
#--- Fonction pour le mode Face à face
    def FAF_zone_points(self):
        """Points selon le temps restant dans la question faf."""
        elapsed = FAF_DURATION - max(0, self.FAF_timer_end - time.time())
        zone = min(int(elapsed / FAF_ZONE_DUR), len(FAF_ZONES) - 1)
        return FAF_ZONES[zone]
    
    def log(self, msg):
        entry = {"t": time.strftime("%H:%M:%S"), "msg": msg}
        self.history.append(entry)
        self.history = self.history[-100:]
        