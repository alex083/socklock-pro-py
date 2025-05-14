import os
import sqlite3
import requests
import subprocess

API_URL = os.getenv('API_URL', 'https://api.runonflux.io/apps/location/proxypoolusa')
REMOTE_USER = os.getenv('REMOTE_USER', 'proxyuser')
REMOTE_PASS = os.getenv('REMOTE_PASS', 'proxypass')
REMOTE_PORT = int(os.getenv('REMOTE_PORT', 3405))
CLIENT_PASS = os.getenv('CLIENT_PASS', 'clientpass')
PROXY_MODE = os.getenv('PROXY_MODE', 'socks5')
MAX_USERS = int(os.getenv('MAX_USERS', 55))
START_USER_ID = int(os.getenv('START_USER_ID', 5999))
SERVER_IP = requests.get('https://ifconfig.me').text.strip()

DB_FILE = '/configs/socklock.db'
CONFIG_DIR = '/configs/proxy_users'
PROXY_LIST = '/configs/proxies.txt'

os.makedirs(CONFIG_DIR, exist_ok=True)

def init_db():
    if not os.path.exists(DB_FILE):
        print("[*] Инициализация базы данных...")
        with sqlite3.connect(DB_FILE) as conn:
            conn.execute("CREATE TABLE proxies (user TEXT PRIMARY KEY, ip TEXT UNIQUE);")

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

def generate_config():
    print("[*] Генерация конфигурации...")
    init_db()

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Проверка текущих IP
        for user, ip in cursor.execute("SELECT user, ip FROM proxies;").fetchall():
            if not check_proxy(ip):
                print(f"[-] {ip} ({user}) — нерабочий")
                cursor.execute("UPDATE proxies SET ip = NULL WHERE user = ?", (user,))
            else:
                print(f"[✓] {ip} ({user}) — рабочий")

        max_id = cursor.execute("SELECT MAX(CAST(SUBSTR(user, 5) AS INTEGER)) FROM proxies;").fetchone()[0] or START_USER_ID

        ip_list = requests.get(API_URL).json()
        ip_list = [entry['ip'].split(':')[0] for entry in ip_list.get('data', [])]

        for ip in ip_list:
            exists = cursor.execute("SELECT 1 FROM proxies WHERE ip = ?", (ip,)).fetchone()
            if exists:
                continue

            current_count = cursor.execute("SELECT COUNT(*) FROM proxies WHERE ip IS NOT NULL;").fetchone()[0]
            if current_count >= MAX_USERS:
                print("[!] Достигнуто максимальное количество активных прокси")
                break

            if check_proxy(ip):
                free_user = cursor.execute("SELECT user FROM proxies WHERE ip IS NULL LIMIT 1;").fetchone()
                if free_user:
                    cursor.execute("UPDATE proxies SET ip = ? WHERE user = ?", (ip, free_user[0]))
                    print(f"[+] Назначен IP {ip} для {free_user[0]} (повторно)")
                else:
                    max_id += 1
                    user = f"user{max_id}"
                    cursor.execute("INSERT INTO proxies (user, ip) VALUES (?, ?)", (user, ip))
                    print(f"[+] Назначен IP {ip} для {user} (новый)")

        conn.commit()

    print("[*] Перегенерация конфигов на каждого пользователя...")
    open(PROXY_LIST, 'w').close()

    for user, ip in sqlite3.connect(DB_FILE).cursor().execute("SELECT user, ip FROM proxies WHERE ip IS NOT NULL;"):
        port = user[4:]
        config_path = os.path.join(CONFIG_DIR, f'{user}.cfg')

        with open(config_path, 'w') as f:
            f.write('\n'.join([
                'nserver 8.8.8.8',
                'nscache 65536',
                'maxconn 100000',
                'auth strong',
                f'users {user}:CL:{CLIENT_PASS}',
                f'allow {user}',
                f'parent 1000 socks5 {ip} {REMOTE_PORT} {REMOTE_USER} {REMOTE_PASS}',
                f"{'proxy' if PROXY_MODE == 'http' else 'socks'} -p{port} -a -i0.0.0.0 -n"
            ]))

        with open(PROXY_LIST, 'a') as f:
            f.write(f"{PROXY_MODE}://{user}:{CLIENT_PASS}@{SERVER_IP}:{port}\n")

    print("[*] Конфигурация обновлена ✅")

if __name__ == "__main__":
    generate_config()
