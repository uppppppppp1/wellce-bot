import logging
from scheduler import build_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

if __name__ == "__main__":
    print("Wellcee Bot starting...")
    scheduler = build_scheduler()
    print("Scheduler running. Press Ctrl+C to stop.")
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("Bot stopped.")
