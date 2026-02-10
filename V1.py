import streamlit as st
import pandas as pd
from astral import LocationInfo
from astral.sun import sun
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta
import plotly.graph_objects as go
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
        # User agent aleatorio para evitar bloqueos de Nominatim
        geolocator = Nominatim(user_agent=f"sun_app_{random.randint(1,999)}")
        return geolocator.geocode(texto, timeout=10, language="es")
    except: return None

# --- GESTIÓN DE UBICACIÓN ---
# Inicializamos valores por defecto si no existen
if 'lat' not in st.session_state:
    st.session_state.lat = 39.664
    st.session_state.lon = -0.228
    st.session_state.dir = "Puerto de Sagunto"

st.title("☀️ Agenda Solar")

# --- INTERFAZ DE BÚSQUEDA ---
col_gps, col_txt = st.columns([1, 3])

with col_gps:
    if st.button("📍 GPS"):
        loc = get_geolocation()
        if loc:
            st.session_state.lat = loc['coords']['latitude']
            st.session_state.lon = loc['coords']['longitude']
            st.session_state.dir = "Ubicación GPS"
            st.rerun()

with col_txt:
    # Usamos un formulario pequeño para asegurar que la búsqueda se procese al pulsar Enter
    with st.form("search_form", clear_on_submit=True):
        entrada = st.text_input("Buscar ciudad...", placeholder="Ej: Madrid, Valencia...")
        submit = st.form_submit_button("Buscar")
        
        if submit and entrada:
            res = buscar_lugar_robusto(entrada)
            if res:
                st.session_state.lat = res.latitude
                st.session_state.lon = res.longitude
                st.session_state.dir = res.address.split(',')[0]
                st.rerun()
            else:
                st.error("No se encontró el lugar. Intenta con otra ciudad.")

# --- CÁLCULOS ---
tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=st.session_state.lon, lat=st.session_state.lat) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("P", "R", tz_name, st.session_state.lat, st.session_state.lon)
ahora = datetime.now(local_tz)

st.success(f"📍 {st.session_state.dir}")

# --- CUADRITOS DE DATOS ---
s1 = sun(city.observer, date=ahora, tzinfo=local_tz)
s2 = sun(city.observer, date=ahora + timedelta(days=1), tzinfo=local_tz)
dif_seg = (s2['sunset'] - s2['sunrise']).total_seconds() - (s1['sunset'] - s1['sunrise']).total_seconds()

c1, c2, c3 = st.columns(3)
c1.metric("Amanecer", s1['sunrise'].strftime('%H:%M'))
c2.metric("Atardecer", s1['sunset'].strftime('%H:%M'))
minutos, segundos = int(abs(dif_seg)//60), int(abs(dif_seg)%60)
c3.metric("Mañana", f"{minutos}m {segundos}s", delta="Más luz" if dif_seg > 0 else "Menos luz")

# --- GRÁFICO BASE (SIN MOVIMIENTO NI DEGRADADOS) ---
data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
for i in range(0, 365, 2): # Saltos de 2 días para que sea más ligero
    dia_m = inicio_año + timedelta(days=i)
    try:
        s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
        am = s_dia['sunrise'].hour + s_dia['sunrise'].minute/60
        at = s_dia['sunset'].hour + s_dia['sunset'].minute/60
        data.append({"Día": i, "Am": am, "Dur": at - am})
    except: continue

df = pd.DataFrame(data)
fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["Día"], y=df["Dur"], base=df["Am"],
    marker_color='rgb(255, 165, 0)', # Color base naranja solar
    hoverinfo='skip' # Desactiva el movimiento/interacción pesada
))

# Marca de hoy
fig.add_vline(x=ahora.timetuple().tm_yday, line_width=2, line_color="red")

fig.update_layout(
    template="plotly_dark", height=400, showlegend=False,
    yaxis=dict(range=[0, 24], fixedrange=True, dtick=4),
    xaxis=dict(fixedrange=True), # Bloquea el zoom/movimiento en el gráfico
    margin=dict(l=10, r=10, t=10, b=10)
)

st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
