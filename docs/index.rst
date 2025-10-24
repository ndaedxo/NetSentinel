NetSentinel AI-Powered Security Platform
========================================

Welcome to the NetSentinel AI-Powered Security Platform documentation.

NetSentinel is an enterprise-grade AI-powered network security monitoring and anomaly detection system that combines honeypot services with advanced machine learning, real-time threat intelligence, and comprehensive enterprise integrations.

## Key Features

- **AI-Powered Detection**: ML-based anomaly detection using Anomalib models
- **Enterprise Integrations**: SIEM, SDN, Threat Intelligence, Database systems
- **Real-Time Processing**: Kafka streaming with Redis caching
- **Advanced Monitoring**: Prometheus, Grafana, Elasticsearch, InfluxDB
- **Security Features**: Authentication, encryption, compliance reporting
- **Scalability**: Multi-node clusters with auto-scaling capabilities

## Architecture

NetSentinel provides a comprehensive security platform with:
- Multi-protocol honeypot services (FTP, SSH, HTTP, RDP, VNC, etc.)
- Real-time ML-based threat analysis
- Enterprise database integration (Elasticsearch, InfluxDB)
- SIEM integration (Splunk, ELK Stack, Syslog)
- SDN integration (OpenFlow controllers)
- Threat intelligence feeds (MISP, STIX/TAXII)
- Advanced monitoring and alerting

This project is maintained by the NetSentinel development team.


.. _getting-started:

Getting Started
---------------

The first section will get you quickly up and running with NetSentinel
AI-powered security platform.

.. toctree::
   :maxdepth: 1

   starting/netsentinel
   starting/configuration
   starting/correlator

Services
---------

Try these out in the NetSentinel configs for more typical server personalities.

.. toctree::
   :maxdepth: 1

   services/webserver
   services/windows
   services/mysql
   services/mssql


Alerting
---------

:ref:`getting-started` walks through two different ways to configure alerting: logging directly to a file, and sending alerts to the Correlator for email and SMS alerts. Other possibilities are below:

.. toctree::
   :maxdepth: 2

   alerts/email
   alerts/hpfeeds
   alerts/webhook


Upgrading
---------

If you have a previous version of OpenCanary installed already, you can upgrade it easily.

Start by activating your virtual environment (`env` in the below example) that has your installed version of OpenCanary,

.. code-block:: sh

   $ . env/bin/activate


Inside the virtualenv, you can upgrade your NetSentinel by,

.. code-block:: sh

  $ pip install netsentinel --upgrade

Please note that this will not wipe your existing NetSentinel config file. If you would like a new one (with the new settings), please regenerate the config file using,

.. code-block:: sh

  $ netsentinel --copyconfig

AI-Powered Features
-------------------

NetSentinel includes comprehensive AI-powered threat detection capabilities.

.. toctree::
   :maxdepth: 1

   ai-features-overview
   ml-setup-guide
   ml-usage-guide

Enterprise Integrations
------------------------

NetSentinel provides extensive enterprise integrations for production environments.

.. toctree::
   :maxdepth: 1

   siem-integration
   sdn-integration
   project-overview
   implementation-status



Indices and tables
------------------
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
