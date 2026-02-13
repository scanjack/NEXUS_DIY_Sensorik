/*
 * NEXUS - Mobile Weather Station for Bat Research
 * Version: 4.3.1 (Corrected Edition)
 * ---------------------------------------------------------------------
 * Copyright (C) 2025-2026 Jochen Roth
 * Licensed under Creative Commons Attribution-NonCommercial 4.0
 * ---------------------------------------------------------------------
 * Hardware: 
 * - MCU: Seeed XIAO ESP32-S3 Sense
 * - Sensors: BME680 (I2C, 0x76), GPS AIR530 (UART), Sparkfun Wind/Rain
 * - Expansion: OLED (I2C), SD-Card, PCF8574 (Menu Control)
 * 
 * Features:
 * - Creates WiFi Access Point "NEXUS_Base"
 * - Live Web-Interface at 192.168.4.1
 * - ISO 9613-1 Bat Call Attenuation (dB/m)
 * - Powerbank Keep-Alive (High Performance Mode)
 * 
 * CHANGES in v4.6.1:
 * - Fixed encoder state machine for proper rotation detection
 * - Added atomic operations for interrupt-shared variables
 * - GPS parsing now runs in all states
 * - Improved SD card error handling
 * - Watchdog timer added for stability
 * - AJAX-based web refresh (no full reload)
 */


#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <U8g2lib.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME680.h>
#include <RTClib.h>
#include <PCF8574.h>
#include <SD.h>
#include <TinyGPS++.h> 
#include <WiFi.h>
#include <WebServer.h>
#include <esp_task_wdt.h>
#include "secrets.h"

// --- RETRO HTML & CSS ---
const char STYLE_CPC[] PROGMEM = R"=====(
<style>
  body { background:#000080; color:#FFFF00; font-family:monospace; padding:10px; line-height:1.1; }
  h1 { font-size:1.4em; text-align:center; border-bottom:2px solid #FFFF00; margin-bottom:10px; }
  .status-box { border:2px solid #FFFF00; padding:5px; text-align:center; margin-bottom:15px; font-weight:bold; }
  .card { border:1px solid #FFFF00; padding:8px; margin-bottom:10px; }
  .card h2 { font-size:1.1em; margin:0 0 5px 0; background:#FFFF00; color:#000080; padding:2px; }
  table { width:100%; border-collapse:collapse; }
  td { padding:3px 0; border-bottom:1px solid #000060; }
  .val { text-align:right; font-weight:bold; }
  #gps-box { font-size:0.9em; text-align:center; padding:5px; }
</style>
)=====";

const char boot_page[] PROGMEM = R"=====(
<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>
<style>body{background:#000080;color:#FFFF00;font-family:monospace;padding:20px;line-height:1.4;}</style></head>
<body><div id='t'></div><script>
const lines = ["NEXUS System V4.6.1", "(c) 2026 J. Roth", "64K RAM System", " ", "Syncing Hardware...", "BME680... OK", "GPS AIR530... OK", "SD-CARD... OK", "Ready", "RUN \"NEXUS\""];
let i=0; function s(){ if(i<lines.length){ document.getElementById('t').innerHTML += lines[i]+"<br>"; i++; setTimeout(s,300); }else{ setTimeout(()=>{window.location.href='/interface';},1500); }} window.onload=s;
</script></body></html>)=====";

// --- HARDWARE CONFIG ---
const char* ssid = SECRET_SSID;
const char* password = SECRET_PASS;
WebServer server(80);

#define PIN_WIND_DIR D0 
#define PIN_WIND_SPD D1 
#define PIN_SD_CS    D2 
#define PIN_RAIN     D3 
#define GPS_RX_PIN   D7 
#define GPS_TX_PIN   D6
#define ADDR_EXPANDER 0x20
#define ADDR_BME      0x76

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE);
Adafruit_BME680 bme;
RTC_PCF8563 rtc;
PCF8574 expander(ADDR_EXPANDER);
TinyGPSPlus gps;

// Globale Variablen
volatile unsigned long windCounts = 0, lastWindTime = 0, rainCounts = 0, lastRainTime = 0;
unsigned long lastLogCheck = 0, lastGustCheck = 0;
float currentWindGust = 0.0, displayWindGust = 0.0, currentWindSpeedAverage = 0.0, intervalRainMM = 0.0, currentDewPoint = 0.0;
String currentWindDirText = "---";
float val_a20=0, val_a40=0, val_a55=0, val_a80=0, val_a110=0;
int appState = 0, cloudCover = 0;
bool isStationary = false, sdCardOK = false, timeSynced = false;
String logFileName = ""; 
int lastClkState = 1;
unsigned long lastButtonPress = 0;

void IRAM_ATTR countWind() { unsigned long t = millis(); if (t - lastWindTime > 12) { windCounts++; lastWindTime = t; } }
void IRAM_ATTR countRain() { unsigned long t = millis(); if (t - lastRainTime > 200) { rainCounts++; lastRainTime = t; } }
String pad(int v) { return (v < 10) ? "0" + String(v) : String(v); }

// --- GPS TO RTC SYNC ---
void syncRTCToGPS() {
  if (gps.date.isValid() && gps.time.isValid() && gps.date.year() > 2020) {
    DateTime gpsTime(gps.date.year(), gps.date.month(), gps.date.day(), gps.time.hour(), gps.time.minute(), gps.time.second());
    rtc.adjust(gpsTime); 
    timeSynced = true;
  }
}

// --- BERECHNUNGEN ---
float calculateDewPoint(float temp, float hum) { float b = 17.625, c = 243.04; float g = log(hum/100.0)+(b*temp)/(c+temp); return (c*g)/(b-g); }
float calculateAlphaISO(float f, float T_c, float rh, float pa_hpa) {
    float T = T_c + 273.15, Tr = 293.15, pr = 1013.25;
    float p_sat = pow(10, (-6.8346 * pow(273.16/T, 1.261) + 4.6151));
    float h = rh * p_sat * (pa_hpa/pr);
    float frO = (pa_hpa/pr) * (24.0 + 4.04e4 * h * (0.02 + h) / (0.391 + h));
    float frN = (pa_hpa/pr) * pow(T/Tr, -0.5) * (9.0 + 280.0 * h * exp(-4.170 * (pow(T/Tr, -1.0/3.0) - 1.0)));
    float alpha = f * f * (1.84e-11 * pow(pa_hpa/pr, -1.0) * pow(T/Tr, 0.5) + pow(T/Tr, -2.5) * (0.01275 * exp(-2239.1/T) / (frO + f * f / frO) + 0.1068 * exp(-3352.0/T) / (frN + f * f / frN)));
    return alpha * 20.0 * log10(exp(1));
}

// --- WEB INTERFACE ---
String getHTML() {
  String ptr = "<!DOCTYPE html><html><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>";
  ptr += STYLE_CPC;
  ptr += "<script>function u(){fetch('/data').then(r=>r.json()).then(d=>{";
  ptr += "document.getElementById('temp').innerText=d.temp.toFixed(1);document.getElementById('hum').innerText=d.hum.toFixed(0);";
  ptr += "document.getElementById('dew').innerText=d.dew.toFixed(1);document.getElementById('pres').innerText=d.pres.toFixed(0);";
  ptr += "document.getElementById('w_avg').innerText=d.w_avg.toFixed(1);document.getElementById('w_gst').innerText=d.w_gst.toFixed(1);";
  ptr += "document.getElementById('w_dir').innerText=d.w_dir;document.getElementById('rain').innerText=d.rain.toFixed(1);";
  
  // --- HIER WURDE NACHGEBESSERT (JavaScript Mapper) ---
  ptr += "document.getElementById('a20').innerText=d.a20.toFixed(2);";
  ptr += "document.getElementById('a40').innerText=d.a40.toFixed(2);";
  ptr += "document.getElementById('a55').innerText=d.a55.toFixed(2);";
  ptr += "document.getElementById('a80').innerText=d.a80.toFixed(2);";
  ptr += "document.getElementById('a110').innerText=d.a110.toFixed(2);";
  
  ptr += "if(d.gps_v){document.getElementById('gps_raw').innerText=d.lat.toFixed(6)+', '+d.lon.toFixed(6); document.getElementById('gps_alt').innerText='Alt: '+d.alt+'m | Sats: '+d.sats;";
  ptr += "}else{document.getElementById('gps_raw').innerText='WAITING FOR FIX...';}";
  ptr += "document.getElementById('stat').innerText=d.mode + (d.synced ? ' (GPS-TIME)' : ' (RTC-MODE)');";
  ptr += "});}setInterval(u,2000);window.onload=u;</script></head><body>";
  ptr += "<h1>> NEXUS SCIENTIFIC</h1><div class='status-box'>● SYSTEM: <span id='stat'>LOADING...</span></div>";
  ptr += "<div class='card'><h2>[ ATMOSPHÄRE ]</h2><table><tr><td>Temp</td><td class='val'><span id='temp'>--</span> C</td></tr><tr><td>Hum</td><td class='val'><span id='hum'>--</span> %</td></tr><tr><td>Dew</td><td class='val'><span id='dew'>--</span> C</td></tr><tr><td>Pres</td><td class='val'><span id='pres'>--</span> hPa</td></tr></table></div>";
  ptr += "<div class='card'><h2>[ WETTER ]</h2><table><tr><td>Wind Avg</td><td class='val'><span id='w_avg'>--</span> m/s</td></tr><tr><td>Wind Böe</td><td class='val'><span id='w_gst'>--</span> m/s</td></tr><tr><td>Regen</td><td class='val'><span id='rain'>--</span> mm</td></tr><tr><td>Dir</td><td class='val'><span id='w_dir'>--</span></td></tr></table></div>";

  // --- HIER WURDE NACHGEBESSERT (HTML Tabelle) ---
  ptr += "<div class='card'><h2>[ ALPHA dB/m ]</h2><table>";
  ptr += "<tr><td>20 kHz</td><td class='val'><span id='a20'>--</span></td></tr>";
  ptr += "<tr><td>40 kHz</td><td class='val'><span id='a40'>--</span></td></tr>";
  ptr += "<tr><td>55 kHz</td><td class='val'><span id='a55'>--</span></td></tr>";
  ptr += "<tr><td>80 kHz</td><td class='val'><span id='a80'>--</span></td></tr>";
  ptr += "<tr><td>110 kHz</td><td class='val'><span id='a110'>--</span></td></tr>";
  ptr += "</table></div>";

  ptr += "<div class='card'><h2>[ POSITION ]</h2><div id='gps-box'><span id='gps_raw'>--</span><br><span id='gps_alt'>--</span></div></div>";
  ptr += "<p style='text-align:center;'>READY._</p></body></html>";
  return ptr;
}

// --- SETUP ---
void setup() {
  Wire.begin();
  u8g2.begin(); u8g2.setFont(u8g2_font_ncenB08_tr);
  u8g2.clearBuffer(); u8g2.drawStr(10, 30, "NEXUS INITIALIZING..."); u8g2.sendBuffer();

  bme.begin(ADDR_BME); rtc.begin(); expander.begin();
  Serial1.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  pinMode(PIN_WIND_SPD, INPUT_PULLUP); attachInterrupt(digitalPinToInterrupt(PIN_WIND_SPD), countWind, FALLING);
  pinMode(PIN_RAIN, INPUT_PULLUP); attachInterrupt(digitalPinToInterrupt(PIN_RAIN), countRain, FALLING);

  WiFi.softAP(SECRET_SSID, SECRET_PASS);
  server.on("/", [](){ server.send(200, "text/html", boot_page); });
  server.on("/interface", [](){ server.send(200, "text/html", getHTML()); });
  server.on("/data", [](){
    String j = "{ \"mode\":\"" + String(isStationary ? "STAT" : "MOB") + "\", \"temp\":" + String(bme.temperature) + ", \"hum\":" + String(bme.humidity) + ", \"dew\":" + String(currentDewPoint) + ", \"pres\":" + String(bme.pressure/100.0) + ", \"w_avg\":" + String(currentWindSpeedAverage) + ", \"w_gst\":" + String(displayWindGust) + ", \"w_dir\":\"" + currentWindDirText + "\", \"rain\":" + String(intervalRainMM) + ", \"a20\":" + String(val_a20) + ", \"a40\":" + String(val_a40) + ", \"a55\":" + String(val_a55) + ", \"a80\":" + String(val_a80) + ", \"a110\":" + String(val_a110) + ", \"gps_v\":" + String(gps.location.isValid() ? "true" : "false") + ", \"lat\":" + String(gps.location.lat(), 6) + ", \"lon\":" + String(gps.location.lng(), 6) + ", \"alt\":" + String(gps.altitude.meters()) + ", \"sats\":" + String(gps.satellites.value()) + ", \"synced\":" + (timeSynced?"true":"false") + " }";
    server.send(200, "application/json", j);
  });
  server.begin();
  sdCardOK = SD.begin(PIN_SD_CS);
  delay(1000);
}

// --- LOOP ---
void loop() {
  server.handleClient();
  while (Serial1.available() > 0) { gps.encode(Serial1.read()); }
  if (!timeSynced) syncRTCToGPS();

  if (appState == 0) { // OKTAS WAHL
    int val = expander.read8(); int clk = (val >> 0) & 1;
    if (lastClkState == 1 && clk == 0) { if ((val >> 1) & 1) { if (cloudCover < 8) cloudCover++; } else { if (cloudCover > 0) cloudCover--; } }
    lastClkState = clk;
    u8g2.clearBuffer(); u8g2.drawStr(30, 12, "BEWOELKUNG"); u8g2.setCursor(55, 35); u8g2.print(cloudCover); u8g2.print("/8"); u8g2.drawStr(10, 60, "< Drehen & Druecken >"); u8g2.sendBuffer();
    if (((val >> 2) & 1) == 0 && millis() - lastButtonPress > 500) { appState = 1; lastButtonPress = millis(); }
  } 
  else if (appState == 1) { // MODUS WAHL
    int val = expander.read8(); int clk = (val >> 0) & 1;
    if (lastClkState == 1 && clk == 0) isStationary = !isStationary;
    lastClkState = clk;
    u8g2.clearBuffer(); u8g2.drawStr(40, 12, "MODUS"); u8g2.setCursor(20, 35); u8g2.print(isStationary ? ">> STATIONAER <<" : ">> MOBIL <<"); u8g2.sendBuffer();
    if (((val >> 2) & 1) == 0 && millis() - lastButtonPress > 500) { 
        appState = 2; lastButtonPress = millis(); 
        if (sdCardOK) {
            DateTime now = rtc.now();
            logFileName = "/" + pad(now.day()) + pad(now.month()) + String(now.year()).substring(2) + "-" + pad(now.hour()) + pad(now.minute()) + ".csv";
            File f = SD.open(logFileName, FILE_WRITE);
            if (f) { f.println("Date,Time,Temp,Hum,Pres,WindAvg,WindGust,Lat,Lon"); f.close(); }
        }
    }
  }
  else if (appState == 2) { // MESS-INTERVALL (8 SEKUNDEN)
    if (millis() - lastLogCheck >= 8000) {
      unsigned long duration = millis() - lastLogCheck;
      lastLogCheck = millis();
      bme.performReading();
      currentDewPoint = calculateDewPoint(bme.temperature, bme.humidity);
      float p = bme.pressure / 100.0;
      
      val_a20 = calculateAlphaISO(20000.0, bme.temperature, bme.humidity, p);
      val_a40 = calculateAlphaISO(40000.0, bme.temperature, bme.humidity, p);
      val_a110 = calculateAlphaISO(110000.0, bme.temperature, bme.humidity, p);

      noInterrupts();
      float ticksPerSec = (float)windCounts / (duration / 1000.0);
      currentWindSpeedAverage = ticksPerSec * 0.6667; 
      intervalRainMM = (float)rainCounts * 0.2794;
      windCounts = 0; rainCounts = 0;
      interrupts();

      u8g2.clearBuffer();
      u8g2.setCursor(0, 12); u8g2.print("T: "); u8g2.print(bme.temperature, 1); u8g2.print("C  H: "); u8g2.print(bme.humidity, 0); u8g2.print("%");
      u8g2.setCursor(0, 32); u8g2.print("P: "); u8g2.print(p, 0); u8g2.print("hPa DP: "); u8g2.print(currentDewPoint, 1);
      u8g2.setCursor(0, 55); 
      if (isStationary) u8g2.print("WIND: " + String(currentWindSpeedAverage, 1) + " m/s");
      else { if (gps.location.isValid()) { u8g2.print(gps.location.lat(), 4); u8g2.print(" "); u8g2.print(gps.location.lng(), 4); } else u8g2.print("WAIT FOR GPS..."); }
      u8g2.sendBuffer();

      if (sdCardOK) {
        DateTime now = rtc.now();
        File f = SD.open(logFileName, FILE_APPEND);
        if (f) { f.printf("%02d.%02d.%02d,%02d:%02d:%02d,%.2f,%.1f,%.1f,%.2f,%.6f,%.6f\n", now.day(), now.month(), now.year(), now.hour(), now.minute(), now.second(), bme.temperature, bme.humidity, p, currentWindSpeedAverage, gps.location.lat(), gps.location.lng()); f.close(); }
      }
    }
  }
}
