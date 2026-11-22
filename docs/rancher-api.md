# Rancher API: заметки исследования

Документ фиксирует, как портал создаёт Kubernetes-песочницу через Rancher API:
какие вызовы нужны, какие форматы запросов и ответов ожидаются, где находятся
подводные камни и какие привилегии действительно необходимы.

> **Статус:** рабочий черновик исследования для Rancher `v2.9.3` в Docker.
> Часть вызовов уже подтверждена на локальном стенде, часть требует проверки
> (такие места помечены ⚠️). Документ нужно обновлять по мере исследования:
> фиксируйте здесь фактические ответы API, а не предположения.

## 1. Стенд и базовый URL

Rancher запускается сервисом `rancher` из `docker-compose.yaml`:

- с хоста: <https://localhost:8443>;
- внутри Docker-сети: `https://rancher:443`;
- API: `<base>/v3` (Rancher 2.x), публичный API логина: `<base>/v3-public`;
- встроенный кластер: `local` (ID кластера — строка `local`).

Все примеры ниже используют переменные:

```bash
export RANCHER=https://localhost:8443
export RANCHER_PORT=8443
export ADMIN_PASSWORD=local-dev-only-change-me
```

Для самоподписанного сертификата используйте `curl -k`. В бэкенде проверка TLS
отключается только для локального стенда (см.
[ADR 0002](decisions/0002-bootstrap-and-tls.md)).

## 2. Аутентификация

### 2.1 Логин администратора

Первичный пароль задаётся переменной `CATTLE_BOOTSTRAP_PASSWORD` (в проекте —
`RANCHER_BOOTSTRAP_PASSWORD`) при **первом** старте Rancher. Дальше пароль
хранится в volume Rancher; изменение переменной окружения его не меняет.

```bash
LOGIN_JSON=$(curl -sk -X POST \
  "$RANCHER/v3-public/localProviders/local?action=login" \
  -H 'Content-Type: application/json' \
  -d "{
    \"username\": \"admin\",
    \"password\": \"$ADMIN_PASSWORD\",
    \"responseType\": \"json\"
  }")

ADMIN_TOKEN=$(echo "$LOGIN_JSON" | jq -r .token)
```

Ожидаемый ответ — объект токена; нужное поле — `.token` (значение вида
`token-xxxxx`). Дальше токен передаётся в заголовке:

```http
Authorization: Bearer token-xxxxx
Content-Type: application/json
```

### 2.2 Долгоживущий API-токен для бэкенда

Логин-токен удобно использовать только в `rancher-init`. Для бэкенда
выпускается отдельный токен без срока жизни:

```bash
TOKEN_JSON=$(curl -sk -X POST "$RANCHER/v3/tokens" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "type": "token",
    "description": "bees-in-kube backend",
    "ttl": 0
  }')

BACKEND_TOKEN=$(echo "$TOKEN_JSON" | jq -r .token)
```

Важно:

- секрет токена (`token`) показывается **только один раз** — сохраните его в
  общий volume и не пишите в логи;
- `ttl: 0` означает «без истечения» ⚠️ (проверьте на своей версии Rancher);
- храните файл с токеном с правами `0600`;
- для production нужен отдельный пользователь/роль с минимальными правами, а
  не admin-токен (в MVP допустимо, но должно быть осознанным решением).

### 2.3 Проверка токена

```bash
curl -sk "$RANCHER/v3/users?me=true" \
  -H "Authorization: Bearer $BACKEND_TOKEN" | jq '.data[0] | {id, username}'
```

## 3. Объекты и идентификаторы

| Объект | Коллекция | Пример ID | Назначение |
| --- | --- | --- | --- |
| Кластер | `/v3/clusters` | `local` | Встроенный кластер Rancher |
| Проект | `/v3/projects` | `local:p-abc12` | Граница песочницы |
| Namespace | `/v3/clusters/local/namespaces` | `sandbox-abc12` | Где работает приложение |
| Пользователь | `/v3/users` | `u-abc12` | Учётка песочницы |
| Привязка роли проекта | `/v3/projectRoleTemplateBindings` | `local:p-abc12:prtb-xyz` | Доступ пользователя к проекту |
| Роль проекта | `/v3/roleTemplates` | `project-member` | Набор прав внутри проекта |
| Токен | `/v3/tokens` | `token-abc12` | Аутентификация API |

Проект и namespace удобно именовать одинаково: `sandbox-<id>`, где `<id>` —
короткий уникальный идентификатор (например, первые 8 символов UUID).
Имена должны соответствовать DNS-1123 (lowercase, цифры, дефисы).

## 4. Сценарий создания песочницы

### 4.0 Дождаться готовности Rancher

`rancher-init` не должен начинать работу сразу: Rancher поднимается минутами.
Минимально — дождаться ответа `/ping`, затем убедиться, что API отвечает:

```bash
until curl -fsSk "$RANCHER/ping" >/dev/null; do
  echo "waiting for rancher..."
  sleep 5
done

until curl -fsSk "$RANCHER/v3" >/dev/null; do
  sleep 5
done
```

⚠️ Дополнительно проверьте, что кластер `local` перешёл в состояние `active`:
при первом старте Rancher провижинит его не мгновенно.

### 4.1 Создать проект

```bash
PROJECT_JSON=$(curl -sk -X POST "$RANCHER/v3/projects" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"type\": \"project\",
    \"name\": \"sandbox-$SANDBOX_ID\",
    \"clusterId\": \"local\",
    \"description\": \"Bees-In-Kube sandbox $SANDBOX_ID\",
    \"labels\": {
      \"bees-in-kube/sandbox-id\": \"$SANDBOX_ID\",
      \"bees-in-kube/created-at\": \"$CREATED_AT\"
    }
  }")

PROJECT_ID=$(echo "$PROJECT_JSON" | jq -r .id)
```

Ожидаемо: `id` вида `local:p-xxxxx`, `state`/`transitioning` — служебные поля.

### 4.2 Создать namespace в проекте

```bash
curl -sk -X POST "$RANCHER/v3/clusters/local/namespaces" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"type\": \"namespace\",
    \"name\": \"sandbox-$SANDBOX_ID\",
    \"clusterId\": \"local\",
    \"projectId\": \"$PROJECT_ID\",
    \"labels\": {
      \"bees-in-kube/sandbox-id\": \"$SANDBOX_ID\"
    }
  }"
```

⚠️ Проверьте, какой из вариантов принимает ваша версия Rancher:

- `POST /v3/clusters/local/namespaces` с `projectId` в теле (основной вариант);
- `POST /v3/projects/<project-id>/namespaces` (если доступен).

После создания дождитесь `state: active`, прежде чем выдавать пользователю
kubeconfig:

```bash
until [ "$(curl -sk "$RANCHER/v3/clusters/local/namespaces/sandbox-$SANDBOX_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq -r .state)" = "active" ]; do
  sleep 2
done
```

### 4.3 Создать пользователя песочницы

```bash
USER_JSON=$(curl -sk -X POST "$RANCHER/v3/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"type\": \"user\",
    \"username\": \"sandbox-$SANDBOX_ID\",
    \"password\": \"$SANDBOX_PASSWORD\",
    \"mustChangePassword\": false,
    \"enabled\": true
  }")

USER_ID=$(echo "$USER_JSON" | jq -r .id)
```

Требования и предостережения:

- пароль генерируйте криптографически стойко (≥ 20 символов);
- `mustChangePassword: false` обязателен, иначе первый логин потребует смены
  пароля и автоматический сценарий сломается;
- пароль нельзя писать в логи; он нужен только для получения kubeconfig и
  дальнейшей работы пользователя;
- при повторном запросе с тем же именем Rancher вернёт ошибку уникальности —
  генерируйте уникальные имена.

### 4.4 Выдать доступ к проекту

```bash
curl -sk -X POST "$RANCHER/v3/projectRoleTemplateBindings" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"type\": \"projectRoleTemplateBinding\",
    \"projectId\": \"$PROJECT_ID\",
    \"userId\": \"$USER_ID\",
    \"roleTemplateId\": \"project-member\"
  }"
```

Почему `project-member`, а не `project-owner`:

- `project-member` позволяет создавать и менять рабочие нагрузки внутри
  namespace проекта;
- `project-owner` дополнительно управляет участниками и настройками проекта —
  песочнице это не нужно;
- `cluster-owner`/`cluster-member` дают доступ на уровне кластера и в MVP не
  используются (см. раздел 7).

⚠️ В некоторых версиях вместо `userId` используется
`userPrincipalId: "local://u-xxxxx"`. Проверьте схему своей версии через
`GET /v3/projectRoleTemplateBindings` или OpenAPI-схему Rancher.

### 4.5 Получить kubeconfig пользователя

Рекомендуемый путь — войти как пользователь песочницы и попросить Rancher
сгенерировать kubeconfig от его имени:

```bash
USER_LOGIN=$(curl -sk -X POST \
  "$RANCHER/v3-public/localProviders/local?action=login" \
  -H 'Content-Type: application/json' \
  -d "{
    \"username\": \"sandbox-$SANDBOX_ID\",
    \"password\": \"$SANDBOX_PASSWORD\",
    \"responseType\": \"json\"
  }")

USER_TOKEN=$(echo "$USER_LOGIN" | jq -r .token)

KUBECONFIG_JSON=$(curl -sk -X POST \
  "$RANCHER/v3/clusters/local?action=generateKubeconfig" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H 'Content-Type: application/json')

KUBECONFIG_YAML=$(echo "$KUBECONFIG_JSON" | jq -r .config)
```

В ответе ожидается поле `.config` с YAML kubeconfig. ⚠️ Проверьте, что в
kubeconfig попал **пользовательский** токен (вида `kubeconfig-u-xxxxx`), а не
admin-токен.

Альтернатива ⚠️: выпустить пользователю токен с `ttl: 0` через `/v3/tokens` и
собрать kubeconfig вручную. Этот путь требует прав на создание токена от имени
другого пользователя и должен быть проверен отдельно.

### 4.6 Сохранить метаданные

Отдельной БД в MVP нет. Минимально необходимое состояние хранится в Rancher:

- `bees-in-kube/sandbox-id` — ID песочницы;
- `bees-in-kube/created-at` — время создания;
- `bees-in-kube/owner` — имя пользователя песочницы (при необходимости).

Метки ставятся на проект и namespace. По ним можно перечислить песочницы:

```bash
curl -sk "$RANCHER/v3/projects?clusterId=local&labelSelector=bees-in-kube%2Fsandbox-id" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

⚠️ Проверьте синтаксис `labelSelector` и экранирование `/` в вашей версии API.

## 5. Полный пример

```bash
#!/usr/bin/env bash
set -euo pipefail

RANCHER=${RANCHER:-https://localhost:8443}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-local-dev-only-change-me}
SANDBOX_ID=${SANDBOX_ID:-$(openssl rand -hex 4)}
NAMESPACE="sandbox-$SANDBOX_ID"
PROJECT_NAME="sandbox-$SANDBOX_ID"
USERNAME="sandbox-$SANDBOX_ID"
USER_PASSWORD=$(openssl rand -base64 32)
CREATED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

login() {
  curl -sk -X POST "$RANCHER/v3-public/localProviders/local?action=login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"$1\",\"password\":\"$2\",\"responseType\":\"json\"}" \
    | jq -r .token
}

ADMIN_TOKEN=$(login admin "$ADMIN_PASSWORD")

PROJECT_ID=$(curl -sk -X POST "$RANCHER/v3/projects" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"type\":\"project\",\"name\":\"$PROJECT_NAME\",\"clusterId\":\"local\"}" \
  | jq -r .id)

curl -sk -X POST "$RANCHER/v3/clusters/local/namespaces" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"type\":\"namespace\",\"name\":\"$NAMESPACE\",\"clusterId\":\"local\",\"projectId\":\"$PROJECT_ID\"}" \
  >/dev/null

USER_ID=$(curl -sk -X POST "$RANCHER/v3/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"type\":\"user\",\"username\":\"$USERNAME\",\"password\":\"$USER_PASSWORD\",\"mustChangePassword\":false,\"enabled\":true}" \
  | jq -r .id)

curl -sk -X POST "$RANCHER/v3/projectRoleTemplateBindings" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{\"type\":\"projectRoleTemplateBinding\",\"projectId\":\"$PROJECT_ID\",\"userId\":\"$USER_ID\",\"roleTemplateId\":\"project-member\"}" \
  >/dev/null

USER_TOKEN=$(login "$USERNAME" "$USER_PASSWORD")

KUBECONFIG_YAML=$(curl -sk -X POST \
  "$RANCHER/v3/clusters/local?action=generateKubeconfig" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H 'Content-Type: application/json' | jq -r .config)

# Rancher может вернуть внутренний адрес (https://rancher:443).
# Для хоста заменяем server на публичный адрес.
echo "$KUBECONFIG_YAML" \
  | sed "s#server: .*#server: https://localhost:${RANCHER_PORT}/k8s/clusters/local#"

echo "sandbox id:    $SANDBOX_ID"
echo "namespace:     $NAMESPACE"
echo "project id:    $PROJECT_ID"
echo "user id:       $USER_ID"
echo "user password: $USER_PASSWORD"
```

## 6. Kubeconfig, endpoint и TLS

Ожидаемая структура kubeconfig:

```yaml
apiVersion: v1
kind: Config
clusters:
  - name: local
    cluster:
      server: https://localhost:8443/k8s/clusters/local
      insecure-skip-tls-verify: true
users:
  - name: sandbox-abcd1234
    user:
      token: kubeconfig-u-xxxxx
contexts:
  - name: sandbox-abcd1234
    context:
      cluster: local
      user: sandbox-abcd1234
      namespace: sandbox-abcd1234
current-context: sandbox-abcd1234
```

Важные моменты:

- **endpoint зависит от того, откуда его получили.** Если `generateKubeconfig`
  вызван внутри Docker-сети по `https://rancher:443`, в kubeconfig может
  попасть недоступный с хоста адрес. Перезапишите `server` на
  `https://localhost:${RANCHER_PORT}/k8s/clusters/local`.
- **TLS.** Сертификат Rancher самоподписанный. Для локального стенда допустим
  `insecure-skip-tls-verify: true`; альтернатива — положить CA Rancher в
  `certificate-authority-data`. Не отключайте проверку TLS за пределами
  локальной разработки.
- **Порт.** При переопределении `RANCHER_PORT` endpoint в kubeconfig должен
  следовать за ним; портал не должен отдавать жёстко зашитый `8443`.
- **Namespace в контексте.** Удобно сразу проставить namespace песочницы,
  чтобы `kubectl get pods` работал без `-n`.
- **Проверка доступа.** Пользователь должен видеть только свой namespace:

  ```bash
  export KUBECONFIG=./sandbox-abcd1234.kubeconfig.yaml
  kubectl get namespaces          # Forbidden
  kubectl -n sandbox-abcd1234 get pods
  kubectl auth can-i create deployments -n sandbox-abcd1234   # yes
  ```

## 7. Минимальные привилегии

| Субъект | Где используется | Права |
| --- | --- | --- |
| admin-токен `rancher-init` | Одноразовая настройка | Создание API-токена |
| admin-токен `backend` | Только серверная часть | Создание проектов, namespace, пользователей, привязок ролей |
| пользователь песочницы | kubeconfig у клиента | `project-member` только в своём проекте |
| браузер пользователя | Портал | Никогда не получает токен администратора |

Правила:

- admin-токен и пароль администратора не попадают во фронтенд, логи и ответы
  API;
- пользователь песочницы не получает `cluster-owner`, `cluster-member` или
  доступ к другим namespace;
- `project-member` выдаётся на конкретный проект, а не на кластер;
- после создания песочницы проверяйте `kubectl auth can-i` (см. раздел 6).

⚠️ Открытый вопрос: достаточно ли `project-member` для
`generateKubeconfig`, или Rancher требует ещё и членство в кластере. Если
требует — заведите минимальную кастомную cluster-role и зафиксируйте это в
ADR 0001. Не выдавайте `cluster-member` «на всякий случай», не проверив, что
он не открывает лишнего.

## 8. Подводные камни

1. **Первый старт Rancher долгий.** Ждите `/ping`, `/v3` и готовности кластера
   `local`, иначе создание namespace/пользователя упадёт.
2. **Самоподписанный сертификат.** Все запросы из скриптов — с `-k` или с
   явно добавленным CA.
3. **Пароль администратора и volume.** `CATTLE_BOOTSTRAP_PASSWORD` действует
   только при первичной инициализации. Если пароль сменили в UI, а volume
   потерян/пересоздан, автоматический логин упадёт. Лечение:
   `docker compose down -v`.
4. **Секрет токена показывается один раз.** Не логируйте его; сохраняйте в
   файл с правами `0600`.
5. **`mustChangePassword`.** Пользователь с `true` не сможет использовать
   kubeconfig до смены пароля.
6. **Внутренний endpoint в kubeconfig.** Заменяйте `server` на адрес,
   доступный с хоста.
7. **Формат ID проекта.** Это не просто имя, а `local:p-xxxxx`; используйте
   значение из ответа API.
8. **Namespace требует `projectId`.** Без него namespace не привяжется к
   проекту и RBAC не сработает.
9. **Асинхронность.** После создания ресурсов дождитесь `state: active`.
10. **Удаление.** Удаление проекта не обязано удалять пользователя и привязки;
    в MVP очистка — через `docker compose down -v`.
11. **Уникальность имён.** Повторное имя пользователя/проекта вернёт ошибку.
12. **Версия API.** Проверяйте `/v3` и схему именно своей версии Rancher;
    поля могут отличаться между 2.8/2.9/2.10.
13. **CSRF.** Для API с `Authorization: Bearer` CSRF-токен не нужен; не
    копируйте браузерные заголовки из UI без необходимости.
14. **Логи.** Не печатайте пароли, токены и полный kubeconfig в stdout.

## 9. Чек-лист проверки

- [ ] `GET /ping` отвечает `pong`.
- [ ] `POST /v3-public/localProviders/local?action=login` возвращает токен.
- [ ] `POST /v3/tokens` создаёт долгоживущий токен, файл с ним читается
      бэкендом.
- [ ] Проект создан, `id` вида `local:p-xxxxx`.
- [ ] Namespace создан в проекте и перешёл в `active`.
- [ ] Пользователь создан с `mustChangePassword: false`.
- [ ] Привязка `project-member` создана.
- [ ] `generateKubeconfig` вернул `.config` с пользовательским токеном.
- [ ] `server` в kubeconfig доступен с хоста.
- [ ] `kubectl get namespaces` → `Forbidden`.
- [ ] `kubectl -n sandbox-<id> create deployment web --image=nginx` → успех.
- [ ] Повторный `docker compose up --build` не ломает уже выпущенный токен.

## 10. Открытые вопросы

- Точный эндпоинт создания namespace в выбранной версии Rancher.
- Достаточно ли `project-member` для генерации kubeconfig.
- Можно ли выпустить токен от имени другого пользователя без admin-прав.
- Как корректно перезаписывать `server` в kubeconfig при нестандартном
  `RANCHER_PORT`.
- Нужен ли `CATTLE_SERVER_URL`, чтобы Rancher сразу генерировал публичный
  endpoint.
- Поведение `ttl: 0` и срок жизни токена в kubeconfig.
- Как удалять песочницу целиком (проект → namespace → пользователь → токены).

## 11. Источники

- Rancher API reference: <https://ranchermanager.docs.rancher.com/api/api-reference>
- Исходный код Rancher: <https://github.com/rancher/rancher>
- Локальная схема API: <https://localhost:8443/v3> (после запуска Rancher)
- Rancher в Docker: <https://ranchermanager.docs.rancher.com/getting-started/installation-and-upgrade/other-installation-methods/rancher-on-a-single-node-with-docker>
