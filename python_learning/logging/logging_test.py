#!/usr/bin/python3

#
# https://fangpenlin.com/posts/2012/08/26/good-logging-practice-in-python/
#

import logging
from logging.handlers import TimedRotatingFileHandler
from numpy import *


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if False:
    logger.info('Start reading database')
    # read database here
    records = {'john': 55, 'tom': 66}
    logger.debug('Records: %s', records)
    logger.info('Updating records ...')
    # update records here
    logger.info('Finish updating records')

if False:
    
    # create a file handler
    handler = logging.FileHandler('hello.log')
    handler.setLevel(logging.INFO)

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(handler)

    logger.info('Hello baby')

if False:
    # create a file handler
    handler = logging.FileHandler('hello.log')
    handler.setLevel(logging.DEBUG)

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(handler)

    logger.info('Hello baby')

    try:
        print(1/0)
    except Exception:
        logger.error('Failed to do something',exc_info=True)
        
if True:
    # create a file handler
    handler = TimedRotatingFileHandler('test.log',when='d',interval=1, backupCount=30)
    handler.setLevel(logging.DEBUG)

    # create a logging format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    # add the handlers to the logger
    logger.addHandler(handler)

    logger.info('Hello baby')

    try:
        print(1/0)
    except Exception:
        #logger.error('Failed to do something',exc_info=True)
        logger.exception('Failed to do something')


