# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

This project is an **AI-powered natural language query service for real estate recommendations and transaction price analysis**, built on a Django template.

The project is currently in the early stages of development, with a basic Django setup and includes web scraping capabilities using Playwright for Naver real estate data.

---

## Core Technology Stack

-   **Frontend:** [Framework/Library (e.g., Bootstrap 5, JavaScript)]
-   **Backend:** [Framework/Language (e.g., Django)]
-   **Database:** [Database Type (e.g., MySQL, Redis)]
-   **Key Libraries:** [List of frequently used libraries (e.g., Django, pytest, django-redis, mysqlclient, Playwright)]

---

## Project Structure

-   `config/`: Main Django project configuration directory.
    -   `user/`: Contains features for user registration, login, logout, withdrawal, and profile updates.
    -   `home/`: Implements the main landing page for users after logging in.
    -   `board/`: Implements features for displaying the results of the search functionality provided on the home page.
    -   `utils/`: Common utility functions and modules used across the project.
    -   `api/`: Logic related to API requests and endpoints.
-   `docs/`: Directory for storing documentation.
-   `static/`: Directory for static files (CSS, JavaScript, images).
-   `media/`: Directory for user-uploaded files and server-generated media.
-   `templates/`: HTML 템플릿을 위한 디렉토리입니다. 이 프로젝트는 **root 레벨의 단일 `templates` 디렉토리만 사용합니다.**
    -   각 앱에서 사용되는 템플릿은 `templates` 디렉토리 내부에 **해당 앱의 이름으로 된 하위 폴더**에 저장해야 합니다. (예: `templates/user/login.html`)
    -   **앱별 `templates` 디렉토리(예: `user/templates/`)는 사용하지 않습니다.**
-   `pre-test/`: Contains experimental scraping scripts.
    -   `gemini-naver.py`: Playwright-based scraper for Naver real estate data.
-   `manage.py`: Standard Django management script.
-   `pyproject.toml`: Project dependencies managed by `uv`.
-   `uv.lock`: Locked dependency versions.


## Core Workflow & Rules

**Important: Before starting any task, you must read and adhere to the rules below.**

1.  **Record Detailed Work in `TASKING.md`**:
    -   After completing a requested task, you **must record** the list of modified files and a summary of the work in the `TASKING.md` file that exists in each app.
    -   Record only successful tasks; there is no need to record failed tasks. Updates and changes should also be recorded only for successful work.

2.  **Check Work History in `HISTORY.md`**:
    -   Before starting a task, read the `HISTORY.md` file in each app to understand what has been previously completed and avoid duplicate work.
    -   Review the checkable task lists and update the checks if the work has been completed.

3.  **Ignore Archival Document (`TASKING_KR.md`)**:
    -   The `TASKING_KR.md` file located in each app is for archival purposes only. As it is not related to current tasks, **you must completely ignore it and not reference or modify its content.**

## Development Commands

### Environment Setup

-   **Install dependencies from file**: `uv sync` (Uses `uv` for dependency management)
-   **Add a new dependency**: `uv add [package-name]`
-   **Activate virtual environment**: Activate the `.venv` directory or prefix commands with `uv run`.

### Django Commands

-   **Run development server**: `uv run python manage.py runserver`
-   **Database migrations**: `uv run python manage.py migrate`
-   **Create migrations**: `uv run python manage.py makemigrations`
-   **Create superuser**: `uv run python manage.py createsuperuser`
-   **Django shell**: `uv run python manage.py shell_plus` (Uses `django-extensions`)

### Testing

-   **Run tests**: `pytest`

    Tests are automatically discovered and executed based on the configuration in the `pyproject.toml` file. `pytest` finds tests based on file patterns like `test_*.py`, `*_test.py`, and function names starting with `test_`.

-   **Key Configurations:**
    -   **Parallel Execution**: Tests run in parallel, adjusted to the number of CPU cores, to increase speed (`-n=auto`).
    -   **DB Optimization**: The test database is reused (`--reuse-db`) and migrations are skipped (`--nomigrations`) to reduce execution time.
    -   **Code Coverage**: Test coverage is automatically calculated with a target of 85%. An HTML report is generated in the `htmlcov` directory.
    -   **Custom Markers**: Use various markers like `models`, `views`, and `api` to selectively run specific types of tests (e.g., `pytest -m models`). Refer to `pyproject.toml` for the full list of markers.

---

## Coding Style Guide

-   **Language:** [Languages and versions (e.g., Python, HTML, JavaScript, CSS)]
-   **Formatting:** Use a code formatter (e.g., **Ruff**).
-   **Naming Convention:**
    -   **Classes (Models, Views, etc.)**: `PascalCase` (e.g., `UserProfile`, `ProductListView`)
    -   **Variables / Functions / Methods**: `snake_case` (e.g., `user_list`, `get_total_price`)
    -   **Project / App**: `snake_case` (e.g., `my_project`, `blog_api`)
    -   **URL Names**: `snake_case` (e.g., `post_detail`)
    -   **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_LOGIN_ATTEMPTS`)
-   **Comments:** Always add comments to complex logic or important sections. Every class must have a docstring at the top explaining its purpose and behavior.

---

## Key Dependencies

-   **Django** 5.2.6+ (Web framework)
-   **Playwright** 1.55.0+ (Web scraping and automation)
-   **django-extensions** (Enhanced Django shell and utilities)
-   **JupyterLab** (Data analysis and prototyping)
-   **IPython** (Interactive Python shell)
-   **pytest** (Testing framework)

---

## Database

This project uses **MySQL** as its primary database and **Redis** for caching and other purposes. SQLite3 is not used.

### MySQL Configuration

- **Database Name**: `ai_test_prj`
- **Username**: `ai_admin`
- **Password**: `test1324`
- **Host**: `localhost` (local development server)
- **Charset**: `utf8mb4`
- **Collation**: `utf8mb4_unicode_ci`

### MySQL Database Setup

If the database and user account don't exist, create them using the following SQL commands:

```sql
-- 1. 데이터베이스 생성
CREATE DATABASE ai_test_prj CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 2. 사용자 생성 (모든 호스트에서 접속 가능)
CREATE USER 'ai_admin'@'%' IDENTIFIED BY 'test1324';

-- 3. 데이터베이스에 모든 권한 부여
GRANT ALL PRIVILEGES ON ai_test_prj.* TO 'ai_admin'@'%';

-- 4. 권한 적용 (선택사항 - GRANT 명령 사용 시 자동으로 적용됨)
FLUSH PRIVILEGES;
```

---

## External API Configuration

### ChatGPT API Integration

- **API Provider**: OpenAI ChatGPT API
- **Configuration**: Environment variables loaded via `.env` file
- **Settings Integration**: API keys loaded in `config/settings.py`
- **Testing**: Dummy testing implemented for development without actual API calls

### Environment Variables Setup

Create a `.env` file in the project root with the following structure:

```env
# ChatGPT API Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# Database Configuration (optional - can use settings.py defaults)
DB_NAME=ai_test_prj
DB_USER=ai_admin
DB_PASSWORD=test1324
DB_HOST=localhost
DB_PORT=3306
```

---

## Important Notes

-   **Response Language: Please generate all responses in Korean.**
-   This project uses `uv` instead of `pip` for dependency management.
-   `django-extensions` provides an enhanced shell (`shell_plus`) and other useful utilities.