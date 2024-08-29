from flask import Flask, render_template, request, redirect, url_for, flash, session
import re
from flask_mysqldb import MySQL
from flask import jsonify
from flask_mail import Mail, Message
from email_validator import validate_email, EmailNotValidError
import pdfkit

def crear_app():
    app = Flask(__name__)
    EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

    app.config['MAIL_SERVER'] = 'smtp.outlook.com'  # El servidor SMTP
    app.config['MAIL_PORT'] = 587  # El puerto
    app.config['MAIL_USERNAME'] = 'reportesctn@outlook.com'  # Tu correo
    app.config['MAIL_PASSWORD'] = 'ucspfhcmjyrebeze'  # Tu contraseña
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = ''
    app.config['MYSQL_DB'] = 'informatica'
    app.secret_key = 'mysecretkey'
    mail = Mail(app)
    mysql = MySQL(app)

    @app.route('/')
    def index():
        if 'role' in session:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM alumno")
            alumnos = cur.fetchall()
            cur.close()
            return render_template('login.html', role=session['role'], alumnos=alumnos)
        return redirect(url_for('login'))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            role = request.form['role']
            ci = request.form['ci']
            role_especialidades = {
                'info': 'Informatica',
                'cc': 'Construccion civil',
                'auto': 'Automotriz',
                'eik': 'Electrónica',
                'edad': 'Electricidad',
                'emca': 'Electromecanica',
                'indu': 'Mecánica Industrial',
                'qca': 'Química'
            }

            if role == 'admin' or role == 'enc':
                if ci in role_especialidades:
                    session['role'] = 'administrador' if role == 'admin' else 'encargado'
                    session['espe'] = role_especialidades[ci]
                    flash('Login successful')
                    if session['role'] == 'administrador':
                        return redirect(url_for('admin', espe=session['espe']))
                    elif session['role'] == 'encargado':
                        return redirect(url_for('elegir_curso', espe = session['espe']))
                else:
                    flash('Invalid CI for admin/encargado')

            elif role == 'alumno':
                cur = mysql.connection.cursor()
                cur.execute("SELECT * FROM alumno WHERE ci = %s", [ci])
                alumno = cur.fetchone()
                cur.close()
                if alumno:
                    session['role'] = 'alumno'
                    session['ci'] = ci
                    flash('Alumno login successful')
                    return redirect(url_for('mostrar'))
                else:
                    flash('Invalid CI for alumno')

            else:
                flash('Invalid role')

        return render_template('login.html')

    @app.route('/<espe>/admin')
    def admin(espe):
        if 'role' in session and session['role'] == 'administrador' or session['role'] == 'encargado':
            return render_template('admin.html', espe=espe, role=session['role'])
        else:
            flash('Access Denied. Please login as administrator.')
            return redirect(url_for('login'))
    # ///////////////////////////////////////////////////////////

    @app.route('/logout')
    def logout():
        session.pop('role', None)
        session.pop('ci', None)
        flash('You have been logged out')
        return redirect(url_for('login'))

    @app.route('/add_contact', methods=['POST'])
    def add_contact():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                nombre = request.form['nombre']
                apellido = request.form['apellido']
                curso = request.form['curso']
                seccion = request.form['seccion']
                especialidad = session['espe']
                ci = request.form['ci']
                correo_encargado = request.form['correo_encargado']

                # Validar longitud del CI
                if len(ci) < 7 or len(ci) > 8:
                    flash('El CI debe tener entre 7 y 8 caracteres', 'error')
                    return redirect(url_for('alumnos', espe=session['espe']))

                cur = mysql.connection.cursor()

                # Verificar si ya existe un alumno con los mismos datos
                cur.execute("""
                    SELECT * FROM alumno
                    WHERE nombre = %s AND apellido = %s AND curso = %s AND seccion = %s AND especialidad = %s AND correo_encargado = %s
                """, (nombre, apellido, curso, seccion, especialidad, correo_encargado))
                alumno_existente = cur.fetchone()

                if alumno_existente:
                    flash('Ya existe un alumno con los mismos datos', 'error')
                    return redirect(url_for('alumnos', espe=session['espe']))

                # Verificar si el CI ya existe
                cur.execute("SELECT * FROM alumno WHERE ci = %s", (ci,))
                ci_existente = cur.fetchone()

                if ci_existente:
                    flash('Ya existe un alumno con este CI', 'error')
                    return redirect(url_for('alumnos', espe=session['espe']))

                try:
                    cur.execute("""
                        INSERT INTO alumno (nombre, apellido, curso, seccion, especialidad, ci, correo_encargado)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (nombre, apellido, curso, seccion, especialidad, ci, correo_encargado))
                    mysql.connection.commit()
                    flash('Contacto agregado exitosamente', 'success')
                except Exception as e:
                    mysql.connection.rollback()
                    flash(f'Error: {e}', 'error')
                finally:
                    cur.close()
                return redirect(url_for('alumnos', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/edit_contact', methods=['POST'])
    def edit_contact():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                ci = request.form['ci']
                nombre = request.form['nombre']
                apellido = request.form['apellido']
                curso = request.form['curso']
                seccion = request.form['seccion']
                especialidad = session['espe']
                correo_encargado = request.form['correo_encargado']

                cur = mysql.connection.cursor()

                # 检查是否有相同的记录（除了ci）
                cur.execute("SELECT * FROM alumno WHERE nombre = %s AND apellido = %s AND curso = %s AND seccion = %s AND especialidad = %s AND correo_encargado = %s AND ci != %s",
                            (nombre, apellido, curso, seccion, especialidad, correo_encargado, ci))
                alumno_existente = cur.fetchone()

                if alumno_existente:
                    flash('Ya existe un alumno con estos datos')
                    return redirect(url_for('alumnos', espe=session['espe']))

                # 更新记录
                try:
                    cur.execute("""
                        UPDATE alumno SET nombre = %s, apellido = %s, curso = %s, seccion = %s, especialidad = %s, correo_encargado = %s
                        WHERE ci = %s
                    """, (nombre, apellido, curso, seccion, especialidad, correo_encargado, ci))
                    mysql.connection.commit()
                    flash('Contacto actualizado exitosamente')
                except Exception as e:
                    mysql.connection.rollback()
                    flash(f'Error: {e}')
                finally:
                    cur.close()
                return redirect(url_for('alumnos', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/delete_contact', methods=['POST'])
    def delete_contact():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                ci = request.form['ci']
                cur = mysql.connection.cursor()
                cur.execute("SELECT id_alumno FROM alumno WHERE ci = %s", [ci])
                alumno_existente = cur.fetchone()
                if alumno_existente:
                    alumno_id = alumno_existente[0]

                    # 查找相关报告ID
                    cur.execute(
                        "SELECT id_reporte FROM reporte WHERE alumno_id_alumno = %s", [alumno_id])
                    reportes_existentes = cur.fetchall()

                    # 删除 detalle_reporte 表中的相关记录
                    for reporte in reportes_existentes:
                        reporte_id = reporte[0]
                        cur.execute(
                            "DELETE FROM detalle_reporte WHERE reporte_id_reporte = %s", [reporte_id])

                    # 删除 reporte 表中的相关记录
                    for reporte in reportes_existentes:
                        reporte_id = reporte[0]
                        cur.execute(
                            "DELETE FROM reporte WHERE id_reporte = %s", [reporte_id])

                    # 删除 alumno 表中的记录
                    cur.execute("DELETE FROM alumno WHERE ci = %s", [ci])

                    mysql.connection.commit()
                cur.close()
                flash('Contact deleted successfully')
            return redirect(url_for('alumnos', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/<espe>/alumnos')
    def alumnos(espe):
        if 'role' in session:
            if session['role'] == 'administrador' or session['role'] == 'alumno':
                busqueda = request.args.get('busqueda', '').strip()
                if busqueda:
                    cur = mysql.connection.cursor()
                    cur.execute("SELECT * FROM alumno WHERE nombre LIKE %s OR apellido LIKE %s OR curso LIKE %s OR seccion LIKE %s OR ci LIKE %s OR especialidad LIKE %s AND especialidad = %s",
                                ('%' + busqueda + '%', '%' + busqueda + '%', '%' + busqueda + '%', '%' + busqueda + '%', '%' + busqueda + '%', '%' + busqueda + '%', espe))
                    alumnos = cur.fetchall()
                    cur.close()
                else:
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "SELECT * FROM alumno where especialidad = %s", (espe,))
                    alumnos = cur.fetchall()
                    cur.close()
                return render_template('alumno.html', role=session['role'], alumnos=alumnos, espe=espe)
        return redirect(url_for('login'))

    @app.route('/reporte')
    def reporte():
        return render_template('reporte.html')

    @app.route('/<espe>/materia')
    def materia(espe):
        if 'role' in session and session['role'] == 'administrador':
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM materia where especialidad = %s or especialidad = 'Plan Común'", (espe,))
            materia = cur.fetchall()
            cur.close()
            return render_template('materia.html', materia=materia, role=session['role'], espe=espe)
        else:
            flash('Access Denied. Please login as administrator.')
            return redirect(url_for('login'))

    @app.route('/<espe>/conductuales')
    def conductuales(espe):
        if 'role' in session and session['role'] == 'administrador':
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM rasgos_conductuales")
            conductuales = cur.fetchall()
            cur.close()
            return render_template('conductuales.html', conductuales=conductuales, role=session['role'], espe=espe)
        else:
            flash('Access Denied. Please login as administrator.')
            return redirect(url_for('login'))

    @app.route('/<espe>/profesor')
    def profesor(espe):
        if 'role' in session and session['role'] == 'administrador':
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM profesor")
            teachers = cur.fetchall()
            cur.execute("SELECT * FROM materia")
            materias = cur.fetchall()
            cur.close()
            return render_template('profesor.html', teachers=teachers, materias=materias, role=session['role'], espe=espe)
        else:
            flash('Access Denied. Please login as administrator.')
            return redirect(url_for('login'))

    @app.route('/add_teacher', methods=['POST'])
    def add_teacher():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                nombre = request.form['nombre']
                apellido = request.form['apellido']
                try:
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "Select * from profesor where nombre = %s and apellido = %s", (nombre, apellido))
                    a = cur.fetchall()
                    if a:
                        return redirect(url_for("profesor"))
                    cur.execute(
                        "INSERT INTO profesor (nombre, apellido) VALUES (%s, %s)", (nombre, apellido))
                    mysql.connection.commit()
                    print('Profesor agregado exitosamente')
                except Exception as e:
                    mysql.connection.rollback()
                    flash(f'Error al agregar profesor: {str(e)}')
                finally:
                    cur.close()
                return redirect(url_for('profesor', espe=session['espe']))
        else:
            return redirect(url_for('login'))
    # ////////////////////////////////////////////////////

    @app.route('/edit_teacher', methods=['POST'])
    def edit_teacher():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                try:
                    teacher_id = request.form['teacher_id']
                    nombre = request.form.get('nombre')
                    apellido = request.form.get('apellido')
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "Select * from profesor where nombre = %s and apellido = %s", (nombre, apellido))
                    a = cur.fetchall()
                    if a:
                        return redirect(url_for("profesor"))
                    if nombre:
                        cur.execute(
                            "UPDATE profesor SET nombre = %s WHERE id_profesor = %s", (nombre, teacher_id))
                    if apellido:
                        cur.execute(
                            "UPDATE profesor SET apellido = %s WHERE id_profesor = %s", (apellido, teacher_id))
                    mysql.connection.commit()
                    flash('Profesor modificado exitosamente')
                except KeyError as e:
                    flash(f'Error: {e} no encontrado en el formulario')
                except Exception as e:
                    flash(f'Error al modificar profesor: {str(e)}')
                    mysql.connection.rollback()
                finally:
                    if 'cur' in locals() and cur:
                        cur.close()
            return redirect(url_for('profesor', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/delete_teacher', methods=['POST'])
    def delete_teacher():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                teacher_id = request.form['teacher_id']
                try:
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "SELECT materia_id_materia FROM materia_por_profesor WHERE profesor_id_profesor = %s", [teacher_id])
                    mat = cur.fetchall()

    # 删除 materia_por_profesor 表中的相关记录
                    for materia in mat:
                        materia_id = materia[0]
                        cur.execute(
                            "DELETE FROM materia_por_profesor WHERE profesor_id_profesor = %s AND materia_id_materia = %s", (teacher_id, materia_id))

                    cur.execute(
                        "DELETE FROM profesor WHERE id_profesor = %s", [teacher_id])

                    mysql.connection.commit()
                    flash('Profesor eliminado exitosamente')
                except Exception as e:
                    flash(f'Error al eliminar profesor: {str(e)}')
                    mysql.connection.rollback()
                finally:
                    if 'cur' in locals() and cur:
                        cur.close()
            return redirect(url_for('profesor', espe=session['espe']))
        else:
            return redirect(url_for('login'))
    # ////////////////////////////////////////////////////////////////

    @app.route('/add_materia', methods=['POST'])
    def add_materia():
        nombre = request.form['nombre']
        especialidad = request.form['especialidad']
        cursos = request.form['anios']
        cur = mysql.connection.cursor()

        try:
            cur.execute(
                "INSERT INTO materia (nombre, especialidad,cursos) VALUES (%s, %s,%s)", (nombre, especialidad,cursos))
            mysql.connection.commit()
            flash('Materia agregada exitosamente')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al agregar materia: {str(e)}')
        finally:
            cur.close()
        return redirect(url_for('materia', espe=session['espe']))

    # ////////////////////////////////////////////////////////////////

    @app.route('/edit_materia', methods=['POST'])
    def edit_materia():
        if request.method == 'POST':
            nombre = request.form['nombre']
            especialidad = request.form['especialidad']
            subject_id = request.form['subject_id']
            cursos = request.form['anios']  # Asegúrate de que 'anios' es el nombre correcto del campo
            
            try:
                cur = mysql.connection.cursor()

                # Verificar si ya existe una materia con el mismo nombre y especialidad, excluyendo la actual
                cur.execute("""
                    SELECT * FROM materia
                    WHERE nombre = %s AND especialidad = %s AND id_materia != %s
                """, (nombre, especialidad, subject_id))
                existing_subject = cur.fetchall()

                if existing_subject:
                    flash('Ya existe una materia con este nombre y especialidad')
                    return redirect(url_for("materia", espe=session.get('espe', 'default_value')))

                # Actualizar la materia
                cur.execute("""
                    UPDATE materia
                    SET nombre = %s, especialidad = %s, cursos = %s
                    WHERE id_materia = %s
                """, (nombre, especialidad, cursos, subject_id))
                mysql.connection.commit()
                flash('Materia modificada exitosamente')

            except KeyError as e:
                flash(f'Error: {e} no encontrado en el formulario')
            except Exception as e:
                flash(f'Error al modificar materia: {str(e)}')
                mysql.connection.rollback()
            finally:
                if 'cur' in locals() and cur:
                    cur.close()

            return redirect(url_for("materia", espe=session.get('espe', 'default_value')))

        
    @app.route('/delete_materia', methods=['POST'])
    def delete_materia():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                subject_id = request.form.get('subject_id', '')
                print(f"Recibida solicitud para eliminar materia con ID: {subject_id}")

                if not subject_id:
                    print("No se proporcionó el ID de la materia.")
                    flash('ID de materia no proporcionado.')
                    return redirect(url_for("materia", espe=session.get('espe', '')))

                try:
                    cur = mysql.connection.cursor()

                    # 1. Elimina los detalles de reporte en detalle_reporte
                    print("Obteniendo reportes relacionados con la materia ID:", subject_id)
                    cur.execute(
                        "SELECT id_reporte FROM reporte WHERE materia_id_materia = %s", 
                        (subject_id,)
                    )
                    reportes = cur.fetchall()
                    print(f"Reportes relacionados con la materia ID {subject_id}: {reportes}")

                    for reporte in reportes:
                        reporte_id = reporte[0]
                        print(f"Eliminando detalle_reporte para reporte ID: {reporte_id}")
                        cur.execute(
                            "DELETE FROM detalle_reporte WHERE reporte_id_reporte = %s", 
                            (reporte_id,)
                        )
                    cur.execute("Delete from reporte where materia_id_materia = %s", (subject_id, ))
                    cur.execute("DELETE FROM detalle_horario WHERE materia_id_materia = %s", (subject_id,))
                    cur.execute("delete from materia_por_profesor where materia_id_materia=%s", (subject_id,))
                    cur.execute("delete from materia where id_materia=%s", (subject_id, ))

                    mysql.connection.commit()
                    print("Materia eliminada exitosamente.")
                    flash('Materia eliminada exitosamente')

                except Exception as e:
                    print(f'Error al eliminar materia: {str(e)}')
                    flash(f'Error al eliminar materia: {str(e)}')
                    mysql.connection.rollback()
                
                finally:
                    if 'cur' in locals() and cur:
                        cur.close()
                
                return redirect(url_for("materia", espe=session.get('espe', '')))
            else:
                return redirect(url_for('login'))
        else:
            return redirect(url_for('login'))





    @app.route('/get_materias', methods=['POST'])
    def get_materias():
        curso_id = request.json.get('curso_id')
        espe = request.json.get('espe')
        cur = mysql.connection.cursor()
        cur.execute("Select curso from horario where id_horario=%s", (curso_id,))
        a = cur.fetchone()
        curso = a[0] if a else None
        s = {}
        k = {}
        i = 0
        if curso == 1:
            s[i] = '1ro 2do y 3ro'
            i += 1
            s[i] = 'solo 1ro'
            i += 1
            s[i] = 'solo 1ro y 2do'
            i += 1
            s[i] = 'solo 1ro y 3ro'
        elif curso == 2:
            s[i] = '1ro 2do y 3ro'
            i += 1
            s[i] = 'solo 2do'
            i += 1
            s[i] = 'solo 2do y 3ro'
            i += 1
            s[i] = 'solo 1ro y 2do'
        else:
            s[i] = '1ro 2do y 3ro'
            i += 1
            s[i] = 'solo 3ro'
            i += 1
            s[i] = 'solo 1ro y 3ro'
            i += 1
            s[i] = 'solo 2do y 3ro'
        
        materias = []
        for i in range(0, 4, 1):
            cur.execute("Select id_materia, nombre from materia where cursos=%s and (especialidad=%s or especialidad='Plan comun')", (s[i], espe))
            k[i] = cur.fetchall()
            for materia in k[i]:
                materias.append(materia)
        
        materia_list = [{'id': index, 'name': materia} for index, materia in materias]
        
        cur.close()

        return jsonify(materia_list)






    @app.route('/add_conductuales', methods=['POST'])
    def add_conductuales():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                desc = request.form['descripcion']
                try:
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "Select * from rasgos_conductuales where descripcion= %s", (desc,))
                    a = cur.fetchall()
                    if a:
                        return redirect(url_for("conductuales"))
                    cur.execute(
                        "INSERT INTO rasgos_conductuales (descripcion) VALUES (%s)", (desc,))
                    mysql.connection.commit()
                    flash('rasgo agregado exitosamente')
                except Exception as e:
                    mysql.connection.rollback()
                    flash(f'Error al agregar rasgo: {str(e)}')
                finally:
                    cur.close()

                return redirect(url_for('conductuales', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/edit_conductuales', methods=['POST'])
    def edit_conductuales():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                try:
                    cond_id = request.form['conductual_id']
                    desc = request.form['descripcion']
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "Select * from rasgos_conductuales where descripcion= %s", (desc,))
                    a = cur.fetchall()
                    if a:
                        return redirect(url_for("conductuales"))
                    if desc:
                        cur.execute(
                            "UPDATE rasgos_conductuales SET descripcion = %s WHERE id_rasgo = %s", (desc, cond_id))
                    mysql.connection.commit()
                    flash('rasgo modificado exitosamente')
                except KeyError as e:
                    flash(f'Error: {e} no encontrado en el formulario')
                except Exception as e:
                    flash(f'Error al modificar rasgo: {str(e)}')
                    mysql.connection.rollback()  # 回滚事务
                finally:
                    if 'cur' in locals() and cur:
                        cur.close()
            return redirect(url_for('conductuales', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/delete_conductuales', methods=['POST'])
    def delete_conductuales():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                cond_id = request.form['conductual_id']
                try:
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "DELETE FROM detalle_reporte WHERE rasgos_conductuales_id_rasgo = %s", [cond_id])
                    cur.execute(
                        "DELETE FROM rasgos_conductuales WHERE id_rasgo = %s", [cond_id])
                    mysql.connection.commit()
                    flash('Profesor eliminado exitosamente')
                except Exception as e:
                    flash(f'Error al eliminar profesor: {str(e)}')
                    mysql.connection.rollback()
                finally:
                    if 'cur' in locals() and cur:
                        cur.close()

            return redirect(url_for('conductuales', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/<espe>/horario')
    def horario(espe):
        if 'role' in session and session['role'] == 'administrador':
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT * FROM horario where especialidad = %s", (espe,))
            horarios = cur.fetchall()
            cur.close()
            return render_template('horario.html', horarios=horarios, role=session['role'], espe=espe)
        else:
            flash('Access Denied. Please login as administrator.')
            return redirect(url_for('login'))

    @app.route('/add_horario', methods=['POST'])
    def add_horario():
        curso = request.form['curso']
        seccion = request.form['seccion']
        especialidad = session['espe']

        if not curso or not seccion or not especialidad:
            flash('Todos los campos son obligatorios.')
            return redirect(url_for("horario"))

        try:
            with mysql.connection.cursor() as cur:
                # Verificar si ya existe el horario antes de intentar insertarlo
                cur.execute("SELECT * FROM horario WHERE curso = %s AND seccion = %s AND especialidad = %s",
                            (curso, seccion, especialidad))
                horario_existente = cur.fetchone()

                if horario_existente:
                    flash('El horario ya existe.')
                    return redirect(url_for("horario", espe=especialidad))
                else:
                    # Insertar nuevo horario
                    cur.execute("INSERT INTO horario (curso, seccion, especialidad) VALUES (%s, %s, %s)",
                                (curso, seccion, especialidad))
                    mysql.connection.commit()
                    flash('Horario agregado exitosamente')

        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al agregar horario: {str(e)}')

        return redirect(url_for('horario', espe=especialidad))

    @app.route('/edit_horario', methods=['POST'])
    def edit_horario():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                horario_id = request.form.get('horario_id')
                curso = request.form.get('curso')
                seccion = request.form.get('seccion')
                especialidad = session.get('espe')

                # Validar campos vacíos
                if not all([horario_id, curso, seccion, especialidad]):
                    flash('Todos los campos son obligatorios')
                    return redirect(url_for('horario', espe=especialidad))

                try:
                    cur = mysql.connection.cursor()
                    
                    # Verificar si el horario con los mismos datos ya existe
                    cur.execute("""
                        SELECT * FROM horario 
                        WHERE curso = %s AND seccion = %s AND especialidad = %s
                    """, (curso, seccion, especialidad))
                    
                    if cur.fetchall():
                        flash('El horario con los mismos datos ya existe')
                        return redirect(url_for('horario', espe=especialidad))

                    # Actualizar el horario
                    cur.execute("""
                        UPDATE horario 
                        SET curso = %s, seccion = %s, especialidad = %s 
                        WHERE id_horario = %s
                    """, (curso, seccion, especialidad, horario_id))
                    
                    mysql.connection.commit()
                    flash('Horario modificado exitosamente')

                except Exception as e:
                    mysql.connection.rollback()
                    flash(f'Error al modificar horario: {str(e)}')

                finally:
                    if 'cur' in locals() and cur:
                        cur.close()

                return redirect(url_for('horario', espe=especialidad))
        else:
            return redirect(url_for('login'))


    @app.route('/delete_horario', methods=['POST'])
    def delete_horario():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                horario_id = request.form['horario_id']
                try:
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "DELETE FROM detalle_horario WHERE horario_id_horario = %s", [horario_id])
                    cur.execute(
                        "DELETE FROM horario WHERE id_horario = %s", [horario_id])
                    mysql.connection.commit()
                    flash('Horario eliminado exitosamente')
                except Exception as e:
                    flash(f'Error al eliminar horario: {str(e)}')
                    mysql.connection.rollback()
                finally:
                    if 'cur' in locals() and cur:
                        cur.close()
            return redirect(url_for('horario', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/<espe>/materia_profe')
    def materia_profe(espe):
        if 'role' in session and session['role'] == 'administrador':
            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT p.id_profesor AS profesor_id, p.nombre AS profesor_nombre, p.apellido AS profesor_apellido, 
                    m.id_materia AS materia_id, m.nombre AS materia_nombre 
                FROM materia_por_profesor mp
                JOIN profesor p ON mp.profesor_id_profesor = p.id_profesor
                JOIN materia m ON mp.materia_id_materia= m.id_materia
                WHERE m.especialidad = %s or m.especialidad = 'Plan Comun'
            """, (espe, ))
            profmat = cur.fetchall()

            cur.execute("SELECT * FROM materia where especialidad = 'Plan Comun' or especialidad = %s", (espe,))
            materias = cur.fetchall()
            cur.execute("SELECT * FROM profesor")
            profesor = cur.fetchall()
            cur.close()
            return render_template('profe_materia.html', profmat=profmat, materias=materias, profesor=profesor, role=session['role'], espe=espe)
        else:
            flash('Access Denied. Please login as administrator.')
            return redirect(url_for('login'))

    @app.route('/add_profmate', methods=['POST'])
    def add_profmate():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                materia_id_materia = request.form.get('materia_id_materia')
                profesor_id_profesor = request.form.get('profesor_id_profesor')

                # Verificación de datos obligatorios
                if not materia_id_materia or not profesor_id_profesor:
                    flash('Todos los campos son obligatorios')
                    return redirect(url_for('materia_profe', espe=session.get('espe')))

                try:
                    cur = mysql.connection.cursor()
                    
                    # Verifica si la relación ya existe
                    cur.execute(
                        "SELECT COUNT(*) FROM materia_por_profesor WHERE materia_id_materia = %s AND profesor_id_profesor = %s", 
                        (materia_id_materia, profesor_id_profesor))
                    count = cur.fetchone()[0]

                    if count > 0:
                        flash('Esta relación ya existe')
                    else:
                        # Verifica si las materias y profesores existen
                        cur.execute("SELECT COUNT(*) FROM materia WHERE id_materia = %s", (materia_id_materia,))
                        if cur.fetchone()[0] == 0:
                            flash('La materia no existe')
                            return redirect(url_for('materia_profe', espe=session.get('espe')))
                        
                        cur.execute("SELECT COUNT(*) FROM profesor WHERE id_profesor = %s", (profesor_id_profesor,))
                        if cur.fetchone()[0] == 0:
                            flash('El profesor no existe')
                            return redirect(url_for('materia_profe', espe=session.get('espe')))

                        # Inserta la nueva relación
                        cur.execute(
                            "INSERT INTO materia_por_profesor (materia_id_materia, profesor_id_profesor) VALUES (%s, %s)", 
                            (materia_id_materia, profesor_id_profesor))
                        mysql.connection.commit()
                        flash('Relación agregada exitosamente')

                except Exception as e:
                    mysql.connection.rollback()
                    flash(f'Error al agregar relación: {str(e)}')
                finally:
                    cur.close()
                    
                return redirect(url_for('materia_profe', espe=session.get('espe')))
        else:
            return redirect(url_for('login'))
    

    @app.route('/edit_profmate', methods=['POST'])
    def edit_profmate():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                old_materia_id = request.form['old_materia_id']
                old_profesor_id = request.form['old_profesor_id']
                new_materia_id = request.form['new_materia_id']
                new_profesor_id = request.form['new_profesor_id']
                try:
                    cur = mysql.connection.cursor()
                    cur.execute("""
                        UPDATE materia_por_profesor 
                        SET materia_id_materia = %s, profesor_id_profesor = %s 
                        WHERE materia_id_materia = %s AND profesor_id_profesor = %s
                    """, (new_materia_id, new_profesor_id, old_materia_id, old_profesor_id))
                    mysql.connection.commit()
                    flash('Relación modificada exitosamente')
                except Exception as e:
                    mysql.connection.rollback()
                    flash(f'Error al modificar relación: {str(e)}')
                finally:
                    cur.close()
                return redirect(url_for('materia_profe', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/delete_profmate', methods=['POST'])
    def delete_profmate():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                materia_id = request.form['old_materia_id']
                profesor_id = request.form['old_profesor_id']
                try:
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "DELETE FROM materia_por_profesor WHERE materia_id_materia = %s AND profesor_id_profesor = %s", (materia_id, profesor_id))
                    mysql.connection.commit()
                    flash('Relación eliminada exitosamente')
                except Exception as e:
                    flash(f'Error al eliminar relación: {str(e)}')
                    mysql.connection.rollback()
                finally:
                    cur.close()
                return redirect(url_for('materia_profe', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/<espe>/materia_hora')
    def materia_hora(espe):
        if 'role' in session and session['role'] == 'administrador':
            cur = mysql.connection.cursor()

            # Obtener las materias disponibles
            cur.execute(
                "SELECT id_materia, nombre FROM materia where especialidad = %s or especialidad = 'Plan Comun'", (espe, ))
            materias = cur.fetchall()

            # Obtener los horarios disponibles
            cur.execute(
                "SELECT id_horario, especialidad, curso, seccion FROM horario WHERE especialidad = %s", (espe, ))
            horarios = cur.fetchall()

            # Obtener la relación materia-horario
            cur.execute("""
                SELECT d.materia_id_materia AS id_materia, m2.nombre AS materia_nombre, d.horario_id_horario AS id_horario, 
CONCAT(h.especialidad, ' ', h.curso, ' ', h.seccion) AS horario_info, d.dia, d.horario 
FROM detalle_horario d 
JOIN materia m2 ON m2.id_materia = d.materia_id_materia 
JOIN horario h ON h.id_horario = d.horario_id_horario 
WHERE h.especialidad = %s;

            """, (espe, ))

            materia_hora = cur.fetchall()
            
            cur.close()

            return render_template('detalle_horario.html', materia_hora=materia_hora, materias=materias, horarios=horarios, role=session['role'], espe=espe)
        else:
            flash('Acceso denegado. Por favor, inicie sesión como administrador.')
            return redirect(url_for('login'))

    @app.route('/add_dethora', methods=['POST'])
    def add_dethora():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                materia_id = request.form['materiaa']
                horario_id = request.form['horarioo']
                dia = request.form['tian']
                horario = request.form['horario']
                try:
                    cur = mysql.connection.cursor()
                    cur.execute("INSERT INTO detalle_horario (materia_id_materia, horario_id_horario, horario, dia) VALUES (%s, %s, %s, %s)",
                                (materia_id, horario_id, horario, dia))
                    mysql.connection.commit()
                    flash('Relación agregada exitosamente')
                except Exception as e:
                    mysql.connection.rollback()
                    flash(f'Error al agregar relación: {str(e)}')
                finally:
                    cur.close()
                return redirect(url_for('materia_hora', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/edit_dethora', methods=['POST'])
    def edit_dethora():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                old_materia_id = request.form['old_materia_id']
                old_horario_id = request.form['old_horario_id']
                materia_id = request.form['materiaa']
                horario_id = request.form['horarioo']
                dia = request.form['tian']
                horario = request.form['horario']
                try:
                    cur = mysql.connection.cursor()
                    cur.execute("""
                        UPDATE detalle_horario
                        SET materia_id_materia=%s, horario_id_horario=%s, horario=%s, dia=%s
                        WHERE materia_id_materia=%s AND horario_id_horario=%s
                    """, (materia_id, horario_id, horario, dia, old_materia_id, old_horario_id))
                    mysql.connection.commit()
                    flash('Relación actualizada exitosamente')
                except Exception as e:
                    mysql.connection.rollback()
                    flash(f'Error al actualizar relación: {str(e)}')
                finally:
                    cur.close()
                return redirect(url_for('materia_hora', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/delete_dethora', methods=['POST'])
    def delete_dethora():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                old_materia_id = request.form['old_materia_id']
                old_horario_id = request.form['old_horario_id']
                try:
                    cur = mysql.connection.cursor()
                    cur.execute("DELETE FROM detalle_horario WHERE materia_id_materia=%s AND horario_id_horario=%s",
                                (old_materia_id, old_horario_id))
                    mysql.connection.commit()
                    flash('Relación eliminada exitosamente')
                except Exception as e:
                    mysql.connection.rollback()
                    flash(f'Error al eliminar relación: {str(e)}')
                finally:
                    cur.close()
                return redirect(url_for('materia_hora', espe=session['espe']))
        else:
            return redirect(url_for('login'))

    @app.route('/<espe>')
    def elegir_curso(espe):
        if 'role' in session and (session['role'] == 'administrador' or session['role'] == 'encargado'):
            if espe == 'Construccion civil' or espe == 'Quimica' or espe == 'Electronica':
                return render_template('tres.html', espe=espe)
            else:
                return render_template('dos.html', espe=espe)
        else:
            flash('Access Denied. Please login as administrator.')
            return redirect(url_for('login'))

    @app.route('/<espe>/<curso>/<seccion>')
    def reportes(espe, curso, seccion):
        if 'role' in session:   
            if session['role'] == 'administrador' or session['role'] == 'encargado':
                cur = mysql.connection.cursor()
                cur.execute(
                    "SELECT id_horario FROM horario where curso=%s and seccion=%s and especialidad=%s", (curso, seccion, espe))
                s = cur.fetchone()
                session['cursosec'] = s
                cur.execute("SELECT * FROM reporte")
                reportes = cur.fetchall()
                if espe:
                    cur.execute("SELECT row_number() over (order by apellido asc) as n_lista, CONCAT(apellido, ' ', nombre) AS nombre_completo, curso, seccion, especialidad, ci FROM alumno WHERE especialidad = %s and curso=%s and seccion=%s order by apellido asc", (espe, curso, seccion))
                else:
                    cur.execute("SELECT * FROM alumno")
                alumnos = cur.fetchall()
                cur.execute(
                    "SELECT id_horario FROM horario WHERE curso=%s and seccion=%s and especialidad=%s", (curso, seccion, espe))
                a = cur.fetchone()
                if a:
                    hor = a[0]
                    cur.execute(
                        "SELECT materia_id_materia FROM detalle_horario WHERE horario_id_horario = %s", (hor,))
                    materiasid = cur.fetchall()
                else:
                    cur.execute("SELECT * FROM materia")
                    materiasid = []
                if materiasid:
                    materias = []
                    for mid in materiasid:
                        aa = mid[0]
                        cur.execute(
                            "SELECT * FROM materia WHERE id_materia = %s", (aa,))
                        materias.extend(cur.fetchall())
                else:
                    cur.execute("SELECT * FROM materia")
                    materias = cur.fetchall()
                cur.execute("SELECT * FROM detalle_horario")
                detalle_horario = cur.fetchall()
                cur.execute("SELECT * FROM rasgos_conductuales")
                rasgos_conductuales = cur.fetchall()
                if a:
                    cur.execute(
                        "SELECT * FROM detalle_horario WHERE horario_id_horario = %s", (a,))
                    elid = cur.fetchall()
                else:
                    elid = []
                cur.execute("SELECT * FROM detalle_reporte")
                detr = cur.fetchall()
                cur.execute(
                    "SELECT id_alumno FROM alumno WHERE especialidad = %s and curso=%s and seccion=%s order by apellido asc", (espe, curso, seccion))
                ida = cur.fetchall()

    # 这里确保我们只传递单个值而不是一个元组
                a = []
                for id_alumno in ida:
                    cur.execute(
                        "SELECT id_reporte FROM reporte WHERE alumno_id_alumno = %s", (id_alumno[0],))
                    a.extend(cur.fetchall())

                a = cur.fetchall()
                cur.close()
                return render_template('reportes.html', role=session['role'], reportes=reportes, alumnos=alumnos, materias=materias, detalle_horario=detalle_horario, rasgos_conductuales=rasgos_conductuales, elid=elid, curso=int(curso), seccion=int(seccion), espe=espe, detr=detr, a=a)
        return redirect(url_for('login'))

    @app.route('/get_rasgos', methods=['GET'])
    def get_rasgos():
        ci = request.args.get('ci')
        fecha = request.args.get('fecha')
        materia = request.args.get('materia')
        horario = request.args.get('horario')

        if not ci or not fecha or not materia or not horario:
            return jsonify(success=False, message="Missing parameters"), 400

        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT rasgos_conductuales_id_rasgo FROM detalle_rasgos
            WHERE ci = %s AND fecha = %s AND materia = %s AND horario = %s
        """, (ci, fecha, materia, horario))
        rasgos = cur.fetchall()
        cur.close()

        return jsonify(success=True, rasgos=[r[0] for r in rasgos])

    @app.route('/submit', methods=['POST'])
    def submit():
        print("submit")
        data = request.get_json()
        fecha = data.get('fecha', '').strip()
        materia = data.get('materiaSelect', '').strip()
        hor = data.get('horariosSelect', '').strip()
        curs = session.get('cursosec')
        curs = curs[0]
        operation = request.args.get('operation')
        cur = mysql.connection.cursor()
        cur.execute(
            "SELECT horario FROM detalle_horario WHERE materia_id_materia=%s AND horario_id_horario=%s", (materia, curs))
        m = cur.fetchone()
        if m:
            m = m[0]
        items = data.get('items', [])
        for item in items:
            ci = item['id']
            values = item['values']
            values = [v for v in values if v != "13"]
            cur.execute("select id_alumno from alumno where ci=%s", (ci,))
            ids = cur.fetchone()
            # Verifica si ya existe un reporte con la misma hora, fecha y alumno
            cur.execute(
                "SELECT id_reporte FROM reporte WHERE horario=%s AND fecha=%s AND Alumno_id_alumno=%s", (m, fecha, ids))
            existing_reporte = cur.fetchone()
            if values:
                if existing_reporte:
                    cur.execute(
                        "select Rasgos_Conductuales_id_rasgo from detalle_reporte where Reporte_id_reporte=%s", (existing_reporte))
                    existing_rasgos = cur.fetchall()
                    for actual_rasgo in existing_rasgos:
                        exists = False
                        for new_rasgo in values:
                            if actual_rasgo == new_rasgo:
                                exists = True
                        if not exists:
                            cur.execute("delete from detalle_reporte where Rasgos_Conductuales_id_rasgo=%s and Reporte_id_reporte=%s", (
                                actual_rasgo, existing_reporte))
                    for new_rasgo in values:
                        exists = False
                        for actual_rasgo in existing_rasgos:
                            if new_rasgo == actual_rasgo:
                                exists = True
                        if not exists:
                            cur.execute(
                                "INSERT INTO detalle_reporte (Reporte_id_reporte, Rasgos_Conductuales_id_rasgo) VALUES (%s, %s)", (existing_reporte, new_rasgo))
                else:
                    cur.execute(
                        "INSERT INTO reporte (horario, fecha, Alumno_id_alumno, Materia_id_materia) VALUES (%s, %s, %s, %s)", (m, fecha, ids, materia))
                    reporte_id = cur.lastrowid
                    for value in values:
                        # Mensaje de depuración
                        print(f"Inserting rasgo ID: {value}")
                        cur.execute(
                            "INSERT INTO detalle_reporte (reporte_id_reporte, Rasgos_Conductuales_id_rasgo) VALUES (%s, %s)", (reporte_id, value))
            else:
                if existing_reporte:
                    cur.execute(
                        "delete from detalle_reporte where Reporte_id_reporte=%s", (existing_reporte))
                    cur.execute(
                        "delete from reporte where id_reporte=%s", (existing_reporte))
        mysql.connection.commit()
        cur.close()
        return jsonify(message="Ejecutado agregar")

    @app.route('/mostrar')
    def mostrar():
        if session['role'] == 'alumno':
            cur = mysql.connection.cursor()

            # 获取学生信息
            cur.execute("SELECT * FROM alumno WHERE ci = %s", (session['ci'],))
            alum = cur.fetchall()

            # 获取学生ID
            cur.execute("SELECT id_alumno FROM alumno WHERE ci = %s",
                        (session['ci'],))
            idalumno = cur.fetchone()
            if idalumno:
                idalumno = idalumno[0]

            # 获取报告信息
            cur.execute(
                "SELECT * FROM reporte WHERE alumno_id_alumno=%s", (idalumno,))
            rep = cur.fetchall()

            # 获取每个报告的ID和对应的行为特征ID
            idrep_list = []
            rasgos_dict = {}
            for report in rep:
                idrep = report[0]
                idrep_list.append(idrep)

                # 获取每个报告对应的行为特征ID
                cur.execute(
                    "SELECT rasgos_conductuales_id_rasgo FROM detalle_reporte WHERE reporte_id_reporte=%s", (idrep,))
                rasgos_ids = cur.fetchall()
                rasgos_dict[idrep] = [r[0] for r in rasgos_ids]

            # 获取学科ID和名称
            mat_dict = {}
            for idrep in idrep_list:
                cur.execute(
                    "SELECT materia_id_materia FROM reporte WHERE id_reporte=%s", (idrep,))
                mat = cur.fetchone()
                if mat:
                    mat = mat[0]
                    cur.execute(
                        "SELECT nombre FROM materia WHERE id_materia=%s", (mat,))
                    mat_name = cur.fetchone()
                    if mat_name:
                        mat_dict[idrep] = mat_name[0]

            # 获取所有行为特征描述
            rasgos_desc_dict = {}
            for idrep, rasgos_ids in rasgos_dict.items():
                rasgos_desc_dict[idrep] = []
                for idrasgo in rasgos_ids:
                    cur.execute(
                        "SELECT descripcion FROM rasgos_conductuales WHERE id_rasgo=%s", (idrasgo,))
                    desc = cur.fetchone()
                    if desc:
                        rasgos_desc_dict[idrep].append(desc[0])

            cur.close()
            return render_template('mt.html', rep=rep, alum=alum, mat_dict=mat_dict, rasgos_desc_dict=rasgos_desc_dict)

    @app.route('/<espe>/<curso>/<seccion>/imprimir')
    def imprimir(espe, curso, seccion):

        print(f"Current role: {session.get('role')}")
        
        if session.get('role') == 'administrador' or session.get('role') == 'enc':
            cur = mysql.connection.cursor()
            
            # 初始化变量
            alum = []
            rep = []
            mat_dict = {}
            rasgos_desc_dict = {}

            try:
                # 获取学生信息
                cur.execute("SELECT * FROM alumno WHERE especialidad = %s AND curso = %s AND seccion = %s", (espe, curso, seccion))
                alum = cur.fetchall()
                print(f"Students: {alum}")  # 调试输出

                # 如果有学生
                if alum:
                    # 获取学生ID
                    idalumno_list = [alumno[0] for alumno in alum]
                    print(f"ID Alumno List: {idalumno_list}")  # 打印 ID 列表

                    if idalumno_list:
                        # 创建占位符字符串 (%s, %s, %s...)
                        placeholders = ', '.join(['%s'] * len(idalumno_list))

                        # 查询多个报告信息
                        query = f"SELECT * FROM reporte WHERE alumno_id_alumno IN ({placeholders})"
                        cur.execute(query, tuple(idalumno_list))
                        rep = cur.fetchall()
                        print(f"Reports: {rep}")  # 调试输出

                        # 获取每个报告的ID和对应的行为特征ID
                        idrep_list = [report[0] for report in rep]
                        print(f"ID Report List: {idrep_list}")  # 打印 ID Report 列表

                        # 创建行为特征字典
                        for idrep in idrep_list:
                            cur.execute("SELECT rasgos_conductuales_id_rasgo FROM detalle_reporte WHERE reporte_id_reporte=%s", (idrep,))
                            rasgos_ids = cur.fetchall()
                            rasgos_desc_dict[idrep] = [r[0] for r in rasgos_ids]
                        
                        print(f"Rasgos dictionary: {rasgos_desc_dict}")  # 调试输出

                        # 获取学科ID和名称
                        for idrep in idrep_list:
                            cur.execute("SELECT materia_id_materia FROM reporte WHERE id_reporte=%s", (idrep,))
                            mat_id = cur.fetchone()
                            if mat_id:
                                cur.execute("SELECT nombre FROM materia WHERE id_materia=%s", (mat_id[0],))
                                mat_name = cur.fetchone()
                                if mat_name:
                                    mat_dict[idrep] = mat_name[0]
                        
                        print(f"Materia dictionary: {mat_dict}")  # 调试输出

                        # 获取行为特征描述
                        for idrep, rasgos_ids in rasgos_desc_dict.items():
                            rasgos_desc_dict[idrep] = []
                            for idrasgo in rasgos_ids:
                                cur.execute("SELECT descripcion FROM rasgos_conductuales WHERE id_rasgo=%s", (idrasgo,))
                                desc = cur.fetchone()
                                if desc:
                                    rasgos_desc_dict[idrep].append(desc[0])
                        
                        print(f"Rasgos descriptions: {rasgos_desc_dict}")  # 调试输出

            except Exception as e:
                print(f"Error: {e}")
            finally:
                cur.close()

            return render_template('imprimir.html', rep=rep, alum=alum, mat_dict=mat_dict, rasgos_desc_dict=rasgos_desc_dict, espe=session['espe'], curso=curso, seccion=seccion)
        else:
            return "Unauthorized", 403




    @app.route('/check_materia', methods=['POST'])
    def check_materia():
        # Recibiendo los datos enviados por la solicitud POST
        data = request.json
        nombre = data.get('nombre')  # Recibe el nombre de la materia
        especialidad = data.get('espe')  # Recibe la especialidad
        curso = data.get('anios')  # Recibe el ID del curso/horario

        # Imprime los datos recibidos para verificación
        print(f"Materia nombre recibido: {nombre}")
        print(f"Especialidad recibida: {especialidad}")
        print(f"Curso nombre recibido: {curso}")

        try:
            # Consulta a la base de datos
            cur = mysql.connection.cursor()
            # Asegúrate de pasar los parámetros correctamente dentro de una tupla
            cur.execute("SELECT * FROM materia WHERE nombre = %s AND especialidad = %s AND cursos = %s", (nombre, especialidad, curso))
            count = cur.fetchone()

            # Imprime el resultado de la consulta
            print(f"Resultado de la consulta: {count}")

            # Determina si la asignatura ya existe en el curso
            existe = count is not None

        except Exception as e:
            # Imprimir el error si ocurre
            print(f"Error en la consulta: {e}")
            existe = False

        finally:
            cur.close()

        return jsonify({'existe': existe})



    
    
    @app.route('/check_materia_edit', methods=['POST'])
    def check_materia_edit():
        data = request.json
        id_materia = data.get('id')
        nombre = data.get('nombre')
        espe = data.get('espe')
        curso = data.get('anios') 
        print("Datos recibidos en el servidor:", data)

        # Conexión a la base de datos
        cur = mysql.connection.cursor()

        try:
            # Verificar si la materia con el ID dado existe y pertenece a la especialidad o es 'Plan Común'
            query = """
                SELECT especialidad 
                FROM materia 
                WHERE id_materia = %s
            """
            cur.execute(query, (id_materia,))
            result = cur.fetchone()
            print("Resultado de la consulta de especialidad:", result)

            if espe:
                existing_espe = result[0]
                print("Especialidad existente:", existing_espe)

                # Verificar que la especialidad sea la correcta
                if existing_espe != espe and existing_espe != 'Plan Común':
                    return jsonify({'error': f'El ID introducido no existe.'})

                # Verificar si ya existe una materia con el mismo nombre pero diferente ID
                query = """
                    SELECT id_materia 
                    FROM materia 
                    WHERE nombre = %s AND id_materia != %s
                """
                cur.execute(query, (nombre, id_materia))
                existing_materia = cur.fetchone()
                print("Resultado de la consulta de nombre existente:", existing_materia)
                
                if existing_materia:
                    return jsonify({'existe': True, 'espe': existing_espe})
                else:
                    return jsonify({'existe': False, 'espe': existing_espe})
            else:
                print("No se encontró la materia o no pertenece a la especialidad indicada.")
                return jsonify({'error': 'No se encontró la materia o no pertenece a la especialidad indicada.'})
        except Exception as e:
            print("Error al consultar la base de datos:", e)
            return jsonify({'error': 'Hubo un problema al verificar la materia. Por favor, intente nuevamente.'})
        finally:
            cur.close()








    @app.route('/check_delete_materia', methods=['POST'])
    def check_delete_materia():
        data = request.get_json()
        subject_id = data.get('subject_id')
        espe = data.get('espe')

        print(f"Received request with subject_id: {subject_id} and espe: {espe}")

        # Consulta la base de datos para obtener la especialidad de la materia
        cur = mysql.connection.cursor()
        cur.execute("SELECT especialidad FROM materia WHERE id_materia = %s", (subject_id,))
        result = cur.fetchone()
        cur.close()

        if result:
            espe_materia = result[0]
            print(f"Specialty of the subject with id {subject_id} is: {espe_materia}")

            # Permitir eliminación si la materia es de 'Plan Común' o si la especialidad de la materia coincide con la especialidad proporcionada
            if espe_materia == 'Plan Común' or espe_materia == espe:
                return jsonify({'existe': True, 'espe': espe_materia})
            else:
                error_message = 'La materia pertenece a una especialidad diferente.'
                print(error_message)
                return jsonify({'existe': True, 'espe': espe_materia, 'error': error_message})
        else:
            print(f"No subject found with id {subject_id}")
            return jsonify({'existe': False, 'espe': None})



    @app.route('/check_matehora', methods=['POST'])
    def check_matehora():
        data = request.get_json()
        horario_id_horario = data.get('horario_id_horario')
        materia_id_materia = data.get('materia_id_materia')
        horario = data.get('horario')
        dia = data.get('dia')

        if not horario_id_horario or not materia_id_materia or not horario or not dia:
            return jsonify({'error': 'Todos los campos son obligatorios'}), 400

        try:
            # Conectar a la base de datos
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT * FROM detalle_horario WHERE materia_id_materia = %s AND horario_id_horario = %s AND horario = %s AND dia = %s",
                (materia_id_materia, horario_id_horario, horario, dia)
            )
            matehora_existe = cur.fetchone()
            cur.close()

            # Devolver respuesta JSON
            if matehora_existe:
                return jsonify({'existe': True})
            else:
                return jsonify({'existe': False})

        except Exception as e:
            app.logger.error(f"Error: {e}")  # Log del error para depuración
            return jsonify({'error': 'Error interno del servidor'}), 500

    @app.route('/check_profemate', methods=['POST'])
    def check_profemate():
        data = request.get_json()
        materia_id_materia = data.get('materia_id_materia')
        profesor_id_profesor = data.get('profesor_id_profesor')

        if not materia_id_materia or not profesor_id_profesor:
            return jsonify({'error': 'Los campos "materia" y "profesor" son obligatorios'}), 400

        try:
            # Conectar a la base de datos
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT * FROM materia_por_profesor WHERE materia_id_materia = %s AND profesor_id_profesor = %s",
                (materia_id_materia, profesor_id_profesor)
            )
            profemate_existente = cur.fetchone()
            cur.close()

            # Devolver respuesta JSON
            if profemate_existente:
                return jsonify({'existe': True})
            else:
                return jsonify({'existe': False})

        except Exception as e:
            app.logger.error(f"Error: {e}")  # Log del error para depuración
            return jsonify({'error': 'Error interno del servidor'}), 500
        
    @app.route('/check_profmate_edit', methods=['POST'])
    def check_profmate_edit():
        data = request.get_json()
        old_materia_id = data.get('old_materia_id')
        old_profesor_id = data.get('old_profesor_id')
        new_materia_id = data.get('new_materia_id')
        new_profesor_id = data.get('new_profesor_id')

        if not old_materia_id or not old_profesor_id or not new_materia_id or not new_profesor_id:
            return jsonify({'error': 'Todos los campos son obligatorios'}), 400

        try:
            cur = mysql.connection.cursor()

            # Verifica si la relación antigua existe
            cur.execute(
                "SELECT COUNT(*) FROM materia_por_profesor WHERE materia_id_materia = %s AND profesor_id_profesor = %s",
                (old_materia_id, old_profesor_id)
            )
            existe_relacion_antigua = cur.fetchone()[0] > 0

            if not existe_relacion_antigua:
                cur.close()
                return jsonify({'error': 'La relación antigua no existe'}), 404

            # Verifica si la nueva relación ya existe
            cur.execute(
                "SELECT COUNT(*) FROM materia_por_profesor WHERE materia_id_materia = %s AND profesor_id_profesor = %s",
                (new_materia_id, new_profesor_id)
            )
            existe_nueva_relacion = cur.fetchone()[0] > 0

            cur.close()

            return jsonify({
                'existe_relacion_antigua': existe_relacion_antigua,
                'existe_nueva_relacion': existe_nueva_relacion
            })

        except Exception as e:
            print(f'Error en check_profmate_edit: {e}')
            return jsonify({'error': 'Error interno del servidor'}), 500








    @app.route('/check_curso', methods=['POST'])
    def check_curso():
        data = request.get_json()
        curso = data.get('curso')
        seccion = data.get('seccion')
        espe = data.get('espe')  # Recibir la especialidad

        if not curso or not seccion or not espe:
            return jsonify({'error': 'Los campos "curso", "seccion" y "especialidad" son obligatorios'}), 400

        try:
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT * FROM horario WHERE curso = %s AND seccion = %s AND especialidad = %s", 
                (curso, seccion, espe)
            )
            curso_existente = cur.fetchone()
            cur.close()

            if curso_existente:
                return jsonify({'existe': True})
            else:
                return jsonify({'existe': False})

        except Exception as e:
            print(f'Error en check_curso: {e}')
            return jsonify({'error': 'Error interno del servidor'}), 500




    @app.route('/check_curso_edit', methods=['POST'])
    def check_curso_edit():
        data = request.get_json()
        curso = data.get('curso')
        seccion = data.get('seccion')
        espe = data.get('espe')
        id_horario = data.get('id_horario')  # ID del curso que se está editando

        # Imprimir valores recibidos
        print(f'Recibido: curso={curso}, seccion={seccion}, especialidad={espe}, id_horario={id_horario}')

        # Verificación de campos vacíos
        if not curso or not seccion or not id_horario or not espe:
            print('Error: Campos vacíos')
            return jsonify({'error': 'Los campos "curso", "seccion", "especialidad" e "id_horario" son obligatorios'}), 400

        try:
            # Conectar a la base de datos
            cur = mysql.connection.cursor()
            print('Conexión a la base de datos establecida.')

            # Verificar si el ID existe en la especialidad correspondiente
            cur.execute("SELECT * FROM horario WHERE id_horario = %s AND especialidad = %s", (id_horario, espe))
            id_existente = cur.fetchone()

            if not id_existente:
                print(f'Error: El ID {id_horario} no pertenece a la especialidad {espe}')
                cur.close()
                return jsonify({'error': 'El ID no pertenece a la especialidad'}), 404

            # Verificar si el curso ya existe (excluyendo el ID actual)
            cur.execute(
                "SELECT * FROM horario WHERE curso = %s AND seccion = %s AND id_horario != %s AND especialidad = %s",
                (curso, seccion, id_horario, espe)
            )
            curso_existente = cur.fetchone()
            cur.close()

            # Devolver respuesta JSON
            if curso_existente:
                print('Curso existente encontrado.')
                return jsonify({'existe': True, 'mismo_id': False})
            else:
                print('Curso no encontrado.')
                return jsonify({'existe': False, 'mismo_id': True})

        except Exception as e:
            # Registro del error para depuración
            print(f'Error en check_curso_edit: {e}')
            return jsonify({'error': 'Error interno del servidor'}), 500


    @app.route('/check_curso_delete', methods=['POST'])
    def check_curso_delete():
        data = request.get_json()
        id_horario = data.get('id_horario')
        espe = data.get('espe')

        # Imprimir valores recibidos
        print(f'Recibido: id_horario={id_horario}, especialidad={espe}')

        if not id_horario or not espe:
            print('Error: Campos vacíos')
            return jsonify({'error': 'Los campos "id_horario" y "especialidad" son obligatorios'}), 400

        try:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM horario WHERE id_horario = %s AND especialidad = %s", (id_horario, espe))
            curso_existente = cur.fetchone()
            cur.close()

            if not curso_existente:
                print(f'Error: El ID {id_horario} no pertenece a la especialidad {espe}')
                return jsonify({'error': 'ID no existe o no pertenece a la especialidad'}), 404

            # Si el curso existe y pertenece a la especialidad
            return jsonify({'existe': True})

        except Exception as e:
            # Registro del error para depuración
            print(f'Error en check_curso_delete: {e}')
            return jsonify({'error': 'Error interno del servidor'}), 500



    @app.route('/check_profe', methods=['POST'])
    def check_profe():
        data = request.get_json()
        nombre = data.get('nombre')
        apellido = data.get('apellido')

        # Verificación de campos vacíos
        if not nombre or not apellido:
            return jsonify({'error': 'Los campos "nombre" y "apellido" son obligatorios'}), 400

        try:
            # Conectar a la base de datos
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT * FROM profesor WHERE nombre = %s AND apellido = %s", (nombre, apellido))
            profesor_existente = cur.fetchone()
            cur.close()

            # Devolver respuesta JSON
            if profesor_existente:
                return jsonify({'existe': True})
            else:
                return jsonify({'existe': False})

        except Exception as e:
            # Registro del error para depuración
            print(f'Error en check_profe: {e}')
            return jsonify({'error': 'Error interno del servidor'}), 500

    @app.route('/check_profe_edit', methods=['POST'])
    def check_profe_edit():
        data = request.get_json()
        nombre = data.get('nombre')
        apellido = data.get('apellido')
        id_profesor = data.get('id_profesor')

        if not nombre or not apellido or not id_profesor:
            return jsonify({'error': 'Los campos "nombre", "apellido" y "id_profesor" son obligatorios'}), 400

        try:
            cur = mysql.connection.cursor()
            
            # Verificar si el ID del profesor existe
            cur.execute("SELECT * FROM profesor WHERE id_profesor = %s", (id_profesor,))
            profesor_existente = cur.fetchone()
            if not profesor_existente:
                cur.close()
                return jsonify({'error': 'El ID del profesor no existe'}), 404

            # Verificar si existe otro profesor con el mismo nombre y apellido pero diferente ID
            cur.execute(
                "SELECT * FROM profesor WHERE nombre = %s AND apellido = %s AND id_profesor != %s",
                (nombre, apellido, id_profesor)
            )
            profesor_existente = cur.fetchone()
            cur.close()

            if profesor_existente:
                return jsonify({'existe': True, 'mismo_id': False})
            else:
                return jsonify({'existe': False, 'mismo_id': True})

        except Exception as e:
            print(f'Error en check_profe_edit: {e}')
            return jsonify({'error': 'Error interno del servidor'}), 500
        
    @app.route('/check_profe_delete', methods=['POST'])
    def check_profe_delete():
        data = request.get_json()
        id_profesor = data.get('id_profesor')
        espe = data.get('espe')  # Obtener la especialidad enviada desde el frontend
        
        if not id_profesor or not espe:
            return jsonify({'error': 'Los campos ID del Profesor y Especialidad son obligatorios'}), 400

        try:
            cur = mysql.connection.cursor()

            # Verificar si el ID del profesor existe y pertenece a la especialidad
            cur.execute("SELECT * FROM profesor WHERE id_profesor = %s AND especialidad = %s", (id_profesor, espe))
            profesor_existente = cur.fetchone()
            
            if not profesor_existente:
                cur.close()
                return jsonify({'error': 'El ID del profesor no existe o no pertenece a la especialidad'}), 404

            # Si el ID y la especialidad coinciden, permitir la eliminación
            cur.close()
            return jsonify({'existe': True})

        except Exception as e:
            print(f'Error en check_profe_delete: {e}')
            return jsonify({'error': 'Error interno del servidor'}), 500


    
    @app.route('/check_ci', methods=['POST'])
    def check_ci():
        data = request.get_json()
        ci = data.get('ci')
        espe = data.get('espe')

        if not ci or not espe:
            return jsonify({'error': 'Todos los campos son obligatorios'}), 400

        try:
            with mysql.connection.cursor() as cur:
                # Verificar si el alumno con el CI existe en cualquier especialidad
                cur.execute("SELECT especialidad FROM alumno WHERE ci = %s", (ci,))
                resultado = cur.fetchone()

                # Devolver respuesta JSON
                if resultado:
                    espe_actual = resultado[0]
                    if espe_actual == espe:
                        return jsonify({'existe': True, 'espe': espe_actual})
                    else:
                        return jsonify({'existe': True, 'espe': espe_actual})
                else:
                    return jsonify({'existe': False})

        except Exception as e:
            return jsonify({'error': 'Ocurrió un error al verificar el CI: ' + str(e)}), 500



    # ////////////////////////////////////////////////////////
    @app.route('/check_conductuales', methods=['POST'])
    def check_conductuales():
        if 'role' in session and session['role'] == 'administrador':
            data = request.get_json()
            descripcion = data.get('descripcion')

            try:
                cur = mysql.connection.cursor()
                # Verifica si la descripción ya existe
                cur.execute("SELECT * FROM rasgos_conductuales WHERE descripcion = %s", (descripcion,))
                existing_record = cur.fetchone()

                if existing_record:
                    return jsonify({'existe': True, 'message': 'El rasgo conductual ya existe.'}), 400

                # Si no existe, inserta el nuevo rasgo
                cur.execute("INSERT INTO rasgos_conductuales (descripcion) VALUES (%s)", (descripcion,))
                mysql.connection.commit()

                return jsonify({'existe': False, 'message': 'Rasgo conductual agregado exitosamente.'}), 200

            except Exception as e:
                mysql.connection.rollback()
                return jsonify({'existe': False, 'message': f'Error al agregar rasgo: {str(e)}'}), 500

            finally:
                cur.close()
        else:
            return jsonify({'existe': False, 'message': 'No autorizado'}), 403
        
    @app.route('/check_conductuales_edit', methods=['POST'])
    def check_conductuales_edit():
        data = request.get_json()
        descripcion = data.get('descripcion')
        id_rasgo = data.get('id_rasgo')  # ID del rasgo conductual que se está editando

        # Verificación de campos vacíos
        if not descripcion or not id_rasgo:
            return jsonify({'error': 'Los campos "descripcion" e "id_rasgo" son obligatorios'}), 400

        try:
            # Conectar a la base de datos
            cur = mysql.connection.cursor()
            
            # Verificar si el ID existe
            cur.execute("SELECT * FROM rasgos_conductuales WHERE id_rasgo = %s", (id_rasgo,))
            rasgo_existente = cur.fetchone()
            
            if not rasgo_existente:
                cur.close()
                return jsonify({'error': 'ID no existe'}), 404
            
            # Verifica si existe otro rasgo con la misma descripción pero diferente ID
            cur.execute(
                "SELECT * FROM rasgos_conductuales WHERE descripcion = %s AND id_rasgo != %s",
                (descripcion, id_rasgo)
            )
            rasgo_existente = cur.fetchone()
            cur.close()

            # Devolver respuesta JSON
            if rasgo_existente:
                return jsonify({'existe': True, 'mismo_id': False})
            else:
                return jsonify({'existe': False, 'mismo_id': True})

        except Exception as e:
            # Registro del error para depuración
            print(f'Error en check_conductuales_edit: {e}')
            return jsonify({'error': 'Error interno del servidor'}), 500
        
    @app.route('/check_conductuales_delete', methods=['POST'])
    def check_conductuales_delete():
        data = request.get_json()
        id_conductual = data.get('id_conductual')

        # Verificación de campos vacíos
        if not id_conductual:
            return jsonify({'error': 'El campo "id_conductual" es obligatorio'}), 400

        try:
            # Conectar a la base de datos
            cur = mysql.connection.cursor()
            
            # Verificar si el ID existe
            cur.execute("SELECT * FROM rasgos_conductuales WHERE id_rasgo = %s", (id_conductual,))
            rasgo_existente = cur.fetchone()
            cur.close()

            if not rasgo_existente:
                return jsonify({'error': 'ID no existe'}), 404

            # Devolver respuesta JSON
            return jsonify({'existe': True})

        except Exception as e:
            # Registro del error para depuración
            print(f'Error en check_conductuales_delete: {e}')
            return jsonify({'error': 'Error interno del servidor'}), 500






    @app.route('/check_email', methods=['POST'])
    def check_email():
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': 'El campo de correo electrónico es obligatorio'})

        # Validar formato de correo electrónico
        if not EMAIL_PATTERN.match(email):
            return jsonify({'error': 'El correo electrónico no tiene un formato válido'})

        try:
            # Conectar a la base de datos
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM alumno WHERE email = %s", (email,))
            email_existente = cur.fetchone()
            cur.close()

            # Devolver respuesta JSON
            if email_existente:
                return jsonify({'existe': True})
            else:
                return jsonify({'existe': False})

        except Exception as e:
            return jsonify({'error': str(e)})
    @app.route('/<ci_alumno>/get_reporte', methods=['GET', 'POST'])
    def get_reporte(ci_alumno):
        try:
            # Conectar a la base de datos
            cur = mysql.connection.cursor()
            cur.execute("SELECT id_alumno from alumno where ci = %s", (ci_alumno, ))
            resultado = cur.fetchone()
            if(resultado):
                id_alumno = resultado
                cur.execute("SELECT * FROM reporte WHERE Alumno_id_alumno = %s", (id_alumno,))
                reporte = cur.fetchall()
                cur.close()
                return jsonify(reporte)
            else:
                return jsonify({'error': 'Alumno no encontrado'}), 404
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    # ///////////////////////////////////////////////////////
    
    


    @app.route('/check_materia_horario', methods=['POST'])
    def check_materia_horario():
        if 'role' in session and session['role'] == 'administrador':
            materia_id = request.form.get('materia_id')
            horario_id = request.form.get('horario_id')

            cur = mysql.connection.cursor()
            # 查询是否存在该关系
            cur.execute("""
                SELECT * FROM detalle_horario 
                WHERE materia_id_materia = %s AND horario_id_horario = %s
            """, (materia_id, horario_id))
            result = cur.fetchone()
            
            cur.close()

            if result:
                return jsonify({'exists': True})  # 关系已存在
            else:
                return jsonify({'exists': False})  # 关系不存在

        else:
            return jsonify({'error': 'Acceso denegado.'})
        
    @app.route('/check_materia_horario_edit', methods=['POST'])
    def check_materia_horario_edit():
        if 'role' in session and session['role'] == 'administrador':
            materia_id = request.form.get('materia_id')
            horario_id = request.form.get('horario_id')

            cur = mysql.connection.cursor()
            # 查询是否存在该关系
            cur.execute("""
                SELECT * FROM detalle_horario 
                WHERE materia_id_materia = %s AND horario_id_horario = %s
            """, (materia_id, horario_id))
            result = cur.fetchone()
            cur.close()

            if result:
                return jsonify({'exists': True})  # 关系已存在
            else:
                return jsonify({'exists': False})  # 关系不存在
    @app.route('/check_materia_horario_delete', methods=['POST'])
    def check_materia_horario_delete():
        if 'role' in session and session['role'] == 'administrador':
            data = request.get_json()  # 获取 JSON 数据
            materia_id = data.get('materiaId')  # 从 JSON 中提取 materiaId
            horario_id = data.get('cursoId')  # 从 JSON 中提取 cursoId

            cur = mysql.connection.cursor()
            # 查询是否存在该关系
            cur.execute("""
                SELECT * FROM detalle_horario 
                WHERE materia_id_materia = %s AND horario_id_horario = %s
            """, (materia_id, horario_id))
            result = cur.fetchone()
            cur.close()

            if not result:
                return jsonify({'error': 'ID no existe'}), 404  # 关系不存在
            return jsonify({'message': 'existe'})  # 关系存在

        else:
            return jsonify({'error': 'Acceso denegado.'}), 403  # 权限问题

    @app.route('/check_materia_repeat', methods=['POST'])
    def check_materia_repeat():
        if 'role' in session and session['role'] == 'administrador':
            horario_id = request.form.get('horario_id')
            dia=request.form.get('dia')
            horario = request.form.get('horario')

            cur = mysql.connection.cursor()
            # 查询是否存在该关系
            cur.execute("""
                SELECT * FROM detalle_horario 
                WHERE  horario_id_horario = %s and horario=%s and dia=%s
            """, ( horario_id,horario,dia ))
            result = cur.fetchone()
            cur.close()

            if result:
                return jsonify({'exists': True})  # 关系已存在
            else:
                return jsonify({'exists': False})  # 关系不存在
    @app.route("/<espe>/<curso>/<seccion>/send-email", methods=["POST"])
    def send_email(espe, curso, seccion):
        if session['role'] == 'administrador' or session['role'] == 'encargado':
            cur = mysql.connection.cursor()
            try:
                year = request.form.get('year')
                month = request.form.get('month')
                print(year, month)
                cur.execute("Select * from alumno where especialidad = %s and curso = %s and seccion = %s", (espe, curso, seccion))
                alumnos = cur.fetchall()
                for alumno in alumnos:
                    print(alumno)
                    cur.execute("Select id_reporte from reporte where Alumno_id_alumno = %s and YEAR(fecha) = %s and MONTH(fecha) = %s", (alumno[0], year, month))
                    id_reportes = cur.fetchall()
                    print(id_reportes)
                    if id_reportes:
                        reportes = {}
                        rasgos = {}
                        cur.execute("Select Correo_encargado from alumno where id_alumno = %s", (alumno[0], ))
                        email = cur.fetchone()
                        if not email_valido(email[0]):
                            print("El email asociado a " + alumno[1] + " " + alumno[2] + " es invalido.")
                            continue
                        cur.execute("Select * from reporte where Alumno_id_alumno = %s and YEAR(fecha) = %s and MONTH(fecha) = %s", (alumno[0], year, month))
                        reportes = cur.fetchall()
                        print(reportes)
                        for idr in id_reportes:
                            print(idr)
                            cur.execute("""SELECT rc.descripcion 
                                            FROM detalle_reporte dr
                                            JOIN Rasgos_Conductuales rc ON dr.Rasgos_Conductuales_id_rasgo = rc.id_rasgo
                                            WHERE dr.Reporte_id_reporte = %s""", (idr[0],))
                            rasgos[idr[0]] = [re.sub(r'\s+', ' ', r[0]).strip() for r in cur.fetchall()]
                        print(rasgos)
                        rendered = render_template('enviar.html', reportes=reportes, rasgos=rasgos, alumno=alumno, id_reportes=id_reportes)
                        pdf = pdfkit.from_string(rendered, False)
                        msg = Message('Reporte Conductual de ' + alumno[1] + ' ' + alumno[2] , sender='reportesctn@outlook.com', recipients=['luanycastillo66@gmail.com'])
                        msg.body = "Reporte Conductual del mes " + month + " del alumno " + alumno[1] + " " + alumno[2]
                        msg.attach((alumno[1] + " " + alumno[2] +".pdf"), "application/pdf", pdf)
                        mail.send(msg)
                        print('Email de ' + alumno[1] + ' ' + alumno[2] + ' enviado!')
            except Exception as e:
                print(f"Error: {e}")
                print("holi")
            finally:
                cur.close()
        else:
            return "Unauthorized", 403
        return("Emails enviados!")
    @app.route("/<espe>/<curso>/<seccion>/report")
    def seleccion_add_imp(espe, curso, seccion):
        return render_template('seleccion.html', espe=espe, curso=curso, seccion=seccion)
    return app
def email_valido(email):
    try:
        v = validate_email(email)
        return True
    except EmailNotValidError:
        return False


if __name__ == '__main__':
    app = crear_app()
    app.run(debug=True, host='0.0.0.0')

