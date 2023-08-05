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
    if not session.get('authenticated'):
        return redirect(url_for('admin'))
    
    cursor = get_db().cursor()
    cursor.execute('SELECT color, COUNT(*) FROM users_new WHERE color IS NOT NULL GROUP BY color')
    color_data = cursor.fetchall()

    # Define your custom colors in RGB format
    CUSTOM_RED = (255, 153, 153)
    CUSTOM_YELLOW = (255, 238, 153)
    CUSTOM_GREEN = (153, 230, 153)

    red_weight, yellow_weight, green_weight = 0, 0, 0
    for color, count in color_data:
        if color == 'red':
            red_weight = count
        elif color == 'yellow':
            yellow_weight = count
        elif color == 'green':
            green_weight = count

    total_count = red_weight + yellow_weight + green_weight
    if total_count == 0:  # To avoid ZeroDivisionError
        background_color = '#FFFFFF'  # Default white background
    else:
        # Calculate the weighted RGB values using custom colors
        r = (red_weight * CUSTOM_RED[0] + green_weight * CUSTOM_GREEN[0] + yellow_weight * CUSTOM_YELLOW[0]) / total_count
        g = (red_weight * CUSTOM_RED[1] + green_weight * CUSTOM_GREEN[1] + yellow_weight * CUSTOM_YELLOW[1]) / total_count
        b = (red_weight * CUSTOM_RED[2] + green_weight * CUSTOM_GREEN[2] + yellow_weight * CUSTOM_YELLOW[2]) / total_count

        # Ensure values are between 0 and 255 and convert RGB values to hexadecimal
        background_color = "#{:02x}{:02x}{:02x}".format(max(0, min(int(r), 255)), max(0, min(int(g), 255)), max(0, min(int(b), 255)))
    
    cursor.execute('SELECT * FROM users_new WHERE color IS NOT NULL')
    user_data = cursor.fetchall()
    return render_template('admin_success.html', user_data=user_data, background_color=background_color)


@app.route('/remove_user', methods=['POST'])
def remove_user():
    user_id = request.form.get('id')
    cursor = get_db().cursor()
    cursor.execute('DELETE FROM users_new WHERE id = ?', (user_id,))
    get_db().commit()

    return jsonify(success=True)

@app.route('/clear_users', methods=['POST'])
def clear_users():
    cursor = get_db().cursor()
    cursor.execute('DELETE FROM users_new')
    get_db().commit()
    return jsonify(success=True)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == 'chfam':
            session['authenticated'] = True  # Set session variable to indicate authentication
            return redirect(url_for('admin_success'))
        else:
            return redirect(url_for('user'))
    else:
        if session.get('authenticated'):
            return redirect(url_for('admin_success'))
        else:
            return render_template('admin.html')

if __name__ == '__main__':
    socketio.run(app, debug=True, port=8080)
