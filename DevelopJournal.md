# # 2024.4.30
- Optimize url collector, the regex is optimized, should validate the found routes
- Use aiocache to cache http requests
- Validate urls after the crawler finish
# 2024.4.29
- [ ] Support 3.8~3.11
  - Current support 3.9~3.11
- [x] Add more CLI tests
  - test_facade
  - test_local_scan
-
# 2024.4.28
- [x] Prettify output, add `--detail` option
- [x] Optimize crawler
  - [x] Filter 404 by default
  - [x] Remove dirty data in url
  - [x] do not seek urls in static resources and js
  - [x] just process urls with response 200

# 2024.4.26
- **New Features**
  - [x] Support to scan local files

# 2024.4.15
- Add status to url result
- All crawler test passed

# TODO
- [ ] Optimize output
- [x] Log file perform not good
- [x] Debug option perform not good
- [x] Remove logpath option

# ISSUES
## [Not Sovled] Windows+Python3.11: No module named secretscraper.__main__; 'secretscraper' is a package and cannot be directly executed
On Windows, python3.10 works fine, python3.11 occur this issue.
