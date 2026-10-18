"""
6.3 a 6.6 Aplicación de los modelos de colas a los escenarios de la jornada
  - M/M/1  (filas independientes por módulo, servicio exponencial)
  - M/G/1  (filas independientes, servicio general: Pollaczek-Khinchine)
  - M/M/s  (fila única, Erlang C)
  - M/M/s corregido (Allen-Cunneen, fila única con la variabilidad real del servicio)

Requisitos:  pip install numpy openpyxl
Uso:         python modelos_colas.py     (con tiempos_servicio.csv en la misma carpeta)
"""
import math
import numpy as np
import openpyxl

# ------------------------------------------------------------ ENTRADAS
x = np.loadtxt("tiempos_servicio.csv", skiprows=1)
media = x.mean()                 # min
sigma = x.std(ddof=1)            # min
mu = 60 / media                  # usuarios/h por módulo
cs2 = (sigma / media) ** 2       # coeficiente de variación al cuadrado del servicio

# Escenarios: (nombre, λ del sistema en usuarios/h, módulos s)
ESCENARIOS = [
    ("Hora valle", 34.7, 3),
    ("Demanda promedio", 65.6, 4),    # 656,1 usuarios/día / 10 h ≈ 65,6
    ("Hora pico", 100.1, 6),
]


# ------------------------------------------------------------ MODELOS
def mm1(lam, s):
    l = lam / s; r = l / mu
    if r >= 1: return None
    lq = r ** 2 / (1 - r)
    return dict(lam_mod=l, rho=r, P0=1 - r, Lq_mod=lq, Lq=lq * s, L=(lq + r) * s,
                Wq=lq / l * 60, W=(lq / l + 1 / mu) * 60, Pw=r)


def mg1(lam, s):
    l = lam / s; r = l / mu
    if r >= 1: return None
    var_h = (sigma / 60) ** 2                                  # varianza del servicio en h²
    lq = (l ** 2 * var_h + r ** 2) / (2 * (1 - r))             # Pollaczek-Khinchine
    return dict(lam_mod=l, rho=r, P0=1 - r, Lq_mod=lq, Lq=lq * s, L=(lq + r) * s,
                Wq=lq / l * 60, W=(lq / l + 1 / mu) * 60, Pw=r)


def mms(lam, s):
    a = lam / mu; r = a / s
    if r >= 1: return None
    suma = sum(a ** n / math.factorial(n) for n in range(s))
    ultimo = a ** s / (math.factorial(s) * (1 - r))
    P0 = 1 / (suma + ultimo)
    Pw = ultimo * P0                                            # Erlang C
    lq = Pw * r / (1 - r)
    return dict(lam_mod=lam, rho=r, P0=P0, Lq_mod=None, Lq=lq, L=lq + a,
                Wq=lq / lam * 60, W=(lq / lam + 1 / mu) * 60, Pw=Pw)


def allen_cunneen(lam, s):
    base = mms(lam, s)
    if base is None: return None
    f = (1 + cs2) / 2                                           # ca² = 1 (llegadas de Poisson)
    lq = base["Lq"] * f
    a = lam / mu
    return dict(lam_mod=lam, rho=base["rho"], P0=base["P0"], Lq_mod=None, Lq=lq, L=lq + a,
                Wq=lq / lam * 60, W=(lq / lam + 1 / mu) * 60, Pw=base["Pw"])


MODELOS = [("M/M/1", mm1), ("M/G/1", mg1), ("M/M/s", mms), ("M/M/s Allen-Cunneen", allen_cunneen)]
FILAS = [("λ de la cola (usuarios/h)", "lam_mod", 2), ("μ por módulo (usuarios/h)", "mu", 2),
         ("Factor de utilización ρ", "rho", 3), ("Probabilidad de sistema vacío P₀", "P0", 3),
         ("Lq por módulo (usuarios)", "Lq_mod", 2), ("Lq total en la sede (usuarios)", "Lq", 2),
         ("L total en la sede (usuarios)", "L", 2), ("Wq: espera en cola (min)", "Wq", 2),
         ("W: tiempo en el sistema (min)", "W", 2), ("Pw: probabilidad de esperar", "Pw", 3)]

# ------------------------------------------------------------ RESULTADOS
print(f"Servicio: media = {media:.4f} min, σ = {sigma:.4f} min, μ = {mu:.4f} usuarios/h, Cs² = {cs2:.4f}\n")
wb = openpyxl.Workbook(); wb.remove(wb.active)
for nombre_m, f in MODELOS:
    ws = wb.create_sheet(nombre_m.replace("/", "")[:31])
    cab = ["Indicador"] + [f"{n} (λ = {l}; s = {s})" for n, l, s in ESCENARIOS]
    ws.append(cab)
    res = [f(l, s) for _, l, s in ESCENARIOS]
    print(f"MODELO {nombre_m}")
    print("  " + " | ".join(cab))
    for etiqueta, clave, dec in FILAS:
        if clave == "Lq_mod" and nombre_m.startswith("M/M/s"):
            continue
        vals = []
        for r in res:
            if r is None: vals.append("Inestable")
            elif clave == "mu": vals.append(round(mu, dec))
            else: vals.append(round(r[clave], dec))
        ws.append([etiqueta] + vals)
        print("  " + etiqueta + " | " + " | ".join(str(v).replace(".", ",") for v in vals))
    print()
wb.save("resultados_modelos.xlsx")
print("Archivo: resultados_modelos.xlsx (una hoja por modelo)")
