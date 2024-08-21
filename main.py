from flask import Flask, render_template, request, redirect, url_for, flash, session
import re
from flask_mysqldb import MySQL
from flask import jsonify

def crear_app():
    app = Flask(__name__)
    EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_USER'] = 'root'
    app.config['MYSQL_PASSWORD'] = ''
    app.config['MYSQL_DB'] = 'informatica'
    app.secret_key = 'mysecretkey'
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
            if role == 'admin':
                if ci == '12345':
                    session['role'] = 'administrador'
                    flash('Admin login successful')
                    return redirect(url_for('admin'))
                else:
                    flash('Invalid admin password')
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
            elif role == 'enc':
                if ci == '88888':
                    session['role'] = 'encargado'
                    flash('Encargado login successful')
                    return redirect(url_for('reporte'))
                else:
                    flash('Invalid encargado password')
        return render_template('login.html')


    @app.route('/admin')
    def admin():
        if 'role' in session and session['role'] == 'administrador':
            return render_template('admin.html')
        else:
            flash('Access Denied. Please login as administrator.')
            return redirect(url_for('login'))
    # ///////////////////////////////////////////////////////////


    @app.route('/dashboard')
    def dashboard():
        try:
            # Conectar a la base de datos
            cur = mysql.connection.cursor()

            # Consulta para obtener la cantidad de alumnos
            cur.execute("SELECT MAX(id_alumno) FROM alumno")
            alumnos_result = cur.fetchone()
            alumnos_count = alumnos_result[0] if alumnos_result[0] is not None else 0

            # Consulta para obtener la cantidad de profesores
            cur.execute("SELECT MAX(id_profesor) FROM profesor")
            profesores_result = cur.fetchone()
            profesores_count = profesores_result[0] if profesores_result[0] is not None else 0

            # Cerrar el cursor
            cur.close()

            # Renderizar la plantilla con los datos de alumnos y profesores
            return render_template('admin.html', alumnoS=alumnos_count, profesoreS=profesores_count)

        except Exception as e:
            flash(f'Ocurrió un error al obtener los datos: {e}', 'error')
            return redirect(url_for('login'))


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
                especialidad = request.form['especialidad']
                ci = request.form['ci']
                correo_encargado = request.form['correo_encargado']

                # Validar longitud del CI
                if len(ci) < 7 or len(ci) > 8:
                    flash('El CI debe tener entre 7 y 8 caracteres', 'error')
                    return redirect(url_for('alumnos'))

                cur = mysql.connection.cursor()

                # Verificar si ya existe un alumno con los mismos datos
                cur.execute("""
                    SELECT * FROM alumno
                    WHERE nombre = %s AND apellido = %s AND curso = %s AND seccion = %s AND especialidad = %s AND correo_encargado = %s
                """, (nombre, apellido, curso, seccion, especialidad, correo_encargado))
                alumno_existente = cur.fetchone()

                if alumno_existente:
                    flash('Ya existe un alumno con los mismos datos', 'error')
                    return redirect(url_for('alumnos'))

                # Verificar si el CI ya existe
                cur.execute("SELECT * FROM alumno WHERE ci = %s", (ci,))
                ci_existente = cur.fetchone()

                if ci_existente:
                    flash('Ya existe un alumno con este CI', 'error')
                    return redirect(url_for('alumnos'))

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
                return redirect(url_for('alumnos'))
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
                especialidad = request.form['especialidad']
                correo_encargado = request.form['correo_encargado']

                cur = mysql.connection.cursor()

                # 检查是否有相同的记录（除了ci）
                cur.execute("SELECT * FROM alumno WHERE nombre = %s AND apellido = %s AND curso = %s AND seccion = %s AND especialidad = %s AND correo_encargado = %s AND ci != %s",
                            (nombre, apellido, curso, seccion, especialidad, correo_encargado, ci))
                alumno_existente = cur.fetchone()

                if alumno_existente:
                    flash('Ya existe un alumno con estos datos')
                    return redirect(url_for('alumnos'))

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
                return redirect(url_for('alumnos'))
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
            return redirect(url_for('alumnos'))
        else:
            return redirect(url_for('login'))


    @app.route('/alumnos')
    def alumnos():
        if 'role' in session:
            if session['role'] == 'administrador' or session['role'] == 'alumno':
                busqueda = request.args.get('busqueda', '').strip()
                if busqueda:
                    cur = mysql.connection.cursor()
                    cur.execute("SELECT * FROM alumno WHERE nombre LIKE %s OR apellido LIKE %s OR curso LIKE %s OR seccion LIKE %s OR especialidad LIKE %s OR ci LIKE %s",
                                ('%' + busqueda + '%', '%' + busqueda + '%', '%' + busqueda + '%', '%' + busqueda + '%', '%' + busqueda + '%', '%' + busqueda + '%'))
                    alumnos = cur.fetchall()
                    cur.close()
                else:
                    cur = mysql.connection.cursor()
                    cur.execute("SELECT * FROM alumno")
                    alumnos = cur.fetchall()
                    cur.close()
                return render_template('alumno.html', role=session['role'], alumnos=alumnos)
        return redirect(url_for('login'))


    @app.route('/reporte')
    def reporte():
        return render_template('reporte.html')


    @app.route('/materia')
    def materia():
        if 'role' in session:
            if session['role'] in ['administrador', 'alumno']:
                busqueda = request.args.get('busqueda', '').strip()
                try:
                    cur = mysql.connection.cursor()
                    if busqueda:
                        cur.execute("SELECT * FROM materia WHERE nombre LIKE %s OR id_materia LIKE %s",
                                    ('%' + busqueda + '%', '%' + busqueda + '%'))
                    else:
                        cur.execute("SELECT * FROM materia")
                    materias = cur.fetchall()

                    cur.close()
                    return render_template('materia.html', role=session['role'], materias=materias)
                except Exception as e:
                    flash(f'Error al obtener materias: {str(e)}')
        return redirect(url_for('login'))


    @app.route('/conductuales')
    def conductuales():
        if 'role' in session and session['role'] == 'administrador':
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM rasgos_conductuales")
            conductuales = cur.fetchall()
            cur.close()
            return render_template('conductuales.html', conductuales=conductuales, role=session['role'])
        else:
            flash('Access Denied. Please login as administrator.')
            return redirect(url_for('login'))


    @app.route('/profesor')
    def profesor():
        if 'role' in session and session['role'] == 'administrador':
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM profesor")
            teachers = cur.fetchall()
            cur.execute("SELECT * FROM materia")
            materias = cur.fetchall()
            cur.close()
            return render_template('profesor.html', teachers=teachers, materias=materias, role=session['role'])
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
                return redirect(url_for('profesor'))
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
            return redirect(url_for('profesor'))
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
            return redirect(url_for('profesor'))
        else:
            return redirect(url_for('login'))
    # ////////////////////////////////////////////////////////////////


    @app.route('/add_materia', methods=['POST'])
    def add_materia():
        nombre = request.form['nombre']
        especialidad = request.form['especialidad']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM materia WHERE nombre = %s AND especialidad = %s",
                    (nombre, especialidad))
        materia_existente = cur.fetchone()

        if materia_existente:
            flash('Ya existe una materia con los mismos datos')
            return redirect(url_for("materia"))

        try:
            cur.execute(
                "INSERT INTO materia (nombre, especialidad) VALUES (%s, %s)", (nombre, especialidad))
            mysql.connection.commit()
            flash('Materia agregada exitosamente')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al agregar materia: {str(e)}')
        finally:
            cur.close()
        return redirect(url_for('materia'))


    # ////////////////////////////////////////////////////////////////



    @app.route('/edit_materia', methods=['POST'])
    def edit_materia():
        if request.method == 'POST':
            try:
                subject_id = request.form['subject_id']
                nombre = request.form['nombre']
                especialidad = request.form['especialidad']

                cur = mysql.connection.cursor()

                # Verificar si ya existe una materia con el mismo nombre y especialidad
                cur.execute("SELECT * FROM materia WHERE nombre = %s AND especialidad = %s AND id_materia != %s",
                            (nombre, especialidad, subject_id))
                existing_subject = cur.fetchall()

                if existing_subject:
                    flash('Ya existe una materia con este nombre y especialidad')
                    return redirect(url_for("materia"))

                # Actualizar la materia
                cur.execute("UPDATE materia SET nombre = %s, especialidad = %s WHERE id_materia = %s",
                            (nombre, especialidad, subject_id))
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
            return redirect(url_for('materia'))


    @app.route('/delete_materia', methods=['POST'])
    def delete_materia():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                subject_id = request.form['subject_id']
                try:
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "SELECT profesor_id_profesor FROM materia_por_profesor WHERE materia_id_materia = %s", [subject_id])
                    mat = cur.fetchall()

    # 删除 materia_por_profesor 表中的相关记录
                    for profesor in mat:
                        profesor_id = profesor[0]
                        cur.execute(
                            "DELETE FROM materia_por_profesor WHERE profesor_id_profesor = %s AND materia_id_materia = %s", (profesor_id, subject_id))

                    cur.execute(
                        "DELETE FROM materia WHERE id_materia = %s", [subject_id])
                    mysql.connection.commit()

                    flash('Materia eliminado exitosamente')
                except Exception as e:
                    flash(f'Error al eliminar materia: {str(e)}')
                    mysql.connection.rollback()
                finally:
                    if 'cur' in locals() and cur:
                        cur.close()
            return redirect(url_for('materia'))
        else:
            return redirect(url_for('login'))


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

                return redirect(url_for('conductuales'))
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
            return redirect(url_for('conductuales'))
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

            return redirect(url_for('conductuales'))
        else:
            return redirect(url_for('login'))


    @app.route('/horario')
    def horario():
        if 'role' in session and session['role'] == 'administrador':
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM horario")
            horarios = cur.fetchall()
            cur.close()
            return render_template('horario.html', horarios=horarios, role=session['role'])
        else:
            flash('Access Denied. Please login as administrator.')
            return redirect(url_for('login'))


    @app.route('/add_horario', methods=['POST'])
    def add_horario():
        curso = request.form['curso']
        seccion = request.form['seccion']
        especialidad = request.form['especialidad']

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
                    return redirect(url_for("horario"))
                else:
                    # Insertar nuevo horario
                    cur.execute("INSERT INTO horario (curso, seccion, especialidad) VALUES (%s, %s, %s)",
                                (curso, seccion, especialidad))
                    mysql.connection.commit()
                    flash('Horario agregado exitosamente')

        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al agregar horario: {str(e)}')

        return redirect(url_for('horario'))




    @app.route('/edit_horario', methods=['POST'])
    def edit_horario():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                try:
                    horario_id = request.form['horario_id']
                    curso = request.form['curso']
                    seccion = request.form['seccion']
                    especialidad = request.form['especialidad']
                    cur = mysql.connection.cursor()
                    cur.execute("Select * from horario where curso=%s, seccion =%s, especialidad=%s",
                                (curso, seccion, especialidad))
                    a = cur.fetchall()
                    if a:
                        return redirect(url_for("horario"))
                    if curso and seccion and especialidad:
                        cur.execute("UPDATE horario SET curso = %s, seccion = %s, especialidad = %s WHERE id_horario = %s", (
                            curso, seccion, especialidad, horario_id))
                    mysql.connection.commit()
                    flash('Horario modificado exitosamente')
                except KeyError as e:
                    flash(f'Error: {e} no encontrado en el formulario')
                except Exception as e:
                    flash(f'Error al modificar horario: {str(e)}')
                    mysql.connection.rollback()
                finally:
                    if 'cur' in locals() and cur:
                        cur.close()
            return redirect(url_for('horario'))
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
            return redirect(url_for('horario'))
        else:
            return redirect(url_for('login'))


    @app.route('/materia_profe')
    def materia_profe():
        if 'role' in session and session['role'] == 'administrador':
            cur = mysql.connection.cursor()
            cur.execute("""
                SELECT p.id_profesor AS profesor_id, p.nombre AS profesor_nombre, p.apellido AS profesor_apellido, 
                    m.id_materia AS materia_id, m.nombre AS materia_nombre 
                FROM materia_por_profesor mp
                JOIN profesor p ON mp.profesor_id_profesor = p.id_profesor
                JOIN materia m ON mp.materia_id_materia= m.id_materia
            """)
            profmat = cur.fetchall()

            cur.execute("SELECT * FROM materia")
            materias = cur.fetchall()
            cur.execute("SELECT * FROM profesor")
            profesor = cur.fetchall()
            cur.close()
            return render_template('profe_materia.html', profmat=profmat, materias=materias, profesor=profesor, role=session['role'])
        else:
            flash('Access Denied. Please login as administrator.')
            return redirect(url_for('login'))


    @app.route('/add_profmate', methods=['POST'])
    def add_profmate():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                materia_id = request.form['materiaa']
                profesor_id = request.form['profesoor']

                # Check if the relationship already exists
                try:
                    cur = mysql.connection.cursor()
                    cur.execute(
                        "SELECT COUNT(*) FROM materia_por_profesor WHERE materia_id_materia = %s AND profesor_id_profesor = %s", (materia_id, profesor_id))
                    count = cur.fetchone()[0]

                    if count > 0:
                        flash('Esta relación ya existe')
                        return redirect(url_for('materia_profe'))

                    # If not exists, insert the new relation
                    cur.execute(
                        "INSERT INTO materia_por_profesor (materia_id_materia, profesor_id_profesor) VALUES (%s, %s)", (materia_id, profesor_id))
                    mysql.connection.commit()
                    flash('Relación agregada exitosamente')
                except Exception as e:
                    mysql.connection.rollback()
                    flash(f'Error al agregar relación: {str(e)}')
                finally:
                    cur.close()
                return redirect(url_for('materia_profe'))
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
                return redirect(url_for('materia_profe'))
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
                return redirect(url_for('materia_profe'))
        else:
            return redirect(url_for('login'))


    @app.route('/materia_hora')
    def materia_hora():
        if 'role' in session and session['role'] == 'administrador':
            cur = mysql.connection.cursor()

            # Obtener las materias disponibles
            cur.execute("SELECT id_materia, nombre FROM materia")
            materias = cur.fetchall()

            # Obtener los horarios disponibles
            cur.execute(
                "SELECT id_horario, especialidad, curso, seccion FROM horario")
            horarios = cur.fetchall()

            # Obtener la relación materia-horario
            cur.execute("""
                SELECT 
                    d.materia_id_materia AS id_materia, 
                    m2.nombre AS materia_nombre, 
                    d.horario_id_horario AS id_horario, 
                    CONCAT(h.especialidad, ' ', h.curso, ' ', h.seccion) AS horario_info,
                    d.dia, 
                    d.horario
                FROM detalle_horario d
                JOIN materia m2 ON m2.id_materia = d.materia_id_materia 
                JOIN horario h ON h.id_horario = d.horario_id_horario
            """)

            materia_hora = cur.fetchall()
            cur.close()

            return render_template('detalle_horario.html', materia_hora=materia_hora, materias=materias, horarios=horarios, role=session['role'])
        else:
            flash('Acceso denegado. Por favor, inicie sesión como administrador.')
            return redirect(url_for('login'))


    @app.route('/add_dethora', methods=['POST'])
    def add_dethora():
        if 'role' in session and session['role'] == 'administrador':
            if request.method == 'POST':
                print(request.form)
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
                return redirect(url_for('materia_hora'))
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
                return redirect(url_for('materia_hora'))
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
                return redirect(url_for('materia_hora'))
        else:
            return redirect(url_for('login'))


    @app.route('/<espe>')
    def elegir_curso(espe):
        if 'role' in session and (session['role'] == 'administrador' or session['role'] == 'encargado'):
            if espe == 'Construccion civil' or espe == 'Quimica' or espe == 'Electronica':
                return render_template('tres.html', especialidad=espe)
            else:
                return render_template('dos.html', especialidad=espe)
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
        print(items)
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
            print(existing_reporte)
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

    @app.route('/check_materia', methods=['POST'])
    def check_materia():
        data = request.get_json()
        nombre = data.get('nombre')
        especialidad = data.get('especialidad')

        if not nombre or not especialidad:
            return jsonify({'error': 'Los campos "nombre" y "especialidad" son obligatorios'}), 400

        try:
            # Conectar a la base de datos
            cur = mysql.connection.cursor()
            cur.execute(
                "SELECT * FROM materia WHERE nombre = %s AND especialidad = %s", (nombre, especialidad))
            materia_existente = cur.fetchone()
            cur.close()

            # Devolver respuesta JSON
            if materia_existente:
                return jsonify({'existe': True})
            else:
                return jsonify({'existe': False})

        except Exception as e:
            return jsonify({'error': 'Error interno del servidor'}), 500
            
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


    @app.route('/verificar_curso', methods=['POST'])
    def verificar_curso():
        data = request.get_json()
        curso = data.get('curso')
        seccion = data.get('seccion')
        especialidad = data.get('especialidad')

        if not curso or not seccion or not especialidad:
            return jsonify({'error': 'Todos los campos son obligatorios'})

        try:
            with mysql.connection.cursor() as cur:
                # Verificar si ya existe el horario
                cur.execute("SELECT * FROM horario WHERE curso = %s AND seccion = %s AND especialidad = %s",
                            (curso, seccion, especialidad))
                horario_existente = cur.fetchone()

            # Devolver respuesta JSON
            if horario_existente:
                return jsonify({'existe': True})
            else:
                return jsonify({'existe': False})

        except Exception as e:
            return jsonify({'error': str(e)})

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

    @app.route('/check_ci', methods=['POST'])
    def check_ci():
        data = request.get_json()
        ci = data.get('ci')

        if not ci:
            return jsonify({'error': 'Todos los campos son obligatorios'})

        try:
            with mysql.connection.cursor() as cur:
                # Verificar si ya existe el alumno
                cur.execute("SELECT * FROM alumno WHERE ci = %s", (ci,))
                alumno_existente = cur.fetchone()

            # Devolver respuesta JSON
            if alumno_existente:
                return jsonify({'existe': True})
            else:
                return jsonify({'existe': False})

        except Exception as e:
            return jsonify({'error': 'Ocurrió un error al verificar el CI: ' + str(e)})

    # ////////////////////////////////////////////////////////


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

    # ///////////////////////////////////////////////////////
    return app


if __name__ == '__main__':
    app = crear_app()
    app.run(debug=True, host='0.0.0.0')