from secretscraper.handler import HyperscanRegexHandler, ReRegexHandler


def test_re_regex_handler_benchmark(regex_dict, resource_text, benchmark):
    handler = ReRegexHandler(rules=regex_dict)
    benchmark(handler.handle, resource_text)


def test_hyper_regex_handler_benchmark(regex_dict, resource_text, benchmark):
    handler = HyperscanRegexHandler(rules=regex_dict, lazy_init=False)
    benchmark(handler.handle, resource_text)
