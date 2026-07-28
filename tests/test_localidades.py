"""Pruebas de src/localidades.py — integridad del catálogo de las 20 localidades."""

import pytest

from localidades import (
    ALT_REFERENCIA,
    LAPSE_RATE,
    LOCALIDADES,
    NOMBRES_LOCALIDADES,
)

CLAVES_REQUERIDAS = {"nombre", "lat", "lon", "altitud", "densidad_urbana", "zona"}

# Caja envolvente de Bogotá D.C. incluyendo la localidad rural de Sumapaz
LAT_MIN, LAT_MAX = 4.20, 4.90
LON_MIN, LON_MAX = -74.50, -73.95


def test_hay_exactamente_veinte_localidades():
    assert len(LOCALIDADES) == 20


def test_los_ids_son_consecutivos_del_1_al_20():
    assert sorted(LOCALIDADES) == list(range(1, 21))


@pytest.mark.parametrize("loc_id", sorted(LOCALIDADES))
def test_cada_localidad_tiene_todas_las_claves(loc_id):
    assert CLAVES_REQUERIDAS <= set(LOCALIDADES[loc_id])


@pytest.mark.parametrize("loc_id", sorted(LOCALIDADES))
def test_coordenadas_dentro_de_bogota(loc_id):
    info = LOCALIDADES[loc_id]

    assert LAT_MIN <= info["lat"] <= LAT_MAX
    assert LON_MIN <= info["lon"] <= LON_MAX


@pytest.mark.parametrize("loc_id", sorted(LOCALIDADES))
def test_densidad_urbana_esta_normalizada(loc_id):
    """El campo se documenta como escala 0-1 y alimenta el modelo sin escalar."""
    assert 0.0 <= LOCALIDADES[loc_id]["densidad_urbana"] <= 1.0


@pytest.mark.parametrize("loc_id", sorted(LOCALIDADES))
def test_altitud_en_rango_plausible_para_la_sabana(loc_id):
    assert 2500 <= LOCALIDADES[loc_id]["altitud"] <= 3300


@pytest.mark.parametrize("loc_id", sorted(LOCALIDADES))
def test_nombre_y_zona_no_estan_vacios(loc_id):
    info = LOCALIDADES[loc_id]

    assert info["nombre"].strip()
    assert info["zona"].strip()


def test_los_nombres_no_se_repiten():
    nombres = [info["nombre"] for info in LOCALIDADES.values()]

    assert len(set(nombres)) == len(nombres)


def test_nombres_localidades_es_el_inverso_exacto_del_catalogo():
    assert len(NOMBRES_LOCALIDADES) == len(LOCALIDADES)

    for loc_id, info in LOCALIDADES.items():
        assert NOMBRES_LOCALIDADES[info["nombre"]] == loc_id


def test_sumapaz_es_la_localidad_mas_alta_y_menos_densa():
    """Sumapaz es el páramo rural; el modelo depende de este contraste."""
    mas_alta = max(LOCALIDADES, key=lambda k: LOCALIDADES[k]["altitud"])
    menos_densa = min(LOCALIDADES, key=lambda k: LOCALIDADES[k]["densidad_urbana"])

    assert LOCALIDADES[mas_alta]["nombre"] == "Sumapaz"
    assert LOCALIDADES[menos_densa]["nombre"] == "Sumapaz"


def test_teusaquillo_es_la_localidad_por_defecto_del_despliegue():
    """predict.predict() usa localidad_id=13 como valor por defecto."""
    assert LOCALIDADES[13]["nombre"] == "Teusaquillo"


def test_constantes_fisicas_del_modelo_altitudinal():
    assert ALT_REFERENCIA == 2625
    # Tasa de caída ambiental estándar ICAO/WMO: 6.5 °C por km
    assert LAPSE_RATE == pytest.approx(0.0065)
