# SecretScraper

![Tests](https://github.com/PadishahIII/SecretScraper/actions/workflows/main.yml/badge.svg)

## Overview

SecretScraper is a highly configurable web scrape tool that crawl links  from target websites and scrape sensitive
data via regular expression.


## Feature
- Web crawler: extract links via both DOM hierarchy and regex
- Support domain white list and black list
- Support multiple targets, input target URLs from a file
- Scalable customization: header, proxy, timeout, cookie, scrape depth, follow redirect, etc.
- Built-in regex to search for sensitive information
- Flexible configuration in yaml format

## Prerequisite
- Platform: Test on MaxOS, Ubuntu and Windows.
- Python Version >= 3.11

## Usage

### Install

```bash
pip install secretscraper
```

### Basic Usage

Start with single target:

```bash
secretscraper -u https://scrapeme.live/shop/
```

Start with multiple targets:

```bash
secretscraper -f urls
```

```text
# urls
http://scrapeme.live/1
http://scrapeme.live/2
http://scrapeme.live/3
http://scrapeme.live/4
http://scrapeme.live/1
```
A sample output:
<img width="1125" alt="image" src="https://github.com/PadishahIII/SecretScraper/assets/83501709/00dd2053-7b9a-4ef3-a2b2-8c168e8ec0ee">

```text
> secretscraper -u http://127.0.0.1:8888
Target urls num: 1
Max depth: 1, Max page num: 1000
Output file: /Users/padishah/Documents/Files/Python_WorkSpace/secretscraper/src/secretscraper/crawler.log
Target URLs: http://127.0.0.1:8888

1 URLs from http://127.0.0.1:8888 [200] (depth:0):
http://127.0.0.1:8888/index.html [200]

1 Domains:
127.0.0.1:8888


13 Secrets found in http://127.0.0.1:8888/1.js 200:
Email: 3333333qqqxxxx@qq.com
Shiro: =deleteme
JS Map: xx/static/asdfaf.js.map
Email: example@example.com
Swagger: static/swagger-ui.html
ID Card: 130528200011110000
URL as a Value: redirect=http://
Phone: 13273487666
Internal IP:  192.168.1.1
Cloud Key: Accesskeyid
Cloud Key: AccessKeySecret
Shiro: rememberme=
Internal IP:  10.0.0.1


1 JS from http://127.0.0.1:8888:
http://127.0.0.1:8888/1.js [200]
```

All supported options:
```bash
> secretscraper --help
Usage: secretscraper [OPTIONS]

  Main commands

Options:
  -V, --version                Show version and exit.
  --debug                      Enable debug.
  -a, --ua TEXT                Set User-Agent
  -c, --cookie TEXT            Set cookie
  -d, --allow-domains TEXT     Domain white list, wildcard(*) is supported,
                               separated by commas, e.g. *.example.com,
                               example*
  -D, --disallow-domains TEXT  Domain black list, wildcard(*) is supported,
                               separated by commas, e.g. *.example.com,
                               example*
  -f, --url-file FILE          Target urls file, separated by line break
  -i, --config FILE            Set config file, defaults to settings.yml
  -m, --mode [1|2]             Set crawl mode, 1(normal) for max_depth=1,
                               2(thorough) for max_depth=2, default 1
  --max-page INTEGER           Max page number to crawl, default 100000
  --max-depth INTEGER          Max depth to crawl, default 1
  -o, --outfile FILE           Output result to specified file
  -s, --status TEXT            Filter response status to display, seperated by
                               commas, e.g. 200,300-400
  -x, --proxy TEXT             Set proxy, e.g. http://127.0.0.1:8080,
                               socks5://127.0.0.1:7890
  -H, --hide-regex             Hide regex search result
  -F, --follow-redirects       Follow redirects
  -u, --url TEXT               Target url
  --detail                     Show detailed result
  -l, --local PATH             Local file or directory, scan local
                               file/directory recursively
  --help                       Show this message and exit.

```

### Advanced Usage

#### Thorough Crawl

The max depth is set to 1, which means only the start urls will be crawled. To change that, you can specify
via `--max-depth <number>`. Or in a simpler way, use `-m 2` to run the crawler in thorough mode which is equivalent
to `--max-depth 2`. By default the normal mode `-m 1` is adopted with max depth set to 1.
```bash
secretscraper -u https://scrapeme.live/shop/ -m 2
```

#### Write Results to File
```bash
secretscraper -u https://scrapeme.live/shop/ -o result.log
```

#### Hide Regex Result
Use `-H` option to hide regex-matching results. Only found links will be displayed.
```bash
secretscraper -u https://scrapeme.live/shop/ -H
```

#### Extract secrets from local file
```bash
secretscraper -l <dir or file>
```

#### Customize Configuration
The built-in config is shown as below. You can assign custom configuration via `-i settings.yml`.
```yaml
verbose: false
debug: false
loglevel: warning
logpath: log

proxy: "" # http://127.0.0.1:7890
max_depth: 1 # 0 for no limit
max_page_num: 1000 # 0 for no limit
timeout: 5
follow_redirects: false
workers_num: 1000
headers:
  Accept: "*/*"
  Cookie: ""
  User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36 SE 2.X MetaSr 1.0

urlFind:
  - '["''‘“`]\s{0,6}(https{0,1}:[-a-zA-Z0-9()@:%_\+.~#?&//={}]{2,100}?)\s{0,6}["''‘“`]'
  - =\s{0,6}(https{0,1}:[-a-zA-Z0-9()@:%_\+.~#?&//={}]{2,100})
  - '["''‘“`]\s{0,6}([#,.]{0,2}/[-a-zA-Z0-9()@:%_\+.~#?&//={}]{2,100}?)\s{0,6}["''‘“`]'
  - '"([-a-zA-Z0-9()@:%_\+.~#?&//={}]+?[/]{1}[-a-zA-Z0-9()@:%_\+.~#?&//={}]+?)"'
  - href\s{0,6}=\s{0,6}["'‘“`]{0,1}\s{0,6}([-a-zA-Z0-9()@:%_\+.~#?&//={}]{2,100})|action\s{0,6}=\s{0,6}["'‘“`]{0,1}\s{0,6}([-a-zA-Z0-9()@:%_\+.~#?&//={}]{2,100})
jsFind:
  - (https{0,1}:[-a-zA-Z0-9（）@:%_\+.~#?&//=]{2,100}?[-a-zA-Z0-9（）@:%_\+.~#?&//=]{3}[.]js)
  - '["''‘“`]\s{0,6}(/{0,1}[-a-zA-Z0-9（）@:%_\+.~#?&//=]{2,100}?[-a-zA-Z0-9（）@:%_\+.~#?&//=]{3}[.]js)'
  - =\s{0,6}[",',’,”]{0,1}\s{0,6}(/{0,1}[-a-zA-Z0-9（）@:%_\+.~#?&//=]{2,100}?[-a-zA-Z0-9（）@:%_\+.~#?&//=]{3}[.]js)
dangerousPath:
  - logout
  - update
  - remove
  - insert
  - delete

rules:
  - name: Swagger
    regex: \b[\w/]+?((swagger-ui.html)|(\"swagger\":)|(Swagger UI)|(swaggerUi)|(swaggerVersion))\b
    loaded: true
  - name: ID Card
    regex: \b((\d{8}(0\d|10|11|12)([0-2]\d|30|31)\d{3}\$)|(\d{6}(18|19|20)\d{2}(0[1-9]|10|11|12)([0-2]\d|30|31)\d{3}(\d|X|x)))\b
    loaded: true
  - name: Phone
    regex: \b((?:(?:\+|00)86)?1(?:(?:3[\d])|(?:4[5-79])|(?:5[0-35-9])|(?:6[5-7])|(?:7[0-8])|(?:8[\d])|(?:9[189]))\d{8})\b
    loaded: true
  - name: JS Map
    regex: \b([\w/]+?\.js\.map)
    loaded: true
  - name: URL as a Value
    regex: (\b\w+?=(https?)(://|%3a%2f%2f))
    loaded: true
  - name: Email
    regex: \b(([a-z0-9][_|\.])*[a-z0-9]+@([a-z0-9][-|_|\.])*[a-z0-9]+\.([a-z]{2,}))\b
    loaded: true
  - name: Internal IP
    regex: '[^0-9]((127\.0\.0\.1)|(10\.\d{1,3}\.\d{1,3}\.\d{1,3})|(172\.((1[6-9])|(2\d)|(3[01]))\.\d{1,3}\.\d{1,3})|(192\.168\.\d{1,3}\.\d{1,3}))'
    loaded: true
  - name: Cloud Key
    regex: \b((accesskeyid)|(accesskeysecret)|\b(LTAI[a-z0-9]{12,20}))\b
    loaded: true
  - name: Shiro
    regex: (=deleteMe|rememberMe=)
    loaded: true
  - name: Suspicious API Key
    regex: "[\"'][0-9a-zA-Z]{32}['\"]"
    loaded: true

```

---

# TODO
- [ ] Support headless browser
- [ ] Add regex doc reference
- [x] Generate configuration file
- [x] Detect dangerous paths and avoid requesting them
- [x] Support url-finder output format, add `--detail` option
- [x] Support windows
- [x] Scan local file
- [x] Extract links via regex

---

# Change Log
## 2024.4.28 Version 1.3.5
- **New Features**
  - Support windows
  - Optimize crawler
  - Prettify output, add `--detail` option
  - Generate default configuration to settings.yml
  - Avoid requesting dangerous paths

## 2024.4.28 Version 1.3.2
- **New Features**
  - Extract links via regex

## 2024.4.26 Version 1.3.1
- **New Features**
  - [x] Support scan local files

## 2024.4.15
- [x] Add status to url result
- [x] All crawler test passed
