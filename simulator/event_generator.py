"""
Gerador completo de eventos para o estádio.
"""
import json
import uuid
import numpy as np
from datetime import datetime
from collections import defaultdict

# Tópicos MQTT
from mqtt_broker import MQTT_TOPIC_ALL_EVENTS, MQTT_TOPIC_QUEUES, MQTT_TOPIC_MAINTENANCE, MQTT_TOPIC_HEATMAP

class EventGenerator:
    """Gerador completo de eventos"""
    def __init__(self, mqtt_client):
        self.mqtt_client = mqtt_client
        self.events = []
        self.event_count = 0
        
        # Contadores
        self.gate_counters = defaultdict(int)
        self.zone_counters = defaultdict(int)
        self.queue_counters = defaultdict(lambda: {"count": 0, "arrivals": [], "departures": []})
        self.bin_fill_levels = {}
        
        # Timers
        self.last_heatmap_update = 0
        self.last_queue_update = 0
        self.last_bin_update = 0
        
        print("Gerador de eventos inicializado")
    
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
        self.mqtt_client.publish(MQTT_TOPIC_ALL_EVENTS, json.dumps(event))
        self.event_count += 1
        return event
    
    def generate_gate_event(self, gate_name, person_id, direction="entry"):
        """Evento de passagem por portão"""
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
        self.mqtt_client.publish(MQTT_TOPIC_ALL_EVENTS, json.dumps(event))
        self.event_count += 1
        return event
    
    def generate_bin_event(self, bin_id, location, fill_percentage=None):
        """Evento de enchimento de caixote do lixo"""
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
                           else "low"
            }
        }
        self.events.append(event)
        self.mqtt_client.publish(MQTT_TOPIC_ALL_EVENTS, json.dumps(event))
        self.mqtt_client.publish(MQTT_TOPIC_MAINTENANCE, json.dumps(event))
        self.event_count += 1
        return event
    
    def generate_bin_overflow_alert(self, bin_id, location):
        """Alerta CRÍTICO de caixote a transbordar"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "bin_overflow_alert",
            "timestamp": datetime.now().isoformat() + "Z",
            "bin_id": bin_id,
            "location": {"x": float(location[0]), "y": float(location[1])},
            "priority": "high",
            "assigned_role": "cleaning",
            "metadata": {
                "action_required": "empty_bin"
            }
        }
        self.events.append(event)
        self.mqtt_client.publish(MQTT_TOPIC_ALL_EVENTS, json.dumps(event))
        self.mqtt_client.publish(MQTT_TOPIC_MAINTENANCE, json.dumps(event))
        self.event_count += 1
        return event
    
    def generate_queue_event(self, location_type, location_id, location, queue_length, capacity, avg_service_time=None):
        """Evento de fila de espera (QUEUE SERVICE)"""
        # Tempos de serviço em segundos, convertidos para minutos para cálculo
        if location_type == "BAR":
            avg_service_time_sec = 30  # 30 segundos médios no bar
        else:  # TOILET
            avg_service_time_sec = 15  # 15 segundos médios no WC
        
        # Converter para minutos
        avg_service_time_min = avg_service_time_sec / 60.0
        
        # Tempo de espera em MINUTOS
        # Fórmula: (pessoas na fila * tempo_serviço_medio) / capacidade_atendimento
        service_capacity = 2 if location_type == "BAR" else 3  # Pessoas atendidas por minuto
        wait_time_min = (queue_length * avg_service_time_min) / service_capacity
        
        occupancy_rate = (queue_length / capacity * 100) if capacity > 0 else 0
        
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "queue_update",
            "timestamp": datetime.now().isoformat() + "Z",
            "location_type": location_type,
            "location_id": location_id,
            "location": {"x": float(location[0]), "y": float(location[1])},
            "queue_length": queue_length,
            "capacity": capacity,
            "occupancy_rate": round(occupancy_rate, 1),
            "estimated_wait_min": round(wait_time_min, 1),
            "metadata": {
                "status": "critico" if wait_time_min > 3 
                        else "alto" if wait_time_min > 1.5 
                        else "medio" if wait_time_min > 0.5
                        else "normal",
                "queue_status": "cheio" if occupancy_rate > 90 
                            else "alto" if occupancy_rate > 70 
                            else "medio" if occupancy_rate > 50 
                            else "baixo",
                "avg_service_time_sec": avg_service_time_sec,
                "service_capacity_per_min": service_capacity
            }
        }
        
        print(f"Evento FILA enviado: {location_id} - {queue_length} pessoas, {wait_time_min:.1f} min espera")
        
        self.events.append(event)
        self.mqtt_client.publish(MQTT_TOPIC_ALL_EVENTS, json.dumps(event))
        self.mqtt_client.publish(MQTT_TOPIC_QUEUES, json.dumps(event))
        
        self.event_count += 1
        return event
    
    def generate_heatmap_density(self, grid_data):
        """Gera evento de heatmap com dados de densidade por coordenada"""
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "crowd_density",
            "timestamp": datetime.now().isoformat() + "Z",
            "grid_data": grid_data,
            "total_people": sum(cell["count"] for cell in grid_data),
            "metadata": {
                "grid_resolution": 5,
                "update_interval": 10
            }
        }
        
        self.events.append(event)
        self.mqtt_client.publish(MQTT_TOPIC_ALL_EVENTS, json.dumps(event))
        self.mqtt_client.publish(MQTT_TOPIC_HEATMAP, json.dumps(event))
        self.event_count += 1
        return event
    
    def update_zone_occupancy(self, zone_id, delta):
        """Atualiza contador de ocupação de zona"""
        self.zone_counters[zone_id] += delta
        self.zone_counters[zone_id] = max(0, self.zone_counters[zone_id])