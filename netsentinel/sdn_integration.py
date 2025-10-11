#!/usr/bin/env python3
"""
SDN (Software Defined Networking) Integration for NetSentinel
Enables dynamic network policy modification and automated traffic control
"""

import json
import time
import logging
import requests
import threading
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import ipaddress
import socket

logger = logging.getLogger(__name__)

class SDNControllerType(Enum):
    """Supported SDN controller types"""
    OPENDLIGHT = "opendaylight"
    ONOS = "onos"
    RYU = "ryu"
    FLOODLIGHT = "floodlight"
    OPENFLOW = "openflow"  # Generic OpenFlow REST API

class FlowAction(Enum):
    """OpenFlow flow actions"""
    DROP = "DROP"
    FORWARD = "OUTPUT"
    REDIRECT = "MODIFY"
    MIRROR = "MIRROR"
    QUARANTINE = "QUARANTINE"

@dataclass
class SDNController:
    """SDN controller configuration"""
    name: str
    type: SDNControllerType
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    api_key: Optional[str] = None
    timeout: int = 10

    @property
    def base_url(self) -> str:
        """Get base URL for controller API"""
        protocol = "https" if self.port == 443 else "http"
        return f"{protocol}://{self.host}:{self.port}"

@dataclass
class FlowRule:
    """OpenFlow flow rule specification"""
    switch_id: str
    table_id: int = 0
    priority: int = 100
    match: Dict[str, Any] = None
    actions: List[Dict[str, Any]] = None
    idle_timeout: int = 300
    hard_timeout: int = 0
    cookie: Optional[int] = None

    def __post_init__(self):
        if self.match is None:
            self.match = {}
        if self.actions is None:
            self.actions = []

@dataclass
class QuarantinePolicy:
    """Network quarantine policy"""
    name: str
    target_ip: str
    switch_id: str
    quarantine_vlan: Optional[int] = None
    redirect_port: Optional[str] = None
    duration: int = 3600  # seconds
    created_at: float = None
    active: bool = True

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

    def is_expired(self) -> bool:
        """Check if quarantine has expired"""
        return time.time() - self.created_at > self.duration

class OpenDaylightController:
    """OpenDaylight SDN controller integration"""

    def __init__(self, controller: SDNController):
        self.controller = controller
        self.session = requests.Session()
        self.session.auth = (controller.username or "admin", controller.password or "admin")
        self.session.headers.update({"Content-Type": "application/json"})

    def get_topology(self) -> Dict[str, Any]:
        """Get network topology information"""
        try:
            url = f"{self.controller.base_url}/restconf/operational/network-topology:network-topology"
            response = self.session.get(url, timeout=self.controller.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get OpenDaylight topology: {e}")
            return {}

    def get_flows(self, switch_id: str) -> List[Dict[str, Any]]:
        """Get flows for a specific switch"""
        try:
            url = f"{self.controller.base_url}/restconf/config/opendaylight-inventory:nodes/node/{switch_id}/table/0"
            response = self.session.get(url, timeout=self.controller.timeout)
            response.raise_for_status()
            data = response.json()
            return data.get("flow-node-inventory:table", [{}])[0].get("flow", [])
        except Exception as e:
            logger.error(f"Failed to get flows for switch {switch_id}: {e}")
            return []

    def add_flow(self, switch_id: str, flow: FlowRule) -> bool:
        """Add a flow rule to a switch"""
        try:
            flow_data = {
                "flow-node-inventory:flow": [
                    {
                        "id": str(flow.cookie or int(time.time())),
                        "table_id": flow.table_id,
                        "priority": flow.priority,
                        "idle-timeout": flow.idle_timeout,
                        "hard-timeout": flow.hard_timeout,
                        "match": flow.match,
                        "instructions": {
                            "instruction": [
                                {
                                    "order": 0,
                                    "apply-actions": {
                                        "action": flow.actions
                                    }
                                }
                            ]
                        }
                    }
                ]
            }

            url = f"{self.controller.base_url}/restconf/config/opendaylight-inventory:nodes/node/{switch_id}/table/{flow.table_id}"
            response = self.session.post(url, json=flow_data, timeout=self.controller.timeout)
            response.raise_for_status()
            logger.info(f"Added flow rule to switch {switch_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add flow to switch {switch_id}: {e}")
            return False

    def delete_flow(self, switch_id: str, flow_id: str) -> bool:
        """Delete a flow rule from a switch"""
        try:
            url = f"{self.controller.base_url}/restconf/config/opendaylight-inventory:nodes/node/{switch_id}/table/0/flow/{flow_id}"
            response = self.session.delete(url, timeout=self.controller.timeout)
            response.raise_for_status()
            logger.info(f"Deleted flow rule {flow_id} from switch {switch_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete flow {flow_id} from switch {switch_id}: {e}")
            return False

class ONOSController:
    """ONOS SDN controller integration"""

    def __init__(self, controller: SDNController):
        self.controller = controller
        self.session = requests.Session()
        self.session.auth = (controller.username or "onos", controller.password or "rocks")
        self.session.headers.update({"Content-Type": "application/json"})

    def get_devices(self) -> List[Dict[str, Any]]:
        """Get network devices"""
        try:
            url = f"{self.controller.base_url}/onos/v1/devices"
            response = self.session.get(url, timeout=self.controller.timeout)
            response.raise_for_status()
            return response.json().get("devices", [])
        except Exception as e:
            logger.error(f"Failed to get ONOS devices: {e}")
            return []

    def get_flows(self, device_id: str) -> List[Dict[str, Any]]:
        """Get flows for a device"""
        try:
            url = f"{self.controller.base_url}/onos/v1/flows/{device_id}"
            response = self.session.get(url, timeout=self.controller.timeout)
            response.raise_for_status()
            return response.json().get("flows", [])
        except Exception as e:
            logger.error(f"Failed to get flows for device {device_id}: {e}")
            return []

    def add_flow(self, device_id: str, flow: Dict[str, Any]) -> bool:
        """Add a flow rule"""
        try:
            url = f"{self.controller.base_url}/onos/v1/flows/{device_id}"
            response = self.session.post(url, json=flow, timeout=self.controller.timeout)
            response.raise_for_status()
            logger.info(f"Added flow rule to device {device_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add flow to device {device_id}: {e}")
            return False

    def delete_flow(self, device_id: str, flow_id: str) -> bool:
        """Delete a flow rule"""
        try:
            url = f"{self.controller.base_url}/onos/v1/flows/{device_id}/{flow_id}"
            response = self.session.delete(url, timeout=self.controller.timeout)
            response.raise_for_status()
            logger.info(f"Deleted flow rule {flow_id} from device {device_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete flow {flow_id} from device {device_id}: {e}")
            return False

class RyuController:
    """Ryu SDN controller integration"""

    def __init__(self, controller: SDNController):
        self.controller = controller
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def get_switches(self) -> List[str]:
        """Get connected switches"""
        try:
            url = f"{self.controller.base_url}/stats/switches"
            response = self.session.get(url, timeout=self.controller.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get Ryu switches: {e}")
            return []

    def add_flow(self, switch_id: str, flow: Dict[str, Any]) -> bool:
        """Add a flow rule using Ryu REST API"""
        try:
            url = f"{self.controller.base_url}/stats/flowentry/add"
            flow_data = {
                "dpid": int(switch_id, 16),  # Convert hex to int
                **flow
            }
            response = self.session.post(url, json=flow_data, timeout=self.controller.timeout)
            response.raise_for_status()
            logger.info(f"Added flow rule to Ryu switch {switch_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add flow to Ryu switch {switch_id}: {e}")
            return False

class SDNManager:
    """
    Central SDN manager for NetSentinel
    Provides automated network policy modification and traffic control
    """

    def __init__(self):
        self.controllers = {}
        self.quarantine_policies = {}
        self.active_flows = {}
        self.monitoring_thread = None
        self.monitoring_active = False

    def add_controller(self, controller: SDNController):
        """Add an SDN controller"""
        self.controllers[controller.name] = controller
        logger.info(f"Added SDN controller: {controller.name} ({controller.type.value})")

    def remove_controller(self, controller_name: str):
        """Remove an SDN controller"""
        if controller_name in self.controllers:
            del self.controllers[controller_name]
            logger.info(f"Removed SDN controller: {controller_name}")

    def get_controller_interface(self, controller_name: str) -> Optional[Any]:
        """Get controller interface instance"""
        if controller_name not in self.controllers:
            return None

        controller = self.controllers[controller_name]
        if controller.type == SDNControllerType.OPENDLIGHT:
            return OpenDaylightController(controller)
        elif controller.type == SDNControllerType.ONOS:
            return ONOSController(controller)
        elif controller.type == SDNControllerType.RYU:
            return RyuController(controller)
        else:
            logger.error(f"Unsupported controller type: {controller.type}")
            return None

    def quarantine_ip(self, controller_name: str, switch_id: str, target_ip: str,
                     duration: int = 3600, quarantine_vlan: Optional[int] = None) -> bool:
        """
        Quarantine an IP address by redirecting its traffic to a quarantine VLAN
        or dropping all traffic from the IP
        """
        try:
            controller = self.get_controller_interface(controller_name)
            if not controller:
                return False

            # Create quarantine policy
            policy_name = f"quarantine_{target_ip}_{int(time.time())}"
            policy = QuarantinePolicy(
                name=policy_name,
                target_ip=target_ip,
                switch_id=switch_id,
                quarantine_vlan=quarantine_vlan,
                duration=duration
            )

            # Create flow rules for quarantine
            flows = self._create_quarantine_flows(policy)

            # Install flows
            success_count = 0
            for flow in flows:
                if controller.add_flow(switch_id, flow):
                    success_count += 1
                    flow_id = f"{switch_id}_{flow.cookie}"
                    self.active_flows[flow_id] = {
                        'policy': policy_name,
                        'controller': controller_name,
                        'switch_id': switch_id,
                        'installed_at': time.time()
                    }

            if success_count > 0:
                self.quarantine_policies[policy_name] = policy
                logger.info(f"Quarantined IP {target_ip} on switch {switch_id} for {duration}s")
                return True
            else:
                logger.error(f"Failed to install quarantine flows for {target_ip}")
                return False

        except Exception as e:
            logger.error(f"Failed to quarantine IP {target_ip}: {e}")
            return False

    def release_quarantine(self, policy_name: str) -> bool:
        """Release a quarantined IP address"""
        try:
            if policy_name not in self.quarantine_policies:
                logger.warning(f"Quarantine policy {policy_name} not found")
                return False

            policy = self.quarantine_policies[policy_name]
            controller = self.get_controller_interface(policy.controller_name)

            if not controller:
                return False

            # Find and remove associated flows
            flows_to_remove = [
                flow_id for flow_id, flow_data in self.active_flows.items()
                if flow_data['policy'] == policy_name
            ]

            success_count = 0
            for flow_id in flows_to_remove:
                flow_data = self.active_flows[flow_id]
                if controller.delete_flow(flow_data['switch_id'], flow_id.split('_')[-1]):
                    success_count += 1
                    del self.active_flows[flow_id]

            if success_count > 0:
                policy.active = False
                logger.info(f"Released quarantine for policy {policy_name}")
                return True
            else:
                logger.error(f"Failed to remove quarantine flows for policy {policy_name}")
                return False

        except Exception as e:
            logger.error(f"Failed to release quarantine {policy_name}: {e}")
            return False

    def redirect_traffic(self, controller_name: str, switch_id: str, source_ip: str,
                        destination_port: str, duration: int = 300) -> bool:
        """
        Redirect traffic from a specific IP to a monitoring/analysis port
        """
        try:
            controller = self.get_controller_interface(controller_name)
            if not controller:
                return False

            # Create redirection flow
            flow = FlowRule(
                switch_id=switch_id,
                priority=200,
                match={
                    "ipv4_src": source_ip,
                    "eth_type": "0x0800"
                },
                actions=[
                    {"output-action": {"output-node-connector": destination_port}}
                ],
                idle_timeout=duration,
                cookie=int(time.time())
            )

            if controller.add_flow(switch_id, flow):
                flow_id = f"{switch_id}_{flow.cookie}"
                self.active_flows[flow_id] = {
                    'type': 'redirection',
                    'controller': controller_name,
                    'switch_id': switch_id,
                    'source_ip': source_ip,
                    'installed_at': time.time()
                }
                logger.info(f"Redirected traffic from {source_ip} to port {destination_port}")
                return True
            else:
                logger.error(f"Failed to redirect traffic from {source_ip}")
                return False

        except Exception as e:
            logger.error(f"Failed to redirect traffic from {source_ip}: {e}")
            return False

    def mirror_traffic(self, controller_name: str, switch_id: str, source_ip: str,
                      mirror_port: str, duration: int = 300) -> bool:
        """
        Mirror traffic from a specific IP to a monitoring port
        """
        try:
            controller = self.get_controller_interface(controller_name)
            if not controller:
                return False

            # Create mirroring flow (send to both original destination and mirror port)
            flow = FlowRule(
                switch_id=switch_id,
                priority=150,
                match={
                    "ipv4_src": source_ip,
                    "eth_type": "0x0800"
                },
                actions=[
                    {"output-action": {"output-node-connector": mirror_port}},
                    {"output-action": {"output-node-connector": "NORMAL"}}  # Continue normal forwarding
                ],
                idle_timeout=duration,
                cookie=int(time.time())
            )

            if controller.add_flow(switch_id, flow):
                flow_id = f"{switch_id}_{flow.cookie}"
                self.active_flows[flow_id] = {
                    'type': 'mirroring',
                    'controller': controller_name,
                    'switch_id': switch_id,
                    'source_ip': source_ip,
                    'mirror_port': mirror_port,
                    'installed_at': time.time()
                }
                logger.info(f"Mirroring traffic from {source_ip} to port {mirror_port}")
                return True
            else:
                logger.error(f"Failed to mirror traffic from {source_ip}")
                return False

        except Exception as e:
            logger.error(f"Failed to mirror traffic from {source_ip}: {e}")
            return False

    def _create_quarantine_flows(self, policy: QuarantinePolicy) -> List[FlowRule]:
        """Create flow rules for IP quarantine"""
        flows = []

        if policy.quarantine_vlan:
            # VLAN-based quarantine
            flow = FlowRule(
                switch_id=policy.switch_id,
                priority=300,
                match={
                    "ipv4_src": policy.target_ip,
                    "eth_type": "0x0800"
                },
                actions=[
                    {"push-vlan-action": {"ethernet-type": "0x8100"}},
                    {"set-field-action": {"vlan-vid": policy.quarantine_vlan}},
                    {"output-action": {"output-node-connector": "NORMAL"}}
                ],
                idle_timeout=policy.duration,
                cookie=int(time.time())
            )
            flows.append(flow)
        else:
            # Drop-based quarantine
            flow = FlowRule(
                switch_id=policy.switch_id,
                priority=300,
                match={
                    "ipv4_src": policy.target_ip,
                    "eth_type": "0x0800"
                },
                actions=[
                    {"drop-action": {}}
                ],
                idle_timeout=policy.duration,
                cookie=int(time.time())
            )
            flows.append(flow)

        return flows

    def start_monitoring(self):
        """Start background monitoring thread"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("SDN monitoring thread started")

    def stop_monitoring(self):
        """Stop background monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("SDN monitoring thread stopped")

    def _monitoring_loop(self):
        """Background monitoring loop for policy expiration"""
        while self.monitoring_active:
            try:
                current_time = time.time()

                # Check for expired quarantines
                expired_policies = [
                    policy_name for policy_name, policy in self.quarantine_policies.items()
                    if policy.active and policy.is_expired()
                ]

                for policy_name in expired_policies:
                    logger.info(f"Releasing expired quarantine policy: {policy_name}")
                    self.release_quarantine(policy_name)

                # Clean up expired flows (fallback cleanup)
                expired_flows = [
                    flow_id for flow_id, flow_data in self.active_flows.items()
                    if current_time - flow_data['installed_at'] > 3600  # 1 hour max
                ]

                for flow_id in expired_flows:
                    del self.active_flows[flow_id]

            except Exception as e:
                logger.error(f"Error in SDN monitoring loop: {e}")

            time.sleep(60)  # Check every minute

    def get_status(self) -> Dict[str, Any]:
        """Get SDN integration status"""
        return {
            'controllers': list(self.controllers.keys()),
            'active_quarantines': len([p for p in self.quarantine_policies.values() if p.active]),
            'active_flows': len(self.active_flows),
            'monitoring_active': self.monitoring_active,
            'total_quarantine_policies': len(self.quarantine_policies)
        }

    def get_quarantine_policies(self) -> List[Dict[str, Any]]:
        """Get all quarantine policies"""
        return [asdict(policy) for policy in self.quarantine_policies.values()]

    def get_active_flows(self) -> List[Dict[str, Any]]:
        """Get all active flows"""
        return list(self.active_flows.values())

# Global SDN manager instance
sdn_manager = None

def get_sdn_manager() -> SDNManager:
    """Get or create global SDN manager instance"""
    global sdn_manager
    if sdn_manager is None:
        sdn_manager = SDNManager()
    return sdn_manager

def setup_default_sdn():
    """Setup default SDN integrations from environment variables"""
    manager = get_sdn_manager()

    # OpenDaylight configuration
    odl_host = os.getenv('OPENDLIGHT_HOST')
    if odl_host:
        controller = SDNController(
            name="opendaylight",
            type=SDNControllerType.OPENDLIGHT,
            host=odl_host,
            port=int(os.getenv('OPENDLIGHT_PORT', '8181')),
            username=os.getenv('OPENDLIGHT_USERNAME', 'admin'),
            password=os.getenv('OPENDLIGHT_PASSWORD', 'admin')
        )
        manager.add_controller(controller)
        logger.info("Configured OpenDaylight SDN controller")

    # ONOS configuration
    onos_host = os.getenv('ONOS_HOST')
    if onos_host:
        controller = SDNController(
            name="onos",
            type=SDNControllerType.ONOS,
            host=onos_host,
            port=int(os.getenv('ONOS_PORT', '8181')),
            username=os.getenv('ONOS_USERNAME', 'onos'),
            password=os.getenv('ONOS_PASSWORD', 'rocks')
        )
        manager.add_controller(controller)
        logger.info("Configured ONOS SDN controller")

    # Ryu configuration
    ryu_host = os.getenv('RYU_HOST')
    if ryu_host:
        controller = SDNController(
            name="ryu",
            type=SDNControllerType.RYU,
            host=ryu_host,
            port=int(os.getenv('RYU_PORT', '8080'))
        )
        manager.add_controller(controller)
        logger.info("Configured Ryu SDN controller")

    # Start monitoring if controllers are configured
    if manager.controllers:
        manager.start_monitoring()
        logger.info("SDN monitoring started")

def quarantine_threat_ip(controller_name: str, switch_id: str, ip_address: str,
                         duration: int = 3600) -> bool:
    """Convenience function to quarantine a threat IP"""
    manager = get_sdn_manager()
    return manager.quarantine_ip(controller_name, switch_id, ip_address, duration)

def release_quarantine_policy(policy_name: str) -> bool:
    """Convenience function to release a quarantine"""
    manager = get_sdn_manager()
    return manager.release_quarantine(policy_name)
