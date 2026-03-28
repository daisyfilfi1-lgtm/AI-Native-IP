"""
上传功能诊断脚本
用于排查文件上传内存问题

使用方法：
    cd backend
    python scripts/diagnose_upload.py

需要环境变量：
    DATABASE_URL - 数据库连接字符串
    STORAGE_LOCAL_PATH - 本地存储路径（如使用本地存储）
"""
import os
import sys
import tempfile
import time
import psutil

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.env_loader import load_backend_env
load_backend_env()

def print_memory_usage(label: str = ""):
    """打印当前内存使用情况"""
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / 1024 / 1024
    print(f"[内存] {label}: {mem_mb:.1f}MB")
    return mem_mb

def test_upload_simulation():
    """模拟文件上传过程，检查内存使用"""
    print("=" * 60)
    print("文件上传内存诊断")
    print("=" * 60)
    
    # 初始内存
    mem_start = print_memory_usage("初始状态")
    
    # 创建测试文件（11KB，模拟用户的情况）
    test_size = 11 * 1024  # 11KB
    test_data = b"x" * test_size
    print(f"\n[测试] 创建测试数据: {test_size / 1024:.1f}KB")
    
    mem_after_create = print_memory_usage("创建测试数据后")
    
    # 模拟分块读取
    chunk_size = 64 * 1024
    chunks = []
    total = 0
    
    print(f"\n[测试] 模拟分块读取 (chunk_size={chunk_size / 1024}KB)")
    for i in range(0, len(test_data), chunk_size):
        chunk = test_data[i:i + chunk_size]
        chunks.append(chunk)
        total += len(chunk)
    
    print(f"       总块数: {len(chunks)}, 总大小: {total / 1024:.1f}KB")
    mem_after_chunks = print_memory_usage("分块读取后")
    
    # 合并数据
    merged = b"".join(chunks)
    print(f"\n[测试] 合并数据: {len(merged) / 1024:.1f}KB")
    mem_after_merge = print_memory_usage("合并数据后")
    
    # 清理
    del test_data
    del chunks
    del merged
    
    print_memory_usage("清理后")
    
    # 分析
    print("\n" + "=" * 60)
    print("诊断结果")
    print("=" * 60)
    
    delta_create = mem_after_create - mem_start
    delta_chunks = mem_after_chunks - mem_after_create
    delta_merge = mem_after_merge - mem_after_chunks
    
    print(f"创建测试数据内存增长: {delta_create:+.1f}MB")
    print(f"分块读取内存增长: {delta_chunks:+.1f}MB")
    print(f"合并数据内存增长: {delta_merge:+.1f}MB")
    
    if delta_merge > 10:  # 超过 10MB 算异常
        print("\n⚠️ 警告: 内存增长异常，可能存在内存泄漏！")
        return False
    else:
        print("\n✅ 内存使用正常")
        return True

def test_dependencies():
    """测试关键依赖是否正确安装"""
    print("\n" + "=" * 60)
    print("依赖检查")
    print("=" * 60)
    
    checks = []
    
    # 检查 psutil
    try:
        import psutil
        print("✅ psutil 已安装")
        checks.append(True)
    except ImportError:
        print("❌ psutil 未安装，运行: pip install psutil")
        checks.append(False)
    
    # 检查 FastAPI
    try:
        import fastapi
        print(f"✅ FastAPI 已安装 (版本: {fastapi.__version__})")
        checks.append(True)
    except ImportError:
        print("❌ FastAPI 未安装")
        checks.append(False)
    
    # 检查 SQLAlchemy
    try:
        import sqlalchemy
        print(f"✅ SQLAlchemy 已安装 (版本: {sqlalchemy.__version__})")
        checks.append(True)
    except ImportError:
        print("❌ SQLAlchemy 未安装")
        checks.append(False)
    
    # 检查 python-multipart
    try:
        import multipart
        print("✅ python-multipart 已安装")
        checks.append(True)
    except ImportError:
        print("❌ python-multipart 未安装")
        checks.append(False)
    
    return all(checks)

def test_database():
    """测试数据库连接"""
    print("\n" + "=" * 60)
    print("数据库连接检查")
    print("=" * 60)
    
    try:
        from sqlalchemy import create_engine, text
        
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url:
            print("❌ DATABASE_URL 未设置")
            return False
        
        # 处理 postgres:// -> postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        print(f"数据库 URL: {database_url[:30]}...")
        
        engine = create_engine(database_url, connect_args={"connect_timeout": 10})
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ 数据库连接成功")
            return True
            
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def test_storage():
    """测试存储配置"""
    print("\n" + "=" * 60)
    print("存储配置检查")
    print("=" * 60)
    
    from app.config.storage_config import get_storage_config
    
    cfg = get_storage_config()
    
    if cfg.get("s3_enabled"):
        print("✅ S3 存储已配置")
        print(f"   Bucket: {cfg.get('bucket', '未设置')}")
        print(f"   Endpoint: {cfg.get('endpoint', '未设置')}")
    elif not cfg.get("local_disabled"):
        print("✅ 本地存储已启用")
        print(f"   存储路径: {cfg.get('local_path', '未设置')}")
        
        # 检查路径是否可写
        local_path = cfg.get("local_path")
        if local_path:
            try:
                os.makedirs(local_path, exist_ok=True)
                test_file = os.path.join(local_path, ".write_test")
                with open(test_file, "w") as f:
                    f.write("test")
                os.remove(test_file)
                print("   路径可写: ✅")
            except Exception as e:
                print(f"   路径不可写: ❌ {e}")
    else:
        print("❌ 存储未配置（S3 和本地存储都不可用）")
        return False
    
    return True

def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("AI-Native IP 工厂 - 文件上传诊断工具")
    print("=" * 60)
    
    results = []
    
    # 1. 检查依赖
    results.append(("依赖检查", test_dependencies()))
    
    # 2. 检查数据库
    results.append(("数据库连接", test_database()))
    
    # 3. 检查存储
    results.append(("存储配置", test_storage()))
    
    # 4. 模拟上传
    results.append(("内存模拟测试", test_upload_simulation()))
    
    # 总结
    print("\n" + "=" * 60)
    print("诊断总结")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n✅ 所有检查通过！上传功能应该正常工作。")
        print("\n如果仍然遇到内存问题，请检查：")
        print("1. Railway 容器内存限制")
        print("2. Netlify 是否正确配置直连")
        print("3. 浏览器开发者工具中的请求 URL")
    else:
        print("\n❌ 部分检查失败，请根据上方提示修复问题。")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
