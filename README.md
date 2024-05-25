# SecretScraper

![Tests](https://github.com/PadishahIII/SecretScraper/actions/workflows/main.yml/badge.svg)
![Pypi Python Version](https://img.shields.io/pypi/pyversions/secretscraper.svg?style=plastic)

## Overview

SecretScraper is a highly configurable web scrape tool that crawl links  from target websites and scrape sensitive
data via regular expression.


 <img alt="Shows an illustrated sun in light mode and a moon with stars in dark mode." src="https://github.com/PadishahIII/SecretScraper/assets/83501709/d1aa763f-5711-47c4-8b8f-9309bac88ae2" width=800>

## Feature
- Web crawler: extract links via both DOM hierarchy and regex
- Support domain white list and black list
- Support multiple targets, input target URLs from a file
- Support local file scan
- Scalable customization: header, proxy, timeout, cookie, scrape depth, follow redirect, etc.
- Built-in regex to search for sensitive information
- Flexible configuration in yaml format

## Prerequisite
- Platform: Test on MacOS, Ubuntu and Windows.
- Python Version >= 3.9

## Usage

### Install

```bash
pip install secretscraper
```

### Update

```bash
pip install --upgrade secretscraper
```
**Note that**, since _Secretscraper_ generates a default configuration under the work directory if `settings.yml` is absent, so remember to update the `settings.yml` to the latest version(just copy from [Customize Configuration](https://github.com/PadishahIII/SecretScraper?tab=readme-ov-file#customize-configuration)).

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
Sample output:
<img width="971" alt="image" src="https://github.com/PadishahIII/SecretScraper/assets/83501709/e2f12441-a1ec-4fea-933e-17cdc3e31583">

<img width="904" alt="image" src="https://github.com/PadishahIII/SecretScraper/assets/83501709/d19faa0e-3ab2-452b-9a82-95e6607d54c6">



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
  -o, --outfile FILE           Output result to specified file in csv format
  -s, --status TEXT            Filter response status to display, seperated by
                               commas, e.g. 200,300-400
  -x, --proxy TEXT             Set proxy, e.g. http://127.0.0.1:8080,
                               socks5://127.0.0.1:7890
  -H, --hide-regex             Hide regex search result
  -F, --follow-redirects       Follow redirects
  -u, --url TEXT               Target url
  --detail                     Show detailed result
  --validate                   Validate the status of found urls
  -l, --local PATH             Local file or directory, scan local
                               file/directory recursively
  --help                       Show this message and exit.
```

### Advanced Usage
#### Validate the Status of Links
Use `--validate` option to check the status of found links, this helps reduce invalid links in the result.
```bash
secretscraper -u https://scrapeme.live/shop/ --validate --max-page=10
```

#### Thorough Crawl

The max depth is set to 1, which means only the start urls will be crawled. To change that, you can specify
via `--max-depth <number>`. Or in a simpler way, use `-m 2` to run the crawler in thorough mode which is equivalent
to `--max-depth 2`. By default the normal mode `-m 1` is adopted with max depth set to 1.
```bash
secretscraper -u https://scrapeme.live/shop/ -m 2
```

#### Write Results to Csv File
```bash
secretscraper -u https://scrapeme.live/shop/ -o result.csv
```

#### Domain White/Black List
Support wildcard(*), white list:
```bash
secretscraper -u https://scrapeme.live/shop/ -d *scrapeme*
```
Black list:
```bash
secretscraper -u https://scrapeme.live/shop/ -D *.gov
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

#### Switch to hyperscan
I have implemented the regex matching functionality with both `hyperscan` and `re` module, `re` module is used as default, if you purse higher performance, you can switch to `hyperscan` by changing the `handler_type` to `hyperscan` in `settings.yml`.

There are some pitfalls of `hyperscan` which you have to take caution to use it:
1. not support regex group: you can not extract content by parentheses.
2. different syntax from `re`

You'd better write regex separately for the two regex engine.

#### Customize Configuration
The built-in config is shown as below. You can assign custom configuration via `-i settings.yml`.
```yaml
verbose: false
debug: false
loglevel: critical
logpath: log
handler_type: re

proxy: "" # http://127.0.0.1:7890
max_depth: 1 # 0 for no limit
max_page_num: 1000 # 0 for no limit
timeout: 5
follow_redirects: true
workers_num: 1000
headers:
  Accept: "*/*"
  Cookie: ""
  User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36 SE 2.X MetaSr 1.0

urlFind:
  - "[\"'‘“`]\\s{0,6}(https{0,1}:[-a-zA-Z0-9()@:%_\\+.~#?&//={}]{2,250}?)\\s{0,6}[\"'‘“`]"
  - "=\\s{0,6}(https{0,1}:[-a-zA-Z0-9()@:%_\\+.~#?&//={}]{2,250})"
  - "[\"'‘“`]\\s{0,6}([#,.]{0,2}/[-a-zA-Z0-9()@:%_\\+.~#?&//={}]{2,250}?)\\s{0,6}[\"'‘“`]"
  - "\"([-a-zA-Z0-9()@:%_\\+.~#?&//={}]+?[/]{1}[-a-zA-Z0-9()@:%_\\+.~#?&//={}]+?)\""
  - "href\\s{0,6}=\\s{0,6}[\"'‘“`]{0,1}\\s{0,6}([-a-zA-Z0-9()@:%_\\+.~#?&//={}]{2,250})|action\\s{0,6}=\\s{0,6}[\"'‘“`]{0,1}\\s{0,6}([-a-zA-Z0-9()@:%_\\+.~#?&//={}]{2,250})"
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
    regex: \b((\d{8}(0\d|10|11|12)([0-2]\d|30|31)\d{3})|(\d{6}(18|19|20)\d{2}(0[1-9]|10|11|12)([0-2]\d|30|31)\d{3}(\d|X|x)))\b
    loaded: true
  - name: Phone
    regex: "['\"](1(3([0-35-9]\\d|4[1-8])|4[14-9]\\d|5([\\d]\\d|7[1-79])|66\\d|7[2-35-8]\\d|8\\d{2}|9[89]\\d)\\d{7})['\"]"
    loaded: true
  - name: JS Map
    regex: \b([\w/]+?\.js\.map)
    loaded: true
  - name: URL as a Value
    regex: (\b\w+?=(https?)(://|%3a%2f%2f))
    loaded: false
  - name: Email
    regex: "['\"]([\\w]+(?:\\.[\\w]+)*@(?:[\\w](?:[\\w-]*[\\w])?\\.)+[\\w](?:[\\w-]*[\\w])?)['\"]"
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
  - name: Jwt
    regex: "['\"](ey[A-Za-z0-9_-]{10,}\\.[A-Za-z0-9._-]{10,}|ey[A-Za-z0-9_\\/+-]{10,}\\.[A-Za-z0-9._\\/+-]{10,})['\"]"
    loaded: true

```

---

# TODO
- [ ] Support headless browser
- [ ] Add regex doc reference
- [ ] Fuzz path that are 404
- [x] Separate subdomains in the result
- [x] Optimize url collector
[//]: # (- [ ] Employ jsbeautifier)
- [x] Generate configuration file
- [x] Detect dangerous paths and avoid requesting them
- [x] Support url-finder output format, add `--detail` option
- [x] Support windows
- [x] Scan local file
- [x] Extract links via regex

---

# Change Log
## 2024.5.25 Version 1.4
- Support csv output
- Set `re` module as regex engine by default
- Support to select regex engine by configuration `handler_type`
## 2024.4.30 Version 1.3.9
- Add `--validate` option: Validate urls after the crawler finish, which helps reduce useless links
- Optimize url collector
- Optimize built-in regex
## 2024.4.29 Version 1.3.8
- Optimize log output
- Optimize the performance of `--debug` option
## 2024.4.29 Version 1.3.7
- Test on multiple python versions
- Support python 3.9~3.11
## 2024.4.29 Version 1.3.6
- Repackage

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
