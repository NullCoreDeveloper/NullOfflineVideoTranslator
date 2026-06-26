#!/bin/bash
source .venv/bin/activate
URL=${1:-"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
TARGET_LANG=${2:-"ru"}

# Получаем оригинальное название видео с YouTube
RAW_TITLE=$(yt-dlp --print "%(title)s" "$URL")

# Санитизируем название через Python (заменяем пробелы на _, удаляем спецсимволы, обрезаем до 12 символов)
CLEAN_TITLE=$(python3 -c "import sys, re; title=sys.argv[1]; print(re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')[:12])" "$RAW_TITLE")

if [ -z "$CLEAN_TITLE" ]; then
    CLEAN_TITLE="video"
fi

FILENAME="${CLEAN_TITLE}.mp4"

yt-dlp -f "bestvideo[height<=1080]+bestaudio/best" --merge-output-format mp4 -o "$FILENAME" "$URL"

if [ ! -f "$FILENAME" ]; then
    echo "===================================================================="
    echo "❌ КРИТИЧЕСКАЯ ОШИБКА: yt-dlp не смог скачать видео с YouTube!"
    echo "Скорее всего, сработала защита от ботов (Sign in to confirm you're not a bot)."
    echo "Google Colab иногда временно блокируется Ютубом."
    echo ""
    echo "💡 РЕШЕНИЕ 1: В меню Colab нажмите 'Среда выполнения' -> 'Отключиться и удалить среду'. Затем запустите всё заново (вы получите чистый сервер)."
    echo "💡 РЕШЕНИЕ 2: Скачайте видео на ПК, выберите выше 'INPUT_MODE = Local File', перетащите файл в папку 'video-translator' слева и запустите ячейку."
    echo "===================================================================="
    exit 1
fi

# Запускаем обработку
python3 main.py "$FILENAME" --target_lang "$TARGET_LANG"
echo "готово!"
