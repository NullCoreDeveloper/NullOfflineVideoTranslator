import os
import sys
import subprocess
import shutil
import venv
import time

def print_header(msg):
    print(f"\n{'='*50}\n🚀 {msg}\n{'='*50}")

def run_command(cmd, desc):
    print(f"Выполняю: {desc}...")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ Ошибка при выполнении: {desc}")
        sys.exit(1)
    print("✅ Успешно!\n")

def check_python():
    print_header("Проверка версии Python")
    if sys.version_info < (3, 10):
        print("❌ Требуется Python версии 3.10 или выше.")
        sys.exit(1)
    print(f"✅ Установлен Python {sys.version_info.major}.{sys.version_info.minor}")

def setup_venv():
    print_header("Настройка виртуального окружения")
    venv_dir = os.path.join(os.getcwd(), ".venv")
    
    if not os.path.exists(venv_dir):
        print("Создание виртуального окружения .venv...")
        venv.create(venv_dir, with_pip=True)
        print("✅ Виртуальное окружение создано.")
    else:
        print("✅ Виртуальное окружение уже существует.")

    # Check if we are running inside the venv
    if sys.prefix == sys.base_prefix:
        print("\n⚠️ ВНИМАНИЕ: Вы запустили скрипт вне виртуального окружения!")
        print("Сейчас я автоматически перезапущу этот скрипт внутри .venv...\n")
        
        # Determine the path to the venv python executable
        if os.name == 'nt':
            python_exec = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            python_exec = os.path.join(venv_dir, "bin", "python")
            
        subprocess.run([python_exec, __file__])
        sys.exit(0) # Exit the outer script

def check_system_deps():
    print_header("Проверка системных зависимостей")
    if shutil.which("ffmpeg") is None:
        print("❌ FFmpeg не найден!")
        print("Пожалуйста, установите FFmpeg:")
        print("Ubuntu/Debian: sudo apt install ffmpeg")
        print("Mac (Homebrew): brew install ffmpeg")
        print("Windows: Скачайте и добавьте в PATH (или через winget install ffmpeg)")
        sys.exit(1)
        
    if shutil.which("rubberband") is None:
        print("❌ rubberband-cli не найден!")
        print("Пожалуйста, установите rubberband (нужен для умного растяжения звука):")
        print("Ubuntu/Debian: sudo apt install rubberband-cli")
        print("Mac (Homebrew): brew install rubberband")
        print("Windows: Скачайте ZIP-архив с официального сайта (https://breakfastquay.com/rubberband/)")
        print("         распакуйте и добавьте путь к rubberband.exe в системный PATH.")
        sys.exit(1)
        
    print("✅ Системные зависимости (FFmpeg, Rubberband) установлены.")

def install_python_deps():
    print_header("Установка Python зависимостей")
    run_command("pip install -r requirements.txt", "Установка базовых библиотек из requirements.txt")
    
    print("\nУстановка WhisperX в режиме совместимости (обход ограничений версий)...")
    whisperx_cmd = (
        "rm -rf whisperx_local && "
        "git clone https://github.com/m-bain/whisperx.git whisperx_local && "
        "sed -i '/requires-python/d' whisperx_local/pyproject.toml && "
        "pip install ./whisperx_local --no-deps && "
        "rm -rf whisperx_local"
    )
    run_command(whisperx_cmd, "Кастомная сборка и установка WhisperX")

def setup_env_vars():
    print_header("Настройка API ключей (.env)")
    
    env_path = ".env"
    env_vars = {}
    
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    env_vars[k] = v
                    
    # HuggingFace Token
    print("\n[HuggingFace Token]")
    print("Нужен для скачивания нейросетей (XTTS, WhisperX/Pyannote).")
    print("1. Зарегистрируйтесь на https://huggingface.co/")
    print("2. Зайдите в Settings -> Access Tokens и создайте токен (Read).")
    print("3. ВАЖНО: Перейдите на https://hf.co/pyannote/speaker-diarization-3.1 и примите пользовательское соглашение!")
    
    hf_token = env_vars.get("HF_TOKEN", "")
    if hf_token:
        print(f"Текущий токен: {hf_token[:5]}...{hf_token[-5:]}")
        change = input("Хотите изменить его? (y/N): ").strip().lower()
        if change == 'y':
            hf_token = input("Введите новый HF_TOKEN: ").strip()
    else:
        hf_token = input("Введите HF_TOKEN: ").strip()
        
    env_vars["HF_TOKEN"] = hf_token

    # Gemini Token
    print("\n[Gemini API Key]")
    print("Нужен для перевода текста (Gemini 1.5 Flash/Pro).")
    print("Получить можно здесь: https://aistudio.google.com/app/apikey")
    
    gemini_key = env_vars.get("GEMINI_API_KEYS", "")
    if gemini_key:
        print(f"Текущий ключ: {gemini_key[:5]}...{gemini_key[-5:]}")
        change = input("Хотите изменить его? (y/N): ").strip().lower()
        if change == 'y':
            gemini_key = input("Введите новый GEMINI_API_KEYS (можно несколько через запятую): ").strip()
    else:
        gemini_key = input("Введите GEMINI_API_KEYS: ").strip()
        
    env_vars["GEMINI_API_KEYS"] = gemini_key

    # Proxy (Optional)
    print("\n[Proxy]")
    proxy = env_vars.get("PROXY_URL", "")
    if proxy:
        print(f"Текущий прокси: {proxy}")
        change = input("Хотите изменить/удалить? (y/N): ").strip().lower()
        if change == 'y':
            proxy = input("Введите PROXY_URL (например socks5h://127.0.0.1:1080) или оставьте пустым: ").strip()
    else:
        proxy = input("Введите PROXY_URL (если нужен для обхода блокировок Gemini) или нажмите Enter: ").strip()
        
    if proxy:
        env_vars["PROXY_URL"] = proxy
    elif "PROXY_URL" in env_vars:
        del env_vars["PROXY_URL"]

    # Write to .env
    with open(env_path, "w") as f:
        for k, v in env_vars.items():
            f.write(f"{k}={v}\n")
    print("\n✅ Файл .env успешно сохранен!")
    return env_vars["HF_TOKEN"]

def download_and_quantize_xtts(hf_token):
    print_header("Скачивание и квантование моделей XTTSv2 (ONNX)")
    
    try:
        from huggingface_hub import hf_hub_download
        from onnxruntime.quantization import quantize_dynamic, QuantType
    except ImportError:
        print("❌ Не найдены библиотеки huggingface_hub или onnxruntime.")
        print("Убедитесь, что шаг установки зависимостей прошел успешно.")
        sys.exit(1)

    repo_id = "pltobing/XTTSv2-Streaming-ONNX"
    files_to_download = [
        "xtts_onnx_orchestrator.py",
        "xtts_streaming_pipeline.py",
        "xtts_tokenizer.py",
        "zh_num2words.py",
        "xtts_onnx/metadata.json",
        "xtts_onnx/vocab.json",
        "xtts_onnx/mel_stats.npy",
        "xtts_onnx/conditioning_encoder.onnx",
        "xtts_onnx/speaker_encoder.onnx",
        "xtts_onnx/hifigan_vocoder.onnx",
        "xtts_onnx/embeddings/mel_embedding.npy",
        "xtts_onnx/embeddings/mel_pos_embedding.npy",
        "xtts_onnx/embeddings/text_embedding.npy",
        "xtts_onnx/embeddings/text_pos_embedding.npy",
        "xtts_onnx/gpt_model.onnx"
    ]
    
    local_dir = "xtts_models"
    os.makedirs(local_dir, exist_ok=True)
    
    print("Скачивание файлов с HuggingFace (это может занять время)...")
    for f in files_to_download:
        dest_path = os.path.join(local_dir, f)
        if not os.path.exists(dest_path):
            print(f"Скачиваю {f}...")
            try:
                hf_hub_download(repo_id=repo_id, filename=f, local_dir=local_dir, token=hf_token)
            except Exception as e:
                print(f"❌ Ошибка скачивания {f}: {e}")
                print("Проверьте валидность HF_TOKEN и подключение к интернету.")
                sys.exit(1)
        else:
            print(f"✅ {f} уже существует. Пропуск.")
            
    # Quantization
    print("\nКвантование основной модели GPT (FP32 -> INT8) для ускорения процессора...")
    gpt_fp32 = os.path.join(local_dir, "xtts_onnx", "gpt_model.onnx")
    gpt_int8 = os.path.join(local_dir, "xtts_onnx", "gpt_model_int8.onnx")
    
    if os.path.exists(gpt_fp32):
        if not os.path.exists(gpt_int8):
            print(f"Начинаю сжатие {gpt_fp32}...")
            start_time = time.time()
            quantize_dynamic(
                model_input=gpt_fp32,
                model_output=gpt_int8,
                weight_type=QuantType.QUInt8,
            )
            print(f"Сжатие завершено за {time.time() - start_time:.2f} сек.")
            print(f"Оригинал: {os.path.getsize(gpt_fp32)/1024/1024:.2f} MB -> Сжатая: {os.path.getsize(gpt_int8)/1024/1024:.2f} MB")
            
            print("Удаляю оригинальную тяжелую модель для экономии места...")
            os.remove(gpt_fp32)
        else:
            print("Сжатая модель уже существует, оригинал удаляется...")
            os.remove(gpt_fp32)
    elif os.path.exists(gpt_int8):
        print("✅ Квантованная модель (INT8) уже готова.")
    else:
        print("❌ Не найдена ни оригинальная, ни сжатая модель GPT!")
        sys.exit(1)

def main():
    print_header("Установщик Video Translator (XTTS + WhisperX)")
    check_python()
    setup_venv()
    
    # Everything below this point runs INSIDE the venv
    check_system_deps()
    install_python_deps()
    
    hf_token = setup_env_vars()
    
    download_and_quantize_xtts(hf_token)
    
    print_header("УСТАНОВКА ЗАВЕРШЕНА!")
    print("Все компоненты успешно скачаны, сжаты и настроены.")
    print("Теперь вы можете запускать перевод видео командой:")
    print("source .venv/bin/activate")
    print("./run.sh video.mp4")

if __name__ == "__main__":
    main()
