from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from functools import wraps
import sqlite3
import os
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'smartsuite2026_secret_key_segura'

DB_PATH = 'smartsuite.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS USUARIO (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            correo TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'trabajador'
                CHECK(rol IN ('admin','trabajador')),
            activo INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS TIPO_EQUIPO (
            id_tipo INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL CHECK(nombre IN ('celular','impresora','lector')),
            descripcion TEXT
        );

        CREATE TABLE IF NOT EXISTS EMPLEADO (
            id_empleado INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cargo TEXT NOT NULL,
            area TEXT,
            correo TEXT NOT NULL UNIQUE,
            telefono TEXT
        );

        CREATE TABLE IF NOT EXISTS EQUIPO (
            id_equipo INTEGER PRIMARY KEY AUTOINCREMENT,
            id_tipo INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            marca TEXT,
            numero_serie TEXT NOT NULL UNIQUE,
            estado TEXT NOT NULL DEFAULT 'disponible'
                CHECK(estado IN ('disponible','prestado','en_mantenimiento')),
            FOREIGN KEY (id_tipo) REFERENCES TIPO_EQUIPO(id_tipo)
        );

        CREATE TABLE IF NOT EXISTS SOLICITUD (
            id_solicitud INTEGER PRIMARY KEY AUTOINCREMENT,
            id_empleado INTEGER NOT NULL,
            id_equipo INTEGER NOT NULL,
            id_supervisor INTEGER,
            fecha_solicitud TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            fecha_estimada_dev TEXT NOT NULL,
            estado_solicitud TEXT NOT NULL DEFAULT 'pendiente'
                CHECK(estado_solicitud IN ('pendiente','aprobada','rechazada')),
            motivo TEXT,
            FOREIGN KEY (id_empleado) REFERENCES EMPLEADO(id_empleado),
            FOREIGN KEY (id_equipo) REFERENCES EQUIPO(id_equipo),
            FOREIGN KEY (id_supervisor) REFERENCES EMPLEADO(id_empleado)
        );

        CREATE TABLE IF NOT EXISTS PRESTAMO (
            id_prestamo INTEGER PRIMARY KEY AUTOINCREMENT,
            id_solicitud INTEGER NOT NULL UNIQUE,
            fecha_entrega TEXT NOT NULL,
            fecha_devolucion_real TEXT,
            estado_prestamo TEXT NOT NULL DEFAULT 'activo'
                CHECK(estado_prestamo IN ('activo','cerrado','vencido')),
            FOREIGN KEY (id_solicitud) REFERENCES SOLICITUD(id_solicitud)
        );

        CREATE TABLE IF NOT EXISTS DEVOLUCION (
            id_devolucion INTEGER PRIMARY KEY AUTOINCREMENT,
            id_prestamo INTEGER NOT NULL UNIQUE,
            fecha_devolucion TEXT NOT NULL,
            estado_equipo_devuelto TEXT NOT NULL
                CHECK(estado_equipo_devuelto IN ('buen_estado','con_danos')),
            observaciones TEXT,
            FOREIGN KEY (id_prestamo) REFERENCES PRESTAMO(id_prestamo)
        );

        CREATE TABLE IF NOT EXISTS MANTENIMIENTO (
            id_mantenimiento INTEGER PRIMARY KEY AUTOINCREMENT,
            id_equipo INTEGER NOT NULL,
            fecha_entrada TEXT NOT NULL,
            fecha_salida TEXT,
            descripcion_falla TEXT,
            tecnico TEXT,
            FOREIGN KEY (id_equipo) REFERENCES EQUIPO(id_equipo)
        );
    ''')

    # Usuarios iniciales
    if c.execute("SELECT COUNT(*) FROM USUARIO").fetchone()[0] == 0:
        usuarios = [
            ('Sergio Santiago', 'sergiosantiago@smartsuit.com.co', generate_password_hash('Admin2026!'), 'admin'),
            ('María González', 'maria.gonzalez@smartsuit.com.co', generate_password_hash('Trabaja123!'), 'trabajador'),
            ('Juan Pérez', 'juan.perez@smartsuit.com.co', generate_password_hash('Trabaja123!'), 'trabajador'),
        ]
        c.executemany(
            "INSERT INTO USUARIO (nombre, correo, password_hash, rol) VALUES (?,?,?,?)",
            usuarios
        )

    # Datos iniciales si la BD está vacía
    if c.execute("SELECT COUNT(*) FROM TIPO_EQUIPO").fetchone()[0] == 0:
        c.executescript('''
            INSERT INTO TIPO_EQUIPO (nombre, descripcion) VALUES
                ('celular','Teléfonos corporativos para uso en campo'),
                ('impresora','Impresoras portátiles para documentos en sitio'),
                ('lector','Lectores de código de barras y QR');

            INSERT INTO EMPLEADO (nombre, cargo, area, correo, telefono) VALUES
                ('Sergio Santiago','Administrador TI','Tecnología','sergiosantiago@smartsuit.com.co','3001234567'),
                ('María González','Técnica Soporte','Soporte','maria.gonzalez@smartsuit.com.co','3009876543'),
                ('Juan Pérez','Ejecutivo Ventas','Ventas','juan.perez@smartsuit.com.co','3012345678'),
                ('Diana Moreno','Ejecutiva Ventas','Ventas','d.moreno@smartsuit.com.co','3023456789'),
                ('Felipe Torres','Gerente Operaciones','Operaciones','f.torres@smartsuit.com.co','3034567890');

            INSERT INTO EQUIPO (id_tipo, nombre, marca, numero_serie, estado) VALUES
                (1,'Galaxy A52','Samsung','SS-A52-001','disponible'),
                (1,'iPhone 13','Apple','AP-I13-002','disponible'),
                (2,'OfficeJet 250','HP','HP-OJ-003','disponible'),
                (3,'Symbol DS2208','Zebra','ZB-DS2-004','disponible'),
                (2,'WorkForce WF-100','Epson','EP-WF-005','disponible'),
                (3,'Honeywell 1900','Honeywell','HW-19-007','disponible');
        ''')

    conn.commit()
    conn.close()

# ── DECORADORES DE AUTENTICACIÓN ──────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder.', 'warning')
            return redirect(url_for('login'))
        if session.get('rol') != 'admin':
            flash('No tienes permisos para realizar esta acción.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ── AUTENTICACIÓN ──────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip().lower()
        password = request.form.get('password', '')
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM USUARIO WHERE correo=? AND activo=1", (correo,)
        ).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id_usuario']
            session['nombre'] = user['nombre']
            session['correo'] = user['correo']
            session['rol'] = user['rol']
            flash(f'Bienvenido, {user["nombre"]} 👋', 'success')
            return redirect(url_for('index'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('login'))

# ── DASHBOARD ──────────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    conn = get_db()
    stats = {
        'disponibles': conn.execute("SELECT COUNT(*) FROM EQUIPO WHERE estado='disponible'").fetchone()[0],
        'prestados':   conn.execute("SELECT COUNT(*) FROM EQUIPO WHERE estado='prestado'").fetchone()[0],
        'mantenimiento': conn.execute("SELECT COUNT(*) FROM EQUIPO WHERE estado='en_mantenimiento'").fetchone()[0],
        'solicitudes_pendientes': conn.execute("SELECT COUNT(*) FROM SOLICITUD WHERE estado_solicitud='pendiente'").fetchone()[0],
        'prestamos_activos': conn.execute("SELECT COUNT(*) FROM PRESTAMO WHERE estado_prestamo='activo'").fetchone()[0],
    }
    vencidos = conn.execute("""
        SELECT COUNT(*) FROM PRESTAMO p
        JOIN SOLICITUD s ON p.id_solicitud = s.id_solicitud
        WHERE p.estado_prestamo='activo'
          AND s.fecha_estimada_dev < date('now','localtime')
    """).fetchone()[0]
    stats['vencidos'] = vencidos

    # Trabajador solo ve sus propias solicitudes
    if session.get('rol') == 'trabajador':
        emp = conn.execute(
            "SELECT id_empleado FROM EMPLEADO WHERE correo=?", (session['correo'],)
        ).fetchone()
        emp_id = emp['id_empleado'] if emp else -1
        ultimas = conn.execute("""
            SELECT s.id_solicitud, e.nombre as empleado, eq.nombre as equipo,
                   s.fecha_solicitud, s.estado_solicitud
            FROM SOLICITUD s
            JOIN EMPLEADO e ON s.id_empleado = e.id_empleado
            JOIN EQUIPO eq ON s.id_equipo = eq.id_equipo
            WHERE s.id_empleado = ?
            ORDER BY s.id_solicitud DESC LIMIT 5
        """, (emp_id,)).fetchall()
    else:
        ultimas = conn.execute("""
            SELECT s.id_solicitud, e.nombre as empleado, eq.nombre as equipo,
                   s.fecha_solicitud, s.estado_solicitud
            FROM SOLICITUD s
            JOIN EMPLEADO e ON s.id_empleado = e.id_empleado
            JOIN EQUIPO eq ON s.id_equipo = eq.id_equipo
            ORDER BY s.id_solicitud DESC LIMIT 5
        """).fetchall()
    conn.close()
    return render_template('index.html', stats=stats, ultimas=ultimas)

# ── EQUIPOS ────────────────────────────────────────────────────────────────────

@app.route('/equipos')
@login_required
def equipos():
    conn = get_db()
    filas = conn.execute("""
        SELECT eq.*, t.nombre as tipo_nombre
        FROM EQUIPO eq JOIN TIPO_EQUIPO t ON eq.id_tipo = t.id_tipo
        ORDER BY eq.id_equipo
    """).fetchall()
    tipos = conn.execute("SELECT * FROM TIPO_EQUIPO").fetchall()
    conn.close()
    return render_template('equipos.html', equipos=filas, tipos=tipos)

@app.route('/equipos/nuevo', methods=['POST'])
@admin_required
def nuevo_equipo():
    d = request.form
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO EQUIPO (id_tipo, nombre, marca, numero_serie, estado)
            VALUES (?,?,?,?,?)
        """, (d['id_tipo'], d['nombre'], d['marca'], d['numero_serie'], 'disponible'))
        conn.commit()
        flash('Equipo registrado exitosamente ✔', 'success')
    except sqlite3.IntegrityError:
        flash('El número de serie ya existe.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('equipos'))

@app.route('/equipos/editar/<int:id>', methods=['POST'])
@admin_required
def editar_equipo(id):
    d = request.form
    conn = get_db()
    conn.execute("""
        UPDATE EQUIPO SET nombre=?, marca=?, estado=?
        WHERE id_equipo=?
    """, (d['nombre'], d['marca'], d['estado'], id))
    conn.commit()
    conn.close()
    flash('Equipo actualizado ✔', 'success')
    return redirect(url_for('equipos'))

@app.route('/equipos/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_equipo(id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM EQUIPO WHERE id_equipo=?", (id,))
        conn.commit()
        flash('Equipo eliminado ✔', 'success')
    except sqlite3.IntegrityError:
        flash('No se puede eliminar: el equipo tiene préstamos o solicitudes asociadas.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('equipos'))

# ── EMPLEADOS ──────────────────────────────────────────────────────────────────

@app.route('/empleados')
@login_required
def empleados():
    conn = get_db()
    filas = conn.execute("SELECT * FROM EMPLEADO ORDER BY id_empleado").fetchall()
    conn.close()
    return render_template('empleados.html', empleados=filas)

@app.route('/empleados/nuevo', methods=['POST'])
@admin_required
def nuevo_empleado():
    d = request.form
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO EMPLEADO (nombre, cargo, area, correo, telefono)
            VALUES (?,?,?,?,?)
        """, (d['nombre'], d['cargo'], d['area'], d['correo'], d['telefono']))
        conn.commit()
        flash('Empleado registrado ✔', 'success')
    except sqlite3.IntegrityError:
        flash('El correo ya está registrado.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('empleados'))

@app.route('/empleados/editar/<int:id>', methods=['POST'])
@admin_required
def editar_empleado(id):
    d = request.form
    conn = get_db()
    conn.execute("""
        UPDATE EMPLEADO SET nombre=?, cargo=?, area=?, correo=?, telefono=?
        WHERE id_empleado=?
    """, (d['nombre'], d['cargo'], d['area'], d['correo'], d['telefono'], id))
    conn.commit()
    conn.close()
    flash('Empleado actualizado ✔', 'success')
    return redirect(url_for('empleados'))

@app.route('/empleados/eliminar/<int:id>', methods=['POST'])
@admin_required
def eliminar_empleado(id):
    conn = get_db()
    try:
        conn.execute("DELETE FROM EMPLEADO WHERE id_empleado=?", (id,))
        conn.commit()
        flash('Empleado eliminado ✔', 'success')
    except sqlite3.IntegrityError:
        flash('No se puede eliminar: el empleado tiene solicitudes asociadas.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('empleados'))

# ── SOLICITUDES ────────────────────────────────────────────────────────────────

@app.route('/solicitudes')
@login_required
def solicitudes():
    conn = get_db()
    if session.get('rol') == 'trabajador':
        emp = conn.execute(
            "SELECT id_empleado FROM EMPLEADO WHERE correo=?", (session['correo'],)
        ).fetchone()
        emp_id = emp['id_empleado'] if emp else -1
        filas = conn.execute("""
            SELECT s.*,
                   e.nombre  as empleado_nombre,
                   eq.nombre as equipo_nombre,
                   sup.nombre as supervisor_nombre
            FROM SOLICITUD s
            JOIN EMPLEADO e   ON s.id_empleado  = e.id_empleado
            JOIN EQUIPO eq    ON s.id_equipo    = eq.id_equipo
            LEFT JOIN EMPLEADO sup ON s.id_supervisor = sup.id_empleado
            WHERE s.id_empleado = ?
            ORDER BY s.id_solicitud DESC
        """, (emp_id,)).fetchall()
    else:
        filas = conn.execute("""
            SELECT s.*,
                   e.nombre  as empleado_nombre,
                   eq.nombre as equipo_nombre,
                   sup.nombre as supervisor_nombre
            FROM SOLICITUD s
            JOIN EMPLEADO e   ON s.id_empleado  = e.id_empleado
            JOIN EQUIPO eq    ON s.id_equipo    = eq.id_equipo
            LEFT JOIN EMPLEADO sup ON s.id_supervisor = sup.id_empleado
            ORDER BY s.id_solicitud DESC
        """).fetchall()
    empleados_list = conn.execute("SELECT * FROM EMPLEADO").fetchall()
    equipos_list   = conn.execute("SELECT * FROM EQUIPO WHERE estado='disponible'").fetchall()
    conn.close()
    return render_template('solicitudes.html', solicitudes=filas,
                           empleados=empleados_list, equipos=equipos_list)

@app.route('/solicitudes/nueva', methods=['POST'])
@login_required
def nueva_solicitud():
    d = request.form
    conn = get_db()
    eq = conn.execute("SELECT estado FROM EQUIPO WHERE id_equipo=?", (d['id_equipo'],)).fetchone()
    if not eq or eq['estado'] != 'disponible':
        flash('El equipo no está disponible.', 'danger')
        conn.close()
        return redirect(url_for('solicitudes'))
    activos = conn.execute("""
        SELECT COUNT(*) FROM PRESTAMO p
        JOIN SOLICITUD s ON p.id_solicitud = s.id_solicitud
        WHERE s.id_empleado=? AND p.estado_prestamo='activo'
    """, (d['id_empleado'],)).fetchone()[0]
    if activos >= 3:
        flash('El empleado ya tiene 3 préstamos activos.', 'danger')
        conn.close()
        return redirect(url_for('solicitudes'))
    conn.execute("""
        INSERT INTO SOLICITUD (id_empleado, id_equipo, id_supervisor,
                               fecha_estimada_dev, motivo)
        VALUES (?,?,?,?,?)
    """, (d['id_empleado'], d['id_equipo'],
          d.get('id_supervisor') or None,
          d['fecha_estimada_dev'], d.get('motivo','')))
    conn.commit()
    conn.close()
    flash('Solicitud registrada ✔', 'success')
    return redirect(url_for('solicitudes'))

@app.route('/solicitudes/aprobar/<int:id>')
@admin_required
def aprobar_solicitud(id):
    conn = get_db()
    sol = conn.execute("SELECT * FROM SOLICITUD WHERE id_solicitud=?", (id,)).fetchone()
    if sol and sol['estado_solicitud'] == 'pendiente':
        conn.execute("UPDATE SOLICITUD SET estado_solicitud='aprobada' WHERE id_solicitud=?", (id,))
        conn.execute("""
            INSERT INTO PRESTAMO (id_solicitud, fecha_entrega, estado_prestamo)
            VALUES (?, datetime('now','localtime'), 'activo')
        """, (id,))
        conn.execute("UPDATE EQUIPO SET estado='prestado' WHERE id_equipo=?", (sol['id_equipo'],))
        conn.commit()
        flash('Solicitud aprobada y préstamo creado ✔', 'success')
    conn.close()
    return redirect(url_for('solicitudes'))

@app.route('/solicitudes/rechazar/<int:id>')
@admin_required
def rechazar_solicitud(id):
    conn = get_db()
    conn.execute("UPDATE SOLICITUD SET estado_solicitud='rechazada' WHERE id_solicitud=?", (id,))
    conn.commit()
    conn.close()
    flash('Solicitud rechazada.', 'warning')
    return redirect(url_for('solicitudes'))

# ── PRÉSTAMOS ──────────────────────────────────────────────────────────────────

@app.route('/prestamos')
@login_required
def prestamos():
    conn = get_db()
    filas = conn.execute("""
        SELECT p.*, s.fecha_estimada_dev,
               e.nombre as empleado_nombre,
               eq.nombre as equipo_nombre,
               eq.id_equipo,
               (SELECT id_devolucion FROM DEVOLUCION d WHERE d.id_prestamo=p.id_prestamo) as devuelto
        FROM PRESTAMO p
        JOIN SOLICITUD s ON p.id_solicitud = s.id_solicitud
        JOIN EMPLEADO e  ON s.id_empleado  = e.id_empleado
        JOIN EQUIPO eq   ON s.id_equipo    = eq.id_equipo
        ORDER BY p.id_prestamo DESC
    """).fetchall()
    hoy = date.today().isoformat()
    conn.close()
    return render_template('prestamos.html', prestamos=filas, hoy=hoy)

@app.route('/prestamos/devolver/<int:id>', methods=['POST'])
@admin_required
def devolver_prestamo(id):
    d = request.form
    conn = get_db()
    p = conn.execute("""
        SELECT p.*, s.id_equipo FROM PRESTAMO p
        JOIN SOLICITUD s ON p.id_solicitud=s.id_solicitud
        WHERE p.id_prestamo=?
    """, (id,)).fetchone()
    if p:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("""
            INSERT INTO DEVOLUCION (id_prestamo, fecha_devolucion,
                                    estado_equipo_devuelto, observaciones)
            VALUES (?,?,?,?)
        """, (id, now, d['estado_equipo'], d.get('observaciones','')))
        conn.execute("""
            UPDATE PRESTAMO SET estado_prestamo='cerrado', fecha_devolucion_real=?
            WHERE id_prestamo=?
        """, (now, id))
        nuevo_estado = 'disponible' if d['estado_equipo'] == 'buen_estado' else 'en_mantenimiento'
        conn.execute("UPDATE EQUIPO SET estado=? WHERE id_equipo=?",
                     (nuevo_estado, p['id_equipo']))
        conn.commit()
        flash('Devolución registrada ✔', 'success')
    conn.close()
    return redirect(url_for('prestamos'))

# ── MANTENIMIENTO ──────────────────────────────────────────────────────────────

@app.route('/mantenimiento')
@login_required
def mantenimiento():
    conn = get_db()
    filas = conn.execute("""
        SELECT m.*, eq.nombre as equipo_nombre
        FROM MANTENIMIENTO m
        JOIN EQUIPO eq ON m.id_equipo = eq.id_equipo
        ORDER BY m.id_mantenimiento DESC
    """).fetchall()
    equipos_mant = conn.execute(
        "SELECT * FROM EQUIPO WHERE estado='en_mantenimiento'"
    ).fetchall()
    conn.close()
    return render_template('mantenimiento.html', registros=filas,
                           equipos_mant=equipos_mant)

@app.route('/mantenimiento/nuevo', methods=['POST'])
@admin_required
def nuevo_mantenimiento():
    d = request.form
    conn = get_db()
    conn.execute("""
        INSERT INTO MANTENIMIENTO (id_equipo, fecha_entrada, descripcion_falla, tecnico)
        VALUES (?, datetime('now','localtime'), ?, ?)
    """, (d['id_equipo'], d.get('descripcion',''), d.get('tecnico','')))
    conn.execute("UPDATE EQUIPO SET estado='en_mantenimiento' WHERE id_equipo=?",
                 (d['id_equipo'],))
    conn.commit()
    conn.close()
    flash('Equipo enviado a mantenimiento ✔', 'success')
    return redirect(url_for('mantenimiento'))

@app.route('/mantenimiento/cerrar/<int:id>')
@admin_required
def cerrar_mantenimiento(id):
    conn = get_db()
    m = conn.execute("SELECT * FROM MANTENIMIENTO WHERE id_mantenimiento=?", (id,)).fetchone()
    if m:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute("UPDATE MANTENIMIENTO SET fecha_salida=? WHERE id_mantenimiento=?", (now, id))
        conn.execute("UPDATE EQUIPO SET estado='disponible' WHERE id_equipo=?", (m['id_equipo'],))
        conn.commit()
        flash('Equipo dado de alta del mantenimiento ✔', 'success')
    conn.close()
    return redirect(url_for('mantenimiento'))

# ── GESTIÓN DE USUARIOS (solo admin) ──────────────────────────────────────────

@app.route('/usuarios')
@admin_required
def usuarios():
    conn = get_db()
    filas = conn.execute("SELECT id_usuario, nombre, correo, rol, activo FROM USUARIO ORDER BY id_usuario").fetchall()
    conn.close()
    return render_template('usuarios.html', usuarios=filas)

@app.route('/usuarios/nuevo', methods=['POST'])
@admin_required
def nuevo_usuario():
    d = request.form
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO USUARIO (nombre, correo, password_hash, rol)
            VALUES (?,?,?,?)
        """, (d['nombre'], d['correo'].lower(), generate_password_hash(d['password']), d['rol']))
        conn.commit()
        flash('Usuario creado ✔', 'success')
    except sqlite3.IntegrityError:
        flash('El correo ya está registrado.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('usuarios'))

@app.route('/usuarios/toggle/<int:id>')
@admin_required
def toggle_usuario(id):
    conn = get_db()
    u = conn.execute("SELECT activo FROM USUARIO WHERE id_usuario=?", (id,)).fetchone()
    if u:
        conn.execute("UPDATE USUARIO SET activo=? WHERE id_usuario=?", (0 if u['activo'] else 1, id))
        conn.commit()
        flash('Estado del usuario actualizado ✔', 'success')
    conn.close()
    return redirect(url_for('usuarios'))

@app.context_processor
def inject_globals():
    return {
        'now': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'current_user': {
            'nombre': session.get('nombre', ''),
            'correo': session.get('correo', ''),
            'rol': session.get('rol', ''),
        }
    }

init_db()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
