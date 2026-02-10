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
    if d < 80 or d > 355: return 'rgb(100, 149, 237)' 
    elif d < 172: return 'rgb(144, 238, 144)' 
    elif d < 264: return 'rgb(255, 165, 0)'   
    else: return 'rgb(210, 105, 30)'

st.title("☀️ Agenda Solar")

if 'sel_idx' not in st.session_state:
    st.session_state.sel_idx = None

col_gps, col_txt = st.columns([1, 2])
with col_gps:
    st.write("")
    if st.button("📍 GPS"):
        loc = get_geolocation()
        if loc:
            st.session_state.lat, st.session_state.lon = loc['coords']['latitude'], loc['coords']['longitude']
            st.session_state.modo = "gps"

with col_txt:
    entrada = st.text_input("Ciudad o CP", placeholder="Puerto de Sagunto")
    if entrada:
        st.session_state.modo = "texto"
        st.session_state.busqueda = entrada

# --- UBICACIÓN ---
lat, lon, direccion = 39.664, -0.228, "Puerto de Sagunto"
if st.session_state.get('modo') == "gps":
    lat, lon = st.session_state.lat, st.session_state.lon
    direccion = "Ubicación GPS"
elif st.session_state.get('modo') == "texto":
    res = buscar_lugar_robusto(st.session_state.busqueda)
    if res:
        lat, lon = res.latitude, res.longitude
        direccion = res.address.split(',')[0]

tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=lon, lat=lat) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("P", "R", tz_name, lat, lon)
ahora = datetime.now(local_tz)

st.success(f"📍 {direccion}")
vista = st.radio("Ver por:", ["Días", "Semanas", "Meses"], horizontal=True)

# --- GENERAR DATOS ---
data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
max_x = 366 if ahora.year % 4 == 0 else 365
pasos = {"Días": 1, "Semanas": 7, "Meses": 30}

for i in range(0, max_x, pasos[vista]):
