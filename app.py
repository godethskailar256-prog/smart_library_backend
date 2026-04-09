from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
import psycopg2.extras

app = Flask(__name__)
# Secret key is required for Flask sessions to work securely
app.secret_key = 'super_secret_library_key_change_in_production'

# Database connection configuration (Supabase URL)
SUPABASE_DB_URI = "postgresql://postgres.lvkfuyqgmuyghefwcsor:kenana82007as@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"

def get_db_connection():
    """Helper function to connect to PostgreSQL (Supabase)"""
    conn = psycopg2.connect(SUPABASE_DB_URI)
    return conn

@app.route('/')
def index():
    """Public landing page showing current occupancy and status."""
    # استقبال خيار اللغة من الرابط، وحفظه في الجلسة (الافتراضي هو الإنجليزي)
    lang = request.args.get('lang')
    if lang in ['ar', 'en']:
        session['lang'] = lang
    else:
        lang = session.get('lang', 'en')

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Fetch the current count from the database
    cursor.execute('SELECT current_count FROM occupancy WHERE id = 1;')
    result = cursor.fetchone()
    count = result['current_count'] if result else 0
    
    cursor.close()
    conn.close()
    
    # تحديد حالة المكتبة بناءً على العدد واللغة المختارة
    if count < 10:
        status = "هادئة" if lang == 'ar' else "Quiet"
    elif 10 <= count < 20:
        status = "متوسطة" if lang == 'ar' else "Moderate"
    elif 20 <= count <= 25:
        status = "مزدحمة" if lang == 'ar' else "Crowded"
    else:
        status = "ممتلئة جداً" if lang == 'ar' else "Very Full"
    
    # نمرر متغير اللغة lang لصفحة HTML لتعرف أي لغة تعرض
    return render_template('index.html', count=count, status=status, lang=lang)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Librarian login page with hardcoded credentials."""
    # If already logged in, skip login and go to dashboard
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        full_name = request.form['full_name']
        national_id = request.form['national_id']

        # Hardcoded credential check
        if full_name == 'kenana mohamed' and national_id == '30705061603067':
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid Credentials")

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Private dashboard showing student logs."""
    # Security check: redirect to login if not authenticated
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    # Fetch all logs, newest first
    cursor.execute('SELECT rfid_id, entry_timestamp FROM student_logs ORDER BY entry_timestamp DESC;')
    logs = cursor.fetchall()
    
    cursor.close()
    conn.close()

    return render_template('dashboard.html', logs=logs)

@app.route('/logout')
def logout():
    """Clears the session and logs the user out."""
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route('/api/update', methods=['POST'])
def api_update():
    """ESP32 API Endpoint to update occupancy and log RFID."""
    data = request.get_json()
    
    if not data or 'rfid_id' not in data or 'count' not in data:
        return jsonify({"error": "Invalid data format"}), 400

    rfid_id = data['rfid_id']
    new_count = data['count']

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Update the current occupancy count
        cursor.execute('UPDATE occupancy SET current_count = %s WHERE id = 1;', (new_count,))
        
        # 2. Insert the new student log
        cursor.execute('INSERT INTO student_logs (rfid_id) VALUES (%s);', (rfid_id,))
        
        conn.commit()
        return jsonify({"message": "Update successful"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)