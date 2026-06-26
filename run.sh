#!/bin/bash
source .venv/bin/activate
URL=${1:-"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}

# Получаем оригинальное название видео с YouTube
RAW_TITLE=$(yt-dlp --print "%(title)s" "$URL")

# Санитизируем название через Python (заменяем пробелы на _, удаляем спецсимволы, обрезаем до 12 символов)
CLEAN_TITLE=$(python3 -c "import sys, re; title=sys.argv[1]; print(re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')[:12])" "$RAW_TITLE")

if [ -z "$CLEAN_TITLE" ]; then
    CLEAN_TITLE="video"
fi

FILENAME="${CLEAN_TITLE}.mp4"

# Скачиваем видео (yt-dlp сам не будет скачивать, если файл уже существует)
yt-dlp -f "bestvideo[height<=1080]+bestaudio/best" --merge-output-format mp4 -o "$FILENAME" "$URL"

# Запускаем обработку
python3 main.py "$FILENAME"
echo "готово!"
