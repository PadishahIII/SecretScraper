import csv

from secretscraper.entity import Secret, create_url
from secretscraper.output_formatter import Formatter
from secretscraper.util import Range


def test_formatter_status_filter_matches_any_allowed_range(local_http_server_base_url: str):
    formatter = Formatter([Range(200, 201), Range(300, 400)])

    ok = create_url(f"{local_http_server_base_url}/ok")
    ok.response_status = "200"

    redirect = create_url(f"{local_http_server_base_url}/redirect")
    redirect.response_status = "302"

    server_error = create_url(f"{local_http_server_base_url}/error")
    server_error.response_status = "500"

    not_found = create_url(f"{local_http_server_base_url}/not-found")
    not_found.response_status = "404"

    assert formatter.filter(ok) is True
    assert formatter.filter(redirect) is True
    assert formatter.filter(server_error) is False
    assert formatter.filter(not_found) is False


def test_output_csv_includes_urls_that_only_exist_in_secret_results(tmp_path, local_http_server_base_url: str):
    formatter = Formatter()
    url = create_url(f"{local_http_server_base_url}/leaf")
    url.response_status = "200"
    url.title = "Leaf"
    url.content_length = 123
    url.content_type = "text/html"
    outfile = tmp_path / "result.csv"

    formatter.output_csv(outfile, {}, {url: {Secret(type="Token", data="abc123")}})

    with outfile.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert rows[0] == [
        "URL",
        "Title",
        "Response Code",
        "Content Length",
        "Content Type",
        "Secrets",
    ]
    assert rows[1] == [
        f"{local_http_server_base_url}/leaf",
        "Leaf",
        "200",
        "123",
        "text/html",
        "Token: abc123",
    ]
