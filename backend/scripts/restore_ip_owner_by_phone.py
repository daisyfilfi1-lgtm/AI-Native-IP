"""
将指定 ip_id 的 owner_user_id 恢复为某登录账号（按手机号或邮箱在 users 表中解析）。

用于「账号能看到 IP 列表」：创作端 GET /api/v1/ip/mine 只返回 owner_user_id = 当前用户的 IP。

用法（backend 目录、已配置 DATABASE_URL）：

  py -3 scripts/restore_ip_owner_by_phone.py --phone 18600200850

  py -3 scripts/restore_ip_owner_by_phone.py --phone 18600200850 --ip-ids xiaomin1,xiaomin

  py -3 scripts/restore_ip_owner_by_phone.py --email 18600200850@local --ip-ids xiaomin1
"""
from __future__ import annotations

import argparse
import os
import re
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from app.env_loader import load_backend_env  # noqa: E402

load_backend_env()

from sqlalchemy import bindparam, create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


def _sanitize_ip_ids(raw: str) -> list[str]:
    out = []
    for x in raw.split(","):
        s = x.strip()
        if not s:
            continue
        if not re.match(r"^[a-zA-Z0-9_-]+$", s):
            print(f"ERROR: 非法 ip_id: {s!r}")
            sys.exit(1)
        out.append(s)
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="恢复 IP 与登录用户的 owner 绑定")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--phone", help="11 位手机号（与 users.phone 一致）")
    g.add_argument("--email", help="邮箱（与 users.email 一致）")
    p.add_argument(
        "--ip-ids",
        default="xiaomin1,xiaomin",
        help="逗号分隔的 ip.ip_id，默认 xiaomin1,xiaomin",
    )
    args = p.parse_args()

    ip_ids = _sanitize_ip_ids(args.ip_ids)
    if not ip_ids:
        print("ERROR: no ip-ids")
        sys.exit(1)

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
        if args.phone:
            urow = db.execute(
                text("SELECT user_id, phone, email FROM users WHERE phone = :p LIMIT 1"),
                {"p": args.phone.strip()},
            ).fetchone()
        else:
            urow = db.execute(
                text("SELECT user_id, phone, email FROM users WHERE email = :e LIMIT 1"),
                {"e": args.email.strip()},
            ).fetchone()

        if not urow:
            print(
                "ERROR: 未找到用户。请先登录一次（手机验证码或邮箱密码），确保 users 表中有该账号。"
            )
            sys.exit(2)

        uid = urow.user_id
        print("用户:", dict(urow._mapping))

        sel = text(
            "SELECT ip_id, name, owner_user_id, status FROM ip WHERE ip_id IN :ids"
        ).bindparams(bindparam("ids", expanding=True))
        rows_before = db.execute(sel, {"ids": ip_ids}).fetchall()
        print("绑定前:", [dict(r._mapping) for r in rows_before] if rows_before else "(这些 ip_id 在 ip 表中暂无行)")

        upd = text(
            """
            UPDATE ip
            SET owner_user_id = :uid, updated_at = NOW()
            WHERE ip_id IN :ids
            RETURNING ip_id, name, owner_user_id
            """
        ).bindparams(bindparam("ids", expanding=True))

        out = db.execute(upd, {"uid": uid, "ids": ip_ids}).fetchall()
        db.commit()
        if not out:
            print(
                "WARNING: 没有更新任何行。请确认 ip 表中存在这些 ip_id；若 IP 从未创建，需先插入 ip 行再执行本脚本。"
            )
            sys.exit(3)
        print("已更新:")
        for r in out:
            print(" ", dict(r._mapping))
        print("OK")
    finally:
        db.close()


if __name__ == "__main__":
    main()
