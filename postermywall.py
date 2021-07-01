import io
import json
from typing import Literal

import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
import discord
import httpx
import asyncio

from selenium.webdriver.common.keys import Keys

chrome_options = Options()
# MUST BE HEADLESS AND HAVE VERY LARGE WINDOW SIZE
chrome_options.add_argument("--headless")

print("Creating browser...")
driver = webdriver.Chrome(options=chrome_options)

size_options = ["all", "poster", "a1", "a2", "a3", "a4", "album-cover", "banner-2-6", "banner-2-8", "banner-4-6",
                "business-card", "desktop-wallpaper", "desktop-wallpaper-inverted", "etsy-banner", "facebook-ad",
                "facebook-cover", "facebook-cover-video", "facebook-shared-image", "flyer-letter", "google-cover",
                "instagram-post", "kindle-cover", "large-rectangle", "leaderboard", "linkedin-banner",
                "linkedin-bg-image", "linkedin-career-cover", "medium-rectangle", "menu-half-page-legal",
                "menu-half-page-letter", "menu-half-page-wide", "menu-poster-wallboard", "pinterest-graphic",
                "presentation", "presentation-169", "square", "tabloid", "tumblr-banner", "tumblr-graphic",
                "twitter-header", "twitter-post", "us-legal", "wide-skyscraper", "youtube-channel-cover",
                "youtube-thumbnail"]

client = httpx.AsyncClient()


def format_obj(obj: dict):
    path, obj = obj
    text = obj['text'].replace('\n', '\\n')
    return f"`{'.'.join([str(node) for node in path])}`: {text}"


class Template:
    id_: str
    name: str
    description: str
    type_: Literal["image", "vide"]
    customize_url: str

    preview_url: str
    thumb_url: str

    preview_dimensions: tuple[int, int]
    thumb_dimensions: tuple[int, int]

    @classmethod
    def from_dict(cls, dict_: dict):
        out = Template()

        out.id_ = dict_["id"]
        out.name = dict_["name"]
        out.description = dict_["description"]
        out.type_ = dict_["type"]
        out.customize_url = dict_["customize_url"]

        if out.type_ == "video":
            out.preview_url = dict_["preview_video_url"]
            out.thumb_url = dict_["thumb_video_url"]
        elif out.type_ == "image":
            out.preview_url = dict_["preview_url"]
            out.thumb_url = dict_["thumb_url"]

        out.preview_dimensions = (int(dict_["preview_width"]), int(dict_["preview_height"]))
        out.thumb_dimensions = (int(dict_["thumb_width"]), int(dict_["thumb_height"]))

        return out

    @classmethod
    async def from_id(cls, id_: str):
        return Template.from_dict((await client.get(f"https://api.postermywall.com/v1/templates/{id_}?"
                                                    f"client_id={CLIENT_ID}")).json())

    def get_dc_embed(self) -> discord.Embed:
        out = discord.Embed(title=self.name, description=self.description)
        out.add_field(name="Properties", value=f"id: `{self.id_}`\n"
                                               f"customize_url: [customize_url]({self.customize_url})")

        out.add_field(name=f"Type: `{self.type_}`", value=f"preview_url: [preview_url]({self.preview_url})\n"
                                                          f"thumb_url: [thumb_url]({self.thumb_url})")
        if self.type_ == "image":
            out.set_image(url=self.preview_url)
            out.set_thumbnail(url=self.thumb_url)
        return out

    async def get_dc_file(self):
        return discord.File(fp=io.BytesIO((await client.get(self.preview_url)).content),
                            filename=f"{self.id_}.{'jpg' if self.type_ == 'image' else 'mp4'}")

    async def get_objects(self) -> list[dict]:
        print("Getting website...")
        driver.get(self.customize_url)

        set_up = """
        a = function() {
            window.hopefullyklass = this;
            this._renderAll();
        }
        fabric.Canvas.prototype._renderAll = fabric.Canvas.prototype.renderAll
        fabric.Canvas.prototype.renderAll = a
        """

        print("Waiting...")
        await asyncio.sleep(5)

        print("Click on the cookie-accept banner")
        driver.find_element_by_xpath('//*[@id="user-consent-form"]/div[2]/div[2]/a').click()

        print("Running first script...")
        driver.execute_script(set_up)

        print("Press CTRL+- to invoke renderAll function in order to get object")
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('-').key_up(Keys.CONTROL).perform()
        # ActionChains(driver).key_down(Keys.CONTROL).send_keys('-').key_up(Keys.CONTROL).perform()
        # ActionChains(driver).key_down(Keys.CONTROL).send_keys('-').key_up(Keys.CONTROL).perform()
        # ActionChains(driver).key_down(Keys.CONTROL).send_keys('+').key_up(Keys.CONTROL).perform()
        # ActionChains(driver).key_down(Keys.CONTROL).send_keys('+').key_up(Keys.CONTROL).perform()
        # ActionChains(driver).key_down(Keys.CONTROL).send_keys('+').key_up(Keys.CONTROL).perform()

        def _get_objects(object: dict, path: list[int] = None):
            path = [] if path is None else path

            if "objects" not in object:
                return [(path, object)]

            out = []
            for i, object in enumerate(object["objects"]):
                out += _get_objects(object, path + [i])

            return out

        object_json = ""
        last_e = None
        for _ in range(20):
            try:
                print("Waiting...")
                await asyncio.sleep(2)

                read = """
                return (function() {return window.hopefullyklass.toJSON();})();
                """

                print("Running second script...")
                object_json = driver.execute_script(read)
                break
            except selenium.common.exceptions.JavascriptException as e:
                last_e = e
        else:
            raise Exception(f"Getting the Canvas class failed 20 times. Aborting, last error: {last_e}")

        print("Finished!")
        return _get_objects(object_json)

    async def get_dc_attrs_embed(self) -> discord.Embed:
        out = discord.Embed(title=f"Attributes of `{self.id_}`",
                            description="\n".join([format_obj(obj) for obj in await self.get_objects()
                                                   if "text" in obj[1]]))
        if self.type_ == "image":
            out.set_image(url=self.preview_url)
            out.set_thumbnail(url=self.thumb_url)
        return out


async def search(keyword: str, type_: Literal["all", "image", "video"] = "all", size: str = "all") -> list[Template]:
    response = await client.get(f"https://api.postermywall.com/v1/templates?client_id={CLIENT_ID}&keyword={keyword}&"
                                f"type={type_}&size={size}")
    print(response.json())
    out = []
    for search_result in response.json():
        out.append(Template.from_dict(search_result))

    return out


async def main():
    template = await Template.from_id("5892940d8441e482e53b12715c06ee3f")
    out = await template.get_objects()
    print(out)


with open("client.id", "r") as f:
    CLIENT_ID = f.read()

if __name__ == "__main__":
    asyncio.run(main())
