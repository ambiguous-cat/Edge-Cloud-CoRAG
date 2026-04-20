#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查隐私数据库的表结构和内容
"""

import sqlite3
import os

def check_privacy_database():
    """检查隐私数据库的结构和内容"""
    print("🔍 检查隐私数据库结构")
    print("=" * 50)
    
    db_path = "../privacy_data/privacy_data.db"
    
    if not os.path.exists(db_path):
        print("❌ 隐私数据库不存在")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 查看所有表
        print("📋 数据库中的表:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            print(f"   - {table_name}")
        
        print()
        
        # 2. 检查每个表的结构和内容
        for table in tables:
            table_name = table[0]
            print(f"📊 表: {table_name}")
            print("-" * 30)
            
            # 查看表结构
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            print("表结构:")
            for col in columns:
                col_id, col_name, col_type, not_null, default_val, pk = col
                pk_str = " (主键)" if pk else ""
                not_null_str = " NOT NULL" if not_null else ""
                print(f"   {col_name}: {col_type}{not_null_str}{pk_str}")
            
            # 查看数据内容
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"\n数据行数: {count}")
            
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
                rows = cursor.fetchall()
                print("前5行数据:")
                for i, row in enumerate(rows, 1):
                    print(f"   {i}. {row}")
                
                if count > 5:
                    print(f"   ... 还有 {count - 5} 行")
            
            print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 检查数据库失败: {e}")

if __name__ == "__main__":
    check_privacy_database()
