import json
import logging
import math

from flask import request, jsonify

from routes import app

logger = logging.getLogger(__name__)


# Ticketing Agent Functions
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
        return max(0, int(30 * (1 - (distance / 6) ** 0.7)))


def calculate_customer_concert_points(customer, concert, priority_mapping):
    points = 0
    # VIP Status
    if customer.get('vip_status', False):
        points += 100
    
    # Credit Card Priority
    customer_credit_card = customer.get('credit_card', '')
    if customer_credit_card in priority_mapping:
        if priority_mapping[customer_credit_card] == concert.get('name', ''):
            points += 50
    
    # Distance/Latency
    distance = calculate_distance(
        customer.get('location', [0, 0]), 
        concert.get('booking_center_location', [0, 0])
    )
    distance_points = calculate_distance_points(distance)
    points += distance_points
    
    return points


@app.route('/ticketing-agent', methods=['POST'])
def ticketing_agent():
    """Main ticketing agent endpoint"""
    try:
        logger.info("Received request to /ticketing-agent")
        logger.info("Content-Type: {}".format(request.content_type))
        logger.info("Headers: {}".format(dict(request.headers)))
        
        content_type = request.content_type or ''
        if not content_type.startswith('application/json'):
            logger.error("Invalid content type: {}".format(content_type))
            return jsonify({"error": "Content-Type must be application/json"}), 400
    
        try:
            data = request.get_json(force=True)  # force=True to parse even if content-type is wrong
        except Exception as json_error:
            logger.error("JSON parsing error: {}".format(str(json_error)))
            return jsonify({"error": "Invalid JSON format"}), 400
        
        if not data:
            logger.error("No JSON data received or data is empty")
            return jsonify({"error": "No JSON data provided"}), 400
        
        logger.info("Received data keys: {}".format(list(data.keys())))
        
        customers = data.get('customers', [])
        concerts = data.get('concerts', [])
        priority = data.get('priority', {})
        
        logger.info("Processing {} customers and {} concerts".format(len(customers), len(concerts)))
        
        if not customers:
            return jsonify({"error": "No customers provided"}), 400
        if not concerts:
            return jsonify({"error": "No concerts provided"}), 400
        
        result = {}
        
        # For each customer, find the concert with highest points
        for customer in customers:
            customer_name = customer.get('name', 'UNKNOWN')
            best_concert = None
            max_points = -1
            
            logger.info("Processing customer: {}".format(customer_name))
            
            # Calculate points for each concert
            for concert in concerts:
                try:
                    points = calculate_customer_concert_points(customer, concert, priority)
                    logger.info("Customer {} -> Concert {}: {} points".format(
                        customer_name, concert.get('name', 'UNKNOWN'), points))
                    
                    if points > max_points:
                        max_points = points
                        best_concert = concert.get('name', 'UNKNOWN')
                except Exception as calc_error:
                    logger.error("Error calculating points for customer {} and concert {}: {}".format(
                        customer_name, concert.get('name', 'UNKNOWN'), str(calc_error)))
                    continue
            
            if best_concert:
                result[customer_name] = best_concert
                logger.info("Customer {} assigned to concert {} with {} points".format(
                    customer_name, best_concert, max_points))
        
        logger.info("Final result: {}".format(result))
        return jsonify(result), 200
    
    except Exception as e:
        logger.error("Unexpected error in ticketing_agent: {}".format(str(e)))
        logger.error("Exception type: {}".format(type(e).__name__))
        import traceback
        logger.error("Full traceback: {}".format(traceback.format_exc()))
        return jsonify({"error": "Internal server error"}), 500

