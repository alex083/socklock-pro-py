import subprocess
import time
import threading

def run_generate_config():
    print("[*] Генерация конфигов...")
    subprocess.run(["python", "/app/scripts/generate_config.py"], check=True)

def run_start_all_users():
    print("[*] Запуск всех пользователей...")
    subprocess.run(["python", "/app/scripts/start_all_user.py"], check=True)

def run_watchdog():
    print("[*] Запуск watchdog (в фоне)...")
    subprocess.Popen(["python", "/app/scripts/watchdog.py"],
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    print("[*] Запуск SockLock Pro (Python)...")
    run_generate_config()
    run_start_all_users()
    run_watchdog()

    # Чтобы процесс контейнера не завершился
    while True:
        time.sleep(3600)
