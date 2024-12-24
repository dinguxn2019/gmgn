from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import undetected_chromedriver as uc
import json
import time
import random
import logging
import pyperclip
import argparse
from webdriver_manager.chrome import ChromeDriverManager
import signal
import atexit
import sys

# Create a filter to exclude the specific message
class MessageFilter(logging.Filter):
    def filter(self, record):
        return not record.getMessage().startswith('patching driver executable')

# Configure logging with the filter
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
handler.addFilter(MessageFilter())
logger.addHandler(handler)

# Remove any existing handlers (including the default one)
for handler in logger.handlers[:-1]:
    logger.removeHandler(handler)

class CustomChrome(uc.Chrome):
    """
    自定义Chrome类，重写__del__方法以避免退出时的错误
    """
    def __del__(self):
        try:
            self.service.stop()
        except:
            pass
        
def create_driver():
    """
    创建并配置Undetected ChromeDriver，增强反检测能力
    """
    options = uc.ChromeOptions()
    
    # 启用无头模式
    options.add_argument('--headless=new')
    
    # 添加必要的无头模式选项
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--enable-javascript')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # 设置用户代理
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # 性能优化，但保留必要功能
    chrome_prefs = {
        'profile.default_content_setting_values': {
            'images': 1,  # 启用图片加载
            'javascript': 1,  # 启用JavaScript
            'cookies': 1  # 启用cookies
        },
        'profile.managed_default_content_settings': {
            'javascript': 1
        }
    }
    options.add_experimental_option('prefs', chrome_prefs)
    
    try:
        # 使用自定义的Chrome类创建实例
        driver = CustomChrome(options=options)
        return driver
    except Exception as e:
        logging.error(f"创建Chrome驱动失败: {str(e)}")
        raise

def safe_quit_driver(driver):
    """
    安全地关闭Chrome驱动
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
        # 停止service
        driver.service.stop()
    except:
        pass
        
    try:
        # 退出驱动
        driver.quit()
    except:
        pass
        
    # 确保完全清理
    try:
        del driver
    except:
        pass

def random_sleep(min_seconds=1, max_seconds=3):
    """随机延迟函数"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def scroll_to_position(driver, y_position):
    """
    滚动到指定位置并等待
    """
    try:
        # 使用scrollTo而不是scrollBy以确保准确位置
        driver.execute_script(f"window.scrollTo(0, {y_position});")
        # 等待滚动完成
        time.sleep(0.5)
        # 验证滚动位置
        actual_position = driver.execute_script("return window.pageYOffset;")
        #logging.info(f"滚动到位置: {actual_position}")
        return True
    except Exception as e:
        logging.error(f"滚动失败: {str(e)}")
        return False

def scroll_to_element(driver, element):
    """
    滚动到元素位置
    """
    try:
        # 获取元素位置
        element_position = element.location['y']
        # 滚动到元素位置，稍微向上偏移以确保完全可见
        driver.execute_script(f"window.scrollTo(0, {element_position - 100});")
        time.sleep(0.5)
        return True
    except Exception as e:
        logging.error(f"滚动到元素失败: {str(e)}")
        return False

def get_element_text(driver, class_name, max_count, include_children=False):
    """
    获取指定class元素的href值
    :param driver: WebDriver实例
    :param class_name: 目标元素的class名
    :param max_count: 最大获取数量
    :param include_children: 是否包含子元素本
    :return: 提取的地址列表
    """
    try:
        # 等待元素加载
        wait = WebDriverWait(driver, 10)
        elements = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'css-4949n9')))
        
        # 获取指定数量的元素的href值
        addresses = []
        for element in elements[:max_count]:
            try:
                href = element.get_attribute('href')
                if href:
                    # 从href中提取地址部分
                    address = href.split('/sol/address/')[-1]
                    addresses.append(address)
            except Exception as e:
                logging.error(f"提取href时发生错误: {str(e)}")
                continue
                
        return addresses
    except Exception as e:
        logging.error(f"获取元素文本失败: {str(e)}")
        return []

def click_blue_chip_holders_tab(driver):
    """
    等待并点击持有者标签
    """
    try:
        # 等待页面加载完成
        wait = WebDriverWait(driver, 10)
        
        # 检查是否存在模态框，如果存在则尝试关闭
        try:
            modal = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'chakra-modal__content-container')))
            # 尝试点击模态框外部区域来关闭它
            driver.execute_script("arguments[0].parentElement.click();", modal)
            time.sleep(1)  # 等待模态框消失
        except:
            pass  # 如果没有模态框，继续执行
        
        # 等待标签出现并确保可见
        tab = wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'chakra-tabs__tab') and .//div[contains(text(), '持有者')]]")))
        
        # 使用JavaScript点击元素，这样可以避免元素被遮挡的问题
        driver.execute_script("arguments[0].click();", tab)
        #logging.info("成功点击持有者标签")
        
        # 等待内容加载
        time.sleep(4)
        return True
    except Exception as e:
        logging.error(f"点击持有者标签失败: {str(e)}")
        return False

def get_page_info(driver, url, max_count):
    """
    获取单页面的信息
    """
    try:
        #logging.info(f"正在访问: {url}")
        driver.get(url)
        
        # 随机延迟，模拟人类行为
        random_sleep(1, 2)
        
        # 等待页面加载
        wait = WebDriverWait(driver, 30)
        wait.until(lambda d: d.execute_script('return document.readyState') == 'complete')
        
        # 点击蓝筹持有者标签
        if not click_blue_chip_holders_tab(driver):
            #logging.error("点击蓝筹持有者标签失败")
            return None
        
        # 等待目标元素出现
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'css-f8qc29')))
        
        # 获取有钱包地址
        wallet_addresses = get_element_text(driver, 'css-f8qc29', max_count)
        
        page_info = {
            'url': url,
            'wallet_addresses': wallet_addresses or []
        }
        
        return page_info
        
    except Exception as e:
        logging.error(f"获取地址 {url} 信息时发生错误: {str(e)}")
        return None

def print_page_info(page_info):
    """
    打印页面信息
    :param page_info: 页面信息字典
    """
    if not page_info:
        return
    
    # 只输出地址，每行一个
    for address in page_info['wallet_addresses']:
        print(address)

def signal_handler(signum, frame):
    """
    信号处理函数，用于优雅地关闭程序
    """
    logging.info("接收到终止信号，正在关闭程序...")
    if 'driver' in globals():
        safe_quit_driver(globals()['driver'])
    exit(0)

def cleanup():
    """
    清理函数，用于程序正常退出时的清理工作
    """
    if 'driver' in globals():
        safe_quit_driver(globals()['driver'])

def main():
    """
    主函数：运行爬虫程序获取持有者信���
    功能：
    1. 接收命令行参数：代币地址、最大获取数量
    2. 批量处理地址并直接显示结果
    
    使用方法：
    python gmgn_get_url.py -i HxRELUuuoQGD6UUqUxe6qGcsX8wuDKQz9HGqsqEAy7n1 -n 100
    或
    python gmgn_get_url.py --input HxRELUuuoQGD6UUqUxe6qGcsX8wuDKQz9HGqsqEAy7n1 --number 100
    """
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 注册清理函数
    atexit.register(cleanup)
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='获取代币持有者信息的爬虫程序')
    parser.add_argument('-i', '--input', type=str, required=True,
                      help='代币地址')
    parser.add_argument('-n', '--number', type=int, default=100,
                      help='要获取的持有者数量 (默认: 100)')
    
    # 解析命令行参数
    args = parser.parse_args()
    
    base_url = "https://gmgn.ai/sol/token"
    
    # 创建URL
    url = f"{base_url.rstrip('/')}/{args.input.lstrip('/')}"
    
    # 创建一个浏览器实例
    global driver
    driver = None
    try:
        driver = create_driver()
        # 处理URL并获取结果
        result = get_page_info(driver, url, args.number)
        if result:
            print_page_info(result)
    except Exception as e:
        logging.error(f"程序执行出错: {str(e)}")
    finally:
        if driver:
            safe_quit_driver(driver)
            driver = None

if __name__ == "__main__":
    main()
