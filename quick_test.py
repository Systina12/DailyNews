"""
快速测试脚本 - 不需要真实新闻

测试内容：
1. 邮件 HTML 生成
2. 邮件发送（可选）
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from workflows.main_workflow import _build_alert_email
from utils.email_sender import send_html_email


def main():
    print("=" * 60)
    print("快速测试 - 实时监控吹哨功能")
    print("=" * 60)
    
    # 模拟高分新闻
    important_news = [
        {
            "category": "头条",
            "score": 95,
            "title": "巴基斯坦宣布与阿富汗进入公开战争状态并对喀布尔发动空袭",
            "link": "https://example.com/news/1",
            "summary": "巴基斯坦政府宣布与阿富汗塔利班政权进入公开战争状态，并对喀布尔多个军事目标发动空袭。这是两国关系急剧恶化的最新标志。",
            "published": "2026-03-06T10:00:00Z",
        },
        {
            "category": "国际",
            "score": 88,
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
    
    print(f"\n步骤 1: 生成邮件 HTML")
    print("-" * 60)
    
    try:
        html = _build_alert_email(important_news, threshold=80)
        print(f"✓ HTML 生成成功")
        print(f"  长度: {len(html)} 字符")
        print(f"  新闻数: {len(important_news)} 条")
        
        # 保存到文件
        output_file = "test_alert_email.html"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  已保存: {output_file}")
        
    except Exception as e:
        print(f"✗ HTML 生成失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n步骤 2: 发送测试邮件（可选）")
    print("-" * 60)
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="发送测试邮件")
    parser.add_argument("--no-test-mode", action="store_true", help="发送到正式邮箱")
    args = parser.parse_args()
    
    if args.send:
        try:
            test_mode = not args.no_test_mode
            subject = f"🚨 重要新闻提醒测试 ({datetime.now().strftime('%H:%M')}) - {len(important_news)}条"
            
            print(f"发送邮件...")
            print(f"  主题: {subject}")
            print(f"  测试模式: {test_mode}")
            
            send_html_email(subject=subject, html_body=html, test_mode=test_mode)
            
            print(f"✓ 邮件发送成功")
            if test_mode:
                print(f"  提示: 检查 TEST_EMAIL 邮箱")
            else:
                print(f"  提示: 检查 SMTP_TO 邮箱")
                
        except Exception as e:
            print(f"✗ 邮件发送失败: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("跳过邮件发送（使用 --send 参数发送）")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    print("\n查看邮件效果：")
    print(f"  用浏览器打开: {output_file}")
    
    print("\n发送测试邮件：")
    print(f"  python quick_test.py --send              # 发送到 TEST_EMAIL")
    print(f"  python quick_test.py --send --no-test-mode  # 发送到 SMTP_TO")


if __name__ == "__main__":
    main()
