"""
临时修复脚本：将竞品账号从 xiaomin 迁移到 xiaomin1
"""
from fastapi import APIRouter, Depends, HTTPException
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

router = APIRouter()

@router.post("/admin/fix-competitor-ip")
async def fix_competitor_ip(db: AsyncSession = Depends(get_db)):
    """
    将竞品账号从 xiaomin 迁移到 xiaomin1
    """
    try:
        # 首先确保 xiaomin1 IP 存在
        await db.execute(text("""
            INSERT INTO ip (ip_id, name, owner_user_id, status, created_at, updated_at)
            VALUES ('xiaomin1', '馒头女子', 'system', 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (ip_id) DO NOTHING
        """))
        
        # 获取迁移前的统计
        result_before = await db.execute(text("""
            SELECT ip_id, COUNT(*) as count 
            FROM competitor_accounts 
            GROUP BY ip_id
        """))
        before_stats = result_before.fetchall()
        
        # 执行迁移
        result = await db.execute(text("""
            UPDATE competitor_accounts 
            SET ip_id = 'xiaomin1' 
            WHERE ip_id = 'xiaomin'
            RETURNING competitor_id, name
        """))
        migrated = result.fetchall()
        
        await db.commit()
        
        # 获取迁移后的统计
        result_after = await db.execute(text("""
            SELECT ip_id, COUNT(*) as count 
            FROM competitor_accounts 
            GROUP BY ip_id
        """))
        after_stats = result_after.fetchall()
        
        return {
            "success": True,
            "message": f"成功迁移 {len(migrated)} 个竞品账号",
            "migrated_competitors": [
                {"id": row.competitor_id, "name": row.name} 
                for row in migrated
            ],
            "stats_before": [
                {"ip_id": row.ip_id, "count": row.count} 
                for row in before_stats
            ],
            "stats_after": [
                {"ip_id": row.ip_id, "count": row.count} 
                for row in after_stats
            ]
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
