NetSentinel AI-Powered Security Platform
=========================================

Getting Started
----------------

NetSentinel is an enterprise-grade AI-powered network security monitoring and anomaly detection system. To get started, you can either use Docker Compose for a complete setup or install locally for development.

## Quick Start with Docker

The easiest way to get started is using Docker Compose:

.. code-block:: sh

   $ git clone https://github.com/netsentinel/netsentinel.git
   $ cd netsentinel
   $ docker-compose up -d

This will start all services including NetSentinel, Kafka, Redis, Elasticsearch, InfluxDB, Prometheus, and Grafana.

## Local Development Setup

To get started with local development, create a virtual environment:

.. code-block:: sh

   $ virtualenv env
   $ . env/bin/activate
   $ pip install -e ./src

NetSentinel ships with a default config, which we'll copy and edit to get started. The config is a single `JSON <https://en.wikipedia.org/wiki/JSON>`_ dictionary.

.. code-block:: sh

   $ netsentinel --copyconfig
   $ $EDITOR ~/.netsentinel.conf

In the config file we'll change **device.node_id** which must be unique for
each instance of netsentinel, and we'll configure **logger** to log
alerts to a file.

.. code-block:: json

    {
      "device.node_id": "Your-very-own-unique-name",
      // ...
      "logger": {
        "class": "PyLogger",
        "kwargs": {
          "handlers": {
            "file": {
              "class": "logging.FileHandler",
              "filename": "/var/tmp/opencanary.log"
            }
          }
        }
      }
      // ...
    }


With that in place, we can run the daemon and test that it logs a failed FTP login attempt to the log file.

.. code-block:: sh

   $ opencanaryd --start
   [...]
   $ ftp localhost
   [...]
   $ cat /var/tmp/opencanary.log
   [...]
   {"dst_host": "127.0.0.1", "dst_port": 21, "local_time": "2015-07-20 13:38:21.281259", "logdata": {"PASSWORD": "default", "USERNAME": "admin"}, "logtype": 2000, "node_id": "opencanary-0", "src_host": "127.0.0.1", "src_port": 49635}


Troubleshooting
---------------

The tool JQ can be used to check that the config file is well-formed JSON.

.. code-block:: sh

   $ jq . ~/.opencanary.conf

Run opencanaryd in the foreground to see more error messages.

.. code-block:: sh

   $ opencanaryd --dev

You may also easily restart the service using,

.. code-block:: sh

   $ opencanaryd --restart
