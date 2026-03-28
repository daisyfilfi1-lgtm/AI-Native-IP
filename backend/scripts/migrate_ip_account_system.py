"""
数据库迁移脚本：为IP表添加账号体系字段

运行方式:
    cd backend
    python -m scripts.migrate_ip_account_system
"""

import os
import sys
import sqlite3

# 添加backend目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_db_path():
    """获取SQLite数据库文件路径"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'app.db')


def migrate():
    """执行迁移"""
    db_path = get_db_path()
    print(f"Using SQLite database: {db_path}")
    
    # 如果数据库文件不存在，会创建它
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查IP表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ip'")
        if not cursor.fetchone():
            print("Creating IP table...")
            cursor.execute('''
                CREATE TABLE ip (
                    ip_id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    owner_user_id VARCHAR(64) NOT NULL,
                    status VARCHAR(32) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            print("IP table created.")
        else:
            print("IP table exists.")
        
        # 需要添加的字段
        columns_to_add = [
            # 账号体系：超级符号识别系统（7个标准化触点）
            ("avatar_url", "VARCHAR(2048)"),
            ("nickname", "VARCHAR(100)"),
            ("bio", "VARCHAR(500)"),
            ("cover_image_url", "VARCHAR(2048)"),
            ("cover_template", "VARCHAR(100)"),
            ("pinned_content", "VARCHAR(500)"),
            ("like_follower_ratio", "VARCHAR(20)"),
            
            # 商业定位：变现前置原则
            ("monetization_model", "VARCHAR(50)"),
            ("target_audience", "VARCHAR(255)"),
            ("content_direction", "VARCHAR(255)"),
            ("unique_value_prop", "VARCHAR(500)"),
            
            # 定位交叉点：擅长 × 热爱 × 市场需求
            ("expertise", "VARCHAR(255)"),
            ("passion", "VARCHAR(255)"),
            ("market_demand", "VARCHAR(255)"),
            
            # 变现象限：产品/服务 × 客单价 × 复购率
            ("product_service", "VARCHAR(255)"),
            ("price_range", "VARCHAR(100)"),
            ("repurchase_rate", "VARCHAR(50)"),
        ]
        
        # 获取现有字段
        cursor.execute("PRAGMA table_info(ip)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        print(f"Existing columns: {len(existing_columns)}")
        
        # 添加新字段
        for column_name, column_type in columns_to_add:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE ip ADD COLUMN {column_name} {column_type}")
                    print(f"[ADDED] Column: {column_name}")
                except Exception as e:
                    print(f"[ERROR] Column {column_name}: {e}")
                    raise
            else:
                print(f"[EXISTS] Column: {column_name}")
        
        conn.commit()
        print("\n[SUCCESS] Migration completed!")
        print(f"Database file: {db_path}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n[FAILED] Migration: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
