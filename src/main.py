import asyncio
import csv
import json
import logging
import re
import time

import aiohttp
import aiopg
import toml
from kafka import KafkaConsumer, KafkaProducer, KafkaAdminClient, TopicPartition
from kafka.admin import NewTopic

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def parse_version(version_str):
    return tuple([int(x) for x in version_str.split('.')])


def load_lines(file_name):
    with open(file_name) as f:
        return f.readlines()


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
            log.info(f"Probe exception for \"{url}\": {ex}.")
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


def create_kafka_config(mq_config):
    kafka_config = mq_config.copy()
    kafka_config['api_version'] = parse_version(mq_config['api_version'])
    kafka_config['security_protocol'] = 'SSL'
    kafka_config['ssl_check_hostname'] = True
    return kafka_config


def configure_kafka_broker(kafka_config, topic):
    admin = KafkaAdminClient(**kafka_config, client_id='admin-1')
    if topic not in admin.list_topics():
        admin.create_topics([NewTopic(topic, 1, 3)])
    admin.close()


def create_web_config(web_config):
    with open(web_config['sites_list']) as f:
        sites_data = csv.reader(f.readlines())
        header = next(sites_data)
        assert header == ['url', 'expect_regex'], "Sites CSV header is not \"url,expect_regex\"."
        sites = [{'url': row[0], 'expect_regex': row[1]}
                 for row in sites_data
                 if len(row) > 0]  # Ignore empty rows
        # TODO Assert no duplicate URLs here (duplicate results violate primary key)
        return sites


web_status_table = 'web_status'


async def setup_db(cursor):
    try:
        await cursor.execute(f"select 1 from {web_status_table}")
    except Exception as ex:
        await cursor.execute(f'''
create table {web_status_table} (
    timestamp timestamp not null,
    url varchar(4096) not null,
    code smallint not null,
    duration float not null,
    match bool,
    primary key(timestamp, url)
)
''')


async def store_batch(cursor, messages):
    for msg in messages:
        try:
            status: dict = json.loads(msg.value)
            log.info(f"Got status {status}.")
            await cursor.execute(
                f"insert into {web_status_table} (timestamp, url, code, duration, match) values (%s, %s, %s, %s, %s)",
                (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(status['timestamp'])),
                 status['url'],
                 status['code'],
                 status['duration'],
                 status['match']))
        except Exception as ex:
            log.error("Cannot process incoming message % : %", msg, ex)


async def with_db_connection(db_config, proc):
    async with aiopg.create_pool(
            db_config['uri'],
            password=load_lines(db_config['password_file'])[0].strip()) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await setup_db(cursor)
                return await proc(cursor)


async def status_archiver(kafka_config, topic, db_config):
    consumer = KafkaConsumer(**kafka_config, client_id='webmon-1')
    consumer.assign([TopicPartition(topic, 0)])
    partition_key = TopicPartition(topic='web-status', partition=0)

    async def store_loop(cursor):
        while True:
            messages = consumer.poll()
            if partition_key not in messages:
                await asyncio.sleep(2)
            else:
                messages = messages[partition_key]
                await store_batch(cursor, messages)

    await with_db_connection(db_config, store_loop)


if __name__ == '__main__':
    config = toml.load('config/config.toml')

    kafka_config = create_kafka_config(config['mq'])
    web_status_topic = 'web-status'
    configure_kafka_broker(kafka_config, web_status_topic)

    sites_config = create_web_config(config['web'])
    delay = config['web']['delay_s']

    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(
        http_checker(sites_config, delay, web_status_topic, kafka_config),
        status_archiver(kafka_config, web_status_topic, config['db'])
    ))
