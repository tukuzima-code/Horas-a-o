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
from streamlit_js_eval import get_geolocation

st.set_page_config(page_title="Luz Solar Pro", layout="centered")

# --- FUNCIONES DE APOYO ---
@st.cache_data(show_spinner=False, ttl=300)
def buscar_lugar_robusto(texto):
    if not texto: return None
    try:
        geolocator = Nominatim(user_agent="solar_app_v4")
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
    if d < 80 or d > 355: return 'rgb(100, 149, 237)' 
    elif d < 172: return 'rgb(144, 238, 144)' 
    elif d < 264: return 'rgb(255, 165, 0)'   
    else: return 'rgb(210, 105, 30)'

# --- ESTADO DE SESIÓN ---
if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon = 39.664, -0.228
    st.session_state.dir = "Puerto de Sagunto"

st
