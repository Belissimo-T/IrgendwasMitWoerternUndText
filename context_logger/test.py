from advanced_logger import Logger, log


def some_other_function():
    log("Probably important")
    with log("Yea vewy impoatant"):
        log("A SDASD")
        log("Vewy Vewy impoatant")
    log("finished now :)")


def main():
    logger = Logger("Not global anymore")
    with logger:
        log("Something")
        log("Another thing")
        with log("SOmething elese"):
            some_other_function()
            log("Still something else")
        log("Ok finished important")


log("This should be in global logger context.")

if __name__ == "__main__":
    main()
