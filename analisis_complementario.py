"""
Análisis complementarios
  1) Validación de la simulación frente a la espera observada en el Registro
  2) Análisis de sensibilidad de la propuesta (demanda y tiempo de servicio)
  3) Costo diario total: configuración actual frente a propuesta
  4) Intervalos de confianza para la Tabla 16

Requisitos:  pip install simpy numpy scipy matplotlib openpyxl
Uso:         python analisis_complementario.py
             (en la misma carpeta que simulacion_audifarma.py, tiempos_servicio.csv y Datos_Audifarma.xlsx)
"""
import contextlib
import datetime as dt
import io
import runpy
import numpy as np
import openpyxl
import matplotlib
import matplotlib.ticker
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Carga el modelo de simulación del numeral 5.7 (sin repetir su salida en pantalla)
with contextlib.redirect_stdout(io.StringIO()):
    M = runpy.run_path("simulacion_audifarma.py")
una_jornada = M["una_jornada"]
G = una_jornada.__globals__                 # parámetros del modelo (LAMBDA, escala, ...)
CONF = M["CONFIGURACIONES"]
REPLICAS, SEMILLA, UMBRAL = M["REPLICAS"], M["SEMILLA"], M["UMBRAL_MIN"]
FRANJAS = M["FRANJAS"]
LAMBDA_BASE = list(G["LAMBDA"])
ESCALA_BASE = G["escala"]
C_SERV, C_ESP = 19_000, 9_620              # COP por hora-módulo y por hora de espera
z = 1.96


def correr(modulos, rng, n=REPLICAS):
    """Devuelve una lista de días: (esperas, franja de llegada, cola minuto a minuto)."""
    return [una_jornada(modulos, rng) for _ in range(n)]


def resumen(dias, modulos):
    wq = np.array([w.mean() for w, _, _ in dias])
    pct = np.array([(w > UMBRAL).mean() for w, _, _ in dias])
    wmax = np.array([w.max() for w, _, _ in dias])
    cmax = np.array([max(c.values()) for _, _, c in dias])
    horas_esp = np.array([w.sum() / 60 for w, _, _ in dias])          # horas-usuario de espera por día
    costo = sum(modulos) * C_SERV + horas_esp * C_ESP
    todas = np.concatenate([w for w, _, _ in dias])
    rb = np.random.default_rng(7)                                     # bootstrap por días para el P95
    p95_b = [np.percentile(np.concatenate([dias[i][0] for i in rb.integers(0, len(dias), len(dias))]), 95)
             for _ in range(500)]
    franja = np.array([[w[f == k].mean() if (f == k).any() else 0 for k in range(10)] for w, f, _ in dias])
    ic = lambda v: z * v.std(ddof=1) / np.sqrt(len(v))
    return dict(wq=(wq.mean(), ic(wq)), pct=(pct.mean(), ic(pct)), wmax=(wmax.mean(), ic(wmax)),
                cmax=(cmax.mean(), ic(cmax)), p95=(np.percentile(todas, 95), z * np.std(p95_b, ddof=1)),
                pct_global=(todas > UMBRAL).mean(), horas_esp=(horas_esp.mean(), ic(horas_esp)),
                costo=(costo.mean(), ic(costo)), franja=franja.mean(axis=0), todas=todas)


# Reproduce exactamente las mismas 200 réplicas de simulacion_audifarma.py (misma semilla y orden)
rng = np.random.default_rng(SEMILLA)
dias_act = correr(CONF["Actual"], rng)
dias_pro = correr(CONF["Propuesta"], rng)
A, P = resumen(dias_act, CONF["Actual"]), resumen(dias_pro, CONF["Propuesta"])

wb = openpyxl.Workbook(); wb.remove(wb.active)
f1 = lambda v, d=1: f"{v:.{d}f}".replace(".", ",")

# ===================================================== 1) VALIDACIÓN
reg = wb_reg = openpyxl.load_workbook("Datos_Audifarma.xlsx")["Registro"]
def seg(t): return t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1e6
obs, obs_f = [], []
for r in reg.iter_rows(min_row=4, values_only=True):
    if isinstance(r[5], dt.time) and isinstance(r[6], dt.time):
        obs.append((seg(r[6]) - seg(r[5])) / 60); obs_f.append(r[5].hour - 7)
obs, obs_f = np.array(obs), np.array(obs_f)
o_ic = z * obs.std(ddof=1) / np.sqrt(len(obs))

print("1) VALIDACIÓN DE LA SIMULACIÓN FRENTE A LO OBSERVADO (configuración actual)")
filas = [("Espera promedio en cola (min)", f"{f1(obs.mean())} ± {f1(o_ic)}", f"{f1(A['wq'][0])} ± {f1(A['wq'][1])}",
          (A['wq'][0] / obs.mean() - 1) * 100),
         ("Mediana de la espera (min)", f1(np.median(obs)), f1(np.median(A['todas'])),
          (np.median(A['todas']) / np.median(obs) - 1) * 100),
         ("Percentil 90 de la espera (min)", f1(np.percentile(obs, 90)), f1(np.percentile(A['todas'], 90)),
          (np.percentile(A['todas'], 90) / np.percentile(obs, 90) - 1) * 100),
         (f"Usuarios que esperan más de {UMBRAL} min", f"{f1(100*(obs > UMBRAL).mean())} %",
          f"{f1(100*A['pct_global'])} %", None)]
ws = wb.create_sheet("1_Validacion")
ws.append(["Indicador", f"Observado (Registro, n = {len(obs)})", f"Simulado ({REPLICAS} réplicas)", "Diferencia"])
for nom, o, s, d in filas:
    dtxt = "" if d is None else f"{d:+.1f} %"
    if d is None:
        dtxt = f"{100*(A['pct_global'] - (obs > UMBRAL).mean()):+.1f} p.p."
    ws.append([nom, o, s, dtxt]); print(f"  {nom}: observado {o} | simulado {s} | {dtxt}")
ws.append([])
ws.append(["Franja", "Observado (min)", "n observado", "Simulado (min)"])
print("  Por franja de llegada (observado / simulado):")
for k in range(10):
    m = obs_f == k
    ws.append([FRANJAS[k], round(obs[m].mean(), 1), int(m.sum()), round(A["franja"][k], 1)])
    print(f"    {FRANJAS[k]}: {f1(obs[m].mean())} (n={m.sum()}) / {f1(A['franja'][k])}")
corr = np.corrcoef([obs[obs_f == k].mean() for k in range(10)], A["franja"])[0, 1]
ws.append(["Correlación por franja", round(corr, 3)])
print(f"  Correlación entre los perfiles por franja: {corr:.3f}")
# Prueba t de Welch: media observada frente a medias diarias simuladas
from scipy import stats
wq_sim_dias = np.array([w.mean() for w, _, _ in dias_act])
t = stats.ttest_ind(obs, np.concatenate([w for w, _, _ in dias_act]), equal_var=False)
print(f"  Prueba t de Welch (observado vs simulado): t = {t.statistic:.2f}, p = {t.pvalue:.3f}\n")
ws.append(["Prueba t de Welch", f"t = {t.statistic:.2f}", f"p = {t.pvalue:.3f}"])

# ===================================================== 2) SENSIBILIDAD
print("2) ANÁLISIS DE SENSIBILIDAD DE LA PROPUESTA")
ws = wb.create_sheet("2_Sensibilidad")
ws.append(["Escenario", "Configuración", "Espera promedio (min)", "IC 95 % (±)", f"% espera > {UMBRAL} min",
           "P95 (min)", "Franja con mayor espera", "Espera en esa franja (min)", "ρ 10:00-11:00"])
CON_REGLA = list(CONF["Propuesta"]); CON_REGLA[3] = 5                 # quinto módulo de 10:00 a 11:00
escenarios = [("Base", 1.00, 1.00), ("Demanda +5 %", 1.05, 1.00), ("Demanda +10 %", 1.10, 1.00),
              ("Demanda +15 %", 1.15, 1.00), ("Servicio +10 %", 1.00, 1.10),
              ("Demanda +10 % y servicio +10 %", 1.10, 1.10)]
rs = np.random.default_rng(99)
sens = []
for nom, fd, fs in escenarios:
    G["LAMBDA"][:] = [l * fd for l in LAMBDA_BASE]
    G["escala"] = ESCALA_BASE * fs
    mu = 60 / (3.0303 * fs)
    for cnom, mods in (("Propuesta", CONF["Propuesta"]), ("Propuesta + 5.º módulo 10-11", CON_REGLA)):
        # El escenario base de la propuesta reutiliza las mismas réplicas de la Tabla 16
        R = P if (fd, fs, cnom) == (1.0, 1.0, "Propuesta") else resumen(correr(mods, rs), mods)
        k = int(np.argmax(R["franja"]))
        rho = G["LAMBDA"][3] / (mods[3] * mu)
        sens.append((nom, cnom, R["wq"][0], R["wq"][1], 100 * R["pct_global"]))
        ws.append([nom, cnom, round(R["wq"][0], 1), round(R["wq"][1], 1), round(100 * R["pct_global"], 1),
                   round(R["p95"][0], 1), FRANJAS[k], round(R["franja"][k], 1), round(rho, 3)])
        print(f"  {nom:32s} | {cnom:28s} | Wq {f1(R['wq'][0])} ± {f1(R['wq'][1])} | "
              f">{UMBRAL} min {f1(100*R['pct_global'])} % | P95 {f1(R['p95'][0])} | "
              f"peor franja {FRANJAS[k]} = {f1(R['franja'][k])} | ρ(10-11) = {rho:.3f}".replace(".", ",", 0))
G["LAMBDA"][:] = LAMBDA_BASE; G["escala"] = ESCALA_BASE
print()

# ===================================================== 3) COSTO DIARIO
print("3) COSTO DIARIO TOTAL")
ws = wb.create_sheet("3_Costo_diario")
ws.append(["Concepto", "Configuración actual", "Configuración propuesta", "Diferencia"])
hm_a, hm_p = sum(CONF["Actual"]), sum(CONF["Propuesta"])
lineas = [("Horas-módulo por día", hm_a, hm_p),
          ("Costo de servicio (COP/día)", hm_a * C_SERV, hm_p * C_SERV),
          ("Horas de espera de los usuarios por día", A["horas_esp"][0], P["horas_esp"][0]),
          ("Costo de espera (COP/día)", A["horas_esp"][0] * C_ESP, P["horas_esp"][0] * C_ESP),
          ("Costo total (COP/día)", A["costo"][0], P["costo"][0])]
for nom, a, p in lineas:
    ws.append([nom, round(a, 1), round(p, 1), round(p - a, 1)])
    print(f"  {nom}: actual {a:,.1f} | propuesta {p:,.1f} | diferencia {p - a:+,.1f}")
ahorro = A["costo"][0] - P["costo"][0]
print(f"  Ahorro total por día: ${ahorro:,.0f}  ({ahorro / A['costo'][0] * 100:.0f} %)")
print(f"  Por cada peso adicional en módulos se ahorran ${(lineas[3][1]-lineas[3][2]) / (lineas[1][2]-lineas[1][1]):.1f} en espera")
print(f"  Proyección anual (≈ 250 días hábiles): ${ahorro * 250:,.0f}\n")
ws.append(["Ahorro total por día", "", "", round(ahorro)])
ws.append(["Proyección anual (250 días hábiles)", "", "", round(ahorro * 250)])

# ===================================================== 4) TABLA 16 CON INTERVALOS
print("4) TABLA 16 CON INTERVALOS DE CONFIANZA DEL 95 %")
ws = wb.create_sheet("4_Tabla16_IC")
ws.append(["Indicador", "Configuración actual", "Configuración propuesta", "Variación"])
t16 = [("Espera promedio en cola (min)", A["wq"], P["wq"], 1),
       ("Percentil 95 de la espera (min)", A["p95"], P["p95"], 1),
       (f"Usuarios que esperan más de {UMBRAL} min (%)", (100 * A["pct_global"], 100 * A["pct"][1]),
        (100 * P["pct_global"], 100 * P["pct"][1]), 1),
       ("Espera máxima del día (min)", A["wmax"], P["wmax"], 1),
       ("Máximo de usuarios en sala (máximo diario)", A["cmax"], P["cmax"], 1)]
ws.append(["Horas-módulo por día", hm_a, hm_p, f"+{hm_p - hm_a}"])
for nom, a, p, d in t16:
    var = f"{p[0] - a[0]:+.1f} p.p." if "(%)" in nom else f"{(p[0] / a[0] - 1) * 100:+.0f} %"
    ws.append([nom, f"{f1(a[0], d)} ± {f1(a[1], d)}", f"{f1(p[0], d)} ± {f1(p[1], d)}", var])
    print(f"  {nom}: {f1(a[0], d)} ± {f1(a[1], d)} | {f1(p[0], d)} ± {f1(p[1], d)} | {var}")
dif = np.array([w.mean() for w, _, _ in dias_act]) - np.array([w.mean() for w, _, _ in dias_pro])
tt = stats.ttest_ind(np.array([w.mean() for w, _, _ in dias_act]), np.array([w.mean() for w, _, _ in dias_pro]),
                     equal_var=False)
print(f"  Diferencia de la espera promedio: {f1(dif.mean())} min; prueba t de Welch: t = {tt.statistic:.1f}, "
      f"p = {tt.pvalue:.1e}")
ws.append(["Prueba t de Welch (espera promedio)", f"t = {tt.statistic:.1f}", f"p = {tt.pvalue:.1e}"])


# ===================================================== FIGURAS
ROJO, AZUL, GRIS = "#d64545", "#1f3b73", "#9aa5b1"
def limpiar(ax):
    ax.grid(axis="y", color="#e5e5e5", zorder=0)
    for s_ in ("top", "right"): ax.spines[s_].set_visible(False)

# Figura: validación por franja (observado vs simulado)
obs_fr = [obs[obs_f == k].mean() for k in range(10)]
obs_ic = [z * obs[obs_f == k].std(ddof=1) / np.sqrt((obs_f == k).sum()) for k in range(10)]
fig, ax = plt.subplots(figsize=(8, 3.6), dpi=200)
xs = np.arange(10)
ax.bar(xs, A["franja"], width=0.6, color=GRIS, label="Simulado (200 réplicas)", zorder=2)
ax.errorbar(xs, obs_fr, yerr=obs_ic, fmt="o", color=ROJO, ms=6, capsize=3, lw=1.5,
            label="Observado (Registro) e IC 95 %", zorder=3)
ax.set_xticks(xs, FRANJAS)
ax.set_xlabel("Franja de llegada del usuario")
ax.set_ylabel("Espera promedio en cola (min)")
ax.text(0.02, 0.95, f"Correlación = {corr:.3f}".replace(".", ","), transform=ax.transAxes, fontsize=8, va="top")
ax.legend(frameon=False, loc="upper right")
limpiar(ax); fig.tight_layout(); fig.savefig("Figura_validacion_simulacion.png")

# Figura: sensibilidad (espera promedio por escenario)
nombres = [e[0] for e in escenarios]
etiquetas = ["Base", "Demanda\n+5 %", "Demanda\n+10 %", "Demanda\n+15 %", "Servicio\n+10 %", "Demanda y\nservicio +10 %"]
v1 = [next(r for r in sens if r[0] == n and r[1] == "Propuesta") for n in nombres]
v2 = [next(r for r in sens if r[0] == n and r[1] != "Propuesta") for n in nombres]
fig, ax = plt.subplots(figsize=(8, 3.8), dpi=200)
xs = np.arange(len(nombres)); w = 0.38
for off, vv, c, lab in ((-w / 2, v1, ROJO, "Propuesta (Tabla 14)"), (w / 2, v2, AZUL, "Propuesta + 5.º módulo de 10:00 a 11:00")):
    b = ax.bar(xs + off, [r[2] for r in vv], width=w - 0.03, yerr=[r[3] for r in vv], capsize=2,
               color=c, label=lab, zorder=2, error_kw=dict(lw=1, ecolor="#555555"))
    for rect, r in zip(b, vv):
        ax.text(rect.get_x() + rect.get_width() / 2, r[2] + r[3] + 0.3, f"{r[2]:.1f}".replace(".", ","),
                ha="center", fontsize=7, zorder=5, bbox=dict(facecolor="white", edgecolor="none", pad=0.5))
ax.axhline(10, color="black", ls="--", lw=1, zorder=3)
ax.text(3.5, 10.3, "Meta: 10 min", ha="center", fontsize=8, zorder=4)
ax.set_xticks(xs, etiquetas, fontsize=8)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
ax.set_ylabel("Espera promedio en cola (min)")
ax.legend(frameon=False, loc="upper left")
limpiar(ax); fig.tight_layout(); fig.savefig("Figura_sensibilidad.png")

# Figura: costo diario
fig, ax = plt.subplots(figsize=(8, 3.6), dpi=200)
cats = ["Configuración actual", "Configuración propuesta"]
serv = [lineas[1][1] / 1e6, lineas[1][2] / 1e6]; esp = [lineas[3][1] / 1e6, lineas[3][2] / 1e6]
ax.barh(cats, serv, color=AZUL, label="Costo de servicio (módulos)", zorder=2, height=0.5)
ax.barh(cats, esp, left=serv, color="#e8a23a", label="Costo de espera (usuarios)", zorder=2, height=0.5)
for i in range(2):
    ax.text(serv[i] + esp[i] + 0.03, i, f"${serv[i] + esp[i]:.2f} millones".replace(".", ","), va="center", fontsize=8)
ax.set_xlabel("Millones de pesos por día")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",")))
ax.set_xlim(0, (serv[0] + esp[0]) * 1.25)
ax.invert_yaxis()
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="x", color="#e5e5e5", zorder=0)
for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
fig.tight_layout(); fig.savefig("Figura_costo_diario.png")
print("Figuras: Figura_validacion_simulacion.png, Figura_sensibilidad.png, Figura_costo_diario.png")

wb.save("resultados_complementarios.xlsx")
print("\nArchivo: resultados_complementarios.xlsx")
