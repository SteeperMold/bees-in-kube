# AGENTS.md

Правила архитектуры и соглашения для участников проекта «Портал запроса
Kubernetes-песочниц» (людей и AI-ассистентов).

## Главное правило

Проект должен запускаться на чистой машине **одной командой**:

```bash
docker compose up --build
```

На хосте разрешён только Docker с Compose v2. Не добавляйте шаги, требующие
локальных Python, Node.js, kubectl, Rancher CLI и т. п. Все команды разработки
и тестов выполняются через Docker Compose.

## Архитектурные границы

| Компонент | Ответственность |
| --- | --- |
| `portal` (nginx) | Раздаёт статику фронтенда и проксирует `/api` в backend |
| `backend` | API портала; **единственный** компонент, обращающийся к Rancher API |
| `frontend` | UI: кнопка создания песочницы, показ и скачивание kubeconfig |
| `rancher` | Rancher со встроенным кластером `local` |
| `rancher-init` | Одноразовая настройка Rancher и выпуск API-токена |

Запрещено:

- обращаться к Rancher API из браузера или фронтенда напрямую;
- отдавать admin-токен Rancher, пароль администратора или внутренние секреты
  во фронтенд, ответы API и логи;
- создавать отдельный кластер на каждую песочницу;
- вводить внешнюю БД, очередь или облачные сервисы в рамках MVP.

## Бэкенд

Backend использует src-layout: `backend/src` — корень импортов, файлы
`__init__.py` не нужны (namespace-пакеты, PEP 420). Импорты пишутся без
префикса `src.`:

```python
from api.router import api_router
from infra.settings import Settings
from services.test_service import TestService
```

Слои:

- `api/` — роутеры, Pydantic-схемы, валидация, `HTTPException`. Вызывает
  сервисы.
- `services/` — бизнес-логика, клиент Rancher, доменные модели. **Не импортирует
  FastAPI.**
- `infra/` — настройки (`pydantic-settings`), подключения к внешним системам,
  логирование.
- `main.py` — сборка приложения, `lifespan`, подключение `api_router` под
  `/api/v1`.

Правила:

- бизнес-логика не живёт в хендлерах;
- секреты читаются из файла/volume, а не хардкодятся;
- новые эндпоинты регистрируются в `api/router.py`;
- тесты не должны требовать запущенного Rancher: мокайте HTTP через `respx`.

Примеры `api/test_handler.py` и `services/test_service.py` — учебные. Удалите
их при первом реальном коммите в backend.

## Конфигурация

- Значения по умолчанию должны позволять запуск без `.env`.
- Переопределяемые переменные описываются в `.env.example`.
- Секреты (пароли, токены) не коммитятся; `.env`, `.venv`, кэши и артефакты
  сборки — в `.gitignore`.
- Порт Rancher на хосте — `RANCHER_PORT`; endpoint в kubeconfig должен
  следовать за ним, а не быть жёстко зашитым `8443`.

## Модель песочницы

Песочница = проект Rancher + namespace + отдельный пользователь Rancher +
привязка `project-member` + kubeconfig. Подробнее:
[`docs/decisions/0001-sandbox-model.md`](docs/decisions/0001-sandbox-model.md).

Требования:

- пользователь песочницы не получает cluster-scoped ролей;
- `kubectl get namespaces` для пользователя песочницы — `Forbidden`;
- состояние песочницы хранится в метках Rancher, отдельной БД нет;
- очистка — `docker compose down -v`.

## Тесты и качество

Backend:

```bash
docker compose --profile test run --rm --build backend-tests
```

Frontend:

```bash
docker compose --profile test run --rm --build frontend-tests
```

E2E:

```bash
docker compose --profile test run --rm --build \
  -e E2E_PORTAL_URL=http://portal backend-tests pytest tests/e2e
```

Требования:

- backend: `ruff check` и `pytest` проходят;
- frontend: `eslint`, `prettier`, `tsc`, `vitest` проходят;
- e2e smoke создаёт песочницу и проверяет kubeconfig на запущенном стеке;
- новые функции сопровождаются тестами;
- секреты и токены не попадают в снапшоты/логи тестов.

## Документация

Обновляйте документацию вместе с кодом:

- `README.md` — запуск, адреса, архитектура, troubleshooting;
- `docs/rancher-api.md` — фактические вызовы API, ответы, подводные камни;
- ADR в `docs/decisions/` — значимые архитектурные решения;
- `docs/case.md` — рамки учебного кейса.

Непроверенные утверждения помечайте ⚠️. Не выдавайте предположения за
проверенные факты.

## Стиль кода

- Python 3.12+, типизация по возможности, `ruff` как линтер и форматтер.
- Имена переменных/функций/классов — на английском; документация и
  комментарии — на русском.
- Не оставляйте мёртвый код и закомментированные блоки.
- Не логируйте пароли, токены и полные kubeconfig.

## Git

- Атомарные коммиты с понятным сообщением (Conventional Commits):
  `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`, `refactor: ...`,
  `chore: ...`.
- В одном коммите — одна логическая единица работы.
- Перед коммитом: тесты, линтер, отсутствие секретов в diff.

## Definition of Done

- [ ] `docker compose up --build` работает на чистой машине/пустом volume.
- [ ] Портал создаёт песочницу и отдаёт kubeconfig.
- [ ] `kubectl` работает в namespace песочницы и получает `Forbidden` на чужие
      namespace.
- [ ] `docker compose down -v` очищает состояние.
- [ ] Тесты и линтеры проходят.
- [ ] Документация обновлена.
