import io
from PIL import Image, PngImagePlugin
from io import BytesIO
import selenium.common.exceptions
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By

import cachelib
from context_logger import log


def get_image(webdriver: WebDriver, word, ipa, part_of_speech, meaning, example, zoom=3):
    hash_obj = (word, ipa, part_of_speech, meaning, example, zoom)

    if data := cachelib.get(hash_obj):
        return data

    with log("Calling google for base site"):
        webdriver.get("https://www.google.de/search?q=laufen+definition")

    with log("Click on the agree button"):
        try:
            log("Finding element 🔍")
            i_agree = webdriver.find_element(By.XPATH, '//*[@id="L2AGLb"]')
            i_agree.click()
            log("Success ✅")
        except selenium.common.exceptions.NoSuchElementException:
            log("Already agreed 😐")

    with log("Finding the base dictionary element"):
        frame = webdriver.find_element(By.CLASS_NAME, "lr_container").find_elements(By.XPATH, "./*")[2]

    example = f'"{example}"'
    pad = 5 * zoom

    xpaths_changes = {"div/div[2]/div[1]/div/span": word,
                      "div/div[2]/div[2]/span/span": ipa,
                      "div/div[4]/div/div/div/div/div/i/span": part_of_speech,
                      "div/div[4]/div/div/ol/li[1]/div/div/div[1]/div[2]/div/div[1]/span": meaning,
                      "div/div[4]/div/div/ol/li[1]/div/div/div[1]/div[2]/div/div[2]/div": example}

    with log("Changing text"):
        for xpath in xpaths_changes:
            change = xpaths_changes[xpath]
            log(f"{xpath} to {change}")

            element = frame.find_element_by_xpath(xpath)
            # change text of element
            webdriver.execute_script(f"arguments[0].innerText = '{change}'", element)

    log("Resizing window")
    webdriver.set_window_size(1600 * zoom, 900 * zoom)

    log("Scaling window")
    webdriver.execute_script(f"document.body.style.zoom='{zoom}'")

    log("Scrolling frame into view")
    ActionChains(webdriver).move_to_element(frame).perform()
    # driver.execute_script("arguments[0].scrollIntoView(true);", frame)

    with log("Taking screenshot"):
        location = frame.location
        size = frame.size
        log("Getting png")
        png = webdriver.get_screenshot_as_png()  # saves screenshot of entire page

        log("Opening with PIL")
        im: PngImagePlugin.PngImageFile = Image.open(BytesIO(png))

        left = location['x'] * zoom - pad
        top = location['y'] * zoom - pad
        right = (location['x'] + size['width']) * zoom + pad
        bottom = (location['y'] + size['height']) * zoom + pad

        log("Cropping")
        im = im.crop((left, top, right, bottom))

        log("Searching for black")
        white = (255, 255, 255, 255)
        for x in range(im.width - 1, -1, -1):
            for y in range(0, im.height):
                if im.getpixel((x, y)) != white:
                    break
            else:
                continue
            break
        else:
            raise Exception("Screenshot is blank, maybe you overdid the zoom?")

        log("Cropping again")
        im = im.crop((0, 0, x + pad, im.height))

        log("Saving")
        img_byte_arr = io.BytesIO()
        im.save(img_byte_arr, format="png")  # saves new cropped image

    log("Finished!")

    out = img_byte_arr.getvalue()

    cachelib.save(out, hash_obj)

    return out
