from marketmaker import MarketMaker
import logging

log = logging.getLogger(__name__)


def main():
    # Initialize logger
    log_format = '%(asctime)s - [%(levelname)s] %(name)s: %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_format)
    retry_log = logging.getLogger('retry.api')
    retry_log.setLevel(logging.ERROR)
    scheduler_log = logging.getLogger('apscheduler')
    scheduler_log.setLevel(logging.ERROR)

    log.info("Initiating Market Maker...")
    maker = MarketMaker()

    log.info("Market Maker engaged!")

    maker.run()

if __name__ == '__main__':
    main()
