import json

notebook = {
  "nbformat": 4,
  "nbformat_minor": 0,
  "metadata": {
    "colab": {
      "name": "Video_Translator_Colab.ipynb",
      "provenance": []
    },
    "kernelspec": {
      "name": "python3",
      "display_name": "Python 3"
    },
    "language_info": {
      "name": "python"
    },
    "accelerator": "GPU"
  },
  "cells": [
    {
      "cell_type": "markdown",
      "metadata": {
        "id": "intro"
      },
      "source": [
        "# 🚀 NullOfflineVideoTranslator (Google Colab Edition)\n",
        "Убедитесь, что вы включили видеокарту: `Среда выполнения` -> `Сменить среду выполнения` -> `T4 GPU`."
      ]
    },
    {
      "cell_type": "code",
      "execution_count": None,
      "metadata": {
        "id": "main_cell"
      },
      "outputs": [],
      "source": [
        "# @title ⚙️ Интерактивная настройка и запуск\n",
        "# @markdown Заполните поля ниже и нажмите кнопку Play слева (▶️).\n",
        "\n",
        "# @markdown --- \n",
        "# @markdown **Настройки GitHub (обязательно)**\n",
        "GITHUB_REPO = \"NullCoreDeveloper/NullOfflineVideoTranslator\" # @param {type:\"string\"}\n",
        "GITHUB_TOKEN = \"\" # @param {type:\"string\"}\n",
        "# @markdown *Если репозиторий публичный, оставьте GITHUB_TOKEN пустым. Если приватный — вставьте Personal Access Token (Classic).* \n",
        "\n",
        "# @markdown --- \n",
        "# @markdown **Настройки нейросетей (обязательно)**\n",
        "HF_TOKEN = \"\" # @param {type:\"string\"}\n",
        "GEMINI_KEYS = \"\" # @param {type:\"string\"}\n",
        "\n",
        "# @markdown --- \n",
        "# @markdown **Какое видео переводим?**\n",
        "VIDEO_URL = \"https://www.youtube.com/watch?v=dQw4w9WgXcQ\" # @param {type:\"string\"}\n",
        "\n",
        "import os\n",
        "import subprocess\n",
        "\n",
        "print(\"⏳ Подготовка окружения...\")\n",
        "\n",
        "# 1. Клонирование репозитория\n",
        "if not os.path.exists(\"video-translator\"):\n",
        "    if GITHUB_TOKEN:\n",
        "        repo_url = f\"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git\"\n",
        "    else:\n",
        "        repo_url = f\"https://github.com/{GITHUB_REPO}.git\"\n",
        "    \n",
        "    !git clone {repo_url} video-translator\n",
        "\n",
        "os.chdir(\"video-translator\")\n",
        "\n",
        "# 2. Создание .env файла\n",
        "with open('.env', 'w') as f:\n",
        "    f.write(f\"HF_TOKEN={HF_TOKEN}\\n\")\n",
        "    f.write(f\"GEMINI_API_KEYS={GEMINI_KEYS}\\n\")\n",
        "    f.write(\"PROXY_URL=\\n\")\n",
        "print(\"✅ Ключи загружены!\")\n",
        "\n",
        "# 3. Установка зависимостей (тихая установка)\n",
        "print(\"📦 Установка нейросетей (это займет 2-3 минуты)...\")\n",
        "!pip install -q yt-dlp pydub ffmpeg-python demucs librosa python-dotenv google-generativeai onnxruntime-gpu\n",
        "!pip install -q git+https://github.com/m-bain/whisperx.git\n",
        "print(\"✅ Зависимости установлены!\")\n",
        "\n",
        "# 4. Запуск перевода\n",
        "print(f\"🎥 Начинаем обработку видео: {VIDEO_URL}\")\n",
        "!bash run.sh \"{VIDEO_URL}\"\n",
        "\n",
        "print(\"\\n🎉 Готово! Ваш .mp4 файл лежит в панели слева.\")"
      ]
    }
  ]
}

with open("NullOfflineVideoTranslator.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=2, ensure_ascii=False)
    
print("Playbook generated successfully: NullOfflineVideoTranslator.ipynb")
