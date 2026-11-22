# Карточка кейса: портал запроса Kubernetes-песочниц

## Кратко

| Параметр | Значение |
| --- | --- |
| Формат | Учебный продуктовый проект «учимся, создавая» |
| Команда | 2–4 человека |
| Длительность | ~6 недель |
| Среда выполнения | Только Docker + Docker Compose v2 |
| Ключевой инструмент | Rancher в Docker (встроенный кластер `local`) |
| Результат | Работающий портал, который выдаёт Kubernetes-песочницу и kubeconfig |

## Проблема

Разработчику нужно быстро получить изолированное Kubernetes-окружение, чтобы
запустить и проверить приложение, не поднимая собственный кластер и не ожидая
ресурсов от инфраструктурной команды.

Нужен самообслуживаемый портал: одно нажатие — и у пользователя есть namespace,
endpoint, токен и kubeconfig.

## Цель

Сделать работающий MVP портала, который через Rancher API:

1. создаёт песочницу;
2. выдаёт пользователю данные для подключения;
3. ограничивает доступ только этой песочницей;
4. поднимается на чистой машине одной командой `docker compose up --build`.

## Ограничения

- На хосте есть **только Docker** с Compose v2: нет локальных Python, Node.js,
  kubectl и т. п.
- Нельзя использовать внешние кластеры и облачные ресурсы.
- Rancher работает в привилегированном контейнере; нужно 6–8 ГБ ОЗУ.
- После запуска не должно быть ручных шагов: настройка Rancher и выпуск
  API-токена автоматизированы.
- Очистка — `docker compose down -v`.

## Что нужно исследовать самостоятельно

- Как Rancher в Docker хранит состояние и как проходит первичная настройка.
- Как аутентифицироваться в Rancher API и выпустить долгоживущий токен.
- Как создать проект, namespace и пользователя через API.
- Какую роль выдать пользователю, чтобы он мог работать только в своём
  namespace.
- Как сгенерировать kubeconfig и какой endpoint в нём окажется.
- Как ведёт себя самоподписанный TLS-сертификат.
- Какие вызовы нужно замокать в тестах.

Рекомендуемые инструменты: документация Rancher, исходный код на GitHub,
Postman/curl на локальном Rancher, `kubectl` на хосте для проверки выданного
kubeconfig.

## Deliverables

1. **Код**
   - `docker-compose.yaml` со всеми сервисами, healthcheck'ами и профилем
     `test`;
   - `backend/` — API портала и клиент Rancher;
   - `frontend/` + `portal/` — страница с кнопкой **Create sandbox**;
   - `rancher-init/` — автоматическая настройка Rancher и выпуск токена.
2. **API**
   - `POST /api/sandboxes` — создать песочницу;
   - ответ с `id`, `namespace`, `status`, `endpoint`, `token`, `kubeconfig`,
     `created_at`.
3. **Документация**
   - обновлённый `README.md`;
   - `docs/rancher-api.md` с фактическими вызовами и ответами;
   - ADR по модели песочницы и по bootstrap/TLS;
   - инструкция запуска и troubleshooting.
4. **Тесты**
   - backend: ruff + pytest, Rancher замокан через `respx`;
   - frontend: eslint + prettier + tsc + vitest;
   - e2e smoke: создать песочницу и проверить kubeconfig.

## Definition of Done

- [ ] `git clone` → `docker compose up --build` на чистой машине поднимает
      портал без ручных шагов.
- [ ] Портал открывается на `http://localhost:8080`.
- [ ] Кнопка **Create sandbox** создаёт песочницу.
- [ ] Пользователь получает endpoint, токен и kubeconfig.
- [ ] `kubectl` с выданным kubeconfig создаёт deployment в своём namespace.
- [ ] `kubectl get namespaces` возвращает `Forbidden`.
- [ ] `docker compose down -v` возвращает окружение к чистому состоянию.
- [ ] `docker compose --profile test run --rm --build backend-tests` проходит.
- [ ] `docker compose --profile test run --rm --build frontend-tests` проходит.
- [ ] Документация описывает реальные вызовы, решения и ограничения.

## Вне рамок

- аутентификация пользователей портала;
- сложный UI;
- БД и очередь;
- TTL, квоты, удаление песочниц;
- production-уровень безопасности и HA Rancher.

## Использование AI

AI-инструменты разрешены для кода, тестов и документации. Ответственность за
понимание и работоспособность результата остаётся на команде: на защите нужно
объяснить, какие вызовы Rancher используются и почему.

## Демо-сценарий

1. `docker compose down -v` — чистое состояние.
2. `docker compose up --build -d --wait` — поднять стек.
3. Открыть портал, нажать **Create sandbox**.
4. Скачать kubeconfig, выполнить:

   ```bash
   export KUBECONFIG=./sandbox-<id>.kubeconfig.yaml
   kubectl -n sandbox-<id> create deployment web --image=nginx
   kubectl -n sandbox-<id> get pods
   kubectl get namespaces          # Forbidden
   ```

5. Показать логи `rancher-init`, ответ API и тесты.
6. Рассказать про ограничения модели и следующие шаги.
