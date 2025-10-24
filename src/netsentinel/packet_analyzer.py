#!/usr/bin/env python3
"""
Packet-level network analysis for NetSentinel
Uses Scapy for real-time packet capture and analysis
"""

import time
import threading
from typing import Dict, List, Optional, Tuple, Callable, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics

# Scapy imports
try:
    from scapy.all import sniff, IP, TCP, UDP, ICMP, Ether, get_if_list, conf
    from scapy.layers.http import HTTPRequest, HTTPResponse

    SCAPY_AVAILABLE = True
except ImportError:
    SCAPY_AVAILABLE = False
    import logging

    logger = logging.getLogger(__name__)
    logger.warning("Scapy not available. Packet analysis disabled.")

# Import new core components
try:
    from .core.base import BaseComponent
    from .core.models import ValidationResult
    from .utils.centralized import (
        handle_errors_simple as handle_errors,
        create_error_context_simple as create_error_context,
        create_logger,
    )
except ImportError:
    # Fallback for standalone usage
    from core.base import BaseComponent
    from core.models import ValidationResult
    from utils.centralized import (
        handle_errors_simple as handle_errors,
        create_error_context_simple as create_error_context,
        create_logger,
    )

logger = create_logger("packet_analyzer", level="INFO")


@dataclass
class PacketInfo:
    """Structured packet information"""

    timestamp: float
    src_ip: str
    dst_ip: str
    src_port: Optional[int]
    dst_port: Optional[int]
    protocol: str
    packet_size: int
    flags: Optional[str] = None
    seq_num: Optional[int] = None
    ack_num: Optional[int] = None
    ttl: Optional[int] = None
    window_size: Optional[int] = None
    payload_size: int = 0
    interface: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class FlowInfo:
    """Network flow information"""

    src_ip: str
    dst_ip: str
    src_port: int
    dst_port: int
    protocol: str
    start_time: float
    last_seen: float
    packet_count: int = 0
    byte_count: int = 0
    flags_seen: set = None

    def __post_init__(self):
        if self.flags_seen is None:
            self.flags_seen = set()

    @property
    def flow_key(self) -> str:
        """Generate unique flow key"""
        return f"{self.src_ip}:{self.src_port}-{self.dst_ip}:{self.dst_port}-{self.protocol}"

    def duration(self) -> float:
        """Get flow duration in seconds"""
        return self.last_seen - self.start_time

    def packets_per_second(self) -> float:
        """Calculate packets per second"""
        duration = self.duration()
        return self.packet_count / duration if duration > 0 else 0

    def bytes_per_second(self) -> float:
        """Calculate bytes per second"""
        duration = self.duration()
        return self.byte_count / duration if duration > 0 else 0


class PacketAnalyzer(BaseComponent):
    """
    Real-time packet capture and analysis engine
    Provides network traffic monitoring and anomaly detection
    """

    def __init__(
        self,
        name: str = "packet_analyzer",
        interface: str = "any",
        max_flows: int = 10000,
        flow_timeout: int = 300,
        enable_analysis: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize packet analyzer

        Args:
            name: Component name
            interface: Network interface to monitor ('any' for all)
            max_flows: Maximum number of active flows to track
            flow_timeout: Flow timeout in seconds
            enable_analysis: Enable real-time analysis
            config: Additional configuration
        """
        super().__init__(name, config, logger)

        if not SCAPY_AVAILABLE:
            self.logger.warning("Scapy not available - packet analysis will be limited")
            # Don't raise error, just disable functionality

        self.interface = interface
        self.max_flows = max_flows
        self.flow_timeout = flow_timeout
        self.enable_analysis = enable_analysis

        # Flow tracking
        self.active_flows = {}  # flow_key -> FlowInfo
        self.flow_queue = deque(maxlen=max_flows)

        # Packet statistics
        self.stats = {
            "total_packets": 0,
            "total_bytes": 0,
            "protocol_counts": defaultdict(int),
            "port_counts": defaultdict(int),
            "ip_counts": defaultdict(int),
            "start_time": time.time(),
        }

        # Analysis results
        self.anomalies = []
        self.analysis_callbacks = []

        # Threading - use proper thread management
        self.running = False
        self.capture_thread = None
        self.analysis_thread = None
        self._thread_lock = threading.RLock()  # Use RLock for better thread safety
        self._stop_event = threading.Event()  # Add stop event for clean shutdown
        self._shutdown_timeout = 10.0  # Maximum time to wait for threads to stop

        # Configuration
        self.suspicious_ports = {
            22,
            23,
            80,
            443,
            3306,
            3389,
            5900,
        }  # Common honeypot ports
        self.scan_detection_threshold = (
            10  # Packets per minute threshold for port scanning
        )

        logger.info(f"Initialized packet analyzer on interface: {interface}")

    def start_capture(self) -> bool:
        """
        Start packet capture and analysis

        Returns:
            bool: True if started successfully
        """
        with self._thread_lock:
            if self.running:
                logger.warning("Packet capture already running")
                return False

            try:
                self.running = True

                # Start capture thread
                self.capture_thread = threading.Thread(
                    target=self._capture_packets, daemon=True, name="packet_capture"
                )
                self.capture_thread.start()

                # Start analysis thread
                if self.enable_analysis:
                    self.analysis_thread = threading.Thread(
                        target=self._analyze_traffic,
                        daemon=True,
                        name="packet_analysis",
                    )
                    self.analysis_thread.start()

                logger.info("Packet capture and analysis started")
                return True

            except Exception as e:
                logger.error(f"Failed to start packet capture: {e}")
                self.running = False
                return False

    def stop_capture(self):
        """Stop packet capture and analysis"""
        with self._thread_lock:
            if not self.running:
                return

            self.running = False
            self._stop_event.set()  # Signal threads to stop

            # Wait for threads to finish with timeout
            if self.capture_thread and self.capture_thread.is_alive():
                self.capture_thread.join(timeout=self._shutdown_timeout)
                if self.capture_thread.is_alive():
                    logger.warning(
                        "Capture thread did not stop gracefully within timeout"
                    )

            if self.analysis_thread and self.analysis_thread.is_alive():
                self.analysis_thread.join(timeout=self._shutdown_timeout)
                if self.analysis_thread.is_alive():
                    logger.warning(
                        "Analysis thread did not stop gracefully within timeout"
                    )

            logger.info("Packet capture and analysis stopped")

    def _capture_packets(self):
        """Main packet capture loop"""

        def packet_callback(packet):
            if not self.running:
                return

            try:
                packet_info = self._parse_packet(packet)
                if packet_info:
                    self._process_packet(packet_info)
            except Exception as e:
                logger.error(f"Error processing packet: {e}")

        try:
            # Configure Scapy
            conf.sniff_promisc = True

            # Start sniffing
            logger.info(f"Starting packet capture on interface: {self.interface}")
            sniff(
                iface=self.interface,
                prn=packet_callback,
                store=0,
                stop_filter=lambda x: not self.running,
            )

        except Exception as e:
            logger.error(f"Packet capture failed: {e}")
            self.running = False

    def _parse_packet(self, packet) -> Optional[PacketInfo]:
        """Parse Scapy packet into structured format"""
        try:
            if not packet.haslayer(IP):
                return None

            ip_layer = packet[IP]
            packet_info = PacketInfo(
                timestamp=time.time(),
                src_ip=ip_layer.src,
                dst_ip=ip_layer.dst,
                packet_size=len(packet),
                ttl=ip_layer.ttl,
                interface=getattr(packet, "sniffed_on", ""),
            )

            # TCP layer
            if packet.haslayer(TCP):
                tcp_layer = packet[TCP]
                packet_info.protocol = "TCP"
                packet_info.src_port = tcp_layer.sport
                packet_info.dst_port = tcp_layer.dport
                packet_info.seq_num = tcp_layer.seq
                packet_info.ack_num = tcp_layer.ack
                packet_info.window_size = tcp_layer.window

                # TCP flags
                flags = []
                if tcp_layer.flags & 0x01:
                    flags.append("FIN")
                if tcp_layer.flags & 0x02:
                    flags.append("SYN")
                if tcp_layer.flags & 0x04:
                    flags.append("RST")
                if tcp_layer.flags & 0x08:
                    flags.append("PSH")
                if tcp_layer.flags & 0x10:
                    flags.append("ACK")
                if tcp_layer.flags & 0x20:
                    flags.append("URG")
                packet_info.flags = ",".join(flags)

                # Payload size
                if tcp_layer.payload:
                    packet_info.payload_size = len(tcp_layer.payload)

            # UDP layer
            elif packet.haslayer(UDP):
                udp_layer = packet[UDP]
                packet_info.protocol = "UDP"
                packet_info.src_port = udp_layer.sport
                packet_info.dst_port = udp_layer.dport
                packet_info.payload_size = (
                    len(udp_layer.payload) if udp_layer.payload else 0
                )

            # ICMP
            elif packet.haslayer(ICMP):
                packet_info.protocol = "ICMP"
                packet_info.payload_size = (
                    len(packet[ICMP].payload) if packet[ICMP].payload else 0
                )

            else:
                packet_info.protocol = "OTHER"

            return packet_info

        except Exception as e:
            logger.error(f"Error parsing packet: {e}")
            return None

    def _process_packet(self, packet_info: PacketInfo):
        """Process parsed packet information"""
        # Update statistics
        self.stats["total_packets"] += 1
        self.stats["total_bytes"] += packet_info.packet_size
        self.stats["protocol_counts"][packet_info.protocol] += 1

        if packet_info.src_ip:
            self.stats["ip_counts"][packet_info.src_ip] += 1

        if packet_info.src_port:
            self.stats["port_counts"][packet_info.src_port] += 1
        if packet_info.dst_port:
            self.stats["port_counts"][packet_info.dst_port] += 1

        # Update flows
        if packet_info.protocol in ["TCP", "UDP"]:
            self._update_flow(packet_info)

        # Real-time analysis
        if self.enable_analysis:
            anomaly = self._analyze_packet_realtime(packet_info)
            if anomaly:
                self.anomalies.append(anomaly)
                self._notify_callbacks("anomaly", anomaly)

    def _update_flow(self, packet_info: PacketInfo):
        """Update flow information"""
        flow_key = (
            f"{packet_info.src_ip}:{packet_info.src_port}-"
            f"{packet_info.dst_ip}:{packet_info.dst_port}-"
            f"{packet_info.protocol}"
        )

        if flow_key not in self.active_flows:
            # Create new flow
            if len(self.active_flows) >= self.max_flows:
                # Remove oldest flow
                oldest_key = self.flow_queue.popleft()
                if oldest_key in self.active_flows:
                    del self.active_flows[oldest_key]

            self.active_flows[flow_key] = FlowInfo(
                src_ip=packet_info.src_ip,
                dst_ip=packet_info.dst_ip,
                src_port=packet_info.src_port,
                dst_port=packet_info.dst_port,
                protocol=packet_info.protocol,
                start_time=packet_info.timestamp,
                last_seen=packet_info.timestamp,
            )
            self.flow_queue.append(flow_key)

        # Update existing flow
        flow = self.active_flows[flow_key]
        flow.last_seen = packet_info.timestamp
        flow.packet_count += 1
        flow.byte_count += packet_info.packet_size

        if packet_info.flags:
            flow.flags_seen.update(packet_info.flags.split(","))

    def _analyze_packet_realtime(self, packet_info: PacketInfo) -> Optional[Dict]:
        """Real-time packet anomaly detection"""
        anomaly = None

        # Port scanning detection
        if (
            packet_info.protocol == "TCP"
            and packet_info.flags
            and "SYN" in packet_info.flags
        ):
            # Check for port scanning behavior
            recent_packets = self._get_recent_packets_from_ip(
                packet_info.src_ip, 60
            )  # Last minute
            syn_packets = [
                p
                for p in recent_packets
                if p.protocol == "TCP" and p.flags and "SYN" in p.flags
            ]

            unique_ports = len(set(p.dst_port for p in syn_packets))
            if unique_ports >= self.scan_detection_threshold:
                anomaly = {
                    "type": "port_scan",
                    "timestamp": packet_info.timestamp,
                    "src_ip": packet_info.src_ip,
                    "details": f"Port scan detected: {unique_ports} unique ports in 60 seconds",
                    "severity": "high",
                    "packet_info": packet_info.to_dict(),
                }

        # Suspicious port activity
        if packet_info.dst_port in self.suspicious_ports:
            # Check for rapid connections to honeypot ports
            recent_connections = self._get_recent_packets_to_port(
                packet_info.dst_port, 300
            )  # Last 5 minutes
            connections_from_ip = len(
                [p for p in recent_connections if p.src_ip == packet_info.src_ip]
            )

            if connections_from_ip >= 5:  # Multiple connections from same IP
                anomaly = {
                    "type": "honeypot_activity",
                    "timestamp": packet_info.timestamp,
                    "src_ip": packet_info.src_ip,
                    "dst_port": packet_info.dst_port,
                    "details": f"Multiple connections to honeypot port {packet_info.dst_port}",
                    "severity": "medium",
                    "packet_info": packet_info.to_dict(),
                }

        # Unusual traffic patterns
        if packet_info.protocol == "TCP":
            flow_key = f"{packet_info.src_ip}:{packet_info.src_port}-{packet_info.dst_ip}:{packet_info.dst_port}-TCP"
            if flow_key in self.active_flows:
                flow = self.active_flows[flow_key]
                if flow.duration() > 0:
                    pps = flow.packets_per_second()
                    if pps > 100:  # Very high packet rate
                        anomaly = {
                            "type": "high_packet_rate",
                            "timestamp": packet_info.timestamp,
                            "src_ip": packet_info.src_ip,
                            "details": f"High packet rate: {pps:.1f} packets/second",
                            "severity": "medium",
                            "packet_info": packet_info.to_dict(),
                        }

        return anomaly

    def _analyze_traffic(self):
        """Periodic traffic analysis"""
        while self.running and not self._stop_event.is_set():
            try:
                # Use stop event for more responsive shutdown
                if self._stop_event.wait(
                    60
                ):  # Wait up to 60 seconds or until stop event
                    break

                # Clean up old flows
                self._cleanup_old_flows()

                # Perform periodic analysis
                periodic_anomalies = self._analyze_traffic_periodic()
                for anomaly in periodic_anomalies:
                    self.anomalies.append(anomaly)
                    self._notify_callbacks("anomaly", anomaly)

            except Exception as e:
                logger.error(f"Traffic analysis error: {e}")
                # Add small delay to prevent tight error loops
                time.sleep(1)

    def _analyze_traffic_periodic(self) -> List[Dict]:
        """Periodic traffic pattern analysis"""
        anomalies = []

        # Analyze flow patterns
        current_time = time.time()
        for flow_key, flow in self.active_flows.items():
            if flow.duration() < 60:  # Skip very short flows
                continue

            # Long-lived connections to suspicious ports
            if (
                flow.dst_port in self.suspicious_ports and flow.duration() > 600
            ):  # 10 minutes
                anomalies.append(
                    {
                        "type": "long_connection",
                        "timestamp": current_time,
                        "src_ip": flow.src_ip,
                        "dst_port": flow.dst_port,
                        "details": f"Long-lived connection to honeypot port: {flow.duration():.0f} seconds",
                        "severity": "low",
                        "flow_info": {
                            "packets": flow.packet_count,
                            "bytes": flow.byte_count,
                            "duration": flow.duration(),
                        },
                    }
                )

        return anomalies

    def _cleanup_old_flows(self):
        """Remove expired flows"""
        current_time = time.time()
        expired_keys = []

        for flow_key, flow in self.active_flows.items():
            if current_time - flow.last_seen > self.flow_timeout:
                expired_keys.append(flow_key)

        for key in expired_keys:
            if key in self.active_flows:
                del self.active_flows[key]

        # Clean up flow queue
        self.flow_queue = deque(
            [k for k in self.flow_queue if k in self.active_flows],
            maxlen=self.max_flows,
        )

        # Clean up old anomalies to prevent memory leaks
        if len(self.anomalies) > 1000:
            self.anomalies = self.anomalies[-500:]  # Keep only recent 500 anomalies

        # Clean up old statistics to prevent memory leaks
        if len(self.stats["ip_counts"]) > 10000:
            # Keep only top 5000 IPs by count
            sorted_ips = sorted(
                self.stats["ip_counts"].items(), key=lambda x: x[1], reverse=True
            )
            self.stats["ip_counts"] = dict(sorted_ips[:5000])

        if len(self.stats["port_counts"]) > 1000:
            # Keep only top 500 ports by count
            sorted_ports = sorted(
                self.stats["port_counts"].items(), key=lambda x: x[1], reverse=True
            )
            self.stats["port_counts"] = dict(sorted_ports[:500])

        # Clean up old protocol counts to prevent memory leaks
        if len(self.stats["protocol_counts"]) > 100:
            # Keep only top 50 protocols by count
            sorted_protocols = sorted(
                self.stats["protocol_counts"].items(), key=lambda x: x[1], reverse=True
            )
            self.stats["protocol_counts"] = dict(sorted_protocols[:50])

    def _get_recent_packets_from_ip(self, ip: str, seconds: int) -> List[PacketInfo]:
        """Get recent packets from a specific IP (simplified - would need packet buffer)"""
        # This is a simplified implementation
        # In a real system, you'd maintain a packet buffer
        return []

    def _get_recent_packets_to_port(self, port: int, seconds: int) -> List[PacketInfo]:
        """Get recent packets to a specific port"""
        # Simplified implementation
        return []

    def add_analysis_callback(self, callback: Callable):
        """Add callback for analysis events"""
        self.analysis_callbacks.append(callback)

    def _notify_callbacks(self, event_type: str, data: Dict):
        """Notify analysis callbacks"""
        for callback in self.analysis_callbacks:
            try:
                callback(event_type, data)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def get_statistics(self) -> Dict:
        """Get packet capture statistics"""
        runtime = time.time() - self.stats["start_time"]
        return {
            "runtime_seconds": runtime,
            "total_packets": self.stats["total_packets"],
            "total_bytes": self.stats["total_bytes"],
            "packets_per_second": (
                self.stats["total_packets"] / runtime if runtime > 0 else 0
            ),
            "bytes_per_second": (
                self.stats["total_bytes"] / runtime if runtime > 0 else 0
            ),
            "protocol_counts": dict(self.stats["protocol_counts"]),
            "top_ports": sorted(
                self.stats["port_counts"].items(), key=lambda x: x[1], reverse=True
            )[:10],
            "top_ips": sorted(
                self.stats["ip_counts"].items(), key=lambda x: x[1], reverse=True
            )[:10],
            "active_flows": len(self.active_flows),
            "anomalies_detected": len(self.anomalies),
        }

    def get_anomalies(self, limit: int = 100) -> List[Dict]:
        """Get recent anomalies"""
        return self.anomalies[-limit:] if self.anomalies else []

    def get_active_flows(self) -> List[Dict]:
        """Get information about active flows"""
        return [flow.__dict__ for flow in self.active_flows.values()]

    # BaseComponent abstract methods
    async def _initialize(self):
        """Initialize packet analyzer resources"""
        # Already done in __init__
        pass

    async def _start_internal(self):
        """Start packet analyzer internal operations"""
        # Packet analyzer is ready to use after initialization
        pass

    async def _stop_internal(self):
        """Stop packet analyzer internal operations"""
        # Stop packet capture if running
        if hasattr(self, "capture_thread") and self.capture_thread.is_alive():
            self.stop_capture()

    async def _cleanup(self):
        """Cleanup packet analyzer resources"""
        # Stop capture and clear flows
        if hasattr(self, "capture_thread") and self.capture_thread.is_alive():
            self.stop_capture()
        self.active_flows.clear()
        self.anomalies.clear()


# Global packet analyzer instance
packet_analyzer = None


def get_packet_analyzer() -> PacketAnalyzer:
    """Get or create global packet analyzer instance"""
    global packet_analyzer
    if packet_analyzer is None:
        packet_analyzer = PacketAnalyzer()
    return packet_analyzer


def start_packet_analysis(interface: str = "any") -> bool:
    """Convenience function to start packet analysis"""
    analyzer = get_packet_analyzer()
    return analyzer.start_capture()


def stop_packet_analysis():
    """Convenience function to stop packet analysis"""
    analyzer = get_packet_analyzer()
    analyzer.stop_capture()
