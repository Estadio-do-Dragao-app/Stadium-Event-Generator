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
            print("Conectado ao broker MQTT")
    
    def publish_event(self, event):
        if self.connected and self.client:
            self.client.publish(self.topic, json.dumps(event))

class EventGenerator:
    def __init__(self, mqtt_publisher):
        self.mqtt_publisher = mqtt_publisher
        self.events = []
        self.event_count = 0
    
    def generate_event(self, event_type, person_id, location, metadata=None):
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

class StadiumBoundaries:
    def __init__(self):
        self.stadium_bounds = {'x_min': -60, 'x_max': 60, 'y_min': -45, 'y_max': 45}
        self.field_center = [0, 0]
        self.field_radius_x = 35
        self.field_radius_y = 20
        
        # Portões de entrada
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
            'NORTE_1': [-55, 40], 'NORTE_2': [-35, 40], 'NORTE_3': [-15, 40], 'NORTE_4': [15, 40], 'NORTE_5': [35, 40], 'NORTE_6': [55, 40],
            'SUL_1': [-55, -40], 'SUL_2': [-35, -40], 'SUL_3': [-15, -40], 'SUL_4': [15, -40], 'SUL_5': [35, -40], 'SUL_6': [55, -40],
            'LESTE_1': [55, 25], 'LESTE_2': [55, 5], 'LESTE_3': [55, -25],
            'OESTE_1': [-55, 25], 'OESTE_2': [-55, 5], 'OESTE_3': [-55, -25]
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
        """Encontra o portão mais próximo de uma posição"""
        gates_list = list(self.gates.values())
        distances = [np.linalg.norm(np.array(position) - np.array(gate)) for gate in gates_list]
        nearest_idx = np.argmin(distances)
        return list(self.gates.keys())[nearest_idx], list(self.gates.values())[nearest_idx]
    
    def get_nearest_bar(self, position):
        """Encontra o bar mais próximo de uma posição"""
        bars_list = list(self.bars.values())
        distances = [np.linalg.norm(np.array(position) - np.array(bar)) for bar in bars_list]
        nearest_idx = np.argmin(distances)
        return list(self.bars.keys())[nearest_idx], list(self.bars.values())[nearest_idx]
    
    def get_nearest_toilet(self, position):
        """Encontra a casa de banho mais próxima de uma posição"""
        toilets_list = list(self.toilets.values())
        distances = [np.linalg.norm(np.array(position) - np.array(toilet)) for toilet in toilets_list]
        nearest_idx = np.argmin(distances)
        return list(self.toilets.keys())[nearest_idx], list(self.toilets.values())[nearest_idx]
    
    def get_seat_near_gate(self, gate_name):
        """Atribui uma cadeira perto do portão especificado"""
        if gate_name == 'GATE_NORTH':
            area_keys = ['NORTE_1', 'NORTE_2', 'NORTE_3', 'NORTE_4', 'NORTE_5', 'NORTE_6']
        elif gate_name == 'GATE_SOUTH':
            area_keys = ['SUL_1', 'SUL_2', 'SUL_3', 'SUL_4', 'SUL_5', 'SUL_6']
        elif gate_name == 'GATE_EAST':
            area_keys = ['LESTE_1', 'LESTE_2', 'LESTE_3']
        else:  # GATE_WEST
            area_keys = ['OESTE_1', 'OESTE_2', 'OESTE_3']
        
        area_key = np.random.choice(area_keys)
        area_center = self.seating_areas[area_key]
        x = area_center[0] + np.random.uniform(-8, 8)
        y = area_center[1] + np.random.uniform(-5, 5)
        return [x, y]

def run_stadium_simulation():
    print("INICIANDO SIMULAÇÃO COMPLETA")

    mqtt_publisher = MQTTPublisher(MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_EVENTS)
    event_gen = EventGenerator(mqtt_publisher)
    boundaries = StadiumBoundaries()

    FPS = 5
    SIMULATION_DURATION = 300
    STEPS = SIMULATION_DURATION * FPS
    n_pedestrians = 150

    TIMELINE = {"pre_game": 60, "game_start": 120, "half_time": 180, "game_resume": 240, "game_end": 300}

    # POSIÇÕES INICIAIS DAS PESSOAS
    START_POSITIONS = [
        # Norte
        [0, 47.4], [-10.6, 45.5],
        # Sul
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
        print(f"Imagem não carregada: {e}")
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
    
    # Distribuição temporal - não vão todos ao mesmo tempo
    service_times = np.random.uniform(TIMELINE["half_time"] + 5, TIMELINE["game_resume"] - 10, n_pedestrians)
    
    assigned_seats = {}
    entry_gates = {}
    current_destinations = {}

    for i in range(n_pedestrians):
        start_pos = START_POSITIONS[i % len(START_POSITIONS)]
        positions[i] = start_pos
        
        # Encontra portão mais próximo da posição inicial
        nearest_gate_name, nearest_gate_pos = boundaries.get_nearest_gate(start_pos)
        entry_gates[i] = nearest_gate_name
        
        # Atribui cadeira perto do portão de entrada
        assigned_seats[i] = boundaries.get_seat_near_gate(nearest_gate_name)
        
        while not is_position_valid(assigned_seats[i][0], assigned_seats[i][1]):
            assigned_seats[i] = boundaries.get_seat_near_gate(nearest_gate_name)

        states[i] = 3
        destinations[i] = assigned_seats[i].copy()
        
        event_gen.generate_event("person_inside_stadium", i,
            {"x": float(positions[i][0]), "y": float(positions[i][1])},
            {"initial_position": True, "nearest_gate": nearest_gate_name})

    plt.ion()
    fig, ax = plt.subplots(figsize=(14, 11))

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
            
            # Desenha portões
            for gate_name, gate_pos in boundaries.gates.items():
                ax.plot(gate_pos[0], gate_pos[1], 'go', markersize=10, alpha=0.7)
                ax.text(gate_pos[0], gate_pos[1] + 3, gate_name, ha='center', va='bottom', 
                       color='green', fontweight='bold', fontsize=8)
            
            # Desenha bares
            for bar_name, bar_pos in boundaries.bars.items():
                ax.plot(bar_pos[0], bar_pos[1], 'ro', markersize=15, alpha=0.7)
                ax.text(bar_pos[0], bar_pos[1] + 3, bar_name, ha='center', va='bottom', 
                       color='red', fontweight='bold', fontsize=8)
            
            # Desenha casas de banho
            for toilet_name, toilet_pos in boundaries.toilets.items():
                ax.plot(toilet_pos[0], toilet_pos[1], 'bo', markersize=12, alpha=0.7)
                ax.text(toilet_pos[0], toilet_pos[1] + 3, toilet_name, ha='center', va='bottom', 
                       color='blue', fontweight='bold', fontsize=8)
        
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

        # LÓGICA DE MOVIMENTO
        for i in range(n_pedestrians):
            current_pos = positions[i]

            # Indo para a cadeira
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
                    event_gen.generate_event("person_sat_down", i,
                        {"x": float(positions[i][0]), "y": float(positions[i][1])}, 
                        {"seat_id": f"SEAT_{i:04d}", "gate": entry_gates[i]})

            # Sentado → pode ir a bar ou WC durante intervalo (tempo individual)
            if (states[i] == 4 and 
                TIMELINE["half_time"] <= current_time < TIMELINE["game_resume"] and
                current_time >= service_times[i]):
                
                # 50/50 entre bar e casa de banho
                if np.random.random() < 0.5:
                    # Vai para bar MAIS PRÓXIMO
                    states[i] = 5
                    bar_name, bar_pos = boundaries.get_nearest_bar(current_pos)
                    current_destinations[i] = bar_name
                    destinations[i] = bar_pos
                    
                    event_gen.generate_event("person_left_seat", i,
                        {"x": float(current_pos[0]), "y": float(current_pos[1])},
                        {"destination": bar_name, "type": "BAR", "nearest": True})
                else:
                    # Vai para casa de banho MAIS PRÓXIMA
                    states[i] = 8
                    toilet_name, toilet_pos = boundaries.get_nearest_toilet(current_pos)
                    current_destinations[i] = toilet_name
                    destinations[i] = toilet_pos
                    
                    event_gen.generate_event("person_left_seat", i,
                        {"x": float(current_pos[0]), "y": float(current_pos[1])},
                        {"destination": toilet_name, "type": "TOILET", "nearest": True})

            # Indo ao bar
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

            # Voltando do bar
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
                    event_gen.generate_event("person_returned_to_seat", i,
                        {"x": float(positions[i][0]), "y": float(positions[i][1])},
                        {"seat_id": f"SEAT_{i:04d}", "from": "BAR"})

            # Indo à casa de banho
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

            # Voltando da casa de banho
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
                    event_gen.generate_event("person_returned_to_seat", i,
                        {"x": float(positions[i][0]), "y": float(positions[i][1])},
                        {"seat_id": f"SEAT_{i:04d}", "from": "TOILET"})

        # VISUALIZAÇÃO
        colors = {
            3: 'cyan',     # Indo para o lugar
            4: 'lime',     # Sentado
            5: 'red',      # Indo ao bar
            6: 'magenta',  # No bar
            7: 'orange',   # Voltando do bar
            8: 'purple',   # Indo à casa de banho
            9: 'pink',     # Na casa de banho
            10: 'brown'    # Voltando da casa de banho
        }
        
        labels = {
            3: 'Indo lugar', 4: 'Sentado', 5: 'Indo bar', 6: 'No bar', 7: 'Voltando bar',
            8: 'Indo WC', 9: 'No WC', 10: 'Voltando WC'
        }
        
        # Desenha posições iniciais
        start_array = np.array(START_POSITIONS)
        ax.scatter(start_array[:, 0], start_array[:, 1], 
                  c='yellow', s=30, alpha=0.5, marker='x', label='Posições Iniciais')
        
        # Desenha cadeiras
        seat_positions = np.array(list(assigned_seats.values()))
        ax.scatter(seat_positions[:, 0], seat_positions[:, 1], 
                  c='blue', s=15, alpha=0.3, marker='s', label='Cadeiras')
        
        # Desenha pessoas
        for state, color in colors.items():
            indices = states == state
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

    print(f"SIMULAÇÃO CONCLUÍDA! {event_gen.event_count} eventos gerados.")

if __name__ == "__main__":
    run_stadium_simulation()