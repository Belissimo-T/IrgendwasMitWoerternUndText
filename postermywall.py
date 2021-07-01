import io
import json
from typing import Literal

import msgpack
import selenium.common.exceptions
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
import discord
import httpx
import asyncio

from selenium.webdriver.common.keys import Keys

import cachelib

chrome_options = Options()
# MUST BE HEADLESS AND HAVE VERY LARGE WINDOW SIZE
# chrome_options.add_argument("--headless")

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


def render_update():
    print("Invoking renderAll")
    ActionChains(driver).key_down(Keys.CONTROL).send_keys('-').key_up(Keys.CONTROL).perform()
    ActionChains(driver).key_down(Keys.CONTROL).send_keys('+').key_up(Keys.CONTROL).perform()


def zoom(target: float = 100) -> int:
    el = driver.find_element_by_xpath('// *[ @ id = "poster-nav-view"] / div')

    d = target - int(el.get_attribute('innerHTML')[:-1])

    while 1:
        current = int(el.get_attribute('innerHTML')[:-1])
        dnew = target - current
        if -d < dnew - d:
            return current

        if dnew < 0:
            ActionChains(driver).key_down(Keys.CONTROL).send_keys('-').key_up(Keys.CONTROL).perform()
        elif dnew > 0:
            ActionChains(driver).key_down(Keys.CONTROL).send_keys('+').key_up(Keys.CONTROL).perform()
        else:
            return current


async def prepare(url: str):
    print("Getting website...")
    driver.get(url)

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

    print("Click on the cookie-accept banner...")
    try:
        driver.find_element_by_xpath('//*[@id="user-consent-form"]/div[2]/div[2]/a').click()
    except selenium.common.exceptions.ElementNotInteractableException:
        print("...already accepted")

    print("Pause")
    try:
        driver.find_element_by_xpath('//*[@id="seekbar-view"]/button[2]').click()
    except selenium.common.exceptions.ElementNotInteractableException:
        print("...Not a video")

    print("Running first script...")
    driver.execute_script(set_up)

    render_update()

    for _ in range(20):
        try:
            driver.execute_script("return window.hopefullyklass.toJSON();")
            return
        except selenium.common.exceptions.JavascriptException as e:
            print(e)

            print("Render update...")
            render_update()

            print("Waiting...")
            await asyncio.sleep(2)
    else:
        raise Exception("Could not get the Canvas object. Tried 20 times. Aborting.")


def screenshot() -> bytes:
    zoom(100)
    return driver.find_element_by_id("whiteboard").screenshot_as_png


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
        if data := cachelib.get(("preview", self.id_)):
            ...
        else:
            data = (await client.get(self.preview_url)).content
            cachelib.save(data, ("preview", self.id_))

        return discord.File(fp=io.BytesIO(data),
                            filename=f"{self.id_}.{'jpg' if self.type_ == 'image' else 'mp4'}")

    async def get_objects(self) -> list[dict]:
        def _get_objects(object: dict, path: list[int] = None):
            path = [] if path is None else path

            if "objects" not in object:
                return [(path, object)]

            out = []
            for i, object in enumerate(object["objects"]):
                out += _get_objects(object, path + [i])

            return out

        if objts := cachelib.get(("objects", self.id_)):
            return _get_objects(msgpack.loads(objts))

        await prepare(self.customize_url)

        print("Running second script...")
        object_json = driver.execute_script("return window.hopefullyklass.toJSON();")

        print("Finished!")

        cachelib.save(msgpack.dumps(object_json), ("objects", self.id_))

        return _get_objects(object_json)

    async def get_dc_attrs_embed(self) -> discord.Embed:
        out = discord.Embed(title=f"Attributes of `{self.id_}`",
                            description="\n".join([format_obj(obj) for obj in await self.get_objects()
                                                   if "text" in obj[1]]))

        out.set_image(url=self.preview_url)
        out.set_thumbnail(url=self.thumb_url)
        return out

    async def modify(self, modifications: list[tuple[list[int], str]]):
        await prepare(self.customize_url)

        for path, mod in modifications:
            modstr = f"window.hopefullyklass{''.join([f'._objects[{i}]' for i in path])}.setText({mod!r})"
            print(modstr)
            driver.execute_script(modstr)

        render_update()

    async def get_dc_modify_file(self, modifications: list[tuple[list[int], str]]) -> discord.File:
        if data := cachelib.get(("modify", self.id_, modifications)):
            ...
        else:
            zoom_factor = 4

            print("Resizing window...")
            driver.set_window_size(1600 * zoom_factor, 900 * zoom_factor)

            print("Scaling window...")
            driver.execute_script(f"document.body.style.zoom='{zoom_factor}'")

            await self.modify(modifications)

            data = screenshot()

            cachelib.save(data, ("modify", self.id_, modifications))

        return discord.File(fp=io.BytesIO(data), filename="image.png")


async def search(keyword: str, type_: Literal["all", "image", "video"] = "all", size: str = "all") -> list[Template]:
    response = await client.get(f"https://api.postermywall.com/v1/templates?client_id={CLIENT_ID}&keyword={keyword}&"
                                f"type={type_}&size={size}")
    print(response.json())
    out = []
    for search_result in response.json():
        out.append(Template.from_dict(search_result))

    return out


with open("client.id", "r") as f:
    CLIENT_ID = f.read()
