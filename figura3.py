"""
Figura 3. Llegadas promedio por franja horaria frente a la capacidad instalada actual.
Las barras de error indican una desviación estándar entre días.

Requisitos:  pip install numpy matplotlib openpyxl
Uso:         python figura3.py     (con Datos_Audifarma.xlsx y tiempos_servicio.csv en la misma carpeta)
"""
import numpy as np
import openpyxl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Datos: llegadas de los 10 días por franja (hoja Llegadas)
ws = openpyxl.load_workbook("Datos_Audifarma.xlsx")["Llegadas"]
C = np.array([[ws.cell(5 + d, 2 + f).value for f in range(10)] for d in range(10)], float)
lam = C.mean(axis=0)
de = C.std(axis=0, ddof=1)

# Capacidad instalada actual: módulos por franja × μ
S = [4, 4, 4, 4, 4, 3, 3, 4, 4, 4]
mu = 60 / np.loadtxt("tiempos_servicio.csv", skiprows=1).mean()
cap = np.array(S) * mu

HORAS = ["7:00", "8:00", "9:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
xs = np.arange(10)

fig, ax = plt.subplots(figsize=(8, 3.6), dpi=200)
ax.bar(xs, lam, width=0.8, color="#3b7fb8", yerr=de, capsize=3,
       error_kw=dict(ecolor="#333333", lw=1), label="Llegadas promedio (usuarios/h)", zorder=2)
ax.step(np.r_[xs - 0.5, 9.5], np.r_[cap, cap[-1]], where="post", color="#8e6bbf", lw=2,
        label="Capacidad instalada actual (s·μ)", zorder=3)

ax.set_xticks(xs, HORAS)
ax.set_xlabel("Inicio de la franja horaria")
ax.set_ylabel("Usuarios por hora")
ax.set_ylim(0, 115)
ax.legend(frameon=True, fontsize=8, loc="upper right")
ax.grid(axis="y", color="#e5e5e5", zorder=0)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
fig.tight_layout()
fig.savefig("Figura3_llegadas_vs_capacidad.png")
print("Archivo: Figura3_llegadas_vs_capacidad.png")
