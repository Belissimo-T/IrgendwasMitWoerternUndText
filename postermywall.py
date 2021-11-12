import asyncio
import io
import time
from typing import Literal

import discord
import httpx
import msgpack
import selenium.common.exceptions
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.keys import Keys

import cachelib
import belissibot_framework
import seleniumutil
from context_logger import Logger, get_current_logger, log, log_decorator

seleniumutil.prepare()

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


@log_decorator("Invoking renderAll js method")
def render_update(webdriver: WebDriver):
    with log("Zooming out"):
        ActionChains(webdriver).key_down(Keys.CONTROL).send_keys('-').key_up(Keys.CONTROL).perform()
    with log("Sleeping 1s"):
        time.sleep(1)
    with log("Zooming in"):
        ActionChains(webdriver).key_down(Keys.CONTROL).send_keys('+').key_up(Keys.CONTROL).perform()


def zoom(webdriver: WebDriver, target: float = 100) -> int:
    el = webdriver.find_element('// *[ @ id = "poster-nav-view"] / div')

    d = target - int(el.get_attribute('innerHTML')[:-1])

    while 1:
        current = int(el.get_attribute('innerHTML')[:-1])
        dnew = target - current
        if -d < dnew - d:
            return current

        if dnew < 0:
            ActionChains(webdriver).key_down(Keys.CONTROL).send_keys('-').key_up(Keys.CONTROL).perform()
        elif dnew > 0:
            ActionChains(webdriver).key_down(Keys.CONTROL).send_keys('+').key_up(Keys.CONTROL).perform()
        else:
            return current


@log_decorator(lambda args: f"Preparing website {args['url']}")
async def prepare(webdriver: WebDriver, url: str):
    with log("Getting website"):
        webdriver.get(url)

    set_up = """
    a = function() {
        window.hopefullyklass = this;
        this._renderAll();
    }
    fabric.Canvas.prototype._renderAll = fabric.Canvas.prototype.renderAll
    fabric.Canvas.prototype.renderAll = a
    """

    log("Waiting")
    await asyncio.sleep(5)

    with log("Clicking on the cookie-accept banner"):
        try:
            webdriver.find_element('//*[@id="user-consent-form"]/div[2]/div[2]/a').click()
            log("success ✅")
        except selenium.common.exceptions.ElementNotInteractableException:
            log("already accepted 😐")

    with log("Pausing"):
        try:
            webdriver.find_element('//*[@id="seekbar-view"]/button[2]').click()
            log("success ✅")
        except selenium.common.exceptions.ElementNotInteractableException:
            log("not a video 😐")

    with log("Running first script"):
        webdriver.execute_script(set_up)

    render_update(webdriver)

    maxtries = 20
    with log("Checking if method worked"):
        for try_ in range(maxtries):
            with log(f"Try: {try_}/{maxtries}"):
                try:
                    webdriver.execute_script("return window.hopefullyklass.toJSON();")
                    log("success ✅")
                    return
                except selenium.common.exceptions.JavascriptException as e:
                    log(f"didn't work 😢")

                    render_update(webdriver)

                    print("Waiting")
                    await asyncio.sleep(2)
        else:
            raise Exception("Could not get the Canvas object. Tried 20 times. Aborting.") from e


@log_decorator("Screenshotting")
def screenshot(webdriver: WebDriver) -> bytes:
    zoom(webdriver, 100)
    # noinspection PyTypeChecker
    return webdriver.find_element("whiteboard").screenshot_as_png


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
        else:
            out.set_image(url="attachment://image.png")
        return out

    async def get_dc_file(self, message: discord.Message):
        if self.type_ == "image":
            if data := cachelib.get(("preview", self.id_)):
                ...
            else:
                data = (await client.get(self.preview_url)).content
                cachelib.save(data, ("preview", self.id_))

            return discord.File(fp=io.BytesIO(data),
                                filename=f"{self.id_}.{'jpg' if self.type_ == 'image' else 'mp4'}")
        else:
            log_ = await belissibot_framework.Log.create(message=message)
            with Logger(get_current_logger().prefix + "_", log_function=log_.log):
                file = await self.get_dc_modify_file([])
            await log_.close(delete_after=10)
            return file

    async def get_objects(self, webdriver: WebDriver) -> list[dict]:
        def _get_objects(object_: dict, path: list[int] = None):
            path = [] if path is None else path

            if "objects" not in object_:
                return [(path, object_)]

            out = []
            for i, object_ in enumerate(object_["objects"]):
                out += _get_objects(object_, path + [i])

            return out

        if objts := cachelib.get(("objects", self.id_)):
            return _get_objects(msgpack.loads(objts))

        await prepare(webdriver, self.customize_url)

        with log("Getting canvas object"):
            object_json = webdriver.execute_script("return window.hopefullyklass.toJSON();")

        log("Finished!")

        cachelib.save(msgpack.dumps(object_json), ("objects", self.id_))

        return _get_objects(object_json)

    async def get_dc_attrs_embed(self) -> discord.Embed:
        objects = await seleniumutil.run_function(lambda webdriver: asyncio.run(self.get_objects(webdriver)))
        out = discord.Embed(title=f"Attributes of `{self.id_}` ({self.name})",
                            description="\n".join([format_obj(obj) for obj in objects
                                                   if "text" in obj[1]]))

        if self.type_ == "image":
            out.set_image(url=self.preview_url)
            out.set_thumbnail(url=self.thumb_url)
        else:
            out.set_image(url="attachment://image.png")

        return out

    @log_decorator("Modifying")
    async def modify(self, webdriver: WebDriver, modifications: list[tuple[list[int], str]]):
        await prepare(webdriver, self.customize_url)

        with log("Modifying"):
            for path, mod in modifications:
                with log(f"{path!r}: {mod!r}"):
                    modstr = f"window.hopefullyklass{''.join([f'._objects[{i}]' for i in path])}.setText({mod!r})"
                    log(modstr)
                    webdriver.execute_script(modstr)

        render_update(webdriver)

    async def _get_modify_data(self, webdriver: WebDriver, modifications: list[tuple[list[int], str]]):
        await self.modify(webdriver, modifications)

        return screenshot(webdriver)

    async def get_dc_modify_file(self, modifications: list[tuple[list[int], str]]) -> discord.File:
        if data := cachelib.get(("modify", self.id_, modifications)):
            ...
        else:
            data = await seleniumutil.run_function(
                lambda webdriver: asyncio.run(self._get_modify_data(webdriver, modifications)), scale=4)

            cachelib.save(data, ("modify", self.id_, modifications))

        return discord.File(fp=io.BytesIO(data), filename="image.png")


async def search(keyword: str, type_: Literal["all", "image", "video"] = "all", size: str = "all") -> list[Template]:
    response = await client.get(f"https://api.postermywall.com/v1/templates?client_id={CLIENT_ID}&keyword={keyword}&"
                                f"type={type_}&size={size}")
    out = []
    for search_result in response.json():
        out.append(Template.from_dict(search_result))

    return out


with open("client.id", "r") as f:
    CLIENT_ID = f.read()
