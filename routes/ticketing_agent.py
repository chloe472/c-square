import json
import logging
import math

from flask import request, jsonify

from routes import app

logger = logging.getLogger(__name__)


# Ticketing Agent Functions
def calculate_distance_squared(customer_location, booking_center_location):
    """Calculate squared distance"""
    x1, y1 = customer_location
    x2, y2 = booking_center_location
    return (x1 - x2) ** 2 + (y1 - y2) ** 2


def calculate_distance_points(distance_squared):
    """Calculate points based on squared distance"""
    # distance >= 6 means distance_squared >= 36
    if distance_squared >= 36:
        return 0
    # distance <= 0 means distance_squared <= 0 
    elif distance_squared <= 0:
        return 30
    else:
        distance = math.sqrt(distance_squared)
        return max(0, int(30 - (distance / 6) * 30))


def calculate_customer_concert_points(customer, concert, priority_mapping):
    points = 0
    
    # VIP Status
    if customer.get('vip_status', False):
        points += 100
    
    # Credit Card Priority 
    customer_credit_card = customer.get('credit_card')
    if customer_credit_card and customer_credit_card in priority_mapping:
        if priority_mapping[customer_credit_card] == concert.get('name'):
            points += 50
    
    # Distance/Latency 
    customer_loc = customer.get('location', [0, 0])
    concert_loc = concert.get('booking_center_location', [0, 0])
    distance_squared = calculate_distance_squared(customer_loc, concert_loc)
    distance_points = calculate_distance_points(distance_squared)
    points += distance_points
    
    return points


@app.route('/ticketing-agent', methods=['POST'])
def ticketing_agent():
    try:
        content_type = request.content_type or ''
        if not content_type.startswith('application/json'):
            return jsonify({"error": "Content-Type must be application/json"}), 400
    
        try:
            data = request.get_json(force=True)
        except Exception:
            return jsonify({"error": "Invalid JSON format"}), 400
        
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        customers = data.get('customers', [])
        concerts = data.get('concerts', [])
        priority = data.get('priority', {})
        
        if not customers:
            return jsonify({"error": "No customers provided"}), 400
        if not concerts:
            return jsonify({"error": "No concerts provided"}), 400
        
        result = {}
        
        concert_list = [(concert.get('name', 'UNKNOWN'), concert) for concert in concerts]
        
        for customer in customers:
            customer_name = customer.get('name', 'UNKNOWN')
            best_concert = None
            max_points = -1
            
            # Calculate points for each concert
            for concert_name, concert in concert_list:
                try:
                    points = calculate_customer_concert_points(customer, concert, priority)
                    
                    if points > max_points:
                        max_points = points
                        best_concert = concert_name
                except Exception:
                    # Skip this concert on error
                    continue
            
            if best_concert:
                result[customer_name] = best_concert
        return jsonify(result), 200
    
    except Exception as e:
        logger.error("Unexpected error in ticketing_agent: {}".format(str(e)))
        return jsonify({"error": "Internal server error"}), 500
