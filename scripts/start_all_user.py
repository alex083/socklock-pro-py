import os
import subprocess

CONFIG_DIR = '/configs/proxy_users'

def start_all_users():
    print("[*] Старт всех пользователей...")

    for cfg in os.listdir(CONFIG_DIR):
        if cfg.endswith('.cfg'):
            cfg_path = os.path.join(CONFIG_DIR, cfg)
            print(f"[+] Запуск {cfg}")
            subprocess.Popen(['/usr/local/3proxy/bin/3proxy', cfg_path],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)

    print("[*] Все пользователи запущены ✅")

if __name__ == "__main__":
    start_all_users()
