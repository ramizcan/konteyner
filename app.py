from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import re

app = Flask(__name__)
app.secret_key = 'gizli_anahtar'  # Güvenlik için

# MySQL Bağlantısı
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="988911rcA+",  # Buraya kendi MySQL şifreni yaz
    database="konteynir"
)

@app.route('/')
def home():
    if 'email' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Veritabanında kullanıcıyı sorgula
        cursor = db.cursor()
        cursor.execute("SELECT id, full_name, password FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user[2], password):  # Şifre kontrolü
            session['email'] = email
            session['name'] = user[1]  # Kullanıcının adını oturumda sakla
            return redirect(url_for('dashboard'))
        else:
            flash("E-posta veya şifre hatalı!", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        full_name = request.form['full_name']
        email = request.form['email']
        phone = request.form['phone']
        user_type = request.form['user_type']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Form doğrulama
        error = None
        
        # Boş alan kontrolü
        if not username or not full_name or not email or not phone or not password:
            error = "Tüm alanları doldurunuz."
            
        # Kullanıcı adı format kontrolü
        elif not re.match(r'^[a-zA-Z0-9_]+$', username):
            error = "Kullanıcı adı sadece harf, rakam ve alt çizgi içerebilir."
            
        # E-posta format kontrolü
        elif not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            error = "Geçerli bir e-posta adresi giriniz."
            
        # Telefon format kontrolü
        elif not re.match(r'^\d{10,11}$', phone.replace('-', '').replace(' ', '')):
            error = "Geçerli bir telefon numarası giriniz."
            
        # Şifre uzunluk kontrolü
        elif len(password) < 8:
            error = "Şifre en az 8 karakter olmalıdır."
            
        # Şifre eşleşme kontrolü
        elif password != confirm_password:
            error = "Şifreler eşleşmiyor."
            
        # Hata yoksa kayıt işlemini gerçekleştir
        if error is None:
            try:
                # Kullanıcı adı ve e-posta kontrolü
                cursor = db.cursor()
                cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
                if cursor.fetchone():
                    error = "Kullanıcı adı veya e-posta zaten kullanımda."
                else:
                    # Şifreyi hashle
                    hashed_password = generate_password_hash(password)
                    
                    # Kullanıcıyı veritabanına ekle
                    cursor.execute(
                        "INSERT INTO users (username, password, full_name, email, phone, user_type) VALUES (%s, %s, %s, %s, %s, %s)",
                        (username, hashed_password, full_name, email, phone, user_type)
                    )
                    db.commit()
                    flash("Kayıt başarıyla oluşturuldu! Giriş yapabilirsiniz.", "success")
                    return redirect(url_for('login'))
            except mysql.connector.Error as err:
                flash(f"Bir hata oluştu: {err}", "error")
        
        if error:
            flash(error, "error")
    
    return render_template('signup.html')

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor()
    
    # Aktif acil çağrıları getir
    cursor.execute("""
        SELECT id, worker_name, emergency_type, description, 
               latitude, longitude, timestamp, is_resolved
        FROM emergency_signals
        WHERE is_active = TRUE
        ORDER BY timestamp DESC
    """)
    acil_cagrilar = cursor.fetchall()
    
    # İşlemdeki (çözülmemiş) çağrıları getir
    cursor.execute("""
        SELECT es.id, es.worker_name, es.emergency_type, 
               es.description, es.latitude, es.longitude, 
               es.timestamp, u.full_name as handler_name
        FROM emergency_signals es
        LEFT JOIN users u ON es.resolved_by = u.id
        WHERE es.is_active = TRUE 
        AND es.is_resolved = FALSE
        ORDER BY es.timestamp DESC
    """)
    islemdeki_cagrilar = cursor.fetchall()
    
    cursor.close()
    
    return render_template('dashboard.html', 
                         user={'name': session.get('name', 'Bilinmeyen Kullanıcı')},
                         acil_cagrilar=acil_cagrilar,
                         islemdeki_cagrilar=islemdeki_cagrilar)

@app.route('/logout')
def logout():
    session.clear()  # Tüm session verilerini temizle
    return redirect(url_for('login'))

@app.route('/konteyner/ekle-secim')
def konteyner_ekle_secim():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('konteyner_ekle_secim.html')

@app.route('/konteyner/sehir-ekle', methods=['GET', 'POST'])
def konteyner_sehir_ekle():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        latitude = request.form['latitude']
        longitude = request.form['longitude']
        total_capacity = request.form['total_capacity']
        
        try:
            cursor = db.cursor()
            cursor.execute("""
                INSERT INTO container_cities 
                (name, location, latitude, longitude, total_capacity)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, location, latitude, longitude, total_capacity))
            db.commit()
            flash("Konteynır şehri başarıyla eklendi!", "success")
            return redirect(url_for('dashboard'))
        except mysql.connector.Error as err:
            flash(f"Hata oluştu: {err}", "error")
    
    return render_template('konteyner_sehir_ekle.html')

@app.route('/konteyner/konteyner-ekle', methods=['GET', 'POST'])
def konteyner_konteyner_ekle():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    # Mevcut şehirleri getir
    cursor = db.cursor()
    cursor.execute("SELECT id, name FROM container_cities")
    cities = cursor.fetchall()
    
    if request.method == 'POST':
        container_city_id = request.form['container_city_id']
        container_number = request.form['container_number']
        capacity = request.form['capacity']
        
        try:
            # Konteynır ekle
            cursor.execute("""
                INSERT INTO containers 
                (container_city_id, container_number, capacity)
                VALUES (%s, %s, %s)
            """, (container_city_id, container_number, capacity))
            
            # Şehrin total_containers değerini güncelle
            cursor.execute("""
                UPDATE container_cities 
                SET total_containers = total_containers + 1
                WHERE id = %s
            """, (container_city_id,))
            
            db.commit()
            flash("Konteynır başarıyla eklendi!", "success")
            return redirect(url_for('dashboard'))
        except mysql.connector.Error as err:
            flash(f"Hata oluştu: {err}", "error")
    
    return render_template('konteyner_konteyner_ekle.html', cities=cities)

@app.route('/konteyner/talepler')
def konteyner_talepler():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    # Talepleri getir
    cursor = db.cursor()
    cursor.execute("""
        SELECT t.id, cc.name as city_name, c.container_number, 
               t.request_type, t.status, t.created_at, u.full_name
        FROM container_requests t
        JOIN containers c ON t.container_id = c.id
        JOIN container_cities cc ON c.container_city_id = cc.id
        JOIN users u ON t.user_id = u.id
        ORDER BY t.created_at DESC
    """)
    talepler = cursor.fetchall()
    
    # Dolu ve boş konteynırları getir
    cursor.execute("""
        SELECT cc.name as city_name, c.container_number, 
               c.capacity, c.current_occupancy,
               CASE 
                   WHEN c.current_occupancy >= c.capacity THEN 'Dolu'
                   ELSE 'Boş'
               END as status,cc.latitude, 
       cc.longitude
        FROM containers c
        JOIN container_cities cc ON c.container_city_id = cc.id
        ORDER BY cc.name, c.container_number
    """)
    konteynerler = cursor.fetchall()
    
    return render_template('konteyner_talepler.html', 
                         talepler=talepler, 
                         konteynerler=konteynerler)

@app.route('/delete-container', methods=['POST'])
def delete_container():
    try:
        data = request.get_json()
        container_id = data.get('container_id')
        
        cursor = db.cursor()  # Yeni bir cursor oluştur
        
        # Konteynırı sil
        cursor.execute("""
            DELETE FROM containers 
            WHERE container_number = %s
        """, (container_id,))
        
        db.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(f"Hata: {str(e)}")
        return jsonify({'success': False})
    finally:
        cursor.close()  # finally bloğunda cursor'ı kapat

# Acil çağrıyı çözüldü olarak işaretle
@app.route('/resolve-emergency', methods=['POST'])
def resolve_emergency():
    if 'email' not in session:
        return jsonify({'success': False, 'error': 'Oturum gerekli'})
        
    try:
        data = request.get_json()
        emergency_id = data.get('emergency_id')
        resolution_notes = data.get('notes', '')
        
        cursor = db.cursor()
        cursor.execute("""
            UPDATE emergency_signals 
            SET is_resolved = TRUE,
                resolved_at = CURRENT_TIMESTAMP,
                resolved_by = (SELECT id FROM users WHERE email = %s),
                resolution_notes = %s
            WHERE id = %s
        """, (session['email'], resolution_notes, emergency_id))
        
        db.commit()
        cursor.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        print(e)
        return jsonify({'success': False, 'error': str(e)})
    
@app.route('/emergency-history')
def emergency_history():
    if 'email' not in session:
        return redirect(url_for('login'))
    
    cursor = db.cursor()
    
    # Filtre parametrelerini al
    emergency_type = request.args.get('type')
    date_start = request.args.get('start')
    date_end = request.args.get('end')
    
    # Base query
    query = """
        SELECT es.id, es.worker_name, es.emergency_type, 
               es.description, es.latitude, es.longitude, 
               es.timestamp, u.full_name as resolver_name,
               es.resolution_notes
        FROM emergency_signals es
        LEFT JOIN users u ON es.resolved_by = u.id
        WHERE 1=1
    """
    params = []
    
    # Filtreleri ekle
    if emergency_type:
        query += " AND es.emergency_type = %s"
        params.append(emergency_type)
    
    if date_start:
        query += " AND DATE(es.timestamp) >= %s"
        params.append(date_start)
    
    if date_end:
        query += " AND DATE(es.timestamp) <= %s"
        params.append(date_end)
    
    # Tarihe göre sırala
    query += " ORDER BY es.timestamp DESC"
    
    cursor.execute(query, params)
    gecmis_cagrilar = cursor.fetchall()
    cursor.close()
    
    return render_template('emergency_history.html', gecmis_cagrilar=gecmis_cagrilar)

if __name__ == '__main__':
    app.run(debug=True)   