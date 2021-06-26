import os
from typing import Union
import pickle
import requests
from io import BytesIO
from bs4 import BeautifulSoup
import unicodedata

url = 'https://clarin.phonetik.uni-muenchen.de/BASWebServices/services/runG2P'


def save_cache():
    with open("cache.dat", "wb") as f:
        pickle.dump(cache, f)

if not os.path.exists("cache.dat"):
    cache = {}
    save_cache()

with open("cache.dat", "rb") as f:
    cache = pickle.load(f)


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')


def g2p(word, lng):
    query = (word, lng)
    if query in cache:
        return cache[query]

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

    out = requests.get(download_link).content.decode("utf-8").split(" ")
    cache.update({query: out})
    save_cache()
    return out


VOWELS = "eiyɨʉɯuɪʏʊeøɘɵɤoeøəɤoɛœɜɞʌɔæɐaɶaɑɒ"  # taken from wikipedia, no guarantee to be accurate


# Hal lo
# Ver ant  wor tung
# fɛɐ ʔant vɔɐ tʊŋ
# f ɛɐʔa ntv ɔɐ t ʊ ŋ

def has_vowels(syllable: Union[list[str], str]):
    for phonemes in syllable:
        for phoneme in phonemes:
            if phoneme in VOWELS:
                return True
    return False


def get_syllables(phonemes: list[str], word: str):
    assert len(phonemes) == len(word)

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

        # add

        phoneme_syllables[-1] += phonemes[i]
        word_syllables[-1] += word[i]

    return phoneme_syllables, word_syllables


if __name__ == '__main__':
    word = input("word>")
    lng = input("lang (zb. deu/eng-US)>")

    phonemes = g2p(word, lng)
    # phonemes = list("fɛɐʔantvɔɐtʊŋ")
    # phonemes = ['l', 'aʊ', '_', 'f', 'ə', 'n\n']

    print(get_syllables(phonemes, word))
