"""
Figura 4. Factor de utilización por franja horaria con la configuración actual de módulos
Requisitos:  pip install numpy matplotlib
Uso:         python figura4_utilizacion.py     (con tiempos_servicio.csv en la misma carpeta)
"""
import numpy as np
import matplotlib
import matplotlib.ticker
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

x = np.loadtxt("tiempos_servicio.csv", skiprows=1)
mu = 60 / x.mean()                                             # 19,80 usuarios/h por módulo
FRANJAS = ["7:00", "8:00", "9:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
LAMBDA = [89.8, 100.1, 89.1, 73.6, 55.1, 40.3, 48.7, 67.4, 57.3, 34.7]
S = [4, 4, 4, 4, 4, 3, 3, 4, 4, 4]
CRITICO = 0.85

rho = [l / (s * mu) for l, s in zip(LAMBDA, S)]
col = ["#d64545" if r >= 1 else "#e8a23a" if r >= CRITICO else "#1f3b73" for r in rho]

print("Franja | λ | s | capacidad | ρ | condición")
for f, l, s, r in zip(FRANJAS, LAMBDA, S, rho):
    cond = "Inestable" if r >= 1 else "Crítico" if r >= CRITICO else "Estable"
    print(f"{f} | {l} | {s} | {s*mu:.1f} | {r:.3f} | {cond}")

fig, ax = plt.subplots(figsize=(8, 3.8), dpi=200)
b = ax.bar(FRANJAS, rho, color=col, width=0.7, zorder=2)
for rect, r, s in zip(b, rho, S):
    ax.text(rect.get_x() + rect.get_width() / 2, r + 0.02, f"{r:.2f}".replace(".", ","), ha="center", fontsize=8,
            zorder=5, bbox=dict(facecolor="white", edgecolor="none", pad=0.5))
    ax.text(rect.get_x() + rect.get_width() / 2, 0.04, f"s = {s}", ha="center", fontsize=7, color="white")
ax.axhline(1, color="black", lw=1.2, zorder=3)
ax.text(9.45, 1.015, "ρ = 1 (límite de estabilidad)", ha="right", fontsize=8)
ax.axhline(CRITICO, color="black", lw=1, ls="--", zorder=3)
ax.text(9.45, CRITICO + 0.015, "ρ = 0,85 (umbral crítico)", ha="right", fontsize=8)
ax.set_xlabel("Franja horaria")
ax.set_ylabel("Factor de utilización ρ = λ / (s·μ)")
ax.set_ylim(0, 1.4)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.1f}".replace(".", ",")))
ax.legend(handles=[Patch(color="#d64545", label="Inestable (ρ ≥ 1)"),
                   Patch(color="#e8a23a", label="Crítico (0,85 ≤ ρ < 1)"),
                   Patch(color="#1f3b73", label="Estable (ρ < 0,85)")],
          frameon=False, loc="upper right", bbox_to_anchor=(1, 1.02), fontsize=8)
ax.grid(axis="y", color="#e5e5e5", zorder=0)
for s_ in ("top", "right"): ax.spines[s_].set_visible(False)
fig.tight_layout(); fig.savefig("Figura4_factor_utilizacion.png")
print("Archivo: Figura4_factor_utilizacion.png")
