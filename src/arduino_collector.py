"""
arduino_collector.py — Recolector de datos en tiempo real desde Arduino.

Formato esperado del sketch de Arduino (línea serial, cada 10 s o configurable):
    18.50,72.30,850,45
    ^temp  ^hum  ^lux ^dB

El sketch debe terminar cada línea con '\\n'.

Uso:
    # Con Arduino real (localidad 8 = Kennedy):
    python arduino_collector.py --port COM3 --baud 9600 --localidad 8

    # Modo simulación (sin hardware):
    python arduino_collector.py --simulate --localidad 13

    # Con predicción en vivo:
    python arduino_collector.py --port COM3 --predict --localidad 8
"""

import argparse
import json
import os
import sys
import time
import csv
import random
import math
from datetime import datetime

import pandas as pd
import numpy as np

# Añadir src al path para importar módulos del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# -------------------------------------------------------
# Configuración
# -------------------------------------------------------
base_dir  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(base_dir, "data", "raw", "data.csv")

RANGOS = {
    "temperatura": (-2.0, 30.0),
    "humedad":     (30.0, 100.0),
    "luz":         (0.0,  1100.0),
    "ruido":       (19.0, 110.0),
}

COLUMNAS = ["timestamp", "localidad_id", "localidad", "latitud", "longitud",
            "altitud", "densidad_urbana", "temperatura", "humedad", "luz", "ruido"]
HISTORIA_MAX = 20   # filas recientes mantenidas en memoria para promedios
LIVE_PATH = os.path.join(base_dir, "data", "live", "latest.json")


# -------------------------------------------------------
# Archivo compartido con Streamlit (última lectura en vivo)
# -------------------------------------------------------
def actualizar_live(ts: datetime, temp: float, hum: float, luz: float, ruido: float,
                    pred, loc_id: int, loc_info: dict):
    """Escribe la lectura más reciente en JSON para que Streamlit la muestre en vivo."""
    os.makedirs(os.path.dirname(LIVE_PATH), exist_ok=True)
    datos = {
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "localidad_id": loc_id,
        "localidad": loc_info["nombre"],
        "temperatura": round(temp, 2),
        "humedad": round(hum, 1),
        "luz": int(luz),
        "ruido": int(ruido),
        "prediccion": round(pred, 2) if pred is not None else None,
    }
    with open(LIVE_PATH, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2)


# -------------------------------------------------------
# Validación de lectura
# -------------------------------------------------------
def validar_lectura(temp, hum, luz, ruido) -> bool:
    valores = {"temperatura": temp, "humedad": hum, "luz": luz, "ruido": ruido}
    for col, val in valores.items():
        lo, hi = RANGOS[col]
        if not (lo <= val <= hi):
            print(f"  [WARN] Valor fuera de rango - {col}: {val} (esperado {lo}-{hi})")
            return False
    return True


# -------------------------------------------------------
# Guardar fila en CSV
# -------------------------------------------------------
def guardar_fila(ts: datetime, temp: float, hum: float, luz: float, ruido: float,
                 loc_id: int, loc_info: dict):
    existe = os.path.isfile(DATA_PATH)
    with open(DATA_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(COLUMNAS)
        writer.writerow([
            ts.strftime("%Y-%m-%d %H:%M:%S"),
            loc_id, loc_info["nombre"],
            loc_info["lat"], loc_info["lon"],
            loc_info["altitud"], loc_info["densidad_urbana"],
            temp, hum, luz, ruido,
        ])


# -------------------------------------------------------
# Predicción en vivo (carga lazy del modelo)
# -------------------------------------------------------
_modelo = None

def predecir_en_vivo(temp, hum, luz, ruido, hora, mes, historia, loc_info: dict):
    global _modelo
    if _modelo is None:
        import joblib
        model_path = os.path.join(base_dir, "models", "model.pkl")
        if not os.path.exists(model_path):
            print("  [WARN] Modelo no encontrado. Ejecuta train_model.py primero.")
            return None
        _modelo = joblib.load(model_path)

    from feature_engineering import features_from_raw
    X = features_from_raw(
        temp, hum, luz, ruido, hora, mes, historia,
        altitud         = loc_info["altitud"],
        latitud         = loc_info["lat"],
        longitud        = loc_info["lon"],
        densidad_urbana = loc_info["densidad_urbana"],
    )
    return float(_modelo.predict(X)[0])


# -------------------------------------------------------
# Lector serial (Arduino real)
# -------------------------------------------------------
def leer_serial(port: str, baud: int, intervalo: int, con_prediccion: bool,
                loc_id: int, loc_info: dict):
    try:
        import serial
    except ImportError:
        print("[ERROR] Instala pyserial:  pip install pyserial")
        sys.exit(1)

    print(f"[INFO] Conectando a {port} @ {baud} baud...")
    print(f"[INFO] Localidad: {loc_info['nombre']} (ID={loc_id}, {loc_info['altitud']} m)")
    try:
        ser = serial.Serial(port, baud, timeout=2)
    except serial.SerialException as e:
        print(f"[ERROR] No se pudo abrir el puerto: {e}")
        sys.exit(1)

    print(f"[OK] Conectado. Guardando en: {DATA_PATH}")
    print("     Ctrl+C para detener.\n")

    historia = pd.DataFrame(columns=["temperatura", "humedad"])
    errores_consecutivos = 0

    try:
        while True:
            linea = ser.readline().decode("utf-8", errors="ignore").strip()
            if not linea or linea.startswith("#"):
                continue

            partes = linea.split(",")
            n = len(partes)
            if n < 2:
                print(f"  [SKIP] Linea invalida (menos de 2 valores): '{linea}'")
                errores_consecutivos += 1
                if errores_consecutivos >= 10:
                    print("[ERROR] Demasiados errores consecutivos. Verifica el sketch.")
                    print(f"[INFO]  Formato esperado: temp,hum,luz,ruido  (ej: 18.50,72.30,850,45)")
                    break
                continue

            errores_consecutivos = 0

            try:
                vals = [float(p) for p in partes[:4]]
            except ValueError:
                print(f"  [SKIP] No se pudo parsear: '{linea}'")
                continue

            if n >= 4:
                temp, hum, luz, ruido = vals[0], vals[1], vals[2], vals[3]
            elif n == 3:
                # 3 valores: temp, hum, luz  — ruido por default
                temp, hum, luz, ruido = vals[0], vals[1], vals[2], 45.0
                print(f"  [INFO] 3 valores recibidos (temp,hum,luz). Ruido default=45")
            else:
                # 2 valores: detectar si son temp,hum o luz,ruido segun rangos
                v0, v1 = vals[0], vals[1]
                temp_ok = -2.0 <= v0 <= 30.0 and 30.0 <= v1 <= 100.0
                luz_ok  =  0.0 <= v0 <= 1100.0 and 19.0 <= v1 <= 110.0
                if temp_ok:
                    temp, hum, luz, ruido = v0, v1, 600.0, 45.0
                    print(f"  [INFO] 2 valores -> temp={temp}C, hum={hum}%. "
                          f"Luz default=600, ruido default=45")
                elif luz_ok:
                    # Solo sensores analogicos (LDR + microfono), sin DHT
                    from localidades import ALT_REFERENCIA, LAPSE_RATE
                    luz, ruido = v0, v1
                    temp = round(14.0 + (ALT_REFERENCIA - loc_info["altitud"]) * LAPSE_RATE, 1)
                    hum  = 72.0
                    print(f"  [INFO] 2 valores -> luz={luz:.0f}, ruido={ruido:.0f}. "
                          f"Sin DHT: temp estimada por altitud={temp}C, hum default=72%")
                else:
                    print(f"  [SKIP] Valores fuera de rango conocido: '{linea}'")
                    continue

            if not validar_lectura(temp, hum, luz, ruido):
                continue

            ts   = datetime.now()
            hora = ts.hour
            mes  = ts.month

            guardar_fila(ts, temp, hum, luz, ruido, loc_id, loc_info)

            nueva_fila = pd.DataFrame([{"temperatura": temp, "humedad": hum}])
            historia = pd.concat([historia, nueva_fila], ignore_index=True).tail(HISTORIA_MAX)

            estado = (
                f"[{ts.strftime('%H:%M:%S')}] "
                f"T={temp:.1f}C  H={hum:.1f}%  Luz={luz:.0f}lx  Ruido={ruido:.0f}dB"
            )

            pred = None
            if con_prediccion:
                pred = predecir_en_vivo(temp, hum, luz, ruido, hora, mes, historia, loc_info)
                if pred is not None:
                    estado += f"  -> T+30min={pred:.2f}C"

            actualizar_live(ts, temp, hum, luz, ruido, pred, loc_id, loc_info)
            print(estado)
            time.sleep(max(0, intervalo - 0.1))

    except KeyboardInterrupt:
        print("\n[STOP] Recoleccion detenida.")
    finally:
        ser.close()


# -------------------------------------------------------
# Modo simulación (sin hardware)
# -------------------------------------------------------
def simular(intervalo: int, con_prediccion: bool, n_lecturas: int,
            loc_id: int, loc_info: dict):
    from localidades import ALT_REFERENCIA, LAPSE_RATE

    alt_corr = (ALT_REFERENCIA - loc_info["altitud"]) * LAPSE_RATE
    densidad = loc_info["densidad_urbana"]

    print(f"[SIM] Modo simulacion - {n_lecturas} lecturas cada {intervalo}s")
    print(f"[SIM] Localidad: {loc_info['nombre']} (alt={loc_info['altitud']}m, densidad={densidad:.0%})")
    print(f"      Guardando en: {DATA_PATH}\n")

    historia = pd.DataFrame(columns=["temperatura", "humedad"])

    for _ in range(n_lecturas):
        ts   = datetime.now()
        hora = ts.hour
        mes  = ts.month

        hora_rad = (hora / 24) * 2 * math.pi
        uhi = (densidad - 0.5) * (1.0 if 6 <= hora <= 18 else 2.5)

        temp  = round(13.0 + 6.0 * math.sin(hora_rad - math.pi / 2) + alt_corr + uhi + random.gauss(0, 0.8), 2)
        hum   = round(72.0 - 8.0 * math.sin(hora_rad - math.pi / 2) + random.gauss(0, 4.0), 1)
        hum   = max(40.0, min(100.0, hum))
        luz   = int(random.randint(500, 1000) if 6 <= hora <= 18 else random.randint(0, 50))

        ruido_base = int(40 + densidad * 20)
        ruido = int(
            random.randint(ruido_base + 10, ruido_base + 31)
            if (7 <= hora <= 9 or 17 <= hora <= 19)
            else random.randint(ruido_base - 10, ruido_base + 11)
        )
        ruido = max(30, min(100, ruido))

        guardar_fila(ts, temp, hum, luz, ruido, loc_id, loc_info)

        nueva_fila = pd.DataFrame([{"temperatura": temp, "humedad": hum}])
        historia = pd.concat([historia, nueva_fila], ignore_index=True).tail(HISTORIA_MAX)

        estado = (
            f"[{ts.strftime('%H:%M:%S')}] "
            f"T={temp:.1f}C  H={hum:.1f}%  Luz={luz}lx  Ruido={ruido}dB"
        )

        pred = None
        if con_prediccion:
            pred = predecir_en_vivo(temp, hum, luz, ruido, hora, mes, historia, loc_info)
            if pred is not None:
                estado += f"  -> T+30min={pred:.2f}C"

        actualizar_live(ts, temp, hum, luz, ruido, pred, loc_id, loc_info)
        print(estado)
        time.sleep(intervalo)

    print("\n[OK] Simulacion terminada.")


# -------------------------------------------------------
# Sketch de Arduino de referencia (imprime al --sketch)
# -------------------------------------------------------
SKETCH_REFERENCIA = """
// -----------------------------------------------
// Sketch de referencia — Microclima Sensor
// Sensores: DHT22 (temp/hum), LDR (luz), KY-038 (ruido)
// Envía línea CSV cada 10 s por Serial: temp,hum,luz,ruido
// -----------------------------------------------
#include <DHT.h>

#define DHTPIN 2
#define DHTTYPE DHT22
#define PIN_LUZ A0
#define PIN_RUIDO A1

DHT dht(DHTPIN, DHTTYPE);

void setup() {
    Serial.begin(9600);
    dht.begin();
}

void loop() {
    float temp = dht.readTemperature();
    float hum  = dht.readHumidity();
    int   luz  = map(analogRead(PIN_LUZ),   0, 1023, 0, 1000);
    int   ruido= map(analogRead(PIN_RUIDO), 0, 1023, 20, 110);

    if (isnan(temp) || isnan(hum)) {
        Serial.println("# ERROR sensor DHT22");
        delay(2000);
        return;
    }

    Serial.print(temp, 2);
    Serial.print(",");
    Serial.print(hum, 1);
    Serial.print(",");
    Serial.print(luz);
    Serial.print(",");
    Serial.println(ruido);

    delay(10000);   // 10 segundos
}
"""


# -------------------------------------------------------
# Punto de entrada
# -------------------------------------------------------
if __name__ == "__main__":
    from localidades import LOCALIDADES

    parser = argparse.ArgumentParser(
        description="Recolector de datos de microclima desde Arduino"
    )
    parser.add_argument("--port",      default="COM3",  help="Puerto serial (ej. COM3, /dev/ttyUSB0)")
    parser.add_argument("--baud",      type=int, default=9600,  help="Baud rate del Arduino")
    parser.add_argument("--intervalo", type=int, default=10,    help="Segundos entre lecturas")
    parser.add_argument("--simulate",  action="store_true",     help="Modo simulación sin hardware")
    parser.add_argument("--lecturas",  type=int, default=100,   help="Cantidad de lecturas en simulación")
    parser.add_argument("--predict",   action="store_true",     help="Mostrar predicción T+30 min en vivo")
    parser.add_argument("--sketch",    action="store_true",     help="Imprimir sketch de Arduino de referencia")
    parser.add_argument("--localidad", type=int, default=13,
                        help="ID de localidad (1-20, defecto 13=Teusaquillo)")
    args = parser.parse_args()

    if args.sketch:
        print(SKETCH_REFERENCIA)
        sys.exit(0)

    loc_id   = args.localidad
    loc_info = LOCALIDADES.get(loc_id)
    if loc_info is None:
        print(f"[ERROR] Localidad {loc_id} no existe. Valores validos: 1-20.")
        sys.exit(1)

    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)

    if args.simulate:
        simular(args.intervalo, args.predict, args.lecturas, loc_id, loc_info)
    else:
        leer_serial(args.port, args.baud, args.intervalo, args.predict, loc_id, loc_info)
