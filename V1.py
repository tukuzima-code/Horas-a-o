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

# Instalación necesaria: pip install streamlit-plotly-events
from streamlit_plotly_events import plotly_events

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

# Inicializar día seleccionado en el estado de la sesión si no existe
if 'sel_date' not in st.session_state:
    st.session_state.sel_date = datetime.now()

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
lat, lon = 39.664, -0.228
direccion = "Puerto de Sagunto"
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

# --- GENERAR DATOS PARA EL GRÁFICO ---
data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
max_x = 366 if ahora.year % 4 == 0 else 365
pasos = {"Días": 1, "Semanas": 7, "Meses": 30}

for i in range(0, max_x, pasos[vista]):
    dia_m = inicio_año + timedelta(days=i)
    try:
        s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
        am, at = s_dia['sunrise'].hour + s_dia['sunrise'].minute/60, s_dia['sunset'].hour + s_dia['sunset'].minute/60
        x_val = i+1 if vista == "Días" else (dia_m.isocalendar()[1] if vista == "Semanas" else dia_m.month)
        data.append({
            "X": x_val, "Am": am, "Dur": at - am, 
            "T_A": s_dia['sunrise'].strftime('%H:%M'), "T_At": s_dia['sunset'].strftime('%H:%M'), 
            "L": dia_m.strftime("%d %b"), "Color": get_season_color(i), "Fecha": dia_m
        })
    except: continue

df = pd.DataFrame(data)

# --- CONSTRUIR EL GRÁFICO ---
fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["X"], y=df["Dur"], base=df["Am"], 
    marker_color=df["Color"],
    customdata=df["L"],
    hovertemplate="<b>%{customdata}</b><extra></extra>"
))

# Líneas de referencia
hoy_x = ahora.timetuple().tm_yday if vista == "Días" else (ahora.isocalendar()[1] if vista == "Semanas" else ahora.month)
fig.add_vline(x=hoy_x, line_width=2, line_color="red")

# Línea de Selección dinámica
sel_dt = st.session_state.sel_date.replace(tzinfo=local_tz)
sel_x = sel_dt.timetuple().tm_yday if vista == "Días" else (sel_dt.isocalendar()[1] if vista == "Semanas" else sel_dt.month)
fig.add_vline(x=sel_x, line_width=3, line_dash="dash", line_color="cyan")

fig.update_layout(
    template="plotly_dark", height=450, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
    yaxis=dict(range=[0, 24], fixedrange=True, dtick=2),
    xaxis=dict(range=[1, max_x if vista=="Días" else (53 if vista=="Semanas" else 12)], fixedrange=True, rangeslider=dict(visible=True, thickness=0.08))
)

# --- CAPTURAR EL TOQUE ---
# Esta función devuelve la lista de puntos clicados
selected_point = plotly_events(fig, click_event=True, hover_event=False, override_height=450)

if selected_point:
    # Actualizamos la fecha seleccionada según el punto tocado
    idx = selected_point[0]['pointNumber']
    st.session_state.sel_date = df.iloc[idx]['Fecha']
    st.rerun()

# --- PANEL DE DETALLES ---
with st.expander(f"📊 Detalles: {st.session_state.sel_date.strftime('%d de %B')}", expanded=True):
    f_calc = st.session_state.sel_date.replace(tzinfo=local_tz)
    s_h = sun(city.observer, date=f_calc, tzinfo=local_tz)
    s_m = sun(city.observer, date=f_calc + timedelta(days=1), tzinfo=local_tz)
    d1, d2 = (s_h['sunset']-s_h['sunrise']).total_seconds(), (s_m['sunset']-s_m['sunrise']).total_seconds()
    diff = d2 - d1
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Tendencia", "📈 Ganando" if diff > 0 else "📉 Perdiendo")
    c2.metric("Cambio", f"{int(abs(diff)//60)}m {int(abs(diff)%60)}s")
    c3.metric("Luna", get_moon_phase(f_calc))
    st.info(f"🌅 Amanecer: {s_h['sunrise'].strftime('%H:%M')} | 🌇 Atardecer: {s_h['sunset'].strftime('%H:%M')}")

st.caption("👆 Toca cualquier barra para ver sus detalles y marcarla.")
    
