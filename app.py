from flask import Flask, render_template, request, redirect, url_for, session, flash
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

cursor = db.cursor()

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
    if 'email' in session:
        return render_template('dashboard.html', user={'name': session['name']})
    return redirect(url_for('login'))

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
               END as status
        FROM containers c
        JOIN container_cities cc ON c.container_city_id = cc.id
        ORDER BY cc.name, c.container_number
    """)
    konteynerler = cursor.fetchall()
    
    return render_template('konteyner_talepler.html', 
                         talepler=talepler, 
                         konteynerler=konteynerler)

if __name__ == '__main__':
    app.run(debug=True)