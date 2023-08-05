import uuid
from flask import Flask, session, g, request, render_template, redirect, url_for
from flask_socketio import SocketIO
import sqlite3
import datetime

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
            CREATE TABLE IF NOT EXISTS session_map
            (socketio_sid TEXT PRIMARY KEY,
            flask_sid TEXT)
        ''')
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

        cursor.execute('INSERT INTO users_new (flask_sid, full_name, table_selection) VALUES (?, ?, ?)',
                       (session['sid'], full_name, table_selection))
        get_db().commit()

        return redirect(url_for('color', full_name=full_name, table_selection=table_selection))
    else:
        return render_template('user.html')

@app.route('/color_selection', methods=['POST'])
def color_selection():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        table_selection = request.form.get('table_selection')
        flask_sid = str(uuid.uuid4())  # generate a unique identifier
        session['flask_sid'] = flask_sid  # store the identifier in the session

        cursor = get_db().cursor()
        cursor.execute('INSERT INTO users_new (flask_sid, full_name, table_selection) VALUES (?, ?, ?)',
               (session['flask_sid'], full_name, table_selection))
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
    print(f"Admin Success - User Data: {user_data}")  # Debug statement
    return render_template('admin_success.html', user_data=user_data)

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


@socketio.on('connect')
def handle_connect():
    print('User connected with Socket.IO sid:', request.sid)
    flask_sid = session.sid  # get the Flask session ID

    cursor = get_db().cursor()
    cursor.execute('INSERT INTO session_map (socketio_sid, flask_sid) VALUES (?, ?)',
                   (request.sid, flask_sid))
    get_db().commit()

@socketio.on('disconnect')
def handle_disconnect():
    print('User disconnected with Socket.IO sid:', request.sid)

    # get the corresponding Flask session ID
    cursor = get_db().cursor()
    cursor.execute('SELECT flask_sid FROM session_map WHERE socketio_sid = ?', (request.sid,))
    row = cursor.fetchone()

    if row:
        flask_sid = row[0]

        # remove the user from the users_new table
        cursor.execute('DELETE FROM users_new WHERE flask_sid = ?', (flask_sid,))
        get_db().commit()

        # remove the mapping from the session_map table
        cursor.execute('DELETE FROM session_map WHERE socketio_sid = ?', (request.sid,))
        get_db().commit()
    else:
        print('No Flask session found for the disconnected user.')

def update_user_data_db():
    cursor = get_db().cursor()
    cursor.execute('SELECT full_name, flask_sid FROM users_new')
    rows = cursor.fetchall()
    active_users = {row[0]: row[1] for row in rows}
    cursor.execute('SELECT full_name FROM users_new WHERE color IS NOT NULL')
    active_colored_users = {row[0] for row in cursor.fetchall()}
    inactive_users = active_users.keys() - active_colored_users

    current_time = datetime.datetime.now()
    for full_name in inactive_users:
        flask_sid = active_users[full_name]
        cursor.execute('SELECT flask_sid FROM session_map WHERE flask_sid = ?', (flask_sid,))
        session_row = cursor.fetchone()

        # Check if the Flask session is still active
        if not session_row:
            cursor.execute('DELETE FROM users_new WHERE full_name = ?', (full_name,))
            get_db().commit()
            socketio.emit('user_update', {'full_name': full_name, 'action': 'leave'}, broadcast=True)
        else:
            # Get the last active time of the Flask session
            cursor.execute('SELECT last_active FROM session_map WHERE flask_sid = ?', (flask_sid,))
            last_active_row = cursor.fetchone()
            if last_active_row:
                last_active = datetime.datetime.strptime(last_active_row[0], '%Y-%m-%d %H:%M:%S')
                # Check if the user has been inactive for more than 5 minutes
                if (current_time - last_active).total_seconds() > 300:
                    cursor.execute('DELETE FROM users_new WHERE full_name = ?', (full_name,))
                    get_db().commit()
                    socketio.emit('user_update', {'full_name': full_name, 'action': 'leave'}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=8080)
