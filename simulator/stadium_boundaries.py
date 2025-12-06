"""
Define a estrutura completa do estádio.
"""
import numpy as np

class StadiumBoundaries:
    def __init__(self):
        # FORMATO VISUAL (retângulo 120×90)
        self.stadium_bounds = {'x_min': -60, 'x_max': 60, 'y_min': -45, 'y_max': 45}
        
        # RESTRIÇÕES:
        self.stadium_center = [0, -3]
        self.stadium_radius = 40
        
        # CAMPO (no centro, fora dos limites para pessoas)
        self.field_x_min = -8
        self.field_x_max = 8
        self.field_y_min = -8
        self.field_y_max = 2
        
        # PORTÕES (fora do estádio)
        self.gates = {
            'GATE_NORTH': [-4.8, 45.2],    # Norte
            'GATE_SOUTH': [0.2, -48.3],   # Sul
        }
        
        # 2 BARES (dentro do estádio, fora do campo)
        self.bars = {
            'BAR_OESTE': {
                'x_min': -34, 'x_max': -27,
                'y_min': -6, 'y_max': 0,
                'center': [-30.5, -3],
                'capacity': 15,  # Apenas 15 pessoas cabem no bar
                'service_time_min': 20,
                'service_time_max': 40,
                'queue_spots': 25  # Espaço para 25 pessoas na fila
            },
            'BAR_LESTE': {
                'x_min': 28.5, 'x_max': 37,
                'y_min': -6, 'y_max': -2,
                'center': [32.75, -4],
                'capacity': 15,
                'service_time_min': 20,
                'service_time_max': 40,
                'queue_spots': 25
            }
        }
        
        # 10 CASAS DE BANHO (dentro do estádio, fora do campo)
        self.toilets = {
            'WC_1': {  # Canto Noroeste Superior
                'x_min': -17.1, 'x_max': -15.2,
                'y_min': 11.2, 'y_max': 12.6,
                'center': [(-17.1 + -15.2)/2, (11.2 + 12.6)/2],  # [-16.15, 11.9]
                'capacity': 4,
                'service_time_min': 10,
                'service_time_max': 20,
                'queue_spots': 15
            },
            'WC_2': {  # Canto Noroeste Inferior
                'x_min': -17.0, 'x_max': -15.2,
                'y_min': -19.6, 'y_max': -18.1,
                'center': [(-17.0 + -15.2)/2, (-19.6 + -18.1)/2],  # [-16.1, -18.85]
                'capacity': 4,
                'service_time_min': 10,
                'service_time_max': 20,
                'queue_spots': 15
            },
            'WC_3': {  # Centro Sul
                'x_min': 0.1, 'x_max': 2.3,
                'y_min': -38.2, 'y_max': -36.3,
                'center': [(0.1 + 2.3)/2, (-38.2 + -36.3)/2],  # [1.2, -37.25]
                'capacity': 6,
                'service_time_min': 10,
                'service_time_max': 20,
                'queue_spots': 20
            },
            'WC_4': {  # Canto Sudeste Inferior
                'x_min': 15.1, 'x_max': 17.0,
                'y_min': -19.4, 'y_max': -17.9,
                'center': [(15.1 + 17.0)/2, (-19.4 + -17.9)/2],  # [16.05, -18.65]
                'capacity': 4,
                'service_time_min': 10,
                'service_time_max': 20,
                'queue_spots': 15
            },
            'WC_5': {  # Canto Sudeste Superior
                'x_min': 15.2, 'x_max': 17.0,
                'y_min': 11.2, 'y_max': 12.7,
                'center': [(15.2 + 17.0)/2, (11.2 + 12.7)/2],  # [16.1, 11.95]
                'capacity': 4,
                'service_time_min': 10,
                'service_time_max': 20,
                'queue_spots': 15
            },
            'WC_6': {  # Centro Norte
                'x_min': 0.1, 'x_max': 2.2,
                'y_min': 29.8, 'y_max': 31.5,
                'center': [(0.1 + 2.2)/2, (29.8 + 31.5)/2],  # [1.15, 30.65]
                'capacity': 6,
                'service_time_min': 10,
                'service_time_max': 20,
                'queue_spots': 20
            },
            'WC_7': {  # Oeste Central Inferior
                'x_min': -34.8, 'x_max': -32.6,
                'y_min': -14.0, 'y_max': -12.3,
                'center': [(-34.8 + -32.6)/2, (-14.0 + -12.3)/2],  # [-33.7, -13.15]
                'capacity': 4,
                'service_time_min': 10,
                'service_time_max': 20,
                'queue_spots': 15
            },
            'WC_8': {  # Oeste Central Superior
                'x_min': -33.5, 'x_max': -31.5,
                'y_min': 8.6, 'y_max': 10.2,
                'center': [(-33.5 + -31.5)/2, (8.6 + 10.2)/2],  # [-32.5, 9.4]
                'capacity': 4,
                'service_time_min': 10,
                'service_time_max': 20,
                'queue_spots': 15
            },
            'WC_9': {  # Este Central Superior
                'x_min': 30.9, 'x_max': 33.2,
                'y_min': 8.5, 'y_max': 10.1,
                'center': [(30.9 + 33.2)/2, (8.5 + 10.1)/2],  # [32.05, 9.3]
                'capacity': 4,
                'service_time_min': 10,
                'service_time_max': 20,
                'queue_spots': 15
            },
            'WC_10': {  # Este Central Inferior
                'x_min': 30.7, 'x_max': 33.0,
                'y_min': -16.8, 'y_max': -14.8,
                'center': [(30.7 + 33.0)/2, (-16.8 + -14.8)/2],  # [31.85, -15.8]
                'capacity': 4,
                'service_time_min': 10,
                'service_time_max': 20,
                'queue_spots': 15
            }
        }
        
        # ZONAS DE BANCOS (dentro do estádio, fora do campo)
        self.seating_areas = {
            # ZONAS SUL
            'SEAT_SUL_1': {
                'x_min': -23.3, 'x_max': -2.8,
                'y_min': -36.8, 'y_max': -34.0,
                'center': [(-23.3 + -2.8)/2, (-36.8 + -34.0)/2],  # [-13.05, -35.4]
                'capacity': 60
            },
            'SEAT_SUL_2': {
                'x_min': 4.1, 'x_max': 20.7,
                'y_min': -41.8, 'y_max': -29.5,
                'center': [(4.1 + 20.7)/2, (-41.8 + -29.5)/2],  # [12.4, -35.65]
                'capacity': 60
            },
            'SEAT_SUL_3': {
                'x_min': 25.2, 'x_max': 37.4,
                'y_min': -25.7, 'y_max': -9.2,
                'center': [(25.2 + 37.4)/2, (-25.7 + -9.2)/2],  # [31.3, -17.45]
                'capacity': 60
            },
            'SEAT_SUL_4': {
                'x_min': -13.6, 'x_max': -1.1,
                'y_min': -22.1, 'y_max': -16.0,
                'center': [(-13.6 + -1.1)/2, (-22.1 + -16.0)/2],  # [-7.35, -19.05]
                'capacity': 60
            },
            'SEAT_SUL_5': {
                'x_min': 1.1, 'x_max': 11.6,
                'y_min': -23.3, 'y_max': -14.4,
                'center': [(1.1 + 11.6)/2, (-23.3 + -14.4)/2],  # [6.35, -18.85]
                'capacity': 60
            },
            'SEAT_SUL_6': {
                'x_min': -21.5, 'x_max': -12.4,
                'y_min': -9.4, 'y_max': 1.0,
                'center': [(-21.5 + -12.4)/2, (-9.4 + 1.0)/2],  # [-16.95, -4.2]
                'capacity': 60
            },
            
            # ZONAS NORTE
            'SEAT_NORTE_1': {
                'x_min': 25.8, 'x_max': 33.9,
                'y_min': 1.5, 'y_max': 16.2,
                'center': [(25.8 + 33.9)/2, (1.5 + 16.2)/2],  # [29.85, 8.85]
                'capacity': 50
            },
            'SEAT_NORTE_2': {
                'x_min': 3.3, 'x_max': 23.9,
                'y_min': 25.1, 'y_max': 30.4,
                'center': [(3.3 + 23.9)/2, (25.1 + 30.4)/2],  # [13.6, 27.75]
                'capacity': 50
            },
            'SEAT_NORTE_3': {
                'x_min': -19.2, 'x_max': -1.8,
                'y_min': 23.2, 'y_max': 35.5,
                'center': [(-19.2 + -1.8)/2, (23.2 + 35.5)/2],  # [-10.5, 29.35]
                'capacity': 50
            },
            'SEAT_NORTE_4': {
                'x_min': 11.7, 'x_max': 20.4,
                'y_min': -9.2, 'y_max': 3.1,
                'center': [(11.7 + 20.4)/2, (-9.2 + 3.1)/2],  # [16.05, -3.05]
                'capacity': 50
            },
            'SEAT_NORTE_5': {
                'x_min': 0.1, 'x_max': 11.8,
                'y_min': 8.5, 'y_max': 16.5,
                'center': [(0.1 + 11.8)/2, (8.5 + 16.5)/2],  # [5.95, 12.5]
                'capacity': 50
            },
            'SEAT_NORTE_6': {
                'x_min': -12.7, 'x_max': -0.4,
                'y_min': 7.6, 'y_max': 15.7,
                'center': [(-12.7 + -0.4)/2, (7.6 + 15.7)/2],  # [-6.55, 11.65]
                'capacity': 50
            }
        }
        
        # Caixotes do lixo (espalhados pelo estádio)
        self.bins = {
            'BIN_NORTE_1': [-30, 38], 'BIN_NORTE_2': [30, 38],
            'BIN_SUL_1': [-30, -38], 'BIN_SUL_2': [30, -38],
            'BIN_LESTE': [52, 0], 'BIN_OESTE': [-52, 0],
            'BIN_BAR_LESTE': [35, -5], 'BIN_BAR_OESTE': [-32, -3],
            'BIN_WC_NORTE_LESTE': [52, 35], 'BIN_WC_NORTE_OESTE': [-52, 35],
            'BIN_WC_SUL_LESTE': [52, -35], 'BIN_WC_SUL_OESTE': [-52, -35]
        }
    
    def is_inside_stadium_circle(self, x, y):
        """Verifica se está dentro do círculo do estádio"""
        distance_squared = (x - self.stadium_center[0])**2 + (y - self.stadium_center[1])**2
        return distance_squared <= self.stadium_radius**2
    
    def is_inside_field(self, x, y):
        """Verifica se está dentro do campo"""
        return (self.field_x_min <= x <= self.field_x_max and 
                self.field_y_min <= y <= self.field_y_max)
    
    def is_position_allowed(self, x, y):
        """Verifica se posição é permitida (dentro do estádio mas fora do campo)"""
        return self.is_inside_stadium_circle(x, y) and not self.is_inside_field(x, y)
    
    def get_random_position_in_zone(self, zone_info):
        """Obtém posição aleatória dentro de uma zona"""
        for _ in range(10):
            x = np.random.uniform(zone_info['x_min'], zone_info['x_max'])
            y = np.random.uniform(zone_info['y_min'], zone_info['y_max'])
            if self.is_position_allowed(x, y):
                return [x, y]
        return zone_info['center']
    
    def get_nearest_gate(self, position):
        """Retorna o portão mais próximo"""
        gates_list = list(self.gates.values())
        distances = [np.linalg.norm(np.array(position) - np.array(gate)) for gate in gates_list]
        nearest_idx = np.argmin(distances)
        return list(self.gates.keys())[nearest_idx], list(self.gates.values())[nearest_idx]
    
    def get_nearest_bar(self, position):
        """Retorna o bar mais próximo"""
        bars_list = list(self.bars.keys())
        distances = []
        for bar_name in bars_list:
            bar_center = self.bars[bar_name]['center']
            distances.append(np.linalg.norm(np.array(position) - np.array(bar_center)))
        nearest_idx = np.argmin(distances)
        nearest_bar = bars_list[nearest_idx]
        return nearest_bar, self.bars[nearest_bar]
    
    def get_nearest_toilet(self, position):
        """Retorna a casa de banho mais próxima"""
        toilets_list = list(self.toilets.keys())
        distances = []
        for toilet_name in toilets_list:
            toilet_center = self.toilets[toilet_name]['center']
            distances.append(np.linalg.norm(np.array(position) - np.array(toilet_center)))
        nearest_idx = np.argmin(distances)
        nearest_toilet = toilets_list[nearest_idx]
        return nearest_toilet, self.toilets[nearest_toilet]
    
    def get_queue_position(self, facility_info, queue_number):
        """Calcula posição na fila baseada no número na fila"""
        x = facility_info['x_min'] - 2 - (queue_number % 5) * 1.5
        y = facility_info['y_min'] + (queue_number // 5) * 1.5
        return [x, y]
    
    def get_seat_near_gate(self, gate_name):
        """Retorna um assento próximo do portão"""
        gate_to_zones = {
            'GATE_NORTH': ['SEAT_NORTE_1', 'SEAT_NORTE_2', 'SEAT_NORTE_3',
                          'SEAT_NORTE_4', 'SEAT_NORTE_5', 'SEAT_NORTE_6'],
            'GATE_SOUTH': ['SEAT_SUL_1', 'SEAT_SUL_2', 'SEAT_SUL_3',
                          'SEAT_SUL_4', 'SEAT_SUL_5', 'SEAT_SUL_6'],
        }
        zones = gate_to_zones.get(gate_name, list(self.seating_areas.keys()))
        zone_name = np.random.choice(zones)
        zone_info = self.seating_areas[zone_name]
        seat_position = self.get_random_position_in_zone(zone_info)
        return zone_name, seat_position