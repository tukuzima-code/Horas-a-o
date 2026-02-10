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

st.set_page_config(page_title="Luz Solar Pro", layout="wide")

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

st.title("☀️ Agenda Solar & Efemérides")

# --- BUSCADOR ---
col_gps, col_txt = st.columns([1, 4])
with col_gps:
    if st.button("📍 GPS", use_container_width=True):
        loc = get_geolocation()
        if loc:
            st.session_state['lat'], st.session_state['lon'] = loc['coords']['latitude'], loc['coords']['longitude']
            st.session_state['dir'] = "Ubicación GPS"; st.rerun()

with col_txt:
    entrada = st.text_input("Buscar...", placeholder="Ej: Sagunto", label_visibility="collapsed")
    if entrada:
        res = buscar_lugar_robusto(entrada)
        if res:
            st.session_state['lat'], st.session_state['lon'] = res.latitude, res.longitude
            st.session_state['dir'] = res.address.split(',')[0]; st.rerun()

# --- CÁLCULOS ---
tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=st.session_state['lon'], lat=st.session_state['lat']) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("P", "R", tz_name, st.session_state['lat'], st.session_state['lon'])
ahora = datetime.now(local_tz)

st.info(f"📍 **{st.session_state['dir']}** ({tz_name})")

# --- MÉTRICAS HOY ---
s1 = sun(city.observer, date=ahora, tzinfo=local_tz)
s2 = sun(city.observer, date=ahora + timedelta(days=1), tzinfo=local_tz)
dif_seg = (s2['sunset'] - s2['sunrise']).total_seconds() - (s1['sunset'] - s1['sunrise']).total_seconds()

m1, m2, m3, m4 = st.columns(4)
m1.metric("🌅 Amanecer", s1['sunrise'].strftime('%H:%M'))
m2.metric("🌇 Atardecer", s1['sunset'].strftime('%H:%M'))
m3.metric("🌓 Luna", get_moon_phase_data(ahora))
minutos, segundos = int(abs(dif_seg)//60), int(abs(dif_seg)%60)
m4.metric("⏱️ Cambio luz", f"{minutos}m {segundos}s", delta="Más luz" if dif_seg > 0 else "Menos luz")

# --- GENERACIÓN DE DATOS ANUALES ---
data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
for i in range(0, 366):
    dia_m = inicio_año + timedelta(days=i)
    if dia_m.year > ahora.year: break
    try:
        s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
        am_dt, at_dt = s_dia['sunrise'], s_dia['sunset']
        dur = (at_dt - am_dt).total_seconds() / 3600
        data.append({
            "Día": i+1, "Am": am_dt.hour + am_dt.minute/60, "Dur": dur, 
            "Amanece": am_dt, "Atardece": at_dt, "Fecha": dia_m
        })
    except: continue

df = pd.DataFrame(data)

# --- GRÁFICO ---
fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["Día"], y=df["Dur"], base=df["Am"], 
    marker_color=[get_season_color(i) for i in df["Día"]],
    hoverinfo="none"
))

# Marcadores de estaciones en el eje X
estaciones = [
    {"dia": 80, "icon": "🌱", "label": "Primavera"},
    {"dia": 172, "icon": "☀️", "label": "Verano"},
    {"dia": 264, "icon": "🍂", "label": "Otoño"},
    {"dia": 355, "icon": "❄️", "label": "Invierno"}
]

for est in estaciones:
    fig.add_annotation(
        x=est["dia"], y=0, text=est["icon"], showarrow=False,
        font=dict(size=20), yshift=-30
    )

fig.add_vline(x=ahora.timetuple().tm_yday, line_width=2, line_color="red")

fig.update_layout(
    template="plotly_dark", height=450, margin=dict(l=10, r=10, t=20, b=60),
    yaxis=dict(range=[0, 24], dtick=4, title="Horas"),
    xaxis=dict(tickmode='array', tickvals=[1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335],
               ticktext=['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'])
)
st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# --- DATOS DE INTERÉS (FOOTER) ---
st.subheader("📊 Efemérides de este año")

# Cálculos de extremos
dia_largo = df.loc[df['Dur'].idxmax()]
dia_corto = df.loc[df['Dur'].idxmin()]
amanece_antes = df.loc[df['Amanece'].dt.time == df['Amanece'].dt.time.min()].iloc[0]
atardece_tarde = df.loc[df['Atardece'].dt.time == df['Atardece'].dt.time.max()].iloc[0]

# Cambio de hora (estimación España/Europa: último domingo de marzo y octubre)
def get_dst_dates(year):
    # Marzo
    m = datetime(year, 3, 31)
    d_marzo = m - timedelta(days=(m.weekday() + 1) % 7)
    # Octubre
    o = datetime(year, 10, 31)
    d_octubre = o - timedelta(days=(o.weekday() + 1) % 7)
    return d_marzo, d_octubre

dst_m, dst_o = get_dst_dates(ahora.year)

f1, f2, f3 = st.columns(3)
with f1:
    st.write(f"🔝 **Día más largo:** {dia_largo['Fecha'].strftime('%d de %B')} ({round(dia_largo['Dur'], 2)}h)")
    st.write(f"📉 **Día más corto:** {dia_corto['Fecha'].strftime('%d de %B')} ({round(dia_corto['Dur'], 2)}h)")
with f2:
    st.write(f"🌅 **Amanece más pronto:** {amanece_antes['Fecha'].strftime('%d de %B')} ({amanece_antes['Amanece'].strftime('%H:%M')})")
    st.write(f"🌇 **Atardece más tarde:** {atardece_tarde['Fecha'].strftime('%d de %B')} ({atardece_tarde['Atardece'].strftime('%H:%M')})")
with f3:
    st.write(f"🕐 **Cambio de hora (Verano):** {dst_m.strftime('%d de marzo')}")
    st.write(f"🕒 **Cambio de hora (Invierno):** {dst_o.strftime('%d de octubre')}")
    
