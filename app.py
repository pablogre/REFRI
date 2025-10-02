from flask import Flask, render_template, request, redirect, url_for, flash, session
import pymysql
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'mi_clave_super_secreta_4567_multiempresa'

# Agrega estas líneas inmediatamente después de secret_key
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600

# Configuración de la base de datos
def get_db_connection():
    try:
        return pymysql.connect(
            host='localhost',
            user='root',
            password='',
            db='refri',
            cursorclass=pymysql.cursors.DictCursor,
            charset='utf8mb4',
            autocommit=True,
            connect_timeout=10,
            read_timeout=10,
            write_timeout=10
        )
    except Exception as e:
        print(f"Error de conexión: {e}")
        raise

# Decorador para requerir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"Sesión: {dict(session)}")  # Ver contenido de sesión
        
        if 'user_id' not in session or 'user_name' not in session:
            flash('Debe iniciar sesión para acceder')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Función para obtener el usuario actual
def get_current_user_id():
    return session.get('user_id')

def get_current_user_name():
    return session.get('user_name')

def get_current_empresa():
    return session.get('empresa')

# ==================== RUTAS PRINCIPALES ====================
@app.route('/')
def index():
    # Si ya está logueado, ir a clientes
    if 'user_id' in session:
        return redirect(url_for('clientes'))
    # Si no está logueado, ir al login
    return redirect(url_for('login'))

# ==================== AUTENTICACIÓN ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id_usuario, usuario, password, empresa, activo 
                FROM usuarios 
                WHERE usuario = %s AND password = %s AND activo = 1
            """, (usuario, password))
            user = cursor.fetchone()
            
            if user:
                session['user_id'] = user['id_usuario']
                session['user_name'] = user['usuario']
                session['empresa'] = user['empresa']
                
                cursor.execute("""
                    UPDATE usuarios SET ultimo_acceso = NOW() 
                    WHERE id_usuario = %s
                """, (user['id_usuario'],))
                
                conn.close()
                flash(f'Bienvenido {user["usuario"]} - {user["empresa"]}')
                return redirect(url_for('clientes'))
            else:
                conn.close()
                flash('Usuario o contraseña incorrectos')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Sesión cerrada correctamente')
    return redirect(url_for('login'))

# ==================== CLIENTES ====================
@app.route('/clientes')
@login_required
def clientes():
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT c.*, COUNT(e.id_equipo) as total_equipos 
            FROM clientes c 
            LEFT JOIN equipos e ON c.id_cli = e.id_cli 
            WHERE c.id_usuario = %s
            GROUP BY c.id_cli
            ORDER BY c.cliente
        """, (user_id,))
        clientes = cursor.fetchall()
    conn.close()
    return render_template('clientes.html', clientes=clientes)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_cliente():
    if request.method == 'POST':
        user_id = get_current_user_id()
        preventivo = 1 if 'preventivo' in request.form else 0
        
        fecha_mant = request.form.get('fecha_mant')
        if preventivo and not fecha_mant:
            from datetime import date
            fecha_mant = date.today().strftime('%Y-%m-%d')
        
        datos = (
            user_id,
            request.form['cliente'],
            request.form['direccion'],
            request.form['localidad'],
            request.form['tel1'],
            request.form['tel2'],
            request.form['cuit'],
            request.form['obs'],
            preventivo,
            int(request.form.get('dias', 0)) if preventivo and request.form.get('dias') else None,
            fecha_mant if preventivo else None,
            float(request.form.get('importe', 0)) if preventivo and request.form.get('importe') else None
        )
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO clientes (id_usuario, cliente, direccion, localidad, tel1, tel2, cuit, obs, preventivo, dias, fecha_mant, importe)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, datos)
        conn.close()
        flash("Cliente agregado correctamente")
        return redirect(url_for('clientes'))
    return render_template('cliente_form.html', cliente=None)

@app.route('/clientes/editar/<int:id_cli>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id_cli):
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        if request.method == 'POST':
            cursor.execute("SELECT id_cli FROM clientes WHERE id_cli = %s AND id_usuario = %s", (id_cli, user_id))
            if not cursor.fetchone():
                flash("No tiene permisos para editar este cliente")
                return redirect(url_for('clientes'))
            
            preventivo = 1 if 'preventivo' in request.form else 0
            fecha_mant = request.form.get('fecha_mant')
            if preventivo and not fecha_mant:
                from datetime import date
                fecha_mant = date.today().strftime('%Y-%m-%d')
            
            datos = (
                request.form['cliente'],
                request.form['direccion'],
                request.form['localidad'],
                request.form['tel1'],
                request.form['tel2'],
                request.form['cuit'],
                request.form['obs'],
                preventivo,
                int(request.form.get('dias', 0)) if preventivo and request.form.get('dias') else None,
                fecha_mant if preventivo else None,
                float(request.form.get('importe', 0)) if preventivo and request.form.get('importe') else None,
                id_cli,
                user_id
            )
            cursor.execute("""
                UPDATE clientes
                SET cliente=%s, direccion=%s, localidad=%s, tel1=%s, tel2=%s, cuit=%s, obs=%s, 
                    preventivo=%s, dias=%s, fecha_mant=%s, importe=%s
                WHERE id_cli=%s AND id_usuario=%s
            """, datos)
            conn.close()
            flash("Cliente actualizado")
            return redirect(url_for('clientes'))
        else:
            cursor.execute("SELECT * FROM clientes WHERE id_cli = %s AND id_usuario = %s", (id_cli, user_id))
            cliente = cursor.fetchone()
            if not cliente:
                flash("Cliente no encontrado")
                return redirect(url_for('clientes'))
    conn.close()
    return render_template('cliente_form.html', cliente=cliente)

@app.route('/clientes/eliminar/<int:id_cli>', methods=['POST'])
@login_required
def eliminar_cliente(id_cli):
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM clientes WHERE id_cli = %s AND id_usuario = %s", (id_cli, user_id))
    conn.close()
    flash("Cliente eliminado")
    return redirect(url_for('clientes'))

@app.route('/clientes/actualizar_mantenimiento/<int:id_cli>', methods=['POST'])
@login_required
def actualizar_mantenimiento(id_cli):
    user_id = get_current_user_id()
    from datetime import date
    fecha_actual = date.today().strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT cliente FROM clientes WHERE id_cli = %s AND id_usuario = %s", (id_cli, user_id))
        cliente = cursor.fetchone()
        
        if cliente:
            cursor.execute("""
                UPDATE clientes SET fecha_mant = %s WHERE id_cli = %s AND id_usuario = %s
            """, (fecha_actual, id_cli, user_id))
            flash(f"Mantenimiento actualizado para {cliente['cliente']}")
        else:
            flash("Cliente no encontrado")
    conn.close()
    
    return redirect(url_for('clientes'))

# ==================== EQUIPOS ====================
@app.route('/equipos/<int:id_cli>')
@login_required
def equipos(id_cli):
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM clientes WHERE id_cli = %s AND id_usuario = %s", (id_cli, user_id))
        cliente = cursor.fetchone()
        if not cliente:
            flash("Cliente no encontrado")
            return redirect(url_for('clientes'))
        
        cursor.execute("SELECT * FROM equipos WHERE id_cli = %s", (id_cli,))
        equipos = cursor.fetchall()
    conn.close()
    return render_template('equipos.html', cliente=cliente, equipos=equipos)

@app.route('/equipos/nuevo/<int:id_cli>', methods=['GET', 'POST'])
@login_required
def nuevo_equipo(id_cli):
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT cliente FROM clientes WHERE id_cli = %s AND id_usuario = %s", (id_cli, user_id))
        cliente = cursor.fetchone()
        if not cliente:
            flash("Cliente no encontrado")
            return redirect(url_for('clientes'))
    
    if request.method == 'POST':
        datos = (
            id_cli,
            request.form['nro_serie'],
            request.form['capacidad'],
            request.form['marca'],
            request.form['modelo'],
            request.form['refrigerante'],
            request.form['ubicacion'],
            1 if 'altura' in request.form else 0,
            request.form['obs'],
            request.form['fecha_inst'],
            request.form['codigo']
        )
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO equipos (id_cli, nro_serie, capacidad, marca, modelo, refrigerante, ubicacion, altura, obs, fecha_inst, codigo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, datos)
        conn.close()
        flash("Equipo agregado")
        return redirect(url_for('equipos', id_cli=id_cli))
    conn.close()
    return render_template('equipo_form.html', equipo=None, id_cli=id_cli, cliente=cliente)

@app.route('/equipos/editar/<int:id_equipo>', methods=['GET', 'POST'])
@login_required
def editar_equipo(id_equipo):
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        if request.method == 'POST':
            cursor.execute("""
                SELECT e.id_cli FROM equipos e 
                INNER JOIN clientes c ON e.id_cli = c.id_cli 
                WHERE e.id_equipo = %s AND c.id_usuario = %s
            """, (id_equipo, user_id))
            
            if not cursor.fetchone():
                flash("No tiene permisos para editar este equipo")
                return redirect(url_for('clientes'))
            
            datos = (
                request.form['nro_serie'],
                request.form['capacidad'],
                request.form['marca'],
                request.form['modelo'],
                request.form['refrigerante'],
                request.form['ubicacion'],
                1 if 'altura' in request.form else 0,
                request.form['obs'],
                request.form['fecha_inst'],
                request.form['codigo'],
                id_equipo
            )
            cursor.execute("""
                UPDATE equipos SET
                nro_serie=%s, capacidad=%s, marca=%s, modelo=%s, refrigerante=%s, ubicacion=%s, altura=%s, obs=%s, fecha_inst=%s, codigo=%s
                WHERE id_equipo=%s
            """, datos)
            conn.close()
            flash("Equipo actualizado")
            return redirect(url_for('equipos', id_cli=request.form['id_cli']))
        else:
            cursor.execute("""
                SELECT e.*, c.cliente FROM equipos e 
                INNER JOIN clientes c ON e.id_cli = c.id_cli 
                WHERE e.id_equipo = %s AND c.id_usuario = %s
            """, (id_equipo, user_id))
            result = cursor.fetchone()
            
            if not result:
                flash("Equipo no encontrado")
                return redirect(url_for('clientes'))
            
            equipo = result
            cliente = {'cliente': result['cliente']}
    conn.close()
    return render_template('equipo_form.html', equipo=equipo, id_cli=equipo['id_cli'], cliente=cliente)

@app.route('/equipos/eliminar/<int:id_equipo>/<int:id_cli>', methods=['POST'])
@login_required
def eliminar_equipo(id_equipo, id_cli):
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT e.id_equipo FROM equipos e 
            INNER JOIN clientes c ON e.id_cli = c.id_cli 
            WHERE e.id_equipo = %s AND c.id_usuario = %s
        """, (id_equipo, user_id))
        
        if cursor.fetchone():
            cursor.execute("DELETE FROM equipos WHERE id_equipo = %s", (id_equipo,))
            flash("Equipo eliminado")
        else:
            flash("No tiene permisos para eliminar este equipo")
    conn.close()
    return redirect(url_for('equipos', id_cli=id_cli))

@app.route('/equipos/todos', methods=['GET', 'POST'])
@login_required
def todos_los_equipos():
    user_id = get_current_user_id()
    conn = get_db_connection()
    busqueda = request.form.get('busqueda')

    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
        if busqueda:
            consulta = """
                SELECT equipos.*, clientes.cliente AS nombre_cliente 
                FROM equipos 
                JOIN clientes ON equipos.id_cli = clientes.id_cli 
                WHERE clientes.id_usuario = %s 
                AND (equipos.codigo LIKE %s OR equipos.nro_serie LIKE %s)
            """
            cursor.execute(consulta, (user_id, '%' + busqueda + '%', '%' + busqueda + '%'))
        else:
            consulta = """
                SELECT equipos.*, clientes.cliente AS nombre_cliente 
                FROM equipos 
                JOIN clientes ON equipos.id_cli = clientes.id_cli
                WHERE clientes.id_usuario = %s
            """
            cursor.execute(consulta, (user_id,))

        equipos = cursor.fetchall()

    conn.close()
    return render_template('todos_equipos.html', equipos=equipos, busqueda=busqueda)

# ==================== TRABAJOS ====================
@app.route('/trabajos/finalizar/<int:id_trabajo>/<int:id_equipo>', methods=['GET', 'POST'])
@login_required
def finalizar_trabajo(id_trabajo, id_equipo):
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        if request.method == 'POST':
            observaciones = request.form.get('observaciones', '')
            from datetime import date
            fecha_finalizacion = date.today().strftime('%Y-%m-%d')
            
            cursor.execute("""
                SELECT t.id_trabajo FROM trabajos t
                INNER JOIN equipos e ON t.id_equipo = e.id_equipo
                INNER JOIN clientes c ON e.id_cli = c.id_cli
                WHERE t.id_trabajo = %s AND c.id_usuario = %s
            """, (id_trabajo, user_id))
            
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE trabajos 
                    SET pendiente = 0, 
                        observaciones = %s, 
                        fecha_finalizacion = %s 
                    WHERE id_trabajo = %s
                """, (observaciones, fecha_finalizacion, id_trabajo))
                flash("Trabajo finalizado correctamente")
            else:
                flash("No tiene permisos para finalizar este trabajo")
            
            conn.close()
            return redirect(url_for('trabajos_equipo', id_equipo=id_equipo))
        else:
            cursor.execute("""
                SELECT t.*, e.*, c.cliente FROM trabajos t
                INNER JOIN equipos e ON t.id_equipo = e.id_equipo
                INNER JOIN clientes c ON e.id_cli = c.id_cli
                WHERE t.id_trabajo = %s AND t.pendiente = 1 AND c.id_usuario = %s
            """, (id_trabajo, user_id))
            result = cursor.fetchone()
            
            if not result:
                flash("Trabajo no encontrado o ya finalizado")
                return redirect(url_for('clientes'))
            
            trabajo = result
            equipo = result
    conn.close()
    return render_template('finalizar_trabajo.html', trabajo=trabajo, equipo=equipo)

@app.route('/trabajos/reabrir/<int:id_trabajo>/<int:id_equipo>', methods=['POST'])
@login_required
def reabrir_trabajo(id_trabajo, id_equipo):
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT t.id_trabajo FROM trabajos t
            INNER JOIN equipos e ON t.id_equipo = e.id_equipo
            INNER JOIN clientes c ON e.id_cli = c.id_cli
            WHERE t.id_trabajo = %s AND c.id_usuario = %s
        """, (id_trabajo, user_id))
        
        if cursor.fetchone():
            cursor.execute("""
                UPDATE trabajos 
                SET pendiente = 1, 
                    observaciones = NULL, 
                    fecha_finalizacion = NULL 
                WHERE id_trabajo = %s
            """, (id_trabajo,))
            flash("Trabajo reabierto como pendiente")
        else:
            flash("No tiene permisos para reabrir este trabajo")
    conn.close()
    return redirect(url_for('trabajos_equipo', id_equipo=id_equipo))

@app.route('/equipos/trabajos/<int:id_equipo>', methods=['GET', 'POST'])
@login_required
def trabajos_equipo(id_equipo):
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT e.* FROM equipos e 
            INNER JOIN clientes c ON e.id_cli = c.id_cli 
            WHERE e.id_equipo = %s AND c.id_usuario = %s
        """, (id_equipo, user_id))
        equipo = cursor.fetchone()
        
        if not equipo:
            flash("Equipo no encontrado")
            return redirect(url_for('clientes'))

        if request.method == 'POST':
            descripcion = request.form['descripcion']
            fecha = request.form['fecha']
            pendiente = 1 if 'pendiente' in request.form else 0
            
            cursor.execute("""
                INSERT INTO trabajos (id_equipo, descripcion, fecha, pendiente)
                VALUES (%s, %s, %s, %s)
            """, (id_equipo, descripcion, fecha, pendiente))
            flash('Trabajo agregado correctamente.')
            return redirect(url_for('trabajos_equipo', id_equipo=id_equipo))

        cursor.execute("""
            SELECT * FROM trabajos 
            WHERE id_equipo = %s AND pendiente = 1 
            ORDER BY fecha DESC
        """, (id_equipo,))
        trabajos_pendientes = cursor.fetchall()
        
        cursor.execute("""
            SELECT * FROM trabajos 
            WHERE id_equipo = %s AND pendiente = 0 
            ORDER BY fecha_finalizacion DESC, fecha DESC 
            LIMIT 10
        """, (id_equipo,))
        trabajos_finalizados = cursor.fetchall()

    conn.close()
    return render_template('trabajos_equipo.html', 
                         equipo=equipo, 
                         trabajos_pendientes=trabajos_pendientes,
                         trabajos_finalizados=trabajos_finalizados)

@app.route('/trabajos/eliminar/<int:id_trabajo>/<int:id_equipo>', methods=['POST'])
@login_required
def eliminar_trabajo(id_trabajo, id_equipo):
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT t.id_trabajo FROM trabajos t
            INNER JOIN equipos e ON t.id_equipo = e.id_equipo
            INNER JOIN clientes c ON e.id_cli = c.id_cli
            WHERE t.id_trabajo = %s AND c.id_usuario = %s
        """, (id_trabajo, user_id))
        
        if cursor.fetchone():
            cursor.execute("DELETE FROM trabajos WHERE id_trabajo = %s", (id_trabajo,))
            flash("Trabajo eliminado")
        else:
            flash("No tiene permisos para eliminar este trabajo")
    conn.close()
    return redirect(url_for('trabajos_equipo', id_equipo=id_equipo))

@app.route('/trabajos/pendientes')
@login_required
def trabajos_pendientes():
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT t.*, e.codigo AS equipo_codigo, c.cliente FROM trabajos t
            JOIN equipos e ON t.id_equipo = e.id_equipo
            JOIN clientes c ON e.id_cli = c.id_cli
            WHERE t.pendiente = 1 AND c.id_usuario = %s
            ORDER BY t.fecha DESC
        """, (user_id,))
        trabajos = cursor.fetchall()
       
        for trabajo in trabajos:
             if isinstance(trabajo['pendiente'], bytes):
                 trabajo['pendiente'] = int.from_bytes(trabajo['pendiente'], byteorder='little')

    conn.close()
    return render_template('trabajos.html', trabajos=trabajos, titulo="Trabajos Pendientes")

@app.route('/trabajos/todos')
@login_required
def trabajos_todos():
    user_id = get_current_user_id()
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT t.*, e.codigo AS equipo_codigo, c.cliente FROM trabajos t
            JOIN equipos e ON t.id_equipo = e.id_equipo
            JOIN clientes c ON e.id_cli = c.id_cli
            WHERE c.id_usuario = %s
            ORDER BY t.fecha DESC
        """, (user_id,))
        trabajos = cursor.fetchall()
        for trabajo in trabajos:
            if isinstance(trabajo['pendiente'], bytes):
                trabajo['pendiente'] = int.from_bytes(trabajo['pendiente'], byteorder='little')

    conn.close()
    return render_template('trabajos.html', trabajos=trabajos, titulo="Todos los Trabajos")

@app.route('/ayuda')
def ayuda():
    return render_template('ayuda.html')


if __name__ == '__main__':
    app.run('0.0.0.0', debug=True, port=5090)