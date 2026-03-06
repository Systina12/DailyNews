"""
实时监控吹哨功能测试工具

功能：
1. 模拟新闻数据（包含高分和低分新闻）
2. 测试 LLM 评分功能
3. 测试邮件生成和发送
4. 支持降低阈值测试
"""

import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflows.main_workflow import _build_alert_email
from utils.email_sender import send_html_email
from utils.logger import get_logger

logger = get_logger("test_realtime_alert")


# 模拟新闻数据
MOCK_NEWS = [
    {
        "title": "巴基斯坦宣布与阿富汗进入公开战争状态并对喀布尔发动空袭",
        "link": "https://example.com/news/1",
        "summaryText": "巴基斯坦政府宣布与阿富汗塔利班政权进入公开战争状态，并对喀布尔多个军事目标发动空袭。这是两国关系急剧恶化的最新标志。",
        "published": "2026-03-06T10:00:00Z",
    },
    {
        "title": "乌克兰向距离边境800公里的俄罗斯地区发射了新型导弹",
        "link": "https://example.com/news/2",
        "summaryText": "乌克兰军方使用新型远程导弹对俄罗斯境内目标实施打击，这是战争升级的重要信号。",
        "published": "2026-03-06T09:30:00Z",
    },
    {
        "title": "美国总统宣布对中国实施新一轮关税制裁",
        "link": "https://example.com/news/3",
        "summaryText": "美国政府宣布对价值500亿美元的中国商品加征25%关税，贸易战进一步升级。",
        "published": "2026-03-06T09:00:00Z",
    },
    {
        "title": "日本发生7.5级地震，已造成至少50人死亡",
        "link": "https://example.com/news/4",
        "summaryText": "日本东北部发生强烈地震，多栋建筑倒塌，救援工作正在进行中。",
        "published": "2026-03-06T08:30:00Z",
    },
    {
        "title": "俄罗斯一动物园在节日后对老虎实施间歇性禁食",
        "link": "https://example.com/news/5",
        "summaryText": "为了老虎的健康，动物园决定在节日后实施间歇性禁食计划。",
        "published": "2026-03-06T08:00:00Z",
    },
    {
        "title": "一名俄罗斯女性在接受美容程序后展示布满伤口的面部",
        "link": "https://example.com/news/6",
        "summaryText": "一名女性在社交媒体上分享了她接受美容程序后的照片，引发关注。",
        "published": "2026-03-06T07:30:00Z",
    },
]


def test_llm_scoring():
    """测试 LLM 评分功能"""
    print("\n" + "=" * 60)
    print("测试 1: LLM 评分功能")
    print("=" * 60)
    
    try:
        from llms.llms import LLMClient
        from workflows.news_pipeline import score_news_importance
        
        llm_client = LLMClient()
        
        print(f"\n评分 {len(MOCK_NEWS)} 条模拟新闻...")
        items_with_scores = score_news_importance(MOCK_NEWS, llm_client)
        
        print("\n评分结果：")
        print("-" * 60)
        for item, score in sorted(items_with_scores, key=lambda x: x[1], reverse=True):
            title = item['title'][:50]
            print(f"  [{score:3d}分] {title}")
        print("-" * 60)
        
        # 统计
        high_scores = [s for _, s in items_with_scores if s >= 80]
        medium_scores = [s for _, s in items_with_scores if 60 <= s < 80]
        low_scores = [s for _, s in items_with_scores if s < 60]
        
        print(f"\n统计：")
        print(f"  高分 (≥80): {len(high_scores)} 条")
        print(f"  中分 (60-79): {len(medium_scores)} 条")
        print(f"  低分 (<60): {len(low_scores)} 条")
        
        print("\n✓ LLM 评分测试通过")
        return items_with_scores
        
    except Exception as e:
        print(f"\n✗ LLM 评分测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_email_generation(threshold=80):
    """测试邮件生成功能"""
    print("\n" + "=" * 60)
    print(f"测试 2: 邮件生成功能（阈值={threshold}）")
    print("=" * 60)
    
    # 模拟高分新闻
    important_news = [
        {
            "category": "头条",
            "score": 95,
            "title": "巴基斯坦宣布与阿富汗进入公开战争状态并对喀布尔发动空袭",
            "link": "https://example.com/news/1",
            "summary": "巴基斯坦政府宣布与阿富汗塔利班政权进入公开战争状态，并对喀布尔多个军事目标发动空袭。",
            "published": "2026-03-06T10:00:00Z",
        },
        {
            "category": "国际",
            "score": 85,
            "title": "乌克兰向距离边境800公里的俄罗斯地区发射了新型导弹",
            "link": "https://example.com/news/2",
            "summary": "乌克兰军方使用新型远程导弹对俄罗斯境内目标实施打击，这是战争升级的重要信号。",
            "published": "2026-03-06T09:30:00Z",
        },
        {
            "category": "财经",
            "score": 82,
            "title": "美国总统宣布对中国实施新一轮关税制裁",
            "link": "https://example.com/news/3",
            "summary": "美国政府宣布对价值500亿美元的中国商品加征25%关税，贸易战进一步升级。",
            "published": "2026-03-06T09:00:00Z",
        },
    ]
    
    try:
        html = _build_alert_email(important_news, threshold)
        
        print(f"\n邮件生成成功：")
        print(f"  HTML 长度: {len(html)} 字符")
        print(f"  包含新闻: {len(important_news)} 条")
        
        # 保存到文件
        output_file = "test_alert_email.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        
        print(f"  已保存到: {output_file}")
        print(f"\n提示: 用浏览器打开 {output_file} 查看邮件效果")
        
        print("\n✓ 邮件生成测试通过")
        return html
        
    except Exception as e:
        print(f"\n✗ 邮件生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_email_sending(html_body, test_mode=True):
    """测试邮件发送功能"""
    print("\n" + "=" * 60)
    print(f"测试 3: 邮件发送功能（test_mode={test_mode}）")
    print("=" * 60)
    
    try:
        subject = f"🚨 重要新闻提醒测试 ({datetime.now().strftime('%H:%M')}) - 3条"
        
        print(f"\n发送测试邮件...")
        print(f"  主题: {subject}")
        print(f"  测试模式: {test_mode}")
        
        send_html_email(subject=subject, html_body=html_body, test_mode=test_mode)
        
        print(f"\n✓ 邮件发送测试通过")
        if test_mode:
            print(f"  提示: 检查 TEST_EMAIL 邮箱")
        else:
            print(f"  提示: 检查 SMTP_TO 邮箱")
        
        return True
        
    except Exception as e:
        print(f"\n✗ 邮件发送测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_with_real_news(threshold=80, test_mode=True):
    """使用真实新闻测试（降低阈值）"""
    print("\n" + "=" * 60)
    print(f"测试 4: 真实新闻测试（阈值={threshold}）")
    print("=" * 60)
    
    try:
        from workflows.main_workflow import run_realtime_workflow
        
        print(f"\n运行实时监控工作流...")
        print(f"  时间范围: 最近 1 小时")
        print(f"  阈值: {threshold} 分")
        print(f"  测试模式: {test_mode}")
        
        result = run_realtime_workflow(
            categories=["头条", "国际"],  # 只测试部分分类
            hours=1,
            importance_threshold=threshold,
            test=test_mode
        )
        
        important_news = result.get("important_news", [])
        
        print(f"\n结果：")
        print(f"  发现重要新闻: {len(important_news)} 条")
        
        if important_news:
            print(f"\n重要新闻列表：")
            for news in important_news:
                print(f"  [{news['score']}分] [{news['category']}] {news['title'][:50]}")
        else:
            print(f"\n  未发现重要新闻（可能需要降低阈值）")
        
        print("\n✓ 真实新闻测试完成")
        return result
        
    except Exception as e:
        print(f"\n✗ 真实新闻测试失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("实时监控吹哨功能 - 完整测试")
    print("=" * 60)
    
    import argparse
    parser = argparse.ArgumentParser(description="测试实时监控吹哨功能")
    parser.add_argument(
        "--mode",
        type=str,
        default="mock",
        choices=["mock", "real", "all"],
        help="测试模式：mock=模拟数据，real=真实新闻，all=全部测试"
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=50,
        help="真实新闻测试的阈值（默认50，降低以便测试）"
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="是否发送测试邮件（需要配置 SMTP）"
    )
    parser.add_argument(
        "--no-test-mode",
        action="store_true",
        help="发送到正式邮箱（默认发送到 TEST_EMAIL）"
    )
    
    args = parser.parse_args()
    test_mode = not args.no_test_mode
    
    results = {
        "llm_scoring": False,
        "email_generation": False,
        "email_sending": False,
        "real_news": False,
    }
    
    # 测试 1: LLM 评分（模拟数据）
    if args.mode in ["mock", "all"]:
        items_with_scores = test_llm_scoring()
        results["llm_scoring"] = items_with_scores is not None
    
    # 测试 2: 邮件生成
    if args.mode in ["mock", "all"]:
        html = test_email_generation(threshold=80)
        results["email_generation"] = html is not None
        
        # 测试 3: 邮件发送（可选）
        if args.send_email and html:
            results["email_sending"] = test_email_sending(html, test_mode=test_mode)
    
    # 测试 4: 真实新闻（降低阈值）
    if args.mode in ["real", "all"]:
        result = test_with_real_news(threshold=args.threshold, test_mode=test_mode)
        results["real_news"] = result is not None
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for test_name, passed in results.items():
        if passed is not None:
            status = "✓ 通过" if passed else "✗ 失败"
            print(f"  {test_name:20s}: {status}")
    
    all_passed = all(v for v in results.values() if v is not None)
    
    if all_passed:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠ 部分测试失败，请检查日志")
    
    print("\n使用提示：")
    print("  1. 模拟数据测试（快速）：")
    print("     python test_realtime_alert.py --mode=mock")
    print("\n  2. 真实新闻测试（降低阈值）：")
    print("     python test_realtime_alert.py --mode=real --threshold=50")
    print("\n  3. 发送测试邮件：")
    print("     python test_realtime_alert.py --mode=mock --send-email")
    print("\n  4. 完整测试：")
    print("     python test_realtime_alert.py --mode=all --threshold=50 --send-email")
    print("\n  5. 发送到正式邮箱：")
    print("     python test_realtime_alert.py --mode=mock --send-email --no-test-mode")


if __name__ == "__main__":
    main()
