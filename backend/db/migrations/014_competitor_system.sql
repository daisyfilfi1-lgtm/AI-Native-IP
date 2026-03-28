-- Migration: 014_competitor_system.sql
-- Description: V4选题推荐系统 - 竞品爆款数据源
-- Created: 2026-03-27

-- ============================================================
-- 1. 创建竞品账号表（如果不存在）
-- ============================================================
CREATE TABLE IF NOT EXISTS competitor_accounts (
    competitor_id VARCHAR(64) PRIMARY KEY,
    ip_id VARCHAR(64) NOT NULL REFERENCES ip(ip_id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    platform VARCHAR(64) NOT NULL DEFAULT 'douyin',
    external_id VARCHAR(255),
    followers_display VARCHAR(64),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 修复：如果表已存在但缺少列，添加它们（使用 IF NOT EXISTS 避免报错）
ALTER TABLE competitor_accounts ADD COLUMN IF NOT EXISTS external_id VARCHAR(255);
ALTER TABLE competitor_accounts ADD COLUMN IF NOT EXISTS followers_display VARCHAR(64);
ALTER TABLE competitor_accounts ADD COLUMN IF NOT EXISTS notes TEXT;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_competitor_accounts_ip_id ON competitor_accounts(ip_id);

-- ============================================================
-- 1.5 确保 xiaomin IP 存在（外键依赖）
-- ============================================================
INSERT INTO ip (ip_id, name, platform, created_at, updated_at)
VALUES ('xiaomin', '晓敏', 'xiaohongshu', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (ip_id) DO NOTHING;

-- ============================================================
-- 2. 创建竞品视频表
-- ============================================================
CREATE TABLE IF NOT EXISTS competitor_videos (
    id SERIAL PRIMARY KEY,
    video_id VARCHAR(64) NOT NULL,
    competitor_id VARCHAR(64) NOT NULL REFERENCES competitor_accounts(competitor_id) ON DELETE CASCADE,
    title TEXT,
    "desc" TEXT,
    author VARCHAR(255),
    platform VARCHAR(32) DEFAULT 'douyin',
    play_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    share_count INTEGER DEFAULT 0,
    tags JSONB DEFAULT '[]',
    content_type VARCHAR(32),
    content_structure JSONB DEFAULT '{}',
    create_time TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(video_id, competitor_id)
);

CREATE INDEX IF NOT EXISTS idx_competitor_videos_competitor_id ON competitor_videos(competitor_id);
CREATE INDEX IF NOT EXISTS idx_competitor_videos_fetched_at ON competitor_videos(fetched_at);
CREATE INDEX IF NOT EXISTS idx_competitor_videos_play_count ON competitor_videos(play_count);
CREATE INDEX IF NOT EXISTS idx_competitor_videos_content_type ON competitor_videos(content_type);

-- ============================================================
-- 3. 插入17个竞品账号（基于竞品分析文档）
-- 使用 INSERT ON CONFLICT 避免重复插入
-- ============================================================

-- 1. 淘淘子 - 鲜活女性、高能量
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_001', 'xiaomin', '淘淘子', 'douyin', 'MS4wLjABAAAAF55VXn2Qj5pMh0PTyD-IG71GiSLs2U7YtbKtsA-oblA', '人设标签: 鲜活女性、旺盛生命力、高能量人士。参考价值: 活人感、感染力', '高能量')
ON CONFLICT (competitor_id) DO NOTHING;

-- 2. 顶妈私房早餐 - 最贴合的竞品，草根宝妈起盘
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_002', 'xiaomin', '顶妈私房早餐', 'douyin', 'MS4wLjABAAAATeQUszhzY6JjMfJy1Gya6ao5gGD66Gg1I_9vcJC-y9dfNHKtcXaQ-Mu0K1SPy8EK', '人设标签: 草根宝妈起盘、真实烟火气、死磕产品与手艺的实战派。最贴合私房赛道的竞品，验证了在家庭厨房里就能跑通商业闭环。', '最贴合')
ON CONFLICT (competitor_id) DO NOTHING;

-- 3. 深圳蓝蒂蔻Gina - 高客单价操盘手
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_003', 'xiaomin', '深圳蓝蒂蔻Gina', 'douyin', 'MS4wLjABAAAA3XsMOiah1EsT6TSzoqMjlgH4GdMhoBCLwunPVyUP34y-EbUgIV04OU2dnpImMfHq', '人设标签: 美业女王、高客单价操盘手、极致的狼性与舞台魅力。参考价值: 私域和线下会场的转化能力，情绪价值交付让学员心甘情愿买单。', '高客单')
ON CONFLICT (competitor_id) DO NOTHING;

-- 4. 梁宸瑜·无价之姐 - 销讲女王
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_004', 'xiaomin', '梁宸瑜·无价之姐', 'douyin', 'MS4wLjABAAAAErFzzalv2271brW_cK7vbdLX67B8zOw2ReVYJ72GyoPu2AbZnT3QYNpq4uyxePWr', '人设标签: 销讲女王、高情商成交专家、女性力量觉醒领袖。参考价值: 线下大课模板，气场全开的舞台表现力和高情商逼单话术。', '销讲')
ON CONFLICT (competitor_id) DO NOTHING;

-- 5. Olga姐姐 - 高认知降维打击
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_005', 'xiaomin', 'Olga姐姐', 'douyin', 'MS4wLjABAAAAWwcXLQaOlIV4k04tSI4xYaYmCzRZt1a9_IDDutj7Wzra_yNzBUDrPQgV8UVJ_dsH', '人设标签: 35年外企CEO/高管、300万粉职场教练。参考价值: 我看透了商业本质的沉稳与睿智，笃定、不容置疑的语气提升信任背书。', '高认知')
ON CONFLICT (competitor_id) DO NOTHING;

-- 6. 张琦老师-商业连锁 - 商业导师头部
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_006', 'xiaomin', '张琦老师-商业连锁', 'douyin', 'MS4wLjABAAAAfmygSsGTU3RIctsoi4vcbWkAQaMRi_KwtQh1bP7WCzf1k0yydcLtKQj7kE-FSwsJ', '人设标签: 商业导师头部，金句频出，气场强大。参考价值: 商业口播教科书，压迫感、一语道破商业本质的排比句结构，拉高完播率。', '商业头部')
ON CONFLICT (competitor_id) DO NOTHING;

-- 7. 崔璀优势星球 - 女性共情力天花板
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_007', 'xiaomin', '崔璀优势星球', 'douyin', 'MS4wLjABAAAAHu4SbvaUZQ1GN2WgySRB6G4nmvUvWxD2fNLzvDKOkOAmqxZkQ5fJtx0ZhANSST7V', '人设标签: 温柔且有力量的宝妈CEO、女性心理疗愈师。参考价值: 女性共情力天花板，懂你、接纳你、帮你放大优势的话术体系，化解全职妈妈防备心。', '共情力天花板')
ON CONFLICT (competitor_id) DO NOTHING;

-- 8. 王潇_潇洒姐 - 趁早精神领袖
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_008', 'xiaomin', '王潇_潇洒姐', 'douyin', 'MS4wLjABAAAAbDuwvhxdzfp009rDpY1mj4NmPu_A_Txsi9SP6Ybz3Bk', '人设标签: 极端自律、终身成长、趁早精神领袖。参考价值: 把自律变成信仰，打卡、社群陪伴模式，提升复购率和转介绍率。', '自律领袖')
ON CONFLICT (competitor_id) DO NOTHING;

-- 9. 张萌萌姐 - 轻资产创业导师
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_009', 'xiaomin', '张萌萌姐', 'douyin', 'MS4wLjABAAAAvrhmrhhYvc4eJvqu_0MStkyBihmGdJZCBl_JVZ0AulE', '人设标签: 凌晨4点起床的狠人、轻资产创业导师。参考价值: 把底层努力包装成奋斗人设，执行力和复盘的SOP。', '执行力')
ON CONFLICT (competitor_id) DO NOTHING;

-- 10. 清华陈晶聊商业 - 顶级逻辑流
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_010', 'xiaomin', '清华陈晶聊商业', 'douyin', 'MS4wLjABAAAAV5oVsV-RjxHKrcCuqQotWtHvT8_Y7z_aQnTvT61slic', '人设标签: 清华学霸、前投资人躬身入局、顶级逻辑流。参考价值: 从上往下看的理性商业视角，结构化的拆解方式，硬核的商业说服力。', '逻辑流')
ON CONFLICT (competitor_id) DO NOTHING;

-- 11. Dada人物圈 - 造梦能力和矩阵打法
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_011', 'xiaomin', 'Dada人物圈', 'douyin', 'MS4wLjABAAAAnTsmfVQNtopff5MrXYMf9y2oVrZ9usIHaCOb_6T1mVo', '人设标签: 90后野心家、微商大咖转型。参考价值: 造梦能力和矩阵切片打法，把赚钱效应无限放大的招募逻辑。', '造梦能力')
ON CONFLICT (competitor_id) DO NOTHING;

-- 12. 赵三观 - 视觉系吸金
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_012', 'xiaomin', '赵三观', 'douyin', 'MS4wLjABAAAA7hiENPfyARPotUS0FootY0s1Qg51l4X3gvkXEKYUHas', '人设标签: 实体营销实战派、视觉系吸金老板娘。参考价值: 用高颜值造型打破刻板印象，把实体店经验降维成线上课程。', '视觉系')
ON CONFLICT (competitor_id) DO NOTHING;

-- 13. 程前Jason - 创业者故事包装
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_013', 'xiaomin', '程前Jason', 'douyin', 'MS4wLjABAAAAoGgpFqfuSXAjeMy21Qk8Pn1NvaSukBN7vCipz3xsPOU', '人设标签: 90后男性、商业访谈、精英感与草根故事结合。参考价值: 把普通创业者故事包装得像热血大片，强节奏、抓痛点、给结果。', '故事包装')
ON CONFLICT (competitor_id) DO NOTHING;

-- 14. 群响刘思毅 - 私域朋友圈模板
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_014', 'xiaomin', '群响刘思毅', 'douyin', 'MS4wLjABAAAAO_KKPhlqsPDzmTIxBFSFUX5Hjuj8Y94gHQpJgqHlub0', '人设标签: 90后男性、草根创业圈子、极度真实。参考价值: 极度真诚、极度渴望赚钱，朋友圈碎碎念写小作文的打法，私域终极模板。', '私域模板')
ON CONFLICT (competitor_id) DO NOTHING;

-- 15. 透透糖 - 草根逆袭导师
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_015', 'xiaomin', '透透糖', 'douyin', 'MS4wLjABAAAAZXgVjvDmWo_ipGRJnXwFREdhkG29krGiVSwIQhzIrDA', '人设标签: 90后、草根逆袭、电商/私域变现导师。参考价值: 早期经历接地气，擅长教普通女孩和宝妈轻资产逆袭，话术极具煽动性且干货极多。', '草根逆袭')
ON CONFLICT (competitor_id) DO NOTHING;

-- 16. 房琪kiki - 神级文案
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_016', 'xiaomin', '房琪kiki', 'douyin', 'MS4wLjABAAAAHAlF09yQrLMxW8wyJUO0NGlrsE7O0_9yTki_BkZM16g', '人设标签: 90后、独立女性、神级文案。参考价值: 每条视频文案精准击中女性内心，个人传记类短视频的文案结构。', '神级文案')
ON CONFLICT (competitor_id) DO NOTHING;

-- 17. 杨天真 - 清醒大女主
INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display)
VALUES ('comp_xiaomin_017', 'xiaomin', '杨天真', 'douyin', 'MS4wLjABAAAAB1lxLcDT1n51dY3jyB-VQACgN0gbYWGxvSdiE0DWYLY', '人设标签: 清醒大女主的精神领袖。参考价值: 犀利职场和人性观点，搞钱是最大底气的价值观传递。', '清醒大女主')
ON CONFLICT (competitor_id) DO NOTHING;

-- ============================================================
-- 4. 插入示例爆款视频数据
-- 使用 INSERT ON CONFLICT 避免重复插入
-- ============================================================

-- 顶妈私房早餐 - 逆袭/转变类
INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_001_dingma', 'comp_xiaomin_002', '从手心向上到月入3万：一个宝妈的3年私房创业史', '三年前我还在家里带孩子，每个月伸手向老公要生活费。今天我想分享我是如何从零开始做私房面食，一步步实现经济独立。', '顶妈私房早餐', 'douyin', 312000, 67000, 'emotion', '{"hook_type": "对比", "conflict": "手心向上", "emotion": "共鸣", "target_audience": "宝妈"}', '2024-01-15 10:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_002_dingma', 'comp_xiaomin_002', '凌晨4点起床做包子，我只用了3个月就回本了', '很多人问我做私房早餐辛不辛苦，我想说的是，比起看人脸色的日子，这点辛苦算什么？', '顶妈私房早餐', 'douyin', 245000, 45000, 'money', '{"hook_type": "数字", "conflict": "辛苦", "emotion": "励志", "target_audience": "宝妈"}', '2024-01-14 08:30:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_003_dingma', 'comp_xiaomin_002', '宝妈做私房早餐的3个避坑指南，看完少亏5万', '做私房3年，踩过的坑比做过的包子还多。今天分享3个血泪教训，希望能帮到想入行的姐妹。', '顶妈私房早餐', 'douyin', 189000, 32000, 'skill', '{"hook_type": "数字", "conflict": "踩坑", "emotion": "警示", "target_audience": "宝妈"}', '2024-01-13 15:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_004_dingma', 'comp_xiaomin_002', '做私房第1天vs第365天，我的变化太大了', '一年前的我手忙脚乱，一年后的我从容淡定。不只是技术上的进步，更是心态的蜕变。', '顶妈私房早餐', 'douyin', 198000, 42000, 'emotion', '{"hook_type": "对比", "conflict": "新手迷茫", "emotion": "欣慰", "target_audience": "新手宝妈"}', '2024-01-11 10:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

-- 崔璀优势星球 - 共情类
INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_001_cuicui', 'comp_xiaomin_007', '全职妈妈的价值，不应该只体现在做家务上', '我想对所有全职妈妈说：你的价值远不止这些。你值得被看见，值得拥有属于自己的事业。', '崔璀优势星球', 'douyin', 567000, 123000, 'emotion', '{"hook_type": "观点", "conflict": "价值被忽视", "emotion": "共情", "target_audience": "全职妈妈"}', '2024-01-15 12:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_002_cuicui', 'comp_xiaomin_007', '为什么很多宝妈做副业都失败了？答案很扎心', '不是你不努力，是你的方向错了。今天分享我辅导过的3000+宝妈案例，总结出的3个核心误区。', '崔璀优势星球', 'douyin', 423000, 89000, 'skill', '{"hook_type": "疑问", "conflict": "失败焦虑", "emotion": "扎心", "target_audience": "宝妈"}', '2024-01-14 18:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

-- 透透糖 - 逆袭类
INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_001_tang', 'comp_xiaomin_015', '90后农村女孩，靠一部手机月入10万的方法', '我从农村出来，没背景没资源，就是靠这个不起眼的小生意，改变了全家人的命运。今天毫无保留分享给你。', '透透糖', 'douyin', 678000, 156000, 'money', '{"hook_type": "数字", "conflict": "出身寒门", "emotion": "励志", "target_audience": "草根女性"}', '2024-01-15 09:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_002_tang', 'comp_xiaomin_015', '没本钱没人脉，宝妈能做的5个零门槛副业', '我自己就是从零开始的，深知宝妈的不容易。这5个副业不需要本钱，不需要人脉，只要有一部手机就能做。', '透透糖', 'douyin', 534000, 112000, 'money', '{"hook_type": "数字", "conflict": "没资源", "emotion": "实用", "target_audience": "宝妈"}', '2024-01-13 14:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_003_tang', 'comp_xiaomin_015', '别再做微商了！2024年宝妈能做的3个新赛道', '微商时代已经过去了，这3个新赛道才是真正的红利期。我已经带了几百个宝妈拿到了结果。', '透透糖', 'douyin', 445000, 98000, 'money', '{"hook_type": "数字", "conflict": "过时模式", "emotion": "机会", "target_audience": "宝妈"}', '2024-01-12 11:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

-- 张琦 - 商业类
INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_001_zhangqi', 'comp_xiaomin_006', '为什么越来越多的宝妈选择轻创业？答案很现实', '不是她们不想上班，是上班养不起家，不上班养不起自己。轻创业，是宝妈唯一的出路。', '张琦老师-商业连锁', 'douyin', 1023000, 234000, 'money', '{"hook_type": "疑问", "conflict": "经济压力", "emotion": "犀利", "target_audience": "宝妈"}', '2024-01-15 13:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

-- Gina - 高客单
INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_001_gina', 'comp_xiaomin_003', '从负债50万到年入千万，我做对了这3件事', '2019年我负债50万，信用卡刷爆，走投无路。今天的我，年入千万，带着几千名女性一起搞钱。', '深圳蓝蒂蔻Gina', 'douyin', 1567000, 345000, 'money', '{"hook_type": "数字+对比", "conflict": "负债", "emotion": "震撼", "target_audience": "想搞钱女性"}', '2024-01-14 20:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

-- 杨天真 - 价值观
INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_001_yang', 'comp_xiaomin_017', '搞钱才是女人最大的底气，别不信', '我见过太多女性，在婚姻里委曲求全，就是因为没有经济独立。听我的，去搞钱，这是你最硬的底气。', '杨天真', 'douyin', 2345000, 567000, 'emotion', '{"hook_type": "观点", "conflict": "经济不独立", "emotion": "犀利", "target_audience": "女性"}', '2024-01-15 16:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

-- 房琪 - 故事
INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_001_fangqi', 'comp_xiaomin_016', '我用了10年，才活成自己喜欢的样子', '从一个小镇姑娘，到今天走遍世界。我想告诉你，不管你起点多低，都可以靠自己改变命运。', '房琪kiki', 'douyin', 1890000, 456000, 'emotion', '{"hook_type": "时间线", "conflict": "出身平凡", "emotion": "治愈", "target_audience": "年轻女性"}', '2024-01-13 19:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

-- 淘淘子 - 高能量
INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_001_tao', 'comp_xiaomin_001', '32岁，我终于活成了别人羡慕的样子', '三年前我还是个焦虑的全职妈妈，每天都在自我怀疑。现在的我，有自己的事业，有底气，有光芒。', '淘淘子', 'douyin', 789000, 189000, 'emotion', '{"hook_type": "结果前置", "conflict": "焦虑迷茫", "emotion": "励志", "target_audience": "30+女性"}', '2024-01-15 11:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

-- 张萌萌姐 - 执行力
INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_001_meng', 'comp_xiaomin_009', '凌晨4点起床，我做对了什么让收入翻10倍', '很多人觉得早起很痛苦，但我想说，比起没钱的日子，早起算什么？分享我的时间管理法。', '张萌萌姐', 'douyin', 445000, 98000, 'skill', '{"hook_type": "数字", "conflict": "时间不够用", "emotion": "励志", "target_audience": "想搞钱的人"}', '2024-01-14 06:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;

-- 顶妈 - 挑战类
INSERT INTO competitor_videos (video_id, competitor_id, title, "desc", author, platform, play_count, like_count, content_type, content_structure, create_time)
VALUES ('vid_005_dingma', 'comp_xiaomin_002', '30天挑战：每天卖100个包子，我能做到吗？', '有人说不行，我说试试。30天记录，从0到日销100个的真实过程。', '顶妈私房早餐', 'douyin', 267000, 58000, 'life', '{"hook_type": "挑战", "conflict": "质疑", "emotion": "励志", "target_audience": "宝妈"}', '2024-01-10 08:00:00')
ON CONFLICT (video_id, competitor_id) DO NOTHING;
