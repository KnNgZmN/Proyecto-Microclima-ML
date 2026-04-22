# Catálogo de las 20 localidades de Bogotá D.C.
# Coordenadas: centroide aproximado de cada localidad
# Altitud: metros sobre el nivel del mar (media del polígono)
# densidad_urbana: escala 0-1 (0=rural, 1=urbano denso)
#
# Fuentes de referencia:
#   - IDECA (Infraestructura de Datos Espaciales de Bogotá)
#   - DANE - Censo 2018, densidad poblacional
#   - IDEAM - Estaciones meteorológicas, atlas climático
#   - SDP - Plan de Ordenamiento Territorial

LOCALIDADES: dict[int, dict] = {
    1:  {
        "nombre": "Usaquén",
        "lat": 4.7016, "lon": -74.0322,
        "altitud": 2600, "densidad_urbana": 0.70,
        "zona": "norte",
    },
    2:  {
        "nombre": "Chapinero",
        "lat": 4.6468, "lon": -74.0671,
        "altitud": 2610, "densidad_urbana": 0.82,
        "zona": "norte-centro",
    },
    3:  {
        "nombre": "Santa Fe",
        "lat": 4.5973, "lon": -74.0734,
        "altitud": 2620, "densidad_urbana": 0.75,
        "zona": "centro",
    },
    4:  {
        "nombre": "San Cristóbal",
        "lat": 4.5609, "lon": -74.0876,
        "altitud": 2720, "densidad_urbana": 0.65,
        "zona": "sur-oriente",
    },
    5:  {
        "nombre": "Usme",
        "lat": 4.4790, "lon": -74.1297,
        "altitud": 2790, "densidad_urbana": 0.45,
        "zona": "sur",
    },
    6:  {
        "nombre": "Tunjuelito",
        "lat": 4.5711, "lon": -74.1282,
        "altitud": 2600, "densidad_urbana": 0.72,
        "zona": "sur",
    },
    7:  {
        "nombre": "Bosa",
        "lat": 4.6206, "lon": -74.1909,
        "altitud": 2565, "densidad_urbana": 0.78,
        "zona": "sur-occidente",
    },
    8:  {
        "nombre": "Kennedy",
        "lat": 4.6278, "lon": -74.1647,
        "altitud": 2570, "densidad_urbana": 0.88,
        "zona": "occidente",
    },
    9:  {
        "nombre": "Fontibón",
        "lat": 4.6709, "lon": -74.1470,
        "altitud": 2558, "densidad_urbana": 0.76,
        "zona": "occidente",
    },
    10: {
        "nombre": "Engativá",
        "lat": 4.7040, "lon": -74.1119,
        "altitud": 2565, "densidad_urbana": 0.82,
        "zona": "occidente",
    },
    11: {
        "nombre": "Suba",
        "lat": 4.7405, "lon": -74.0893,
        "altitud": 2580, "densidad_urbana": 0.72,
        "zona": "norte-occidente",
    },
    12: {
        "nombre": "Barrios Unidos",
        "lat": 4.6648, "lon": -74.0822,
        "altitud": 2590, "densidad_urbana": 0.88,
        "zona": "centro-norte",
    },
    13: {
        "nombre": "Teusaquillo",
        "lat": 4.6321, "lon": -74.0871,
        "altitud": 2600, "densidad_urbana": 0.87,
        "zona": "centro",
    },
    14: {
        "nombre": "Los Mártires",
        "lat": 4.6072, "lon": -74.0889,
        "altitud": 2598, "densidad_urbana": 0.86,
        "zona": "centro",
    },
    15: {
        "nombre": "Antonio Nariño",
        "lat": 4.5848, "lon": -74.1002,
        "altitud": 2592, "densidad_urbana": 0.82,
        "zona": "sur-centro",
    },
    16: {
        "nombre": "Puente Aranda",
        "lat": 4.6144, "lon": -74.1117,
        "altitud": 2580, "densidad_urbana": 0.83,
        "zona": "occidente",
    },
    17: {
        "nombre": "La Candelaria",
        "lat": 4.5969, "lon": -74.0680,
        "altitud": 2625, "densidad_urbana": 0.70,
        "zona": "centro-histórico",
    },
    18: {
        "nombre": "Rafael Uribe Uribe",
        "lat": 4.5570, "lon": -74.1101,
        "altitud": 2617, "densidad_urbana": 0.72,
        "zona": "sur",
    },
    19: {
        "nombre": "Ciudad Bolívar",
        "lat": 4.4882, "lon": -74.1605,
        "altitud": 2750, "densidad_urbana": 0.52,
        "zona": "sur",
    },
    20: {
        "nombre": "Sumapaz",
        "lat": 4.3304, "lon": -74.3247,
        "altitud": 3150, "densidad_urbana": 0.05,
        "zona": "rural-páramo",
    },
}

# Altitud de referencia: centroide del casco urbano consolidado
ALT_REFERENCIA = 2625  # metros

# Tasa de caída ambiental estándar (ICAO/WMO)
LAPSE_RATE = 0.0065  # °C por metro de ascenso

NOMBRES_LOCALIDADES = {v["nombre"]: k for k, v in LOCALIDADES.items()}
