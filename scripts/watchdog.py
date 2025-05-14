import os
import sqlite3
import requests
import subprocess
import time

DB_FILE = '/configs/socklock.db'
CONFIG_DIR = '/configs/proxy_users'
API_URL = os.getenv('API_URL', 'https://api.runonflux.io/apps/location/proxypoolusa')
REMOTE_USER = os.getenv('REMOTE_USER', 'proxyuser')
REMOTE_PASS = os.getenv('REMOTE_PASS', 'proxypass')
REMOTE_PORT = int(os.getenv('REMOTE_PORT', 3405))
CLIENT_PASS = os.getenv('CLIENT_PASS', 'clientpass')

def check_proxy(ip):
    try:
        result = subprocess.run(
            [
                'curl', '--silent',
                '--socks5-hostname', f'{REMOTE_USER}:{REMOTE_PASS}@{ip}:{REMOTE_PORT}',
                'http://ip-api.com/json',
                '-m', '6'
            ],
            stdout=subprocess.PIPE,
            timeout=6
        )
        if result.returncode == 0:
            data = result.stdout.decode()
            if '"query":"' in data:
                extracted_ip = data.split('"query":"')[1].split('"')[0]
                parts = extracted_ip.split('.')
                if len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts):
                    return True
    except:
        pass
    return False

def replace_and_restart_user(user):
    port = user[4:]
    config_path = f"{CONFIG_DIR}/{user}.cfg"
    tmp_config = f"/tmp/{user}.cfg"

    print(f"[~] Обновляем IP для {user}...")

    ip_list = requests.get(API_URL).json()
    ip_list = [entry['ip'].split(':')[0] for entry in ip_list.get('data', [])]

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        for new_ip in ip_list:
            is_used = cursor.execute("SELECT user FROM proxies WHERE ip = ?", (new_ip,)).fetchone()
            if is_used and is_used[0] != user:
                continue

            if check_proxy(new_ip):
                cursor.execute("UPDATE proxies SET ip = ? WHERE user = ?", (new_ip, user))
                conn.commit()

                with open(tmp_config, 'w') as f:
                    f.write('\n'.join([
                        'nserver 8.8.8.8',
                        'nscache 65536',
                        'maxconn 100000',
                        'auth strong',
                        f'users {user}:CL:{CLIENT_PASS}',
                        f'allow {user}',
                        f'parent 1000 socks5 {new_ip} {REMOTE_PORT} {REMOTE_USER} {REMOTE_PASS}',
                        f'socks -p{port} -a -i0.0.0.0 -n'
                    ]))

                os.replace(tmp_config, config_path)
                subprocess.run(['pkill', '-f', f"/usr/local/3proxy/bin/3proxy {config_path}"], stderr=subprocess.DEVNULL)
                time.sleep(1)
                subprocess.Popen(['/usr/local/3proxy/bin/3proxy', config_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[*] Перезапущен процесс для {user} (обновление)")
                return True

    print(f"[-] Не удалось найти рабочий IP для {user}")
    return False

def watchdog_loop():
    while True:
        print("[*] Проверка пользователей с действующими IP...")

        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()

            for user, ip in cursor.execute("SELECT user, ip FROM proxies WHERE ip IS NOT NULL;").fetchall():
                if not check_proxy(ip):
                    print(f"[-] Найден нерабочий IP у {user} ({ip})")
                    cursor.execute("UPDATE proxies SET ip = NULL WHERE user = ?", (user,))
                    conn.commit()
                    replace_and_restart_user(user)
                else:
                    print(f"[✓] {ip} ({user}) — рабочий")

            print("[*] Проверка пользователей без IP...")

            for user, in cursor.execute("SELECT user FROM proxies WHERE ip IS NULL OR ip='';").fetchall():
                replace_and_restart_user(user)

        print("[*] Пауза 5 минут...")
        time.sleep(300)

if __name__ == "__main__":
    watchdog_loop()
