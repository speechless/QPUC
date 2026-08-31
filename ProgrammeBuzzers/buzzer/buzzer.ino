#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>

// --- Configuration à adapter ---
const char* WIFI_SSID     = "TCHOUPICOMPUTER 0635";
const char* WIFI_PASSWORD = "X1[7973v";

const char* bid = "X0004X";
const char* name = "Buzzer 4";


const char* WS_HOST = "192.168.137.1";  // IP du PC qui fait tourner main.py
const uint16_t WS_PORT = 8765;
const char* WS_PATH = "/esp";

WebSocketsClient webSocket;
String clientSessionId;

void sendHello() {
  StaticJsonDocument<128> doc;
  doc["event"] = "hello";
  doc["client_session_id"] = clientSessionId;
  doc["name"] = name;
  doc["bid"] = bid;

  String out;
  serializeJson(doc, out);
  webSocket.sendTXT(out);
  Serial.println("-> " + out);
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch (type) {
    case WStype_DISCONNECTED:
      Serial.println("[WS] Déconnecté");
      break;

    case WStype_CONNECTED:
      Serial.println("[WS] Connecté au serveur");
      sendHello();
      break;

    case WStype_TEXT:
      Serial.printf("[WS] Message reçu: %s\n", payload);
      // TODO: traiter les messages venant du serveur
      // (ex: activation/désactivation du buzzer, changement de phase, etc.)
      break;

    case WStype_ERROR:
      Serial.println("[WS] Erreur de connexion");
      break;

    default:
      break;
  }
}

void connectWifi() {
  Serial.print("Connexion au WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Connecté, IP locale: ");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  connectWifi();

  // Identifiant stable basé sur l'adresse MAC (persiste entre les reboots,
  // équivalent au esp_session_id attendu par server/wsEventManager.py)
  clientSessionId = "esp-" + WiFi.macAddress();
  clientSessionId.replace(":", "");
  
  webSocket.begin(WS_HOST, WS_PORT, WS_PATH);
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(3000);
}

void loop() {
  webSocket.loop();
}
