#!/usr/bin/env python3
"""
ChaosPanda - Chaos Engineering Tool for Pasta Production System
Inspired by Netflix's ChaosMonkey
Randomly kills cutting machines and schedulers to test system resilience
"""

import logging
import os
import sys
import time
import argparse
from chaos_engine import ChaosEngine

# Logger setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s:%(name)s:%(message)s'
)
LOGGER = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='ChaosPanda - Chaos Engineering Tool for Pasta Production System'
    )
    
    parser.add_argument(
        '--max-cutting-machines',
        type=int,
        default=1,
        help='Maximum number of cutting machines to kill concurrently (default: 1)'
    )
    
    parser.add_argument(
        '--max-schedulers',
        type=int,
        default=0,
        help='Maximum number of schedulers to kill concurrently (default: 0)'
    )
    
    parser.add_argument(
        '--kafka-bootstrap',
        type=str,
        default='kafka:29092',
        help='Kafka bootstrap servers (default: kafka:29092)'
    )
    
    parser.add_argument(
        '--redis-host',
        type=str,
        default='redis',
        help='Redis host (default: redis)'
    )
    
    parser.add_argument(
        '--redis-port',
        type=int,
        default=6379,
        help='Redis port (default: 6379)'
    )
    
    parser.add_argument(
        '--docker-host',
        type=str,
        default='unix:///var/run/docker.sock',
        help='Docker socket or host (default: unix:///var/run/docker.sock)'
    )
    
    parser.add_argument(
        '--test-name',
        type=str,
        default='chaos-test',
        help='Test name for logging (default: chaos-test)'
    )
    
    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_arguments()
    
    LOGGER.info("=" * 80)
    LOGGER.info("🐼 ChaosPanda - Chaos Engineering for Pasta Production System")
    LOGGER.info("=" * 80)
    LOGGER.info(f"Configuration:")
    LOGGER.info(f"  Max Cutting Machines: {args.max_cutting_machines}")
    LOGGER.info(f"  Max Schedulers: {args.max_schedulers}")
    LOGGER.info(f"  Kafka Bootstrap: {args.kafka_bootstrap}")
    LOGGER.info(f"  Redis: {args.redis_host}:{args.redis_port}")
    LOGGER.info(f"  Docker Host: {args.docker_host}")
    LOGGER.info(f"  Test Name: {args.test_name}")
    LOGGER.info("=" * 80)
    
    try:
        # Create and start chaos engine
        chaos_engine = ChaosEngine(
            max_cutting_machines=args.max_cutting_machines,
            max_schedulers=args.max_schedulers,
            kafka_bootstrap_servers=args.kafka_bootstrap,
            redis_host=args.redis_host,
            redis_port=args.redis_port,
            docker_host=args.docker_host,
            test_name=args.test_name
        )
        
        chaos_engine.start()
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        LOGGER.info("\n" + "=" * 80)
        LOGGER.info("🛑 ChaosPanda shutdown signal received")
        LOGGER.info("=" * 80)
        sys.exit(0)
    except Exception as e:
        LOGGER.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()