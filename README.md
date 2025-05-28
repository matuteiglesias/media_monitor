
# 🗞️ Media Monitor

**`media_monitor`** es un sistema liviano de backend para el monitoreo automatizado de medios. Se ejecuta periódicamente en tu máquina, consulta feeds RSS de temas económicos y políticos argentinos, y guarda *digests* de noticias en formato CSV, organizados por ventanas temporales.

Este backend está pensado como **la base para una máquina editorial**: desde aquí se generan inputs estructurados que luego pueden alimentar flujos de análisis, generación de ideas, borradores de artículos, visualizaciones, y contenido enriquecido por IA.

---

## 🚧 Estado actual

* Recolecta artículos desde múltiples RSS temáticos de Google News.
* Ejecuta fetch cada 4 horas (cronjob), y guarda los artículos en `data/rss_slices/` como CSVs.
* Cada corrida aplica *time slicing* (ej. últimas 4h, últimas 2d, semana previa, etc.) según reglas preestablecidas.
* Las ventanas están diseñadas para capturar distintos ritmos del ciclo noticioso.

---

## 📁 Estructura del proyecto

```
media_monitor/
├── digests.py                # Script principal: fetch RSS y aplicar slices temporales
├── dev.ipynb / test.ipynb    # Notebooks de prueba y desarrollo
├── data/
│   └── rss_slices/           # Carpeta donde se guardan los CSV por ventana temporal
├── .gitignore
└── README.md
```

---

## 🕰️ Cron job sugerido

Ejecuta el script cada 4 horas (ejemplo con Anaconda):

```
0 */4 * * * cd /home/matias/Documents/media_monitor && /home/matias/anaconda3/bin/python digests.py
```

Esto garantiza que el sistema:

* Se mantenga activo de forma autónoma
* Vaya acumulando fragmentos informativos a lo largo del tiempo

---

## ✨ Futuras extensiones (planeadas)

* Análisis de menciones por entidad o personaje
* Generación automática de resúmenes y visualizaciones
* Inyección en CMS con plantillas de contenido
* Ilustración automática con imágenes generadas por IA
* Integración con sistemas de clasificación y etiquetado

---

## 🔧 Requisitos

* Python 3.9+
* Librerías: `feedparser`, `pandas`, `csv`, `datetime`

Instalación sugerida:

```bash
pip install -r requirements.txt
```

---

## 📬 Contacto

Para sugerencias o mejoras, contactá a [Matías Iglesias](https://github.com/matuteiglesias).

---

¿Querés que también te genere un `requirements.txt` básico y un badge para GitHub Actions si pensás desplegarlo en un servidor más adelante?
