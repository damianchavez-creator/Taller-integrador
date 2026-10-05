"""
app.py - Simulador Monte Carlo de concentración de mercado.

Ejecutar con:  streamlit run app.py
Dependencias:  pip install streamlit numpy pandas plotly

Requiere un módulo `motor.py` en la misma carpeta con las funciones
`cr_k`, `ihh`, `generar_cuotas` y `simular_mercado` de los pasos anteriores.
"""
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from motor import cr_k, generar_cuotas, ihh, simular_mercado

# ----------------------------------------------------------------------
# Configuración de página
# ----------------------------------------------------------------------
st.set_page_config(page_title="Simulador de Concentración", layout="wide")
st.title("Simulador Monte Carlo de concentración de mercado")

UMBRAL_ITER_ALTO = 100_000


def calcular_indicador(fracciones, clave, k):
    """Calcula el indicador del caso en la MISMA escala que la simulación
    (IHH en puntos, CRk en fracción) para poder compararlos."""
    if clave == "ihh":
        return ihh(fracciones, "puntos")
    return cr_k(fracciones, k)


# ----------------------------------------------------------------------
# Umbrales teóricos de concentración (módulo de evaluación)
# ----------------------------------------------------------------------
NIVELES = ["Baja", "Moderada", "Alta"]

# IHH en puntos: (límite entre Baja/Moderada, límite entre Moderada/Alta).
# Verifica los umbrales vigentes de tu autoridad de competencia local.
ESTANDARES_IHH = {
    "Guías de fusiones EE. UU. 1992 / 2023 (1 000 / 1 800)": (1000, 1800),
    "Guías de fusiones EE. UU. 2010 (1 500 / 2 500)": (1500, 2500),
}

# CRk en fracción. Clasificación de Shepherd, formulada para CR4:
# <40% competencia efectiva, 40-60% oligopolio laxo, >60% oligopolio estrecho.
ESTANDAR_CRK = ("Clasificación de Shepherd para CR4 (40% / 60%)", (0.40, 0.60))


def clasificar(valor, limites):
    """Baja si valor < bajo; Moderada si bajo <= valor <= alto; Alta si > alto."""
    bajo, alto = limites
    if valor < bajo:
        return "Baja"
    if valor <= alto:
        return "Moderada"
    return "Alta"


def percentil_caso(datos, valor):
    """% de simulaciones con indicador menor o igual al del caso."""
    return float(np.mean(datos <= valor) * 100)


def texto_umbrales(clave, limites):
    bajo, alto = limites
    if clave == "ihh":
        return (f"- **Baja:** IHH < {bajo:,.0f}\n"
                f"- **Moderada:** {bajo:,.0f} a {alto:,.0f}\n"
                f"- **Alta:** IHH > {alto:,.0f}")
    return (f"- **Baja:** CRk < {bajo:.0%}\n"
            f"- **Moderada:** {bajo:.0%} a {alto:.0%}\n"
            f"- **Alta:** CRk > {alto:.0%}")


def notas_tecnicas(clave, n, k, limites):
    if clave == "ihh":
        minimo = 10_000 / n
        return [
            "El IHH suma los cuadrados de las cuotas (en %), por lo que "
            "pondera más a las empresas grandes.",
            f"Con N = {n} empresas, el IHH mínimo posible es {minimo:,.0f} "
            f"(cuotas iguales), así que el nivel mínimo alcanzable en este "
            f"mercado es **{clasificar(minimo, limites)}**.",
        ]
    notas = ["El CRk suma las k mayores cuotas e ignora cómo se reparte "
             "el resto del mercado."]
    if k != 4:
        notas.append(f"Los umbrales de Shepherd se formularon para CR4; con "
                     f"k = {k} la clasificación es solo orientativa.")
    if k == n:
        notas.append("Con k = N el CRk vale siempre 100%, así que no "
                     "discrimina entre mercados.")
    return notas


# ----------------------------------------------------------------------
# Sidebar: parámetros de entrada
# ----------------------------------------------------------------------
with st.sidebar:
    st.header("Parámetros")

    indicador = st.selectbox(
        "Indicador de concentración",
        options=["IHH", "CRk"],
        help="IHH: Índice de Herfindahl-Hirschman (puntos, 0-10 000). "
             "CRk: suma de las k mayores cuotas.",
    )

    n_empresas = st.number_input(
        "Número de empresas (N)",
        min_value=2, max_value=100, value=5, step=1,
    )

    k = None
    if indicador == "CRk":
        k = st.number_input(
            "k (empresas más grandes)",
            min_value=1, max_value=int(n_empresas),
            value=min(3, int(n_empresas)), step=1,
        )

    iteraciones = st.number_input(
        "Iteraciones de Monte Carlo",
        min_value=100, max_value=500_000, value=1000, step=1000,
    )

    st.warning(
        "⚠️ **Rendimiento:** el tiempo y el consumo de cómputo crecen de forma "
        "lineal con las iteraciones (y con N). Valores muy altos pueden "
        "volver lenta o bloquear la aplicación, sobre todo en servidores "
        "compartidos."
    )
    if iteraciones > UMBRAL_ITER_ALTO:
        st.warning(
            f"Has superado {UMBRAL_ITER_ALTO:,} iteraciones: la simulación "
            "puede tardar varios segundos o minutos."
        )

    ejecutar = st.button("Ejecutar simulación", type="primary")

# Parámetros vigentes (normalizados)
clave = "ihh" if indicador == "IHH" else "cr_k"
n = int(n_empresas)
k_int = int(k) if clave == "cr_k" else None
unidad = "puntos" if clave == "ihh" else "fracción"
params_actuales = (clave, n, k_int)

# ----------------------------------------------------------------------
# Ejecución de la simulación (el resultado persiste en session_state
# para que editar el caso particular no obligue a re-simular)
# ----------------------------------------------------------------------
if ejecutar:
    with st.spinner("Simulando..."):
        t0 = time.perf_counter()
        resultados = simular_mercado(
            n, clave, k=k_int, iteraciones=int(iteraciones)
        )
        duracion = time.perf_counter() - t0
    st.session_state["sim"] = {
        "params": params_actuales,
        "datos": np.asarray(resultados),
        "duracion": duracion,
    }

# ----------------------------------------------------------------------
# 1) Caso particular
# ----------------------------------------------------------------------
st.header("1. Caso particular")

modo = st.radio(
    "Origen de las cuotas",
    ["Ingreso manual", "Caso aleatorio"],
    horizontal=True,
)

fracciones_caso = None   # cuotas del caso como fracciones (suman 1)
valor_caso = None        # valor del indicador para el caso

if modo == "Ingreso manual":
    st.caption(f"Ingresa las cuotas de las {n} empresas en porcentaje (%). "
               "Deben sumar 100.")
    base = pd.DataFrame(
        {"Cuota (%)": np.full(n, 100.0 / n)},
        index=[f"Empresa {i + 1}" for i in range(n)],
    )
    # La key depende de N: si N cambia, la tabla se reinicia
    editado = st.data_editor(
        base,
        key=f"editor_{n}",
        column_config={
            "Cuota (%)": st.column_config.NumberColumn(
                min_value=0.0, max_value=100.0, step=0.01, format="%.4f"
            )
        },
    )
    cuotas_pct = editado["Cuota (%)"].to_numpy(dtype=float)
    st.caption(f"Suma actual: {np.nansum(cuotas_pct):.4f} %")
    fracciones_caso = cuotas_pct / 100.0

else:
    if st.button("🎲 Generar caso aleatorio"):
        # alpha=1: mismo supuesto que la simulación (uniforme en el simplex)
        st.session_state["caso_aleatorio"] = generar_cuotas(n, alpha=1.0)

    aleatorio = st.session_state.get("caso_aleatorio")
    if aleatorio is not None and len(aleatorio) == n:
        fracciones_caso = aleatorio
        tabla = pd.DataFrame(
            {"Cuota (%)": aleatorio * 100},
            index=[f"Empresa {i + 1}" for i in range(n)],
        )
        st.dataframe(tabla.style.format("{:.4f}"))
    else:
        st.info("Pulsa el botón para generar un caso aleatorio.")

# Indicador del caso (con la validación del motor)
if fracciones_caso is not None:
    try:
        valor_caso = calcular_indicador(fracciones_caso, clave, k_int)
        st.metric(f"{indicador} del caso particular ({unidad})",
                  f"{valor_caso:,.4f}")
    except (ValueError, TypeError) as e:
        st.error(f"Caso no válido: {e}")

# ----------------------------------------------------------------------
# 2) Distribución empírica de la simulación
# ----------------------------------------------------------------------
st.header("2. Distribución empírica (Monte Carlo)")

sim = st.session_state.get("sim")

if sim is None:
    st.info("Configura los parámetros y pulsa **Ejecutar simulación**.")
elif sim["params"] != params_actuales:
    st.warning("Cambiaste el indicador, N o k desde la última simulación. "
               "Vuelve a pulsar **Ejecutar simulación** para actualizar el "
               "gráfico.")
else:
    datos = sim["datos"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Media", f"{datos.mean():.4f}")
    c2.metric("Desv. estándar", f"{datos.std(ddof=1):.4f}")
    c3.metric("Percentil 5", f"{np.percentile(datos, 5):.4f}")
    c4.metric("Percentil 95", f"{np.percentile(datos, 95):.4f}")

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=datos, nbinsx=40, name="Simulación",
        marker_line_width=1, marker_line_color="white", opacity=0.85,
    ))

    if valor_caso is not None:
        fig.add_vline(
            x=valor_caso, line_width=3, line_dash="dash", line_color="red",
            annotation_text=f"Caso particular: {valor_caso:,.2f}"
                            if clave == "ihh"
                            else f"Caso particular: {valor_caso:.4f}",
            annotation_position="top right",
            annotation_font_color="red",
        )

    fig.update_layout(
        title=f"Distribución simulada de {indicador} "
              f"(N = {n}{f', k = {k_int}' if k_int else ''}, "
              f"{len(datos):,} iteraciones)",
        xaxis_title=f"{indicador} ({unidad})",
        yaxis_title="Frecuencia (nº de simulaciones)",
        showlegend=False,
        bargap=0.02,
    )
    st.plotly_chart(fig)

    if valor_caso is not None:
        percentil = float(np.mean(datos <= valor_caso) * 100)
        st.success(
            f"El caso particular se ubica en el **percentil {percentil:.1f}** "
            f"de la distribución simulada: el {percentil:.1f}% de los "
            f"mercados aleatorios tiene un {indicador} menor o igual."
        )
    else:
        st.info("Define un caso particular válido para ver su posición "
                "sobre el histograma.")

    st.caption(f"{len(datos):,} iteraciones en {sim['duracion']:.2f} s.")

# ----------------------------------------------------------------------
# 3) Módulo de evaluación
# ----------------------------------------------------------------------
st.header("3. Evaluación")

# Distribución simulada, solo si corresponde a los parámetros vigentes
datos_sim = (sim["datos"] if sim is not None
             and sim["params"] == params_actuales else None)

if valor_caso is None:
    st.info("Define un caso particular válido (sección 1) para poder "
            "evaluarte.")
else:
    st.write("Observa las cuotas del caso particular. "
             "**¿Qué nivel de concentración crees que tiene?**")

    if clave == "ihh":
        nombre_estandar = st.selectbox("Estándar de referencia",
                                       list(ESTANDARES_IHH))
        limites = ESTANDARES_IHH[nombre_estandar]
    else:
        nombre_estandar, limites = ESTANDAR_CRK

    respuesta = st.radio("Tu respuesta", NIVELES, index=None, horizontal=True)

    if st.button("Verificar respuesta", disabled=respuesta is None):
        st.session_state["eval"] = {
            "respuesta": respuesta,
            "valor": valor_caso,
            "params": params_actuales,
            "estandar": nombre_estandar,
        }

    # La retroalimentación se muestra solo si sigue vigente (mismo caso,
    # mismos parámetros y mismo estándar que cuando se respondió)
    ev = st.session_state.get("eval")
    vigente = (ev is not None
               and ev["valor"] == valor_caso
               and ev["params"] == params_actuales
               and ev["estandar"] == nombre_estandar)

    if vigente:
        correcta = clasificar(valor_caso, limites)
        if ev["respuesta"] == correcta:
            st.success(f"✅ ¡Correcto! El caso tiene concentración "
                       f"**{correcta}**.")
        else:
            st.error(f"❌ Respondiste **{ev['respuesta']}**, pero el caso "
                     f"tiene concentración **{correcta}**.")

        valor_txt = (f"{valor_caso:,.2f} puntos" if clave == "ihh"
                     else f"{valor_caso:.2%}")
        st.markdown(f"**Valor del caso:** {indicador} = {valor_txt}")

        st.subheader("Justificación técnica")
        st.markdown(f"Estándar aplicado: *{nombre_estandar}*\n\n"
                    + texto_umbrales(clave, limites))
        for nota in notas_tecnicas(clave, n, k_int, limites):
            st.markdown(f"- {nota}")

        st.subheader("Posición en la distribución de Monte Carlo")
        if datos_sim is None:
            st.info("Ejecuta la simulación con estos parámetros para ver "
                    "el percentil del caso.")
        else:
            pct = percentil_caso(datos_sim, valor_caso)
            bajo, alto = limites
            masks = {
                "Baja": datos_sim < bajo,
                "Moderada": (datos_sim >= bajo) & (datos_sim <= alto),
                "Alta": datos_sim > alto,
            }
            share = float(masks[correcta].mean() * 100)
            st.markdown(
                f"- El caso está en el **percentil {pct:.1f}**: el "
                f"{pct:.1f}% de los mercados simulados tiene un {indicador} "
                f"menor o igual.\n"
                f"- El **{share:.1f}%** de los mercados simulados cae en la "
                f"misma categoría (**{correcta}**), lo que indica qué tan "
                f"típico es este nivel bajo el supuesto de cuotas "
                f"uniformes (alpha = 1)."
            )
