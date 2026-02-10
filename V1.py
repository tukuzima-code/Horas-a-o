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

# --- CONFIGURACIÓN DE PÁGINA ANCHA ---
st.set_page_config(
    page_title="Luz Solar Pro", 
    layout="wide",  # Esto hace que use todo el ancho en ordenador
    initial_sidebar_state="collapsed"
)

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

def get_season_color(d):
    if d < 80 or d > 355: return 'rgb(100, 149, 237)' 
    elif d < 172: return 'rgb(144, 238, 144)' 
    elif d < 264: return 'rgb(255, 165, 0)'   
    else: return 'rgb(210, 105, 30)'

# --- ESTADO DE SESIÓN ---
if 'lat' not in st.session_state:
    st.session_state['lat'], st.session_state['lon'] = 39.664, -0.228
    st.session_state['dir'] = "Puerto de Sagunto"

st.title("☀️ Agenda Solar Pro")

# --- BUSCADOR ---
col_gps, col_txt = st.columns([1, 4]) # Ajustado el ratio para pantalla ancha
with col_gps:
    if st.button("📍 Mi ubicación (GPS)", use_container_width=True):
        loc = get_geolocation()
        if loc:
            st.session_state['lat'] = loc['coords']['latitude']
            st.session_state['lon'] = loc['coords']['longitude']
            st.session_state['dir'] = "Ubicación GPS"
            st.rerun()

with col_txt:
    entrada = st.text_input("Buscar ciudad o código postal...", placeholder="Ej: Sagunto", label_visibility="collapsed")
    if entrada:
        res = buscar_lugar_robusto(entrada)
        if res:
            st.session_state['lat'] = res.latitude
            st.session_state['lon'] = res.longitude
            st.session_state['dir'] = res.address.split(',')[0]
            st.rerun()

# --- CÁLCULOS ---
tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=st.session_state['lon'], lat=st.session_state['lat']) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("P", "R", tz_name, st.session_state['lat'], st.session_state['lon'])
ahora = datetime.now(local_tz)

st.info(f"📍 Mostrando datos para: **{st.session_state['dir']}**")

# --- MÉTRICAS ---
s1 = sun(city.observer, date=ahora, tzinfo=local_tz)
s2 = sun(city.observer, date=ahora + timedelta(days=1), tzinfo=local_tz)
dur1 = (s1['sunset'] - s1['sunrise']).total_seconds()
dur2 = (s2['sunset'] - s2['sunrise']).total_seconds()
dif_seg = dur2 - dur1

# En ordenador se verán 4 columnas en una fila
m1, m2, m3, m4 = st.columns(4)
m1.metric("🌅 Amanecer", s1['sunrise'].strftime('%H:%M'))
m2.metric("🌇 Atardecer", s1['sunset'].strftime('%H:%M'))
m3.metric("🌓 Luna", get_moon_phase_data(ahora))

minutos, segundos = int(abs(dif_seg)//60), int(abs(dif_seg)%60)
trend = "aumentando" if dif_seg > 0 else "disminuyendo"
m4.metric("⏱️ Cambio luz", f"{minutos}m {segundos}s", delta=trend)

st.markdown("---")

# --- GRÁFICO ANUAL (AHORA MÁS ANCHO) ---
vista = st.radio("Escala del gráfico:", ["Días", "Semanas", "Meses"], horizontal=True)

data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
max_x = 366 if ahora.year % 4 == 0 else 365
pasos = {"Días": 1, "Semanas": 7, "Meses": 30}

for i in range(0, max_x, pasos[vista]):
    dia_m = inicio_año + timedelta(days=i)
    try:
        s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
        am = s_dia['sunrise'].hour + s_dia['sunrise'].minute/60
        at = s_dia['sunset'].hour + s_dia['sunset'].minute/60
        luna = get_moon_phase_data(dia_m)
        
        x_val = i+1 if vista == "Días" else (dia_m.isocalendar()[1] if vista == "Semanas" else dia_m.month)
        data.append({
            "X": x_val, "Am": am, "Dur": at - am, 
            "T_A": s_dia['sunrise'].strftime('%H:%M'), 
            "T_At": s_dia['sunset'].strftime('%H:%M'), 
            "L": dia_m.strftime("%d %b"), 
            "Luna": luna,
            "Color": get_season_color(i)
        })
    except: continue

df = pd.DataFrame(data)
fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["X"], y=df["Dur"], base=df["Am"], 
    marker_color=df["Color"],
    customdata=df[["T_A", "T_At", "L", "Luna"]],
    hovertemplate="<b>%{customdata[2]}</b><br>🌅 Salida: %{customdata[0]}<br>🌇 Puesta: %{customdata[1]}<br>🌙 Luna: %{customdata[3]}<extra></extra>"
))

hoy_x = ahora.timetuple().tm_yday if vista == "Días" else (ahora.isocalendar()[1] if vista == "Semanas" else ahora.month)
fig.add_vline(x=hoy_x, line_width=2, line_color="red")

fig.update_layout(
    template="plotly_dark", 
    height=500, # Un poco más alto para ordenador
    margin=dict(l=10, r=10, t=10, b=10), 
    showlegend=False,
    yaxis=dict(range=[0, 24], dtick=2, title="Horas del día (0-24h)"), # dtick 2 para más detalle en pantalla grande
    xaxis=dict(fixedrange=True, rangeslider=dict(visible=True, thickness=0.03))
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
