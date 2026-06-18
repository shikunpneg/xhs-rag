#!/usr/bin/env node
/**
 * 批量导入笔记到Cloudflare Vectorize
 * 
 * 使用方法：
 * 1. 先在本地启动wrangler dev
 * 2. 运行: node import-notes.js
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import sqlite3 from 'better-sqlite3';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 本地数据库路径
const DB_PATH = path.join(__dirname, '..', 'data', 'xhs_notes.db');

// API地址（Cloudflare生产环境）
const API_BASE = 'https://xhs-rag.ok2442504.workers.dev';

/**
 * 从本地SQLite加载笔记
 */
function loadNotesFromDB() {
    if (!fs.existsSync(DB_PATH)) {
        console.error('数据库文件不存在:', DB_PATH);
        console.log('请先在本地RAG系统中采集笔记');
        return [];
    }
    
    const db = sqlite3(DB_PATH);
    
    const notes = db.prepare(`
        SELECT 
            note_id, 
            title, 
            content, 
            url, 
            user_id as author,
            nickname,
            liked_count,
            collected_count,
            publish_time,
            created_at
        FROM notes
    `).all();
    
    db.close();
    
    console.log(`从数据库加载了 ${notes.length} 篇笔记`);
    return notes;
}

/**
 * 批量添加到API
 */
async function batchAddNotes(notes, batchSize = 10) {
    const results = {
        success: 0,
        failed: 0,
        errors: []
    };
    
    for (let i = 0; i < notes.length; i += batchSize) {
        const batch = notes.slice(i, i + batchSize);
        const batchNumber = Math.floor(i / batchSize) + 1;
        const totalBatches = Math.ceil(notes.length / batchSize);
        
        console.log(`\n处理批次 ${batchNumber}/${totalBatches} (${batch.length} 条笔记)`);
        
        try {
            const response = await fetch(`${API_BASE}/api/notes/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ notes: batch })
            });
            
            const result = await response.json();
            
            if (result.successful) {
                results.success += result.successful;
                console.log(`  ✅ 成功添加 ${result.successful}/${batch.length} 条`);
            }
            
            if (result.results) {
                result.results.forEach(r => {
                    if (!r.success) {
                        results.failed++;
                        results.errors.push({
                            note_id: r.note_id,
                            error: r.error
                        });
                    }
                });
            }
            
        } catch (error) {
            console.error(`  ❌ 批次 ${batchNumber} 请求失败:`, error.message);
            results.failed += batch.length;
            results.errors.push({
                batch: batchNumber,
                error: error.message
            });
        }
        
        // 避免请求过快
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
    
    return results;
}

/**
 * 主函数
 */
async function main() {
    console.log('================================');
    console.log('笔记批量导入工具');
    console.log('================================\n');
    
    // 检查API连接
    console.log('检查API连接...');
    try {
        const healthRes = await fetch(`${API_BASE}/health`);
        if (healthRes.ok) {
            console.log('✅ API已连接\n');
        } else {
            throw new Error('API返回错误状态');
        }
    } catch (error) {
        console.error('❌ API连接失败:', error.message);
        console.log('\n请确保：');
        console.log('1. 已运行 npx wrangler dev');
        console.log('2. Wrangler服务正在 http://localhost:8787 运行\n');
        process.exit(1);
    }
    
    // 加载笔记
    const notes = loadNotesFromDB();
    
    if (notes.length === 0) {
        console.log('没有找到可导入的笔记');
        process.exit(0);
    }
    
    // 确认导入
    console.log('\n即将导入的笔记预览：');
    notes.slice(0, 5).forEach((note, i) => {
        console.log(`  ${i + 1}. ${note.title.substring(0, 50)}...`);
    });
    if (notes.length > 5) {
        console.log(`  ... 还有 ${notes.length - 5} 条`);
    }
    
    // 开始导入
    console.log('\n开始导入...\n');
    const results = await batchAddNotes(notes);
    
    // 显示结果
    console.log('\n================================');
    console.log('导入完成！');
    console.log(`✅ 成功: ${results.success}`);
    console.log(`❌ 失败: ${results.failed}`);
    
    if (results.errors.length > 0) {
        console.log('\n错误详情：');
        results.errors.slice(0, 10).forEach(err => {
            console.log(`  - ${err.note_id || '未知'}: ${err.error}`);
        });
    }
    console.log('================================');
}

// 运行
main().catch(console.error);
