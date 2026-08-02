import time
from datetime import datetime
from typing import Callable

def run_loop_func(func: Callable[[], None], days: int=1) -> None:
   
    if days <= 0:
        raise ValueError("Days must be a positive integer.")
    interval = (days * 24 * 60 * 60)
    while True:
        print(f"Running function at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        func()
        print(f"Function completed. Next run in {days} day(s).")
        time.sleep(interval)  