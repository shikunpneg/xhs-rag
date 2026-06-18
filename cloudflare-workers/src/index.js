/**
 * 小红书 RAG Cloudflare Workers
 * 核心功能：
 * 1. 向量检索（Vectorize）
 * 2. LLM推理（Workers AI）
 * 3. 情感分析
 * 4. 关键词提取
 * 5. 模拟浏览器爬虫（Cloudflare Browser Rendering）
 */

import puppeteer from "@cloudflare/puppeteer";

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'X-Content-Type-Options': 'nosniff',
};

async function handleOptions(request) {
  return new Response(null, {
    headers: { ...corsHeaders, 'Access-Control-Max-Age': '86400' },
  });
}

async function generateEmbedding(text, env) {
  try {
    const result = await env.AI.run('@cf/baai/bge-base-en-v1.5', {
      text: text,
    });
    
    let embedding = result.data;
    
    if (!embedding) {
      throw new Error('Embedding generation returned undefined data');
    }
    
    if (Array.isArray(embedding) && embedding.length === 1 && Array.isArray(embedding[0])) {
      embedding = embedding[0];
    }
    
    if (!Array.isArray(embedding)) {
      throw new Error('Embedding generation returned invalid format');
    }
    
    embedding = embedding.map(v => {
      if (v === null || v === undefined || isNaN(v)) {
        return 0.0;
      }
      return parseFloat(v);
    });
    
    return embedding;
  } catch (error) {
    console.error('Embedding generation failed:', error);
    throw error;
  }
}

async function retrieve(query, env, topK = 5) {
  if (!env.VECTORIZE) {
    throw new Error('Vectorize not configured');
  }

  const embedding = await generateEmbedding(query, env);
  const results = await env.VECTORIZE.query(embedding, { topK, returnMetadata: true });

  if (!results || !results.matches || !Array.isArray(results.matches)) {
    return [];
  }

  const sources = results.matches
    .filter(match => match && match.id && match.metadata)
    .map(match => ({
      note_id: match.id,
      title: match.metadata.title || '',
      content: match.metadata.content || '',
      url: match.metadata.url || '',
      author: match.metadata.author || '',
      score: match.score || 0,
    }));

  return sources;
}

async function generateAnswer(query, sources, env) {
  const apiKey = env.DEEPSEEK_API_KEY;
  if (!apiKey) {
    throw new Error('DeepSeek API key not configured');
  }

  const context = sources
    .map((source, index) => {
      const content = source.content || source.title || '';
      return `${index + 1}. ${content.slice(0, 200)}`;
    })
    .join('\n\n');

  const systemPrompt = '你是一个专业的小红书内容助手。请根据提供的参考资料回答用户的问题。';
  const userPrompt = `参考资料：\n${context}\n\n用户问题：${query}`;

  const response = await fetch('https://api.deepseek.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: 'deepseek-chat',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt },
      ],
      max_tokens: 500,
      temperature: 0.7,
    }),
  });

  const data = await response.json();
  return data.choices[0].message.content;
}

async function analyzeSentiment(text, env) {
  const prompt = `请分析以下文本的情感倾向，并输出JSON格式结果：\n\n文本内容：${text}\n\n输出格式：{"sentiment": "positive/negative/neutral", "score": 0-1, "summary": "简短摘要"}\n只输出JSON，不要其他内容。`;

  try {
    const response = await env.AI.run('@cf/meta/llama-3-8b-instruct', {
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 256,
      temperature: 0.3,
    });

    try {
      const jsonStr = response.response.match(/\{[\s\S]*\}/);
      return jsonStr ? JSON.parse(jsonStr[0]) : {
        sentiment: 'neutral',
        score: 0.5,
        summary: text.substring(0, 50),
        error: 'JSON解析失败',
      };
    } catch {
      return {
        sentiment: 'neutral',
        score: 0.5,
        summary: text.substring(0, 50),
        error: 'JSON解析失败',
      };
    }
  } catch (error) {
    console.error('Sentiment analysis failed:', error);
    return {
      sentiment: 'neutral',
      score: 0.5,
      summary: text.substring(0, 50),
      error: '分析失败',
    };
  }
}

async function extractKeywords(text, env) {
  const prompt = `请从以下文本中提取10个最重要的关键词：\n\n文本内容：${text}\n\n请只输出关键词，用逗号分隔，不要其他内容。`;

  try {
    const response = await env.AI.run('@cf/meta/llama-3-8b-instruct', {
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 256,
      temperature: 0.3,
    });

    const keywords = response.response
      .split(/[,，、]/)
      .map(k => k.trim())
      .filter(k => k.length > 0)
      .slice(0, 10);

    return keywords;
  } catch (error) {
    console.error('Keyword extraction failed:', error);
    return [];
  }
}

async function addNoteToIndex(note, env) {
  if (!env.VECTORIZE) {
    throw new Error('Vectorize not configured');
  }

  const textToEmbed = `${note.title}\n\n${note.content}`;
  const embedding = await generateEmbedding(textToEmbed, env);

  await env.VECTORIZE.insert([{
    id: note.note_id,
    values: embedding,
    metadata: {
      title: note.title || '',
      content: note.content || '',
      url: note.url || '',
      author: note.author || '',
    },
  }]);
}

async function addNotesBatch(notes, env) {
  if (!env.VECTORIZE) {
    return { success: false, error: 'Vectorize not configured' };
  }

  const results = [];
  for (const note of notes) {
    try {
      await addNoteToIndex(note, env);
      results.push({ note_id: note.note_id, success: true });
    } catch (error) {
      results.push({ note_id: note.note_id, success: false, error: error.message });
    }
  }

  const successful = results.filter(r => r.success).length;

  return {
    success: successful > 0,
    total: notes.length,
    successful,
    failed: notes.length - successful,
    results,
  };
}

async function crawlXHSNotes(userId, maxNotes = 20, env) {
  const notes = [];
  
  if (!env.BROWSER) {
    return { success: false, error: 'Browser rendering not configured', notes: [] };
  }

  let browser = null;
  
  try {
    console.log(`[爬虫] 开始爬取账号: ${userId}`);
    
    if (!env.BROWSER || typeof env.BROWSER.launch !== 'function') {
      return { success: false, error: 'Browser Rendering API 不可用，请检查配置', notes: [] };
    }
    
    browser = await env.BROWSER.launch();
    
    const page = await browser.newPage();
    
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
    
    await page.setViewport({ width: 1920, height: 1080 });
    
    let cookieString = env.XHS_COOKIE;
    
    if (env.KV_CONFIG) {
      try {
        const kvCookie = await env.KV_CONFIG.get('xhs_cookie');
        if (kvCookie) {
          cookieString = kvCookie;
          console.log('[爬虫] 从KV获取到Cookie');
        }
      } catch (e) {
        console.log('[爬虫] 从KV读取Cookie失败，使用环境变量Cookie');
      }
    }
    
    if (cookieString) {
      const cookies = cookieString.split(';').map(c => {
        const [name, value] = c.split('=').map(s => s.trim());
        return { name, value, domain: '.xiaohongshu.com' };
      }).filter(c => c.name && c.value);
      
      await page.setCookie(...cookies);
      console.log(`[爬虫] 设置了 ${cookies.length} 个Cookie`);
    } else {
      console.log('[爬虫] 警告: 没有可用的Cookie');
    }
    
    const profileUrl = `https://www.xiaohongshu.com/user/profile/${userId}`;
    console.log(`[爬虫] 访问页面: ${profileUrl}`);
    
    await page.goto(profileUrl, { 
      waitUntil: 'networkidle2',
      timeout: 60000 
    });
    
    console.log(`[爬虫] 页面加载完成`);
    
    const pageTitle = await page.title();
    console.log(`[爬虫] 页面标题: ${pageTitle}`);
    
    await new Promise(resolve => setTimeout(resolve, 3000));
    
    await page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight);
    });
    console.log(`[爬虫] 已滚动页面`);
    
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    const result = await page.evaluate((maxNotes, userId) => {
      const selectors = [
        '.note-item',
        '.note-card',
        '[class*="note"]',
        '[class*="card"]',
        '[class*="item"]',
        'article',
        'a[href*="/explore/"]',
      ];
      
      let allItems = [];
      for (const selector of selectors) {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
          if (!allItems.includes(el)) {
            allItems.push(el);
          }
        });
      }
      
      if (allItems.length === 0) {
        const bodyHtml = document.body.innerHTML.substring(0, 2000);
        return { 
          error: 'no note items found', 
          pageTitle: document.title,
          bodyPreview: bodyHtml,
          allElementCount: document.querySelectorAll('*').length
        };
      }
      
      const notes = [];
      
      for (let i = 0; i < allItems.length; i++) {
        if (notes.length >= maxNotes) break;
        
        const item = allItems[i];
        let link = item.querySelector('a');
        
        if (!link && item.tagName === 'A') {
          link = item;
        }
        
        if (!link || !link.href || !link.href.includes('/explore/')) continue;
        
        const href = link.href;
        const noteIdMatch = href.match(/\/explore\/(\w+)/);
        const noteId = noteIdMatch ? noteIdMatch[1] : '';
        
        if (!noteId) continue;
        
        const titleEl = item.querySelector('.title, [class*="title"], .desc, [class*="desc"], .note-title');
        const img = item.querySelector('img');
        
        let title = '';
        let content = '';
        
        if (titleEl) {
          title = titleEl.innerText || titleEl.textContent || '';
          content = titleEl.innerText || titleEl.textContent || '';
        } else {
          const textContent = item.innerText || item.textContent || '';
          if (textContent.length > 0 && textContent.length < 200) {
            title = textContent;
            content = textContent;
          }
        }
        
        const encodeText = (text) => {
          try {
            return btoa(encodeURIComponent(text));
          } catch (e) {
            return '';
          }
        };
        
        notes.push({
          note_id: noteId,
          title: encodeText(title.trim()),
          content: encodeText(content.trim()),
          cover_url: img ? img.src || img.dataset.src || img.getAttribute('src') || '' : '',
          liked_count: 0,
          comment_count: 0,
          share_count: 0,
          user_id: userId,
          author: '',
          url: href,
        });
      }
      
      if (notes.length === 0) {
        const linkElements = document.querySelectorAll('a[href*="/explore/"]');
        const links = Array.from(linkElements).slice(0, 10).map(a => a.href);
        return { 
          error: 'no valid notes extracted',
          foundLinks: links,
          totalElements: allItems.length
        };
      }
      
      return { notes, total: notes.length };
    }, maxNotes, userId);
    
    console.log(`[爬虫] 提取结果: ${JSON.stringify(result)}`);
    
    if (result.error) {
      return { success: false, error: result.error, notes: [], debug: {
        pageTitle: result.pageTitle,
        bodyPreview: result.bodyPreview,
        allElementCount: result.allElementCount,
        foundLinks: result.foundLinks,
        totalElements: result.totalElements
      } };
    }
    
    const decodeText = (encoded) => {
      if (!encoded) return '';
      try {
        return decodeURIComponent(atob(encoded));
      } catch (e) {
        return encoded;
      }
    };
    
    const decodedNotes = result.notes.map(note => ({
      ...note,
      title: decodeText(note.title),
      content: decodeText(note.content),
    }));
    
    notes.push(...decodedNotes);
    
    console.log(`[爬虫] 成功获取 ${notes.length} 篇笔记`);
    console.log(`[爬虫] 第一篇笔记标题: ${notes[0]?.title?.substring(0, 50)}...`);
    
    return { success: true, notes: decodedNotes, total: decodedNotes.length };
    
  } catch (error) {
    console.error('[爬虫] 爬取失败:', error);
    return { success: false, error: error.message, notes: [] };
  } finally {
    if (browser) {
      try {
        await browser.close();
        console.log('[爬虫] 浏览器已关闭');
      } catch (e) {
        console.error('[爬虫] 关闭浏览器失败:', e);
      }
    }
  }
}

async function handleRequest(request, env) {
  if (request.method === 'OPTIONS') {
    return handleOptions(request);
  }

  const url = new URL(request.url);
  const path = url.pathname;

  try {
    if (path === '/' || path === '/index.html') {
      const assetPath = new URL(path === '/' ? '/index.html' : path, request.url);
      const assetResponse = await env.ASSETS.fetch(new Request(assetPath));
      if (assetResponse.ok) {
        return new Response(assetResponse.body, {
          headers: { ...corsHeaders, 'Content-Type': 'text/html; charset=utf-8' },
        });
      }
    }

    if (path === '/api/chat' && request.method === 'POST') {
      const startTime = Date.now();
      const body = await request.json();
      const { query, top_k } = body;

      console.log(`[问答] 收到请求 - query: ${query?.substring(0, 50)}... | top_k: ${top_k}`);

      if (!query) {
        console.log('[问答] 错误: query为空');
        return new Response(JSON.stringify({ error: 'Query is required' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }

      const topK = parseInt(top_k) || parseInt(env.DEFAULT_TOP_K) || 5;
      console.log(`[问答] 开始检索 - topK: ${topK}`);
      
      const sources = await retrieve(query, env, topK);
      console.log(`[问答] 检索完成 - 找到 ${sources.length} 条相关笔记`);
      
      if (sources.length > 0) {
        sources.forEach((src, i) => {
          console.log(`[问答] 来源 ${i+1}: ${src.title?.substring(0, 30)}... (score: ${src.score?.toFixed(4)})`);
        });
      }

      console.log('[问答] 开始生成回答');
      const answer = await generateAnswer(query, sources, env);
      console.log(`[问答] 回答生成完成 - 长度: ${answer?.length || 0}`);

      const duration = Date.now() - startTime;
      console.log(`[问答] 请求完成 - 耗时: ${duration}ms`);

      return new Response(JSON.stringify({
        answer,
        sources,
        total_sources: sources.length,
        duration_ms: duration,
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json; charset=utf-8' },
      });
    }

    if (path === '/api/embed' && request.method === 'POST') {
      const body = await request.json();
      const { text } = body;

      if (!text) {
        return new Response(JSON.stringify({ error: 'Text is required' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }

      const embedding = await generateEmbedding(text, env);

      return new Response(JSON.stringify({
        embedding,
        dimension: embedding ? embedding.length : 0,
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    if (path === '/api/analyze' && request.method === 'POST') {
      const body = await request.json();
      const { text } = body;

      if (!text) {
        return new Response(JSON.stringify({ error: 'Text is required' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }

      const sentiment = await analyzeSentiment(text, env);
      const keywords = await extractKeywords(text, env);

      return new Response(JSON.stringify({
        sentiment,
        keywords,
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    if (path === '/api/notes' && request.method === 'POST') {
      const body = await request.json();
      await addNoteToIndex(body, env);

      return new Response(JSON.stringify({ success: true }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    if (path === '/api/notes/batch' && request.method === 'POST') {
      const body = await request.json();
      const { notes } = body;

      if (!notes || !Array.isArray(notes)) {
        return new Response(JSON.stringify({ error: 'Notes array is required' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }

      const results = [];
      for (const note of notes) {
        try {
          await addNoteToIndex(note, env);
          results.push({ note_id: note.note_id, success: true });
        } catch (error) {
          results.push({ note_id: note.note_id, success: false, error: error.message });
        }
      }

      const successful = results.filter(r => r.success).length;

      return new Response(JSON.stringify({
        success: successful > 0,
        total: notes.length,
        successful,
        failed: notes.length - successful,
        results,
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    if (path === '/api/crawl' && request.method === 'POST') {
      const startTime = Date.now();
      const body = await request.json();
      const { user_id, max_notes } = body;

      console.log(`[爬虫API] 收到请求 - user_id: ${user_id} | max_notes: ${max_notes}`);

      if (!user_id) {
        console.log('[爬虫API] 错误: user_id为空');
        return new Response(JSON.stringify({ error: 'User ID is required' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }

      console.log(`[爬虫API] 开始爬取 - userId: ${user_id}, maxNotes: ${max_notes || 20}`);
      const crawlResult = await crawlXHSNotes(user_id, max_notes || 20, env);
      
      if (crawlResult.success && crawlResult.notes.length > 0) {
        console.log(`[爬虫API] 爬取成功 - 共 ${crawlResult.notes.length} 篇笔记`);
        crawlResult.notes.forEach((note, i) => {
          console.log(`[爬虫API] 笔记 ${i+1}: ${note.title?.substring(0, 30)}...`);
        });
        
        console.log('[爬虫API] 开始导入到Vectorize');
        const importResult = await addNotesBatch(crawlResult.notes, env);
        console.log(`[爬虫API] 导入完成 - 成功: ${importResult.successful}, 失败: ${importResult.failed}`);
        
        const duration = Date.now() - startTime;
        console.log(`[爬虫API] 请求完成 - 耗时: ${duration}ms`);
        
        return new Response(JSON.stringify({
          ...crawlResult,
          import_result: importResult,
          duration_ms: duration,
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json; charset=utf-8' },
        });
      } else {
        console.log(`[爬虫API] 爬取失败或无笔记 - error: ${crawlResult.error}, notes: ${crawlResult.notes?.length || 0}`);
        return new Response(JSON.stringify(crawlResult), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json; charset=utf-8' },
        });
      }
    }

    if (path === '/api/notes/batch-with-embedding' && request.method === 'POST') {
      const body = await request.json();
      const { notes } = body;

      if (!notes || !Array.isArray(notes)) {
        return new Response(JSON.stringify({ error: 'Notes array is required' }), {
          status: 400,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }

      if (!env.VECTORIZE) {
        throw new Error('Vectorize not configured');
      }

      const vectors = notes.map(note => ({
        id: note.note_id,
        values: note.embedding,
        metadata: {
          title: note.title || '',
          content: note.content || '',
          url: note.url || '',
          author: note.author || '',
        },
      }));

      await env.VECTORIZE.insert(vectors);

      return new Response(JSON.stringify({
        success: true,
        total: notes.length,
        successful: notes.length,
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    if (path === '/health') {
      return new Response(JSON.stringify({
        status: 'ok',
        service: 'XHS RAG',
        version: '1.0.0',
        timestamp: new Date().toISOString(),
        has_vectorize: !!env.VECTORIZE,
        has_ai: !!env.AI,
      }), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    // 手动触发Cookie更新和爬取接口
    if (path === '/api/cron/trigger' && request.method === 'POST') {
      const startTime = Date.now();
      console.log('[手动触发] 收到手动触发请求');
      
      try {
        const result = await handleCronEvent(env);
        
        const duration = Date.now() - startTime;
        console.log(`[手动触发] 执行完成 - 耗时: ${duration}ms`);
        
        return new Response(JSON.stringify({
          success: result.success,
          message: result.success ? '定时任务执行成功' : 'Cookie更新失败',
          cookie_result: result,
          duration_ms: duration,
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      } catch (error) {
        console.error('[手动触发] 执行失败:', error);
        return new Response(JSON.stringify({
          success: false,
          error: error.message,
        }), {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
    }
    
    // 仅更新Cookie接口
    if (path === '/api/cookie/update' && request.method === 'POST') {
      console.log('[Cookie更新] 收到手动更新请求');
      
      try {
        const result = await updateCookie(env);
        
        return new Response(JSON.stringify({
          success: result.success,
          message: result.message,
          cookie_length: result.cookie_length,
          updated_at: result.updated_at,
        }), {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      } catch (error) {
        console.error('[Cookie更新] 更新失败:', error);
        return new Response(JSON.stringify({
          success: false,
          error: error.message,
        }), {
          status: 500,
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        });
      }
    }
    
    // 获取当前Cookie状态
    if (path === '/api/cookie/status' && request.method === 'GET') {
      console.log('[Cookie状态] 收到查询请求');
      
      let status = {
        has_env_cookie: !!env.XHS_COOKIE,
        has_kv_cookie: false,
        kv_updated_at: null,
      };
      
      if (env.KV_CONFIG) {
        try {
          const kvCookie = await env.KV_CONFIG.get('xhs_cookie');
          const updatedAt = await env.KV_CONFIG.get('cookie_updated_at');
          status.has_kv_cookie = !!kvCookie;
          status.kv_updated_at = updatedAt;
        } catch (e) {
          console.log('[Cookie状态] KV读取失败:', e.message);
        }
      }
      
      return new Response(JSON.stringify(status), {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      });
    }

    const assetResponse = await env.ASSETS.fetch(request);
    if (assetResponse.ok) {
      return assetResponse;
    }

    return new Response('Not found', {
      status: 404,
      headers: corsHeaders,
    });
  } catch (error) {
    console.error('Request handling error:', error);
    return new Response(JSON.stringify({
      error: error.message,
    }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
}

async function updateCookie(env) {
  console.log('[Cookie更新] 开始自动更新Cookie');
  
  // 方案1: 使用 Browserless.io REST API
  if (env.BROWSERLESS_API_KEY && env.BROWSERLESS_API_KEY !== 'YOUR_BROWSERLESS_API_KEY_HERE') {
    try {
      console.log('[Cookie更新] 使用 Browserless.io REST API');
      
      const response = await fetch(
        `https://chrome.browserless.io/function?token=${env.BROWSERLESS_API_KEY}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            code: `
              await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
              await page.goto('https://www.xiaohongshu.com', { waitUntil: 'networkidle2', timeout: 60000 });
              await new Promise(resolve => setTimeout(resolve, 5000));
              const cookies = await page.cookies();
              JSON.stringify(cookies.map(c => c.name + '=' + c.value).join('; '));
            `,
            gotoOptions: { waitUntil: 'networkidle2' },
          }),
        }
      );
      
      if (response.ok) {
        const cookieString = await response.text();
        console.log(`[Cookie更新] Browserless.io 返回Cookie长度: ${cookieString?.length || 0}`);
        
        if (cookieString && cookieString.length > 10) {
          if (env.KV_CONFIG) {
            await env.KV_CONFIG.put('xhs_cookie', cookieString);
            await env.KV_CONFIG.put('cookie_updated_at', new Date().toISOString());
            console.log('[Cookie更新] 新Cookie已保存到KV');
          }
          
          return {
            success: true,
            cookie_length: cookieString.length,
            updated_at: new Date().toISOString(),
            message: 'Cookie更新成功（Browserless.io）',
            source: 'browserless_rest',
          };
        }
      } else {
        console.log(`[Cookie更新] Browserless.io REST API失败: ${response.status}`);
      }
    } catch (browserlessError) {
      console.error('[Cookie更新] Browserless.io 失败:', browserlessError.message);
    }
  }
  
  // 方案2: 尝试使用 Cloudflare Browser Rendering API
  if (env.BROWSER) {
    try {
      console.log('[Cookie更新] 尝试使用 Cloudflare Browser Rendering API');
      const browser = await env.BROWSER.launch();
      console.log('[Cookie更新] 浏览器启动成功');
      
      const page = await browser.newPage();
      
      await page.setExtraHTTPHeaders({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
      });
      
      console.log('[Cookie更新] 正在访问小红书首页');
      await page.goto('https://www.xiaohongshu.com', {
        waitUntil: 'networkidle2',
        timeout: 60000,
      });
      
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      const cookies = await page.cookies();
      console.log(`[Cookie更新] 获取到 ${cookies.length} 个Cookie`);
      
      const cookieString = cookies.map(c => `${c.name}=${c.value}`).join('; ');
      
      if (cookieString && cookieString.length > 10) {
        if (env.KV_CONFIG) {
          await env.KV_CONFIG.put('xhs_cookie', cookieString);
          await env.KV_CONFIG.put('cookie_updated_at', new Date().toISOString());
          console.log('[Cookie更新] 新Cookie已保存到KV');
        }
        
        console.log(`[Cookie更新] 新Cookie: ${cookieString.substring(0, 100)}...`);
        
        await browser.close();
        
        return {
          success: true,
          cookie_length: cookieString.length,
          updated_at: new Date().toISOString(),
          message: 'Cookie更新成功',
          source: 'cloudflare_browser',
        };
      } else {
        await browser.close();
        console.log('[Cookie更新] 警告: 获取到的Cookie为空或无效');
        return {
          success: false,
          message: '获取到的Cookie为空',
        };
      }
    } catch (browserError) {
      console.error('[Cookie更新] Cloudflare Browser Rendering API 失败:', browserError.message);
    }
  }
  
  // 方案3: 使用环境变量Cookie作为降级方案
  if (env.XHS_COOKIE) {
    try {
      if (env.KV_CONFIG) {
        await env.KV_CONFIG.put('xhs_cookie', env.XHS_COOKIE);
        await env.KV_CONFIG.put('cookie_updated_at', new Date().toISOString());
      }
      
      console.log('[Cookie更新] 已保存环境变量Cookie到KV');
      
      return {
        success: true,
        cookie_length: env.XHS_COOKIE.length,
        updated_at: new Date().toISOString(),
        message: '使用环境变量Cookie',
        source: 'env_variable',
      };
    } catch (e) {
      return {
        success: false,
        message: 'Cookie更新失败: ' + e.message,
      };
    }
  } else {
    return {
      success: false,
      message: '无可用Cookie（环境变量XHS_COOKIE未配置）',
    };
  }
}

async function handleCronEvent(env) {
  console.log('[定时任务] 开始执行定时任务');
  
  let cookieResult = { success: false, message: '未知错误' };
  
  try {
    cookieResult = await updateCookie(env);
    console.log(`[定时任务] Cookie更新结果: ${JSON.stringify(cookieResult)}`);
  } catch (cookieError) {
    console.error('[定时任务] Cookie更新异常:', cookieError);
    cookieResult = { success: false, message: cookieError.message };
  }
  
  if (cookieResult.success) {
    const userIds = ['5bd9405f6b58b737b5401d2e'];
    
    for (const userId of userIds) {
      console.log(`[定时任务] 开始爬取用户 ${userId} 的最新笔记`);
      
      try {
        const crawlResult = await crawlXHSNotes(userId, 5, env);
        
        if (crawlResult.success && crawlResult.notes.length > 0) {
          const importResult = await addNotesBatch(crawlResult.notes, env);
          console.log(`[定时任务] 用户 ${userId} 爬取完成 - 新增 ${importResult.successful} 篇笔记`);
        } else {
          console.log(`[定时任务] 用户 ${userId} 爬取失败或无新笔记`);
        }
      } catch (crawlError) {
        console.error(`[定时任务] 用户 ${userId} 爬取异常:`, crawlError);
      }
    }
  }
  
  console.log('[定时任务] 定时任务执行完毕');
  return cookieResult;
}

export default {
  async fetch(request, env, ctx) {
    return handleRequest(request, env);
  },
  
  async scheduled(event, env, ctx) {
    console.log(`[定时任务] 触发定时任务 - ${event.cron}`);
    await handleCronEvent(env);
  },
};
