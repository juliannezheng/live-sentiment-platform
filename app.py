import uuid
from flask import Flask, session, g, request, render_template, redirect, url_for, jsonify
from flask_socketio import SocketIO
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key'
socketio = SocketIO(app)

DATABASE = 'user_data.db'

table_options = {
    'table1': 'Behaviorals',
    'table2': 'Technicals',
    'table3': 'Stock Pitch',
    'table4': 'Fun',
    'table5': 'Group Case'
}

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        cursor = db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users_new
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            table_selection TEXT,
            color TEXT,
            flask_sid TEXT)
        ''')
        db.commit()
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/', methods=['GET', 'POST'])
def user():
    cursor = get_db().cursor()
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        table_selection = request.form.get('table_selection')
        cursor.execute('INSERT INTO users_new (full_name, table_selection) VALUES (?, ?)',
                       (full_name, table_selection))
        get_db().commit()

        return redirect(url_for('color', full_name=full_name, table_selection=table_selection))
    else:
        return render_template('user.html')

@app.route('/color_selection', methods=['POST'])
def color_selection():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        table_selection = request.form.get('table_selection')
        cursor = get_db().cursor()
        cursor.execute('INSERT INTO users_new (full_name, table_selection) VALUES (?, ?)',
               (full_name, table_selection))
        get_db().commit()

        return redirect(url_for('color', full_name=full_name, table_selection=table_selection))

@app.route('/color/<full_name>/<table_selection>', methods=['GET', 'POST'])
def color(full_name, table_selection):
    if request.method == 'POST':
        color = request.form.get('color_selection')
        cursor = get_db().cursor()
        cursor.execute('UPDATE users_new SET color = ? WHERE full_name = ? AND table_selection = ?',
                       (color, full_name, table_selection))
        get_db().commit()

        # Emit a color update event to all connected clients
        socketio.emit('color_update', {'full_name': full_name, 'color': color}, broadcast=True)

        return '', 204
    else:
        return render_template('color.html', full_name=full_name, table_selection=table_selection, table_options=table_options)

@app.route('/admin_success')
def admin_success():
    cursor = get_db().cursor()
    cursor.execute('SELECT * FROM users_new WHERE color IS NOT NULL')
    user_data = cursor.fetchall()
    return render_template('admin_success.html', user_data=user_data)

@app.route('/remove_user', methods=['POST'])
def remove_user():
    user_id = request.form.get('id')
    cursor = get_db().cursor()
    cursor.execute('DELETE FROM users_new WHERE id = ?', (user_id,))
    get_db().commit()

    return jsonify(success=True)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'chfam':
            return redirect(url_for('admin_success'))
        else:
            return redirect(url_for('user'))
    else:
        return render_template('admin.html')

if __name__ == '__main__':
    socketio.run(app, debug=True, port=8080)
