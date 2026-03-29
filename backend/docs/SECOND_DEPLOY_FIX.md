# 第二次部署修复 - 竞品账号配置优化

## 问题

17个sec_uid拼接后约1100字符，虽然环境变量限制通常是32KB-256KB（完全够用），但为了管理方便和可靠性，改为**数据库配置**方式。

## 解决方案

已修改代码，竞品账号优先从数据库读取，环境变量作为备选。

## 部署步骤

### 方案A：数据库配置（推荐）

已在 `014_competitor_system.sql` 中预置了17个竞品账号，直接运行迁移即可：

```bash
# 在Railway Console执行
psql $DATABASE_URL -f db/migrations/014_competitor_system.sql
```

这会自动创建：
- competitor_accounts 表
- 17个竞品账号数据
- xiaomin IP记录

### 方案B：环境变量配置（备用）

如果仍想用环境变量，完整值如下（虽然很长但可以填入）：

```bash
TIKHUB_COMPETITOR_SEC_UIDS=MS4wLjABAAAAF55VXn2Qj5pMh0PTyD-IG71GiSLs2U7YtbKtsA-oblA,MS4wLjABAAAATeQUszhzY6JjMfJy1Gya6ao5gGD66Gg1I_9vcJC-y9dfNHKtcXaQ-Mu0K1SPy8EK,MS4wLjABAAAA3XsMOiah1EsT6TSzoqMjlgH4GdMhoBCLwunPVyUP34y-EbUgIV04OU2dnpImMfHq,MS4wLjABAAAAErFzzalv2271brW_cK7vbdLX67B8zOw2ReVYJ72GyoPu2AbZnT3QYNpq4uyxePWr,MS4wLjABAAAAWwcXLQaOlIV4k04tSI4xYaYmCzRZt1a9_IDDutj7Wzra_yNzBUDrPQgV8UVJ_dsH,MS4wLjABAAAAfmygSsGTU3RIctsoi4vcbWkAQaMRi_KwtQh1bP7WCzf1k0yydcLtKQj7kE-FSwsJ,MS4wLjABAAAAHu4SbvaUZQ1GN2WgySRB6G4nmvUvWxD2fNLzvDKOkOAmqxZkQ5fJtx0ZhANSST7V,MS4wLjABAAAAbDuwvhxdzfp009rDpY1mj4NmPu_A_Txsi9SP6Ybz3Bk,MS4wLjABAAAAvrhmrhhYvc4eJvqu_0MStkyBihmGdJZCBl_JVZ0AulE,MS4wLjABAAAAV5oVsV-RjxHKrcCuqQotWtHvT8_Y7z_aQnTvT61slic,MS4wLjABAAAAnTsmfVQNtopff5MrXYMf9y2oVrZ9usIHaCOb_6T1mVo,MS4wLjABAAAA7hiENPfyARPotUS0FootY0s1Qg51l4X3gvkXEKYUHas,MS4wLjABAAAAoGgpFqfuSXAjeMy21Qk8Pn1NvaSukBN7vCipz3xsPOU,MS4wLjABAAAAO_KKPhlqsPDzmTIxBFSFUX5Hjuj8Y94gHQpJgqHlub0,MS4wLjABAAAAZXgVjvDmWo_ipGRJnXwFREdhkG29krGiVSwIQhzIrDA,MS4wLjABAAAAHAlF09yQrLMxW8wyJUO0NGlrsE7O0_9yTki_BkZM16g,MS4wLjABAAAAB1lxLcDT1n51dY3jyB-VQACgN0gbYWGxvSdiE0DWYLY
```

**长度说明**:
- 总长度: 约1100字符
- Railway限制: 32KB-256KB ✓ 完全够用
- 只是看着长，复制粘贴即可

## 推荐的部署顺序

1. **执行 014 迁移** - 创建竞品账号表
2. **执行 015 迁移** - 添加四维字段
3. **同步竞品数据** - 抓取视频

无需设置 `TIKHUB_COMPETITOR_SEC_UIDS` 环境变量！

## 验证数据已存在

```bash
# 检查竞品账号
psql $DATABASE_URL -c "SELECT name, external_id FROM competitor_accounts WHERE ip_id='xiaomin';"

# 预期返回17条记录
```

## 代码更新说明

代码已修改，优先从数据库读取：

```python
# 1. 先查数据库
competitors = await self._get_competitor_accounts_from_db(ip_id)

# 2. 数据库为空，才用环境变量
if not competitors:
    competitors = self._get_competitor_accounts_from_env()
```

这样更可靠，也方便管理（在数据库增删改竞品账号）。
