import traceback
import warnings
import sys
from twisted.application import service
from pkg_resources import iter_entry_points

from netsentinel.config import config, is_docker
from netsentinel.logger import getLogger
from netsentinel.modules.http import CanaryHTTP
from netsentinel.modules.https import CanaryHTTPS
from netsentinel.modules.ftp import CanaryFTP
from netsentinel.modules.ssh import CanarySSH
from netsentinel.modules.telnet import Telnet
from netsentinel.modules.httpproxy import HTTPProxy
from netsentinel.modules.mysql import CanaryMySQL
from netsentinel.modules.mssql import MSSQL
from netsentinel.modules.ntp import CanaryNtp
from netsentinel.modules.tftp import CanaryTftp
from netsentinel.modules.vnc import CanaryVNC
from netsentinel.modules.sip import CanarySIP
from netsentinel.modules.git import CanaryGit
from netsentinel.modules.redis import CanaryRedis
from netsentinel.modules.tcpbanner import CanaryTCPBanner
from netsentinel.modules.rdp import CanaryRDP


def warn(*args, **kwargs):
    pass


warnings.warn = warn


# from opencanary.modules.example0 import CanaryExample0
# from opencanary.modules.example1 import CanaryExample1

ENTRYPOINT = "canary.usermodule"
MODULES = [
    CanaryFTP,
    CanaryGit,
    CanaryHTTP,
    CanaryHTTPS,
    CanaryMySQL,
    CanaryNtp,
    CanaryRDP,
    CanaryRedis,
    CanarySIP,
    CanarySSH,
    CanaryTCPBanner,
    CanaryTftp,
    CanaryVNC,
    HTTPProxy,
    MSSQL,
    Telnet,
    # CanaryExample0,
    # CanaryExample1,
]

if config.moduleEnabled("snmp"):
    try:
        # Module need Scapy, but the rest of OpenCanary doesn't
        from netsentinel.modules.snmp import CanarySNMP

        MODULES.append(CanarySNMP)
    except ImportError:
        print("Can't import SNMP. Please ensure you have Scapy installed.")
        pass

if config.moduleEnabled("llmnr"):
    try:
        # Module needs Scapy, but the rest of OpenCanary doesn't
        from netsentinel.modules.llmnr import CanaryLLMNR

        MODULES.append(CanaryLLMNR)
    except ImportError:
        print("Can't import LLMNR. Please ensure you have Scapy installed.")
        pass

# NB: imports below depend on inotify, only available on linux
if sys.platform.startswith("linux"):
    from netsentinel.modules.samba import CanarySamba

    MODULES.append(CanarySamba)
    if config.moduleEnabled("portscan") and is_docker():
        # Remove portscan if running in DOCKER (specified in Dockerfile)
        print("Can't use portscan in Docker. Portscan module disabled.")
    else:
        from netsentinel.modules.portscan import CanaryPortscan

        MODULES.append(CanaryPortscan)


logger = getLogger(config)


def start_mod(application, klass):  # noqa: C901
    try:
        obj = klass(config=config, logger=logger)
    except Exception:
        err = "Failed to instantiate instance of class %s in %s. %s" % (
            klass.__name__,
            klass.__module__,
            traceback.format_exc(),
        )
        logMsg({"logdata": err})
        return

    if hasattr(obj, "startYourEngines"):
        try:
            obj.startYourEngines()
            msg = "Ran startYourEngines on class %s in %s" % (
                klass.__name__,
                klass.__module__,
            )
            logMsg({"logdata": msg})

        except Exception:
            err = "Failed to run startYourEngines on %s in %s. %s" % (
                klass.__name__,
                klass.__module__,
                traceback.format_exc(),
            )
            logMsg({"logdata": err})
    elif hasattr(obj, "getService"):
        try:
            service = obj.getService()
            if not isinstance(service, list):
                service = [service]
            for s in service:
                s.setServiceParent(application)
            msg = "Added service from class %s in %s to fake" % (
                klass.__name__,
                klass.__module__,
            )
            logMsg({"logdata": msg})
        except Exception:
            err = "Failed to add service from class %s in %s. %s" % (
                klass.__name__,
                klass.__module__,
                traceback.format_exc(),
            )
            logMsg({"logdata": err})
    else:
        err = "The class %s in %s does not have any required starting method." % (
            klass.__name__,
            klass.__module__,
        )
        logMsg({"logdata": err})


def logMsg(msg):
    data = {}
    data["logdata"] = {"msg": msg}
    logger.log(data, retry=False)


application = service.Application("netsentinel")

# List of modules to start
start_modules = []

# Add all custom modules
# (Permanently enabled as they don't officially use settings yet)
for ep in iter_entry_points(ENTRYPOINT):
    try:
        klass = ep.load(require=False)
        start_modules.append(klass)
    except Exception:
        err = "Failed to load class from the entrypoint: %s. %s" % (
            str(ep),
            traceback.format_exc(),
        )
        logMsg({"logdata": err})

# Add only enabled modules
start_modules.extend(filter(lambda m: config.moduleEnabled(m.NAME), MODULES))

for klass in start_modules:
    start_mod(application, klass)

msg = "Canary running!!!"
logMsg({"logdata": msg})
