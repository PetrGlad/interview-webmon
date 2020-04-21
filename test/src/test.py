from flask import Flask
import time
from multiprocessing import Process
import psycopg2
import toml

app = Flask(__name__)


@app.route('/hello')
def route_hello():
    return 'hello'


@app.route('/fast')
def route_fast():
    return 'fast'


@app.route('/slow')
def route_slow():
    time.sleep(1)
    return 'slow'


# TODO DRY, Share db and config code with main ...
def load_lines(file_name):
    with open(file_name) as f:
        return f.readlines()


def with_db_connection(db_config, proc):
    with psycopg2.connect(db_config['uri'],
                          password=load_lines(db_config['password_file'])[0].strip()) as conn:
        with conn.cursor() as cur:
            proc(cur)


def test_proc(db_config, delay):
    print("Awaiting probes.")
    time.sleep(delay * 3 + 5)  # 2 cycles + some time for in-flight messages to settle

    def check_statuses(cur):
        print("Checking db results.")
        cur.execute("SELECT timestamp, url, code, duration, match FROM web_status;")
        print(cur.fetchone())
        for row in cur:
            print(row)

    # print(os.listdir('/app/config'))
    with_db_connection(db_config, check_statuses)


if __name__ == '__main__':
    print(load_lines('config/config.toml'))
    print(load_lines('/app/config/config.toml'))
    config = toml.load('config/config.toml')
    print(config)
    flask = Process(target=app.run)
    try:
        flask.start()
        test_proc(config['db'], config['web']['delay_s'])
    finally:
        flask.terminate()
