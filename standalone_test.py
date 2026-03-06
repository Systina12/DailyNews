"""
独立测试脚本 - 不依赖项目其他模块

直接测试邮件 HTML 生成功能
"""

from datetime import datetime


def build_alert_email(important_news, threshold):
    """构建重要新闻提醒邮件的 HTML（独立版本）"""
    html_parts = []
    
    html_parts.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }
        .header { background-color: #d32f2f; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .news-item { border-left: 4px solid #d32f2f; padding: 15px; margin-bottom: 15px; background-color: #fff3f3; }
        .score { display: inline-block; background-color: #d32f2f; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold; }
        .category { display: inline-block; background-color: #666; color: white; padding: 3px 8px; border-radius: 3px; margin-left: 5px; }
        .title { font-size: 16px; font-weight: bold; margin: 10px 0; color: #333; }
        .summary { color: #666; margin: 10px 0; line-height: 1.5; }
        .link { color: #1976d2; text-decoration: none; }
        .footer { margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>🚨 重要新闻提醒</h2>
            <p>检测到 """ + str(len(important_news)) + """ 条重要性评分 ≥""" + str(threshold) + """ 的新闻</p>
        </div>
""")
    
    # 按评分排序
    sorted_news = sorted(important_news, key=lambda x: x["score"], reverse=True)
    
    for news in sorted_news:
        # 转义HTML特殊字符
        title = news['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        summary = news['summary'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        link = news['link'].replace('&', '&amp;').replace('"', '&quot;')
        
        html_parts.append(f"""
        <div class="news-item">
            <div>
                <span class="score">{news['score']}分</span>
                <span class="category">{news['category']}</span>
            </div>
            <div class="title">{title}</div>
            <div class="summary">{summary}</div>
            <div><a class="link" href="{link}" target="_blank">查看原文 →</a></div>
        </div>
""")
    
    html_parts.append("""
        <div class="footer">
            <p>此邮件由 DailyNews 实时监控系统自动发送</p>
            <p>生成时间: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        </div>
    </div>
</body>
</html>
""")
    
    return ''.join(html_parts)


def main():
    print("=" * 60)
    print("独立测试 - 邮件 HTML 生成")
    print("=" * 60)
    
    # 模拟高分新闻
    important_news = [
        {
            "category": "头条",
            "score": 95,
            "title": "巴基斯坦宣布与阿富汗进入公开战争状态并对喀布尔发动空袭",
            "link": "https://example.com/news/1",
            "summary": "巴基斯坦政府宣布与阿富汗塔利班政权进入公开战争状态，并对喀布尔多个军事目标发动空袭。这是两国关系急剧恶化的最新标志。",
        },
        {
            "category": "国际",
            "score": 88,
            "title": "乌克兰向距离边境800公里的俄罗斯地区发射了新型导弹",
            "link": "https://example.com/news/2",
            "summary": "乌克兰军方使用新型远程导弹对俄罗斯境内目标实施打击，这是战争升级的重要信号。",
        },
        {
            "category": "财经",
            "score": 82,
            "title": "美国总统宣布对中国实施新一轮关税制裁",
            "link": "https://example.com/news/3",
            "summary": "美国政府宣布对价值500亿美元的中国商品加征25%关税，贸易战进一步升级。",
        },
        {
            "category": "头条",
            "score": 81,
            "title": "日本发生7.5级地震，已造成至少50人死亡",
            "link": "https://example.com/news/4",
            "summary": "日本东北部发生强烈地震，多栋建筑倒塌，救援工作正在进行中。",
        },
    ]
    
    print(f"\n生成邮件 HTML...")
    print(f"  模拟新闻: {len(important_news)} 条")
    print(f"  阈值: 80 分")
    
    try:
        html = build_alert_email(important_news, threshold=80)
        
        print(f"\n✓ HTML 生成成功")
        print(f"  长度: {len(html)} 字符")
        
        # 保存到文件
        output_file = "test_alert_email.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        
        print(f"  已保存: {output_file}")
        
        # 显示新闻列表
        print(f"\n新闻列表（按评分排序）：")
        print("-" * 60)
        for news in sorted(important_news, key=lambda x: x["score"], reverse=True):
            print(f"  [{news['score']}分] [{news['category']}] {news['title'][:40]}...")
        print("-" * 60)
        
        print(f"\n✓ 测试完成！")
        print(f"\n下一步：")
        print(f"  1. 用浏览器打开 {output_file} 查看邮件效果")
        print(f"  2. 检查邮件格式是否正确")
        print(f"  3. 检查评分、分类、标题、摘要是否显示正确")
        print(f"  4. 检查样式是否美观（红色警告风格）")
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
