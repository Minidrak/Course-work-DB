import os
import time
import secrets
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from redis_config import (
    store_token, get_token, delete_token, store_session_data, get_session_data, delete_session_data,
    cache_artworks, get_cached_artworks, invalidate_artworks_cache,
    cache_artwork_reviews, get_cached_artwork_reviews, invalidate_artwork_reviews_cache,
    publish_notification, redis_client
)

app = Flask(__name__)
CORS(app)

# Конфигурация для загрузки файлов
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

#
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.getenv('POSTGRES_DB', 'artshop'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', '123'),
        host=os.getenv('DB_HOST', 'db'),
        port=os.getenv('DB_PORT', '5432')
    )
    return conn

def get_user_role(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.name FROM "user" u
        JOIN role r ON u.role_id = r.id
        WHERE u.id = %s;
    """, (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
        return result[0]
    return None

def generate_auth_token():
    """Generate a secure random token"""
    return secrets.token_hex(32)

def verify_token(token):
    """Verify if token exists in Redis and return user_id"""
    if not token:
        return None
    
    # Search for token in Redis
    for key in redis_client.scan_iter("user_token:*"):
        stored_token = redis_client.get(key)
        if stored_token == token:
            user_id = key.split(':')[1]
            return user_id
    return None

@app.route('/register', methods=['POST'])
def register():
    time.sleep(1)
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'Username, email and password are required'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Проверка на существование данного email при регистрации
        cur.execute('SELECT id FROM "user" WHERE username = %s OR email = %s', (username, email))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'error': 'Username or email already exists'}), 400

        password_hash = generate_password_hash(password)

        # Вызов процедуры регистрации
        cur.execute("CALL register_user_proc(%s, %s, %s);", (username, email, password_hash))
        conn.commit()

        # Узнать id нового пользователя
        cur.execute('SELECT id FROM "user" WHERE username = %s;', (username,))
        user_record = cur.fetchone()
        if user_record:
            user_id = user_record[0]
            # Generate and store token
            token = generate_auth_token()
            store_token(user_id, token)
            # Store session data
            session_data = {
                'username': username,
                'email': email,
                'role': 'user'  # Default role for new users
            }
            store_session_data(user_id, session_data)
        else:
            user_id = None

        cur.close()
        conn.close()

        if user_id:
            return jsonify({
                'message': 'User registered successfully',
                'user_id': user_id,
                'token': token
            }), 201
        else:
            return jsonify({'error': 'Registration failed'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    time.sleep(1)
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Получение хеш пароля и user_id
        cur.execute('SELECT id, password_hash FROM "user" WHERE username = %s;', (username,))
        result = cur.fetchone()
        if not result:
            cur.close()
            conn.close()
            return jsonify({'error': 'Invalid credentials'}), 401

        user_id, stored_hash = result
        if not check_password_hash(stored_hash, password):
            cur.close()
            conn.close()
            return jsonify({'error': 'Invalid credentials'}), 401

        # Вызов функции для получения user_id и роли
        cur.execute("SELECT * FROM login_user_proc(%s, %s);", (username, stored_hash))
        login_result = cur.fetchone()
        cur.close()
        conn.close()

        if login_result:
            fetched_user_id, role = login_result
            # Генерируем и сохраняем токен
            token = generate_auth_token()
            store_token(fetched_user_id, token)

            session_data = {
                'username': username,
                'role': role
            }
            store_session_data(fetched_user_id, session_data)
            
            return jsonify({
                'message': 'Login successful',
                'user_id': fetched_user_id,
                'role': role,
                'token': token
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'No token provided'}), 401

    user_id = verify_token(token)
    if not user_id:
        return jsonify({'error': 'Invalid token'}), 401

    # Удаляем токен и данные сессии при выходе
    delete_token(user_id)
    delete_session_data(user_id)
    
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/artworks', methods=['GET'])
def get_artworks():
    try:
        # Сначала пробуем взять кэш
        try:
            cached_artworks = get_cached_artworks()
            if cached_artworks:
                return jsonify(cached_artworks), 200
        except Exception as cache_error:
            print(f"Cache error: {str(cache_error)}")
            

        # Если нет кэша, то берем из базы
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM get_artworks_proc();")
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        artworks = [dict(zip(colnames, row)) for row in rows]
        # Преобразуем price из Decimal
        for art in artworks:
            art['price'] = float(art['price'])
            art['stock'] = int(art['stock']) if art['stock'] is not None else 0

        # Пытаемся кэшировать результаты
        try:
            cache_artworks(artworks)
        except Exception as cache_error:
            print(f"Cache error: {str(cache_error)}")
            
        
        return jsonify(artworks), 200
    except Exception as e:
        print(f"Error in get_artworks: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/create_order', methods=['POST'])
def create_order():
    data = request.get_json()
    user_id = data.get('user_id')
    items = data.get('items')

    if not user_id or not items or not isinstance(items, list):
        return jsonify({'error': 'Invalid request data'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        order_ids = []
        for item in items:
            artwork_id = item.get('artwork_id')
            quantity = item.get('quantity', 1)
            if not artwork_id or not isinstance(quantity, int):
                continue

            cur.execute("CALL create_order_proc(%s, %s, %s, %s);", (user_id, artwork_id, quantity, None))
            conn.commit()

            # Получение последнего созданного заказ для данного пользователя
            cur.execute("""
                SELECT id FROM "order"
                WHERE user_id = %s
                ORDER BY order_date DESC
                LIMIT 1;
            """, (user_id,))
            order_record = cur.fetchone()
            if order_record:
                order_id = order_record[0]
                order_ids.append(order_id)

                # Отправляем уведомление о новом заказе PubSub
                notification = {
                    'type': 'new_order',
                    'order_id': order_id,
                    'user_id': user_id,
                    'artwork_id': artwork_id,
                    'quantity': quantity
                }
                publish_notification('orders', notification)

        cur.close()
        conn.close()

        return jsonify({'message': 'Orders created successfully', 'order_ids': order_ids}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/add_review', methods=['POST'])
def add_review():
    data = request.get_json()
    user_id = data.get('user_id')
    artwork_id = data.get('artwork_id')
    rating = data.get('rating')
    comment = data.get('comment')

    if not all([user_id, artwork_id, rating]):
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO review (user_id, artwork_id, rating, comment)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, (user_id, artwork_id, rating, comment))
        review_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        # Удаляем кэш для этого артикула
        invalidate_artwork_reviews_cache(artwork_id)

        # Отправляем уведомление о новом отзыве PubSub
        notification = {
            'type': 'new_review',
            'artwork_id': artwork_id,
            'user_id': user_id,
            'rating': rating
        }
        publish_notification('artwork_reviews', notification)

        return jsonify({'message': 'Review added successfully', 'review_id': review_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/add_artwork', methods=['POST'])
def add_artwork():
    time.sleep(1)
    user_id = request.form.get('user_id')
    title = request.form.get('title')
    description = request.form.get('description', '')
    price = request.form.get('price')
    category = request.form.get('category')
    stock = request.form.get('stock', 0)
    photo = request.files.get('photo')

    if not user_id or not title or not price or not category:
        return jsonify({'error': 'user_id, title, price and category are required'}), 400

    try:
        role = get_user_role(user_id)
        if role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        conn = get_db_connection()
        cur = conn.cursor()

        # Получение category_id
        cur.execute('SELECT id FROM category WHERE name = %s;', (category,))
        category_result = cur.fetchone()
        if not category_result:
            cur.close()
            conn.close()
            return jsonify({'error': f'Category {category} does not exist'}), 400
        category_id = category_result[0]

        photo_url = None
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            unique_filename = f"{int(time.time())}_{filename}"
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            photo.save(photo_path)
            photo_url = f"/static/uploads/{unique_filename}"

        # Вызов процедуры для добавления артворка
        cur.execute("""
            CALL add_artwork_proc(%s, %s, %s, %s, %s, %s);
        """, (title, description, price, category_id, photo_url, stock))
        conn.commit()

        # Получение ID добавленного артикула
        cur.execute('SELECT id FROM artwork WHERE title = %s;', (title,))
        artwork_record = cur.fetchone()
        if artwork_record:
            artwork_id = artwork_record[0]
        else:
            artwork_id = None

        cur.close()
        conn.close()

        if artwork_id:
            # Удаляем кэш для всех артикулов
            invalidate_artworks_cache()

            # Отправляем уведомление о новом артикуле PubSub
            notification = {
                'type': 'new_artwork',
                'artwork_id': artwork_id,
                'title': title,
                'price': price
            }
            publish_notification('artworks', notification)

            return jsonify({'message': 'Artwork added successfully', 'artwork_id': artwork_id, 'photo_url': photo_url}), 201
        else:
            return jsonify({'error': 'Failed to add artwork'}), 500

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/delete_artwork', methods=['DELETE'])
def delete_artwork():
    data = request.get_json()
    user_id = data.get('user_id')
    artwork_id = data.get('artwork_id')

    if not user_id or not artwork_id:
        return jsonify({'error': 'user_id and artwork_id are required'}), 400

    try:
        role = get_user_role(user_id)
        if role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        conn = get_db_connection()
        cur = conn.cursor()

        # Узнать photo_url для удаления файла
        cur.execute('SELECT photo_url FROM artwork WHERE id = %s;', (artwork_id,))
        photo_result = cur.fetchone()
        photo_url = photo_result[0] if photo_result else None

        # Вызов процедуры для удаления артворка
        cur.execute("CALL delete_artwork_proc(%s);", (artwork_id,))
        conn.commit()
        cur.close()
        conn.close()

        # Удаляем файл изображения
        if photo_url:
            photo_path = os.path.join(os.getcwd(), photo_url.lstrip('/'))
            if os.path.exists(photo_path):
                os.remove(photo_path)

        return jsonify({'message': 'Artwork deleted successfully'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

# @app.route('/update_artwork', methods=['PUT'])
# def update_artwork():


@app.route('/get_user_role', methods=['GET'])
def get_role():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id is required'}), 400
    try:
        role = get_user_role(user_id)
        if role:
            return jsonify({'role': role}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Маршрут для обслуживания статических файлов (изображений)   artwoork_id___filename
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/reviews/<int:artwork_id>', methods=['GET'])
def get_reviews(artwork_id):
    try:
        # сначала пробуем взять кэш
        cached_reviews = get_cached_artwork_reviews(artwork_id)
        if cached_reviews:
            return jsonify(cached_reviews), 200

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT r.*, u.username 
            FROM review r
            JOIN "user" u ON r.user_id = u.id
            WHERE r.artwork_id = %s
            ORDER BY r.review_date DESC;
        """, (artwork_id,))
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        cur.close()
        conn.close()

        reviews = [dict(zip(colnames, row)) for row in rows]
        
        # кэшируем результаты
        cache_artwork_reviews(artwork_id, reviews)
        
        return jsonify(reviews), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/orders/<int:user_id>', methods=['GET'])
def get_orders(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id, o.order_date, o.status, oi.artwork_id, a.title, oi.quantity, oi.price
            FROM "order" o
            JOIN orderitem oi ON o.id = oi.order_id
            JOIN artwork a ON oi.artwork_id = a.id
            WHERE o.user_id = %s
            ORDER BY o.order_date DESC;
        """, (user_id,))
        orders = cur.fetchall()
        cur.close()
        conn.close()

        orders_dict = {}
        for order in orders:
            order_id = order[0]
            if order_id not in orders_dict:
                orders_dict[order_id] = {
                    'order_date': order[1].strftime('%Y-%m-%d %H:%M:%S'),
                    'status': order[2],
                    'items': []
                }
            orders_dict[order_id]['items'].append({
                'artwork_id': order[3],
                'title': order[4],
                'quantity': order[5],
                'price': float(order[6])
            })

        orders_list = []
        for order_id, details in orders_dict.items():
            orders_list.append({
                'order_id': order_id,
                'order_date': details['order_date'],
                'status': details['status'],
                'items': details['items']
            })

        return jsonify(orders_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/orders', methods=['GET'])
def get_all_orders():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT o.id, o.order_date, o.status, u.username, oi.artwork_id, a.title, oi.quantity, oi.price
            FROM "order" o
            JOIN "user" u ON o.user_id = u.id
            JOIN orderitem oi ON o.id = oi.order_id
            JOIN artwork a ON oi.artwork_id = a.id
            ORDER BY o.order_date DESC;
        """)
        orders = cur.fetchall()
        cur.close()
        conn.close()

        orders_dict = {}
        for order in orders:
            order_id = order[0]
            if order_id not in orders_dict:
                orders_dict[order_id] = {
                    'order_date': order[1].strftime('%Y-%m-%d %H:%M:%S'),
                    'status': order[2],
                    'username': order[3],
                    'items': []
                }
            orders_dict[order_id]['items'].append({
                'artwork_id': order[4],
                'title': order[5],
                'quantity': order[6],
                'price': float(order[7])
            })

        orders_list = []
        for order_id, details in orders_dict.items():
            orders_list.append({
                'order_id': order_id,
                'order_date': details['order_date'],
                'status': details['status'],
                'username': details['username'],
                'items': details['items']
            })

        return jsonify(orders_list), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)