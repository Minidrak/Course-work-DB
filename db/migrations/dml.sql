

-- Создание ролей
INSERT INTO role (name) VALUES ('admin'), ('editor'), ('regular_user')
ON CONFLICT (name) DO NOTHING;

-- Создание администратора

INSERT INTO "user" (username, email, password_hash, role_id)
VALUES (
    'admin',
    'admin@example.com',
    'scrypt:32768:8:1$EOQ56OemR3OixPdt$3852eeee94873f318bfd46b66b106eb815a496437ad3cc0271ffb640ead6cebee55f0d56d9fd3015d816201cd59bb757043fa481763d414fae76878e5b1928a5',
    (SELECT id FROM role WHERE name = 'admin')
)
ON CONFLICT (username) DO NOTHING;

-- Создание категорий
INSERT INTO category (name) VALUES ('Живопись'), ('Скульптура'), ('Фотография')
ON CONFLICT (name) DO NOTHING;

-- Создание произведений искусства
INSERT INTO artwork (title, description, price, category_id, photo_url)
VALUES 
('Картина "Звездная ночь"', 'Говорят, что при свете дня на ней ничего не видно...', 1000.00, (SELECT id FROM category WHERE name = 'Живопись'), '/static/uploads/1_star_night_sky.jpg'),
('Скульптура "Давид"', 'Автор попросил убрать свою скульптуру(авторские права, сорре)', 2000.00, (SELECT id FROM category WHERE name = 'Скульптура'), '/static/uploads/2_sculptura_david.jpg'),
('Мона Лиза', 'Знаменитая картина Леонардо да Винчи', 1000000.00, 1, '/static/uploads/3_Mona_Lisa.jpg'),
('Миккеланджело', 'Скульптура Микеланджело', 500000.00, 2, '/static/uploads/4_sculptur_mikkkelangelo.jpg'),
('Ночной дозор', 'Картина Рембрандта', 800000.00, 1, '/static/uploads/5_night_dozor.jpg'),
('Подсолнухи', 'Картина Ван Гога', 900000.00, 1, '/static/uploads/6_podsolnux.jpg')
ON CONFLICT (title) DO NOTHING;

-- Привязка инвентаризации
INSERT INTO inventory (artwork_id, stock)
SELECT a.id, 10 FROM artwork a WHERE a.title = 'Картина "Звездная ночь"' 
ON CONFLICT (artwork_id) DO NOTHING;

INSERT INTO inventory (artwork_id, stock)
SELECT a.id, 5 FROM artwork a WHERE a.title = 'Скульптура "Давид"'
ON CONFLICT (artwork_id) DO NOTHING;

INSERT INTO inventory (artwork_id, stock)
SELECT a.id, 5 FROM artwork a WHERE a.title = 'Мона Лиза'
ON CONFLICT (artwork_id) DO NOTHING;

INSERT INTO inventory (artwork_id, stock)
SELECT a.id, 5 FROM artwork a WHERE a.title = 'Миккеланджело"'
ON CONFLICT (artwork_id) DO NOTHING;

INSERT INTO inventory (artwork_id, stock)
SELECT a.id, 5 FROM artwork a WHERE a.title = 'Подсолнухи'
ON CONFLICT (artwork_id) DO NOTHING;

INSERT INTO inventory (artwork_id, stock)
SELECT a.id, 5 FROM artwork a WHERE a.title = 'Ночной дозор'
ON CONFLICT (artwork_id) DO NOTHING;

-- Обновление last_review_date в artwork |
UPDATE artwork
SET last_review_date = NULL
WHERE last_review_date IS NULL;


-- users snippet
-- INSERT INTO "user" (username, email, password_hash, role_id)
-- VALUES ('admin', 'admin@example.com', 'hashed_password', 1);
-- INSERT INTO "user" (username, email, password_hash, role_id)
-- VALUES ('customer1', 'customer1@example.com', 'hashed_password', 2);
-- INSERT INTO "user" (username, email, password_hash, role_id)
-- VALUES ('moderator', 'moderator@example.com', 'hashed_password', 3);
-- INSERT INTO "user" (username, email, password_hash, role_id)
-- VALUES ('artist1', 'artist1@example.com', 'hashed_password', 4);
-- INSERT INTO "user" (username, email, password_hash, role_id)
-- VALUES ('customer2', 'customer2@example.com', 'hashed_password', 2);


--category snippet
-- INSERT INTO category (name) VALUES ('Живопись');
-- INSERT INTO category (name) VALUES ('Скульптура');
-- INSERT INTO category (name) VALUES ('Фотография');
INSERT INTO category (name) VALUES ('Графика');
INSERT INTO category (name) VALUES ('Керамика');


--artwork snippet
-- INSERT INTO artwork (title, description, price, category_id, photo_url)
-- VALUES ('Мона Лиза', 'Знаменитая картина Леонардо да Винчи', 1000000.00, 1, '/static/uploads/3_Mona_Lisa.jpg');
-- INSERT INTO artwork (title, description, price, category_id, photo_url)
-- VALUES ('Давид', 'Скульптура Микеланджело', 500000.00, 2, '/static/uploads/4_sculptur_mikkkelangelo.jpg');
-- INSERT INTO artwork (title, description, price, category_id, photo_url)
-- VALUES ('Ночной дозор', 'Картина Рембрандта', 800000.00, 1, '/static/uploads/5_night_dozor.jpg');
-- INSERT INTO artwork (title, description, price, category_id, photo_url)
-- VALUES ('Подсолнухи', 'Картина Ван Гога', 900000.00, 1, '/static/uploads/6_podsolnux.jpg');


--inventory snippet
-- INSERT INTO inventory (artwork_id, stock) VALUES (1, 10);
-- INSERT INTO inventory (artwork_id, stock) VALUES (2, 5);
-- INSERT INTO inventory (artwork_id, stock) VALUES (3, 8);
-- INSERT INTO inventory (artwork_id, stock) VALUES (4, 12);


--upd inv
-- UPDATE inventory
-- SET stock = 12
-- WHERE artwork_id = 1;


--order snippet
-- INSERT INTO "order" (user_id, order_date, status)
-- VALUES (2, '2024-12-01 10:30:00', 'Placed');
-- INSERT INTO "order" (user_id, order_date, status)
-- VALUES (2, '2024-12-05 14:20:00', 'Shipped');
-- INSERT INTO "order" (user_id, order_date, status)
-- VALUES (5, '2024-12-10 09:45:00', 'Delivered');
-- INSERT INTO "order" (user_id, order_date, status)
-- VALUES (3, '2024-12-12 16:00:00', 'Placed');


--orderitem snippet
-- INSERT INTO orderitem (order_id, artwork_id, quantity, price)
-- VALUES (1, 1, 2, 1000000.00);
-- INSERT INTO orderitem (order_id, artwork_id, quantity, price)
-- VALUES (1, 3, 1, 800000.00);
-- INSERT INTO orderitem (order_id, artwork_id, quantity, price)
-- VALUES (2, 2, 1, 500000.00);
-- INSERT INTO orderitem (order_id, artwork_id, quantity, price)
-- VALUES (3, 4, 3, 900000.00);
-- INSERT INTO orderitem (order_id, artwork_id, quantity, price)
-- VALUES (4, 5, 1, 600000.00);


--reviews snippet
-- INSERT INTO reviews (user_id, artwork_id, rating, comment, review_date)
-- VALUES (2, 1, 5, 'Великолепная картина!', '2024-12-02 11:15:00');
-- INSERT INTO reviews (user_id, artwork_id, rating, comment, review_date)
-- VALUES (5, 3, 4, 'Очень красивая работа', '2024-12-06 17:30:00');
-- INSERT INTO reviews (user_id, artwork_id, rating, comment, review_date)
-- VALUES (3, 2, 4, 'Впечатляющая скульптура', '2024-12-11 13:45:00');
-- INSERT INTO reviews (user_id, artwork_id, rating, comment, review_date)
-- VALUES (2, 4, 5, 'Потрясающие цвета и композиция', '2024-12-13 09:20:00');
