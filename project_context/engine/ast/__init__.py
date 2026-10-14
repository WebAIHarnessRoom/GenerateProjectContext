from .python import summarize_python

AST_PARSERS = {
    "python": summarize_python,
    "none": None,
}


def get_parser(name):
    return AST_PARSERS.get(name or "none")