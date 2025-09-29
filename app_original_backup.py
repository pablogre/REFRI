from flask import Flask, render_template, request, redirect, url_for, flash
import pymysql

app = Flask(__name__)
app.secret_key = 'mi_clave_super_secreta_4567'

# Configuración de la base de datos
# Conexión DB
def get_db_connection():
    return pymysql.connect(
        host='localhost',
        user='root',
        password='',
        db='refri',
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route('/')
def index():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT c.*, COUNT(e.id_equipo) as total_equipos 
            FROM clientes c 
            LEFT JOIN equipos e ON c.id_cli = e.id_cli 
            GROUP BY c.id_cli
        """)
        clientes = cursor.fetchall()
    conn.close()
    return render_template('clientes.html', clientes=clientes)


# ==================== CLIENTES ====================
@app.route('/clientes')
def clientes():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT c.*, COUNT(e.id_equipo) as total_equipos 
            FROM clientes c 
            LEFT JOIN equipos e ON c.id_cli = e.id_cli 
            GROUP BY c.id_cli
        """)
        clientes = cursor.fetchall()
    conn.close()
    return render_template('clientes.html', clientes=clientes)

# RUTAS SIMPLIFICADAS - Con TINYINT es mucho más fácil

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    if request.method == 'POST':
        # Procesar el checkbox preventivo
        preventivo = 1 if 'preventivo' in request.form else 0
        
        # Si preventivo está marcado pero no hay fecha, usar fecha actual
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
            float(request.form.get('importe', 0)) if preventivo and request.form.get('importe') else None
        )
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO clientes (cliente, direccion, localidad, tel1, tel2, cuit, obs, preventivo, dias, fecha_mant, importe)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, datos)
            conn.commit()
        conn.close()
        flash("Cliente agregado correctamente")
        return redirect(url_for('clientes'))
    return render_template('cliente_form.html', cliente=None)

@app.route('/clientes/editar/<int:id_cli>', methods=['GET', 'POST'])
def editar_cliente(id_cli):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        if request.method == 'POST':
            # Procesar el checkbox preventivo
            preventivo = 1 if 'preventivo' in request.form else 0
            
            # Si preventivo está marcado pero no hay fecha, usar fecha actual
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
                id_cli
            )
            cursor.execute("""
                UPDATE clientes
                SET cliente=%s, direccion=%s, localidad=%s, tel1=%s, tel2=%s, cuit=%s, obs=%s, 
                    preventivo=%s, dias=%s, fecha_mant=%s, importe=%s
                WHERE id_cli=%s
            """, datos)
            conn.commit()
            conn.close()
            flash("Cliente actualizado")
            return redirect(url_for('index'))
        else:
            cursor.execute("SELECT * FROM clientes WHERE id_cli = %s", (id_cli,))
            cliente = cursor.fetchone()
    conn.close()
    return render_template('cliente_form.html', cliente=cliente)

# RUTAS PRINCIPALES SIN COMPLICACIONES


@app.route('/clientes/eliminar/<int:id_cli>', methods=['POST'])
def eliminar_cliente(id_cli):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM clientes WHERE id_cli = %s", (id_cli,))
        conn.commit()
    conn.close()
    flash("Cliente eliminado")
    return redirect(url_for('clientes'))


# Nueva ruta para actualizar solo el mantenimiento
# Reemplaza la función actualizar_mantenimiento en tu app.py por esta versión simple:

@app.route('/clientes/actualizar_mantenimiento/<int:id_cli>', methods=['POST'])
def actualizar_mantenimiento(id_cli):
    from datetime import date
    fecha_actual = date.today().strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    with conn.cursor() as cursor:
        # Obtener nombre del cliente para el mensaje
        cursor.execute("SELECT cliente FROM clientes WHERE id_cli = %s", (id_cli,))
        cliente = cursor.fetchone()
        
        # Actualizar fecha de mantenimiento
        cursor.execute("""
            UPDATE clientes SET fecha_mant = %s WHERE id_cli = %s
        """, (fecha_actual, id_cli))
        conn.commit()
    conn.close()
    
    flash(f"Mantenimiento actualizado para {cliente['cliente'] if cliente else 'el cliente'}")
    return redirect(url_for('index'))

# Nueva ruta para ver clientes con mantenimiento vencido
@app.route('/mantenimientos/vencidos')
def mantenimientos_vencidos():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT *, 
                   COUNT(e.id_equipo) as total_equipos,
                   DATEDIFF(CURDATE(), DATE_ADD(fecha_mant, INTERVAL dias DAY)) as dias_vencidos
            FROM clientes c 
            LEFT JOIN equipos e ON c.id_cli = e.id_cli 
            WHERE c.preventivo = 1 
              AND c.fecha_mant IS NOT NULL 
              AND c.dias > 0
              AND CURDATE() > DATE_ADD(c.fecha_mant, INTERVAL c.dias DAY)
            GROUP BY c.id_cli
            ORDER BY dias_vencidos DESC
        """)
        clientes_vencidos = cursor.fetchall()
    conn.close()
    
    return render_template('mantenimientos_vencidos.html', clientes=clientes_vencidos)


# ==================== EQUIPOS ====================
@app.route('/equipos/<int:id_cli>')
def equipos(id_cli):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM clientes WHERE id_cli = %s", (id_cli,))
        cliente = cursor.fetchone()
        cursor.execute("SELECT * FROM equipos WHERE id_cli = %s", (id_cli,))
        equipos = cursor.fetchall()
    conn.close()
    return render_template('equipos.html', cliente=cliente, equipos=equipos)

@app.route('/equipos/nuevo/<int:id_cli>', methods=['GET', 'POST'])
def nuevo_equipo(id_cli):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT cliente FROM clientes WHERE id_cli = %s", (id_cli,))
        cliente = cursor.fetchone()
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
            # CORREGÍ LA CONSULTA: faltaba una coma entre fecha_inst y codigo
            cursor.execute("""
                INSERT INTO equipos (id_cli, nro_serie, capacidad, marca, modelo, refrigerante, ubicacion, altura, obs, fecha_inst, codigo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, datos)
            conn.commit()
        conn.close()
        flash("Equipo agregado")
        return redirect(url_for('equipos', id_cli=id_cli))
    conn.close()
    return render_template('equipo_form.html', equipo=None, id_cli=id_cli, cliente=cliente)

@app.route('/equipos/editar/<int:id_equipo>', methods=['GET', 'POST'])
def editar_equipo(id_equipo):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        if request.method == 'POST':
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
            conn.commit()
            conn.close()
            flash("Equipo actualizado")
            return redirect(url_for('equipos', id_cli=request.form['id_cli']))
        else:
            cursor.execute("SELECT * FROM equipos WHERE id_equipo = %s", (id_equipo,))
            equipo = cursor.fetchone()
            cursor.execute("SELECT cliente FROM clientes WHERE id_cli = %s", (equipo['id_cli'],))
            cliente = cursor.fetchone()
    conn.close()
    return render_template('equipo_form.html', equipo=equipo, id_cli=equipo['id_cli'], cliente=cliente)


@app.route('/equipos/eliminar/<int:id_equipo>/<int:id_cli>', methods=['POST'])
def eliminar_equipo(id_equipo, id_cli):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM equipos WHERE id_equipo = %s", (id_equipo,))
        conn.commit()
    conn.close()
    flash("Equipo eliminado")
    return redirect(url_for('equipos', id_cli=id_cli))

@app.route('/equipos/todos', methods=['GET', 'POST'])
def todos_los_equipos():
    conn = get_db_connection()
    busqueda = request.form.get('busqueda')

    with conn.cursor(pymysql.cursors.DictCursor) as cursor:
        if busqueda:
            consulta = """
                SELECT equipos.*, clientes.cliente AS nombre_cliente 
                FROM equipos 
                JOIN clientes ON equipos.id_cli = clientes.id_cli 
                WHERE equipos.codigo LIKE %s OR equipos.nro_serie LIKE %s
            """
            cursor.execute(consulta, ('%' + busqueda + '%', '%' + busqueda + '%'))
        else:
            consulta = """
                SELECT equipos.*, clientes.cliente AS nombre_cliente 
                FROM equipos 
                JOIN clientes ON equipos.id_cli = clientes.id_cli
            """
            cursor.execute(consulta)

        equipos = cursor.fetchall()

    conn.close()
    return render_template('todos_equipos.html', equipos=equipos, busqueda=busqueda)

# ==================== TRABAJOS ====================

# Ruta para finalizar un trabajo
@app.route('/trabajos/finalizar/<int:id_trabajo>/<int:id_equipo>', methods=['GET', 'POST'])
def finalizar_trabajo(id_trabajo, id_equipo):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        if request.method == 'POST':
            observaciones = request.form.get('observaciones', '')
            from datetime import date
            fecha_finalizacion = date.today().strftime('%Y-%m-%d')
            
            # Actualizar el trabajo como finalizado
            cursor.execute("""
                UPDATE trabajos 
                SET pendiente = 0, 
                    observaciones = %s, 
                    fecha_finalizacion = %s 
                WHERE id_trabajo = %s
            """, (observaciones, fecha_finalizacion, id_trabajo))
            conn.commit()
            conn.close()
            flash("Trabajo finalizado correctamente")
            return redirect(url_for('trabajos_equipo', id_equipo=id_equipo))
        else:
            # Mostrar formulario para finalizar - verificar que el trabajo esté pendiente
            cursor.execute("""
                SELECT * FROM trabajos 
                WHERE id_trabajo = %s AND pendiente = 1
            """, (id_trabajo,))
            trabajo = cursor.fetchone()
            
            if not trabajo:
                conn.close()
                flash("El trabajo no existe o ya está finalizado")
                return redirect(url_for('trabajos_equipo', id_equipo=id_equipo))
            
            cursor.execute("SELECT * FROM equipos WHERE id_equipo = %s", (id_equipo,))
            equipo = cursor.fetchone()
    conn.close()
    return render_template('finalizar_trabajo.html', trabajo=trabajo, equipo=equipo)



# Ruta para reabrir un trabajo (cambiar de finalizado a pendiente)
@app.route('/trabajos/reabrir/<int:id_trabajo>/<int:id_equipo>', methods=['POST'])
def reabrir_trabajo(id_trabajo, id_equipo):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            UPDATE trabajos 
            SET pendiente = 1, 
                observaciones = NULL, 
                fecha_finalizacion = NULL 
            WHERE id_trabajo = %s
        """, (id_trabajo,))
        conn.commit()
    conn.close()
    flash("Trabajo reabierto como pendiente")
    return redirect(url_for('trabajos_equipo', id_equipo=id_equipo))


# Reemplaza la función trabajos_equipo en tu app.py con esta versión corregida:

@app.route('/equipos/trabajos/<int:id_equipo>', methods=['GET', 'POST'])
def trabajos_equipo(id_equipo):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM equipos WHERE id_equipo = %s", (id_equipo,))
        equipo = cursor.fetchone()

        if request.method == 'POST':
            # Datos del formulario para nuevo trabajo
            descripcion = request.form['descripcion']
            fecha = request.form['fecha']
            pendiente = 1 if 'pendiente' in request.form else 0
            
            cursor.execute("""
                INSERT INTO trabajos (id_equipo, descripcion, fecha, pendiente)
                VALUES (%s, %s, %s, %s)
            """, (id_equipo, descripcion, fecha, pendiente))
            conn.commit()
            flash('Trabajo agregado correctamente.')
            return redirect(url_for('trabajos_equipo', id_equipo=id_equipo))

        # Obtener trabajos PENDIENTES
        cursor.execute("""
            SELECT * FROM trabajos 
            WHERE id_equipo = %s AND pendiente = 1 
            ORDER BY fecha DESC
        """, (id_equipo,))
        trabajos_pendientes = cursor.fetchall()
        
        # Obtener trabajos FINALIZADOS (últimos 10)
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
def eliminar_trabajo(id_trabajo, id_equipo):
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("DELETE FROM trabajos WHERE id_trabajo = %s", (id_trabajo,))
        conn.commit()
    conn.close()
    flash("Trabajo eliminado")
    return redirect(url_for('trabajos_equipo', id_equipo=id_equipo))

@app.route('/trabajos/pendientes')
def trabajos_pendientes():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT t.*, e.codigo AS equipo_codigo, c.cliente FROM trabajos t
            JOIN equipos e ON t.id_equipo = e.id_equipo
            JOIN clientes c ON e.id_cli = c.id_cli
            WHERE t.pendiente = 1
            ORDER BY t.fecha DESC
        """)
        trabajos = cursor.fetchall()
       
        for trabajo in trabajos:
             if isinstance(trabajo['pendiente'], bytes):
                 trabajo['pendiente'] = int.from_bytes(trabajo['pendiente'], byteorder='little')

    conn.close()
    return render_template('trabajos.html', trabajos=trabajos, titulo="Trabajos Pendientes")

@app.route('/trabajos/todos')
def trabajos_todos():
    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT t.*, e.codigo AS equipo_codigo, c.cliente FROM trabajos t
            JOIN equipos e ON t.id_equipo = e.id_equipo
            JOIN clientes c ON e.id_cli = c.id_cli
            ORDER BY t.fecha DESC
        """)
        trabajos = cursor.fetchall()
        for trabajo in trabajos:
            if isinstance(trabajo['pendiente'], bytes):
                trabajo['pendiente'] = int.from_bytes(trabajo['pendiente'], byteorder='little')

    conn.close()
    return render_template('trabajos.html', trabajos=trabajos, titulo="Todos los Trabajos")

# ====================

if __name__ == '__main__':
    app.run('0.0.0.0',debug=True,port=5090)