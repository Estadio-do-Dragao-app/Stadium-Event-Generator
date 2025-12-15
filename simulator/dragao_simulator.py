"""
Simulador do Estádio do Dragão - Versão Final (Tempos Realistas & Legenda)
"""
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.image import imread
import time
import sys
import math

try:
    from mqtt_broker import StadiumMQTTClient
    from event_generator import EventGenerator
    from stadium_boundaries import StadiumBoundaries
except ImportError as e:
    print(f"Erro: {e}")
    sys.exit(1)

class StadiumSimulation:
    def __init__(self, num_people=500, duration=1800):
        self.num_people = num_people
        self.duration = duration
        
        # Estrutura do estádio
        self.boundaries = StadiumBoundaries()
        
        # Estado das pessoas
        self.positions = np.zeros((num_people, 2))
        self.states = np.zeros(num_people, dtype=int)
        self.destinations = np.zeros((num_people, 2))
        self.people_levels = np.zeros(num_people, dtype=int)
        
        # Variáveis de controle
        self.entry_gates = {}
        self.current_destinations = {} 
        self.time_in_facility = np.zeros(num_people)
        self.in_queue = np.zeros(num_people, dtype=bool)
        self.target_poi = {} # Track which POI they are going to
        self.poi_queue_sizes = {} # Track queue size per POI
        
        # Escadas
        self.stair_time = np.zeros(num_people)
        
        # Timeline (Total 1800s = 30 min)
        # Escala: 1 min simulado = 1 seg real * timescale (mas aqui steps são segundos)
        self.timeline = {
            "pre_game": 0,      # Início
            "game_start": 300,  # 5 min: Começa o jogo
            "half_time": 900,   # 15 min: Intervalo
            "game_resume": 1500,# 25 min: 2ª Parte (Intervalo 10m)
            "game_end": 2100    # 35 min: Fim do Jogo (Saída)
        }
        
        # Imagens
        self.level_images = []
        self.level_extents = []
        self._load_images()
        
        # MQTT
        self.mqtt_client = self._setup_mqtt()
        self.event_gen = EventGenerator(self.mqtt_client)
        
        self.walk_speed = 1

    def _setup_mqtt(self):
        try:
            client = StadiumMQTTClient("stadium_simulator")
            if client.connect() == 0:
                return client
        except:
            pass
        
        class DummyClient:
            def publish(self, *args, **kwargs): return 0
            def subscribe(self, *args, **kwargs): return (0, [0])
            def disconnect(self): pass
        
        return DummyClient()
    
    def _load_images(self):
        """Carrega imagens (1481×945 pixels - tamanho real)"""
        for img_file in ['stadium_0.png', 'stadium_1.png']:
            try:
                img = imread(img_file)
                self.level_images.append(img)
                extent = [0, 1481, 0, 945]
                self.level_extents.append(extent)
            except Exception as e:
                print(f"Erro ao carregar {img_file}: {e}")
                fallback = np.zeros((945, 1481, 3), dtype=np.uint8)
                self.level_images.append(fallback)
                self.level_extents.append([0, 1481, 0, 945])
    
    def setup_people(self):
        """Configura pessoas - Lógica: Lugar L1 -> Escada -> Gate -> Caminho Inverso"""
        print("Configurando pessoas...")
        
        zones_l0 = [z for z, info in self.boundaries.seating_zones.items() if info['level'] == 0]
        zones_l1 = [z for z, info in self.boundaries.seating_zones.items() if info['level'] == 1]
        
        for i in range(self.num_people):
            # 1. Definir Nível Alvo
            target_level = 1 if (np.random.random() < 0.3 and zones_l1) else 0
            
            # 2. Escolher Zona e Lugar FINAL
            valid_zones = zones_l1 if target_level == 1 else zones_l0
            target_zone_name = np.random.choice(valid_zones)
            seat_pos = self.boundaries.get_random_seat_in_zone(target_zone_name)
            
            self.current_destinations[i] = target_zone_name 
            
            # 3. Calcular Caminho Reverso
            if target_level == 1:
                stair_result = self.boundaries.get_nearest_stairs(seat_pos, 1, 0)
                if not stair_result:
                    continue  # Skip if no stairs found
                
                stair_name, stair_info = stair_result
                # Gate mais perto da ESCADA
                gate_result = self.boundaries.get_nearest_gate(stair_info['location'], level=0)
                if not gate_result:
                    continue  # Skip if no gate found
                    
                gate_name, gate_info = gate_result
                
                self.positions[i] = gate_info['location']
                self.entry_gates[i] = gate_name
                self.people_levels[i] = 0 
                
                self.states[i] = 15 # Indo para escadas
                self.destinations[i] = stair_info['location']
                
            else: # target_level == 0
                # Gate mais perto do LUGAR
                gate_result = self.boundaries.get_nearest_gate(seat_pos, level=0)
                if not gate_result:
                    continue  # Skip if no gate found
                    
                gate_name, gate_info = gate_result
                
                self.positions[i] = gate_info['location']
                self.entry_gates[i] = gate_name
                self.people_levels[i] = 0
                
                self.states[i] = 3 # Indo para lugar
                self.destinations[i] = seat_pos

            # Evento entrada
            self.event_gen.generate_gate_event(f"GATE_{gate_info['gate_number']}", i, "entry")
        
        print(f"Pessoas configuradas: {self.num_people}")

    def update_people(self, current_time):
        """Atualiza estado das pessoas"""
        
        for i in range(self.num_people):
            pos = self.positions[i]
            level = self.people_levels[i]
            
            # ================= MOVIMENTO =================
            if self.states[i] == 15: # Gate -> Escadas
                self._move_to_destination(i, self.walk_speed)
                if np.linalg.norm(self.destinations[i] - pos) < 5.0:
                    self.states[i] = 16 
                    self.stair_time[i] = 40 
            
            elif self.states[i] == 16: # Subindo
                self.stair_time[i] -= 1
                if self.stair_time[i] <= 0:
                    self.people_levels[i] = 1 
                    target_zone = self.current_destinations.get(i) 
                    if not target_zone: target_zone = 'ESTE_L1'
                    seat = self.boundaries.get_random_seat_in_zone(target_zone)
                    if seat: self.destinations[i] = seat
                    self.states[i] = 3 
            
            elif self.states[i] == 3: # Indo para lugar
                self._move_to_destination(i, self.walk_speed)
                if np.linalg.norm(self.destinations[i] - pos) < 3.0:
                    self.states[i] = 4 # Sentado
            
            # ================= COMPORTAMENTO SENTADO =================
            elif self.states[i] == 4:
                # Sair apenas no FIM DO JOGO
                if current_time > self.timeline["game_end"]:
                     # Sair gradualmente
                    if np.random.random() < 0.05: self._initiate_exit(i)
                
                # Intervalo: Ir ao Bar/WC (MUITO FREQUENTE - 5%)
                elif self.timeline["half_time"] <= current_time < self.timeline["game_resume"]:
                    if self.states[i] == 4:
                        if np.random.random() < 0.05: 
                            self._go_to_bar(i) if np.random.random() < 0.6 else self._go_to_toilet(i)

                # Durante Jogo: (MODERADO - 1%)
                elif current_time > self.timeline["game_start"] and current_time < self.timeline["game_end"]:
                     if np.random.random() < 0.01:
                        self._go_to_bar(i) if np.random.random() < 0.6 else self._go_to_toilet(i)
            
            # ================= SERVIÇOS =================
            elif self.states[i] in [5, 9]: # Indo Bar/WC
                self._move_to_destination(i, self.walk_speed)
                if np.linalg.norm(self.destinations[i] - pos) < 3.0:
                    self.states[i] += 2 
                    # Tempo de serviço variável: 30-120 segundos
                    self.time_in_facility[i] = np.random.randint(30, 120)
                    # Evento Queue - incrementar contador
                    loc_type = "BAR" if self.states[i] == 7 else "TOILET"
                    poi_id = self.target_poi.get(i, "UNK")
                    if poi_id != "UNK":
                        self.poi_queue_sizes[poi_id] = self.poi_queue_sizes.get(poi_id, 0) + 1
                    queue_size = self.poi_queue_sizes.get(poi_id, 1)
                    self.event_gen.generate_queue_event(loc_type, poi_id, self.destinations[i], queue_size, 10, level=int(level))
            
            elif self.states[i] in [7, 11]: # Esperando
                self.time_in_facility[i] -= 1
                if self.time_in_facility[i] <= 0:
                    # Decrementar fila ao sair
                    poi_id = self.target_poi.get(i, "UNK")
                    if poi_id != "UNK" and poi_id in self.poi_queue_sizes:
                        self.poi_queue_sizes[poi_id] = max(0, self.poi_queue_sizes[poi_id] - 1)
                        # Enviar evento com novo tamanho
                        loc_type = "BAR" if self.states[i] == 7 else "TOILET"
                        queue_size = self.poi_queue_sizes[poi_id]
                        self.event_gen.generate_queue_event(loc_type, poi_id, self.destinations[i], queue_size, 10, level=int(level))
                    # Voltar ao lugar
                    target_zone = self.current_destinations.get(i)
                    if target_zone:
                         seat = self.boundaries.get_random_seat_in_zone(target_zone)
                         self.destinations[i] = seat
                    self.states[i] = 3

            # ================= SAÍDA =================
            elif self.states[i] == 17: # Escadas Descida
                self._move_to_destination(i, self.walk_speed)
                if np.linalg.norm(self.destinations[i] - pos) < 5.0:
                    self.states[i] = 18 
                    self.stair_time[i] = 40
            
            elif self.states[i] == 18:
                self.stair_time[i] -= 1
                if self.stair_time[i] <= 0:
                    self.people_levels[i] = 0 
                    gate_name = self.entry_gates[i]
                    if gate_name:
                         info = self.boundaries.gates[gate_name]
                         self.destinations[i] = info['location']
                         self.event_gen.generate_gate_event(gate_name, i, "exit")
                    self.states[i] = 13 
            
            elif self.states[i] == 13: # Indo para Gate
                self._move_to_destination(i, self.walk_speed * 1.2)
                if np.linalg.norm(self.destinations[i] - pos) < 5.0:
                    self.states[i] = 14 

    def _initiate_exit(self, i):
        level = self.people_levels[i]
        if level == 1:
            self.states[i] = 17 
            stair, info = self.boundaries.get_nearest_stairs(self.positions[i], 1, 0)
            if info: self.destinations[i] = info['location']
        else:
            self.states[i] = 13
            gate = self.entry_gates[i]
            if gate:
                info = self.boundaries.gates[gate]
                self.destinations[i] = info['location']

    def _go_to_bar(self, i):
        level = self.people_levels[i]
        name, info = self.boundaries.get_nearest_bar(self.positions[i], level)
        if info:
            self.states[i] = 5
            self.destinations[i] = info['center']
            self.target_poi[i] = name
            
    def _go_to_toilet(self, i):
        level = self.people_levels[i]
        name, info = self.boundaries.get_nearest_toilet(self.positions[i], level)
        if info:
            self.states[i] = 9
            self.destinations[i] = info['center']
            self.target_poi[i] = name

    def _move_to_destination(self, i, speed):
        """Movimento robusto com Sliding e Debug"""
        pos = self.positions[i]
        dest = self.destinations[i]
        level = self.people_levels[i]
        
        vec = dest - pos
        dist = np.linalg.norm(vec)
        
        if dist < 1.0: return # Chegou
        
        # Passo normal
        step = (vec / dist) * min(speed, dist)
        proposed_pos = pos + step
        
        # 1. Tentar movimento direto
        if self.boundaries.is_position_valid(proposed_pos[0], proposed_pos[1], level):
            self.positions[i] = proposed_pos
            return
            
        # 2. Se falhou, tentar deslizar (Sliding)
        # Tentar só X
        test_x = pos + np.array([step[0], 0])
        if self.boundaries.is_position_valid(test_x[0], test_x[1], level):
            self.positions[i] = test_x
            return
            
        # Tentar só Y
        test_y = pos + np.array([0, step[1]])
        if self.boundaries.is_position_valid(test_y[0], test_y[1], level):
            self.positions[i] = test_y
            return
            
        # 3. Se falhou (Bloqueado por Campo ou Limites)
        # Tentar movimento orbital (contornar o centro)
        cx, cy = self.boundaries.get_center_for_level(level)
        to_center = pos - np.array([cx, cy])
        dist_center = np.linalg.norm(to_center)
        
        if dist_center > 0:
            # Vetor tangente (rotação 90 graus)
            tangent = np.array([-to_center[1], to_center[0]])
            tangent = tangent / np.linalg.norm(tangent)
            
            # Decidir direção (horário ou anti-horário) baseado no produto vetorial
            cross_prod = np.cross(vec, to_center)
            if cross_prod < 0: tangent = -tangent
            
            move_amount = min(speed, dist)
            test_orbital = pos + tangent * move_amount
            if self.boundaries.is_position_valid(test_orbital[0], test_orbital[1], level):
                self.positions[i] = test_orbital
                return

        # 4. Bloqueio Total
        if i == 0: 
            print(f"⚠️ AGENTE 0 PRESO [L:{level}] Pos:{pos.astype(int)} -> Dest:{dest.astype(int)}")
            # ... teleporte de emergência mantém-se ...
            noise = np.random.normal(0, 2, 2)
            escape = pos + noise
            if self.boundaries.is_position_valid(escape[0], escape[1], level):
                self.positions[i] = escape

    def _trigger_fire(self, current_time):
        zones = list(self.boundaries.seating_zones.values())
        if not zones: return
        target_zone = zones[np.random.randint(len(zones))]
        
        ang = (target_zone['angle_start'] + target_zone['angle_end']) / 2
        r_inner = target_zone['radius_inner_x']
        
        fire_pos = self.boundaries.ellipse_pos(ang, r_inner + 20, level=target_zone['level'])
        affected = [target_zone['sector']]
        pass_level = target_zone['level']
        
        self.event_gen.generate_fire_alert(
            "FIRE_TEST", fire_pos, affected, level=pass_level, severity="critical"
        )
        print(f"\n🔥 INCÊNDIO EM {target_zone['sector']} (Nível {target_zone['level']})")

    def _update_display(self, axes, fig, current_time, fire=False):
        # CORES & LEGENDAS
        # Definir dicionário completo e criar lista para legendas
        states_def = {
            3:  ('cyan', 'Andar (Lugar)'),
            4:  ('lime', 'Sentado'),
            5:  ('orange', 'Indo Bar'),
            7:  ('magenta', 'No Bar'),
            9:  ('purple', 'Indo WC'),
            11: ('pink', 'No WC'),
            13: ('yellow', 'Saindo'),
            14: ('gray', 'Saiu'),
            15: ('white', 'Indo Escadas'),
            17: ('gold', 'Indo Saída (Esc)')
        }
        
        for level in [0, 1]:
            ax = axes[level]
            ax.clear()
            
            if level < len(self.level_images):
                ax.imshow(self.level_images[level], extent=self.level_extents[level], 
                         alpha=0.6, origin='lower', aspect='auto')
            
            level_mask = (self.people_levels == level)
            
            for state, (color, label) in states_def.items():
                mask = level_mask & (self.states == state)
                if np.any(mask):
                    ax.scatter(
                        self.positions[mask, 0], self.positions[mask, 1],
                        c=color, s=12, edgecolors='black', linewidth=0.2, alpha=0.9
                    )
            
            if level == 0:
                for gname, ginfo in self.boundaries.gates.items():
                    gx, gy = ginfo['location']
                    ax.plot(gx, gy, 'ks', markersize=4)
            
            # Formatar tempo
            mins = current_time // 60
            phase = "Entrada"
            if current_time > 300: phase = "1ª Parte"
            if current_time > 900: phase = "Intervalo"
            if current_time > 1080: phase = "2ª Parte"
            if current_time > 1680: phase = "Saída"
            
            ax.set_title(f"N{level} | {mins} min | {phase} | Pessoas: {np.sum(level_mask)}")
            ax.set_xlim(0, 1481)
            ax.set_ylim(0, 945)
            ax.set_axis_off()

        # LEGENDA GLOBAL (Apenas na figura)
        patches = [mpatches.Patch(color=c, label=l) for c, l in states_def.values()]
        fig.legend(handles=patches, loc='lower center', ncol=5, fontsize=8, frameon=True)
        
        fig.tight_layout()
        # Ajustar para caber a legenda
        plt.subplots_adjust(bottom=0.15)

    def run_simulation(self):
        plt.ion()
        fig, axes = plt.subplots(1, 2, figsize=(16, 9))
        
        self.setup_people()
        
        fire_time = 1400 # Fogo na 2a parte
        fire_trig = False
        
        try:
            # Loop até 1800 (30 min)
            for step in range(self.duration + 100):
                self.update_people(step)
                
                if step == fire_time and not fire_trig:
                    self._trigger_fire(step)
                    fire_trig = True
                
                # Render menos frequente (a cada 5 steps) e PAUSA AQUI
                if step % 5 == 0: 
                    self._update_display(axes, fig, step)
                    plt.pause(0.01) # Única pausa do loop!

                if step % 10 == 0:
                    self._generate_heatmaps()
                
                if step % 60 == 0:
                    l0 = np.sum(self.people_levels == 0)
                    l1 = np.sum(self.people_levels == 1)
                    st = self.states
                    seated = np.sum(st == 4)
                    serv = np.sum((st == 7) | (st == 11))  # No Bar (7) ou No WC (11) - em serviço
                    queue = np.sum((st == 5) | (st == 9))  # Indo Bar (5) ou Indo WC (9) - a caminho/fila
                    move = self.num_people - seated - serv - queue
                    print(f"Time: {step//60:02d}m | L0:{l0} L1:{l1} | Seated: {seated} in Service: {serv} in Queue: {queue} Moving: {move}") 
                
        except KeyboardInterrupt:
            pass
        finally:
            plt.ioff()
            plt.show()

    def _generate_heatmaps(self):
        """Gera heatmaps para ambos os pisos usando numpy histogram"""
        grid_step = 50 # 50 pixels approx 5 meters
        width, height = 1481, 945
        
        x_bins = np.arange(0, width + grid_step, grid_step)
        y_bins = np.arange(0, height + grid_step, grid_step)
        
        for level in [0, 1]:
            mask = (self.people_levels == level)
            if not np.any(mask):
                # Send empty update to clear if no one is there
                self.event_gen.generate_heatmap_density([], level=level)
                continue
                
            active_positions = self.positions[mask]
            
            # Use histogram2d for fast binning
            hist, _, _ = np.histogram2d(
                active_positions[:, 0], 
                active_positions[:, 1], 
                bins=[x_bins, y_bins]
            )
            
            # Convert to format expected by backend
            grid_data = []
            nx, ny = hist.shape
            for i in range(nx):
                for j in range(ny):
                    count = int(hist[i, j])
                    if count > 0:
                        # Center of the cell
                        cx = x_bins[i] + grid_step/2
                        cy = y_bins[j] + grid_step/2
                        grid_data.append({
                            "x": int(cx),
                            "y": int(cy),   
                            "count": count
                        })
            
            self.event_gen.generate_heatmap_density(grid_data, level=level)

def main():
    sim = StadiumSimulation(num_people=500, duration=2200)
    sim.run_simulation()
    return 0

if __name__ == "__main__":
    sys.exit(main())