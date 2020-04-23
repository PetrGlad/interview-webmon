import sys
import time
from multiprocessing import Process
from pprint import pprint
import http.client

import psycopg2
import toml
from flask import Flask

app = Flask(__name__)

SLOW_DELAY = 1.0


@app.route('/hello')
def route_hello():
    return 'hello'


@app.route('/fast')
def route_fast():
    return 'fast'


@app.route('/slow')
def route_slow():
    time.sleep(SLOW_DELAY)
    return 'slow'


@app.route('/never')
def route_never():
    time.sleep(SLOW_DELAY * 5)
    return 'never'


# TODO DRY, Share db and config code with main ...
def load_lines(file_name):
    with open(file_name) as f:
        return f.readlines()


def with_db_connection(db_config, proc):
    with psycopg2.connect(db_config['uri'],
                          password=load_lines(db_config['password_file'])[0].strip()) as conn:
        with conn.cursor() as cur:
            return proc(cur)


def normalize_status(row):
    """Return (url, http_status, slow?, content_match?)"""
    if row[1] == 0:
        assert not row[3]
        return row[0], 0, True, False
    else:
        return row[0], row[1], row[2] >= SLOW_DELAY, row[3]


def test_proc(db_config, delay):
    print("Awaiting probes.")
    start_at = time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime(time.time()))
    time.sleep(delay * 3 + 10)  # 2 cycles + some time for in-flight messages to settle

    def check_statuses(cur):
        print(f"Checking db results after {start_at}.")
        cur.execute("SELECT url, code, duration, match FROM web_status where timestamp >= %s",
                    (start_at,))
        rows = [row for row in cur]
        print(f"Received {len(rows)} records.")
        results = set([normalize_status(r) for r in rows])
        print("Normalized results:")
        pprint(results)
        expecting = {('http://10.0.0.5:12321/fast', 0, True, False),  # No connection
                     ('http://10.0.0.5:8080/fast', 200, False, True),  # OK
                     ('http://10.0.0.5:8080/hello', 200, False, False),  # Content mismatch
                     ('http://10.0.0.5:8080/never', 0, True, False),  # Timeout
                     ('http://10.0.0.5:8080/newverland', 404, False, False),  # 404
                     ('http://10.0.0.5:8080/slow', 200, True, True)  # Slow
                     }
        print("Expecting:")
        pprint(expecting)
        # It could be possible to compare wit '==' to potentially detect more problems.
        # But flask is not available immediately, which is already recorded by probe.
        # Also there may be other probes running.
        # A reliable implementation of '==' comparison would be more complex.
        return len(expecting.difference(results)) == 0

    return with_db_connection(db_config, check_statuses)


if __name__ == '__main__':
    config = toml.load('config/config.toml')
    flask = Process(target=lambda: app.run(host='10.0.0.5', port=8080))
    try:
        flask.start()
        if test_proc(config['db'], config['web']['delay_s']):
            print("\nTest passed.\n")
        else:
            print("\nTest failed.\n")
            sys.exit(1)
    finally:
        flask.terminate()
