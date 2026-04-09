"""Randomized delays and mouse/scroll jitter to mimic human activity."""
import random
import time

import config


def click_delay() -> None:
    """Short pause between individual UI clicks."""
    time.sleep(random.uniform(config.MIN_CLICK_DELAY_SEC, config.MAX_CLICK_DELAY_SEC))


def profile_delay() -> None:
    """Longer pause between processing different profiles."""
    time.sleep(random.uniform(config.MIN_PROFILE_DELAY_SEC, config.MAX_PROFILE_DELAY_SEC))


def micro_delay() -> None:
    """Tiny randomized pause for typing naturalness."""
    time.sleep(random.uniform(0.2, 0.7))


def type_like_human(locator, text: str) -> None:
    """Type text character-by-character with random micro-delays."""
    for char in text:
        locator.type(char, delay=random.uniform(40, 120))


def random_scroll(page) -> None:
    """Perform a couple of random downward scrolls to trigger lazy loading."""
    try:
        for _ in range(random.randint(1, 3)):
            offset = random.randint(200, 600)
            page.mouse.wheel(0, offset)
            time.sleep(random.uniform(0.4, 1.2))
    except Exception:
        pass


def random_mouse_jitter(page) -> None:
    """Move the mouse to a random position within the viewport."""
    try:
        x = random.randint(100, 1200)
        y = random.randint(100, 700)
        page.mouse.move(x, y, steps=random.randint(5, 15))
    except Exception:
        pass
