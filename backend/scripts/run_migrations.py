"""
在云平台首次部署或更新表结构时执行：读取 DATABASE_URL，按顺序执行 migrations 下的 SQL。
用法（在 backend 目录下）：python scripts/run_migrations.py
或：railway run python scripts/run_migrations.py / render 的 release 命令
"""
import os
import sys

# 保证 backend 为工作目录，便于 import app
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

import psycopg2

MIGRATIONS_DIR = os.path.join(backend_dir, "db", "migrations")
ORDER = ["001_init.sql", "002_ingest_tasks.sql"]


def _run_sql_script(cur, content: str) -> None:
    """执行多条 SQL（按分号拆分，忽略空行与纯注释）。"""
    for raw in content.split(";"):
        stmt = raw.strip()
        if not stmt or stmt.startswith("--"):
            continue
        cur.execute(stmt)


def run_migrations():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        for name in ORDER:
            path = os.path.join(MIGRATIONS_DIR, name)
            if not os.path.isfile(path):
                print(f"Skip (not found): {name}")
                continue
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            print(f"Running {name}...")
            _run_sql_script(cur, content)
            print(f"Done {name}")
    finally:
        cur.close()
        conn.close()
    print("All migrations completed.")


if __name__ == "__main__":
    run_migrations()
