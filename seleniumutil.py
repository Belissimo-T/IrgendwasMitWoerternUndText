from asyncio import Event, Semaphore
from multiprocessing.pool import ThreadPool
from typing import Callable, Union

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver

from context_logger import Logger, log, log_decorator, loggerstack_contextvar, nlist_contextvar, get_current_nlist, \
    get_current_logger

chrome_options = Options()
chrome_options.add_argument("--headless")


class WebBrowserQueue:
    def __init__(self, num_browsers=2):
        self.browsers: list[list[(WebDriver, bool)]] = []

        with log(f"Creating browsers ({num_browsers})..."):
            for i in range(num_browsers):
                log(f"{i}")
                driver = WebDriver(options=chrome_options)
                self.browsers.append([driver, True])

        self.semaphore = Semaphore(num_browsers)

    @log_decorator("acquiring browser lock")
    async def aquire(self) -> WebDriver:
        await self.semaphore.acquire()

        for i, (web_driver, is_free) in enumerate(self.browsers):
            if is_free:
                self.browsers[i][1] = False
                break
        else:
            raise Exception("Semaphore told lies!")
        return web_driver

    @log_decorator("releasing browser lock")
    def release(self, webdriver: WebDriver):
        for i, (web_driver, is_free) in enumerate(self.browsers):
            if web_driver == webdriver:
                self.browsers[i][1] = True
                break

        self.semaphore.release()


wbq: Union[WebBrowserQueue, None] = None


def prepare():
    global wbq
    if wbq is None:
        wbq = WebBrowserQueue(5)


# warten bis irgendein browser thread das lock löst
# queue austeilen bis counter == 0

# warten bis der queue thread das lock gelöst hat, das in den queue gepackt wurde


def zoom(webdriver: WebDriver, factor: float = 1):
    webdriver.execute_script(f"document.body.style.zoom='{factor}'")


def _async_thread_wrapper(event: Event, func: Callable):
    result = func()
    event.set()
    return result


def set_logger(logger: Logger, nlist: list[int]):
    loggerstack_contextvar.set([logger])
    nlist_contextvar.set(nlist[:])


async def async_thread_wrapper(func: Callable):
    # start a thread
    pool = ThreadPool(processes=1, initializer=set_logger, initargs=(get_current_logger(), get_current_nlist()))

    # create an event
    event = Event()

    async_result = pool.apply_async(_async_thread_wrapper, (event, func))

    # wait for finish using an event
    await event.wait()

    return async_result.get()


def _execute(webdriver: WebDriver, func: Callable, size: tuple[int, int] = (1600, 900), scale: float = 1):
    # set window size
    log("Setting window size")
    width, height = size
    webdriver.set_window_size(width, height)

    # set scale
    log("Scaling")
    webdriver.execute_script(f"document.body.style.zoom='{scale}'")

    # call function
    return func(webdriver)


async def run_function(func: Callable, size: tuple[int, int] = (1600, 900), scale: float = 1):
    if not wbq:
        # raise Exception("WebBrowserQueue not created, call the prepare() method first.")
        prepare()
    driver = await wbq.aquire()

    log("handing control to async selenium thread")
    try:
        result = await async_thread_wrapper(lambda: _execute(driver, func, size, scale))
    finally:
        wbq.release(driver)
    return result
