import streamlit as st
import pandas as pd
from astral import LocationInfo
from astral.sun import sun
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
import plotly.graph_objects as go
import ephem
from timezonefinder import TimezoneFinder
import pytz
import random
from streamlit_js_eval import get_geolocation

st.set_page_config(page_title="Luz Solar Pro", layout="centered")

# --- FUNCIONES ---
@st.cache_data(show_spinner=False, ttl=300)
def buscar_lugar_robusto(texto):
    if not texto: return None
    try:
        user_agent = f"solar_app_{random.randint(1000, 9999)}_search"
        geolocator = Nominatim(user_agent=user_agent)
        return geolocator.geocode(texto, timeout=10, language="es")
    except: return None

def get_moon_phase(date):
    m = ephem.Moon(date)
    p = m.phase / 100
    if p < 0.1: return "🌑"
    elif p < 0.4: return "🌙"
    elif p < 0.6: return "🌓"
    elif p < 0.9: return "🌔"
    else: return "🌕"

def get_season_color(d):
    # Definición de colores por día del año
    if d < 80 or d > 355: return 'rgb(100, 149, 237)' # Invierno
    elif d < 172: return 'rgb(144, 238, 144)'         # Primavera
    elif d < 264: return 'rgb(255, 165, 0)'           # Verano
    else: return 'rgb(210, 105, 30)'                  # Otoño

# --- INICIALIZACIÓN DE SESIÓN ---
if 'lat' not in st.session_state:
    st.session_state['lat'] = 39.664
if 'lon' not in st.session_state:
    st.session_state['lon'] = -0.228
if 'dir' not in st.session_state:
    st.session_state['dir'] = "Puerto de Sagunto"

st.title("☀️ Agenda Solar")

# --- BUSCADOR Y GPS ---
col_gps, col_txt = st.columns([1, 3])

with col_gps:
    if st.button("📍 GPS"):
        loc = get_geolocation()
        if loc:
            st.session_state['lat'] = loc['coords']['latitude']
            st.session_state['lon'] = loc['coords']['longitude']
            st.session_state['dir'] = "Ubicación
