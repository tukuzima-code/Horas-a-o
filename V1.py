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

# --- FUNCIONES ---
@st.cache_data(show_spinner=False, ttl=300)
def buscar_lugar_robusto(texto):
    if not texto: return None
    try:
        geolocator = Nominatim(user_agent="solar_app_v6")
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

# --- ESTADO Y UBICACIÓN ---
if 'lat' not in st.session_state:
    st.session_state.lat, st.session_state.lon = 39.664, -0.228
    st.session_state.dir = "Puerto de Sagunto"
if 'graph_key' not in st.session_state:
    st.session_state.graph_key = 0

st.title("☀️ Agenda Solar")

col_gps, col_txt = st.columns([1, 2])
with col_gps:
    if st.button("📍 GPS"):
        loc = get_geolocation()
        if loc:
            st.session_state.lat, st.session_state.lon = loc['coords']['latitude'], loc['coords']['longitude']
            st.session_state.dir = "Ubicación GPS"
            st.session_state.graph_key += 1
            st.rerun()

with col_txt:
    entrada = st.text_input("Buscar ciudad...", placeholder="Ej: Sagunto")
    if entrada:
        res = buscar_lugar_robusto(entrada)
        if res:
            st.session_state.lat, st.session_state.lon = res.latitude, res.longitude
            st.session_state.dir = res.address.split(',')[0]
            st.session_state.graph_key += 1
            st.rerun()

tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=st.session_state.lon, lat=st.session_state.lat) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("P", "R", tz_name, st.session_state.lat, st.session_state.lon)
ahora = datetime.now(local_tz)

st.success(f"📍 {st.session_state.dir}")
vista = st.radio("Escala:", ["Días", "Semanas", "Meses"], horizontal=True)

# --- PREPARACIÓN DE DATOS ---
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
        data.append({"X": x_val, "Am": am, "Dur": at - am, "Fecha": dia_m, "Color": get_season_color(i)})
    except: continue
df = pd.DataFrame(data)

# --- EL GRÁFICO (AHORA VA PRIMERO EN EL CÓDIGO) ---
fig = go.Figure()
fig.add_trace(go.Bar(x=df["X"], y=df["Dur"], base=df["Am"], marker_color=df["Color"]))
hoy_x = ahora.timetuple().tm_yday if vista == "Días" else (ahora.isocalendar()[1] if vista == "Semanas" else ahora.month)
fig.add_vline(x=hoy_x, line_width=2, line_color="red")
fig.update_layout(template="plotly_dark", height=350, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                  yaxis=dict(range=[0, 24], fixedrange=True, dtick=4),
                  xaxis=dict(range=[1, max_x if vista=="Días" else 12], fixedrange=True, rangeslider=dict(visible=True, thickness=0.08)),
                  clickmode='event+select')

# Capturamos el evento. Al usar on_select="rerun", el script vuelve a empezar sabiendo qué has tocado.
event_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun", selection_mode="points", key=f"g_{st.session_state.graph_key}")

# --- PANELES DE DATOS (SE DIBUJAN DESPUÉS DE CAPTURAR LA SELECCIÓN) ---
st.divider()

# 1. Panel de HOY (Siempre arriba)
s_hoy = sun(city.observer, date=ahora, tzinfo=local_tz)
s_man = sun(city.observer, date=ahora + timedelta(days=1), tzinfo=local_tz)
dif_seg = (s_man['sunset']-s_man['sunrise']).total_seconds() - (s_hoy['sunset']-s_hoy['sunrise']).total_seconds()

st.subheader("🗓️ Hoy")
c1, c2, c3 = st.columns(3)
c1.metric("Amanecer", s_hoy['sunrise'].strftime('%H:%M'))
c2.metric("Atardecer", s_hoy['sunset'].strftime('%H:%M'))
c3.metric("Cambio", f"{int(abs(dif_seg)//60)}m {int(abs(dif_seg)%60)}s", delta="Más luz" if dif_seg > 0 else "Menos luz")

# 2. Panel de SELECCIÓN (Aparece instantáneamente al tocar)
if event_data and len(event_data.get("selection", {}).get("points", [])) > 0:
    idx = event_data["selection"]["points"][0]["point_index"]
    f_sel = df.iloc[idx]
    fecha_sel = f_sel['Fecha'].replace(tzinfo=local_tz)
    s_sel = sun(city.observer, date=fecha_sel, tzinfo=local_tz)
    
    st.markdown(f"### 🔍 Seleccionado: {fecha_sel.strftime('%d %B')}")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Amanecer", s_sel['sunrise'].strftime('%H:%M'))
    sc2.metric("Atardecer", s_sel['sunset'].strftime('%H:%M'))
    sc3.metric("Luna", get_moon_phase(fecha_sel))
    
    if st.button("✖️ Cerrar"):
        st.session_state.graph_key += 1
        st.rerun()
else:
    st.info("👆 Toca una barra para comparar.")
    
