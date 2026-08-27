/*
 * BUZZER ESP8266 — Système quiz "premier arrivé premier servi"
 *
 * Câblage :
 *   - Fin de course entre D1 (GPIO5) et GND  (pull-up interne activé)
 *     → repos : bouton FERMÉ = LOW  |  actionné : bouton OUVERT = HIGH
 *   - LED entre D5 (GPIO14) et GND via résistance 220Ω
 *     → s'allume quand on buzze avec succès
 *
 * Bibliothèques requises (Gestionnaire de bibliothèques Arduino) :
 *   - "WebSockets" par Markus Sattler  (chercher "WebSockets by Markus Sattler")
 *   - "ArduinoJson" par Benoit Blanchon
 */

#include <ESP8266WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// ─────────────────────────────────────────────
//  CONFIGURATION — à modifier avant de flasher
// ─────────────────────────────────────────────
const char* WIFI_SSID     = "TCHOUPICOMPUTER 0635";
const char* WIFI_PASSWORD = "X1[7973v";
const char* SERVER_HOST   = "192.168.137.1";  // IP du PC serveur
const int   SERVER_PORT   = 8765;
const char* BUZZER_ID     = "buzzer3";         // Unique par appareil : buzzer1..4
const char* BUZZER_NAME   = "Joueur 3";        // Nom affiché sur l'interface PC

// ─────────────────────────────────────────────
//  PINS
// ─────────────────────────────────────────────
const int PIN_BUTTON   = D1;   // GPIO5
const int PIN_LED      = D5;   // GPIO14 — allumée quand buzzé avec succès

// ─────────────────────────────────────────────
//  ÉTAT
// ─────────────────────────────────────────────
WebSocketsClient ws;

bool enabled         = false;  // Le PC autorise-t-il le buzzer ?
bool alreadyBuzzed   = false;  // A-t-on déjà buzzé ce round ?
bool wsConnected     = false;

// Debounce
bool     lastButtonState  = HIGH;
bool     buttonState      = HIGH;
unsigned long lastDebounce = 0;
const unsigned long DEBOUNCE_MS = 50;

// Reconnexion WiFi
unsigned long lastWifiCheck = 0;

// ─────────────────────────────────────────────
//  HELPERS LED
// ─────────────────────────────────────────────
void setLeds() {
  // LED allumée uniquement si on est le buzzer gagnant du round
  digitalWrite(PIN_LED, alreadyBuzzed ? HIGH : LOW);
}

// ─────────────────────────────────────────────
//  ENVOI D'UN ÉVÉNEMENT AU SERVEUR
// ─────────────────────────────────────────────
// pressed=true  : bouton actionné (fin de course ouvert = GPIO HIGH avec pull-up)
// pressed=false : bouton relâché  (fin de course fermé  = GPIO LOW)
void sendBuzz(bool pressed) {
  StaticJsonDocument<128> doc;
  doc["event"]  = "buzz";
  doc["id"]     = BUZZER_ID;
  doc["name"]   = BUZZER_NAME;
  doc["state"]  = pressed ? "pressed" : "released";
  doc["millis"] = millis();

  char buf[128];
  serializeJson(doc, buf);
  ws.sendTXT(buf);

  // LED allumée seulement si appui autorisé (premier arrivé)
  if (pressed && !alreadyBuzzed) {
    alreadyBuzzed = true;
  }
  setLeds();
  Serial.print("[BUZZ] state=");
  Serial.println(pressed ? "pressed" : "released");
}

void sendStatus() {
  StaticJsonDocument<128> doc;
  doc["event"] = "hello";
  doc["id"]    = BUZZER_ID;
  doc["name"]  = BUZZER_NAME;

  char buf[128];
  serializeJson(doc, buf);
  ws.sendTXT(buf);
}

// ─────────────────────────────────────────────
//  RÉCEPTION DES COMMANDES DU SERVEUR
// ─────────────────────────────────────────────
void handleMessage(uint8_t* payload, size_t length) {
  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    Serial.print("[WS] JSON invalide: ");
    Serial.println(err.c_str());
    return;
  }

  const char* cmd = doc["cmd"];
  if (!cmd) return;

  Serial.print("[CMD] ");
  Serial.println(cmd);

  if (strcmp(cmd, "enable") == 0) {
    enabled       = true;
    alreadyBuzzed = false;
  } else if (strcmp(cmd, "disable") == 0) {
    enabled       = false;
    alreadyBuzzed = false;
  } else if (strcmp(cmd, "reset") == 0) {
    // Nouveau round : on réinitialise sans changer l'état enabled
    alreadyBuzzed = false;
  } else if (strcmp(cmd, "lock") == 0) {
    // Quelqu'un d'autre a buzzé en premier
    enabled = false;
    if (!alreadyBuzzed) alreadyBuzzed = false;
  }

  setLeds();
}

// ─────────────────────────────────────────────
//  CALLBACK WEBSOCKET
// ─────────────────────────────────────────────
void onWsEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.println("[WS] Déconnecté");
      wsConnected = false;
      enabled     = false;
      setLeds();
      break;

    case WStype_CONNECTED:
      Serial.println("[WS] Connecté au serveur");
      wsConnected = true;
      sendStatus();
      setLeds();
      break;

    case WStype_TEXT:
      handleMessage(payload, length);
      break;

    default:
      break;
  }
}

// ─────────────────────────────────────────────
//  SETUP
// ─────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(100);

  pinMode(PIN_BUTTON, INPUT_PULLUP);
  pinMode(PIN_LED,    OUTPUT);
  digitalWrite(PIN_LED, LOW);

  // Connexion WiFi
  Serial.print("[WiFi] Connexion à ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < 15000) {
    delay(300);
    Serial.print(".");
    // Clignoter pendant la connexion
    digitalWrite(PIN_LED, !digitalRead(PIN_LED));
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println();
    Serial.print("[WiFi] Connecté. IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[WiFi] Échec de connexion — redémarrage dans 5s");
    delay(5000);
    ESP.restart();
  }

  // WebSocket
  ws.begin(SERVER_HOST, SERVER_PORT, "/esp");
  ws.onEvent(onWsEvent);
  ws.setReconnectInterval(3000);

  Serial.println("[INIT] Buzzer prêt.");
}

// ─────────────────────────────────────────────
//  LOOP
// ─────────────────────────────────────────────
void loop() {
  ws.loop();

  // Reconnexion WiFi si perdu
  if (millis() - lastWifiCheck > 10000) {
    lastWifiCheck = millis();
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("[WiFi] Perdu — reconnexion...");
      WiFi.reconnect();
    }
  }

  // Lecture bouton avec debounce
  // Fin de course avec pull-up : repos=LOW (fermé), actionné=HIGH (ouvert)
  bool reading = digitalRead(PIN_BUTTON);

  if (reading != lastButtonState) {
    lastDebounce = millis();
  }

  if (millis() - lastDebounce > DEBOUNCE_MS) {
    if (reading != buttonState) {
      buttonState = reading;
      bool pressed = !(buttonState == HIGH);  // HIGH = fin de course ouvert = appui

      if (!wsConnected) {
        Serial.println("[BTN] Non connecté, changement ignoré");
      } else if (!enabled && pressed) {
        Serial.println("[BTN] Désactivé, appui ignoré");
      } else if (alreadyBuzzed && pressed) {
        Serial.println("[BTN] Déjà buzzé ce round");
      } else {
        // On envoie TOUJOURS le changement d'état (appui ET relâchement)
        sendBuzz(pressed);
      }
    }
  }

  lastButtonState = reading;

  // Clignotement LED si déconnecté
  // static unsigned long lastBlink = 0;
  // if (!wsConnected && millis() - lastBlink > 500) {
  //   lastBlink = millis();
  //   digitalWrite(PIN_LED, !digitalRead(PIN_LED));
  // }
}
