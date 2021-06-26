import os
import random

import requests
from PIL import Image, ImageDraw, ImageFont, PngImagePlugin
from io import BytesIO

# https://web.archive.org/web/20160313023518/http://fonts.debian.net/free-fonts-20091020.tar.gz

if os.name == "nt":
    path = "C:/Windows/Fonts"
else:
    path = "fonts/"

_, _, (fonts, ) = zip(*list(os.walk(path)))


def get_image(width: int = 1600, height: int = 900, blur: int = None) -> bytes:
    blur = random.randint(0, 3) if blur is None else blur

    url = f"https://picsum.photos/{width}/{height}.jpg" + (f"?blur={blur}" if blur else "")
    data = requests.get(url).content
    return data


def get_lines(text: str, font: ImageFont.ImageFont, max_width: int):
    words = text.split(" ")

    lines: list[str] = [""]
    for word in words:
        if font.getsize(lines[-1] + " " + word)[0] > max_width:
            lines.append(word)
        else:
            lines[-1] += " " + word

    return lines


def get_zitat(text: str, author: str):
    # breakpoint()
    dim = (1600, 900)
    image_data = get_image(*dim)
    image: PngImagePlugin.PngImageFile = Image.open(BytesIO(image_data))
    draw = ImageDraw.Draw(image)

    pos = (int(dim[0]/2), 100)

    size = random.randint(80, 150)
    random.shuffle(fonts)
    for font_name in fonts:
        try:
            font = ImageFont.truetype(font_name, size)
            break
        except OSError:
            print(f"Couldn't open {font_name}")
    else:
        raise OSError("Stopped trying opening fonts. No fonts openable.")
    lines = "\n".join(get_lines(text, font, dim[0] - 200))

    avg_color = image.resize((1, 1), resample=Image.LINEAR).getpixel((0, 0))

    color = (255, 255, 255) if sum(avg_color) < sum((128, 128, 128)) else (0, 0, 0)

    draw.multiline_text(xy=pos, text=lines + f"\n- {author}",
                        fill=color, font=font,# anchor="mt",
                        align="center", stroke_width=2, stroke_fill=tuple((255 - rgb) for rgb in color))

    img_byte_arr = BytesIO()
    image.save(img_byte_arr, format="png")
    return img_byte_arr.getvalue()
