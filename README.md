# Course-work-DB
## ✨Сервис по продаже произведений искусства✨
Версия Python: 3.10 slim (На python 3.13 не работал psycopg2)
Инструкция:
- Открыть docker-compose.yml
- Изменить порт у сервиса "db" с "1:5432" на привычный "5432:5432"
В терминале: 
```
docker-compose up --build
```
- Открыть в браузере: 127.0.0.1:8501
Изначально предоставлен аккаунт админа:
```
login: admin
password: admin
```
Для удобства был использован порт 1 для открытия базы данных в докере внешне в DBveaver.
Можно использовать и другой метод подключения к базе данных прямо в консоли в докере:
```
docker exec -it course_work_db_2-db-1 bash
psql -U postgres -d artshop
```

![alt text](image-1.png)