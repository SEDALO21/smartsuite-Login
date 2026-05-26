# 🚀 Guía de Despliegue — SmartSuite con Base de Datos en la Nube

## ✅ Opción Recomendada: Railway + SQLite Persistente (Gratis)

### Por qué Railway:
- Gratis hasta 5$/mes de uso (suficiente para proyectos pequeños)
- Base de datos visible en la web
- Deploy directo desde VS Code con GitHub
- URL pública automática

---

## PASO 1 — Subir a GitHub (desde VS Code)

1. Abre la carpeta `SMARTSUITE-v2` en VS Code
2. Presiona `Ctrl + Shift + P` → escribe **"Git: Initialize Repository"**
3. Haz click en el ícono de **Source Control** (rama izquierda)
4. Escribe un mensaje: `"SmartSuite con login"` y haz commit
5. Haz click en **"Publish to GitHub"**
   - Elige cuenta de GitHub (créala en github.com si no tienes)
   - Ponlo como **Private** si no quieres que sea público

---

## PASO 2 — Crear base de datos en Supabase (PostgreSQL gratis)

1. Ve a **https://supabase.com** → Create a free account
2. Haz click en **New Project**
3. Nombre: `smartsuite-db`, Region: South America (São Paulo)
4. Guarda la **contraseña de la BD** en un lugar seguro
5. Una vez creado, ve a **Settings → Database**
6. Copia la **Connection String (URI)**: empieza con `postgresql://...`

---

## PASO 3 — Adaptar app para PostgreSQL (opcional pero recomendado)

Si quieres PostgreSQL real, instala:
```
pip install psycopg2-binary sqlalchemy
```

Para empezar más fácil, Railway también acepta SQLite con volumen persistente.

---

## PASO 4 — Desplegar en Railway

1. Ve a **https://railway.app** → Login con GitHub
2. Haz click en **New Project → Deploy from GitHub repo**
3. Selecciona tu repo `SMARTSUITE-v2`
4. Railway detecta automáticamente que es Flask (por el Procfile)
5. En **Variables**, agrega:
   - `SECRET_KEY` = `smartsuite2026_mi_clave_secreta`
6. Haz click en **Deploy**
7. En 2 minutos tendrás una URL tipo: `https://smartsuite-production.up.railway.app`

---

## PASO 5 — Ver los datos en la nube

### Opción A: Usar Supabase (PostgreSQL)
- En Supabase → **Table Editor** → ves todas las tablas y registros
- Cada acción que hagas en tu app se refleja ahí en tiempo real

### Opción B: SQLite con DB Browser (local + Railway)
- En Railway puedes ver los logs
- Descarga **DB Browser for SQLite** en tu PC para inspeccionar el .db localmente

---

## 📊 Bases de datos en la nube gratuitas — Comparativa

| Base de datos | Plan gratis | Interfaz web | Facilidad |
|--------------|-------------|--------------|-----------|
| **Supabase** | 500MB, ilimitado | ✅ Excelente | ⭐⭐⭐⭐⭐ |
| **PlanetScale** | 5GB | ✅ Buena | ⭐⭐⭐⭐ |
| **Neon** | 0.5GB | ✅ Buena | ⭐⭐⭐⭐ |
| **Railway DB** | Incluido | ✅ Básica | ⭐⭐⭐ |

**→ Recomendación: Supabase** porque tiene la mejor interfaz web y plan gratuito generoso.

---

## 🔐 Usuarios del sistema

| Correo | Contraseña | Rol |
|--------|------------|-----|
| sergiosantiago@smartsuit.com.co | Admin2026! | Administrador |
| maria.gonzalez@smartsuit.com.co | Trabaja123! | Trabajador |
| juan.perez@smartsuit.com.co | Trabaja123! | Trabajador |

---

## Permisos por rol

### 🔴 Administrador (Sergio Santiago):
- Ver y editar TODO: equipos, empleados, solicitudes, préstamos, mantenimiento
- Aprobar o rechazar solicitudes
- Registrar devoluciones
- Gestionar usuarios del sistema

### 🔵 Trabajador (María / Juan):
- Ver equipos disponibles
- Crear sus propias solicitudes
- Ver el estado de sus solicitudes
- Ver préstamos (solo lectura)
