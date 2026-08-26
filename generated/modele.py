import time, uuid

FOUR_DURATION = 40
FF_DURATION   = 20   # 20s par question face à face, divisé en 4 zones de 5s

# Zones du face à face : 4 pts dans les 5 premières secondes, puis 3, 2, 1
FF_ZONES = [4, 3, 2, 1]      # points par zone
FF_ZONE_DUR = FF_DURATION / len(FF_ZONES)  # 5s par zone

PHASE_SETUP    = "setup"
PHASE_9PTS     = "9pts"
PHASE_4SUITE   = "4suite"
PHASE_FACAFACE = "facaface"
PHASE_EGALITE  = "egalite"
PHASE_FIN      = "fin"


# ══════════════════════════════════════════════════════════════════════
#  MODÈLES
# ══════════════════════════════════════════════════════════════════════
class Player:
    def __init__(self, pid, name, buzzer_id=""):
        self.id         = pid
        self.name       = name
        self.buzzer_id  = buzzer_id
        self.points     = 0
        self.qualified  = False
        self.eliminated = False

    def to_dict(self):
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d):
        p = cls(d["id"], d["name"], d.get("buzzer_id", ""))
        p.points     = d.get("points", 0)
        p.qualified  = d.get("qualified", False)
        p.eliminated = d.get("eliminated", False)
        return p


class GameState:
    def __init__(self):
        self.game_id    = str(uuid.uuid4())[:8]
        self.created_at = time.strftime("%Y-%m-%d %H:%M")
        self.phase      = PHASE_SETUP
        self.players    = []
        self.themes     = ["", "", "", ""]
        self.finished   = False
        self.history    = []

        # 9 pts
        self.nine_mode      = "auto"
        self.q_value        = 1
        self.q_count        = 0
        self.round_active   = False
        self.buzzer_order   = []
        self.buzzed_wrong   = []
        self.winner_pid     = None

        # 4 suite
        # best_scores = {pid: max_consec} enregistré pendant la manche
        self.four_current_pid    = None
        self.four_score          = 0    # bonnes réponses consécutives actuelles
        self.four_best           = 0    # meilleur score consécutif du tour en cours
        self.four_timer_end      = 0.0
        self.four_timer_running  = False
        self.four_done_pids      = []
        self.four_best_scores    = {}   # {pid: meilleur_score}
        self.four_theme_index    = 0
        self.four_theme_chosen   = None # thème choisi par le candidat actuel
        self.four_themes_taken   = []   # indices de thèmes déjà utilisés

        # ff
        self.ff_player_a       = None
        self.ff_player_b       = None
        self.ff_scores         = {}    # {pid: points cumulés}
        self.ff_timer_end      = 0.0   # fin du chrono 20s courant
        self.ff_timer_running  = False
        self.ff_active_pid     = None
        self.ff_buzzed_pid     = None
        self.ff_current_pts    = 4     # valeur actuelle selon zone chrono
        self.ff_total_target   = 12    # objectif points

        # egalite
        self.eq_pids         = []
        self.eq_scores       = {}
        self.eq_buzzed_wrong = []

    def unqualified_players(self):
        return [p for p in self.players if not p.qualified and not p.eliminated]

    def qualified_count(self):
        return sum(1 for p in self.players if p.qualified)

    def player_by_id(self, pid):
        return next((p for p in self.players if p.id == pid), None)

    def player_by_buzzer(self, bid):
        return next((p for p in self.players if p.buzzer_id == bid), None)

    def auto_q_value(self):
        n = len(self.unqualified_players())
        if n >= 4: return (self.q_count % 3) + 1
        if n == 3: return 2
        return 3

    def ff_zone_points(self):
        """Points selon le temps restant dans la question ff."""
        elapsed = FF_DURATION - max(0, self.ff_timer_end - time.time())
        zone = min(int(elapsed / FF_ZONE_DUR), len(FF_ZONES) - 1)
        return FF_ZONES[zone]

    def log(self, msg):
        from state import log
        entry = {"t": time.strftime("%H:%M:%S"), "msg": msg}
        self.history.append(entry)
        self.history = self.history[-100:]
        log.info(msg)

    def to_dict(self):
        return {
            "game_id": self.game_id, "created_at": self.created_at,
            "phase": self.phase, "players": [p.to_dict() for p in self.players],
            "themes": self.themes, "finished": self.finished, "history": self.history,
            "nine_mode": self.nine_mode, "q_value": self.q_value,
            "q_count": self.q_count, "round_active": self.round_active,
            "buzzer_order": self.buzzer_order, "buzzed_wrong": self.buzzed_wrong,
            "winner_pid": self.winner_pid,
            "four_current_pid": self.four_current_pid,
            "four_score": self.four_score, "four_best": self.four_best,
            "four_timer_end": self.four_timer_end,
            "four_timer_running": self.four_timer_running,
            "four_done_pids": self.four_done_pids,
            "four_best_scores": self.four_best_scores,
            "four_theme_index": self.four_theme_index,
            "four_theme_chosen": self.four_theme_chosen,
            "four_themes_taken": self.four_themes_taken,
            "ff_player_a": self.ff_player_a, "ff_player_b": self.ff_player_b,
            "ff_scores": self.ff_scores,
            "ff_timer_end": self.ff_timer_end,
            "ff_timer_running": self.ff_timer_running,
            "ff_active_pid": self.ff_active_pid,
            "ff_buzzed_pid": self.ff_buzzed_pid,
            "ff_current_pts": self.ff_current_pts,
            "ff_total_target": self.ff_total_target,
            "eq_pids": self.eq_pids, "eq_scores": self.eq_scores,
            "eq_buzzed_wrong": self.eq_buzzed_wrong,
            # computed
            "ff_zone_pts": self.ff_zone_points() if self.ff_timer_running else 4,
            "ff_zone_dur": FF_ZONE_DUR,
            "ff_total_dur": FF_DURATION,
        }

    @classmethod
    def from_dict(cls, d):
        g = cls()
        for k in ["game_id","created_at","phase","themes","finished","history",
                  "nine_mode","q_value","q_count","round_active","buzzer_order",
                  "buzzed_wrong","winner_pid","four_current_pid","four_score",
                  "four_best","four_timer_end","four_timer_running","four_done_pids",
                  "four_best_scores","four_theme_index","four_theme_chosen",
                  "four_themes_taken","ff_player_a","ff_player_b","ff_scores",
                  "ff_timer_end","ff_timer_running","ff_active_pid","ff_buzzed_pid",
                  "ff_current_pts","ff_total_target","eq_pids","eq_scores","eq_buzzed_wrong"]:
            if k in d: setattr(g, k, d[k])
        g.players = [Player.from_dict(p) for p in d.get("players", [])]
        return g
