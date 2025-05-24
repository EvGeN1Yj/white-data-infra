#!/bin/bash

echo "Остановка и удаление контейнеров..."
docker compose down

echo "Удаление Docker-образов..."
docker rmi bekk-api-gateway
docker rmi bekk-lab1-service
docker rmi bekk-lab2-service
docker rmi bekk-lab3-service
docker rmi bekk-data-generator

# Путь к целевой директории
BD_DIR="./bd"
ELASTIC_DIR="$BD_DIR/data/elasticsearch"

# Удаляем старую директорию, если существует
if [ -d "$BD_DIR" ]; then
    echo "Удаление старой директории $BD_DIR..."
    sudo rm -rf "$BD_DIR"
fi

# Создаем необходимую структуру директорий
echo "Создание структуры директорий..."
mkdir -p "$ELASTIC_DIR"

# Устанавливаем права
echo "Настройка прав для $ELASTIC_DIR..."
sudo chown -R 1000:1000 "$ELASTIC_DIR"

# Проверяем результат
if [ $? -eq 0 ]; then
    echo "Директории успешно созданы и права настроены:"
    tree "$BD_DIR" -d
else
    echo "Ошибка при настройке прав!" >&2
    exit 1
fi
