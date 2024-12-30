from crawler import start_crawl


if __name__ == "__main__":
    """
    クローラー使用例
    https://playwright.dev/python/docs/intro から始めて、
    https://playwright.dev/python/docs/ のURLプレフィックスを持つファイルを集めたい場合
    """
    start_crawl(
        props={
            'host': 'https://playwright.dev',
            'path_prefix': '/python/docs/',
            'start_url': 'https://playwright.dev/python/docs/intro',
            'languages': ["Python"],
            'projects': ['Playwright']
        }
    )
