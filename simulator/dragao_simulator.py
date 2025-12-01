# simulator/event_generator_system.py
from matplotlib.image import imread
import numpy as np
import matplotlib.pyplot as plt
import os
import json
import time
import uuid
from datetime import datetime
import threading
from collections import defaultdict

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False

print("=== STADIUM EVENT GENERATOR SYSTEM ===")

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC_EVENTS = "stadium/events"

class MQTTPublisher:
    def __init__(self, broker, port, topic):
        self.broker = broker
        self.port = port
        self.topic = topic
        self.client = None
        self.connected = False
        
        if MQTT_AVAILABLE:
            self.client = mqtt.Client(protocol=mqtt.MQTTv5)
            self.client.on_connect = self._on_connect
            try:
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_start()
                time.sleep(1)
            except Exception as e:
                print(f"MQTT não disponível: {e}")
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.connected = True
            print("✅ Conectado ao broker MQTT")
    
    def publish_event(self, event):
        if self.connected and self.client:
            self.client.publish(self.topic, json.dumps(event))

class EventGenerator:
    def __init__(self, mqtt_publisher):
        self.mqtt_publisher = mqtt_publisher
        self.events = []
        self.event_count = 0
        
        # Contadores para estatísticas
        self.gate_counters = defaultdict(int)
        self.zone_counters = defaultdict(int)
        self.queue_counters = defaultdict(lambda: {"count": 0, "arrivals": [], "departures": []})
        self.bin_fill_levels = {}
        
    def generate_event(self, event_type, person_id, location, metadata=None):
        """Evento genérico de pessoa"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now().isoformat() + "Z",
            "person_id": f"P_{person_id:06d}",
            "ticket_id": f"TKT_{person_id:06d}",
            "location": location,
            "metadata": metadata or {}
        }
        self.events.append(event)
        self.mqtt_publisher.publish_event(event)
        self.event_count += 1
        return event
    
    # ========== EVENTOS DE PORTÃO ==========
    
    def generate_gate_event(self, gate_name, person_id, direction="entry"):
        """Evento de passagem por portão (STAFF APP - gate counts)"""
        self.gate_counters[gate_name] += 1 if direction == "entry" else -1
        
        throughput = np.random.uniform(15, 25)
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "gate_passage",
            "timestamp": datetime.now().isoformat() + "Z",
            "gate_id": gate_name,
            "person_id": f"P_{person_id:06d}",
            "direction": direction,
            "current_count": self.gate_counters[gate_name],
            "throughput_per_min": round(throughput, 1),
            "metadata": {
                "heat_level": "red" if self.gate_counters[gate_name] > 150 
                             else "yellow" if self.gate_counters[gate_name] > 80 
                             else "green"
            }
        }
        self.events.append(event)
        self.mqtt_publisher.publish_event(event)
        self.event_count += 1
        return event
    
    # ========== EVENTOS DE CAIXOTES ==========
    
    def generate_bin_event(self, bin_id, location, fill_percentage=None):
        """Evento de enchimento de caixote do lixo (STAFF APP - maintenance)"""
        if fill_percentage is None:
            current = self.bin_fill_levels.get(bin_id, 0)
            fill_percentage = min(100, current + np.random.uniform(5, 15))
        
        self.bin_fill_levels[bin_id] = fill_percentage
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "bin_status",
            "timestamp": datetime.now().isoformat() + "Z",
            "bin_id": bin_id,
            "location": {"x": float(location[0]), "y": float(location[1])},
            "fill_percentage": round(fill_percentage, 1),
            "needs_service": fill_percentage > 85,
            "metadata": {
                "priority": "critical" if fill_percentage > 95 
                           else "high" if fill_percentage > 85 
                           else "medium" if fill_percentage > 70 
                           else "low",
                "poi_node": f"N{abs(hash(bin_id)) % 1000}"
            }
        }
        self.events.append(event)
        self.mqtt_publisher.publish_event(event)
        self.event_count += 1
        return event
    
    def generate_bin_overflow_alert(self, bin_id, location):
        """Alerta CRÍTICO de caixote a transbordar (específico para Cleaning)"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "bin_overflow_alert",
            "timestamp": datetime.now().isoformat() + "Z",
            "bin_id": bin_id,
            "location": {"x": float(location[0]), "y": float(location[1])},
            "priority": "high",
            "assigned_role": "cleaning",
            "metadata": {
                "action_required": "empty_bin",
                "poi_node": f"N{abs(hash(bin_id)) % 1000}"
            }
        }
        self.events.append(event)
        self.mqtt_publisher.publish_event(event)
        self.event_count += 1
        return event
    
    # ========== EVENTOS DE SENSORES DE INCÊNDIO ==========
    
    def generate_fire_alarm_event(self, sensor_id, location, smoke_level, temperature):
        """
        Evento de alarme de incêndio/fumo (sensor físico)
        Sensor de fumo/temperatura deteta anomalia
        """
        alarm_id = f"FIRE-{uuid.uuid4().hex[:6]}"
        
        # Determina severidade baseada nos valores dos sensores
        if smoke_level > 80 or temperature > 60:
            severity = "critical"
            priority = "critical"
        elif smoke_level > 50 or temperature > 45:
            severity = "high"
            priority = "high"
        else:
            severity = "medium"
            priority = "medium"
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "fire_alarm",
            "timestamp": datetime.now().isoformat() + "Z",
            "alarm_id": alarm_id,
            "sensor_id": sensor_id,
            "priority": priority,
            "location": {"x": float(location[0]), "y": float(location[1])},
            "sensor_readings": {
                "smoke_level_pct": round(smoke_level, 1),  # 0-100%
                "temperature_celsius": round(temperature, 1)
            },
            "severity": severity,
            "assigned_role": "security",  # Security coordena evacuação
            "status": "active",  # active, investigating, resolved, false_alarm
            "metadata": {
                "requires_evacuation": severity == "critical",
                "poi_node": f"N{abs(hash(sensor_id)) % 1000}",
                "affected_zones": []  # zonas próximas a evacuar
            }
        }
        self.events.append(event)
        self.mqtt_publisher.publish_event(event)
        self.event_count += 1
        return event
    
    def generate_staff_dispatch(self, alarm_id, staff_ids, staff_role, eta_seconds, route):
        """
        Despacho de equipa para alarme de incêndio
        Múltiplos staff podem ser despachados
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "staff_dispatch",
            "timestamp": datetime.now().isoformat() + "Z",
            "alarm_id": alarm_id,
            "staff_ids": staff_ids,  # lista de staff
            "staff_role": staff_role,  # security (coordena evacuação)
            "eta_seconds": eta_seconds,
            "route": route,
            "metadata": {
                "team_size": len(staff_ids),
                "dispatch_reason": "fire_alarm_response"
            }
        }
        self.events.append(event)
        self.mqtt_publisher.publish_event(event)
        self.event_count += 1
        return event
    
    def generate_staff_assignment(self, incident_id, staff_id, staff_role, eta_seconds, route):
        """Evento de atribuição de staff (Security/Cleaning/Supervisor)"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "staff_assignment",
            "timestamp": datetime.now().isoformat() + "Z",
            "incident_id": incident_id,
            "staff_id": staff_id,
            "staff_role": staff_role,
            "eta_seconds": eta_seconds,
            "route": route,
            "metadata": {
                "assignment_method": "nearest_available"
            }
        }
        self.events.append(event)
        self.mqtt_publisher.publish_event(event)
        self.event_count += 1
        return event
    
    # ========== EVENTOS DE EVACUAÇÃO ==========
    
    def generate_evacuation_event(self, edge_from, edge_to, reason="smoke"):
        """Evento de evacuação com fecho de corredor (AMBOS APPS)"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "evac_update",
            "timestamp": datetime.now().isoformat() + "Z",
            "closure": {
                "edge": f"{edge_from}-{edge_to}",
                "from_node": edge_from,
                "to_node": edge_to,
                "reason": reason,
                "closed": True
            },
            "metadata": {
                "severity": "critical" if reason in ["fire", "structural"] 
                           else "high" if reason == "smoke" 
                           else "medium"
            }
        }
        self.events.append(event)
        self.mqtt_publisher.publish_event(event)
        self.event_count += 1
        return event
    
    # ========== EVENTOS DE DENSIDADE ==========
    
    def generate_density_event(self, area_id, area_type, count, capacity, location_center):
        """Evento de densidade de pessoas numa área (AMBOS APPS - heatmap)"""
        occupancy_rate = (count / capacity * 100) if capacity > 0 else 0
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "crowd_density",
            "timestamp": datetime.now().isoformat() + "Z",
            "area_id": area_id,
            "area_type": area_type,
            "current_count": count,
            "capacity": capacity,
            "occupancy_rate": round(occupancy_rate, 1),
            "location": {"x": float(location_center[0]), "y": float(location_center[1])},
            "heat_level": "red" if occupancy_rate > 80 
                         else "yellow" if occupancy_rate > 50 
                         else "green",
            "metadata": {}
        }
        self.events.append(event)
        self.mqtt_publisher.publish_event(event)
        self.event_count += 1
        return event
    
    # ========== EVENTOS DE FILAS ==========
    
    def generate_queue_event(self, location_type, location_id, location, queue_length, avg_service_time=None):
        """Evento de fila de espera (FAN APP - wait times)"""
        if avg_service_time is None:
            avg_service_time = 2.0 if location_type == "TOILET" else 3.5
        
        wait_time_min = queue_length * avg_service_time if queue_length > 0 else 0
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "queue_update",
            "timestamp": datetime.now().isoformat() + "Z",
            "location_type": location_type,
            "location_id": location_id,
            "location": {"x": float(location[0]), "y": float(location[1])},
            "queue_length": queue_length,
            "estimated_wait_min": round(wait_time_min, 1),
            "metadata": {
                "status": "crowded" if wait_time_min > 8 
                         else "busy" if wait_time_min > 4 
                         else "normal",
                "avg_service_time_min": avg_service_time
            }
        }
        self.events.append(event)
        self.mqtt_publisher.publish_event(event)
        self.event_count += 1
        return event
    
    # ========== HELPERS ==========
    
    def update_zone_occupancy(self, zone_id, delta):
        """Atualiza contador de ocupação de zona"""
        self.zone_counters[zone_id] += delta
        self.zone_counters[zone_id] = max(0, self.zone_counters[zone_id])

class StadiumBoundaries:
    def __init__(self):
        self.stadium_bounds = {'x_min': -60, 'x_max': 60, 'y_min': -45, 'y_max': 45}
        self.field_center = [0, 0]
        self.field_radius_x = 35
        self.field_radius_y = 20
        
        self.gates = {
            'GATE_NORTH': [0, 48],
            'GATE_SOUTH': [0, -48],
            'GATE_EAST': [60, 0],
            'GATE_WEST': [-60, 0]
        }
        
        self.bars = {
            'BAR_NORTE': [0, 35],
            'BAR_SUL': [0, -35],
            'BAR_LESTE': [45, 0],
            'BAR_OESTE': [-45, 0]
        }
        
        self.toilets = {
            'WC_NORTE_1': [40, 30],
            'WC_NORTE_2': [-40, 30],
            'WC_SUL_1': [40, -30],
            'WC_SUL_2': [-40, -30],
            'WC_LESTE': [50, 0],
            'WC_OESTE': [-50, 0]
        }
        
        self.seating_areas = {
            'NORTE_1': [-55, 40], 'NORTE_2': [-35, 40], 'NORTE_3': [-15, 40], 
            'NORTE_4': [15, 40], 'NORTE_5': [35, 40], 'NORTE_6': [55, 40],
            'SUL_1': [-55, -40], 'SUL_2': [-35, -40], 'SUL_3': [-15, -40], 
            'SUL_4': [15, -40], 'SUL_5': [35, -40], 'SUL_6': [55, -40],
            'LESTE_1': [55, 25], 'LESTE_2': [55, 5], 'LESTE_3': [55, -25],
            'OESTE_1': [-55, 25], 'OESTE_2': [-55, 5], 'OESTE_3': [-55, -25]
        }
        
        self.zone_capacities = {
            **{k: 200 for k in self.seating_areas.keys()},
            **{k: 50 for k in self.bars.keys()},
            **{k: 30 for k in self.toilets.keys()},
            **{k: 100 for k in self.gates.keys()}
        }
        
        self.bins = {
            'BIN_NORTE_1': [-30, 38], 'BIN_NORTE_2': [30, 38],
            'BIN_SUL_1': [-30, -38], 'BIN_SUL_2': [30, -38],
            'BIN_LESTE': [52, 0], 'BIN_OESTE': [-52, 0],
            'BIN_BAR_NORTE': [5, 35], 'BIN_BAR_SUL': [5, -35]
        }
    
    def is_inside_stadium(self, x, y):
        return (self.stadium_bounds['x_min'] <= x <= self.stadium_bounds['x_max'] and 
                self.stadium_bounds['y_min'] <= y <= self.stadium_bounds['y_max'])
    
    def is_inside_field(self, x, y):
        norm_x = (x - self.field_center[0]) / self.field_radius_x
        norm_y = (y - self.field_center[1]) / self.field_radius_y
        return (norm_x**2 + norm_y**2) <= 1.0
    
    def is_position_allowed(self, x, y):
        return self.is_inside_stadium(x, y) and not self.is_inside_field(x, y)
    
    def get_nearest_gate(self, position):
        gates_list = list(self.gates.values())
        distances = [np.linalg.norm(np.array(position) - np.array(gate)) for gate in gates_list]
        nearest_idx = np.argmin(distances)
        return list(self.gates.keys())[nearest_idx], list(self.gates.values())[nearest_idx]
    
    def get_nearest_bar(self, position):
        bars_list = list(self.bars.values())
        distances = [np.linalg.norm(np.array(position) - np.array(bar)) for bar in bars_list]
        nearest_idx = np.argmin(distances)
        return list(self.bars.keys())[nearest_idx], list(self.bars.values())[nearest_idx]
    
    def get_nearest_toilet(self, position):
        toilets_list = list(self.toilets.values())
        distances = [np.linalg.norm(np.array(position) - np.array(toilet)) for toilet in toilets_list]
        nearest_idx = np.argmin(distances)
        return list(self.toilets.keys())[nearest_idx], list(self.toilets.values())[nearest_idx]
    
    def get_seat_near_gate(self, gate_name):
        if gate_name == 'GATE_NORTH':
            area_keys = ['NORTE_1', 'NORTE_2', 'NORTE_3', 'NORTE_4', 'NORTE_5', 'NORTE_6']
        elif gate_name == 'GATE_SOUTH':
            area_keys = ['SUL_1', 'SUL_2', 'SUL_3', 'SUL_4', 'SUL_5', 'SUL_6']
        elif gate_name == 'GATE_EAST':
            area_keys = ['LESTE_1', 'LESTE_2', 'LESTE_3']
        else:
            area_keys = ['OESTE_1', 'OESTE_2', 'OESTE_3']
        
        area_key = np.random.choice(area_keys)
        area_center = self.seating_areas[area_key]
        x = area_center[0] + np.random.uniform(-8, 8)
        y = area_center[1] + np.random.uniform(-5, 5)
        return area_key, [x, y]
    
    def get_zone_at_position(self, position):
        """Identifica em que zona a pessoa está"""
        x, y = position
        
        for bar_name, bar_pos in self.bars.items():
            if np.linalg.norm(np.array(position) - np.array(bar_pos)) < 5:
                return bar_name, "service"
        
        for toilet_name, toilet_pos in self.toilets.items():
            if np.linalg.norm(np.array(position) - np.array(toilet_pos)) < 5:
                return toilet_name, "service"
        
        for area_name, area_pos in self.seating_areas.items():
            if abs(x - area_pos[0]) < 10 and abs(y - area_pos[1]) < 8:
                return area_name, "seating"
        
        return "CORRIDOR", "corridor"

def run_stadium_simulation():
    print("INICIANDO SIMULAÇÃO COMPLETA COM TODOS OS EVENTOS")

    mqtt_publisher = MQTTPublisher(MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_EVENTS)
    event_gen = EventGenerator(mqtt_publisher)
    boundaries = StadiumBoundaries()

    FPS = 5
    SIMULATION_DURATION = 300
    STEPS = SIMULATION_DURATION * FPS
    n_pedestrians = 150

    TIMELINE = {
        "pre_game": 60, 
        "game_start": 120, 
        "half_time": 180, 
        "game_resume": 240, 
        "game_end": 280,
        "evacuation_complete": 300
    }

    START_POSITIONS = [
        [0, 47.4], [-10.6, 45.5],
        [-13, -44.6], [17, -43.8]
    ]

    try:
        stadium_img = imread("map_stadium.png")
        img_extent = [-70, 70, -55, 55]
        use_image = True
        
        gray = np.dot(stadium_img[...,:3], [0.299, 0.587, 0.114])
        walkable_mask = gray > 0.55
        
        for _ in range(4):
            walkable_mask = np.logical_and.reduce([walkable_mask,
                np.roll(walkable_mask, 1, axis=0), np.roll(walkable_mask, -1, axis=0),
                np.roll(walkable_mask, 1, axis=1), np.roll(walkable_mask, -1, axis=1)])
                
        def is_walkable_from_image(x, y):
            ix = int((x - img_extent[0]) / (img_extent[1] - img_extent[0]) * stadium_img.shape[1])
            iy = int((y - img_extent[2]) / (img_extent[3] - img_extent[2]) * stadium_img.shape[0])
            iy = stadium_img.shape[0] - 1 - iy
            if not (0 <= ix < stadium_img.shape[1] and 0 <= iy < stadium_img.shape[0]):
                return False
            return walkable_mask[iy, ix]
            
    except Exception as e:
        print(f"⚠️  Imagem não carregada: {e}")
        use_image = False
        img_extent = [-70, 70, -55, 55]
        is_walkable_from_image = lambda x, y: boundaries.is_position_allowed(x, y)

    def is_position_valid(x, y):
        if use_image:
            return is_walkable_from_image(x, y)
        else:
            return boundaries.is_position_allowed(x, y)

    positions = np.zeros((n_pedestrians, 2))
    states = np.zeros(n_pedestrians, dtype=int)
    destinations = np.zeros((n_pedestrians, 2))
    
    service_times = np.random.uniform(TIMELINE["half_time"] + 5, TIMELINE["game_resume"] - 10, n_pedestrians)
    
    assigned_seats = {}
    assigned_zones = {}
    entry_gates = {}
    current_destinations = {}
    
    for bin_id in boundaries.bins.keys():
        event_gen.bin_fill_levels[bin_id] = np.random.uniform(10, 30)

    for i in range(n_pedestrians):
        start_pos = START_POSITIONS[i % len(START_POSITIONS)]
        positions[i] = start_pos
        
        nearest_gate_name, nearest_gate_pos = boundaries.get_nearest_gate(start_pos)
        entry_gates[i] = nearest_gate_name
        
        zone_name, seat_pos = boundaries.get_seat_near_gate(nearest_gate_name)
        assigned_seats[i] = seat_pos
        assigned_zones[i] = zone_name
        
        while not is_position_valid(assigned_seats[i][0], assigned_seats[i][1]):
            zone_name, seat_pos = boundaries.get_seat_near_gate(nearest_gate_name)
            assigned_seats[i] = seat_pos
            assigned_zones[i] = zone_name

        states[i] = 3
        destinations[i] = assigned_seats[i].copy()
        
        event_gen.generate_event("person_inside_stadium", i,
            {"x": float(positions[i][0]), "y": float(positions[i][1])},
            {"initial_position": True, "nearest_gate": nearest_gate_name})
        
        event_gen.generate_gate_event(nearest_gate_name, i, direction="entry")

    plt.ion()
    fig, ax = plt.subplots(figsize=(14, 11))
    
    last_density_update = 0
    last_queue_update = 0
    last_bin_update = 0
    evacuation_triggered = False

    # ========== SENSORES DE INCÊNDIO ==========
    # Simula sensores de fumo/temperatura

    fire_sensors = {
        'SENSOR_BAR_NORTE': boundaries.bars['BAR_NORTE'],
        'SENSOR_BAR_SUL': boundaries.bars['BAR_SUL'],
        'SENSOR_WC_NORTE': boundaries.toilets['WC_NORTE_1'],
        'SENSOR_WC_SUL': boundaries.toilets['WC_SUL_1'],
        'SENSOR_CORREDOR_LESTE': [55, 15],
        'SENSOR_CORREDOR_OESTE': [-55, 15]
    }

    fire_alarm_triggered = False

    for step in range(STEPS):
        current_time = step / FPS
        ax.clear()
        
        if use_image:
            ax.imshow(stadium_img, extent=img_extent, aspect='equal')
        else:
            ax.set_facecolor('#003366')
            stadium_rect = plt.Rectangle((boundaries.stadium_bounds['x_min'], boundaries.stadium_bounds['y_min']),
                                       boundaries.stadium_bounds['x_max'] - boundaries.stadium_bounds['x_min'],
                                       boundaries.stadium_bounds['y_max'] - boundaries.stadium_bounds['y_min'],
                                       fill=False, edgecolor='white', linewidth=3)
            ax.add_patch(stadium_rect)
            
            field = plt.Ellipse(boundaries.field_center, 
                              boundaries.field_radius_x * 2, boundaries.field_radius_y * 2,
                              facecolor='darkgreen', alpha=0.7)
            ax.add_patch(field)
            
            for gate_name, gate_pos in boundaries.gates.items():
                ax.plot(gate_pos[0], gate_pos[1], 'go', markersize=10, alpha=0.7)
                ax.text(gate_pos[0], gate_pos[1] + 3, gate_name, ha='center', va='bottom', 
                       color='green', fontweight='bold', fontsize=8)
            
            for bar_name, bar_pos in boundaries.bars.items():
                ax.plot(bar_pos[0], bar_pos[1], 'ro', markersize=15, alpha=0.7)
                ax.text(bar_pos[0], bar_pos[1] + 3, bar_name, ha='center', va='bottom', 
                       color='red', fontweight='bold', fontsize=8)
            
            for toilet_name, toilet_pos in boundaries.toilets.items():
                ax.plot(toilet_pos[0], toilet_pos[1], 'bo', markersize=12, alpha=0.7)
                ax.text(toilet_pos[0], toilet_pos[1] + 3, toilet_name, ha='center', va='bottom', 
                       color='blue', fontweight='bold', fontsize=8)
            
            for bin_name, bin_pos in boundaries.bins.items():
                fill = event_gen.bin_fill_levels.get(bin_name, 0)
                color = 'red' if fill > 85 else 'orange' if fill > 70 else 'gray'
                ax.plot(bin_pos[0], bin_pos[1], 'o', color=color, markersize=8, alpha=0.6)
            
            # Mostrar sensores de incêndio
            for sensor_name, sensor_pos in fire_sensors.items():
                ax.plot(sensor_pos[0], sensor_pos[1], 's', color='darkred', markersize=10, alpha=0.7)
                ax.text(sensor_pos[0], sensor_pos[1] + 2, sensor_name, ha='center', va='bottom', 
                       color='darkred', fontweight='bold', fontsize=6)
        
        ax.axis('off')
        ax.set_xlim(img_extent[0], img_extent[1])
        ax.set_ylim(img_extent[2], img_extent[3])

        phase = "ENTRADA"
        if current_time > TIMELINE["game_end"]: phase = "SAÍDA"
        elif current_time > TIMELINE["game_resume"]: phase = "2ª PARTE"
        elif current_time > TIMELINE["half_time"]: phase = "INTERVALO"
        elif current_time > TIMELINE["game_start"]: phase = "1ª PARTE"
        elif current_time > TIMELINE["pre_game"]: phase = "PRÉ-JOGO"

        ax.set_title(f"ESTÁDIO DO DRAGÃO — {phase} — {current_time:.0f}s — Eventos: {event_gen.event_count}",
                     fontsize=16, color="white", backgroundcolor="#000080", pad=20)

        # ========== EVENTOS PERIÓDICOS ==========
        
        if current_time - last_density_update >= 10:
            for zone_name in list(boundaries.seating_areas.keys()) + list(boundaries.bars.keys()) + list(boundaries.toilets.keys()):
                count = event_gen.zone_counters.get(zone_name, 0)
                capacity = boundaries.zone_capacities.get(zone_name, 100)
                location = boundaries.seating_areas.get(zone_name) or boundaries.bars.get(zone_name) or boundaries.toilets.get(zone_name)
                
                if location:
                    zone_type = "seating" if zone_name in boundaries.seating_areas else "service"
                    event_gen.generate_density_event(zone_name, zone_type, count, capacity, location)
            
            last_density_update = current_time
        
        if current_time - last_queue_update >= 8:
            for bar_name, bar_pos in boundaries.bars.items():
                queue_length = event_gen.zone_counters.get(bar_name, 0)
                event_gen.generate_queue_event("BAR", bar_name, bar_pos, queue_length, avg_service_time=3.5)
            
            for toilet_name, toilet_pos in boundaries.toilets.items():
                queue_length = event_gen.zone_counters.get(toilet_name, 0)
                event_gen.generate_queue_event("TOILET", toilet_name, toilet_pos, queue_length, avg_service_time=2.0)
            
            last_queue_update = current_time
        
        if current_time - last_bin_update >= 15:
            for bin_id, bin_pos in boundaries.bins.items():
                increment = np.random.uniform(8, 15) if TIMELINE["half_time"] <= current_time < TIMELINE["game_resume"] else np.random.uniform(2, 5)
                event_gen.generate_bin_event(bin_id, bin_pos)
                
                if event_gen.bin_fill_levels.get(bin_id, 0) > 95:
                    event_gen.generate_bin_overflow_alert(bin_id, bin_pos)
                    print(f"🗑️  BIN OVERFLOW: {bin_id} precisa de limpeza urgente!")
            
            last_bin_update = current_time

        # ========== SENSORES DE INCÊNDIO ==========

        # ALARME DE INCÊNDIO: sensor de fumo/temperatura (muito raro)
        if not fire_alarm_triggered and TIMELINE["game_start"] < current_time < TIMELINE["game_end"]:
            if np.random.random() < 0.001:  # 0.1% chance (muito raro)
                
                # Escolhe sensor aleatório
                sensor_id = np.random.choice(list(fire_sensors.keys()))
                sensor_location = fire_sensors[sensor_id]
                
                # Simula leituras do sensor (valores anormais)
                smoke_level = np.random.uniform(60, 95)  # % de fumo
                temperature = np.random.uniform(40, 70)   # °C
                
                alarm = event_gen.generate_fire_alarm_event(
                    sensor_id,
                    sensor_location,
                    smoke_level,
                    temperature
                )
                
                print(f"🔥 ALARME DE INCÊNDIO: {sensor_id} - Fumo: {smoke_level:.0f}% Temp: {temperature:.0f}°C em t={current_time:.0f}s")
                
                # Despacha equipa de segurança
                staff_team = [f"STAFF_SECURITY_{i:03d}" for i in range(1, 4)]  # 3 seguranças
                
                event_gen.generate_staff_dispatch(
                    alarm["alarm_id"],
                    staff_team,
                    "security",
                    eta_seconds=np.random.randint(30, 90),
                    route=[f"N{np.random.randint(1, 100)}" for _ in range(4)]
                )
                
                # Se severidade CRITICAL → fecha corredor próximo (evacuação)
                if alarm["severity"] == "critical":
                    nearby_nodes = ["N23", "N24"]  # nós próximos do sensor
                    event_gen.generate_evacuation_event(
                        nearby_nodes[0], 
                        nearby_nodes[1], 
                        reason="fire"
                    )
                    print(f"⚠️  EVACUAÇÃO INICIADA: corredor {nearby_nodes[0]}-{nearby_nodes[1]} fechado")
                
                fire_alarm_triggered = True
        
        if not evacuation_triggered and current_time > TIMELINE["game_end"] + 5:
            if np.random.random() < 0.01:
                event_gen.generate_evacuation_event("N23", "N24", reason="crowd")
                evacuation_triggered = True
                print(f"⚠️  EVACUAÇÃO: corredor N23-N24 fechado em t={current_time:.0f}s")

        # ========== LÓGICA DE MOVIMENTO ==========
        
        for i in range(n_pedestrians):
            current_pos = positions[i]

            if states[i] == 3:
                direction = destinations[i] - current_pos
                distance = np.linalg.norm(direction)
                
                if distance > 1.0:
                    step_vector = (direction / distance) * 0.8
                    new_pos = current_pos + step_vector
                    
                    if is_position_valid(new_pos[0], new_pos[1]):
                        positions[i] = new_pos
                    else:
                        angle = np.random.uniform(-0.5, 0.5)
                        rotation = np.array([[np.cos(angle), -np.sin(angle)], 
                                           [np.sin(angle), np.cos(angle)]])
                        positions[i] = current_pos + rotation @ step_vector * 0.8
                else:
                    states[i] = 4
                    positions[i] = assigned_seats[i].copy()
                    
                    event_gen.update_zone_occupancy(assigned_zones[i], +1)
                    
                    event_gen.generate_event("person_sat_down", i,
                        {"x": float(positions[i][0]), "y": float(positions[i][1])}, 
                        {"seat_id": f"SEAT_{i:04d}", "gate": entry_gates[i], "zone": assigned_zones[i]})

            if (states[i] == 4 and 
                TIMELINE["half_time"] <= current_time < TIMELINE["game_resume"] and
                current_time >= service_times[i]):
                
                event_gen.update_zone_occupancy(assigned_zones[i], -1)
                
                if np.random.random() < 0.5:
                    states[i] = 5
                    bar_name, bar_pos = boundaries.get_nearest_bar(current_pos)
                    current_destinations[i] = bar_name
                    destinations[i] = bar_pos
                    
                    event_gen.generate_event("person_left_seat", i,
                        {"x": float(current_pos[0]), "y": float(current_pos[1])},
                        {"destination": bar_name, "type": "BAR", "nearest": True})
                else:
                    states[i] = 8
                    toilet_name, toilet_pos = boundaries.get_nearest_toilet(current_pos)
                    current_destinations[i] = toilet_name
                    destinations[i] = toilet_pos
                    
                    event_gen.generate_event("person_left_seat", i,
                        {"x": float(current_pos[0]), "y": float(current_pos[1])},
                        {"destination": toilet_name, "type": "TOILET", "nearest": True})

            if states[i] == 5:
                direction = destinations[i] - current_pos
                distance = np.linalg.norm(direction)
                
                if distance > 2.0:
                    step_vector = (direction / distance) * 0.7
                    new_pos = current_pos + step_vector
                    
                    if is_position_valid(new_pos[0], new_pos[1]):
                        positions[i] = new_pos
                else:
                    states[i] = 6
                    positions[i] = destinations[i].copy()
                    
                    event_gen.update_zone_occupancy(current_destinations[i], +1)
                    
                    event_gen.generate_event("person_at_bar", i,
                        {"x": float(positions[i][0]), "y": float(positions[i][1])},
                        {"bar_name": current_destinations[i], "nearest": True})
                    
                    def return_from_bar(person_idx, wait_time):
                        time.sleep(wait_time)
                        if person_idx < len(states) and states[person_idx] == 6:
                            states[person_idx] = 7
                            destinations[person_idx] = assigned_seats[person_idx].copy()
                    
                    wait_time = np.random.uniform(10, 30) / FPS
                    threading.Thread(target=return_from_bar, args=(i, wait_time), daemon=True).start()

            if states[i] == 7:
                direction = destinations[i] - current_pos
                distance = np.linalg.norm(direction)
                
                if distance > 1.0:
                    step_vector = (direction / distance) * 0.7
                    new_pos = current_pos + step_vector
                    
                    if is_position_valid(new_pos[0], new_pos[1]):
                        positions[i] = new_pos
                else:
                    states[i] = 4
                    positions[i] = assigned_seats[i].copy()
                    
                    if current_destinations[i]:
                        event_gen.update_zone_occupancy(current_destinations[i], -1)
                    event_gen.update_zone_occupancy(assigned_zones[i], +1)
                    
                    event_gen.generate_event("person_returned_to_seat", i,
                        {"x": float(positions[i][0]), "y": float(positions[i][1])},
                        {"seat_id": f"SEAT_{i:04d}", "from": "BAR", "zone": assigned_zones[i]})

            if states[i] == 8:
                direction = destinations[i] - current_pos
                distance = np.linalg.norm(direction)
                
                if distance > 2.0:
                    step_vector = (direction / distance) * 0.6
                    new_pos = current_pos + step_vector
                    
                    if is_position_valid(new_pos[0], new_pos[1]):
                        positions[i] = new_pos
                else:
                    states[i] = 9
                    positions[i] = destinations[i].copy()
                    
                    event_gen.update_zone_occupancy(current_destinations[i], +1)
                    
                    event_gen.generate_event("person_at_toilet", i,
                        {"x": float(positions[i][0]), "y": float(positions[i][1])},
                        {"toilet_name": current_destinations[i], "nearest": True})
                    
                    def return_from_toilet(person_idx, wait_time):
                        time.sleep(wait_time)
                        if person_idx < len(states) and states[person_idx] == 9:
                            states[person_idx] = 10
                            destinations[person_idx] = assigned_seats[person_idx].copy()
                    
                    wait_time = np.random.uniform(5, 15) / FPS
                    threading.Thread(target=return_from_toilet, args=(i, wait_time), daemon=True).start()

            if states[i] == 10:
                direction = destinations[i] - current_pos
                distance = np.linalg.norm(direction)
                
                if distance > 1.0:
                    step_vector = (direction / distance) * 0.6
                    new_pos = current_pos + step_vector
                    
                    if is_position_valid(new_pos[0], new_pos[1]):
                        positions[i] = new_pos
                else:
                    states[i] = 4
                    positions[i] = assigned_seats[i].copy()
                    
                    if current_destinations[i]:
                        event_gen.update_zone_occupancy(current_destinations[i], -1)
                    event_gen.update_zone_occupancy(assigned_zones[i], +1)
                    
                    event_gen.generate_event("person_returned_to_seat", i,
                        {"x": float(positions[i][0]), "y": float(positions[i][1])},
                        {"seat_id": f"SEAT_{i:04d}", "from": "TOILET", "zone": assigned_zones[i]})

            if current_time > TIMELINE["game_end"] and states[i] == 4:
                states[i] = 11
                exit_gate_name, exit_gate_pos = boundaries.get_nearest_gate(current_pos)
                current_destinations[i] = exit_gate_name
                destinations[i] = exit_gate_pos
                
                event_gen.update_zone_occupancy(assigned_zones[i], -1)
                
                event_gen.generate_event("person_leaving_stadium", i,
                    {"x": float(current_pos[0]), "y": float(current_pos[1])},
                    {"exit_gate": exit_gate_name})

            if states[i] == 11:
                direction = destinations[i] - current_pos
                distance = np.linalg.norm(direction)
                
                if distance > 2.0:
                    step_vector = (direction / distance) * 0.9
                    new_pos = current_pos + step_vector
                    
                    if is_position_valid(new_pos[0], new_pos[1]):
                        positions[i] = new_pos
                else:
                    states[i] = 12
                    positions[i] = destinations[i].copy()
                    
                    event_gen.generate_gate_event(current_destinations[i], i, direction="exit")
                    
                    event_gen.generate_event("person_exited_stadium", i,
                        {"x": float(positions[i][0]), "y": float(positions[i][1])},
                        {"exit_gate": current_destinations.get(i, "UNKNOWN")})

        # ========== VISUALIZAÇÃO ==========
        colors = {
            3: 'cyan', 4: 'lime', 5: 'red', 6: 'magenta', 7: 'orange',
            8: 'purple', 9: 'pink', 10: 'brown', 11: 'yellow', 12: 'gray'
        }
        
        labels = {
            3: 'Indo lugar', 4: 'Sentado', 5: 'Indo bar', 6: 'No bar', 7: 'Voltando bar',
            8: 'Indo WC', 9: 'No WC', 10: 'Voltando WC', 11: 'Saindo', 12: 'Saiu'
        }
        
        start_array = np.array(START_POSITIONS)
        ax.scatter(start_array[:, 0], start_array[:, 1], 
                  c='yellow', s=30, alpha=0.5, marker='x', label='Posições Iniciais')
        
        seat_positions = np.array(list(assigned_seats.values()))
        ax.scatter(seat_positions[:, 0], seat_positions[:, 1], 
                  c='blue', s=15, alpha=0.3, marker='s', label='Cadeiras')
        
        for state, color in colors.items():
            indices = (states == state) & (states != 12)
            if np.any(indices):
                ax.scatter(positions[indices, 0], positions[indices, 1], 
                          c=color, s=40, label=labels[state], edgecolors='black', linewidth=0.5)

        ax.legend(loc='upper left', fontsize=8)
        plt.draw()
        plt.pause(0.01)

    plt.ioff()
    plt.show()

    os.makedirs("../outputs", exist_ok=True)
    with open("../outputs/stadium_events.json", "w", encoding="utf-8") as f:
        json.dump(event_gen.events, f, indent=2, ensure_ascii=False)

    print(f"\n✅ SIMULAÇÃO CONCLUÍDA!")
    print(f"📊 Total de eventos gerados: {event_gen.event_count}")
    print(f"📁 Eventos salvos em: ../outputs/stadium_events.json")
    print(f"\n📈 ESTATÍSTICAS:")
    print(f"   - Pessoas que entraram: {n_pedestrians}")
    print(f"   - Pessoas que saíram: {np.sum(states == 12)}")
    print(f"   - Bins acima de 85%: {sum(1 for v in event_gen.bin_fill_levels.values() if v > 85)}")
    if fire_alarm_triggered:
        print(f"   - Alarme de incêndio ativado: SIM")
    else:
        print(f"   - Alarme de incêndio ativado: NÃO")

if __name__ == "__main__":
    run_stadium_simulation()