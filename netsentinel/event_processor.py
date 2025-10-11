#!/usr/bin/env python3
"""
Real-time event processor for OpenCanary hybrid system
Processes events from Kafka and provides real-time analysis with ML-powered anomaly detection
"""

import json
import time
import kafka
import redis
from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest
import threading
import os
import logging

# Import ML anomaly detector
from .ml_anomaly_detector import ml_detector

# Import firewall manager for automated response
from .firewall_manager import block_threat_ip, get_firewall_manager

# Import packet analyzer for network-level analysis
from .packet_analyzer import get_packet_analyzer

# Import threat intelligence for enhanced analysis
from .threat_intelligence import get_threat_intel_manager, check_threat_indicator

# Import enterprise database for long-term storage and analytics
from .enterprise_database import get_enterprise_db, store_security_event

app = Flask(__name__)

# Metrics
EVENTS_PROCESSED = Counter('events_processed_total', 'Total events processed', ['event_type'])
PROCESSING_DURATION = Histogram('event_processing_duration_seconds', 'Event processing time')
THREAT_SCORE = Counter('threat_score_total', 'Threat score accumulated', ['source_ip'])
ML_ANOMALY_SCORE = Counter('ml_anomaly_score_total', 'ML anomaly score accumulated', ['source_ip', 'model_type'])
HYBRID_THREAT_SCORE = Counter('hybrid_threat_score_total', 'Hybrid threat score (rule + ML)', ['source_ip'])

class EventProcessor:
    def __init__(self):
        self.kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092').split(',')
        self.valkey_host = os.getenv('VALKEY_HOST', 'valkey')
        self.valkey_port = int(os.getenv('VALKEY_PORT', 6379))
        self.valkey_password = os.getenv('VALKEY_PASSWORD', 'hybrid-detection-2024')
        
        # Kafka consumer
        self.consumer = kafka.KafkaConsumer(
            'netsentinel-events',
            bootstrap_servers=self.kafka_servers,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id='hybrid-processor'
        )
        
        # Valkey client
        self.valkey = redis.Redis(
            host=self.valkey_host,
            port=self.valkey_port,
            password=self.valkey_password,
            decode_responses=True
        )
        
        # Threat intelligence cache
        self.threat_cache = {}
        self.running = False
        
        # ML anomaly detector
        self.ml_detector = ml_detector
        self.ml_enabled = True
        
        # Hybrid scoring weights
        self.rule_weight = 0.6  # 60% rule-based
        self.ml_weight = 0.4    # 40% ML-based

        # Packet analyzer for network-level analysis
        self.packet_analyzer = get_packet_analyzer()
        self.packet_analysis_enabled = os.getenv('PACKET_ANALYSIS_ENABLED', 'true').lower() == 'true'

        # Setup packet analyzer callback
        if self.packet_analysis_enabled:
            self.packet_analyzer.add_analysis_callback(self._handle_packet_anomaly)

        # Threat intelligence for enhanced analysis
        self.threat_intel = get_threat_intel_manager()
        self.threat_intel_enabled = os.getenv('THREAT_INTEL_ENABLED', 'true').lower() == 'true'

        # Start threat intelligence updates if enabled
        if self.threat_intel_enabled:
            try:
                self.threat_intel.start_updates()
                logger.info("Threat intelligence updates started")
            except Exception as e:
                logger.error(f"Failed to start threat intelligence: {e}")

        # Enterprise database for long-term storage
        self.enterprise_db = get_enterprise_db()
        self.enterprise_db_enabled = os.getenv('ENTERPRISE_DB_ENABLED', 'true').lower() == 'true'

        if self.enterprise_db_enabled:
            logger.info("Enterprise database integration enabled")
    
    def start(self):
        self.running = True

        # Start packet analysis if enabled
        if self.packet_analysis_enabled:
            packet_interface = os.getenv('PACKET_ANALYSIS_INTERFACE', 'any')
            try:
                self.packet_analyzer.start_capture()
                logger.info(f"Packet analysis started on interface: {packet_interface}")
            except Exception as e:
                logger.error(f"Failed to start packet analysis: {e}")

        thread = threading.Thread(target=self._process_events)
        thread.daemon = True
        thread.start()
        return thread
    
    def _process_events(self):
        while self.running:
            try:
                message_batch = self.consumer.poll(timeout_ms=1000)
                for topic_partition, messages in message_batch.items():
                    for message in messages:
                        self._process_single_event(message.value)
            except Exception as e:
                print(f"Error processing events: {e}")
                time.sleep(1)
    
    def _process_single_event(self, event_data):
        start_time = time.time()
        
        try:
            # Extract event information
            event_type = event_data.get('logtype', 'unknown')
            source_ip = event_data.get('src_host', 'unknown')
            
            # Update metrics
            EVENTS_PROCESSED.labels(event_type=event_type).inc()
            
            # Calculate rule-based threat score
            rule_score = self._calculate_threat_score(event_data)
            
            # Calculate ML-based anomaly score
            ml_score = 0.0
            ml_analysis = {}
            if self.ml_enabled and self.ml_detector:
                try:
                    ml_score, ml_analysis = self.ml_detector.detect_anomaly(event_data)
                    ML_ANOMALY_SCORE.labels(source_ip=source_ip, model_type=self.ml_detector.model_type).inc(ml_score)
                except Exception as e:
                    print(f"ML detection error: {e}")
            
            # Calculate hybrid threat score
            hybrid_score = (self.rule_weight * rule_score) + (self.ml_weight * ml_score * 10)  # Scale ML score

            if hybrid_score > 0:
                THREAT_SCORE.labels(source_ip=source_ip).inc(rule_score)
                HYBRID_THREAT_SCORE.labels(source_ip=source_ip).inc(hybrid_score)

                # Automated response: Block high-threat IPs
                try:
                    blocked = block_threat_ip(source_ip, hybrid_score, "hybrid_threat_detection")
                    if blocked:
                        logger.info(f"Automatically blocked IP {source_ip} due to high threat score: {hybrid_score}")
                except Exception as e:
                    logger.error(f"Failed to block IP {source_ip}: {e}")
                
                # Store enhanced threat data in Valkey (short-term cache)
                threat_key = f"threat:{source_ip}"
                threat_data = {
                    'rule_score': rule_score,
                    'ml_score': ml_score,
                    'hybrid_score': hybrid_score,
                    'ml_analysis': ml_analysis,
                    'timestamp': time.time(),
                    'event': event_data,
                    'scoring_method': 'hybrid'
                }
                self.valkey.setex(threat_key, 3600, json.dumps(threat_data))

                # Store in enterprise database for long-term analytics
                if self.enterprise_db_enabled:
                    try:
                        # Prepare event data for enterprise storage
                        enterprise_event = {
                            'logtype': event_data.get('logtype'),
                            'src_host': source_ip,
                            'threat_score': hybrid_score,
                            'rule_score': rule_score,
                            'ml_score': ml_score,
                            'logdata': event_data.get('logdata', {}),
                            'processed_at': time.time(),
                            'tags': ['honeypot', 'processed']
                        }

                        if event_data.get('dst_port'):
                            enterprise_event['dst_port'] = event_data['dst_port']

                        store_security_event(enterprise_event, "threats")
                    except Exception as e:
                        logger.error(f"Failed to store event in enterprise database: {e}")
            
            # Real-time correlation
            self._correlate_events(event_data)
            
            PROCESSING_DURATION.observe(time.time() - start_time)
            
        except Exception as e:
            print(f"Error processing event: {e}")
    
    def _calculate_threat_score(self, event_data):
        """Calculate threat score based on event characteristics"""
        score = 0

        # Base score by event type
        event_type_scores = {
            2000: 5,  # FTP login attempt
            3000: 3,  # HTTP request
            4000: 8,  # SSH connection
            4002: 10, # SSH login attempt
            6001: 6,  # Telnet login attempt
            8001: 7,  # MySQL login attempt
            9999: 4,  # Packet anomaly
        }

        event_type = event_data.get('logtype', 0)
        score += event_type_scores.get(event_type, 1)

        # Additional scoring based on patterns
        if 'PASSWORD' in event_data.get('logdata', {}):
            score += 3

        if 'USERNAME' in event_data.get('logdata', {}):
            score += 2

        # Threat intelligence enrichment
        if self.threat_intel_enabled:
            score += self._calculate_threat_intel_score(event_data)

        return score

    def _calculate_threat_intel_score(self, event_data) -> int:
        """Calculate additional threat score from threat intelligence feeds"""
        score = 0

        try:
            source_ip = event_data.get('src_host')
            if source_ip:
                # Check if source IP is in threat intelligence
                threat_info = check_threat_indicator(source_ip)
                if threat_info:
                    # Base score for known malicious IP
                    score += 5

                    # Additional scoring based on confidence and threat type
                    confidence_bonus = threat_info.confidence // 20  # 0-5 points based on confidence
                    score += confidence_bonus

                    # Extra points for high-confidence threats
                    if threat_info.confidence >= 80:
                        score += 3

                    # Extra points for certain threat types
                    if threat_info.threat_type in ['botnet', 'malware', 'phishing']:
                        score += 2

                    logger.info(f"Threat intelligence match for IP {source_ip}: {threat_info.threat_type} "
                              f"(confidence: {threat_info.confidence}%) - added {score} points")

            # Check for other indicators in event data
            logdata = event_data.get('logdata', {})

            # Check domains in HTTP requests
            domain = logdata.get('domain') or logdata.get('host')
            if domain:
                threat_info = check_threat_indicator(domain)
                if threat_info and threat_info.indicator_type == 'domain':
                    score += 4  # Domain-based threats are significant
                    logger.info(f"Threat intelligence match for domain {domain}: {threat_info.threat_type}")

            # Check URLs in HTTP requests
            url = logdata.get('url')
            if url:
                threat_info = check_threat_indicator(url)
                if threat_info and threat_info.indicator_type == 'url':
                    score += 3
                    logger.info(f"Threat intelligence match for URL {url}: {threat_info.threat_type}")

        except Exception as e:
            logger.error(f"Error calculating threat intelligence score: {e}")

        return score

    def _correlate_events(self, event_data):
        """Correlate events for advanced threat detection"""
        source_ip = event_data.get('src_host')
        if not source_ip:
            return

        # Store recent events for correlation
        correlation_key = f"correlation:{source_ip}"
        self.valkey.lpush(correlation_key, json.dumps(event_data))
        self.valkey.ltrim(correlation_key, 0, 99)  # Keep last 100 events
        self.valkey.expire(correlation_key, 3600)  # Expire in 1 hour

    def _handle_packet_anomaly(self, event_type: str, anomaly_data: Dict):
        """Handle packet-level anomalies by converting to OpenCanary events"""
        try:
            if event_type != 'anomaly':
                return

            # Convert packet anomaly to OpenCanary event format
            event_data = {
                'logtype': 9999,  # Custom packet anomaly event type
                'logdata': {
                    'anomaly_type': anomaly_data['type'],
                    'severity': anomaly_data['severity'],
                    'details': anomaly_data['details'],
                    'packet_info': anomaly_data.get('packet_info', {}),
                    'flow_info': anomaly_data.get('flow_info', {})
                },
                'src_host': anomaly_data['src_ip'],
                'timestamp': anomaly_data['timestamp'],
                'anomaly_source': 'packet_analyzer'
            }

            # Add destination info if available
            if 'dst_port' in anomaly_data:
                event_data['dst_port'] = anomaly_data['dst_port']

            logger.info(f"Packet anomaly detected: {anomaly_data['type']} from {anomaly_data['src_ip']}")

            # Process through normal event pipeline
            self._process_single_event(event_data)

            # Store packet anomaly in enterprise database
            if self.enterprise_db_enabled:
                try:
                    self.enterprise_db.store_anomaly(anomaly_data)
                except Exception as e:
                    logger.error(f"Failed to store packet anomaly in enterprise database: {e}")

        except Exception as e:
            logger.error(f"Error handling packet anomaly: {e}")
    
    def get_threat_analysis(self, source_ip=None):
        """Get threat analysis for specific IP or all IPs"""
        if source_ip:
            threat_key = f"threat:{source_ip}"
            threat_data = self.valkey.get(threat_key)
            return json.loads(threat_data) if threat_data else None
        else:
            # Get all threats
            threats = {}
            for key in self.valkey.scan_iter(match="threat:*"):
                ip = key.split(':')[1]
                threat_data = self.valkey.get(key)
                if threat_data:
                    threats[ip] = json.loads(threat_data)
            return threats

# Global processor instance
processor = EventProcessor()

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': time.time()})

@app.route('/metrics')
def metrics():
    return generate_latest()

@app.route('/threats')
def get_threats():
    return jsonify(processor.get_threat_analysis())

@app.route('/threats/<source_ip>')
def get_threat_by_ip(source_ip):
    threat = processor.get_threat_analysis(source_ip)
    return jsonify(threat) if threat else jsonify({'error': 'Threat not found'}), 404

@app.route('/ml/model-info')
def get_ml_model_info():
    """Get information about the ML model"""
    if processor.ml_detector:
        return jsonify(processor.ml_detector.get_model_info())
    return jsonify({'error': 'ML detector not available'}), 404

@app.route('/ml/train', methods=['POST'])
def train_ml_model():
    """Train the ML model on normal events"""
    try:
        # This would typically receive training data from the request
        # For now, we'll use a simple training approach
        if processor.ml_detector:
            # Train on recent normal events (this is a simplified approach)
            normal_events = []
            for key in processor.valkey.scan_iter(match="correlation:*"):
                events = processor.valkey.lrange(key, 0, 10)
                for event_str in events:
                    try:
                        event_data = json.loads(event_str)
                        normal_events.append(event_data)
                    except:
                        continue

            if normal_events:
                processor.ml_detector.train_on_normal_events(normal_events)
                return jsonify({'status': 'success', 'trained_on': len(normal_events)})
            else:
                return jsonify({'error': 'No training data available'}), 400
        else:
            return jsonify({'error': 'ML detector not available'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Firewall Management Endpoints
@app.route('/firewall/status')
def get_firewall_status():
    """Get firewall status and blocked IPs"""
    try:
        firewall_mgr = get_firewall_manager()
        status = firewall_mgr.get_firewall_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/firewall/block/<ip_address>', methods=['POST'])
def block_ip_manual(ip_address):
    """Manually block an IP address"""
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'manual_block')

        firewall_mgr = get_firewall_manager()
        success = firewall_mgr.block_ip(ip_address, reason)

        if success:
            return jsonify({'status': 'success', 'message': f'IP {ip_address} blocked'})
        else:
            return jsonify({'error': f'Failed to block IP {ip_address}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/firewall/unblock/<ip_address>', methods=['POST'])
def unblock_ip_manual(ip_address):
    """Manually unblock an IP address"""
    try:
        firewall_mgr = get_firewall_manager()
        success = firewall_mgr.unblock_ip(ip_address)

        if success:
            return jsonify({'status': 'success', 'message': f'IP {ip_address} unblocked'})
        else:
            return jsonify({'error': f'Failed to unblock IP {ip_address}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/firewall/blocked')
def get_blocked_ips():
    """Get list of currently blocked IPs"""
    try:
        firewall_mgr = get_firewall_manager()
        blocked_ips = firewall_mgr.get_blocked_ips()
        return jsonify({
            'blocked_ips': blocked_ips,
            'count': len(blocked_ips)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/firewall/check/<ip_address>')
def check_ip_status(ip_address):
    """Check if an IP address is blocked"""
    try:
        firewall_mgr = get_firewall_manager()
        is_blocked = firewall_mgr.is_ip_blocked(ip_address)
        return jsonify({
            'ip_address': ip_address,
            'is_blocked': is_blocked
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Packet Analysis Endpoints
@app.route('/packet/status')
def get_packet_analysis_status():
    """Get packet analysis status and statistics"""
    try:
        analyzer = get_packet_analyzer()
        stats = analyzer.get_statistics()
        return jsonify({
            'packet_analysis_enabled': processor.packet_analysis_enabled,
            'interface': os.getenv('PACKET_ANALYSIS_INTERFACE', 'any'),
            'statistics': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/packet/anomalies')
def get_packet_anomalies():
    """Get recent packet-level anomalies"""
    try:
        analyzer = get_packet_analyzer()
        anomalies = analyzer.get_anomalies(limit=50)
        return jsonify({
            'anomalies': anomalies,
            'count': len(anomalies)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/packet/flows')
def get_active_flows():
    """Get information about active network flows"""
    try:
        analyzer = get_packet_analyzer()
        flows = analyzer.get_active_flows()
        return jsonify({
            'active_flows': flows,
            'count': len(flows)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/packet/start', methods=['POST'])
def start_packet_capture():
    """Start packet capture and analysis"""
    try:
        analyzer = get_packet_analyzer()
        interface = request.json.get('interface', 'any') if request.json else 'any'

        # Update analyzer with new interface if provided
        if interface != 'any':
            analyzer.interface = interface

        success = analyzer.start_capture()
        return jsonify({
            'status': 'success' if success else 'failed',
            'interface': analyzer.interface
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/packet/stop', methods=['POST'])
def stop_packet_capture():
    """Stop packet capture and analysis"""
    try:
        analyzer = get_packet_analyzer()
        analyzer.stop_capture()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Threat Intelligence Endpoints
@app.route('/threat-intel/status')
def get_threat_intel_status():
    """Get threat intelligence status and statistics"""
    try:
        manager = get_threat_intel_manager()
        stats = manager.get_statistics()
        return jsonify({
            'threat_intel_enabled': processor.threat_intel_enabled,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/threat-intel/check/<indicator>')
def check_threat_indicator_api(indicator):
    """Check if an indicator is in threat intelligence"""
    try:
        threat_info = check_threat_indicator(indicator)
        if threat_info:
            return jsonify({
                'is_threat': True,
                'indicator': threat_info.to_dict()
            })
        else:
            return jsonify({
                'is_threat': False,
                'indicator': indicator
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/threat-intel/indicators')
def get_threat_indicators():
    """Get threat indicators with optional filtering"""
    try:
        manager = get_threat_intel_manager()

        # Parse query parameters
        indicator_type = request.args.get('type')
        source = request.args.get('source')
        limit = int(request.args.get('limit', 50))

        indicators = manager.get_indicators(
            indicator_type=indicator_type,
            source=source,
            limit=limit
        )

        return jsonify({
            'indicators': [indicator.to_dict() for indicator in indicators],
            'count': len(indicators)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/threat-intel/feeds')
def get_threat_feeds():
    """Get threat intelligence feeds status"""
    try:
        manager = get_threat_intel_manager()
        feeds = {}

        for name, feed in manager.feeds.items():
            feeds[name] = {
                'name': feed.name,
                'url': feed.url,
                'feed_type': feed.feed_type,
                'enabled': feed.enabled,
                'update_interval': feed.update_interval,
                'last_update': feed.last_update,
                'last_success': feed.last_success,
                'error_count': feed.error_count
            }

        return jsonify({
            'feeds': feeds,
            'count': len(feeds)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/threat-intel/feeds/<feed_name>/enable', methods=['POST'])
def enable_threat_feed(feed_name):
    """Enable or disable a threat feed"""
    try:
        data = request.get_json() or {}
        enabled = data.get('enabled', True)

        manager = get_threat_intel_manager()
        manager.enable_feed(feed_name, enabled)

        return jsonify({
            'status': 'success',
            'feed': feed_name,
            'enabled': enabled
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/threat-intel/update', methods=['POST'])
def update_threat_feeds():
    """Manually trigger threat feed updates"""
    try:
        manager = get_threat_intel_manager()
        manager.update_feeds()

        return jsonify({
            'status': 'success',
            'message': 'Threat feed update initiated'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Enterprise Database Endpoints
@app.route('/db/status')
def get_database_status():
    """Get enterprise database status and statistics"""
    try:
        db = get_enterprise_db()
        stats = db.get_statistics()
        return jsonify({
            'enterprise_db_enabled': processor.enterprise_db_enabled,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/db/search/events')
def search_events():
    """Search security events in Elasticsearch"""
    try:
        # Parse query parameters
        index_type = request.args.get('index', 'events')
        size = int(request.args.get('size', 50))
        src_ip = request.args.get('src_ip')
        dst_port = request.args.get('dst_port')
        threat_score_min = request.args.get('threat_score_min')
        threat_score_max = request.args.get('threat_score_max')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')

        # Build Elasticsearch query
        query = {"bool": {"must": []}}

        if src_ip:
            query["bool"]["must"].append({"term": {"src_ip": src_ip}})

        if dst_port:
            query["bool"]["must"].append({"term": {"dst_port": int(dst_port)}})

        if threat_score_min or threat_score_max:
            range_query = {"range": {"threat_score": {}}}
            if threat_score_min:
                range_query["range"]["threat_score"]["gte"] = float(threat_score_min)
            if threat_score_max:
                range_query["range"]["threat_score"]["lte"] = float(threat_score_max)
            query["bool"]["must"].append(range_query)

        if start_time or end_time:
            time_range = {"range": {"@timestamp": {}}}
            if start_time:
                time_range["range"]["@timestamp"]["gte"] = start_time
            if end_time:
                time_range["range"]["@timestamp"]["lte"] = end_time
            query["bool"]["must"].append(time_range)

        # If no filters specified, match all
        if not query["bool"]["must"]:
            query = {"match_all": {}}

        db = get_enterprise_db()
        results = db.search_events(query, index_type, size)

        return jsonify({
            'query': query,
            'results': results,
            'total': results.get('hits', {}).get('total', {}).get('value', 0)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/db/metrics/<measurement>')
def get_metrics(measurement):
    """Get time-series metrics from InfluxDB"""
    try:
        hours = int(request.args.get('hours', 24))

        db = get_enterprise_db()
        metrics = db.get_metrics(measurement, hours)

        return jsonify({
            'measurement': measurement,
            'hours': hours,
            'data': metrics
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/db/events/recent')
def get_recent_events():
    """Get recent security events"""
    try:
        limit = int(request.args.get('limit', 20))

        # Query for recent events (last 24 hours)
        query = {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": "now-24h"}}}
                ]
            }
        }

        db = get_enterprise_db()
        results = db.search_events(query, "threats", limit)

        return jsonify({
            'period': '24h',
            'events': [hit['_source'] for hit in results.get('hits', {}).get('hits', [])],
            'count': len(results.get('hits', {}).get('hits', []))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/db/anomalies/recent')
def get_recent_anomalies():
    """Get recent anomaly detections"""
    try:
        limit = int(request.args.get('limit', 20))

        # Query for recent anomalies
        query = {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": "now-24h"}}}
                ]
            }
        }

        db = get_enterprise_db()
        results = db.search_events(query, "anomalies", limit)

        return jsonify({
            'period': '24h',
            'anomalies': [hit['_source'] for hit in results.get('hits', {}).get('hits', [])],
            'count': len(results.get('hits', {}).get('hits', []))
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Start event processor
    processor.start()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=8082, debug=False)
