from typing import Callable
import asyncio
from concurrent.futures.thread import ThreadPoolExecutor as Pool
from asgiref.sync import sync_to_async

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver


print("Creating browser...")
chrome_options = Options()
chrome_options.add_argument("--headless")
driver = WebDriver(options=chrome_options)

browser_lock = asyncio.Lock()


def zoom(webdriver: WebDriver, factor: float):
    webdriver.execute_script(f"document.body.style.zoom='{factor}'")


def _execute(webdriver: WebDriver, func: Callable, size: tuple[int, int] = (1600, 900), scale: float = 1):
    # set window size
    print("Setting window size")
    width, height = size
    webdriver.set_window_size(width, height)

    # set scale
    print("Scaling...")
    webdriver.execute_script(f"document.body.style.zoom='{scale}'")

    # call function
    return func(webdriver)


async def run_function(func: Callable, size: tuple[int, int] = (1600, 900), scale: float = 1):
    print("Waiting for lock...")
    async with browser_lock:
        print("Starting async thread selenium")
        return await sync_to_async(_execute)(driver, func, size, scale)
