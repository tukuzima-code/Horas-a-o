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

# Configuración inicial
st.set_page_config(page_title="Luz Solar Pro", layout="centered")

# Funciones de apoyo
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

# --- ESTADO DE SESIÓN ---
if 'lat' not in st.session_state:
    st.session_state.lat = 39.664
if 'lon' not in st.session_state:
    st.session_state.lon = -0.228
if 'dir' not in st.session_state:
    st.session_state.dir = "Puerto de Sagunto (Por defecto)"

st.title("☀️ Agenda Solar")

# --- INTERFAZ DE UBICACIÓN ---
col_gps, col_txt = st.columns([1, 2])

with col_gps:
    st.write("")
    if st.button("📍 GPS"):
        loc = get_geolocation()
        if loc:
            st.session_state.lat = loc['coords']['latitude']
            st.session_state.lon = loc['coords']['longitude']
            st.session_state.dir = "Ubicación GPS"
            st.rerun()

with col_txt:
    entrada = st.text_input("Ciudad o CP", placeholder="Puerto de Sagunto")
    if entrada:
        res = buscar_lugar_robusto(entrada)
        if res:
            st.session_state.lat = res.latitude
            st.session_state.lon = res.longitude
            st.session_state.dir = res.address.split(',')[0]
            st.rerun()

# --- PROCESAMIENTO DE TIEMPO ---
tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=st.session_state.lon, lat=st.session_state.lat) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("P", "R", tz_name, st.session_state.lat, st.session_state.lon)
ahora = datetime.now(local_tz)

st.success(f"📍 {st.session_state.dir}")
vista = st.radio("Ver por:", ["Días", "Semanas", "Meses"], horizontal=True)

# --- GENERACIÓN DE DATOS ---
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
        x_val = i+1 if vista == "Días" else (dia_m.isocalendar()[1] if vista == "Semanas" else dia_m.month)
        data.append({
            "X": x_val, "Am": am, "Dur": at - am, 
            "T_A": s_dia['sunrise'].strftime('%H:%M'), 
            "T_At": s_dia['sunset'].strftime('%H:%M'), 
            "L": dia_m.strftime("%d %b"), "Color": get_season_color(i), "Fecha": dia_m
        })
    except:
        continue

df = pd.DataFrame(data)

# --- GRÁFICO INTERACTIVO ---
fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["X"], y=df["Dur"], base=df["Am"], 
    marker_color=df["Color"],
    customdata=df["L"],
    hovertemplate="<b>%{customdata}</b><extra></extra>"
))

hoy_x = ahora.timetuple().tm_yday if vista == "Días" else (ahora.isocalendar()[1] if vista == "Semanas" else ahora.month)
fig.add_vline(x=hoy_x, line_width=2, line_color="red")

fig.update_layout(
    template="plotly_dark", height=450, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
    yaxis=dict(range=[0, 24], fixedrange=True, dtick=2),
    xaxis=dict(range=[1, max_x if vista=="Días" else (53 if vista=="Semanas" else 12)], 
               fixedrange=True, rangeslider=dict(visible=True, thickness=0.08)),
    clickmode='event+select'
)

# Captura de selección táctil
event_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points")

# --- LÓGICA DE DETALLES ---
idx = 0
if event_data and len(event_data.get("selection", {}).get("points", [])) > 0:
    idx = event_data["selection"]["points"][0]["point_index"]
else:
    # Por defecto mostrar hoy
    cercano = df.iloc[(df['X']-hoy_x).abs().argsort()[:1]]
    idx = cercano.index[0]

f_sel = df.iloc[idx]
fecha_calc = f_sel['Fecha'].replace(tzinfo=local_tz)

with st.expander(f"📊 Detalles: {fecha_calc.strftime('%d de %B')}", expanded=True):
    s_h = sun(city.observer, date=fecha_calc, tzinfo=local_tz)
    s_m = sun(city.observer, date=fecha_calc + timedelta(days=1), tzinfo=local_tz)
    dur1, dur2 = (s_h['sunset']-s_h['sunrise']).total_seconds(), (s_m['sunset']-s_m['sunrise']).total_seconds()
    diff = dur2 - dur1
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Tendencia", "📈 Ganando" if diff > 0 else "📉 Perdiendo")
    c2.metric("Cambio", f"{int(abs(diff)//60)}m {int(abs(diff)%60)}s")
    c3.metric("Luna", get_moon_phase(fecha_calc))
    st.info(f"🌅 Amanecer: {s_h['sunrise'].strftime('%H:%M')} | 🌇 Atardecer: {s_h['sunset'].strftime('%H:%M')}")

st.caption("👆 Toca una barra para analizar ese día. Los ejes están bloqueados para estabilidad.")
