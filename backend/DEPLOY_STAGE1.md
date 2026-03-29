# Stage 1 部署指南 - Railway

## 变更摘要

本次更新包含竞品监控系统的完整实现：
- 多源热榜聚合（抖音/小红书/快手/B站）
- 内置爆款库兜底（60+模板）
- 智能IP匹配（四维评分）
- 竞品数据同步服务

## 部署前准备

### 1. 确认环境变量

在 Railway Dashboard → Variables 中设置：

```bash
# TIKHub API（必须）
TIKHUB_API_KEY=k6ANCMEu1nWQhW2vRIel/y3ucxi0XoQyzwuJhE/ZBvWr1W+4FmaNU2KDKw==

# 竞品账号列表（必须）- 17个竞品账号sec_uid
TIKHUB_COMPETITOR_SEC_UIDS=MS4wLjABAAAAF55VXn2Qj5pMh0PTyD-IG71GiSLs2U7YtbKtsA-oblA,MS4wLjABAAAATeQUszhzY6JjMfJy1Gya6ao5gGD66Gg1I_9vcJC-y9dfNHKtcXaQ-Mu0K1SPy8EK,MS4wLjABAAAA3XsMOiah1EsT6TSzoqMjlgH4GdMhoBCLwunPVyUP34y-EbUgIV04OU2dnpImMfHq,MS4wLjABAAAAErFzzalv2271brW_cK7vbdLX67B8zOw2ReVYJ72GyoPu2AbZnT3QYNpq4uyxePWr,MS4wLjABAAAAWwcXLQaOlIV4k04tSI4xYaYmCzRZt1a9_IDDutj7Wzra_yNzBUDrPQgV8UVJ_dsH,MS4wLjABAAAAfmygSsGTU3RIctsoi4vcbWkAQaMRi_KwtQh1bP7WCzf1k0yydcLtKQj7kE-FSwsJ,MS4wLjABAAAAHu4SbvaUZQ1GN2WgySRB6G4nmvUvWxD2fNLzvDKOkOAmqxZkQ5fJtx0ZhANSST7V,MS4wLjABAAAAbDuwvhxdzfp009rDpY1mj4NmPu_A_Txsi9SP6Ybz3Bk,MS4wLjABAAAAvrhmrhhYvc4eJvqu_0MStkyBihmGdJZCBl_JVZ0AulE,MS4wLjABAAAAV5oVsV-RjxHKrcCuqQotWtHvT8_Y7z_aQnTvT61slic,MS4wLjABAAAAnTsmfVQNtopff5MrXYMf9y2oVrZ9usIHaCOb_6T1mVo,MS4wLjABAAAA7hiENPfyARPotUS0FootY0s1Qg51l4X3gvkXEKYUHas,MS4wLjABAAAAoGgpFqfuSXAjeMy21Qk8Pn1NvaSukBN7vCipz3xsPOU,MS4wLjABAAAAO_KKPhlqsPDzmTIxBFSFUX5Hjuj8Y94gHQpJgqHlub0,MS4wLjABAAAAZXgVjvDmWo_ipGRJnXwFREdhkG29krGiVSwIQhzIrDA,MS4wLjABAAAAHAlF09yQrLMxW8wyJUO0NGlrsE7O0_9yTki_BkZM16g,MS4wLjABAAAAB1lxLcDT1n51dY3jyB-VQACgN0gbYWGxvSdiE0DWYLY

# 数据库（应该已有）
DATABASE_URL=${{Postgres.DATABASE_URL}}

# AI服务（应该已有）
OPENAI_API_KEY=your_key
OPENAI_BASE_URL=https://api.deepseek.com
```

## 部署步骤

### 步骤1：提交代码到Git

```bash
# 在 backend 目录下
cd backend

# 添加所有新文件
git add app/services/competitor_sync_service.py
.git add app/services/competitor_monitor_service.py
.git add app/services/real_competitor_service.py
.git add app/services/smart_ip_matcher.py
.git add app/services/datasource/multi_source_hotlist.py
.git add app/services/datasource/builtin_viral_repository.py
.git add app/services/datasource/__init__.py
.git add app/routers/topic_recommendation_v4.py
.git add app/services/topic_recommendation_v4.py
.git add db/migrations/015_competitor_four_dim.sql
.git add scripts/sync_competitors_to_db.py

# 提交
git commit -m "feat: Stage 1 - 竞品监控系统

- 多源热榜聚合（抖音/小红书/快手/B站）
- 内置爆款库兜底（60+模板）
- 智能IP匹配（四维评分：相关度/热度/竞争度/转化率）
- 竞品数据同步服务（17个账号）
- 按4-3-2-1内容矩阵排序

新增API:
- GET /strategy/v4/competitor-videos (按四维排序)
- POST /strategy/v4/sync-competitors (手动同步)
"

# 推送
git push origin main
```

### 步骤2：Railway自动部署

代码推送后，Railway会自动：
1. 检测代码变更
2. 构建Docker镜像
3. 部署新版本

在 Railway Dashboard 查看部署状态：
- 绿色 = 部署成功
- 红色 = 部署失败（查看Logs）

### 步骤3：执行数据库迁移

部署成功后，在Railway Console执行：

```bash
# 进入Railway Console（右上角按钮）
# 执行迁移
psql $DATABASE_URL -f db/migrations/015_competitor_four_dim.sql
```

或：

```bash
# 使用Python执行
python -c "
from app.db.session import engine
from app.db.models import Base
# 自动创建缺失的表/字段
Base.metadata.create_all(bind=engine)
print('Migration done')
"
```

### 步骤4：同步竞品数据

在Railway Console执行一次性同步：

```bash
cd backend
python scripts/sync_competitors_to_db.py --ip_id xiaomin --limit 10
```

预期输出：
```
✓ 淘淘子: 5/5 synced
✓ 顶妈私房早餐: 5/5 synced
...
Total synced: 84 videos
```

### 步骤5：验证API

测试新API是否正常工作：

```bash
# 测试四维排序API
curl "https://your-app.railway.app/strategy/v4/competitor-videos?ip_id=xiaomin&limit=5&use_matrix=true" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 预期返回：按四维排序的竞品视频列表
```

## 验证清单

部署完成后，检查以下功能：

- [ ] 环境变量 TIKHUB_API_KEY 已设置
- [ ] 环境变量 TIKHUB_COMPETITOR_SEC_UIDS 已设置
- [ ] 数据库迁移成功（四维字段已添加）
- [ ] 竞品数据已同步（competitor_videos表有数据）
- [ ] API /strategy/v4/competitor-videos 正常返回
- [ ] 原有API /strategy/v4/topics/recommend 仍正常工作

## 回滚方案

如果部署失败：

```bash
# 在Railway Dashboard中
# 1. 点击 "Deployments"
# 2. 找到上一个成功的部署
# 3. 点击 "Rollback"

# 或手动回滚代码
git revert HEAD
git push origin main
```

## 监控

部署后关注以下指标：

1. **API响应时间** - 四维排序查询应 < 500ms
2. **TIKHub API调用** - 监控用量和错误率
3. **数据库连接** - 确保连接池正常

## 下一步

部署成功后，继续**环节2**：爆款链接 → 提取标题
