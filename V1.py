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

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Agenda Solar Pro", layout="wide")

def decimal_a_horas_mins(decimal_horas):
    """Convierte decimales (9.4) a formato humano (9h 24min)"""
    horas = int(decimal_horas)
    minutos = int(round((decimal_horas - horas) * 60))
    if minutos == 60:
        horas += 1
        minutos = 0
    return f"{horas}h {minutos}min"

@st.cache_data(show_spinner=False, ttl=600)
def buscar_ubicacion(texto):
    """Busca lat/lon por nombre de ciudad o código postal"""
    if not texto: return None
    try:
        user_agent = f"solar_app_{random.randint(1000, 9999)}"
        geolocator = Nominatim(user_agent=user_agent)
        # Añadimos ", Spain" por defecto para mejorar la precisión si es solo un CP
        query = texto if "," in texto else f"{texto}, Spain"
        location = geolocator.geocode(query, timeout=10, language="es")
        return location
    except:
        return None

def get_moon_phase_data(date):
    m = ephem.Moon(date)
    p = m.phase 
    icon = "🌑" if p < 5 else "🌙" if p < 45 else "🌓" if p < 55 else "🌔" if p < 95 else "🌕"
    return f"{icon} {int(p)}%"

def get_season_color(d):
    if d < 80 or d > 355: return 'rgb(100, 149, 237)' # Invierno
    elif d < 172: return 'rgb(144, 238, 144)' # Primavera
    elif d < 264: return 'rgb(255, 165, 0)'   # Verano
    else: return 'rgb(210, 105, 30)'          # Otoño

# --- LÓGICA DE UBICACIÓN ---
if 'lat' not in st.session_state:
    st.session_state['lat'], st.session_state['lon'] = 39.664, -0.228
    st.session_state['dir'] = "Puerto de Sagunto"

st.title("☀️ Agenda Solar & Efemérides")

# Buscador simplificado
entrada = st.text_input("Introduce población o código postal (ej: Sagunto o 46520)", 
                        placeholder="Presiona Enter para buscar...")

if entrada:
    res = buscar_ubicacion(entrada)
    if res:
        st.session_state['lat'], st.session_state['lon'] = res.latitude, res.longitude
        st.session_state['dir'] = res.address.split(',')[0]
    else:
        st.error("No se encontró la ubicación. Prueba a ser más específico.")

# --- CÁLCULOS ASTRONÓMICOS ---
tf = TimezoneFinder()
tz_name = tf.timezone_at(lng=st.session_state['lon'], lat=st.session_state['lat']) or "Europe/Madrid"
local_tz = pytz.timezone(tz_name)
city = LocationInfo("Lugar", "Región", tz_name, st.session_state['lat'], st.session_state['lon'])
ahora = datetime.now(local_tz)

st.info(f"📍 Datos actuales para: **{st.session_state['dir']}**")

# --- MÉTRICAS SUPERIORES ---
s_hoy = sun(city.observer, date=ahora, tzinfo=local_tz)
s_manana = sun(city.observer, date=ahora + timedelta(days=1), tzinfo=local_tz)
dif_seg = (s_manana['sunset'] - s_manana['sunrise']).total_seconds() - (s_hoy['sunset'] - s_hoy['sunrise']).total_seconds()

m1, m2, m3, m4 = st.columns(4)
m1.metric("🌅 Amanecer", s_hoy['sunrise'].strftime('%H:%M'))
m2.metric("🌇 Atardecer", s_hoy['sunset'].strftime('%H:%M'))
m3.metric("🌓 Luna", get_moon_phase_data(ahora))
m4.metric("⏱️ Cambio luz", f"{int(abs(dif_seg)//60)}m {int(abs(dif_seg)%60)}s", 
          delta="Ganando luz" if dif_seg > 0 else "Perdiendo luz")

# --- GRÁFICO ---
data = []
inicio_año = datetime(ahora.year, 1, 1, tzinfo=local_tz)
for i in range(0, 366):
    dia_m = inicio_año + timedelta(days=i)
    if dia_m.year > ahora.year: break
    try:
        s_dia = sun(city.observer, date=dia_m, tzinfo=local_tz)
        am, at = s_dia['sunrise'], s_dia['sunset']
        dur_decimal = (at - am).total_seconds() / 3600
        data.append({
            "Día": i+1, "Am_dec": am.hour + am.minute/60, "Dur_decimal": dur_decimal, 
            "Dur_texto": decimal_a_horas_mins(dur_decimal), "Amanece": am.strftime('%H:%M'), 
            "Atardece": at.strftime('%H:%M'), "Fecha": dia_m.strftime("%d %b"),
            "Luna": get_moon_phase_data(dia_m), "Amanece_dt": am, "Atardece_dt": at
        })
    except: continue

df = pd.DataFrame(data)
fig = go.Figure()
fig.add_trace(go.Bar(
    x=df["Día"], y=df["Dur_decimal"], base=df["Am_dec"], 
    marker_color=[get_season_color(i) for i in df["Día"]],
    customdata=df[["Amanece", "Atardece", "Fecha", "Luna", "Dur_texto"]],
    hovertemplate="<b>%{customdata[2]}</b><br>🌅 Salida: %{customdata[0]}<br>🌇 Puesta: %{customdata[1]}<br>⏱️ Duración: %{customdata[4]}<br>🌙 Luna: %{customdata[3]}<extra></extra>"
))

# Iconos estaciones
for est in [{"dia": 80, "icon": "🌱"}, {"dia": 172, "icon": "☀️"}, {"dia": 264, "icon": "🍂"}, {"dia": 355, "icon": "❄️"}]:
    fig.add_annotation(x=est["dia"], y=0, text=est["icon"], showarrow=False, font=dict(size=20), yshift=-30)

fig.add_vline(x=ahora.timetuple().tm_yday, line_width=2, line_color="red")

fig.update_layout(
    template="plotly_dark", height=500, margin=dict(l=10, r=10, t=20, b=60), showlegend=False,
    yaxis=dict(range=[0, 24], dtick=4, title="Horas"),
    xaxis=dict(tickmode='array', tickvals=[1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335],
               ticktext=['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'],
               rangeslider=dict(visible=True, thickness=0.04))
)
st.plotly_chart(fig, use_container_width=True)

# --- PANEL DE EFEMÉRIDES (DATOS DE INTERÉS) ---
st.markdown("### 📊 Datos de interés este año")
d_largo = df.loc[df['Dur_decimal'].idxmax()]
d_corto = df.loc[df['Dur_decimal'].idxmin()]
am_antes = df.loc[df['Amanece_dt'].dt.time == df['Amanece_dt'].dt.time.min()].iloc[0]
at_tarde = df.loc[df['Atardece_dt'].dt.time == df['Atardece_dt'].dt.time.max()].iloc[0]

# Cambio de hora
m = datetime(ahora.year, 3, 31); dst_v = m - timedelta(days=(m.weekday() + 1) % 7)
o = datetime(ahora.year, 10, 31); dst_i = o - timedelta(days=(o.weekday() + 1) % 7)

c1, c2, c3 = st.columns(3)
with c1:
    st.write(f"🔝 **Día más largo:** {d_largo['Fecha']} ({d_largo['Dur_texto']})")
    st.write(f"📉 **Día más corto:** {d_corto['Fecha']} ({d_corto['Dur_texto']})")
with c2:
    st.write(f"🌅 **Amanece más pronto:** {am_antes['Fecha']} ({am_antes['Amanece']})")
    st.write(f"🌇 **Atardece más tarde:** {at_tarde['Fecha']} ({at_tarde['Atardece']})")
with c3:
    st.write(f"🕐 **Cambio Verano:** {dst_v.strftime('%d de marzo')}")
    st.write(f"🕒 **Cambio Invierno:** {dst_i.strftime('%d de octubre')}")
    
