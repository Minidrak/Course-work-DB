
-- Таблица ролей
CREATE TABLE IF NOT EXISTS role (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL
);

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id INTEGER REFERENCES role(id) NOT NULL
);

-- Таблица категорий
CREATE TABLE IF NOT EXISTS category (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

-- Таблица произведений искусства
CREATE TABLE IF NOT EXISTS artwork (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) UNIQUE NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    category_id INTEGER REFERENCES category(id) NOT NULL,
    photo_url VARCHAR(255),
    last_review_date TIMESTAMP
);

-- Таблица инвентаризации
CREATE TABLE IF NOT EXISTS inventory (
    id SERIAL PRIMARY KEY,
    artwork_id INTEGER REFERENCES artwork(id) UNIQUE NOT NULL,
    stock INTEGER NOT NULL CHECK (stock >= 0)
);

-- Таблица заказов
CREATE TABLE IF NOT EXISTS "order" (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "user"(id) NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) NOT NULL
);

-- Таблица элементов заказа
CREATE TABLE IF NOT EXISTS orderitem (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES "order"(id) NOT NULL,
    artwork_id INTEGER REFERENCES artwork(id) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0)
);

-- Таблица отзывов
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "user"(id) NOT NULL,
    artwork_id INTEGER REFERENCES artwork(id) NOT NULL,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание функции триггера для обновления last_review_date
CREATE OR REPLACE FUNCTION update_last_review_date()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE artwork
    SET last_review_date = NEW.review_date
    WHERE id = NEW.artwork_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Создание триггера
CREATE TRIGGER trg_update_last_review_date
AFTER INSERT ON reviews
FOR EACH ROW
EXECUTE FUNCTION update_last_review_date();


--  процедура для регистрации пользователя
CREATE OR REPLACE PROCEDURE register_user_proc(
    p_username VARCHAR,
    p_email VARCHAR,
    p_password_hash VARCHAR
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO "user" (username, email, password_hash, role_id)
    VALUES (
        p_username, 
        p_email, 
        p_password_hash, 
        (SELECT id FROM role WHERE name='regular_user')
    );
    --ON CONFLICT (username, email) DO NOTHING;
END;
$$;

--  процедура для аутентификации пользователя
CREATE OR REPLACE FUNCTION login_user_proc(
    p_username VARCHAR,
    p_password VARCHAR
)
RETURNS TABLE(user_id INTEGER, role VARCHAR) AS $$
BEGIN
    RETURN QUERY
    SELECT u.id, r.name
    FROM "user" u
    JOIN role r ON u.role_id = r.id
    WHERE u.username = p_username
      AND u.password_hash = p_password; 
END;
$$ LANGUAGE plpgsql;

--  процедура для создания заказа
CREATE OR REPLACE PROCEDURE create_order_proc(
    p_user_id INTEGER,
    p_artwork_id INTEGER,
    p_quantity INTEGER,
    OUT p_order_id INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Проверка наличия товара
    IF (SELECT stock FROM inventory WHERE artwork_id = p_artwork_id) < p_quantity THEN
        RAISE EXCEPTION 'Недостаточно товара на складе';
    END IF;

    -- Создание заказа
    INSERT INTO "order" (user_id, status)
    VALUES (p_user_id, 'pending')
    RETURNING id INTO p_order_id;

    -- Добавление элемента заказа
    INSERT INTO orderitem (order_id, artwork_id, quantity, price)
    SELECT p_order_id, a.id, p_quantity, a.price
    FROM artwork a
    WHERE a.id = p_artwork_id;

    -- Обновление инвентаря
    UPDATE inventory
    SET stock = stock - p_quantity
    WHERE artwork_id = p_artwork_id;
END;
$$;

--  процедура для добавления отзыва
CREATE OR REPLACE PROCEDURE add_review_proc(
    p_user_id INTEGER,
    p_artwork_id INTEGER,
    p_rating INTEGER,
    p_comment TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO reviews (user_id, artwork_id, rating, comment)
    VALUES (p_user_id, p_artwork_id, p_rating, p_comment);
END;
$$;

--  процедура для получения списка произведений искусства
CREATE OR REPLACE FUNCTION get_artworks_proc()
RETURNS TABLE(
    id INTEGER,
    title VARCHAR,
    description TEXT,
    price NUMERIC,
    category VARCHAR,
    stock INTEGER,
    photo_url VARCHAR,
    last_review_date TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id, a.title, a.description, a.price, c.name, i.stock, a.photo_url, a.last_review_date
    FROM 
        artwork a
    JOIN 
        category c ON a.category_id = c.id
    JOIN 
        inventory i ON a.id = i.artwork_id;
END;
$$ LANGUAGE plpgsql;

--  процедура для добавления произведения искусства (admin)
CREATE OR REPLACE PROCEDURE add_artwork_proc(
    p_title VARCHAR,
    p_description TEXT,
    p_price NUMERIC,
    p_category_id INTEGER,
    p_photo_url VARCHAR,
    p_stock INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO artwork (title, description, price, category_id, photo_url)
    VALUES (p_title, p_description, p_price, p_category_id, p_photo_url)
    ON CONFLICT (title) DO NOTHING;

    -- Получение artwork_id
    DECLARE
        v_artwork_id INTEGER;
    BEGIN
        SELECT id INTO v_artwork_id FROM artwork WHERE title = p_title;
        IF v_artwork_id IS NOT NULL THEN
            INSERT INTO inventory (artwork_id, stock)
            VALUES (v_artwork_id, p_stock)
            ON CONFLICT (artwork_id) DO UPDATE SET stock = inventory.stock + EXCLUDED.stock;
        END IF;
    END;
END;
$$;

--  процедура для обновления инвентаря
CREATE OR REPLACE PROCEDURE update_inventory_proc(
    p_artwork_id INTEGER,
    p_quantity INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE inventory
    SET stock = stock + p_quantity
    WHERE artwork_id = p_artwork_id;
END;
$$;

--  процедура для удаления произведения искусства (администратор)
CREATE OR REPLACE PROCEDURE delete_artwork_proc(
    p_artwork_id INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM reviews WHERE artwork_id = p_artwork_id;
    DELETE FROM orderitem WHERE artwork_id = p_artwork_id;
    DELETE FROM inventory WHERE artwork_id = p_artwork_id;
    DELETE FROM artwork WHERE id = p_artwork_id;
END;
$$;

--  процедура для получения отзывов по произведению
CREATE OR REPLACE FUNCTION get_reviews_proc(p_artwork_id INTEGER)
RETURNS TABLE(
    rating INTEGER,
    comment TEXT,
    review_date TIMESTAMP,
    username VARCHAR
) AS $$
BEGIN
    RETURN QUERY
    SELECT r.rating, r.comment, r.review_date, u.username
    FROM reviews r
    JOIN "user" u ON r.user_id = u.id
    WHERE r.artwork_id = p_artwork_id
    ORDER BY r.review_date DESC;
END;
$$ LANGUAGE plpgsql;
