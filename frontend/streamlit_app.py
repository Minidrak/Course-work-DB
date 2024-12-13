import streamlit as st
import requests
from PIL import Image
from io import BytesIO


API_URL = "http://backend:8000"  # docker

# Инициализация сессионных переменных
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'cart' not in st.session_state:
    st.session_state['cart'] = []

def login():
    st.title("Авторизация")
    username = st.text_input("Логин")
    password = st.text_input("Пароль", type="password")
    if st.button("Войти"):
        try:
            response = requests.post(f"{API_URL}/login", json={"username": username, "password": password})
            if response.status_code == 200:
                data = response.json()
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = data['user_id']
                st.success("Успешный вход!")
            else:
                error = response.json().get('error', 'Неизвестная ошибка')
                st.error(f"Ошибка входа: {error}")
        except requests.exceptions.ConnectionError:
            st.error("Не удалось подключиться к серверу. Проверьте настройки Docker.")

def register():
    st.title("Регистрация")
    username = st.text_input("Логин")
    email = st.text_input("Email")
    password = st.text_input("Пароль", type="password")
    confirm_password = st.text_input("Подтверждение пароля", type="password")
    
    if st.button("Зарегистрироваться"):
        if password != confirm_password:
            st.error("Пароли не совпадают")
            return
        try:
            response = requests.post(f"{API_URL}/register", json={
                "username": username,
                "email": email,
                "password": password
            })
            if response.status_code == 201:
                st.success("Регистрация прошла успешно! Теперь вы можете войти.")
            else:
                error = response.json().get('error', 'Произошла ошибка')
                st.error(f"Ошибка регистрации: {error}")
        except requests.exceptions.ConnectionError:
            st.error("Не удалось подключиться к серверу. Проверьте настройки Docker.")

def show_artworks():
    st.title("Каталог произведений искусства")
    try:
        response = requests.get(f"{API_URL}/artworks")
        if response.status_code == 200:
            artworks = response.json()
            for art in artworks:
                st.subheader(art['title'])
                st.write(f"Категория: {art['category']}")
                st.write(art['description'])
                st.write(f"Цена: {art['price']} | В наличии: {art['stock']}")

                # Отображение изображения
                if art['photo_url']:
                    image_url = f"{API_URL}{art['photo_url']}"
                    try:
                        image_response = requests.get(image_url)
                        if image_response.status_code == 200:
                            image = Image.open(BytesIO(image_response.content))
                            st.image(image, use_container_width=True)  # Обновлено
                        else:
                            st.write("Изображение недоступно")
                    except Exception as e:
                        st.write("Ошибка загрузки изображения")
                
                # Проверка наличия товара
                if art['stock'] <= 0:
                    st.warning("Товара нет в наличии")
                    continue

                # Определение максимального доступного количества
                max_quantity = art['stock']

                # Проверка, есть ли уже этот товар в корзине
                existing_item = next((item for item in st.session_state['cart'] if item['artwork_id'] == art['id']), None)
                if existing_item:
                    max_quantity = art['stock'] - existing_item['quantity']
                    if max_quantity <= 0:
                        st.warning("Достигнуто максимальное количество в корзине")
                        continue

                quantity = st.number_input(
                    f"Количество для '{art['title']}'",
                    min_value=1,
                    max_value=max_quantity,
                    value=1,
                    step=1,
                    key=f"quantity_{art['id']}"
                )

                if st.button(f"Добавить '{art['title']}' в корзину", key=f"add_{art['id']}"):
                    if existing_item:
                        existing_item['quantity'] += quantity
                    else:
                        st.session_state['cart'].append({
                            'artwork_id': art['id'],
                            'quantity': quantity,
                            'title': art['title'],
                            'price': art['price']
                        })
                    st.success(f"Добавлено {quantity} x '{art['title']}' в корзину!")
        else:
            st.error("Не удалось получить список произведений")
    except requests.exceptions.ConnectionError:
        st.error("Не удалось подключиться к серверу. Проверьте настройки Docker.")

def show_cart():
    st.title("Корзина")
    if not st.session_state['cart']:
        st.write("Ваша корзина пуста.")
        return
    
    total = 0
    for idx, item in enumerate(st.session_state['cart']):
        st.write(f"{item['title']} x {item['quantity']} = {item['quantity'] * item['price']} ")
        total += item['quantity'] * item['price']
    st.write(f"**Итого: {total}**")
    
    if st.button("Оформить заказ"):
        try:
            response = requests.post(f"{API_URL}/create_order", json={
                "user_id": st.session_state['user_id'],
                "items": [{"artwork_id": i['artwork_id'], "quantity": i['quantity']} for i in st.session_state['cart']]
            })
            if response.status_code == 201:
                data = response.json()
                st.success(f"Заказ #{data['order_id']} успешно создан!")
                st.session_state['cart'].clear()
            else:
                error = response.json().get('error', 'Произошла ошибка')
                st.error(f"Ошибка при создании заказа: {error}")
        except requests.exceptions.ConnectionError:
            st.error("Не удалось подключиться к серверу. Проверьте настройки Docker.")

def add_review():
    st.title("Оставить отзыв")
    artwork_id = st.number_input("ID произведения", min_value=1, value=1)
    rating = st.number_input("Оценка (1-5)", min_value=1, max_value=5, value=5)
    comment = st.text_area("Комментарий")
    if st.button("Отправить отзыв"):
        try:
            response = requests.post(f"{API_URL}/add_review", json={
                "user_id": st.session_state['user_id'],
                "artwork_id": artwork_id,
                "rating": rating,
                "comment": comment
            })
            if response.status_code == 201:
                st.success("Отзыв добавлен!")
            else:
                error = response.json().get('error', 'Произошла ошибка')
                st.error(f"Не удалось добавить отзыв: {error}")
        except requests.exceptions.ConnectionError:
            st.error("Не удалось подключиться к серверу. Проверьте настройки Docker.")

def add_artwork():
    st.title("Добавить произведение искусства")
    title = st.text_input("Название")
    description = st.text_area("Описание")
    price = st.number_input("Цена", min_value=0.0, step=0.01)
    category = st.text_input("Категория")
    stock = st.number_input("Количество на складе", min_value=0, step=1)
    photo = st.file_uploader("Загрузить изображение", type=['png', 'jpg', 'jpeg', 'gif'])
    
    if st.button("Добавить произведение"):
        if not title or not price or not category:
            st.error("Название, цена и категория обязательны для заполнения")
            return
        if photo is None:
            st.error("Необходимо загрузить изображение")
            return
        # Подготовка данных для отправки
        files = {'photo': (photo.name, photo, photo.type)}
        data = {
            'user_id': st.session_state['user_id'],
            'title': title,
            'description': description,
            'price': price,
            'category': category,
            'stock': stock
        }
        try:
            response = requests.post(f"{API_URL}/add_artwork", data=data, files=files)
            if response.status_code == 201:
                data = response.json()
                st.success("Произведение добавлено успешно!")
            else:
                error = response.json().get('error', 'Произошла ошибка')
                st.error(f"Ошибка добавления произведения: {error}")
        except requests.exceptions.ConnectionError:
            st.error("Не удалось подключиться к серверу. Проверьте настройки Docker.")

def delete_artwork():
    st.title("Удалить произведение искусства")
    artwork_id = st.number_input("ID произведения", min_value=1, value=1)
    
    if st.button("Удалить произведение"):
        try:
            response = requests.delete(f"{API_URL}/delete_artwork", json={
                "user_id": st.session_state['user_id'],
                "artwork_id": artwork_id
            })
            if response.status_code == 200:
                st.success("Произведение удалено успешно!")
            else:
                error = response.json().get('error', 'Произошла ошибка')
                st.error(f"Ошибка удаления произведения: {error}")
        except requests.exceptions.ConnectionError:
            st.error("Не удалось подключиться к серверу. Проверьте настройки Docker.")

def update_artwork():
    st.title("Обновить произведение искусства")
    artwork_id = st.number_input("ID произведения", min_value=1, value=1)
    title = st.text_input("Новое название (оставьте пустым, если не требуется)")
    description = st.text_area("Новое описание (оставьте пустым, если не требуется)")
    price = st.number_input("Новая цена (оставьте 0, если не требуется)", min_value=0.0, step=0.01)
    category = st.text_input("Новая категория (оставьте пустым, если не требуется)")
    stock = st.number_input("Новое количество на складе (оставьте 0, если не требуется)", min_value=0, step=1)
    photo = st.file_uploader("Загрузить новое изображение (опционально)", type=['png', 'jpg', 'jpeg', 'gif'])
    
    if st.button("Обновить произведение"):
        update_data = {
            'user_id': st.session_state['user_id'],
            'artwork_id': artwork_id
        }
        if title:
            update_data['title'] = title
        if description:
            update_data['description'] = description
        if price > 0:
            update_data['price'] = price
        if category:
            update_data['category'] = category
        if stock > 0:
            update_data['stock'] = stock
        
        files = {}
        if photo is not None:
            files['photo'] = (photo.name, photo, photo.type)
        
        try:
            response = requests.put(f"{API_URL}/update_artwork", data=update_data, files=files)
            if response.status_code == 200:
                st.success("Произведение обновлено успешно!")
            else:
                error = response.json().get('error', 'Произошла ошибка')
                st.error(f"Ошибка обновления произведения: {error}")
        except requests.exceptions.ConnectionError:
            st.error("Не удалось подключиться к серверу. Проверьте настройки Docker.")

def admin_panel():
    st.sidebar.subheader("Админ-панель")
    admin_menu = ["Добавить произведение", "Удалить произведение", "Обновить произведение"]
    choice = st.sidebar.selectbox("Меню", admin_menu)
    
    if choice == "Добавить произведение":
        add_artwork()
    elif choice == "Удалить произведение":
        delete_artwork()
    elif choice == "Обновить произведение":
        update_artwork()

def show_orders():
    st.title("Мои Заказы")
    try:
        response = requests.get(f"{API_URL}/orders/{st.session_state['user_id']}")
        if response.status_code == 200:
            orders = response.json()
            if not orders:
                st.write("У вас еще нет заказов.")
                return
            for order in orders:
                st.subheader(f"Заказ #{order['order_id']}")
                st.write(f"Дата заказа: {order['order_date']} | Статус: {order['status']}")
                st.write("**Товары:**")
                for item in order['items']:
                    st.write(f"- {item['title']} x {item['quantity']} = {item['quantity'] * item['price']} руб.")
                total = sum(item['quantity'] * item['price'] for item in order['items'])
                st.write(f"**Итого:** {total} руб.\n")
        else:
            st.error("Не удалось получить ваши заказы.")
    except requests.exceptions.ConnectionError:
        st.error("Не удалось подключиться к серверу. Проверьте настройки Docker.")

def admin_show_all_orders():
    st.title("Все Заказы")
    try:
        response = requests.get(f"{API_URL}/admin/orders")
        if response.status_code == 200:
            orders = response.json()
            if not orders:
                st.write("Нет заказов.")
                return
            for order in orders:
                st.subheader(f"Заказ #{order['order_id']} от {order['username']}")
                st.write(f"Дата заказа: {order['order_date']} | Статус: {order['status']}")
                st.write("**Товары:**")
                for item in order['items']:
                    st.write(f"- {item['title']} x {item['quantity']} = {item['quantity'] * item['price']} руб.")
                total = sum(item['quantity'] * item['price'] for item in order['items'])
                st.write(f"**Итого:** {total} руб.\n")
        else:
            st.error("Не удалось получить заказы.")
    except requests.exceptions.ConnectionError:
        st.error("Не удалось подключиться к серверу. Проверьте настройки Docker.")

def orders_page():
    if st.session_state['logged_in']:
        # Проверка роли пользователя
        try:
            response = requests.get(f"{API_URL}/get_user_role", params={"user_id": st.session_state['user_id']})
            if response.status_code == 200:
                role = response.json().get('role')
                if role == 'admin':
                    admin_show_all_orders()
                else:
                    show_orders()
            else:
                error = response.json().get('error', 'Произошла ошибка')
                st.error(f"Не удалось проверить роль пользователя: {error}")
        except requests.exceptions.ConnectionError:
            st.error("Не удалось подключиться к серверу. Проверьте настройки Docker.")
    else:
        st.warning("Пожалуйста, авторизуйтесь.")


def main():
    # Панель навигации
    menu = ["Авторизация", "Регистрация", "Каталог", "Корзина", "Отзывы", "Заказы"]
    if st.session_state['logged_in']:
        menu.append("Админ-панель")
    choice = st.sidebar.selectbox("Навигация", menu)
    
    if choice == "Авторизация":
        if not st.session_state['logged_in']:
            login()
        else:
            st.success("Вы уже вошли в систему.")
    
    elif choice == "Регистрация":
        if not st.session_state['logged_in']:
            register()
        else:
            st.warning("Вы уже вошли в систему.")
    
    elif choice == "Каталог":
        if st.session_state['logged_in']:
            show_artworks()
        else:
            st.warning("Пожалуйста, авторизуйтесь.")
    
    elif choice == "Корзина":
        if st.session_state['logged_in']:
            show_cart()
        else:
            st.warning("Пожалуйста, авторизуйтесь.")
    
    elif choice == "Отзывы":
        if st.session_state['logged_in']:
            add_review()
        else:
            st.warning("Пожалуйста, авторизуйтесь.")
    
    elif choice == "Заказы":
        if st.session_state['logged_in']:
            orders_page()
        else:
            st.warning("Пожалуйста, авторизуйтесь.")
    
    elif choice == "Админ-панель":
        if st.session_state['logged_in']:
            # Проверка роли пользователя
            try:
                response = requests.get(f"{API_URL}/get_user_role", params={"user_id": st.session_state['user_id']})
                if response.status_code == 200:
                    role = response.json().get('role')
                    if role == 'admin':
                        admin_panel()
                    else:
                        st.error("У вас нет доступа к админ-панели.")
                else:
                    error = response.json().get('error', 'Произошла ошибка')
                    st.error(f"Не удалось проверить роль пользователя: {error}")
            except requests.exceptions.ConnectionError:
                st.error("Не удалось подключиться к серверу. Проверьте настройки Docker.")
        else:
            st.warning("Пожалуйста, авторизуйтесь.")

if __name__ == "__main__":
    main()