-- Создание БД
CREATE DATABASE devops;

-- Создание пользователя для репликации
CREATE USER db_repl_user REPLICATION LOGIN PASSWORD '${DB_REPL_PASSWORD}';

-- Подключение к БД
\c devops

-- Создание таблиц, если не существует
CREATE TABLE IF NOT EXISTS emails (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS numbers (
    id SERIAL PRIMARY KEY,
    phone_number VARCHAR(20) NOT NULL
);

-- Вставка тестовых данных в таблицы
INSERT INTO emails (email) 
VALUES ('pups@pups.ru'), ('karapups@pups.ru');

INSERT INTO numbers (phone_number) 
VALUES ('88006666666'), ('+76665555555');