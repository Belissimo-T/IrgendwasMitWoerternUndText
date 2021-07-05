import io
from PIL import Image, PngImagePlugin
from io import BytesIO

from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.webdriver import WebDriver

import cachelib


def get_image(webdriver: WebDriver, word, ipa, part_of_speech, meaning, example, zoom=3):
    hash_obj = (word, ipa, part_of_speech, meaning, example, zoom)

    if data := cachelib.get(hash_obj):
        return data

    print("Calling google for base site...")
    webdriver.get("https://www.google.de/search?q=laufen+definition")

    print("Click on the agree button...")
    i_agree = webdriver.find_element_by_xpath('//*[@id="L2AGLb"]')
    i_agree.click()

    print("Find the base dictionary element...")
    frame = webdriver.find_element_by_class_name("lr_container").find_elements_by_xpath("./*")[2]

    example = f'"{example}"'
    pad = 5 * zoom

    xpaths_changes = {"div/div[2]/div[1]/div/span": word,
                      "div/div[2]/div[2]/span/span": ipa,
                      "div/div[4]/div/div/div/div/div/i/span": part_of_speech,
                      "div/div[4]/div/div/ol/li[1]/div/div/div[1]/div[2]/div/div[1]/span": meaning,
                      "div/div[4]/div/div/ol/li[1]/div/div/div[1]/div[2]/div/div[2]/div": example}

    print("Changing...")
    for xpath in xpaths_changes:
        change = xpaths_changes[xpath]
        print(f"{xpath} to {change}")

        element = frame.find_element_by_xpath(xpath)
        # change text of element
        webdriver.execute_script(f"arguments[0].innerText = '{change}'", element)

    print("Resizing window...")
    webdriver.set_window_size(1600 * zoom, 900 * zoom)

    print("Scaling window...")
    webdriver.execute_script(f"document.body.style.zoom='{zoom}'")

    print("Scrolling frame into view...")
    ActionChains(webdriver).move_to_element(frame).perform()
    # driver.execute_script("arguments[0].scrollIntoView(true);", frame)

    print("Taking screenshot...")
    location = frame.location
    size = frame.size
    print("...Getting png")
    png = webdriver.get_screenshot_as_png()  # saves screenshot of entire page

    print("...Opening with PIL")
    im: PngImagePlugin.PngImageFile = Image.open(BytesIO(png))

    left = location['x'] * zoom - pad
    top = location['y'] * zoom - pad
    right = (location['x'] + size['width']) * zoom + pad
    bottom = (location['y'] + size['height']) * zoom + pad

    print("...Cropping")
    im = im.crop((left, top, right, bottom))

    print("...Searching for black")
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

    print("...Cropping again")
    im = im.crop((0, 0, x + pad, im.height))

    print("...Saving")
    img_byte_arr = io.BytesIO()
    im.save(img_byte_arr, format="png")  # saves new cropped image

    print("Closing browser...")
    # driver.close()

    print("Finished!")

    out = img_byte_arr.getvalue()

    cachelib.save(out, hash_obj)

    return out
