#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import concurrent.futures
import dns.resolver
import ipaddress
import random
import socket
import string
import sys
import requests
from tqdm import tqdm
from colorama import init, Fore, Style

# 初始化colorama
init(autoreset=True)

class SubdomainEnumerator:
    def __init__(self, domain, wordlist=None, threads=10, timeout=5, output=None, verbose=False, http_verify=False):
        self.domain = domain
        self.wordlist = wordlist
        self.threads = threads
        self.timeout = timeout
        self.output_file = output
        self.verbose = verbose
        self.http_verify = http_verify
        self.results = set()
        self.wildcard_ips = set()
        self.wildcard_http_patterns = {}
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = self.timeout
        self.resolver.lifetime = self.timeout
        
        # 设置HTTP请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }

    def print_info(self, message):
        """打印信息消息"""
        print(f"{Fore.BLUE}[+] {Style.RESET_ALL}{message}")

    def print_warning(self, message):
        """打印警告消息"""
        print(f"{Fore.YELLOW}[!] {Style.RESET_ALL}{message}")

    def print_error(self, message):
        """打印错误消息"""
        print(f"{Fore.RED}[-] {Style.RESET_ALL}{message}")

    def print_success(self, message):
        """打印成功消息"""
        print(f"{Fore.GREEN}[+] {Style.RESET_ALL}{message}")

    def load_wordlist(self):
        """加载子域名字典文件"""
        try:
            with open(self.wordlist, 'r') as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.print_error(f"加载字典文件失败: {e}")
            sys.exit(1)

    def detect_wildcard(self):
        """检测域名是否有泛解析"""
        self.print_info("检查泛解析DNS...")
        
        # 生成5个随机子域名来测试泛解析
        random_subdomains = []
        for _ in range(5):
            random_prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            random_subdomains.append(f"{random_prefix}.{self.domain}")
        
        for subdomain in random_subdomains:
            try:
                answers = self.resolver.resolve(subdomain, 'A')
                for rdata in answers:
                    self.wildcard_ips.add(str(rdata))
                    if self.verbose:
                        self.print_warning(f"检测到泛解析: {subdomain} 解析到 {rdata}")
                
                # 如果启用HTTP验证，获取HTTP响应特征
                if self.http_verify and self.wildcard_ips:
                    self.get_wildcard_http_patterns(subdomain)
                    
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout):
                pass
            except Exception as e:
                if self.verbose:
                    self.print_error(f"泛解析检测过程中出错: {e}")
        
        if self.wildcard_ips:
            self.print_warning(f"检测到泛解析DNS，IP地址: {', '.join(self.wildcard_ips)}")
            return True
        else:
            self.print_info("未检测到泛解析DNS")
            return False

    def get_wildcard_http_patterns(self, subdomain):
        """获取泛解析域名的HTTP响应特征"""
        try:
            for protocol in ['http', 'https']:
                url = f"{protocol}://{subdomain}"
                try:
                    response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=False)
                    
                    # 存储HTTP响应特征
                    if protocol not in self.wildcard_http_patterns:
                        self.wildcard_http_patterns[protocol] = {
                            'status_code': response.status_code,
                            'content_length': len(response.content),
                            'title': self.extract_title(response.text),
                            'server': response.headers.get('Server', ''),
                        }
                        
                    if self.verbose:
                        self.print_info(f"获取到泛解析HTTP特征 ({protocol}): 状态码={response.status_code}, 内容长度={len(response.content)}")
                        
                except requests.exceptions.RequestException:
                    pass
        except Exception as e:
            if self.verbose:
                self.print_error(f"获取HTTP特征时出错: {e}")

    def extract_title(self, html):
        """从HTML中提取标题"""
        try:
            start = html.find('<title>')
            end = html.find('</title>')
            if start != -1 and end != -1:
                return html[start + 7:end].strip()
        except:
            pass
        return ''

    def is_wildcard_ip(self, ip):
        """检查IP是否为泛解析IP"""
        return ip in self.wildcard_ips

    def is_wildcard_http_response(self, protocol, status_code, content_length, title, server):
        """检查HTTP响应是否与泛解析特征匹配"""
        if protocol not in self.wildcard_http_patterns:
            return False
            
        pattern = self.wildcard_http_patterns[protocol]
        
        # 检查状态码
        if status_code != pattern['status_code']:
            return False
            
        # 检查内容长度（允许10%的差异）
        content_diff = abs(content_length - pattern['content_length']) / pattern['content_length'] if pattern['content_length'] else 1
        if content_diff > 0.1:
            return False
            
        # 检查标题
        if title != pattern['title']:
            return False
            
        # 检查服务器头
        if server != pattern['server']:
            return False
            
        return True

    def verify_subdomain(self, subdomain):
        """验证子域名是否为真实子域名或泛解析误报"""
        # 如果没有检测到泛解析，无需验证
        if not self.wildcard_ips:
            return True
        
        # 如果不启用HTTP验证，只检查IP
        if not self.http_verify:
            try:
                ip = socket.gethostbyname(subdomain)
                return ip not in self.wildcard_ips
            except:
                return False
        
        # 启用HTTP验证时，检查HTTP响应特征
        try:
            for protocol in ['http', 'https']:
                if protocol not in self.wildcard_http_patterns:
                    continue
                    
                url = f"{protocol}://{subdomain}"
                try:
                    response = requests.get(url, headers=self.headers, timeout=self.timeout, verify=False)
                    
                    # 提取响应特征
                    status_code = response.status_code
                    content_length = len(response.content)
                    title = self.extract_title(response.text)
                    server = response.headers.get('Server', '')
                    
                    # 如果HTTP响应特征与泛解析不同，认为是真实子域名
                    if not self.is_wildcard_http_response(protocol, status_code, content_length, title, server):
                        return True
                        
                except requests.exceptions.RequestException:
                    # 连接失败可能表明这是一个不同的服务
                    return True
                    
            # 所有协议都匹配泛解析特征
            return False
            
        except Exception as e:
            if self.verbose:
                self.print_error(f"验证子域名时出错: {e}")
            return False

    def resolve_subdomain(self, subdomain):
        """解析子域名并检查其有效性"""
        full_domain = f"{subdomain}.{self.domain}"
        
        try:
            answers = self.resolver.resolve(full_domain, 'A')
            ips = [str(rdata) for rdata in answers]
            
            # 检查所有解析的IP是否都是泛解析IP
            if all(self.is_wildcard_ip(ip) for ip in ips):
                # 进一步验证
                if self.verify_subdomain(full_domain):
                    return (full_domain, ips)
                else:
                    if self.verbose:
                        self.print_warning(f"跳过泛解析子域名: {full_domain} -> {', '.join(ips)}")
                    return None
            else:
                # 至少有一个IP不是泛解析IP
                return (full_domain, ips)
                
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout):
            return None
        except Exception as e:
            if self.verbose:
                self.print_error(f"解析 {full_domain} 时出错: {e}")
            return None

    def enumerate(self):
        """使用字典枚举子域名"""
        self.print_info(f"开始为 {self.domain} 枚举子域名")
        
        # 首先检测泛解析
        has_wildcard = self.detect_wildcard()
        
        # 加载字典
        subdomains = self.load_wordlist()
        self.print_info(f"从字典中加载了 {len(subdomains)} 个子域名")
        
        # 使用ThreadPoolExecutor进行并发子域名解析
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.threads) as executor:
            results = list(tqdm(
                executor.map(self.resolve_subdomain, subdomains),
                total=len(subdomains),
                desc="枚举子域名",
                unit="个"
            ))
        
        # 过滤掉None结果并添加到结果集
        valid_results = [r for r in results if r is not None]
        for domain, ips in valid_results:
            self.results.add((domain, ', '.join(ips)))
        
        self.print_success(f"找到 {len(self.results)} 个有效子域名")
        
        # 如果指定了输出文件，保存结果
        if self.output_file:
            self.save_results()
        
        # 打印结果
        self.print_results()
        
        return self.results

    def save_results(self):
        """保存结果到输出文件"""
        try:
            with open(self.output_file, 'w') as f:
                for domain, ips in sorted(self.results):
                    f.write(f"{domain} -> {ips}\n")
            self.print_success(f"结果已保存到 {self.output_file}")
        except Exception as e:
            self.print_error(f"保存结果时出错: {e}")

    def print_results(self):
        """打印枚举结果"""
        print("\n" + Fore.GREEN + "[+] 枚举结果:" + Style.RESET_ALL)
        print("-" * 60)
        for domain, ips in sorted(self.results):
            print(f"{Fore.CYAN}{domain}{Style.RESET_ALL} -> {ips}")
        print("-" * 60)


def main():
    parser = argparse.ArgumentParser(description="子域名枚举工具（带泛解析检测）")
    parser.add_argument("-d", "--domain", required=True, help="目标域名")
    parser.add_argument("-w", "--wordlist", required=True, help="字典文件路径")
    parser.add_argument("-t", "--threads", type=int, default=10, help="线程数 (默认: 10)")
    parser.add_argument("-o", "--output", help="输出文件路径")
    parser.add_argument("--timeout", type=int, default=5, help="DNS解析超时时间(秒) (默认: 5)")
    parser.add_argument("-v", "--verbose", action="store_true", help="启用详细输出")
    parser.add_argument("--http-verify", action="store_true", help="使用HTTP响应特征验证泛解析")
    
    args = parser.parse_args()
    
    # 禁用SSL警告
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        pass
    
    enumerator = SubdomainEnumerator(
        domain=args.domain,
        wordlist=args.wordlist,
        threads=args.threads,
        timeout=args.timeout,
        output=args.output,
        verbose=args.verbose,
        http_verify=args.http_verify
    )
    
    try:
        enumerator.enumerate()
    except KeyboardInterrupt:
        print("\n" + Fore.YELLOW + "[!] 用户中断了枚举" + Style.RESET_ALL)
        sys.exit(0)


if __name__ == "__main__":
    main() 