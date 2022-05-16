from selenium.webdriver.chrome.webdriver import WebDriver
import pickle
import discord
from io import BytesIO

import seleniumutil
import google_dictionary
from context_logger import log_decorator

DICT_PREFIX = "dictionaries/"

seleniumutil.prepare()


def split_word(word: str, chars=".·*") -> list[str]:
    out = [""]
    for char in word:
        if char in chars:
            out.append("")
        elif char not in "\\":
            out[-1] += char
    return out


class Word:
    def __init__(self, syllables: list[str], ipa: str, part_of_speech: str, meaning: str,
                 example: str, force_no_stressed: bool = False):
        ipa = ipa.replace("'", "ˈ").replace("´", "ˈ").replace("`", "ˈ")

        assert "ˈ" in ipa or force_no_stressed, "Phonetic transcription doesn't show a stressed syllable."

        self.syllables = syllables
        self.ipa = ipa
        self.part_of_speech = part_of_speech
        self.meaning = meaning
        self.example = example

    def get_data_key(self):
        return "".join(self.syllables)

    def get_display_name(self):
        return "·".join(self.syllables)

    def get_formatted_syllabic_structure(self):
        total_text = []
        total_ipa = []
        for i in range(len(self.syllables)):
            text = self.syllables[i]
            ipa = "".join(self.ipa[i]).replace("_", "")

            space = max(len(text), len(ipa))

            total_text.append(text.ljust(space, " "))
            total_ipa.append(ipa.ljust(space, " "))
        return f'`WORD: {" ".join(total_text)}`\n`PHON: {" ".join(total_ipa)}`'

    def get_command(self):
        return f"!wörterbuch render {self.get_display_name()!r} {self.ipa!r} {self.part_of_speech!r} " \
               f"{self.meaning!r} {self.example!r}"

    @log_decorator("Getting DC File")
    async def get_dc_file(self, filename: str = "image.png"):
        display_name = self.get_display_name()
        bytes_arr = await seleniumutil.run_function(
            lambda webdriver: google_dictionary.get_image(webdriver,
                                                          display_name, self.ipa, self.part_of_speech, self.meaning,
                                                          self.example)
        )
        stream = BytesIO(bytes_arr)
        return discord.File(stream, filename=filename)

    @log_decorator("Getting DC Embed")
    async def get_dc_embed(self, message: str = "") -> tuple[discord.Embed, discord.File]:
        image = await self.get_dc_file("image.png")
        display_name = self.get_display_name()

        description = (f"{message}\n\n" if message else "") + \
                      f"word: `{display_name}`\n" \
                      f"ipa: `{self.ipa}`\n" \
                      f"part of speech: `{self.part_of_speech}`\n" \
                      f"meaning: `{self.meaning}`\n" \
                      f"example: `{self.example}`\n" \
                      f"command: `{self.get_command()}`"

        word_embed = discord.Embed(title=display_name, description=description, color=discord.Color(0x00FF00))
        word_embed.set_image(url=f"attachment://image.png")

        return word_embed, image


class Dictionary:
    def __init__(self, name: str, data: dict = None):
        self._name = name
        self._data: dict[str: Word] = {} if data is None else data

        self.save()

    @classmethod
    def from_file(cls, name: str):
        with open(f"{DICT_PREFIX}{name}.dict", "rb") as f:
            data = pickle.load(f)

        return Dictionary(name, data)

    def save(self):
        with open(f"{DICT_PREFIX}{self._name}.dict", "wb") as f:
            pickle.dump(self._data, f)

    def add_word(self, word: Word):
        self._data.update({word.get_data_key(): word})
        self.save()

    def remove_word(self, word: str):
        del self._data[word]
        self.save()

    def search_word(self, query: str) -> list[Word]:
        if query in self._data:
            return [self._data[query]]
        else:
            out = []
            query = query.lower()
            for key, word in self._data.items():
                key = key.lower()
                if key == query or key.startswith(query) or query in key:
                    out.append(word)
            return out

    def __iter__(self):
        return iter(self._data.values())

    def __len__(self):
        return len(self._data)
