import os
import sys
import time
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RANCHER_URL = os.getenv("RANCHER_URL", "https://rancher")
SERVER_EXTERNAL_URL = os.getenv("SERVER_EXTERNAL_URL", "https://localhost:8443")
BOOTSTRAP_PASSWORD = os.getenv("CATTLE_BOOTSTRAP_PASSWORD", "admin")
NEW_ADMIN_PASSWORD = os.getenv("RANCHER_ADMIN_PASSWORD", "SuperSecretPassword123!")
TOKEN_FILE_PATH = os.getenv("TOKEN_FILE_PATH", "/shared/rancher_token.txt")

def wait_for_rancher(timeout: int = 300) -> None:
    """Ожидает готовности Rancher API (/ping)."""
    print(f"Ожидание готовности Rancher по адресу {RANCHER_URL}...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(f"{RANCHER_URL}/ping", verify=False, timeout=5)
            api = requests.get(
                f"{RANCHER_URL}/v3-public/localProviders/local",
                verify=False,
                timeout=5,
            )
            if resp.status_code == 200 and resp.text.strip() == "pong" and api.status_code == 200:
                print("Rancher API готов к работе!")
                return
        except requests.RequestException:
            pass
        time.sleep(5)
    print("Ошибка: превышено время ожидания Rancher API.", file=sys.stderr)
    sys.exit(1)

def login(password: str) -> str:
    """Авторизуется в Rancher и возвращает временный токен сессии."""
    resp = requests.post(
        f"{RANCHER_URL}/v3-public/localProviders/local?action=login",
        json={"username": "admin", "password": password},
        verify=False,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]

def main() -> None:
    if os.path.exists(TOKEN_FILE_PATH) and os.path.getsize(TOKEN_FILE_PATH) > 0:
        print(f"Токен уже существует в {TOKEN_FILE_PATH}. Повторная инициализация не требуется.")
        sys.exit(0)

    wait_for_rancher()

    try:
        session_token = login(BOOTSTRAP_PASSWORD)
        need_password_change = True
    except requests.HTTPError:
        print("Не удалось войти с bootstrap-паролем, пробуем постоянный пароль...")
        session_token = login(NEW_ADMIN_PASSWORD)
        need_password_change = False

    headers = {"Authorization": f"Bearer {session_token}"}

    if need_password_change:
        print("Смена пароля администратора...")
        resp = requests.post(
            f"{RANCHER_URL}/v3/users?action=changepassword",
            json={
                "currentPassword": BOOTSTRAP_PASSWORD,
                "newPassword": NEW_ADMIN_PASSWORD,
            },
            headers=headers,
            verify=False,
            timeout=10,
        )
        resp.raise_for_status()

    print(f"Установка server-url: {SERVER_EXTERNAL_URL}...")
    resp = requests.put(
        f"{RANCHER_URL}/v3/settings/server-url",
        json={"name": "server-url", "value": SERVER_EXTERNAL_URL},
        headers=headers,
        verify=False,
        timeout=10,
    )
    resp.raise_for_status()

    requests.put(
        f"{RANCHER_URL}/v3/settings/telemetry-opt",
        json={"name": "telemetry-opt", "value": "out"},
        headers=headers,
        verify=False,
        timeout=10,
    )

    print("Генерация API-токена для backend...")
    resp = requests.post(
        f"{RANCHER_URL}/v3/tokens",
        json={
            "type": "token",
            "description": "backend-service-token",
            "ttl": 0,  # 0 = бессрочный токен
        },
        headers=headers,
        verify=False,
        timeout=10,
    )
    resp.raise_for_status()
    api_token = resp.json()["token"]

    # 6. Сохраняем токен в общий Docker volume
    os.makedirs(os.path.dirname(TOKEN_FILE_PATH), exist_ok=True)
    with open(TOKEN_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(api_token)

    print(f"Инициализация завершена успешно! Токен сохранен в {TOKEN_FILE_PATH}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Критическая ошибка при настройке Rancher: {exc}", file=sys.stderr)
        sys.exit(1)