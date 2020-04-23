import asyncio
import json
import logging
import re
import time

import aiohttp
from kafka import KafkaProducer

log = logging.getLogger(__name__)


async def check_url(url, expect_regex, delay):
    async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=min(delay, 10.0))) as session:
        start_at = time.time()
        try:
            async with session.get(url) as response:  # Not following redirects
                content = await response.text()
                status = {'url': url,
                          'code': response.status,
                          'duration': time.time() - start_at,
                          'match': bool(re.search(expect_regex, content)),
                          'timestamp': time.time()}
                log.debug(f"New status {status}.")
                return status
        except Exception as ex:
            log.info(f"Probe exception for \"{url}\": {type(ex)} {ex}")
            return {'url': url,
                    'code': 0,
                    'duration': time.time() - start_at,
                    'match': False,
                    'timestamp': time.time()}


async def http_checker(sites_config, delay, web_status_topic, kafka_config):
    sender = KafkaProducer(**kafka_config, client_id='status-logger-1', acks=1)

    async def check(site):
        status = await check_url(site['url'], site['expect_regex'], delay)
        sender.send(web_status_topic, value=json.dumps(status).encode('utf-8'))  # Note: this is blocking

    try:
        while True:  # Until the process is interrupted
            await asyncio.gather(*[check(site) for site in sites_config])
            sender.flush()
            await asyncio.sleep(delay)
    finally:
        sender.close()
