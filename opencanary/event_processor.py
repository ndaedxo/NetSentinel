#!/usr/bin/env python3
"""
Real-time event processor for OpenCanary hybrid system
Processes events from Kafka and provides real-time analysis
"""

import json
import time
import kafka
import redis
from flask import Flask, jsonify
from prometheus_client import Counter, Histogram, generate_latest
import threading
import os

app = Flask(__name__)

# Metrics
EVENTS_PROCESSED = Counter('events_processed_total', 'Total events processed', ['event_type'])
PROCESSING_DURATION = Histogram('event_processing_duration_seconds', 'Event processing time')
THREAT_SCORE = Counter('threat_score_total', 'Threat score accumulated', ['source_ip'])

class EventProcessor:
    def __init__(self):
        self.kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092').split(',')
        self.valkey_host = os.getenv('VALKEY_HOST', 'valkey')
        self.valkey_port = int(os.getenv('VALKEY_PORT', 6379))
        self.valkey_password = os.getenv('VALKEY_PASSWORD', 'hybrid-detection-2024')
        
        # Kafka consumer
        self.consumer = kafka.KafkaConsumer(
            'opencanary-events',
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
    
    def start(self):
        self.running = True
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
            
            # Calculate threat score
            threat_score = self._calculate_threat_score(event_data)
            if threat_score > 0:
                THREAT_SCORE.labels(source_ip=source_ip).inc(threat_score)
                
                # Store in Valkey for real-time queries
                threat_key = f"threat:{source_ip}"
                self.valkey.setex(threat_key, 3600, json.dumps({
                    'score': threat_score,
                    'timestamp': time.time(),
                    'event': event_data
                }))
            
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
        }
        
        event_type = event_data.get('logtype', 0)
        score += event_type_scores.get(event_type, 1)
        
        # Additional scoring based on patterns
        if 'PASSWORD' in event_data.get('logdata', {}):
            score += 3
        
        if 'USERNAME' in event_data.get('logdata', {}):
            score += 2
        
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

if __name__ == '__main__':
    # Start event processor
    processor.start()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=8082, debug=False)
