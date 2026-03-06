"""
诊断吹哨功能中链接丢失的问题
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingestion.RSSclient import RSSClient
from workflows.news_pipeline import run_news_pipeline_all
from llms.llms import LLMClient
from workflows.news_pipeline import score_news_importance
from utils.logger import get_logger

logger = get_logger("diagnose_whistle")


def diagnose_link_flow():
    """诊断链接在整个流程中的传递情况"""
    
    print("=" * 80)
    print("诊断吹哨功能链接传递流程")
    print("=" * 80)
    
    # 1. 检查 RSS 原始数据
    print("\n[步骤1] 检查 RSS 原始数据...")
    try:
        client = RSSClient()
        raw_data = client.get_news(hours=1)
        items = raw_data.get("items", [])
        
        if not items:
            print("❌ 没有获取到新闻数据")
            return
        
        print(f"✓ 获取到 {len(items)} 条新闻")
        
        # 检查前3条的链接
        print("\n检查前3条新闻的链接字段：")
        for i, item in enumerate(items[:3], 1):
            title = item.get("title", "")[:50]
            
            # 检查所有可能的链接字段
            link_fields = {
                "link": item.get("link"),
                "canonical": item.get("canonical"),
                "alternate": item.get("alternate"),
                "origin": item.get("origin"),
            }
            
            print(f"\n  新闻 {i}: {title}")
            for field, value in link_fields.items():
                if value:
                    print(f"    {field}: {value[:80]}")
                else:
                    print(f"    {field}: (空)")
            
            # 检查 canonical 数组
            if "canonical" in item and isinstance(item["canonical"], list):
                print(f"    canonical 是数组，长度: {len(item['canonical'])}")
                for j, c in enumerate(item["canonical"][:2]):
                    if isinstance(c, dict):
                        print(f"      [{j}] href: {c.get('href', '(无)')[:80]}")
    
    except Exception as e:
        print(f"❌ RSS 数据获取失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 2. 检查预处理后的数据
    print("\n" + "=" * 80)
    print("[步骤2] 检查预处理和分类后的数据...")
    try:
        blocks = run_news_pipeline_all(categories=["头条"], hours=1)
        
        if not blocks:
            print("❌ 没有分类数据")
            return
        
        block = blocks[0]
        items = block.get("items", [])
        
        if not items:
            print("❌ 分类后没有新闻")
            return
        
        print(f"✓ 分类后有 {len(items)} 条新闻")
        
        # 检查前3条的链接
        print("\n检查前3条新闻的链接字段：")
        for i, item in enumerate(items[:3], 1):
            title = item.get("title", "")[:50]
            link = item.get("link", "")
            
            print(f"\n  新闻 {i}: {title}")
            print(f"    link: {link[:80] if link else '(空)'}")
            
            # 检查其他可能的字段
            for field in ["canonical", "alternate", "origin"]:
                if field in item:
                    print(f"    {field}: {str(item[field])[:80]}")
    
    except Exception as e:
        print(f"❌ 预处理失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 检查评分后的数据
    print("\n" + "=" * 80)
    print("[步骤3] 检查 LLM 评分后的数据...")
    try:
        llm_client = LLMClient()
        items_with_scores = score_news_importance(items[:5], llm_client)  # 只测试前5条
        
        print(f"✓ 评分完成，共 {len(items_with_scores)} 条")
        
        # 检查评分后链接是否保留
        print("\n检查评分后的链接：")
        for i, (item, score) in enumerate(items_with_scores[:3], 1):
            title = item.get("title", "")[:50]
            link = item.get("link", "")
            
            print(f"\n  新闻 {i} (评分: {score}): {title}")
            print(f"    link: {link[:80] if link else '(空)'}")
    
    except Exception as e:
        print(f"❌ 评分失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 4. 模拟构建邮件
    print("\n" + "=" * 80)
    print("[步骤4] 模拟构建邮件 HTML...")
    
    # 筛选高分新闻
    important_news = []
    for item, score in items_with_scores:
        if score >= 70:  # 降低阈值以便测试
            title = item.get("title", "")
            link = item.get("link", "")
            
            important_news.append({
                "category": "头条",
                "score": score,
                "title": title,
                "original_title": title,
                "link": link,
                "summary": item.get("summaryText", "")[:100],
                "published": item.get("published", ""),
            })
            
            print(f"\n  高分新闻 ({score}分): {title[:50]}")
            print(f"    link: {link[:80] if link else '(空)'}")
    
    if not important_news:
        print("\n⚠ 没有高分新闻（≥70分），无法测试邮件构建")
        return
    
    # 构建邮件 HTML
    print(f"\n✓ 找到 {len(important_news)} 条高分新闻，构建邮件...")
    
    from workflows.main_workflow import _build_alert_email
    html = _build_alert_email(important_news, 70)
    
    # 检查 HTML 中的链接
    print("\n检查生成的 HTML 中的链接：")
    import re
    links = re.findall(r'href="([^"]+)"', html)
    
    print(f"  找到 {len(links)} 个链接")
    for i, link in enumerate(links[:5], 1):
        print(f"    [{i}] {link[:80]}")
    
    # 保存 HTML 用于检查
    output_path = "test_whistle_email.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n✓ HTML 已保存到: {output_path}")
    
    print("\n" + "=" * 80)
    print("诊断完成！")
    print("=" * 80)


if __name__ == "__main__":
    diagnose_link_flow()
