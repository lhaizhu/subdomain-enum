# 子域名枚举工具

这是一个用Python编写的子域名枚举工具，具有泛解析检测功能，可以有效减少误报。

## 功能特点

- 多线程子域名枚举
- 泛解析检测和处理
- HTTP响应特征验证（减少泛解析误报）
- 彩色输出界面
- 可自定义字典文件
- 支持批量处理多个域名
- 结果输出到文件
- 详细的日志输出选项

## 安装

1. 克隆此仓库或下载脚本文件
2. 安装依赖项：

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本用法（单个域名）

```bash
python subdomain_enum_enhanced.py -d example.com -w wordlist.txt
```

### 使用HTTP验证减少泛解析误报

```bash
python subdomain_enum_enhanced.py -d example.com -w wordlist.txt --http-verify
```

### 批量处理多个域名

从文件读取多个域名进行批量枚举：

```bash
python subdomain_enum_enhanced.py -df domains.txt -w wordlist.txt
```

将结果保存到指定目录（每个域名一个文件）：

```bash
python subdomain_enum_enhanced.py -df domains.txt -w wordlist.txt -od results
```

### 完整参数说明

```
usage: subdomain_enum_enhanced.py [-h] (-d DOMAIN | -df DOMAIN_FILE) -w WORDLIST [-t THREADS] [-o OUTPUT] [-od OUTPUT_DIR] [--timeout TIMEOUT] [-v] [--http-verify]

子域名枚举工具（带泛解析检测）

options:
  -h, --help            显示帮助信息并退出
  -d DOMAIN, --domain DOMAIN
                        目标域名
  -df DOMAIN_FILE, --domain-file DOMAIN_FILE
                        包含多个域名的文件路径，每行一个域名
  -w WORDLIST, --wordlist WORDLIST
                        字典文件路径
  -t THREADS, --threads THREADS
                        线程数 (默认: 10)
  -o OUTPUT, --output OUTPUT
                        输出文件路径
  -od OUTPUT_DIR, --output-dir OUTPUT_DIR
                        输出目录路径（用于多域名模式）
  --timeout TIMEOUT     DNS解析超时时间(秒) (默认: 5)
  -v, --verbose         启用详细输出
  --http-verify         使用HTTP响应特征验证泛解析
```

## 域名文件格式

当使用`-df/--domain-file`参数时，域名文件应包含每行一个域名，例如：

```
example.com
example.org
example.net
```

可以使用`#`开头的行添加注释，这些行将被忽略。

## 字典文件

字典文件应包含每行一个子域名前缀，例如：

```
www
mail
blog
admin
test
```

## 泛解析处理

该工具通过以下方式处理泛解析：

1. 生成随机子域名并检查它们是否解析到相同的IP地址
2. 如果检测到泛解析，记录泛解析IP地址
3. 在枚举过程中，跳过解析到泛解析IP的子域名
4. 对可能的子域名进行额外验证，以减少误报
5. 可选的HTTP响应特征验证，通过比较HTTP状态码、内容长度、标题和服务器头来识别真实子域名

## 增强版功能

增强版脚本 (`subdomain_enum_enhanced.py`) 相比基础版本增加了以下功能：

1. **HTTP响应特征验证**：通过分析HTTP响应的特征来区分真实子域名和泛解析
2. **彩色输出界面**：使用colorama库提供彩色终端输出，提高可读性
3. **批量处理多个域名**：支持从文件读取多个域名进行批量枚举
4. **更详细的错误处理**：提供更多的错误信息和调试输出
5. **改进的泛解析检测算法**：更准确地识别泛解析域名

## 示例

```bash
# 基本用法
python subdomain_enum_enhanced.py -d example.com -w subdomains.txt -t 20 -o results.txt

# 启用详细输出和HTTP验证
python subdomain_enum_enhanced.py -d example.com -w subdomains.txt -t 20 -o results.txt -v --http-verify

# 批量处理多个域名
python subdomain_enum_enhanced.py -df domains.txt -w subdomains.txt -t 20 -od results -v
```

## 注意事项

- 请合法合规使用此工具
- 大型字典文件可能需要较长时间处理
- 某些网络环境可能需要调整超时参数
- HTTP验证可能会增加枚举时间，但可以显著减少误报
- 批量处理大量域名时，建议使用输出目录参数`-od`，这样每个域名的结果会保存到单独的文件中 