import asyncio
import psycopg2
from kafka import KafkaConsumer, KafkaProducer, KafkaAdminClient, TopicPartition
from kafka.admin import NewTopic
import logging

logging.basicConfig(level=logging.DEBUG)

# async def g(ln):
#     return ln + '!'
#
#
# async def f(i):
#     print('hello ' + await g(f'world #{i}'))
#
#
# async def main():
#     tasks = [asyncio.create_task(f(x)) for x in range(10000)]
#     await asyncio.gather(*tasks)

# asyncio.run(main())

log = logging.getLogger(__name__)


def do_kafka():
    topic = 'web_status'
    # kafka_config = {'bootstrap_servers': 'kafka-1-petrglad-8b82.aivencloud.com:16068',
    #                 'ssl_cafile': 'keys/kafka/ca.pem',
    #                 'ssl_certfile': 'keys/kafka/service.cert',
    #                 'ssl_keyfile': 'keys/kafka/service.key'}

    admin = KafkaAdminClient(bootstrap_servers='kafka-1-petrglad-8b82.aivencloud.com:16068',
                             api_version=(2, 4, 1),
                             security_protocol='SSL',
                             ssl_check_hostname=True,
                             ssl_cafile='keys/kafka/ca.pem',
                             ssl_certfile='keys/kafka/service.cert',
                             ssl_keyfile='keys/kafka/service.key',
                             client_id='admin-1')
    admin.create_topics([NewTopic(topic, 1, 3)])
    admin.close()

    producer = KafkaProducer(
        bootstrap_servers='kafka-1-petrglad-8b82.aivencloud.com:16068',
        api_version=(2, 4, 1),
        security_protocol='SSL',
        ssl_check_hostname=True,
        ssl_cafile='keys/kafka/ca.pem',
        ssl_certfile='keys/kafka/service.cert',
        ssl_keyfile='keys/kafka/service.key',
        client_id='status-logger-1',
        acks=1)
    log.info(" ================ Sender connected to broker.")

    for k in range(5):
        log.info(f"Sending #{k}")
        producer.send(topic, value=f'hello:{k}'.encode('utf-8'))

    log.info(f"Producer: bootstrap connected {producer.bootstrap_connected()}")
    log.info(
        f"Producer: topic {topic} partitions {len(producer.partitions_for(topic))} - {producer.partitions_for(topic)}")
    producer.close()

    log.info(" ================ Receiver is connecting to broker.")
    consumer = KafkaConsumer(bootstrap_servers='kafka-1-petrglad-8b82.aivencloud.com:16068',
                             api_version=(2, 4, 1),
                             security_protocol='SSL',
                             ssl_check_hostname=True,
                             ssl_cafile='keys/kafka/ca.pem',
                             ssl_certfile='keys/kafka/service.cert',
                             ssl_keyfile='keys/kafka/service.key',
                             client_id='webmon-1b')
    log.info(" ================ Receiver connected to broker.")
    consumer.assign([TopicPartition(topic, 0)])
    consumer.seek_to_beginning(TopicPartition(topic, 0))
    for msg in consumer:
        log.info(f" ================ Got message {msg}.")


def load_lines(file_name):
    with open(file_name) as f:
        return f.readlines()

def do_postgres():
    with psycopg2.connect("postgres://@pg-1-petrglad-8b82.aivencloud.com:16066/defaultdb?sslmode=require",
                          password=load_lines('keys/pg/pg.key')[0].strip(),
                          user="avnadmin",
                          ) as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE TABLE test (id serial PRIMARY KEY, num integer, data varchar);")
            cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)", (100, "abc'def"))
            cur.execute("SELECT * FROM test;")
            print(cur.fetchone())
            conn.commit()
