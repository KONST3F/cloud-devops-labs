# Заметки

Сервис для лабораторных по DevOps: страница отправляет заметки на Python-сервер, который сохраняет их в PostgreSQL.

[Лабораторная 0](Лабораторная_0.md) · [Лабораторная 1](Лабораторная_1.md) · [Лабораторная 2](Лабораторная_2.md)

## Лабораторная 0

Нужны Python 3, Docker и OpenSSL. В PowerShell из папки проекта:

```powershell
python -m pip install -r requirements.txt
./setup-local.ps1
$dbPassword = ((Get-Content .env | Where-Object { $_ -match '^DB_PASSWORD=' }) -split '=', 2)[1]
docker run -d --name notes-lab0-db `
  -e POSTGRES_USER=labuser -e "POSTGRES_PASSWORD=$dbPassword" -e POSTGRES_DB=notes `
  -p 127.0.0.1:15433:5432 -v notes_lab0_data:/var/lib/postgresql/data postgres:15
$env:DATABASE_URL="postgresql://labuser:${dbPassword}@127.0.0.1:15433/notes"
python app.py
```

Открыть `http://127.0.0.1:18081`, добавить заметку и обновить страницу. Если контейнер уже создан, использовать `docker start notes-lab0-db` вместо `docker run`.

## Лабораторные 1 и 2

Нужны Docker Compose, Python 3 и OpenSSL. Для `check.sh` нужен Git Bash. Из папки проекта:

```powershell
$env:COMPOSE_PROJECT_NAME='devops-final'
./setup-local.ps1
docker compose up -d --build
docker build -f Dockerfile.bad -t devops-final:bad .
& 'C:\Program Files\Git\bin\bash.exe' check.sh
python tools/check_sections.py
python tools/benchmark.py
```

Скрипт создаёт `.env`, самоподписанный сертификат и файлы авторизации. Логин админки `student`, пароль находится в локальном `.env` в поле `ADMIN_PASSWORD`. При повторном запуске существующие пароли и сертификат сохраняются; файл авторизации пересоздаётся. `.env`, `auth/` и `certs/` исключены из Git. Самоподписанный сертификат используется только для локальной проверки.

Nginx слушает `127.0.0.1:80` и `127.0.0.1:443`. Для тестов используется `curl --resolve`, поэтому менять hosts не требуется. Если порты заняты, сначала освободите их.

Проверка nginx ненадолго останавливает `backend-a`. Проверка тома добавляет запись и пересоздаёт контейнер базы без удаления тома. Замер сборки выполняется в отдельной копии исходников. Чтобы остановить сервис:

```powershell
docker compose stop
```
