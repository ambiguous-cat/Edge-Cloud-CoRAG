#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTTP响应测试文件
"""

from http_response_tester import HTTPResponseTester, quick_http_test

def test_single_url():
    """测试单个URL"""
    print("=== 测试单个URL ===")
    
    tester = HTTPResponseTester(timeout=10)
    try:
        result = tester.test_single_url("https://www.baidu.com")
        
        print(f"URL: {result.url}")
        print(f"成功: {result.success}")
        print(f"响应时间: {result.response_time:.2f}ms")
        print(f"状态码: {result.status_code}")
        
        if not result.success:
            print(f"错误信息: {result.error_message}")
            
    finally:
        tester.close()

def test_custom_urls():
    """测试自定义URL列表"""
    print("\n=== 测试自定义URL列表 ===")
    
    # 你可以在这里添加你想要测试的URL
    custom_urls = [
        "https://www.baidu.com",
        "https://www.qq.com",
        "https://www.taobao.com",
        "https://www.jd.com",
        "https://www.github.com",
        "https://www.stackoverflow.com"
    ]
    
    results = quick_http_test(custom_urls, timeout=5)
    
    # 你可以进一步处理结果
    print(f"\n总共测试了 {len(results)} 个URL")


def test_with_retry():
    """测试重试功能"""
    print("\n=== 测试重试功能 ===")
    
    tester = HTTPResponseTester(timeout=5)
    try:
        # 测试一个可能不稳定的网站
        result = tester.test_url_with_retry("https://www.github.com", max_retries=3)
        
        print(f"最终结果:")
        print(f"  URL: {result.url}")
        print(f"  成功: {result.success}")
        print(f"  响应时间: {result.response_time:.2f}ms")
        
    finally:
        tester.close()

def main():
    """主函数"""
    print("HTTP响应测试程序")
    print("=" * 50)
    custom_urls = [
        "https://www.baidu.com",
        "https://www.qq.com",
        "https://www.taobao.com",
        "https://www.jd.com",
        "https://www.github.com",
        "https://www.stackoverflow.com",
        "http://localhost:11434"
    ]
    print(quick_http_test(custom_urls, timeout=10))
    url = "https://www.baidu.com/"
    tester=HTTPResponseTester()
    result = tester.test_single_url(url)
    print(result)
    # try:
    #     # 运行各种测试
    #     test_single_url()
    #     test_custom_urls()
    #     test_with_retry()
    #
    #
    #     print("\n" + "=" * 50)
    #     print("所有测试完成！")
    #
    # except KeyboardInterrupt:
    #     print("\n测试被用户中断")
    # except Exception as e:
    #     print(f"\n测试过程中发生错误: {str(e)}")

if __name__ == "__main__":
    main()
