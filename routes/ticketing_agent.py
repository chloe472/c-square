import json
import logging
import math

from flask import request, jsonify

from routes import app

logger = logging.getLogger(__name__)


def calculate_distance(customer_location, booking_center_location):
    """Calculate distance between customer and booking center"""
    x1, y1 = customer_location
    x2, y2 = booking_center_location
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

def calculate_distance_points(distance):
    """Calculate points based on distance"""
    if distance >= 6:
        return 0
    elif distance <= 0:
        return 30
    else:
        return max(0, int(30 - (distance / 6) * 30))


def calculate_customer_concert_points(customer, concert, priority_mapping):
    """Calculate total points for a customer-concert combination"""
    points = 0
    
    # VIP Status
    if customer['vip_status']:
        points += 100
    
    # Credit Card Priority
    customer_credit_card = customer['credit_card']
    if customer_credit_card in priority_mapping:
        if priority_mapping[customer_credit_card] == concert['name']:
            points += 50
    
    # Distance/Latency
    distance = calculate_distance(customer['location'], concert['booking_center_location'])
    distance_points = calculate_distance_points(distance)
    points += distance_points
    
    return points


@app.route('/ticketing-agent', methods=['POST'])
def ticketing_agent():
    try:
        if request.content_type != 'application/json':
            logger.error("Invalid content type: {}".format(request.content_type))
            return jsonify({"error": "Content-Type must be application/json"}), 400
        
        data = request.get_json()
        
        if not data:
            logger.error("No JSON data received")
            return jsonify({"error": "Invalid JSON"}), 400
        
        logger.info("Received ticketing agent request: {}".format(data))
        
        customers = data.get('customers', [])
        concerts = data.get('concerts', [])
        priority = data.get('priority', {})
        
        result = {}
        
        # For each customer, find the concert with highest points
        for customer in customers:
            customer_name = customer['name']
            best_concert = None
            max_points = -1
            
            logger.info("Processing customer: {}".format(customer_name))
            
            # Calculate points for each concert
            for concert in concerts:
                points = calculate_customer_concert_points(customer, concert, priority)
                logger.info("Customer {} -> Concert {}: {} points".format(
                    customer_name, concert['name'], points))
                
                if points > max_points:
                    max_points = points
                    best_concert = concert['name']
            
            result[customer_name] = best_concert
            logger.info("Customer {} assigned to concert {} with {} points".format(
                customer_name, best_concert, max_points))
        
        logger.info("Final result: {}".format(result))
        return jsonify(result), 200
    
    except Exception as e:
        logger.error("Error in ticketing_agent: {}".format(str(e)))
        return jsonify({"error": str(e)}), 500
