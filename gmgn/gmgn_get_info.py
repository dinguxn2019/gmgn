from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import undetected_chromedriver as uc
import json
import time
import random
import logging
import gc
from webdriver_manager.chrome import ChromeDriverManager
import csv
import os
import argparse  # 添加argparse模块

# 配置日志
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置 undetected_chromedriver 的日志级别为 WARNING
logging.getLogger('undetected_chromedriver').setLevel(logging.WARNING)
# 设置 selenium 的日志级别为 WARNING
logging.getLogger('selenium').setLevel(logging.WARNING)
# 设置 urllib3 的日志级别为 WARNING
logging.getLogger('urllib3').setLevel(logging.WARNING)

def create_driver():
    """
    创建并配置Undetected ChromeDriver，增强反检测能力
    """
    # 禁用 webdriver manager 的日志
    os.environ['WDM_LOG_LEVEL'] = '0'
    
    options = uc.ChromeOptions()
    
    # 使用新的无头模式
    options.add_argument('--headless=new')
    
    # 添加反检测参数
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--enable-javascript')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-infobars')
    options.add_argument('--disable-notifications')
    options.add_argument('--log-level=3')  # 只显示致命错误
    
    # 使用随机的 user-agent
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 性能优化配置
    chrome_prefs = {
        'profile.default_content_setting_values': {
            'images': 1,
            'javascript': 1,
            'cookies': 1
        },
        'profile.managed_default_content_settings': {
            'javascript': 1
        }
    }
    options.add_experimental_option('prefs', chrome_prefs)
    
    # 创建undetected_chromedriver实例，禁用自动退出
    driver = uc.Chrome(options=options, suppress_welcome=True, log_level=0)
    
    # 修改Chrome类的__del__方法以避免退出时的错误
    def new_del(self):
        try:
            self.quit()
        except:
            pass
    driver.__class__.__del__ = new_del
    
    # 执行额外的反检测JavaScript
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def cleanup_driver(driver):
    """
    安全地清理driver
    """
    if not driver:
        return
        
    try:
        # 关闭所有窗口
        for handle in driver.window_handles[:]:
            try:
                driver.switch_to.window(handle)
                driver.close()
            except:
                pass
    except:
        pass
        
    try:
        # 退出driver
        driver.quit()
    except:
        pass
        
    # 强制设置为None以触发垃圾回收
    driver = None

def random_sleep(min_seconds=1, max_seconds=3):
    """随机延迟函数"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def get_element_text(driver, class_name, include_children=False):
    """
    获取指定class元素的文本
    :param driver: WebDriver实例
    :param class_name: CSS类
    :param include_children: 是否包含子元素文本
    :return: 元素文本或None
    """
    try:
        elements = driver.find_elements(By.CLASS_NAME, class_name)
        if not elements:
            return None
        
        if len(elements) == 1:
            element = elements[0]
            if include_children:
                return element.get_attribute('innerText').strip()
            else:
                # 获取直接文本内容，不包含子元素
                return driver.execute_script("""
                    var element = arguments[0];
                    return Array.from(element.childNodes)
                        .filter(node => node.nodeType === 3)
                        .map(node => node.textContent.trim())
                        .join(' ');
                """, element).strip()
        
        # 果有多个元素，返回列表
        if include_children:
            return [element.get_attribute('innerText').strip() for element in elements]
        else:
            return [driver.execute_script("""
                var element = arguments[0];
                return Array.from(element.childNodes)
                    .filter(node => node.nodeType === 3)
                    .map(node => node.textContent.trim())
                    .join(' ');
            """, element).strip() for element in elements]
    except:
        return None

def get_page_info(driver, url, original_address):
    """
    获取单个页面的信息
    """
    try:
        #logging.info(f"正在访问: {url}")
        driver.get(url)
        
        # 随机延迟，模拟人类行为
        random_sleep(1, 2)
        
        # 等待页面加载
        wait = WebDriverWait(driver, 30)
        wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
        
        # 模拟人类滚动行为
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        random_sleep(1, 2)
        
        # 等待关键元素出现
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'css-6hgaua')))
        
        # 获取基本信息
        page_info = {
            'url': url,
            'address': original_address,  # 添加原始地址
            'recent_7d_profit': {
                'percentage': get_element_text(driver, 'css-18pbzhy') or "/",
                'amount': get_element_text(driver, 'css-vi0yzx') or "/"
            },
            'win_rate': get_element_text(driver, 'css-3h278t') or "/",
            'total_trades': {
                'current': get_element_text(driver, 'css-131utnt') or "/",
                'target': get_element_text(driver, 'css-159dfc2') or "/",
            },
            'total_profit_loss': get_element_text(driver, 'css-1pjn4fe', True) or "/",
            'unrealized_profit': get_element_text(driver, 'css-1ki3vv4') or "/",
            'buy_cost': {
                'total': get_element_text(driver, 'css-13k40wa') or "/",
                'average': get_element_text(driver, 'css-13k40wa', True) or "/",
            },
            'avg_realized_profit': get_element_text(driver, 'css-1pjn4fe', True) or "/",
            'token_balance': (get_element_text(driver, 'css-qq3v8v', True) or "/").replace('\n', ''),
        }
        
        return page_info
        
    except Exception as e:
        logging.error(f"获取地址 {url} 信息时发生错误: {str(e)}")
        return None

def read_addresses_from_file(filename):
    """
    从文件中读取地址列表
    :param filename: 地址文件名
    :return: 地址列表
    """
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            # 读取所有行，去除空白字符，并过滤掉空行
            addresses = [line.strip() for line in file if line.strip()]
        return addresses
    except FileNotFoundError:
        print(f"错误: 找不到文件 '{filename}'")
        return []
    except Exception as e:
        print(f"读取文件时发生错误: {str(e)}")
        return []

def print_page_info(page_info):
    """
    打印页面信息，使用友好的中文格式
    :param page_info: 页面信息字典
    """
    if not page_info:
        return
    
    # 输出CSV格式的数据，用于后续处理
    csv_line = f"{page_info['address']},{page_info['win_rate']},{page_info['total_trades']['current']}/{page_info['total_trades']['target']},{page_info['recent_7d_profit']['percentage']} ({page_info['recent_7d_profit']['amount']}),{page_info['token_balance']}"
    print(csv_line)

def process_batch(driver, urls, addresses):
    """
    处理一批URL，每处理一个地址就立即显示结果
    """
    results = []
    for url, address in zip(urls, addresses):
        #print(f"\n正在获取地址 {address} 的信息...")
        result = get_page_info(driver, url, address)
        if result:
            results.append(result)
            print_page_info(result)
        else:
            print(f"获取地址 {address} 的信息失败")
        random_sleep(1, 2)  # 在请求之间添加随机延迟
    
    return results

def save_to_csv(results, filename='results.csv', max_retries=3):
    """
    保存结果到CSV文件，带有重试机制
    """
    for attempt in range(max_retries):
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:  # 使用 utf-8-sig 添加 BOM
                writer = csv.writer(f)
                writer.writerow(['钱包地址', '胜率', '7D交易数', '最近7D盈亏', 'SOL余额'])
                for result in results:
                    writer.writerow([
                        result['address'],
                        result['win_rate'],
                        f"{result['total_trades']['current']}/{result['total_trades']['target']}",
                        f"{result['recent_7d_profit']['percentage']} ({result['recent_7d_profit']['amount']})",
                        result['token_balance']
                    ])
            #logging.info(f"结果已成功保存到 {filename}")
            return True
        except PermissionError:
            if attempt < max_retries - 1:
                error_msg = f"尝试 {attempt + 1}/{max_retries}: 文件被占用，等待重试..."
                logging.warning(error_msg)
                print(f"\n{error_msg}")
                print("请关闭已打开的 results.csv 文件后按回车键继续...")
                input()
            else:
                alternative_filename = f'results_{int(time.time())}.csv'
                logging.warning(f"无法写入 {filename}，尝试使用替代文件名: {alternative_filename}")
                return save_to_csv(results, alternative_filename, 1)
        except Exception as e:
            logging.error(f"保存文件时发生错误: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return False
    return False

def main():
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(description='获取GMGN地址信息')
    parser.add_argument('-i', '--input', type=str, nargs='+', required=True, help='���查询的钱包地址，可输入多个地址，以空格分隔')
    args = parser.parse_args()
    
    base_url = "https://gmgn.ai/sol/address"
    
    # 使用命令行参数中的地址列表
    address_list = args.input
    
    if not address_list:
        logging.error("没有提供有效的地址，程序退出")
        return
    
    # 将地址列表转换为URL列表
    urls = [f"{base_url.rstrip('/')}/{address.lstrip('/')}" for address in address_list]
    
    # 创建一个浏览器实例
    driver = None
    try:
        driver = create_driver()
        # 存所有结果
        all_results = []
        
        # 每次处理2个URL（减少批量大小，降低被检测风险）
        batch_size = 2
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i + batch_size]
            batch_addresses = address_list[i:i + batch_size]
            #print(f"\n正在处理第 {i//batch_size + 1} 批地址...")
            
            # 处理这一批URL
            batch_results = process_batch(driver, batch_urls, batch_addresses)
            all_results.extend(batch_results)
        
        # 输出结果到CSV文件
        if not save_to_csv(all_results):
            logging.error("保存结果失败")
    
    except Exception as e:
        logging.error(f"程序执行出错: {str(e)}")
    finally:
        cleanup_driver(driver)
        gc.collect()  # 强制垃圾回收
        
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
    finally:
        # 确保所有资源都被清理
        gc.collect()
