from PIL import ImageFont


def get_lines(text: str, font: ImageFont.ImageFont, max_width: int) -> tuple[list[str], tuple[int, int]]:
    words = text.split(" ")

    lines: list[str] = [""]
    bbox = (0, 0)
    for word in words:
        if (bbox := font.getsize(lines[-1] + " " + word))[0] > max_width:
            lines.append(word)
        else:
            lines[-1] += " " + word

    return lines, bbox
