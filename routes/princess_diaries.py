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
    
    # Compute shortest paths
    dist = shortest(list(stations), subway)
    
    # Sort tasks by start time
    tasks_orig = {task['name']: task for task in tasks}
    tasks = sorted(tasks, key=lambda x: x['start'])
    n = len(tasks)
    
    prev_compatible = [-1] * n
    for i in range(n):
        for j in range(i - 1, -1, -1):
            if tasks[j]['end'] <= tasks[i]['start']:
                prev_compatible[i] = j
                break
    
    dp = [(0, 0, [], start_station)]  
    
    for i in range(n):
        task = tasks[i]
        
        prev_score, prev_cost, prev_schedule, prev_station = dp[i]
        best_score = prev_score
        best_cost = prev_cost  
        best_schedule = prev_schedule[:]
        best_last_station = prev_station
        
        if prev_compatible[i] == -1:
            base_score, base_cost, base_schedule, base_station = 0, 0, [], start_station
        else:
            base_score, base_cost, base_schedule, base_station = dp[prev_compatible[i] + 1]
        
        travel_cost = dist[base_station][task['station']]
        new_score = base_score + task['score']
        new_cost = base_cost + travel_cost
        new_schedule = base_schedule + [task['name']]
        new_last_station = task['station']
        
        if (new_score > best_score or 
            (new_score == best_score and new_cost < best_cost)):
            best_score = new_score
            best_cost = new_cost
            best_schedule = new_schedule
            best_last_station = new_last_station
        
        dp.append((best_score, best_cost, best_schedule, best_last_station))
    
    final_score, travel_cost, schedule, last_station = dp[n]
    return_cost = dist[last_station][start_station]
    
    return {
        "max_score": final_score,
        "min_fee": travel_cost + return_cost,
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