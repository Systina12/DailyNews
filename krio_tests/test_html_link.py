"""
测试HTML链接生成
"""

# 模拟新闻数据
news = {
    "score": 95,
    "category": "头条",
    "title": "测试新闻标题",
    "summary": "这是一条测试新闻的摘要内容。",
    "link": "https://www.example.com/news/test"
}

# 生成HTML
title = news.get('title', '无标题').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
summary = news.get('summary', '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
link = news.get('link', '#')

# 确保链接不为空
if not link or link.strip() == '':
    link = '#'

# 转义链接中的特殊字符
link = link.replace('&', '&amp;').replace('"', '&quot;')

html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .news-item {{ border: 1px solid #ddd; padding: 15px; margin: 10px; }}
        .link {{ color: #1976d2; text-decoration: none; }}
        .link:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>HTML链接测试</h1>
    
    <div class="news-item">
        <div><strong>{news['score']}分</strong> [{news['category']}]</div>
        <div><strong>标题：</strong>{title}</div>
        <div><strong>摘要：</strong>{summary}</div>
        <div><strong>链接：</strong><a class="link" href="{link}" target="_blank">查看原文 →</a></div>
    </div>
    
    <hr>
    
    <h2>调试信息</h2>
    <pre>
原始链接: {news.get('link', 'None')}
处理后链接: {link}
HTML代码: &lt;a href="{link}" target="_blank"&gt;查看原文 →&lt;/a&gt;
    </pre>
    
    <h2>测试链接</h2>
    <p>直接链接测试：<a href="https://www.example.com" target="_blank">点击这里</a></p>
    <p>变量链接测试：<a href="{link}" target="_blank">点击这里</a></p>
</body>
</html>
"""

# 保存文件
with open("test_html_link.html", "w", encoding="utf-8") as f:
    f.write(html)

print("=" * 60)
print("HTML链接测试")
print("=" * 60)
print(f"\n原始链接: {news.get('link', 'None')}")
print(f"处理后链接: {link}")
print(f"\nHTML已保存到: test_html_link.html")
print("\n请用浏览器打开 test_html_link.html 并检查：")
print("1. '查看原文 →' 是否为蓝色")
print("2. 鼠标悬停时是否显示链接")
print("3. 点击是否能打开链接")
print("4. 对比'直接链接测试'和'变量链接测试'")
