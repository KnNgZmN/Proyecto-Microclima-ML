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
from typing import NamedTuple, Optional

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
# Interpretación de la línea serial
#
# Esta lógica vivía dentro del bucle de leer_serial(), detrás de la
# apertura del puerto físico, por lo que era imposible de probar. Al
# extraerla queda como función pura: entra texto, sale una lectura.
# -------------------------------------------------------
class ColectorError(RuntimeError):
    """Error irrecuperable del colector.

    Reemplaza a los sys.exit() que antes estaban dentro de las funciones:
    una función de librería no debe matar el proceso que la llama. El
    punto de entrada la captura y traduce a código de salida.
    """


class LineaIncompleta(ValueError):
    """La línea trae menos de dos valores.

    Se distingue del resto de descartes porque es la única condición que
    alimenta el contador de errores consecutivos: indica que el sketch
    del Arduino está enviando en un formato que no reconocemos.
    """


class Lectura(NamedTuple):
    """Lectura ya interpretada, lista para validar y persistir.

    `nota` describe cualquier suposición que hubo que hacer (valores por
    defecto, temperatura estimada por altitud). El llamador la imprime;
    así la función se mantiene pura y las pruebas pueden verificar qué
    supuesto se aplicó, no solo el resultado.
    """
    temperatura: float
    humedad: float
    luz: float
    ruido: float
    nota: str = ""


def parsear_lectura(linea: str, loc_info: dict) -> Optional[Lectura]:
    """
    Interpreta una línea CSV enviada por el Arduino.

    El sketch puede enviar 4, 3 o 2 valores según los sensores conectados:
      4 → temp,hum,luz,ruido      (montaje completo)
      3 → temp,hum,luz            (sin micrófono)
      2 → se desambigua por rango (solo DHT, o solo LDR + micrófono)

    Retorna
    -------
    Lectura : si la línea pudo interpretarse.
    None    : si debe ignorarse en silencio — línea vacía, comentario del
              sketch ('#'), valores no numéricos, o par de valores que no
              cae en ningún rango conocido.

    Lanza
    -----
    LineaIncompleta : si la línea trae menos de dos valores.
    """
    linea = linea.strip()
    if not linea or linea.startswith("#"):
        return None

    partes = linea.split(",")
    n = len(partes)
    if n < 2:
        raise LineaIncompleta(linea)

    try:
        vals = [float(p) for p in partes[:4]]
    except ValueError:
        return None

    if n >= 4:
        return Lectura(vals[0], vals[1], vals[2], vals[3])

    if n == 3:
        return Lectura(
            vals[0], vals[1], vals[2], 45.0,
            "3 valores recibidos (temp,hum,luz). Ruido default=45",
        )

    # Dos valores: hay que deducir qué sensores los enviaron.
    v0, v1 = vals[0], vals[1]
    temp_ok = -2.0 <= v0 <= 30.0   and 30.0 <= v1 <= 100.0
    luz_ok  =  0.0 <= v0 <= 1100.0 and 19.0 <= v1 <= 110.0

    # NOTA: los dos rangos se solapan (p. ej. "25,50" cumple ambos). El
    # orden de estas dos ramas es, por tanto, parte del contrato: ante la
    # ambigüedad se prefiere interpretar temp,hum. Las pruebas lo fijan.
    if temp_ok:
        return Lectura(
            v0, v1, 600.0, 45.0,
            f"2 valores -> temp={v0}C, hum={v1}%. Luz default=600, ruido default=45",
        )

    if luz_ok:
        # Sin DHT: se estima la temperatura por altitud con la tasa de
        # caída ambiental, la misma constante que usa el modelo.
        from localidades import ALT_REFERENCIA, LAPSE_RATE
        temp = round(14.0 + (ALT_REFERENCIA - loc_info["altitud"]) * LAPSE_RATE, 1)
        return Lectura(
            temp, 72.0, v0, v1,
            f"2 valores -> luz={v0:.0f}, ruido={v1:.0f}. "
            f"Sin DHT: temp estimada por altitud={temp}C, hum default=72%",
        )

    return None


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
def abrir_puerto(port: str, baud: int):
    """Abre el puerto serie real. Aislada para poder sustituirla en pruebas."""
    try:
        import serial
    except ImportError:
        raise ColectorError("Instala pyserial:  pip install pyserial")

    try:
        return serial.Serial(port, baud, timeout=2)
    except serial.SerialException as e:
        raise ColectorError(f"No se pudo abrir el puerto: {e}")


def leer_serial(port: str, baud: int, intervalo: int, con_prediccion: bool,
                loc_id: int, loc_info: dict,
                conexion=None, max_lecturas: int = None) -> int:
    """
    Lee lecturas del Arduino por puerto serie y las persiste.

    Parámetros
    ----------
    conexion     : objeto tipo Serial ya abierto. Si es None se abre uno
                   real sobre `port`. Permite inyectar un doble en pruebas
                   y ejecutar el bucle sin hardware.
    max_lecturas : detiene el bucle tras N lecturas válidas guardadas.
                   None (defecto) = indefinido, hasta Ctrl+C.

    Retorna
    -------
    int : cantidad de lecturas válidas guardadas.
    """
    ser = conexion
    if ser is None:
        print(f"[INFO] Conectando a {port} @ {baud} baud...")
        print(f"[INFO] Localidad: {loc_info['nombre']} (ID={loc_id}, {loc_info['altitud']} m)")
        ser = abrir_puerto(port, baud)

    print(f"[OK] Conectado. Guardando en: {DATA_PATH}")
    print("     Ctrl+C para detener.\n")

    historia = pd.DataFrame(columns=["temperatura", "humedad"])
    errores_consecutivos = 0
    guardadas = 0

    try:
        while max_lecturas is None or guardadas < max_lecturas:
            linea = ser.readline().decode("utf-8", errors="ignore").strip()

            try:
                lectura = parsear_lectura(linea, loc_info)
            except LineaIncompleta:
                print(f"  [SKIP] Linea invalida (menos de 2 valores): '{linea}'")
                errores_consecutivos += 1
                if errores_consecutivos >= 10:
                    print("[ERROR] Demasiados errores consecutivos. Verifica el sketch.")
                    print("[INFO]  Formato esperado: temp,hum,luz,ruido  (ej: 18.50,72.30,850,45)")
                    break
                continue

            # Una línea vacía o comentario no reinicia el contador: no es
            # señal de que el sketch esté enviando bien.
            if linea and not linea.startswith("#"):
                errores_consecutivos = 0

            if lectura is None:
                if linea and not linea.startswith("#"):
                    print(f"  [SKIP] No se pudo interpretar: '{linea}'")
                continue

            if lectura.nota:
                print(f"  [INFO] {lectura.nota}")

            temp, hum, luz, ruido = (
                lectura.temperatura, lectura.humedad, lectura.luz, lectura.ruido
            )

            if not validar_lectura(temp, hum, luz, ruido):
                continue

            ts   = datetime.now()
            hora = ts.hour
            mes  = ts.month

            guardar_fila(ts, temp, hum, luz, ruido, loc_id, loc_info)
            guardadas += 1

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

    return guardadas


# -------------------------------------------------------
# Modo simulación (sin hardware)
# -------------------------------------------------------
def sintetizar_lectura(hora: int, densidad: float, alt_corr: float,
                       rng=random) -> Lectura:
    """
    Genera una lectura sintética con la física del clima bogotano.

    Aplica el ciclo diurno, la corrección altitudinal y la isla de calor
    urbana (más marcada de noche, cuando el asfalto libera el calor
    acumulado). Es pura salvo por `rng`, que se inyecta para poder
    sembrarlo y obtener resultados reproducibles en las pruebas.
    """
    hora_rad = (hora / 24) * 2 * math.pi
    uhi = (densidad - 0.5) * (1.0 if 6 <= hora <= 18 else 2.5)

    temp = round(13.0 + 6.0 * math.sin(hora_rad - math.pi / 2) + alt_corr + uhi + rng.gauss(0, 0.8), 2)
    hum  = round(72.0 - 8.0 * math.sin(hora_rad - math.pi / 2) + rng.gauss(0, 4.0), 1)
    hum  = max(40.0, min(100.0, hum))
    luz  = int(rng.randint(500, 1000) if 6 <= hora <= 18 else rng.randint(0, 50))

    ruido_base = int(40 + densidad * 20)
    ruido = int(
        rng.randint(ruido_base + 10, ruido_base + 31)
        if (7 <= hora <= 9 or 17 <= hora <= 19)
        else rng.randint(ruido_base - 10, ruido_base + 11)
    )
    ruido = max(30, min(100, ruido))

    return Lectura(temp, hum, luz, ruido)


def simular(intervalo: int, con_prediccion: bool, n_lecturas: int,
            loc_id: int, loc_info: dict, rng=random) -> int:
    """Genera y persiste `n_lecturas` sintéticas, sin hardware."""
    from localidades import ALT_REFERENCIA, LAPSE_RATE

    alt_corr = (ALT_REFERENCIA - loc_info["altitud"]) * LAPSE_RATE
    densidad = loc_info["densidad_urbana"]

    print(f"[SIM] Modo simulacion - {n_lecturas} lecturas cada {intervalo}s")
    print(f"[SIM] Localidad: {loc_info['nombre']} (alt={loc_info['altitud']}m, densidad={densidad:.0%})")
    print(f"      Guardando en: {DATA_PATH}\n")

    historia = pd.DataFrame(columns=["temperatura", "humedad"])
    generadas = 0

    for _ in range(n_lecturas):
        ts   = datetime.now()
        hora = ts.hour
        mes  = ts.month

        lectura = sintetizar_lectura(hora, densidad, alt_corr, rng)
        temp, hum, luz, ruido = (
            lectura.temperatura, lectura.humedad, lectura.luz, lectura.ruido
        )

        guardar_fila(ts, temp, hum, luz, ruido, loc_id, loc_info)
        generadas += 1

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
    return generadas


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

    # ColectorError sustituye a los sys.exit() que antes vivían dentro de
    # las funciones: la traducción a código de salida ocurre solo aquí.
    try:
        if args.simulate:
            simular(args.intervalo, args.predict, args.lecturas, loc_id, loc_info)
        else:
            leer_serial(args.port, args.baud, args.intervalo, args.predict, loc_id, loc_info)
    except ColectorError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
