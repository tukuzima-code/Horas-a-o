import streamlit as st
import pandas as pd
from astral import LocationInfo
from astral.sun import sun
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from datetime import datetime, timedelta
import plotly.graph_objects as go
import ephem
from timezonefinder import TimezoneFinder
import pytz

# Configuración de la aplicación
st.set_page_config(page_title="Luz Solar Pro", layout="centered")

# --- FUNCIONES DE APOYO ---

@st.cache_data(show_spinner=False)
def obtener_ubicacion(cp):
    """Obtiene coordenadas con caché para no saturar la API"""
    try:
        # User-agent único para evitar bloqueos de Nominatim
        geolocator = Nominatim(user_agent="mi_app_solar_personal_2026_vfinal")
        return geolocator.geocode(cp, timeout=10)
    except (GeocoderTimedOut, GeocoderServiceError):
        return None

def get_moon_phase(date):
    """Calcula el emoji de la fase lunar"""
    m = ephem.Moon(date)
    phase = m.phase / 100
    if phase < 0.1: return "🌑"
    elif phase < 0.4: return "🌙"
    elif phase < 0.6: return "🌓"
    elif phase < 0.9: return "🌔"
    else: return "🌕"

def get_season_color(day_of_year):
    """Asigna color según la época
