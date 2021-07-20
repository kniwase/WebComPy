from javascript import RegExp, String


camel_pattern = RegExp.new(r'[A-Z]+', 'g')


def camel_replacer(match: str, *_: str) -> str:
    return '-' + match.lower()


def convert_camel_to_kebab(text: str):
    return String.new(text).replace(camel_pattern, camel_replacer).strip('-')


def convert_snake_to_kebab(text: str):
    return String.new(text).replace('_', '-')
