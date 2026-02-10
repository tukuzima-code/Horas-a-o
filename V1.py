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

if 'modo' not in st.session_state:
    st.session_state.modo = 'defecto'

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
if st.session_state.modo == "gps":
    lat, lon = st.session_state.lat, st.session_state.lon
    direccion = "Ubicación GPS"
elif st.session_state.modo == "texto":
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

# --- SELECTOR DE DÍA DE COMPARACIÓN ---
st.write("---")
dia_seleccionado = st.date_input("📅 Selecciona un día para marcar en el gráfico:", ahora)
st.write("---")

vista = st.radio("Ver por:", ["Días", "Semanas", "Meses"], horizontal=True)

# --- ESTADÍSTICAS DEL DÍA SELECCIONADO ---
with st.expander(f"📊 Detalles del {dia_seleccionado.strftime('%d %b')}"):
    try:
        # Usamos el día seleccionado por el usuario para el cálculo
        fecha_calc = datetime.combine(dia_seleccionado, datetime.min.time()).replace(tzinfo=local_tz)
        s1 = sun(city.observer, date=fecha_calc, tzinfo=local_tz)
        s2 = sun(city.observer, date=fecha_calc + timedelta(days=1), tzinfo=local_tz)
        dur1 = (s1['sunset'] - s1['sunrise']).total_seconds()
        dur2 = (s2['sunset'] - s2['sunrise']).total_seconds()
        
        delta_total_seg = abs(dur2 - dur1)
        minutos = int(delta_total_seg // 60)
        segundos = int(delta_total_seg % 60)
        tendencia = "📈 Ganando luz" if (dur2 > dur1) else "📉 Perdiendo luz"
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("**Tendencia:**")
            st.write(tendencia)
        with c2:
            st.write("**Cambio diario:**")
            st.write(f"{minutos}m {segundos}s")
        with c3:
            st.write("**Luna:**")
            st.write(get_moon_phase(fecha_calc))
            
        st.info(f"Salida: {s1['sunrise'].strftime('%H:%M')} | Puesta: {s1['sunset'].strftime('%H:%M')}")
    except:
        st.write("Selecciona una fecha válida dentro de los límites.")

# --- GRÁFICO ---
data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
pasos = {"Días": 1, "Semanas": 7, "Meses": 30}
max_x = 366 if ahora.year % 4 == 0 else 365

for i in range(0, max_x, pasos[vista]):
    dia_m = inicio_año + timedelta(days=i)
    try:
        s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
        am, at = s_dia['sunrise'].hour + s_dia['sunrise'].minute/60, s_dia['sunset'].hour + s_dia['sunset'].minute/60
        data.append({"X": (i+1 if vista == "Días" else (dia_m.isocalendar()[1] if vista == "Semanas" else dia_m.month)), 
                     "Am": am, "Dur": at - am, "T_A": s_dia['sunrise'].strftime('%H:%M'), "T_At": s_dia['sunset'].strftime('%H:%M'), 
                     "L": dia_m.strftime("%d %b"), "Color": get_season_color(i), "Luna": get_moon_phase(dia_m)})
    except: continue

df = pd.DataFrame(data)
fig = go.Figure()
fig.add_trace(go.Bar(x=df["X"], y=df["Dur"], base=df["Am"], marker_color=df["Color"], customdata=df[["T_A", "T_At", "Luna", "L"]],
                     hovertemplate="<b>%{customdata[3]}</b><br>☀️ %{customdata[0]} | 🌅 %{customdata[1]}<br>🌙 %{customdata[2]}<extra></extra>"))

# LÍNEA HOY (ROJA)
hoy_x = ahora.timetuple().tm_yday if vista == "Días" else (ahora.isocalendar()[1] if vista == "Semanas" else ahora.month)
fig.add_vline(x=hoy_x, line_width=2, line_color="red", annotation_text="Hoy", annotation_position="top left")

# LÍNEA SELECCIONADA (AZUL)
sel_x = dia_seleccionado.timetuple().tm_yday if vista == "Días" else (dia_seleccionado.isocalendar()[1] if vista == "Semanas" else dia_seleccionado.month)
if sel_x != hoy_x:
    fig.add_vline(x=sel_x, line_width=3, line_dash="dash", line_color="cyan", annotation_text="Selección", annotation_position="top right")

rango_max = max_x if vista == "Días" else (53 if vista == "Semanas" else 12)

fig.update_layout(
    template="plotly_dark", dragmode=False, height=500, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
    yaxis=dict(range=[0, 24], fixedrange=True, dtick=2),
    xaxis=dict(title=vista, range=[1, rango_max], fixedrange=True, rangeslider=dict(visible=True, thickness=0.08))
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
st.caption("🔴 Rojo: Hoy | 🔵 Azul Discontinuo: Día seleccionado")
