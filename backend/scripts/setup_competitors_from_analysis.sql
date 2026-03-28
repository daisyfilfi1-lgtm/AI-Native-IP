-- ============================================================
-- 竞品账号配置脚本
-- 数据来源: docs/IP知识库/竞品分析.docx
-- 分析账号数量: 17个（针对小敏IP的竞品分析）
-- ============================================================

-- 先删除旧的竞品配置（小敏IP）
DELETE FROM competitor_accounts WHERE ip_id = 'xiaomin';

-- 插入竞品账号
-- 注意: 这里使用抖音主页链接，实际抓取时需要sec_uid
-- 可以通过分享链接获取sec_uid，或使用已有的链接转换

INSERT INTO competitor_accounts (competitor_id, ip_id, name, platform, external_id, notes, followers_display) VALUES
-- 1. 淘淘子 - 鲜活女性、高能量
('comp_xiaomin_001', 'xiaomin', '淘淘子', 'douyin', 
 'MS4wLjABAAAAF55VXn2Qj5pMh0PTyD-IG71GiSLs2U7YtbKtsA-oblA',
 '人设标签: 鲜活女性、旺盛生命力、高能量人士。参考价值: 活人感、感染力',
 '高能量'),

-- 2. 顶妈私房早餐 - 最贴合的竞品，草根宝妈起盘
('comp_xiaomin_002', 'xiaomin', '顶妈私房早餐', 'douyin',
 'MS4wLjABAAAATeQUszhzY6JjMfJy1Gya6ao5gGD66Gg1I_9vcJC-y9dfNHKtcXaQ-Mu0K1SPy8EK',
 '人设标签: 草根宝妈起盘、真实烟火气、死磕产品与手艺的实战派。最贴合私房赛道的竞品，验证了在家庭厨房里就能跑通商业闭环。',
 '最贴合'),

-- 3. 深圳蓝蒂蔻Gina - 高客单价操盘手
('comp_xiaomin_003', 'xiaomin', '深圳蓝蒂蔻Gina', 'douyin',
 'MS4wLjABAAAA3XsMOiah1EsT6TSzoqMjlgH4GdMhoBCLwunPVyUP34y-EbUgIV04OU2dnpImMfHq',
 '人设标签: 美业女王、高客单价操盘手、极致的狼性与舞台魅力。参考价值: 私域和线下会场的转化能力，情绪价值交付让学员心甘情愿买单。',
 '高客单'),

-- 4. 梁宸瑜·无价之姐 - 销讲女王
('comp_xiaomin_004', 'xiaomin', '梁宸瑜·无价之姐', 'douyin',
 'MS4wLjABAAAAErFzzalv2271brW_cK7vbdLX67B8zOw2ReVYJ72GyoPu2AbZnT3QYNpq4uyxePWr',
 '人设标签: 销讲女王、高情商成交专家、女性力量觉醒领袖。参考价值: 线下大课模板，气场全开的舞台表现力和高情商逼单话术。',
 '销讲'),

-- 5. Olga姐姐 - 高认知降维打击
('comp_xiaomin_005', 'xiaomin', 'Olga姐姐', 'douyin',
 'MS4wLjABAAAAWwcXLQaOlIV4k04tSI4xYaYmCzRZt1a9_IDDutj7Wzra_yNzBUDrPQgV8UVJ_dsH',
 '人设标签: 35年外企CEO/高管、300万粉职场教练。参考价值: 我看透了商业本质的沉稳与睿智，笃定、不容置疑的语气提升信任背书。',
 '高认知'),

-- 6. 张琦老师-商业连锁 - 商业导师头部
('comp_xiaomin_006', 'xiaomin', '张琦老师-商业连锁', 'douyin',
 'MS4wLjABAAAAfmygSsGTU3RIctsoi4vcbWkAQaMRi_KwtQh1bP7WCzf1k0yydcLtKQj7kE-FSwsJ',
 '人设标签: 商业导师头部，金句频出，气场强大。参考价值: 商业口播教科书，压迫感、一语道破商业本质的排比句结构，拉高完播率。',
 '商业头部'),

-- 7. 崔璀优势星球 - 女性共情力天花板
('comp_xiaomin_007', 'xiaomin', '崔璀优势星球', 'douyin',
 'MS4wLjABAAAAHu4SbvaUZQ1GN2WgySRB6G4nmvUvWxD2fNLzvDKOkOAmqxZkQ5fJtx0ZhANSST7V',
 '人设标签: 温柔且有力量的宝妈CEO、女性心理疗愈师。参考价值: 女性共情力天花板，懂你、接纳你、帮你放大优势的话术体系，化解全职妈妈防备心。',
 '共情力天花板'),

-- 8. 王潇_潇洒姐 - 趁早精神领袖
('comp_xiaomin_008', 'xiaomin', '王潇_潇洒姐', 'douyin',
 'MS4wLjABAAAAbDuwvhxdzfp009rDpY1mj4NmPu_A_Txsi9SP6Ybz3Bk',
 '人设标签: 极端自律、终身成长、趁早精神领袖。参考价值: 把自律变成信仰，打卡、社群陪伴模式，提升复购率和转介绍率。',
 '自律领袖'),

-- 9. 张萌萌姐 - 轻资产创业导师
('comp_xiaomin_009', 'xiaomin', '张萌萌姐', 'douyin',
 'MS4wLjABAAAAvrhmrhhYvc4eJvqu_0MStkyBihmGdJZCBl_JVZ0AulE',
 '人设标签: 凌晨4点起床的狠人、轻资产创业导师。参考价值: 把底层努力包装成奋斗人设，执行力和复盘的SOP。',
 '执行力'),

-- 10. 清华陈晶聊商业 - 顶级逻辑流
('comp_xiaomin_010', 'xiaomin', '清华陈晶聊商业', 'douyin',
 'MS4wLjABAAAAV5oVsV-RjxHKrcCuqQotWtHvT8_Y7z_aQnTvT61slic',
 '人设标签: 清华学霸、前投资人躬身入局、顶级逻辑流。参考价值: 从上往下看的理性商业视角，结构化的拆解方式，硬核的商业说服力。',
 '逻辑流'),

-- 11. Dada人物圈 - 造梦能力和矩阵打法
('comp_xiaomin_011', 'xiaomin', 'Dada人物圈', 'douyin',
 'MS4wLjABAAAAnTsmfVQNtopff5MrXYMf9y2oVrZ9usIHaCOb_6T1mVo',
 '人设标签: 90后野心家、微商大咖转型。参考价值: 造梦能力和矩阵切片打法，把赚钱效应无限放大的招募逻辑。',
 '造梦能力'),

-- 12. 赵三观 - 视觉系吸金
('comp_xiaomin_012', 'xiaomin', '赵三观', 'douyin',
 'MS4wLjABAAAA7hiENPfyARPotUS0FootY0s1Qg51l4X3gvkXEKYUHas',
 '人设标签: 实体营销实战派、视觉系吸金老板娘。参考价值: 用高颜值造型打破刻板印象，把实体店经验降维成线上课程。',
 '视觉系'),

-- 13. 程前Jason - 创业者故事包装
('comp_xiaomin_013', 'xiaomin', '程前Jason', 'douyin',
 'MS4wLjABAAAAoGgpFqfuSXAjeMy21Qk8Pn1NvaSukBN7vCipz3xsPOU',
 '人设标签: 90后男性、商业访谈、精英感与草根故事结合。参考价值: 把普通创业者故事包装得像热血大片，强节奏、抓痛点、给结果。',
 '故事包装'),

-- 14. 群响刘思毅 - 私域朋友圈模板
('comp_xiaomin_014', 'xiaomin', '群响刘思毅', 'douyin',
 'MS4wLjABAAAAO_KKPhlqsPDzmTIxBFSFUX5Hjuj8Y94gHQpJgqHlub0',
 '人设标签: 90后男性、草根创业圈子、极度真实。参考价值: 极度真诚、极度渴望赚钱，朋友圈碎碎念写小作文的打法，私域终极模板。',
 '私域模板'),

-- 15. 透透糖 - 草根逆袭导师
('comp_xiaomin_015', 'xiaomin', '透透糖', 'douyin',
 'MS4wLjABAAAAZXgVjvDmWo_ipGRJnXwFREdhkG29krGiVSwIQhzIrDA',
 '人设标签: 90后、草根逆袭、电商/私域变现导师。参考价值: 早期经历接地气，擅长教普通女孩和宝妈轻资产逆袭，话术极具煽动性且干货极多。',
 '草根逆袭'),

-- 16. 房琪kiki - 神级文案
('comp_xiaomin_016', 'xiaomin', '房琪kiki', 'douyin',
 'MS4wLjABAAAAHAlF09yQrLMxW8wyJUO0NGlrsE7O0_9yTki_BkZM16g',
 '人设标签: 90后、独立女性、神级文案。参考价值: 每条视频文案精准击中女性内心，个人传记类短视频的文案结构。',
 '神级文案'),

-- 17. 杨天真 - 清醒大女主
('comp_xiaomin_017', 'xiaomin', '杨天真', 'douyin',
 'MS4wLjABAAAAB1lxLcDT1n51dY3jyB-VQACgN0gbYWGxvSdiE0DWYLY',
 '人设标签: 清醒大女主的精神领袖。参考价值: 犀利职场和人性观点，搞钱是最大底气的价值观传递。',
 '清醒大女主');

-- 查看插入结果
SELECT 
    competitor_id,
    name,
    platform,
    followers_display,
    LEFT(notes, 50) as notes_preview
FROM competitor_accounts 
WHERE ip_id = 'xiaomin'
ORDER BY competitor_id;
