#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.path.insert(0, '.')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/ip_factory')

print('=== Test 1: Database Check ===')
try:
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    # Check competitor_accounts
    result = db.execute(text("SELECT COUNT(*) FROM competitor_accounts WHERE ip_id = 'xiaomin'"))
    comp_count = result.scalar()
    print(f'Competitor accounts: {comp_count}')
    
    # Check competitor_videos
    result = db.execute(text("""
        SELECT COUNT(*), AVG(play_count) 
        FROM competitor_videos cv
        JOIN competitor_accounts ca ON cv.competitor_id = ca.competitor_id
        WHERE ca.ip_id = 'xiaomin'
    """))
    row = result.fetchone()
    print(f'Competitor videos: {row[0] if row else 0}')
    
    db.close()
    print('Database check OK')
except Exception as e:
    print(f'Database error: {e}')

print()
print('=== Test 2: Import V4 Service ===')
try:
    from app.services.topic_recommendation_v4 import get_recommendation_service_v4
    print('V4 service imported OK')
except Exception as e:
    print(f'Import error: {e}')

print()
print('=== Test 3: Import Content Pipeline ===')
try:
    from app.services.content_generation_pipeline import create_strategy_agent
    print('Content pipeline imported OK')
except Exception as e:
    print(f'Import error: {e}')
