#define BATTERY_PIN 34

// Nombre de lectures pour moyenner (réduit le bruit de l'ADC)
#define NB_SAMPLES 10

// Différence entre valeur mesurées à l'ESP et au multimètre
#define CALIBRATION_FACTOR 1.036

float readBatteryVoltage() {
  long sum = 0;
  for (int i = 0; i < NB_SAMPLES; i++) {
    sum += analogRead(BATTERY_PIN);
    delay(5);
  }
  float raw = sum / (float)NB_SAMPLES;

  // Ratio du pont diviseur : R1=10k, R2=10k → division par 2
  float voltage = (raw / 4095.0) * 3.3 * 2.0 * CALIBRATION_FACTOR;
  return voltage;
}

int batteryPercent(float v) {
  if (v >= 4.2) return 100;
  if (v <= 3.0) return 0;
  if (v > 3.7) return 70 + (v - 3.7) / (4.2 - 3.7) * 30;
  return (v - 3.0) / (3.7 - 3.0) * 70;
}

String batteryStatus(float v) {
  if (v >= 4.1) return "Pleine";
  if (v >= 3.7) return "Bonne";
  if (v >= 3.4) return "Faible";
  if (v >= 3.0) return "Critique";
  return "Vide / Erreur";
}

void setup() {
  Serial.begin(115200);
  analogSetAttenuation(ADC_11db); // plage 0-3,3V sur l'ADC
  analogReadResolution(12);       // résolution max (0-4095)
}

void loop() {
  float v = readBatteryVoltage();
  int pct = batteryPercent(v);
  String status = batteryStatus(v);

  Serial.printf("Tension: %.2fV | Niveau: %d%% | Etat: %s\n",
                v, pct, status.c_str());

  // Alerte si batterie critique
  if (v < 3.2) {
    Serial.println("!! ATTENTION: pensez a recharger !!");
  }

  delay(2000);
}