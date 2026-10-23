from collector import collect_page
from settings import load_config


def main():
    path = collect_page(input('Paste an official venue webpage URL: '), load_config())
    print(path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()
