"""
将指定 IP（按名称）的 owner_user_id 绑定到某手机号对应用户。

用法（在 backend 目录下，已配置 DATABASE_URL）：
  python scripts/link_ip_owner_by_phone.py --phone 18600200850 --name "馒头女子"

前提：该手机号已至少登录过一次（users 表中有记录）。
"""
import argparse
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from app.env_loader import load_backend_env  # noqa: E402

load_backend_env()

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--phone", required=True, help="11 位手机号")
    p.add_argument("--name", required=True, help="IP 名称（与 ip.name 一致）")
    args = p.parse_args()

    url = os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(url)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        row = db.execute(
            text(
                """
                UPDATE ip AS i
                SET owner_user_id = u.user_id, updated_at = NOW()
                FROM users AS u
                WHERE u.phone = :phone AND i.name = :name
                RETURNING i.ip_id, i.name, i.owner_user_id
                """
            ),
            {"phone": args.phone.strip(), "name": args.name.strip()},
        ).fetchone()
        db.commit()
        if not row:
            print(
                "No row updated. Check: users has phone, ip.name matches exactly, migration 011 applied."
            )
            sys.exit(2)
        print("OK:", dict(row._mapping))
    finally:
        db.close()


if __name__ == "__main__":
    main()
