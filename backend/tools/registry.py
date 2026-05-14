from tools import search, parser, gen

tools: dict = {}

def register(name: str, fn):
    tools[name] = fn

def get(name: str):
    return tools.get(name)

register("search", search.run)
register("parser", parser.run)
register("gen", gen.run)
register("scrape", parser.scrape)
register("scrape_js", parser.scrape_js)
register("extract", parser.extract)
