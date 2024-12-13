import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для взаимодействия с фронтендом

# Конфигурация для загрузки файлов
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Убедитесь, что папка для загрузок существует
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.getenv('POSTGRES_DB', 'artshop'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', 'postgres'),
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

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({'error': 'Username, email and password are required'}), 400
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Проверка, существует ли уже пользователь с таким именем или email
        cur.execute('SELECT id FROM "user" WHERE username = %s OR email = %s', (username, email))
        if cur.fetchone():
            cur.close()
            conn.close()
            return jsonify({'error': 'Username or email already exists'}), 400
        
        password_hash = generate_password_hash(password)
        
        # По умолчанию назначаем роль 'regular_user'
        cur.execute("""
            INSERT INTO "user" (username, email, password_hash, role_id)
            VALUES (%s, %s, %s, (SELECT id FROM role WHERE name = 'regular_user'))
            RETURNING id;
        """, (username, email, password_hash))
        
        user_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({'message': 'User registered successfully', 'user_id': user_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT password_hash, id FROM "user" WHERE username = %s', (username,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result is None:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        stored_hash, user_id = result
        if check_password_hash(stored_hash, password):
            # При успешной аутентификации возвращаем user_id
            return jsonify({'message': 'Login successful', 'user_id': user_id}), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/artworks', methods=['GET'])
def get_artworks():
    # Получаем список произведений искусства из view или напрямую из таблиц
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, title, description, price, category, stock, photo_url FROM view_artwork_details')
        rows = cur.fetchall()
        cur.close()
        conn.close()

        artworks = []
        for r in rows:
            artworks.append({
                'id': r[0],
                'title': r[1],
                'description': r[2],
                'price': float(r[3]),
                'category': r[4],
                'stock': r[5],
                'photo_url': r[6]  # Путь к изображению
            })
        return jsonify(artworks), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/create_order', methods=['POST'])
def create_order():
    # Ожидаем JSON вида:
    # {
    #   "user_id": <int>,
    #   "items": [
    #       {"artwork_id": <int>, "quantity": <int>}
    #   ]
    # }
    data = request.get_json()
    user_id = data.get('user_id')
    items = data.get('items')

    if not user_id or not items or not isinstance(items, list):
        return jsonify({'error': 'Invalid request data'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Проверка наличия достаточного количества товаров
        for item in items:
            artwork_id = item.get('artwork_id')
            quantity = item.get('quantity', 1)
            cur.execute("SELECT stock FROM inventory WHERE artwork_id = %s FOR UPDATE", (artwork_id,))
            result = cur.fetchone()
            if result is None:
                conn.rollback()
                return jsonify({'error': f'Artwork {artwork_id} not found in inventory'}), 400
            stock = result[0]
            if stock < quantity:
                conn.rollback()
                return jsonify({'error': f'Not enough stock for artwork {artwork_id}. Available: {stock}, Requested: {quantity}'}), 400

        # Создаем заказ
        cur.execute("""
            INSERT INTO "order" (user_id, status)
            VALUES (%s, 'pending')
            RETURNING id;
        """, (user_id,))
        order_id = cur.fetchone()[0]

        # Добавляем элементы заказа и обновляем инвентарь
        for item in items:
            artwork_id = item.get('artwork_id')
            quantity = item.get('quantity', 1)
            # Получаем текущую цену товара
            cur.execute("SELECT price FROM artwork WHERE id = %s", (artwork_id,))
            res = cur.fetchone()
            if res is None:
                conn.rollback()
                return jsonify({'error': f'Artwork {artwork_id} not found'}), 400

            price = res[0]
            # Вставляем позицию заказа
            cur.execute("""
                INSERT INTO orderitem (order_id, artwork_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, artwork_id, quantity, price))

            # Обновляем количество на складе
            cur.execute("""
                UPDATE inventory
                SET stock = stock - %s
                WHERE artwork_id = %s
            """, (quantity, artwork_id))

        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Order created successfully', 'order_id': order_id}), 201
    except psycopg2.Error as pe:
        conn.rollback()
        return jsonify({'error': f'Database error: {str(pe)}'}), 500
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/add_review', methods=['POST'])
def add_review():
    # Ожидаем JSON вида:
    # {
    #   "user_id": <int>,
    #   "artwork_id": <int>,
    #   "rating": <int>,
    #   "comment": <string>
    # }
    data = request.get_json()
    user_id = data.get('user_id')
    artwork_id = data.get('artwork_id')
    rating = data.get('rating')
    comment = data.get('comment', '')

    if not user_id or not artwork_id or not rating:
        return jsonify({'error': 'user_id, artwork_id and rating are required'}), 400

    if rating < 1 or rating > 5:
        return jsonify({'error': 'rating must be between 1 and 5'}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO reviews (user_id, artwork_id, rating, comment)
            VALUES (%s, %s, %s, %s)
        """, (user_id, artwork_id, rating, comment))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'message': 'Review added successfully'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

# Административные маршруты
@app.route('/add_artwork', methods=['POST'])
def add_artwork():
    # Ожидаем multipart/form-data с полями:
    # - user_id
    # - title
    # - description
    # - price
    # - category
    # - stock
    # - photo (файл изображения)
    if 'user_id' not in request.form:
        return jsonify({'error': 'user_id is required'}), 400

    user_id = request.form['user_id']
    title = request.form.get('title')
    description = request.form.get('description')
    price = request.form.get('price')
    category = request.form.get('category')
    stock = request.form.get('stock', 0)
    photo = request.files.get('photo')

    if not title or not price or not category:
        return jsonify({'error': 'title, price and category are required'}), 400

    try:
        role = get_user_role(user_id)
        if role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        conn = get_db_connection()
        cur = conn.cursor()

        # Получаем id категории
        cur.execute('SELECT id FROM category WHERE name = %s', (category,))
        category_result = cur.fetchone()
        if not category_result:
            conn.close()
            return jsonify({'error': f'Category {category} does not exist'}), 400
        category_id = category_result[0]

        # Вставляем произведение искусства
        cur.execute("""
            INSERT INTO artwork (title, description, price, category_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """, (title, description, price, category_id))
        artwork_id = cur.fetchone()[0]

        # Вставляем инвентаризацию
        cur.execute("""
            INSERT INTO inventory (artwork_id, stock)
            VALUES (%s, %s);
        """, (artwork_id, stock))

        # Обработка загрузки изображения
        photo_url = None
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            # Уникализируем имя файла
            unique_filename = f"{artwork_id}_{filename}"
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            photo.save(photo_path)
            # Путь для доступа к изображению
            photo_url = f"/static/uploads/{unique_filename}"
            # Обновляем artwork с photo_url
            cur.execute("""
                UPDATE artwork
                SET photo_url = %s
                WHERE id = %s;
            """, (photo_url, artwork_id))
        
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'message': 'Artwork added successfully', 'artwork_id': artwork_id, 'photo_url': photo_url}), 201
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

        # Получаем путь к изображению для удаления файла
        cur.execute('SELECT photo_url FROM artwork WHERE id = %s', (artwork_id,))
        photo_result = cur.fetchone()
        photo_url = photo_result[0] if photo_result else None

        # Удаляем инвентаризацию
        cur.execute('DELETE FROM inventory WHERE artwork_id = %s', (artwork_id,))

        # Удаляем произведение искусства
        cur.execute('DELETE FROM artwork WHERE id = %s', (artwork_id,))

        conn.commit()
        cur.close()
        conn.close()

        # Удаляем файл изображения из файловой системы
        if photo_url:
            photo_path = os.path.join(os.getcwd(), photo_url.lstrip('/'))
            if os.path.exists(photo_path):
                os.remove(photo_path)

        return jsonify({'message': 'Artwork deleted successfully'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/update_artwork', methods=['PUT'])
def update_artwork():
    # Ожидаем multipart/form-data с полями:
    # - user_id
    # - artwork_id
    # - (опционально) title, description, price, category, stock, photo (файл)
    if 'user_id' not in request.form or 'artwork_id' not in request.form:
        return jsonify({'error': 'user_id and artwork_id are required'}), 400

    user_id = request.form['user_id']
    artwork_id = request.form['artwork_id']
    title = request.form.get('title')
    description = request.form.get('description')
    price = request.form.get('price')
    category = request.form.get('category')
    stock = request.form.get('stock')
    photo = request.files.get('photo')

    try:
        role = get_user_role(user_id)
        if role != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403

        conn = get_db_connection()
        cur = conn.cursor()

        # Обновление категории, если указана
        if category:
            cur.execute('SELECT id FROM category WHERE name = %s', (category,))
            category_result = cur.fetchone()
            if not category_result:
                conn.close()
                return jsonify({'error': f'Category {category} does not exist'}), 400
            category_id = category_result[0]
            cur.execute('UPDATE artwork SET category_id = %s WHERE id = %s', (category_id, artwork_id))

        # Обновление остальных полей
        if title:
            cur.execute('UPDATE artwork SET title = %s WHERE id = %s', (title, artwork_id))
        if description:
            cur.execute('UPDATE artwork SET description = %s WHERE id = %s', (description, artwork_id))
        if price and float(price) > 0:
            cur.execute('UPDATE artwork SET price = %s WHERE id = %s', (price, artwork_id))

        # Обновление инвентаризации, если указана
        if stock and int(stock) >= 0:
            cur.execute('UPDATE inventory SET stock = %s WHERE artwork_id = %s', (stock, artwork_id))

        # Обработка загрузки нового изображения
        photo_url = None
        if photo and allowed_file(photo.filename):
            filename = secure_filename(photo.filename)
            unique_filename = f"{artwork_id}_{filename}"
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            photo.save(photo_path)
            photo_url = f"/static/uploads/{unique_filename}"
            # Обновляем artwork с новым photo_url
            cur.execute("""
                UPDATE artwork
                SET photo_url = %s
                WHERE id = %s;
            """, (photo_url, artwork_id))
        
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'message': 'Artwork updated successfully', 'photo_url': photo_url}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

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

# Маршрут для обслуживания статических файлов (изображений)
@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/reviews/<int:artwork_id>', methods=['GET'])
def get_reviews(artwork_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT r.rating, r.comment, r.review_date, u.username
            FROM reviews r
            JOIN "user" u ON r.user_id = u.id
            WHERE r.artwork_id = %s
            ORDER BY r.review_date DESC;
        """, (artwork_id,))
        reviews = cur.fetchall()
        cur.close()
        conn.close()
        
        reviews_list = []
        for review in reviews:
            reviews_list.append({
                'rating': review[0],
                'comment': review[1],
                'review_date': review[2].strftime('%Y-%m-%d %H:%M:%S'),
                'username': review[3]
            })
        return jsonify(reviews_list), 200
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
        
        # Преобразуем словарь в список
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
        
        # Преобразуем словарь в список
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