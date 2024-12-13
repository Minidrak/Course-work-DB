

-- Создание ролей
INSERT INTO role (name) VALUES ('admin'), ('editor'), ('regular_user')
ON CONFLICT (name) DO NOTHING;

-- Создание администратора

INSERT INTO "user" (username, email, password_hash, role_id)
VALUES (
    'admin',
    'admin@example.com',
    'scrypt:32768:8:1$EOQ56OemR3OixPdt$3852eeee94873f318bfd46b66b106eb815a496437ad3cc0271ffb640ead6cebee55f0d56d9fd3015d816201cd59bb757043fa481763d414fae76878e5b1928a5', -- Замените на ваш хеш
    (SELECT id FROM role WHERE name = 'admin')
)
ON CONFLICT (username) DO NOTHING;

-- Создание категорий
INSERT INTO category (name) VALUES ('Живопись'), ('Скульптура'), ('Фотография')
ON CONFLICT (name) DO NOTHING;

-- Создание произведений искусства
INSERT INTO artwork (title, description, price, category_id)
VALUES 
('Картина "Звездная ночь"', 'Говорят, что при свете дня на ней ничего не видно...', 1000.00, (SELECT id FROM category WHERE name = 'Живопись')),
('Скульптура "Давид"', 'Автор попросил убрать свою скульптуру(авторские права, соре)', 2000.00, (SELECT id FROM category WHERE name = 'Скульптура'))
ON CONFLICT (title) DO NOTHING;

-- Привязка инвентаризации
INSERT INTO inventory (artwork_id, stock)
SELECT a.id, 10 FROM artwork a WHERE a.title = 'Картина "Звездная ночь"' 
ON CONFLICT (artwork_id) DO NOTHING;

INSERT INTO inventory (artwork_id, stock)
SELECT a.id, 5 FROM artwork a WHERE a.title = 'Скульптура "Давид"'
ON CONFLICT (artwork_id) DO NOTHING;

-- Обновление last_review_date в artwork
UPDATE artwork
SET last_review_date = NULL
WHERE last_review_date IS NULL;