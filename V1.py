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
import math
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

def get_moon_phase_data(date):
    m = ephem.Moon(date)
    p = m.phase 
    if p < 5: icon = "🌑"
    elif p < 45: icon = "🌙"
    elif p < 55: icon = "🌓"
    elif p < 95: icon = "🌔"
    else: icon = "🌕"
    return f"{icon} {int(p)}%"

def estimate_temp(day_of_year, lat, is_max=True):
    """Estima temperatura media basada en latitud y día del año (Modelo sinusoidal)"""
    # Ajuste según hemisferio
    shift = 200 if lat > 0 else 20 
    # Amplitud térmica según cercanía al ecuador
    amplitude = 15 if abs(lat) > 30 else 5
    base_temp = 25 - abs(lat)*0.3 if is_max else 15 - abs(lat)*0.3
    
    temp = base_temp + amplitude * math.cos(2 * math.pi * (day_of_year - shift) / 365)
    return round(temp, 1)

def get_season_color(d):
    if d < 80 or d > 355: return 'rgb(100, 149, 237)' 
    elif d < 172: return 'rgb(144, 238, 144)' 
    elif d < 264: return 'rgb(255, 165, 0)'   
    else: return 'rgb(210, 105, 30)'

# --- INICIALIZACIÓN DE SESIÓN ---
if 'lat' not in st.session_state:
    st.session_state['lat'], st.session_state['lon'] = 39.664, -0.228
    st.session_state['dir'] = "Puerto de Sagunto"

st.title("☀️ Agenda Solar")

# --- BUSCADOR Y GPS ---
col_gps, col_txt = st.columns([1, 3])
with col_gps:
    if st.button("📍 GPS"):
        loc = get_geolocation()
        if loc:
            st.session_state['lat'], st.session_state['lon'] = loc['coords']['latitude'], loc['coords']['longitude']
            st.session_state['dir'] = "Ubicación GPS"
            st.rerun()

with col_txt:
    entrada = st.text_input("Ciudad o CP", placeholder="Ej: Sagunto", label_visibility="collapsed")
    if entrada:
        res = buscar_lugar_robusto(entrada)
        if res:
            st.session_state['lat'], st.session_state['lon'] = res.latitude, res.longitude
            st.session_state['dir'] = res.address.split(',')[0]
            st.rerun()

# --- CÁLCULOS ---
tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=st.session_state['lon'], lat=st.session_state['lat']) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("P", "R", tz_name, st.session_state['lat'], st.session_state['lon'])
ahora = datetime.now(local_tz)
day_of_year = ahora.timetuple().tm_yday

st.success(f"📍 {st.session_state['dir']}")

# --- MÉTRICAS (LOS CUADRITOS) ---
s1 = sun(city.observer, date=ahora, tzinfo=local_tz)
t_max_hoy = estimate_temp(day_of_year, st.session_state['lat'], True)
t_min_hoy = estimate_temp(day_of_year, st.session_state['lat'], False)

st.markdown("---")
m1, m2, m3 = st.columns(3)
m1.metric("🌅 Amanecer", s1['sunrise'].strftime('%H:%M'))
m2.metric("🌇 Atardecer", s1['sunset'].strftime('%H:%M'))
m3.metric("🌓 Luna", get_moon_phase_data(ahora))

# Nuevas métricas de temperatura
c_temp1, c_temp2 = st.columns(2)
c_temp1.metric("🌡️ Media Máx (est.)", f"{t_max_hoy}°C")
c_temp2.metric("❄️ Media Mín (est.)", f"{t_min_hoy}°C")
st.markdown("---")

# --- GRÁFICO ANUAL ---
vista = st.radio("Escala:", ["Días", "Semanas", "Meses"], horizontal=True)

data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
max_x = 366 if ahora.year % 4 == 0 else 365
pasos = {"Días": 1, "Semanas": 7, "Meses": 30}

for i in range(0, max_x, pasos[vista]):
    dia_m = inicio_año + timedelta(days=i)
    try:
        s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
        am, at = s_dia['sunrise'].hour + s_dia['sunrise'].minute/60, s_dia['sunset'].hour + s_dia['sunset'].minute/60
        t_max = estimate_temp(i, st.session_state['lat'], True)
        t_min = estimate_temp(i, st.session_state['lat'], False)
        
        x_val = i+1 if vista == "Días" else (dia_m.isocalendar()[1] if vista == "Semanas" else dia_m.month)
        data.append({
            "X": x_val, "Am": am, "Dur": at - am, 
            "T_A": s_dia['sunrise'].strftime('%H:%M'), "T_At": s_dia['sunset'].strftime('%H:%M'), 
            "L": dia_m.strftime("%d %b"), "Luna": get_moon_phase_data(dia_m),
            "Max": t_max, "Min": t_min, "Color": get_season_color(i)
        })
    except: continue

df = pd.DataFrame(data)
fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["X"], y=df["Dur"], base=df["Am"], 
    marker_color=df["Color"],
    customdata=df[["T_A", "T_At", "L", "Luna", "Max", "Min"]],
    hovertemplate="""
    <b>%{customdata[2]}</b><br>
    🌅 Salida: %{customdata[0]} | 🌇 Puesta: %{customdata[1]}<br>
    🌙 Luna: %{customdata[3]}<br>
    🌡️ T. Media: %{customdata[5]}° / %{customdata[4]}°C
    <extra></extra>
    """
))

fig.add_vline(x=ahora.timetuple().tm_yday if vista == "Días" else (ahora.isocalendar()[1] if vista == "Semanas" else ahora.month), line_width=2, line_color="red")

fig.update_layout(
    template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
    yaxis=dict(range=[0, 24], dtick=4),
    xaxis=dict(fixedrange=True, rangeslider=dict(visible=True, thickness=0.06))
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
