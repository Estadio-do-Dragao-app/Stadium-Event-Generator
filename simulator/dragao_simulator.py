# simulator/event_generator_system.py
import numpy as np
import matplotlib.pyplot as plt
import os
import json
import time
import uuid
from datetime import datetime, timedelta
import threading
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("⚠️ MQTT não disponível. Instale paho-mqtt para envio de eventos em tempo real.")

print("=== STADIUM EVENT GENERATOR SYSTEM ===")
print("📡 Conforme especificado pelo Prof. Daniel Corujo")

# Configurações MQTT (ajustar conforme necessário)
MQTT_BROKER = "localhost"  # ou IP do broker do outro grupo
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
            self.client = mqtt.Client()
            self.client.on_connect = self._on_connect
            try:
                self.client.connect(self.broker, self.port, 60)
                self.client.loop_start()
                time.sleep(1)  # Espera pela conexão
            except Exception as e:
                print(f"❌ Não foi possível conectar ao broker MQTT: {e}")
        else:
            print("📝 Modo offline: eventos serão apenas guardados em arquivo")
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print("✅ Conectado ao broker MQTT")
        else:
            print(f"❌ Falha de conexão MQTT. Código: {rc}")
    
    def publish_event(self, event):
        if self.connected and self.client:
            self.client.publish(self.topic, json.dumps(event))
            print(f"📡 MQTT: {event['event_type']} → {event['person_id']}")
        else:
            print(f"📝 LOCAL: {event['event_type']} → {event['person_id']}")

class EventGenerator:
    def __init__(self, mqtt_publisher):
        self.mqtt_publisher = mqtt_publisher
        self.events = []
        self.event_count = 0
    
    def generate_event(self, event_type, person_id, location, metadata=None):
        """Gera evento no formato JSON especificado pelo professor"""
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

def run_stadium_simulation():
    print("\n🎯 INICIANDO SIMULAÇÃO REALISTA DE JOGO")
    print("⏰ Timeline: Entrada → Jogo → Intervalo → Jogo → Saída")
    
    # Inicializa MQTT Publisher
    mqtt_publisher = MQTTPublisher(MQTT_BROKER, MQTT_PORT, MQTT_TOPIC_EVENTS)
    event_gen = EventGenerator(mqtt_publisher)
    
    # Configuração REALISTA (2 horas de jogo aceleradas)
    FPS = 5  # Frames por segundo (simulação)
    SIMULATION_DURATION = 300  # 5 minutos reais = ~2 horas de jogo
    STEPS = SIMULATION_DURATION * FPS
    
    n_pedestrians = 200  # Adeptos
    
    # Timeline do jogo (em segundos da simulação)
    TIMELINE = {
        "pre_game": 60,     # 0-60s: Entrada no estádio
        "game_start": 120,  # 120s: Jogo começa
        "half_time": 180,   # 180s: Intervalo
        "game_resume": 240, # 240s: Segunda parte
        "game_end": 300     # 300s: Fim do jogo
    }
    
    # Estrutura do estádio
    SECTORS = {
        "NORTE": {"bounds": [-55, 32, 55, 40], "capacity": 50},
        "SUL": {"bounds": [-55, -40, 55, -32], "capacity": 50},
        "LESTE": {"bounds": [52, -30, 60, 30], "capacity": 30},
        "OESTE": {"bounds": [-60, -30, -52, 30], "capacity": 30},
        "CENTRAL": {"bounds": [-15, -15, 15, 15], "capacity": 40}
    }
    
    BARS = {
        "BAR_NORTE": {"pos": [0, 45], "capacity": 20},
        "BAR_SUL": {"pos": [0, -45], "capacity": 20},
        "BAR_LESTE": {"pos": [65, 0], "capacity": 15},
        "BAR_OESTE": {"pos": [-65, 0], "capacity": 15}
    }
    
    # Estado inicial dos adeptos
    positions = np.zeros((n_pedestrians, 2))
    states = np.zeros(n_pedestrians, dtype=int)  # 0: fora, 1: entrada, 2: no lugar, 3: no bar, 4: saída
    destinations = np.zeros((n_pedestrians, 2))
    arrival_times = np.random.uniform(0, TIMELINE["pre_game"], n_pedestrians)
    sectors = np.random.choice(list(SECTORS.keys()), n_pedestrians)
    seats = {}
    
    # Inicializa posições e destinos
    for i in range(n_pedestrians):
        # Começam fora do estádio
        gate = np.random.choice(["PORTÃO_NORTE", "PORTÃO_SUL", "PORTÃO_LESTE", "PORTÃO_OESTE"])
        if gate == "PORTÃO_NORTE":
            positions[i] = [np.random.uniform(-30, 30), 50]
        elif gate == "PORTÃO_SUL":
            positions[i] = [np.random.uniform(-30, 30), -50]
        elif gate == "PORTÃO_LESTE":
            positions[i] = [65, np.random.uniform(-20, 20)]
        else:  # OESTE
            positions[i] = [-65, np.random.uniform(-20, 20)]
        
        # Atribui lugar no setor
        sector_bounds = SECTORS[sectors[i]]["bounds"]
        seats[i] = [
            np.random.uniform(sector_bounds[0], sector_bounds[2]),
            np.random.uniform(sector_bounds[1], sector_bounds[3])
        ]
        destinations[i] = positions[i]  # Inicialmente parado
    
    # Setup do plot
    plt.ion()
    fig, ax = plt.subplots(figsize=(12, 8))
    
    print(f"🎲 Simulando {n_pedestrians} adeptos por {SIMULATION_DURATION}s")
    print("⏳ A iniciar timeline realista...")
    
    for step in range(STEPS):
        current_time = step / FPS
        ax.clear()
        
        # Determina fase do jogo
        if current_time < TIMELINE["pre_game"]:
            phase = "PRÉ-JOGO - ENTRADA"
            ax.set_facecolor("#FFE4B5")  # Laranje claro
        elif current_time < TIMELINE["game_start"]:
            phase = "ANTES DO JOGO"
            ax.set_facecolor("#98FB98")  # Verde claro
        elif current_time < TIMELINE["half_time"]:
            phase = "PRIMEIRA PARTE"
            ax.set_facecolor("#87CEEB")  # Azul céu
        elif current_time < TIMELINE["game_resume"]:
            phase = "INTERVALO"
            ax.set_facecolor("#FFB6C1")  # Rosa
        elif current_time < TIMELINE["game_end"]:
            phase = "SEGUNDA PARTE" 
            ax.set_facecolor("#87CEEB")
        else:
            phase = "JOGO TERMINADO - SAÍDA"
            ax.set_facecolor("#D3D3D3")  # Cinza
        
        ax.set_xlim(-70, 70)
        ax.set_ylim(-55, 55)
        ax.set_title(f"🏟️ Estádio do Dragão - {phase}\nTempo: {current_time:.1f}s | Eventos: {event_gen.event_count}", 
                    fontsize=14, pad=20)
        
        # Desenha estádio
        stadium = plt.Rectangle((-62, -42), 124, 84, fill=False, edgecolor='black', linewidth=3)
        ax.add_patch(stadium)
        
        # Desenha setores
        colors = {'NORTE': 'red', 'SUL': 'blue', 'LESTE': 'green', 'OESTE': 'orange', 'CENTRAL': 'purple'}
        for sector, info in SECTORS.items():
            bounds = info["bounds"]
            rect = plt.Rectangle((bounds[0], bounds[1]), bounds[2]-bounds[0], bounds[3]-bounds[1],
                                fill=False, edgecolor=colors[sector], linewidth=2, linestyle='--')
            ax.add_patch(rect)
            ax.text((bounds[0]+bounds[2])/2, (bounds[1]+bounds[3])/2, sector, 
                   ha='center', va='center', fontsize=8, color=colors[sector])
        
        # Desenha bares
        for bar_name, bar_info in BARS.items():
            ax.plot(bar_info["pos"][0], bar_info["pos"][1], 'ks', markersize=10)
            ax.text(bar_info["pos"][0], bar_info["pos"][1]+3, bar_name, 
                   ha='center', va='bottom', fontsize=8)
        
        # Lógica de simulação por fase
        for i in range(n_pedestrians):
            # FASE 1: ENTRADA NO ESTÁDIO
            if current_time < TIMELINE["pre_game"] and states[i] == 0:
                if current_time >= arrival_times[i]:
                    states[i] = 1  # A entrar
                    destinations[i] = seats[i]  # Dirige-se ao lugar
                    
                    # EVENTO: Pessoa entrou no estádio
                    event_gen.generate_event(
                        "person_entered_stadium",
                        i,
                        {"x": float(positions[i, 0]), "y": float(positions[i, 1]), "sector": "ENTRADA"},
                        {"gate": "GATE_1", "arrival_time": float(current_time)}
                    )
            
            # FASE 2: CHEGADA AO LUGAR
            if states[i] == 1:  # A caminho do lugar
                direction = destinations[i] - positions[i]
                distance = np.linalg.norm(direction)
                
                if distance > 2.0:
                    # Move-se para o destino
                    move_vector = (direction / distance) * 0.8
                    positions[i] += move_vector
                    
                    # EVENTO ocasional: Pessoa a mover-se
                    if step % 20 == 0:
                        event_gen.generate_event(
                            "person_moving",
                            i,
                            {"x": float(positions[i, 0]), "y": float(positions[i, 1]), "sector": sectors[i]},
                            {"destination": "SEAT", "speed": float(np.linalg.norm(move_vector))}
                        )
                else:
                    # Chegou ao lugar
                    states[i] = 2
                    positions[i] = destinations[i]  # Ajusta posição exata
                    
                    # EVENTO: Pessoa sentou-se
                    event_gen.generate_event(
                        "person_sat_down", 
                        i,
                        {"x": float(positions[i, 0]), "y": float(positions[i, 1]), "sector": sectors[i]},
                        {"seat_number": f"{sectors[i]}_{i%100}", "arrival_time": float(current_time)}
                    )
            
            # FASE 3: COMPORTAMENTO DURANTE O JOGO
            if states[i] == 2 and current_time > TIMELINE["game_start"]:
                # Decisão de ir ao bar (aleatório, mais frequente no intervalo)
                go_to_bar_prob = 0.002  # Baixa probabilidade durante o jogo
                if TIMELINE["half_time"] <= current_time < TIMELINE["game_resume"]:
                    go_to_bar_prob = 0.1  # Alta probabilidade no intervalo
                
                if np.random.random() < go_to_bar_prob:
                    states[i] = 3  # Indo ao bar
                    bar_name = np.random.choice(list(BARS.keys()))
                    destinations[i] = BARS[bar_name]["pos"]
                    
                    # EVENTO: Pessoa saiu do lugar
                    event_gen.generate_event(
                        "person_left_seat",
                        i,
                        {"x": float(positions[i, 0]), "y": float(positions[i, 1]), "sector": sectors[i]},
                        {"destination": bar_name, "reason": "REFRESHMENT"}
                    )
            
            # FASE 4: NO BAR/VOLTANDO
            if states[i] == 3:  # No bar ou a caminho
                direction = destinations[i] - positions[i]
                distance = np.linalg.norm(direction)
                
                if distance > 2.0:
                    # A caminho do bar
                    move_vector = (direction / distance) * 0.6
                    positions[i] += move_vector
                else:
                    # Chegou ao bar - fica um tempo
                    if states[i] == 3:  # Primeira vez no bar
                        states[i] = 4  # Marcado como "no bar"
                        bar_time = np.random.uniform(5, 15)  # Tempo no bar
                        
                        # EVENTO: Pessoa no bar
                        event_gen.generate_event(
                            "person_at_bar",
                            i,
                            {"x": float(positions[i, 0]), "y": float(positions[i, 1]), "sector": "BAR"},
                            {"bar_name": bar_name, "estimated_stay": bar_time}
                        )
                        
                        # Agenda volta ao lugar
                        def return_to_seat(person_idx, delay):
                            time.sleep(delay)
                            if person_idx < len(states):
                                states[person_idx] = 5  # Voltando
                                destinations[person_idx] = seats[person_idx]
                        
                        # Cria thread para simular tempo no bar
                        threading.Thread(target=return_to_seat, args=(i, bar_time/FPS), daemon=True).start()
            
            # FASE 5: VOLTANDO AO LUGAR
            if states[i] == 5:  # Voltando do bar
                direction = destinations[i] - positions[i]
                distance = np.linalg.norm(direction)
                
                if distance > 2.0:
                    move_vector = (direction / distance) * 0.6
                    positions[i] += move_vector
                else:
                    # Voltou ao lugar
                    states[i] = 2
                    
                    # EVENTO: Pessoa voltou ao lugar
                    event_gen.generate_event(
                        "person_returned_to_seat",
                        i,
                        {"x": float(positions[i, 0]), "y": float(positions[i, 1]), "sector": sectors[i]},
                        {"time_away": np.random.uniform(30, 120)}
                    )
        
        # Desenha pessoas com cores por estado
        state_colors = {0: 'gray', 1: 'orange', 2: 'green', 3: 'red', 4: 'red', 5: 'purple'}
        state_labels = {0: 'Fora', 1: 'Entrando', 2: 'No lugar', 3: 'Indo ao bar', 4: 'No bar', 5: 'Voltando'}
        
        for state in range(6):
            idx = np.where(states == state)[0]
            if len(idx) > 0:
                ax.scatter(positions[idx, 0], positions[idx, 1], 
                          c=state_colors[state], s=20, alpha=0.7, label=state_labels[state])
        
        ax.legend(loc='upper right')
        ax.set_aspect('equal')
        plt.draw()
        plt.pause(0.01)
    
    # FASE FINAL: EVENTOS DE SAÍDA
    print("\n🎉 Gerando eventos de saída pós-jogo...")
    for i in range(n_pedestrians):
        if states[i] in [2, 3, 4, 5]:  # Se ainda está no estádio
            event_gen.generate_event(
                "person_exited_stadium",
                i,
                {"x": float(positions[i, 0]), "y": float(positions[i, 1]), "sector": "SAÍDA"},
                {"exit_time": float(current_time), "total_stay": float(current_time - arrival_times[i])}
            )
    
    plt.ioff()
    plt.show()
    
    # Guarda todos os eventos em JSON
    os.makedirs("../outputs", exist_ok=True)
    output_file = "../outputs/stadium_events_complete.json"
    with open(output_file, "w", encoding='utf-8') as f:
        json.dump(event_gen.events, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ SIMULAÇÃO CONCLUÍDA!")
    print(f"📊 Total de eventos gerados: {event_gen.event_count}")
    print(f"💾 Eventos guardados em: {output_file}")
    print(f"📡 Eventos publicados via MQTT: {MQTT_AVAILABLE and mqtt_publisher.connected}")
    
    # Estatísticas
    event_types = {}
    for event in event_gen.events:
        event_type = event['event_type']
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    print("\n📈 Estatísticas de Eventos:")
    for event_type, count in event_types.items():
        print(f"   {event_type}: {count}")
    
    # Para MQTT
    if MQTT_AVAILABLE and mqtt_publisher.client:
        mqtt_publisher.client.loop_stop()
    
    return event_gen.events

if __name__ == "__main__":
    events = run_stadium_simulation()