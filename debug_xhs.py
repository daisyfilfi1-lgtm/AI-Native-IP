# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import asyncio
import os
import re
import json

sys.path.insert(0, 'backend')
os.chdir('backend')

async def test():
    from playwright.async_api import async_playwright
    
    url = 'http://xhslink.com/o/632S35VaAwg'
    print('Opening with Playwright...')
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X)',
            viewport={'width': 375, 'height': 812}
        )
        page = await context.new_page()
        
        # 等待更长时间
        await page.goto(url, wait_until='networkidle', timeout=30000)
        
        # 滚动页面触发懒加载
        print('Scrolling...')
        for i in range(3):
            await page.evaluate('window.scrollBy(0, 500)')
            await asyncio.sleep(1)
        
        # 1. Page title
        title = await page.title()
        print('\n=== Page Title ===')
        print(title)
        
        # 2. 尝试各种 selector
        print('\n=== DOM Selectors ===')
        selectors = [
            ('#detail-desc', 'detail-desc'),
            ('.note-content', 'note-content'),
            ('article', 'article'),
            ('.detail-desc', 'detail-desc-2'),
            ('[class*="note"]', 'note-class'),
            ('[class*="content"]', 'content-class'),
            ('.user-info', 'user-info'),  # 可能包含部分内容
            ('.video-info', 'video-info'),
        ]
        
        for sel, name in selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    txt = await el.text_content(timeout=2000)
                    if txt and len(txt.strip()) > 10:
                        print(f'{name}: {txt.strip()[:300]}')
            except Exception as e:
                pass
        
        # 3. 获取所有文本
        print('\n=== All Page Text ===')
        try:
            all_text = await page.evaluate('''
                () => {
                    // 获取 body 下的所有文本
                    const walker = document.createTreeWalker(
                        document.body, 
                        NodeFilter.SHOW_TEXT, 
                        null, 
                        false
                    );
                    let texts = [];
                    let node;
                    while(node = walker.nextNode()) {
                        const text = node.textContent.trim();
                        if (text.length > 20) {
                            texts.push(text);
                        }
                    }
                    return texts.slice(0, 10).join('\\n');
                }
            ''')
            print(all_text[:1000])
        except Exception as e:
            print(f'Error: {e}')
        
        # 4. 查看页面结构
        print('\n=== HTML Structure (first 2000 chars) ===')
        html = await page.content()
        print(html[:2000])
        
        await browser.close()
        print('\nDone')

asyncio.run(test())