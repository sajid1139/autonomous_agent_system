async def run(content: str, title: str = "Report") -> str:
    lines = [l.strip() for l in content.strip().split("\n") if l.strip()]
    sections = []
    current = []
    for line in lines:
        if len(line) < 60 and line.endswith(":"):
            if current:
                sections.append("\n".join(current))
                current = []
            sections.append(f"## {line.rstrip(':')}")
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current))
    body = "\n\n".join(sections)
    return f"# {title}\n\n{body}"
