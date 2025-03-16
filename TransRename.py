import os
import re
import hashlib
import random
import requests
import json
import time
from collections import OrderedDict
from getpass import getpass
from hmac import HMAC
from hashlib import sha256

try:
    from tqdm import tqdm
except ImportError:
    print("错误：缺少进度条依赖，请执行安装命令：pip install tqdm")
    exit(1)

# 配置常量
# 在文件开头添加资源路径处理
import sys
import os

def resource_path(relative_path):
    """ 获取打包后的资源绝对路径"""
    # 使用 getattr 安全访问属性
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

# 修改配置文件路径获取方式
CONFIG_DIR = os.path.join(os.path.expanduser('~'), '.config', 'multi_translate')
if getattr(sys, 'frozen', False):
    CONFIG_DIR = resource_path('config')
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.json')
SUPPORTED_APIS = OrderedDict([
    ('baidu', '百度翻译'),
    ('tencent', '腾讯翻译')
])
SUPPORTED_LANGUAGES = [
    ("自动检测", "auto"),
    ("中文", "zh"),
    ("英语", "en"),
    ("日语", "jp"),
    ("韩语", "kor"),
    ("法语", "fra"),
    ("西班牙语", "spa"),
    ("俄语", "ru"),
    ("德语", "de"),
    ("意大利语", "it"),
    ("葡萄牙语", "pt"),
    ("阿拉伯语", "ara"),
    ("泰语", "th"),
    ("越南语", "vie")
]
CHUNK_SIZE = 1000


class ConfigManager:
    @staticmethod
    def load_config():
        """加载配置文件，不存在时创建默认配置"""
        default_config = {
            'current_api': 'baidu',
            'apis': {
                'baidu': {'appid': '', 'appkey': ''},
                'tencent': {'secret_id': '', 'secret_key': ''}
            }
        }
        
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            if not os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2)
                return default_config
                
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 配置加载失败: {str(e)}")
            return default_config

    @staticmethod
    def save_config(config):
        """保存配置到文件"""
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            return True
        except IOError as e:
            print(f"❌ 配置保存失败: {str(e)}")
            return False

    @staticmethod
    def update_api_config(api_type):
        """更新指定API配置（修复输入卡顿问题）"""
        config = ConfigManager.load_config()
        print(f"\n=== 配置{SUPPORTED_APIS[api_type]}参数 ===")
        print("（输入'exit'可返回主菜单）")

        try:
            if api_type == 'baidu':
                # APP ID输入
                print("\n[步骤1/2] 百度翻译APP ID")
                while True:
                    appid = input("请输入APP ID（至少5位字符）：").strip()
                    if appid.lower() == 'exit':
                        return config
                    if len(appid) >= 5:
                        print("✅ APP ID格式有效")
                        break
                    print(f"❌ 输入长度：{len(appid)}，需要至少5位字符")

                # 密钥输入（增加输入提示）
                print("\n[步骤2/2] 百度翻译密钥")
                print("⚠️ 注意：输入时不会显示字符，请直接输入后按回车")
                while True:
                    try:
                        appkey = getpass("请输入密钥（至少8位字符）：").strip()
                        if len(appkey) < 8:
                            print(f"❌ 输入长度：{len(appkey)}，需要至少8位字符")
                            continue
                        break
                    except Exception as e:
                        print(f"输入错误: {str(e)}")

                config['apis'][api_type] = {'appid': appid, 'appkey': appkey}

                # 保存配置
                if ConfigManager.save_config(config):
                    print("\n🔄 正在验证API连通性...")
                    try:
                        test_result = Translator.translate(
                            text="test",
                            api_type=api_type,
                            target_lang="zh",
                            api_config=config['apis'][api_type]
                        )
                        print(f"✅ 验证成功！测试翻译结果：{test_result}")
                    except Exception as e:
                        print(f"❌ API验证失败：{str(e)}")
                    
                    # 提取公共验证逻辑
                    def verify_api():
                        try:
                            test_result = Translator.translate(
                                text="test", api_type=api_type,
                                target_lang="zh", api_config=config['apis'][api_type]
                            )
                            print(f"✅ 验证成功！测试翻译结果：{test_result}")
                            return True
                        except Exception as e:
                            print(f"❌ API验证失败：{str(e)}")
                            return False
                            
                    if verify_api():
                        print("🎉 配置已完成，自动返回主菜单")
                return config

            elif api_type == 'tencent':
                print("\n[步骤1/2] 腾讯云SecretId")
                while True:
                    secret_id = getpass("请输入SecretId（AKID开头，36位）：").strip()
                    if secret_id.lower() == 'exit':
                        return config
                    if secret_id.startswith('AKID') and len(secret_id) == 36:
                        print("✅ SecretId格式有效")
                        break
                    print("❌ SecretId应以AKID开头且36位")

                print("\n[步骤2/2] 腾讯云SecretKey")
                while True:
                    secret_key = getpass("请输入SecretKey（32位字符）：").strip()
                    if secret_key.lower() == 'exit':
                        return config
                    if len(secret_key) == 32:
                        print("✅ SecretKey格式有效")
                        break
                    print("❌ SecretKey应为32位字符")

                config['apis'][api_type] = {'secret_id': secret_id, 'secret_key': secret_key}

            if ConfigManager.save_config(config):
                print("\n🔄 正在验证API连通性...")
                try:
                    test_result = Translator.translate(
                        text="test",
                        api_type=api_type,
                        target_lang="zh",
                        api_config=config['apis'][api_type]
                    )
                    print(f"✅ 验证成功！测试翻译结果：{test_result}")
                    print("🎉 配置已完成，自动返回主菜单")
                except Exception as e:
                    print(f"❌ API验证失败：{str(e)}")
                    print("⚠️ 请检查：1.网络连接 2.API参数 3.服务余额")
            else:
                print("❌ 配置保存失败")

            return config

        except Exception as e:
            print(f"❌ 发生未知错误：{str(e)}")
            return config

    @staticmethod
    def switch_api():
        """切换当前API"""
        config = ConfigManager.load_config()
        print("\n可用翻译API：")
        for i, (key, name) in enumerate(SUPPORTED_APIS.items(), 1):
            print(f"{i}. {name}")

        try:
            choice = int(input("请选择要切换的API：")) - 1
            api_type = list(SUPPORTED_APIS.keys())[choice]
            config['current_api'] = api_type
            if ConfigManager.save_config(config):
                print(f"✅ 已切换到{SUPPORTED_APIS[api_type]}")
            return config
        except (ValueError, IndexError):
            print("❌ 无效的选择")
            return config


class RenameManager:
    def __init__(self):
        self.file_records = OrderedDict()
        self.counter = 1
        self.original_names = {}  # 新增回滚记录

    def add_record(self, file_path, orig_name, new_name):
        self.original_names[file_path] = orig_name  # 记录原始路径
        self.file_records[self.counter] = {
            "path": file_path,
            "original": orig_name,
            "translated": new_name,
            "custom": None
        }
        self.counter += 1

    def display_preview(self):
        print("\n{:<5} {:<50} {:<50}".format("序号", "原始文件名", "翻译后文件名"))
        print("-" * 105)
        for idx, data in self.file_records.items():
            display_name = data["custom"] or data["translated"]
            orig = self._truncate(data["original"])
            trans = self._truncate(display_name)
            print(f"{idx:<5} {orig:<50} {trans:<50}")

    @staticmethod
    def _truncate(text, length=45):
        return text[:length] + "..." if len(text) > length else text

    def modify_name(self, file_id, new_name):
        if file_id in self.file_records:
            self.file_records[file_id]["custom"] = new_name
            return True
        return False


class Translator:
    @staticmethod
    def translate(text, api_type, target_lang, api_config, retries=3):
        """统一翻译接口（新增重试机制）"""
        for attempt in range(retries):
            try:
                # 原有翻译逻辑
                if api_type == 'baidu':
                    return Translator.baidu_translate(text, target_lang, api_config)
                elif api_type == 'tencent':
                    return Translator.tencent_translate(text, target_lang, api_config)
                raise ValueError("不支持的API类型")
                
            except Exception as e:
                if attempt == retries - 1:
                    raise  # 最后一次尝试直接抛出异常
                time.sleep(2 ** attempt)  # 指数退避

    @staticmethod
    def baidu_translate(query, to_lang, config):
        """百度翻译实现"""
        url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
        salt = str(random.randint(32768, 65536))
        sign_str = config['appid'] + query + salt + config['appkey']
        sign = hashlib.md5(sign_str.encode()).hexdigest()

        params = {
            'q': query,
            'from': 'auto',
            'to': to_lang,
            'appid': config['appid'],
            'salt': salt,
            'sign': sign
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = json.loads(response.text)
            return result['trans_result'][0]['dst']
        except Exception as e:
            raise Exception(f"百度翻译失败：{str(e)}")

    @staticmethod
    def tencent_translate(query, to_lang, config):
        """腾讯翻译实现"""
        endpoint = "tmt.tencentcloudapi.com"
        service = "tmt"
        action = "TextTranslate"
        version = "2018-03-21"
        region = "ap-guangzhou"
        timestamp = int(time.time())

        # 生成签名
        def sign(key, msg):
            return HMAC(key, msg.encode("utf-8"), sha256).digest()

        secret_date = HMAC(("TC3" + config['secret_key']).encode("utf-8"),
                           str(timestamp).encode("utf-8"), sha256).hexdigest()
        secret_service = HMAC(secret_date.encode("utf-8"),
                              service.encode("utf-8"), sha256).hexdigest()
        secret_signing = HMAC(secret_service.encode("utf-8"),
                              "tc3_request".encode("utf-8"), sha256).hexdigest()

        headers = {
            "Authorization": f"TC3-HMAC-SHA256 Credential={config['secret_id']}/{timestamp}/{region}/{service}/tc3_request, "
                             f"SignedHeaders=content-type;host, Signature={secret_signing}",
            "Content-Type": "application/json",
            "Host": endpoint,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": version,
            "X-TC-Region": region
        }

        try:
            response = requests.post(
                f"https://{endpoint}",
                headers=headers,
                json={"SourceText": query, "Source": "auto", "Target": to_lang, "ProjectId": 0},
                timeout=10
            )
            response.raise_for_status()
            result = json.loads(response.text)
            return result['Response']['TargetText']
        except Exception as e:
            raise Exception(f"腾讯翻译失败：{str(e)}")


def display_language_menu():
    print("\n请选择目标语言：")
    for i, (name, code) in enumerate(SUPPORTED_LANGUAGES[1:], 1):
        print(f"{i}. {name} ({code})")
    print("0. 退出程序")


def get_language_choice():
    while True:
        try:
            max_choice = len(SUPPORTED_LANGUAGES) - 1
            choice = int(input(f"请输入数字选择目标语言 (0-{max_choice}): "))
            if choice == 0:
                exit("用户终止操作")
            if 1 <= choice <= max_choice:
                return SUPPORTED_LANGUAGES[choice][1]
            raise ValueError
        except (ValueError, IndexError):
            print("❌ 错误：请输入有效的数字选项")


def sanitize_filename(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()


def generate_new_name(directory, base_name, ext):
    counter = 1
    new_name = f"{base_name}{ext}"
    while os.path.exists(os.path.join(directory, new_name)):
        new_name = f"{base_name}_{counter}{ext}"
        counter += 1
    return new_name


def process_filename(file_base, api_type, api_config, target_lang):
    # 原正则表达式改进版本，更好处理混合内容
    parts = re.findall(r'([a-zA-Z]{2,})|([0-9\s-]+)|([^a-zA-Z0-9\s-]+)', file_base)
    translated_parts = []

    for letters, preserved, others in parts:
        if letters:
            try:
                translated = Translator.translate(
                    text=letters,
                    api_type=api_type,
                    target_lang=target_lang,
                    api_config=api_config
                )
                translated_parts.append(translated)
            except Exception as e:
                print(f"❌ 翻译失败保留原文: {letters} ({str(e)})")
                translated_parts.append(letters)
        elif preserved:
            translated_parts.append(preserved)
        elif others:
            translated_parts.append(others)

    return ''.join(translated_parts)


def collect_files(root_dir, api_type, api_config, to_lang):
    root_dir = os.path.normpath(root_dir)  # 规范化路径
    root_dir = root_dir.encode('utf-8').decode('utf-8')  # 统一编码
    manager = RenameManager()

    print("\n正在扫描文件...")
    all_files = []
    for foldername, _, filenames in os.walk(root_dir):
        all_files.extend([(foldername, fn) for fn in filenames])

    print(f"发现 {len(all_files)} 个待处理文件")

    # 分块处理
    for chunk_idx in range(0, len(all_files), CHUNK_SIZE):
        chunk = all_files[chunk_idx:chunk_idx + CHUNK_SIZE]
        desc = f"处理块 {chunk_idx // CHUNK_SIZE + 1}/{(len(all_files) - 1) // CHUNK_SIZE + 1}"

        with tqdm(chunk, desc=desc, unit="file") as pbar:
            for foldername, filename in pbar:
                file_path = os.path.join(foldername, filename)
                file_base, file_ext = os.path.splitext(filename)

                try:
                    translated_base = process_filename(file_base, api_type, api_config, to_lang)
                    cleaned_name = sanitize_filename(translated_base)
                    final_name = generate_new_name(foldername, cleaned_name, file_ext)
                    manager.add_record(file_path, filename, final_name)
                except Exception as e:
                    pbar.write(f"❌ 跳过文件 {filename}：{str(e)}")
                pbar.set_postfix_str(filename[:15])

    return manager


def edit_mode(manager):
    while True:
        manager.display_preview()
        choice = input("\n输入要修改的序号（多个用逗号分隔）或按回车继续：").strip()
        if not choice:
            break

        try:
            ids = [int(x.strip()) for x in choice.split(",")]
            for file_id in ids:
                if file_id not in manager.file_records:
                    print(f"❌ 无效序号：{file_id}")
                    continue

                record = manager.file_records[file_id]
                new_name = input(f"请输入新文件名（当前：{record['translated']}）：").strip()
                if new_name:
                    base, ext = os.path.splitext(new_name)
                    cleaned_base = sanitize_filename(base)
                    final_name = generate_new_name(
                        os.path.dirname(record["path"]),
                        cleaned_base,
                        ext or os.path.splitext(record["path"])[1]
                    )
                    manager.modify_name(file_id, final_name)
        except ValueError:
            print("❌ 输入格式错误，请使用数字序号")


def execute_rename(manager):
    success = 0
    with tqdm(manager.file_records.values(), desc="执行重命名", unit="file") as pbar:
        for record in pbar:
            try:
                final_name = record["custom"] or record["translated"]
                os.rename(record["path"], os.path.join(
                    os.path.dirname(record["path"]),
                    final_name
                ))
                success += 1
                pbar.set_postfix_str(f"最新: {final_name[:15]}...")
            except Exception as e:
                pbar.write(f"❌ 重命名失败 {record['original']}: {str(e)}")
    print(f"\n✅ 操作完成：{success} 成功，{len(manager.file_records) - success} 失败")


def main_flow():
    config = ConfigManager.load_config()

    while True:
        print("\n=== 多API翻译重命名工具 ===")
        print(f"当前API：{SUPPORTED_APIS[config['current_api']]}")
        print("1. 开始处理文件")
        print("2. 配置当前API参数")
        print("3. 切换翻译API")
        print("4. 退出程序")
        choice = input("请选择操作：").strip()

        if choice == '1':
            process_files(config)
        elif choice == '2':
            config = ConfigManager.update_api_config(config['current_api'])
        elif choice == '3':
            config = ConfigManager.switch_api()
        elif choice == '4':
            print("感谢使用，再见！")
            exit()
        else:
            print("❌ 无效的选项")


def process_files(config):
    api_type = config['current_api']
    api_config = config['apis'][api_type]

    # 验证API配置
    verify_msg = {
        'baidu': (not api_config.get('appid') or not api_config.get('appkey'), "请先配置百度翻译API参数"),
        'tencent': (not api_config.get('secret_id') or not api_config.get('secret_key'), "请先配置腾讯翻译API参数")
    }
    if verify_msg.get(api_type, (True, "未知API类型"))[0]:
        print(f"❌ {verify_msg[api_type][1]}")
        return

    # 获取用户输入
    root_dir = input("\n请输入要处理的根目录路径：").strip()
    if not os.path.isdir(root_dir):
        print("❌ 错误：目录不存在")
        return

    display_language_menu()
    to_lang = get_language_choice()

    try:
        manager = collect_files(root_dir, api_type, api_config, to_lang)
        edit_mode(manager)

        if manager.file_records:
            confirm = input("\n是否执行重命名操作？(y/n)：").lower() == 'y'
            if confirm:
                execute_rename(manager)
            else:
                print("⚠️ 操作已取消")
        else:
            print("ℹ️ 没有需要处理的文件")
    except Exception as e:
        print(f"❌ 处理过程中发生错误：{str(e)}")
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断操作")


if __name__ == "__main__":
    # 打包后初始化逻辑
    if getattr(sys, 'frozen', False):
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR, exist_ok=True)
    
    try:
        if not os.path.exists(CONFIG_PATH):
            print("⭐ 首次使用需要初始化配置")
            ConfigManager.save_config(ConfigManager.load_config())

        main_flow()
    except KeyboardInterrupt:
        print("\n👋 程序已退出")