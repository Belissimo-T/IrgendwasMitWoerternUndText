import os
from typing import Union
import pickle
import requests
from io import BytesIO
from bs4 import BeautifulSoup
import unicodedata

from wörterbuch import Word

url = 'https://clarin.phonetik.uni-muenchen.de/BASWebServices/services/runG2P'


def save_cache():
    with open("cache.dat", "wb") as f:
        pickle.dump(cache, f)


if not os.path.exists("cache.dat"):
    cache = {}
    save_cache()

else:
    with open("cache.dat", "rb") as f:
        cache = pickle.load(f)


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def process_response(response: str) -> list[str]:
    print(response)
    return list(map(lambda x: x.replace(" ", "").replace("+", "").strip(), response.replace("?", "ʔ").split(" ")))


def g2p(word, lng):
    query = (word, lng)
    if query in cache:
        return process_response(cache[query])

    multiple_files = [
        ('i', ('text.txt', BytesIO(word.encode()))),
        ('lng', (None, BytesIO(lng.encode()))),
        ('outsym', (None, BytesIO("ipa".encode()))),
        ('oform', (None, BytesIO("txt".encode()))),
        ('align', (None, BytesIO("yes".encode())))
    ]
    r = requests.post(url, files=multiple_files)

    parsed_html = BeautifulSoup(r.text, features="lxml")
    assert parsed_html.body.find('success').text == "true", f"Something went wrong: {parsed_html}"
    download_link = parsed_html.body.find('downloadlink').text

    outstr = requests.get(download_link).content.decode("utf-8")

    cache.update({query: outstr})
    save_cache()

    return process_response(outstr)


VOWELS = "ɯəʏuʌɑʉyɤɞɪøɒoʊɵeɔœiaɶɨɜæɛɐɘaeiouAEIOU"


def has_vowels(syllable: Union[list[str], str]):
    for phonemes in syllable:
        for phoneme in phonemes:
            if phoneme in VOWELS:
                return True
    return False


def get_syllables(phonemes: list[str], word: str):
    assert len(phonemes) == len(word), f"Length of phonemes {phonemes!r} and word {word!r} do not match."

    phoneme_syllables: list[str] = [""]
    word_syllables: list[str] = [""]
    for i in range(len(phonemes)):
        # if current syllable has no vowel, keep adding phonemes
        if not has_vowels(phoneme_syllables[-1]):
            if phonemes[i] != "_": phoneme_syllables[-1] += phonemes[i]
            word_syllables[-1] += word[i]
            continue

        # create a new syllable if next phoneme is a vowel
        if len(phonemes) > i + 1 and has_vowels(phonemes[i + 1]):
            phoneme_syllables.append("")
            word_syllables.append("")

        # add current phoneme and char to the current syllable
        phoneme_syllables[-1] += phonemes[i]
        word_syllables[-1] += word[i]

    return phoneme_syllables, word_syllables


def main():
    lng = input("lang (ex. deu/eng-US)>")

    while 1:
        word = input("word>")

        phonemes = g2p(word, lng)

        phon_syl, word_syl = get_syllables(phonemes, word)

        print(Word.get_formatted_syllabic_structure(phon_syl, word_syl))


if __name__ == '__main__':
    main()
