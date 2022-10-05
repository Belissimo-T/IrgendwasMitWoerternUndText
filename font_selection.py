import io
import os
import random
import shutil
import time

import discord
from PIL import Image, ImageDraw, ImageFont
import dataclasses
from text_tools import get_lines

DEFAULT_TESTTEXT = "AaBbCc DdEeFf GgHhIi JjKkLl MmNnOo PpQqRr SsTtUu VvWwXx YyZz ÄäÖöÜüẞß !?.-"


@dataclasses.dataclass
class Font:
    font_filepath: str

    @property
    def name(self):
        name, _ = os.path.splitext(os.path.basename(self.font_filepath))
        return name

    def get_example_image(self, dimensions=(1600, 900),
                          font_size=78,
                          text=DEFAULT_TESTTEXT
                          ) -> Image:
        img = Image.new("RGB", dimensions, color=(255, 255, 255))
        d = ImageDraw.Draw(img)

        font = ImageFont.truetype(self.font_filepath, font_size)

        # noinspection PyTypeChecker
        lines, bbox = get_lines(text, font, dimensions[0] * .95)  # 5% padding

        # text at center of image
        d.multiline_text((dimensions[0] / 2, dimensions[1] / 2), "\n".join(lines), fill=(0, 0, 0), font=font,
                         anchor="mm", align="center")

        return img

    def get_embed(self, testtext: str = DEFAULT_TESTTEXT):
        out = discord.Embed(title=f"Font `{self.name}`", color=discord.Color.purple(),
                            description=f"Review this font by pressing the buttons below. The displayed text is:\n"
                                        f"```\n{testtext}```")
        out.set_image(url=f"attachment://{self.name}.png")

        return out

    def get_dc_image(self, **kwargs):
        png_bytes = io.BytesIO()
        self.get_example_image(**kwargs).save(png_bytes, format="PNG")

        return discord.File(io.BytesIO(png_bytes.getvalue()), filename=f"{self.name}.png")

    def moved(self, new_dir: str):
        _, name = os.path.split(self.font_filepath)

        return Font(os.path.join(new_dir, name))

    def __eq__(self, other):
        return self.name == other.name

    def __repr__(self):
        return f"Font({self.name!r})"


@dataclasses.dataclass
class FontDir:
    base_dir: str
    dir_name: str

    def __post_init__(self):
        os.makedirs(self.dir_path, exist_ok=True)

    @property
    def dir_path(self):
        return os.path.join(self.base_dir, self.dir_name)

    @property
    def font_paths(self):
        return [os.path.join(self.dir_path, font) for font in os.listdir(self.dir_path)]

    def random_path(self):
        candidate_font_paths = self.font_paths

        try:
            return random.choice(candidate_font_paths)
        except IndexError as e:
            raise NoMoreCandidatesError() from e

    def random_font(self):
        return Font(self.random_path())

    @property
    def fonts(self):
        return [Font(font_path) for font_path in self.font_paths]

    @property
    def font_count(self):
        return len(self.font_paths)


class NoMoreCandidatesError(Exception): ...


class FontNotStagedError(Exception): ...


class NoAcceptedFontsError(Exception): ...


class FontSelector:
    """
    Candidate -1-> Staging -2-> Accepted/Rejected
        1. FS.get_next_candidate()
        2. FS.accept() / FS.reject()
    """

    def __init__(self, working_dir: str = "fonts"):
        self.working_dir = working_dir

        os.makedirs(self.working_dir, exist_ok=True)

        self.candidates = FontDir(self.working_dir, "candidates")
        self.staging = FontDir(self.working_dir, "staging")
        self.accepted = FontDir(self.working_dir, "accepted")
        self.excluded = FontDir(self.working_dir, "excluded")

        self.remove_old_from_staging()

    def remove_old_from_staging(self):
        for font in self.staging.font_paths:
            if time.time() - 600 > os.stat(font).st_mtime:
                self.unstage(Font(font))

    @property
    def total_font_count(self):
        return (self.candidates.font_count
                + self.staging.font_count
                + self.accepted.font_count
                + self.excluded.font_count)

    def stage_next_candidate(self) -> Font:
        self.remove_old_from_staging()

        while 1:
            candidate = self.candidates.random_font()

            try:
                _ = ImageFont.truetype(candidate.font_filepath, 30)
                return self.stage(candidate)
            except OSError:
                self.reject(candidate)

    def stage(self, font: Font):
        assert font in self.candidates.fonts, f"Font {font!r} not in candidates."

        shutil.move(font.font_filepath, self.staging.dir_path)

        return font.moved(self.staging.dir_path)

    def unstage(self, font: Font):
        assert font in self.staging.fonts, f"Font {font!r} not staging."

        shutil.move(font.font_filepath, self.candidates.dir_path)

    def relocalize(self, font: Font) -> Font:
        if font in self.accepted.fonts:
            return font.moved(self.accepted.dir_path)
        elif font in self.excluded.fonts:
            return font.moved(self.excluded.dir_path)
        elif font in self.staging.fonts:
            return font.moved(self.staging.dir_path)
        elif font in self.candidates.fonts:
            return font.moved(self.candidates.dir_path)

        assert False, f"Invalid state: Font {font!r} mysteriously disappeared."

    def accept(self, font: Font):
        shutil.move(self.relocalize(font).font_filepath, self.accepted.dir_path)

    def reject(self, font: Font):
        shutil.move(self.relocalize(font).font_filepath, self.excluded.dir_path)


def get_font_review_text(fs: FontSelector) -> str:
    total, accepted, excluded, staged = fs.total_font_count, fs.accepted.font_count, fs.excluded.font_count, \
                                        fs.staging.font_count

    return (f"Of `{total:_}` fonts:\n"
            f" - `{accepted:_}` (`{accepted / total:.1%}`) have been accepted\n"
            f" - `{excluded:_}` (`{excluded / total:.1%}`) have been excluded\n"
            f" - `{staged:_}` (`{staged / total:.1%}`) are currently staged")
