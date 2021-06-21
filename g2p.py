import requests
from io import BytesIO
from bs4 import BeautifulSoup

url = 'https://clarin.phonetik.uni-muenchen.de/BASWebServices/services/runG2P'


def g2p(word, lng):
    multiple_files = [
        ('i', ('text.txt', BytesIO(word.encode()))),
        ('lng', (None, BytesIO(lng.encode()))),
        ('outsym', (None, BytesIO("ipa".encode()))),
        ('oform', (None, BytesIO("txt".encode())))
    ]
    r = requests.post(url, files=multiple_files)

    parsed_html = BeautifulSoup(r.text, features="lxml")
    assert parsed_html.body.find('success').text == "true", f"Something went wrong: {parsed_html}"
    download_link = parsed_html.body.find('downloadlink').text

    return requests.get(download_link).content.decode("utf-8").replace(" ", "")


if __name__ == '__main__':
    while 1:
        word = input("word>")
        lng = input("lang (zb. deu/eng-US)>")

        print(g2p(word, lng))
