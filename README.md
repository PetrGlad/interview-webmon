# Web sites monitor

Get HTTP statuses and match response results with given regexps.
Result is then piped to Kafka, and then stored from Kafka into a PostgreSQL database.

The collected data is HTTP response code, match/no match flag for body regex,
the time it took the web server to respond, and timestamp of the test.


## Configuration

All configuration files are in `./config` directory.
Modify `config/config.toml` before building the container.
The required files layout is
```
config
├── config.toml # The configuration file, look inside for hints
├── keys
│   ├── kafka 
│   │   ├── ca.pem # kafka server CA
│   │   ├── service.cert # kafka server TLS cert
│   │   └── service.key # user key
│   └── pg 
│       ├── ca.pem # service CA
│       └── pg.key # contains password on the first line, whitespace is trimmed
└── sites.csv # List of sites to test
```

To get keys from Aiven cloud use `avn` command for example
```
python3 -m pip install aiven-client
avn user login  YOUR_EMAIL_HERE
avn service user-creds-download --username avnadmin kafka-1 -d config/keys/kafka/
cp config/keys/kafka/ca.pem config/keys/pg/
```
Be sure to double check user name in `user-creds-download` command 
as it does not check whether user with that name exist and succeeds anyway.

Unfortunately for Postgres it is not supported. So you have to copy database 
user password from database's service admin page into `config/keys/pg/pk.key`.


## Build and run

Tor run in a Docker container add user and service keys to `config/keys`
as described above then run `./run.sh`.

If you run directly on your machine install python prerequisites
and `libpq-dev` system package, e.g.:
```bash
sudo apt install libpq-dev
pip install -r requirements.txt
```


## Implementation notes

Query and storage procedures are in same process, Ishlud be straightforward
to separate them into different containers by splitting main function.

I never used async/await in Python before so decided that it would be an
interesting experiment. While checking lots of URLs it seems that most of the
time would be spent waiting for results (the problem is io bound).

`aiokafka` library provides nicer interface for async/await but it requires
older version of kafka-python. I could not make it work with AdminClient on time.
So kafka-python 2.x is used.
