NetSentinel Web Server
======================

NetSentinel provides comprehensive web server honeypot capabilities with AI-powered threat detection. Configure inside ~/.netsentinel.conf:

.. code-block:: json

   {
    "ftp.banner": "FTP server ready",
    "ftp.enabled": true,
    "ftp.port":21,
    "http.banner": "Apache/2.2.22 (Ubuntu)",
    "http.enabled": true,
    "http.port": 80,
    "http.skin": "nasLogin",
    "http.skin.list": [
        {
            "desc": "Plain HTML Login",
            "name": "basicLogin"
        },
        {
            "desc": "Synology NAS Login",
            "name": "nasLogin"
        }
    ],
    "https.enabled": true,
    "https.port": 443,
    "https.skin": "nasLogin",
    "https.certificate": "/etc/ssl/netsentinel/netsentinel.pem",
    "https.key": "/etc/ssl/netsentinel/netsentinel.key",
    "ssh.enabled": true,
    "ssh.port": 8022,
    "ssh.version": "SSH-2.0-OpenSSH_5.1p1 Debian-4",
    // [..] # logging configuration
   }
