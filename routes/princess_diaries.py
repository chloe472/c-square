import json
import logging
from flask import request, jsonify
from routes import app

logger = logging.getLogger(__name__)

def shortest(stations, connections):
    dist = {}
    for i in stations:
        dist[i] = {}
        for j in stations:
            dist[i][j] = float('inf') if i != j else 0
    
    for conn in connections:
        u, v, cost = conn['connection'][0], conn['connection'][1], conn['fee']
        dist[u][v] = cost
        dist[v][u] = cost 
    
    for k in stations:
        for i in stations:
            for j in stations:
                if dist[i][k] + dist[k][j] < dist[i][j]:
                    dist[i][j] = dist[i][k] + dist[k][j]
    
    return dist

def solve_princess_diaries(data):
    tasks = data['tasks']
    subway = data['subway']
    start_station = data['starting_station']
    
    if not tasks:
        return {"max_score": 0, "min_fee": 0, "schedule": []}
    
    # Get all stations
    stations = set([start_station])
    for task in tasks:
        stations.add(task['station'])
    for conn in subway:
        stations.update(conn['connection'])
    
    dist = shortest(list(stations), subway)
    tasks = sorted(tasks, key=lambda x: x['start'])
    n = len(tasks)
    
    memo = {}
    parent = {}  

    next_non_overlapping = [n] * n
    for i in range(n):
        task = tasks[i]
        for j in range(i + 1, n):
            if tasks[j]['start'] >= task['end']:
                next_non_overlapping[i] = j
                break
    
    def dp(i, current_station):
        """Returns (max_score, min_cost)"""
        if i >= n:
            return 0, dist[current_station][start_station]
        
        if (i, current_station) in memo:
            return memo[(i, current_station)]
        
        skip_score, skip_cost = dp(i + 1, current_station)
        best_score, best_cost = skip_score, skip_cost
        best_choice = "skip"
        best_next_i = i + 1
        
        task = tasks[i]
        travel_cost = dist[current_station][task['station']]
        
        next_i = next_non_overlapping[i]
        
        take_future_score, take_future_cost = dp(next_i, task['station'])
        take_score = task['score'] + take_future_score
        take_cost = travel_cost + take_future_cost
        
        if (take_score > best_score or 
            (take_score == best_score and take_cost < best_cost)):
            best_score, best_cost = take_score, take_cost
            best_choice = "take"
            best_next_i = next_i
        
        memo[(i, current_station)] = (best_score, best_cost)
        
        if best_choice == "take":
            parent[(i, current_station)] = ("take", best_next_i)
        else:
            parent[(i, current_station)] = ("skip", best_next_i)
        
        return best_score, best_cost
    
    max_score, min_fee = dp(0, start_station)

    schedule = []
    i, current_station = 0, start_station
    
    while i < n:
        if (i, current_station) not in parent:
            break
            
        decision = parent[(i, current_station)]
        if isinstance(decision, tuple) and decision[0] == "take":
            schedule.append(tasks[i]['name'])
            current_station = tasks[i]['station']
            i = decision[1]
        else:
            i = decision[1] if isinstance(decision, tuple) else decision
    
    return {
        "max_score": max_score,
        "min_fee": min_fee,
        "schedule": schedule
    }

@app.route('/princess-diaries', methods=['POST'])
def princess_diaries():
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
        
        required_fields = ['tasks', 'subway', 'starting_station']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        result = solve_princess_diaries(data)
        
        logger.info(f"Solved princess diaries: max_score={result['max_score']}, min_fee={result['min_fee']}")
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error in princess_diaries: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500