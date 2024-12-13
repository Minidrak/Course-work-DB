

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
    title VARCHAR(200) UNIQUE NOT NULL, -- Добавлено уникальное ограничение
    description TEXT,
    price NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    category_id INTEGER REFERENCES category(id) NOT NULL,
    photo_url VARCHAR(255)  -- Поле для хранения пути к изображению
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

-- Добавление поля last_review_date в artwork
ALTER TABLE artwork
ADD COLUMN IF NOT EXISTS last_review_date TIMESTAMP;

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

-- Создание представления для подробной информации о произведениях
CREATE OR REPLACE VIEW view_artwork_details AS
SELECT 
    a.id,
    a.title,
    a.description,
    a.price,
    c.name AS category,
    i.stock,
    a.photo_url,
    a.last_review_date
FROM 
    artwork a
JOIN 
    category c ON a.category_id = c.id
JOIN 
    inventory i ON a.id = i.artwork_id;