"""
Simulador principal do Estádio do Dragão.
"""
from matplotlib.image import imread
import numpy as np
import matplotlib.pyplot as plt
import os
import json
import time
import threading
from datetime import datetime
from collections import defaultdict

from mqtt_broker import StadiumMQTTClient
from stadium_boundaries import StadiumBoundaries
from event_generator import EventGenerator

print("\n" + "="*60)
print("ESTADIO DO DRAGAO - SIMULADOR COMPLETO")
print("="*60)

class StadiumSimulation:
    """Simulação completa do estádio"""
    def __init__(self, num_people=300, duration=1800):
        self.output_dir = "../outputs"
        self.num_people = num_people
        self.duration = duration
        self.fps = 1

        self.total_people = num_people
        self.simulation_duration = duration
        
        self.output_dir = "../outputs"
        
        self.event_log = []
        self.queue_data_log = []
        self.phase_changes = []
        self.seated_count = 0
        self.at_bars_count = 0
        self.at_wc_count = 0
        self.queue_bars_count = 0
        self.queue_wc_count = 0
        self.exited_count = 0
        self.fire_alert_triggered = False
        
        print("Tentando conectar ao Mosquitto MQTT Broker...")
        
        # Tentar conectar com retry
        max_retries = 3
        connected = False
        
        for attempt in range(max_retries):
            try:
                self.mqtt_client = StadiumMQTTClient("stadium_simulator")
                result = self.mqtt_client.connect()
                if result == 0:
                    print(f"✓ Conectado ao Mosquitto (tentativa {attempt + 1}/{max_retries})")
                    connected = True
                    break
                else:
                    print(f"✗ Falha na conexão (tentativa {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        print("Tentando novamente em 2 segundos...")
                        time.sleep(2)
            except Exception as e:
                print(f"Erro: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
        
        if not connected:
            print("\n⚠ Não foi possível conectar ao Mosquitto")
            print("Verifique se o serviço está rodando:")
            print("  net start mosquitto")
            print("\nContinuando com modo offline...")
            class DummyClient:
                def publish(self, *args, **kwargs):
                    return 0
                def subscribe(self, *args, **kwargs):
                    return (0, [0])
                def on_message(self, *args, **kwargs):
                    pass
                def disconnect(self, *args, **kwargs):
                    pass
                def get_stats(self):
                    return {'messages_count': 0}
            self.mqtt_client = DummyClient()
        
        # Criar gerador de eventos
        self.event_gen = EventGenerator(self.mqtt_client)
        
        # Criar boundaries
        self.boundaries = StadiumBoundaries()
        
        # Estado da simulação
        self.positions = None
        self.states = None
        self.destinations = None
        
        # Variáveis de controle
        self.service_times_bar = None
        self.time_in_facility = None
        self.queue_positions = None
        self.current_queues = defaultdict(list)
        self.facility_occupancy = defaultdict(int)
        self.assigned_seats = {}
        self.assigned_zones = {}
        self.entry_gates = {}
        self.current_destinations = {}
        self.queue_wait_times = None
        self.queue_start_times = None
        self.in_queue = None
        
        # Timeline
        self.timeline = {
            "pre_game": 100, 
            "game_start": 200, 
            "half_time": 800, 
            "game_resume": 1000, 
            "game_end": 1600,
            "evacuation_complete": 1800
        }
        
        # Carregar imagem
        self.stadium_img = None
        self.img_extent = [-70, 70, -55, 55]
        self.use_image = False
        self._load_stadium_image()
        
        print(f"Simulacao configurada com {num_people} pessoas, duracao: {duration}s")
    
    def _load_stadium_image(self):
        """Carrega imagem do estádio"""
        try:
            self.stadium_img = imread("map_stadium.png")
            
            # Processar imagem para walkable areas
            gray = np.dot(self.stadium_img[...,:3], [0.299, 0.587, 0.114])
            self.walkable_mask = gray > 0.55
            
            # Suavizar máscara
            for _ in range(4):
                self.walkable_mask = np.logical_and.reduce([
                    self.walkable_mask,
                    np.roll(self.walkable_mask, 1, axis=0),
                    np.roll(self.walkable_mask, -1, axis=0),
                    np.roll(self.walkable_mask, 1, axis=1),
                    np.roll(self.walkable_mask, -1, axis=1)
                ])
            
            self.use_image = True
            print("Imagem do estadio carregada com sucesso")
            
        except Exception as e:
            print(f"Imagem nao carregada: {e}")
            self.use_image = False
    
    def is_position_valid(self, x, y):
        """Verifica se posição é válida"""
        if self.use_image:
            # Converter coordenadas para pixels
            ix = int((x - self.img_extent[0]) / (self.img_extent[1] - self.img_extent[0]) * self.stadium_img.shape[1])
            iy = int((y - self.img_extent[2]) / (self.img_extent[3] - self.img_extent[2]) * self.stadium_img.shape[0])
            iy = self.stadium_img.shape[0] - 1 - iy
            
            if not (0 <= ix < self.stadium_img.shape[1] and 0 <= iy < self.stadium_img.shape[0]):
                return False
            return self.walkable_mask[iy, ix]
        else:
            return self.boundaries.is_position_allowed(x, y)
    
    def setup_people(self):
        """Configura as pessoas iniciais"""
        print(f"Configurando {self.num_people} pessoas...")
        
        # Inicializar arrays
        self.positions = np.zeros((self.num_people, 2))
        self.states = np.zeros(self.num_people, dtype=int)
        self.destinations = np.zeros((self.num_people, 2))
        self.service_times_bar = np.random.uniform(
            self.timeline["half_time"] + 5, 
            self.timeline["game_resume"] - 10, 
            self.num_people
        )
        self.time_in_facility = np.zeros(self.num_people)
        self.queue_positions = np.zeros(self.num_people, dtype=int)
        self.queue_wait_times = np.zeros(self.num_people)
        self.queue_start_times = np.zeros(self.num_people)
        self.in_queue = np.zeros(self.num_people, dtype=bool)
        
        START_POSITIONS = [
            [-4.8, 45.2],[0.2, -48.3]
        ]
        
        for i in range(self.num_people):
            start_pos = START_POSITIONS[i % len(START_POSITIONS)]
            self.positions[i] = start_pos
            
            # Portão mais próximo
            nearest_gate_name, _ = self.boundaries.get_nearest_gate(start_pos)
            self.entry_gates[i] = nearest_gate_name
            
            # Assento atribuído
            zone_name, seat_pos = self.boundaries.get_seat_near_gate(nearest_gate_name)
            self.assigned_seats[i] = seat_pos
            self.assigned_zones[i] = zone_name
            
            # Verificar se posição é válida
            while not self.is_position_valid(seat_pos[0], seat_pos[1]):
                zone_name, seat_pos = self.boundaries.get_seat_near_gate(nearest_gate_name)
                self.assigned_seats[i] = seat_pos
                self.assigned_zones[i] = zone_name
            
            # Estado inicial
            self.states[i] = 3  # Indo ao lugar
            self.destinations[i] = seat_pos.copy()
            
            # Gerar evento
            self.event_gen.generate_gate_event(nearest_gate_name, i, direction="entry")
        
        # Inicializar bins
        for bin_id in self.boundaries.bins.keys():
            self.event_gen.bin_fill_levels[bin_id] = np.random.uniform(10, 30)
        
        print("Pessoas configuradas")
    
    def update_queues(self, current_time):
        """Atualiza eventos de filas"""
        # Filas nos bares
        for bar_name, bar_info in self.boundaries.bars.items():
            queue_length = len(self.current_queues.get(bar_name, []))
            capacity = bar_info['queue_spots']
            center = bar_info['center']
            
            self.event_gen.generate_queue_event(
                "BAR", bar_name, center, queue_length, capacity, avg_service_time=3.5
            )
        
        # Filas nas casas de banho
        for toilet_name, toilet_info in self.boundaries.toilets.items():
            queue_length = len(self.current_queues.get(toilet_name, []))
            capacity = toilet_info['queue_spots']
            center = toilet_info['center']
            
            self.event_gen.generate_queue_event(
                "TOILET", toilet_name, center, queue_length, capacity, avg_service_time=2.0
            )
    
    def update_bins(self, current_time):
        """Atualiza caixotes"""
        for bin_id, bin_pos in self.boundaries.bins.items():
            current = self.event_gen.bin_fill_levels.get(bin_id, 0)
            
            if self.timeline["half_time"] <= current_time < self.timeline["game_resume"]:
                increment = np.random.uniform(8, 15)
            else:
                increment = np.random.uniform(2, 5)
            
            fill_percentage = min(100, current + increment)
            
            self.event_gen.generate_bin_event(bin_id, bin_pos, fill_percentage)
            
            if fill_percentage > 95:
                self.event_gen.generate_bin_overflow_alert(bin_id, bin_pos)
            
            self.event_gen.bin_fill_levels[bin_id] = fill_percentage

    def _process_exit_movement(self, i):
        """Processa o movimento de saída"""
        direction = self.destinations[i] - self.positions[i]
        distance = np.linalg.norm(direction)
        
        if distance > 2.0:  # Ainda não chegou ao portão
            step_vector = (direction / distance) * 0.5  # Velocidade normal
            new_pos = self.positions[i] + step_vector
            
            if self.is_position_valid(new_pos[0], new_pos[1]):
                self.positions[i] = new_pos
            else:
                # Tentar caminho alternativo
                angle = np.random.uniform(-0.3, 0.3)
                rotation = np.array([[np.cos(angle), -np.sin(angle)], 
                                   [np.sin(angle), np.cos(angle)]])
                self.positions[i] = self.positions[i] + rotation @ step_vector * 0.8
        else:
            # Chegou ao portão - sair completamente
            self.states[i] = 14  # Estado: saiu
            gate_name = self.current_destinations[i]
            
            # Gerar evento de passagem pelo portão (saída)
            self.event_gen.generate_gate_event(gate_name, i, direction="exit")
            
            # Atualizar contador
            self.exited_count += 1
    
    def update_people(self, current_time):
        """Atualiza todas as pessoas"""
        for i in range(self.num_people):
            current_pos = self.positions[i]
            
            # Estado 3: Indo para o lugar
            if self.states[i] == 3:
                direction = self.destinations[i] - current_pos
                distance = np.linalg.norm(direction)
                
                if distance > 1.0:
                    step_vector = (direction / distance) * 0.4
                    new_pos = current_pos + step_vector
                    
                    if self.is_position_valid(new_pos[0], new_pos[1]):
                        self.positions[i] = new_pos
                    else:
                        angle = np.random.uniform(-0.5, 0.5)
                        rotation = np.array([[np.cos(angle), -np.sin(angle)], 
                                           [np.sin(angle), np.cos(angle)]])
                        self.positions[i] = current_pos + rotation @ step_vector * 0.8
                else:
                    self.states[i] = 4  # Sentado
                    self.event_gen.update_zone_occupancy(self.assigned_zones[i], +1)
            
            # Estado 4: Sentado - pode ir a serviços
            elif self.states[i] == 4:
                time_since_last = current_time - self.queue_start_times[i] if self.queue_start_times[i] > 0 else 1000
                
                # No intervalo
                if self.timeline["half_time"] <= current_time < self.timeline["game_resume"]:
                    # Ir ao bar
                    if current_time >= self.service_times_bar[i] and np.random.random() < 0.05:
                        self._go_to_bar(i)
                    # Ir à casa de banho
                    elif np.random.random() < 0.03:
                        self._go_to_toilet(i)
                # Durante o jogo
                elif time_since_last > 180 and np.random.random() < 0.02:
                    self._go_to_toilet(i)
                elif time_since_last > 300 and np.random.random() < 0.01:
                    self._go_to_bar(i)
            # Estados de movimento
            elif self.states[i] == 5:  # Indo ao bar
                self._move_to_service(i, 0.4)
            elif self.states[i] == 9:  # Indo à casa de banho
                self._move_to_service(i, 0.4)
            
            # Estados em fila
            elif self.states[i] == 6:  # Fila do bar
                self._manage_bar_queue(i)
            elif self.states[i] == 10:  # Fila da casa de banho
                self._manage_toilet_queue(i)
            
            # Estados em serviço
            elif self.states[i] == 7:  # No bar
                self._manage_bar_service(i)
            elif self.states[i] == 11:  # Na casa de banho
                self._manage_toilet_service(i)
            
            # Estados de retorno
            elif self.states[i] == 8:  # Voltando do bar
                self._return_to_seat(i)
            elif self.states[i] == 12:  # Voltando da casa de banho
                self._return_to_seat(i)
            elif self.states[i] == 13:
                self._process_exit_movement(i) # Saindo do estádio
    
    def _go_to_bar(self, i):
        """Pessoa decide ir ao bar"""
        bar_name, bar_info = self.boundaries.get_nearest_bar(self.positions[i])
        self.event_gen.update_zone_occupancy(self.assigned_zones[i], -1)
        self.states[i] = 5
        self.current_destinations[i] = bar_name
        self.destinations[i] = bar_info['center']
        self.queue_start_times[i] = time.time()
    
    def _go_to_toilet(self, i):
        """Pessoa decide ir à casa de banho"""
        toilet_name, toilet_info = self.boundaries.get_nearest_toilet(self.positions[i])
        self.event_gen.update_zone_occupancy(self.assigned_zones[i], -1)
        self.states[i] = 9
        self.current_destinations[i] = toilet_name
        self.destinations[i] = toilet_info['center']
        self.queue_start_times[i] = time.time()
    
    def _move_to_service(self, i, speed):
        """Move pessoa para serviço"""
        direction = self.destinations[i] - self.positions[i]
        distance = np.linalg.norm(direction)
        
        if distance > 2.0:
            step_vector = (direction / distance) * speed
            new_pos = self.positions[i] + step_vector
            
            if self.is_position_valid(new_pos[0], new_pos[1]):
                self.positions[i] = new_pos
            else:
                angle = np.random.uniform(-0.5, 0.5)
                rotation = np.array([[np.cos(angle), -np.sin(angle)], 
                                   [np.sin(angle), np.cos(angle)]])
                self.positions[i] = self.positions[i] + rotation @ step_vector * speed
        else:
            # Chegou ao serviço
            if self.states[i] == 5:
                self._arrive_at_bar(i)
            else:
                self._arrive_at_toilet(i)
    
    def _arrive_at_bar(self, i):
        """Pessoa chega ao bar"""
        bar_name = self.current_destinations[i]
        bar_info = self.boundaries.bars[bar_name]
        
        if self.facility_occupancy.get(bar_name, 0) < bar_info['capacity']:
            # Entra no bar
            self.states[i] = 7
            self.facility_occupancy[bar_name] += 1
            self.time_in_facility[i] = np.random.uniform(bar_info['service_time_min'], 
                                                       bar_info['service_time_max']) * self.fps
        else:
            # Entra na fila
            self.states[i] = 6
            self.in_queue[i] = True
            if bar_name not in self.current_queues:
                self.current_queues[bar_name] = []
            self.current_queues[bar_name].append(i)
            self.queue_positions[i] = len(self.current_queues[bar_name]) - 1
    
    def _arrive_at_toilet(self, i):
        """Pessoa chega à casa de banho"""
        toilet_name = self.current_destinations[i]
        toilet_info = self.boundaries.toilets[toilet_name]
        
        if self.facility_occupancy.get(toilet_name, 0) < toilet_info['capacity']:
            # Entra na casa de banho
            self.states[i] = 11
            self.facility_occupancy[toilet_name] += 1
            self.time_in_facility[i] = np.random.uniform(toilet_info['service_time_min'], 
                                                       toilet_info['service_time_max']) * self.fps
        else:
            # Entra na fila
            self.states[i] = 10
            self.in_queue[i] = True
            if toilet_name not in self.current_queues:
                self.current_queues[toilet_name] = []
            self.current_queues[toilet_name].append(i)
            self.queue_positions[i] = len(self.current_queues[toilet_name]) - 1
    
    def _manage_bar_queue(self, i):
        """Gerencia pessoa na fila do bar"""
        bar_name = self.current_destinations[i]
        queue = self.current_queues.get(bar_name, [])
        
        if queue and queue[0] == i:
            if self.facility_occupancy.get(bar_name, 0) < self.boundaries.bars[bar_name]['capacity']:
                # Sai da fila e entra no bar
                self.in_queue[i] = False
                self.states[i] = 7
                self.facility_occupancy[bar_name] += 1
                self.current_queues[bar_name].pop(0)
                self.time_in_facility[i] = np.random.uniform(
                    self.boundaries.bars[bar_name]['service_time_min'], 
                    self.boundaries.bars[bar_name]['service_time_max']
                ) * self.fps
                
                # Atualizar posições dos outros na fila
                for j, person_id in enumerate(self.current_queues.get(bar_name, [])):
                    if person_id < self.num_people:
                        self.queue_positions[person_id] = j
    def _manage_toilet_queue(self, i):
        """Gerencia pessoa na fila da casa de banho"""
        toilet_name = self.current_destinations[i]
        queue = self.current_queues.get(toilet_name, [])
        
        if queue and queue[0] == i:
            if self.facility_occupancy.get(toilet_name, 0) < self.boundaries.toilets[toilet_name]['capacity']:
                # Sai da fila e entra na casa de banho
                self.in_queue[i] = False
                self.states[i] = 11
                self.facility_occupancy[toilet_name] += 1
                self.current_queues[toilet_name].pop(0)
                self.time_in_facility[i] = np.random.uniform(
                    self.boundaries.toilets[toilet_name]['service_time_min'], 
                    self.boundaries.toilets[toilet_name]['service_time_max']
                ) * self.fps
                
                # Atualizar posições dos outros na fila
                for j, person_id in enumerate(self.current_queues.get(toilet_name, [])):
                    if person_id < self.num_people:
                        self.queue_positions[person_id] = j
    
    def _manage_bar_service(self, i):
        """Gerencia tempo no bar"""
        self.time_in_facility[i] -= 1
        
        if self.time_in_facility[i] <= 0:
            bar_name = self.current_destinations[i]
            self.facility_occupancy[bar_name] = max(0, self.facility_occupancy[bar_name] - 1)
            self.states[i] = 8  # Voltando do bar
            self.destinations[i] = self.assigned_seats[i].copy()
    
    def _manage_toilet_service(self, i):
        """Gerencia tempo na casa de banho"""
        self.time_in_facility[i] -= 1
        
        if self.time_in_facility[i] <= 0:
            toilet_name = self.current_destinations[i]
            self.facility_occupancy[toilet_name] = max(0, self.facility_occupancy[toilet_name] - 1)
            self.states[i] = 12  # Voltando da casa de banho
            self.destinations[i] = self.assigned_seats[i].copy()
    
    def _return_to_seat(self, i):
        """Pessoa volta ao assento"""
        direction = self.destinations[i] - self.positions[i]
        distance = np.linalg.norm(direction)
        
        if distance > 1.0:
            step_vector = (direction / distance) * 0.7
            new_pos = self.positions[i] + step_vector
            
            if self.is_position_valid(new_pos[0], new_pos[1]):
                self.positions[i] = new_pos
            else:
                angle = np.random.uniform(-0.5, 0.5)
                rotation = np.array([[np.cos(angle), -np.sin(angle)], 
                                   [np.sin(angle), np.cos(angle)]])
                self.positions[i] = self.positions[i] + rotation @ step_vector * 0.7
        else:
            self.states[i] = 4  # Sentado
            self.event_gen.update_zone_occupancy(self.assigned_zones[i], +1)

    def _initiate_exit(self, i):
        """Inicia o processo de saída para uma pessoa"""
        if self.states[i] in [13, 14]:  # Já está saindo ou saiu
            return
        
        # Encontrar o portão de saída (usar o mesmo de entrada)
        gate_name = self.entry_gates.get(i, None)
        if not gate_name:
            gate_name, _ = self.boundaries.get_nearest_gate(self.positions[i])
        
        gate_pos = self.boundaries.gates[gate_name]
        
        # Mudar estado para "saindo"
        self.states[i] = 13  # Estado de saída
        self.destinations[i] = np.array(gate_pos)
        self.current_destinations[i] = gate_name
        
        # Remover da contagem da zona
        if i in self.assigned_zones:
            self.event_gen.update_zone_occupancy(self.assigned_zones[i], -1)
        
        # Gerar evento de início de saída
        self.event_gen.generate_event(
            event_type="exit_started",
            person_id=i,
            location=[float(self.positions[i][0]), float(self.positions[i][1])],
            metadata={
                "gate": gate_name,
                "from_zone": self.assigned_zones.get(i, "unknown"),
                "exit_reason": "game_ended"
            }
        )
    
    def update_heatmap(self, current_time):
        """Atualiza heatmap"""
        grid_data = []
        GRID_RESOLUTION = 5
        
        x_cells = int((self.boundaries.stadium_bounds['x_max'] - self.boundaries.stadium_bounds['x_min']) / GRID_RESOLUTION)
        y_cells = int((self.boundaries.stadium_bounds['y_max'] - self.boundaries.stadium_bounds['y_min']) / GRID_RESOLUTION)
        
        for i in range(x_cells):
            for j in range(y_cells):
                x_min = self.boundaries.stadium_bounds['x_min'] + i * GRID_RESOLUTION
                x_max = x_min + GRID_RESOLUTION
                y_min = self.boundaries.stadium_bounds['y_min'] + j * GRID_RESOLUTION
                y_max = y_min + GRID_RESOLUTION
                
                count = 0
                for k in range(self.num_people):
                    x, y = self.positions[k]
                    if x_min <= x < x_max and y_min <= y < y_max and self.states[k] not in [0, 14]:
                        count += 1
                
                if count > 0:
                    center_x = (x_min + x_max) / 2
                    center_y = (y_min + y_max) / 2
                    grid_data.append({
                        "x": center_x,
                        "y": center_y,
                        "count": count,
                        "cell_id": f"cell_{i}_{j}"
                    })
        
        if grid_data:
            self.event_gen.generate_heatmap_density(grid_data)
    
    def get_phase(self, current_time):
        """Retorna fase atual"""
        if current_time > self.timeline["game_end"]:
            return "SAIDA"
        elif current_time > self.timeline["game_resume"]:
            return "2a PARTE"
        elif current_time > self.timeline["half_time"]:
            return "INTERVALO"
        elif current_time > self.timeline["game_start"]:
            return "1a PARTE"
        elif current_time > self.timeline["pre_game"]:
            return "PRE-JOGO"
        else:
            return "ENTRADA"
    
    def run(self):
        """Executa simulação completa"""
        print("Iniciando simulacao completa...")
        print(f"Duracao: {self.duration} segundos")
        
        # Setup
        self.setup_people()
        
        # Configurar visualização
        plt.ion()
        fig, ax = plt.subplots(figsize=(14, 11))
        
        total_steps = self.duration * self.fps  # 1800 steps
        
        # Contadores para controlar atualizações - Aumentados para menor frequência
        last_bin_update = 0
        last_heatmap_update = 0
        last_gate_update = 0
        
        # Loop principal
        for step in range(total_steps):
            current_time = step  # Em segundos
            
            # ATUALIZAR FILAS a cada 10 segundos (aumentado de 5)
            if current_time - self.event_gen.last_queue_update >= 10:
                self.update_queues(current_time)
                self.event_gen.last_queue_update = current_time
            
            # ATUALIZAR CAIXOTES a cada 30 segundos (aumentado de 10)
            if current_time - last_bin_update >= 30:
                self.update_bins(current_time)
                last_bin_update = current_time
            
            # ATUALIZAR HEATMAP a cada 30 segundos (aumentado de 15)
            if current_time - last_heatmap_update >= 30:
                self.update_heatmap(current_time)
                last_heatmap_update = current_time
            
            # GERAR EVENTOS DE PORTÃO ALEATÓRIOS durante entrada (primeiros 60s) - A cada 5s em vez de 2
            if current_time < self.timeline["pre_game"] and current_time - last_gate_update >= 5:
                if np.random.random() < 0.3:
                    gate_name = np.random.choice(list(self.boundaries.gates.keys()))
                    person_id = np.random.randint(0, self.num_people)
                    self.event_gen.generate_gate_event(gate_name, person_id, direction="entry")
                    last_gate_update = current_time
            
            # GERAR EVENTOS DE SAÍDA no final - A cada 10s em vez de 5
            if current_time > self.timeline["game_end"] and current_time - last_gate_update >= 10:
                if np.random.random() < 0.2:
                    gate_name = np.random.choice(list(self.boundaries.gates.keys()))
                    person_id = np.random.randint(0, self.num_people)
                    self.event_gen.generate_gate_event(gate_name, person_id, direction="exit")
                    last_gate_update = current_time

            if current_time > self.timeline["game_end"]:
                # Para cada pessoa, verificar se já está sentada e iniciar saída
                for i in range(self.num_people):
                    if self.states[i] == 4:  # Apenas pessoas sentadas
                        # Verificar se já passou tempo suficiente desde o início da saída
                        time_since_end = current_time - self.timeline["game_end"]
                        
                        # Probabilidade aumenta com o tempo
                        exit_probability = min(0.1, time_since_end / 5000)
                        
                        if np.random.random() < exit_probability:
                            # Iniciar processo de saída
                            self._initiate_exit(i)
            
            # Dispara um único alerta de incêndio aos 900 segundos
            if current_time >= 900 and not self.fire_alert_triggered:
                possible_locations = ["zona_central"]
                location_id = np.random.choice(possible_locations)
                
                if location_id in self.boundaries.bars:
                    loc = self.boundaries.bars[location_id]['center']
                elif location_id in self.boundaries.toilets:
                    loc = self.boundaries.toilets[location_id]['center']
                else:
                    loc = [0, -3]
                
                self.event_gen.generate_fire_alert(location_id, loc,possible_locations, severity="high")
                self.fire_alert_triggered = True
            
            # Atualizar pessoas
            self.update_people(current_time)
            
            # Atualizar visualização a cada step (removido %2 para fluidez, tempo avança 1s por step)
            self._update_visualization(ax, fig, current_time)
            
            # Mostrar progresso a cada 60 segundos (aumentado de 30 para menos output)
            if step % 60 == 0:
                phase = self.get_phase(current_time)
                seated = np.sum(self.states == 4)
                in_bar_queue = np.sum(self.states == 6)
                in_toilet_queue = np.sum(self.states == 10)
                at_bars = np.sum(self.states == 7)
                at_toilets = np.sum(self.states == 11)
                
                print(f"\n[{current_time:03d}s - {phase}]")
                print(f"  Sentados: {seated:3d} | Bares: {at_bars:2d} ({in_bar_queue:2d} fila) | WC: {at_toilets:2d} ({in_toilet_queue:2d} fila)")
            
            # Pausa maior para simulação mais lenta em tempo real (0.1s por step simulada)ss
            time.sleep(0.1)
        
        # Finalizar
        plt.ioff()
        plt.close()
        
        # Gerar eventos finais de evacuação
        print("\nGerando eventos de evacuação...")
        for i in range(self.num_people):
            gate_name = self.entry_gates[i]
            self.event_gen.generate_gate_event(gate_name, i, direction="exit")
            time.sleep(0.01)
        
        # Salvar resultados
        self._save_results()
        
        print("\nSimulacao concluida")
        
        # Estatísticas finais
        broker_stats = self.mqtt_client.get_stats() if hasattr(self.mqtt_client, 'get_stats') else {'messages_count': 0}
        total_bar_queue = sum(len(q) for q in self.current_queues.values() 
                              if any(k in self.boundaries.bars for k in self.current_queues.keys()))
        total_toilet_queue = sum(len(q) for q in self.current_queues.values() 
                                 if any(k in self.boundaries.toilets for k in self.current_queues.keys()))
        
        print(f"\nEstatisticas finais:")
        print(f"  Pessoas: {self.num_people}")
        print(f"  Eventos gerados: {self.event_gen.event_count}")
        print(f"  Mensagens MQTT: {broker_stats.get('messages_count', 0)}")
        print(f"  Filas bares (final): {total_bar_queue}")
        print(f"  Filas WC (final): {total_toilet_queue}")
        
        # Desconectar do MQTT
        try:
            self.mqtt_client.disconnect()
        except:
            pass
    
    def _update_visualization(self, ax, fig, current_time):
        """Atualiza visualização com imagem"""
        ax.clear()
        
        # Mostrar imagem do estádio
        if self.use_image:
            ax.imshow(self.stadium_img, extent=self.img_extent, aspect='equal')
        else:
            ax.set_facecolor('#003366')
            # Desenhar estádio simples
            stadium_rect = plt.Rectangle((-60, -45), 120, 90,
                                       fill=False, edgecolor='white', linewidth=3)
            ax.add_patch(stadium_rect)
            
            # Campo
            field_rect = plt.Rectangle((-8, -8), 16, 10,
                                     facecolor='darkgreen', alpha=0.7, edgecolor='red', linewidth=2)
            ax.add_patch(field_rect)
            
            # Bares
            for bar_name, bar_info in self.boundaries.bars.items():
                bar_rect = plt.Rectangle(
                    (bar_info['x_min'], bar_info['y_min']),
                    bar_info['x_max'] - bar_info['x_min'],
                    bar_info['y_max'] - bar_info['y_min'],
                    fill=True, color='red', alpha=0.4, edgecolor='darkred', linewidth=2
                )
                ax.add_patch(bar_rect)
                
                # Mostrar ocupação
                count = self.facility_occupancy.get(bar_name, 0)
                queue = len(self.current_queues.get(bar_name, []))
                ax.text(bar_info['center'][0], bar_info['center'][1], 
                       f"BAR\n{count}/{bar_info['capacity']}\nF:{queue}",
                       ha='center', va='center', color='white', fontsize=8,
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='red', alpha=0.7))
            
            # Banheiros
            for toilet_name, toilet_info in self.boundaries.toilets.items():
                toilet_rect = plt.Rectangle(
                    (toilet_info['x_min'], toilet_info['y_min']),
                    toilet_info['x_max'] - toilet_info['x_min'],
                    toilet_info['y_max'] - toilet_info['y_min'],
                    fill=True, color='blue', alpha=0.3, edgecolor='darkblue', linewidth=1
                )
                ax.add_patch(toilet_rect)
                
                count = self.facility_occupancy.get(toilet_name, 0)
                queue = len(self.current_queues.get(toilet_name, []))
                ax.text(toilet_info['center'][0], toilet_info['center'][1], 
                       f"WC\n{count}/{toilet_info['capacity']}\nF:{queue}",
                       ha='center', va='center', color='white', fontsize=7,
                       bbox=dict(boxstyle="round,pad=0.2", facecolor='blue', alpha=0.6))
        
        ax.axis('off')
        ax.set_xlim(self.img_extent[0], self.img_extent[1])
        ax.set_ylim(self.img_extent[2], self.img_extent[3])
        
        # Título
        phase = self.get_phase(current_time)
        ax.set_title(f"ESTADIO DO DRAGAO - {phase} - {current_time:.0f}s - {self.num_people} PESSOAS",
                    fontsize=16, color="white", backgroundcolor="#000080", pad=20)
        
        # Plotar pessoas
        colors = {
            3: 'cyan', 4: 'lime', 5: 'red', 6: 'darkred', 7: 'magenta', 8: 'orange',
            9: 'purple', 10: 'darkblue', 11: 'pink', 12: 'brown', 13: 'yellow', 14: 'gray'
        }
        
        labels = {
            3: 'Indo lugar', 4: 'Sentado', 5: 'Indo bar', 6: 'Fila bar', 7: 'No bar',
            8: 'Voltando bar', 9: 'Indo WC', 10: 'Fila WC', 11: 'No WC', 
            12: 'Voltando WC', 13: 'Saindo', 14: 'Saiu'
        }
        
        # Mostrar pessoas em fila
        for i in range(self.num_people):
            if self.in_queue[i]:
                ax.plot(self.positions[i][0], self.positions[i][1], 'o', 
                       color='white', markersize=8, markeredgecolor='black', linewidth=0.5)
        
        # Plotar por estado
        for state, color in colors.items():
            indices = (self.states == state) & (self.states != 14) & (~self.in_queue)
            if np.any(indices):
                ax.scatter(self.positions[indices, 0], self.positions[indices, 1], 
                          c=color, s=30, label=labels[state], edgecolors='black', linewidth=0.5)
        
        # Estatísticas
        people_in_queue = np.sum(self.in_queue)
        people_at_bars = np.sum(self.states == 7)
        people_at_toilets = np.sum(self.states == 11)
        
        stats_text = (f"Total: {self.num_people} pessoas\n"
                     f"Em fila: {people_in_queue}\n"
                     f"Nos bares: {people_at_bars}\n"
                     f"Nos banheiros: {people_at_toilets}\n"
                     f"Sentados: {np.sum(self.states == 4)}\n"
                     f"Eventos: {self.event_gen.event_count}")
        
        ax.text(self.img_extent[0] + 5, self.img_extent[3] - 15, stats_text,
                fontsize=9, color='white', verticalalignment='top',
                bbox=dict(boxstyle="round,pad=0.3", facecolor='black', alpha=0.7))
        
        # Legenda
        ax.legend(loc='upper left', fontsize=8, ncol=3)
        
        plt.draw()
        plt.pause(0.01)

    def _convert_numpy_types(self, obj):
        """
        Converte tipos numpy (int32, int64, float32, etc.) para tipos Python nativos.
        """
        import numpy as np
        
        if isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(self._convert_numpy_types(item) for item in obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif hasattr(obj, '__dict__'):  # Para objetos
            return self._convert_numpy_types(obj.__dict__)
        else:
            return obj
    
    def _save_results(self):
        """Salva as estatísticas da simulação em arquivo JSON"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        stats = {
            'total_people': self.total_people,
            'simulation_duration': self.simulation_duration,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'events': self.event_log,
            'queue_data': self.queue_data_log,
            'phase_changes': self.phase_changes,
            'final_state': {
                'seated': self.seated_count,
                'at_bars': self.at_bars_count,
                'at_wc': self.at_wc_count,
                'in_queue_bars': self.queue_bars_count,
                'in_queue_wc': self.queue_wc_count,
                'exited': self.exited_count
            }
        }
        
        # Converter tipos numpy para tipos Python nativos
        stats = self._convert_numpy_types(stats)
        
        filename = os.path.join(self.output_dir, f"simulation_{int(time.time())}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        print(f"Resultados salvos em {filename}")

def main():
    """Função principal"""
    try:
        simulation = StadiumSimulation(num_people=300, duration=1800)
        simulation.run()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nSimulacao interrompida pelo utilizador")
        return 1
    except Exception as e:
        print(f"\nErro na simulacao: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    main()