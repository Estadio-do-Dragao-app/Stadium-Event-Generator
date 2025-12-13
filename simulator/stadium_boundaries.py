"""
Define a estrutura completa do estádio usando sistema elíptico do Map-Service.
Baseado em: node/Map-Service/load_data_db.py
"""
import numpy as np
import math

class StadiumBoundaries:
    def __init__(self):
        # ==================== CONFIGURAÇÃO CALIBRADA ====================
        # Imagem: 1481×945 pixels
        self.IMG_WIDTH = 1481
        self.IMG_HEIGHT = 945
        
        # --- CONFIGURAÇÃO ELÍPTICA ---
        # Aspect Ratio Global (Y/X) calculado: 0.701
        self.ELLIPSE_RATIO = 0.701
    
        # Centros Calibrados
        self.CENTER_X_L0 = 746.1
        self.CENTER_Y_L0 = 480.6
        self.CENTER_X_L1 = 707.4
        self.CENTER_Y_L1 = 466.8
        
        # Compatibilidade com código antigo (usa L0 como default)
        self.CENTER_X = self.CENTER_X_L0
        self.CENTER_Y = self.CENTER_Y_L0
        
        # Raios de referência (Mantidos para lógica de gates/corredores)
        # Raios de referência (Ajustados para acompanhar as bancadas R_out ~360)
        self.OUTER_PERIMETER_X = 390 # Gates ficam aqui
        self.OUTER_PERIMETER_Y = 390 * self.ELLIPSE_RATIO
        
        self.CORRIDOR_INNER_X = 370 # Bares/WCs ficam aqui
        self.CORRIDOR_INNER_Y = 370 * self.ELLIPSE_RATIO
        
        # Corredores calculados
        self.CORRIDOR_OUTER_X = 380
        self.CORRIDOR_OUTER_Y = 380 * self.ELLIPSE_RATIO
        
        self.CORRIDOR_MID_X = 375
        self.CORRIDOR_MID_Y = 375 * self.ELLIPSE_RATIO
        
        # Raio Campo (Área Proibida) calibrado
        self.FIELD_RADIUS_X = 219.2 
        self.FIELD_RADIUS_Y = 219.2 * self.ELLIPSE_RATIO
        
        self.stadium_bounds = {
            'x_min': 0, 'x_max': self.IMG_WIDTH,
            'y_min': 0, 'y_max': self.IMG_HEIGHT
        }
        
        # Definição Lógica das Bancadas (Setores Amplos para Gates/Estruturas)
        self.STANDS = {
            'Norte': {'angle_start': 45, 'angle_end': 135, 'tiers': 1, 'levels': [0]},
            'Sul':   {'angle_start': 225, 'angle_end': 315, 'tiers': 1, 'levels': [0]},
            'Este':  {'angle_start': 135, 'angle_end': 225, 'tiers': 2, 'levels': [0, 1]},
            'Oeste': {'angle_start': 315, 'angle_end': 405, 'tiers': 2, 'levels': [0, 1]}
        }
        
        self.REAL_GATES = {
            'Norte': [21, 22, 23],
            'Sul': [7, 8, 9],
            'Este': [10, 11, 12, 13, 17, 18],
            'Oeste': [3, 4, 5, 6, 24, 25, 26, 27]
        }
        
        # Inicializar estruturas
        self.seating_zones = self._create_seating_zones()
        self.gates = self._create_gates()
        self.bars = self._create_bars()
        self.toilets = self._create_toilets()
        self.stairs = self._create_stairs()
        self.bins = self._create_bins()
        
        print(f"Estrutura carregada: {len(self.seating_zones)} zonas, {len(self.gates)} gates")

    # ==================== AUXILIARES ====================

    def get_center_for_level(self, level):
        if level == 1:
            return self.CENTER_X_L1, self.CENTER_Y_L1
        return self.CENTER_X_L0, self.CENTER_Y_L0

    def ellipse_pos(self, angle_deg, radius_x, radius_y=None, level=0):
        """Calcula posição (x,y) usando o centro correto do nível e ratio"""
        cx, cy = self.get_center_for_level(level)
        
        if radius_y is None:
            radius_y = radius_x * self.ELLIPSE_RATIO
            
        angle = math.radians(angle_deg)
        x = cx + radius_x * math.cos(angle)
        y = cy + radius_y * math.sin(angle)
        return [x, y]
    
    def is_position_in_field(self, x, y, level=0):
        """Verifica se posição está no CAMPO (área proibida), ajustado por nível"""
        cx, cy = self.get_center_for_level(level)
        dx = x - cx
        dy = y - cy
        
        rx = self.FIELD_RADIUS_X if level == 0 else self.FIELD_RADIUS_X - 10
        ry = rx * self.ELLIPSE_RATIO
        
        in_ellipse = (dx / rx)**2 + (dy / ry)**2
        return in_ellipse <= 1.0

    def get_angle_from_position(self, x, y, level=0):
        cx, cy = self.get_center_for_level(level)
        dx = x - cx
        dy = y - cy
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0: angle += 360
        return angle

    def is_angle_in_range(self, angle, start, end):
        """Verifica se ângulo está no intervalo (com wraparound)"""
        if end > 360:
            return angle >= start or angle <= (end - 360)
        else:
            return start <= angle <= end

    # ==================== CRIAÇÃO DE ZONAS (CALIBRADO) ====================

    def _create_seating_zones(self):
        zones = {}

        zones['NORTE_L0'] = {
            'type': 'elliptical_sector',
            'level': 0,
            'sector': 'NORTE',
            'angle_start': 46.8,
            'angle_end': 133.0,
            'radius_inner_x': 226.2,
            'radius_outer_x': 357.3,
            'capacity': 200
        }

        zones['SUL_L0'] = {
            'type': 'elliptical_sector',
            'level': 0,
            'sector': 'SUL',
            'angle_start': 226.6,
            'angle_end': 311.8,
            'radius_inner_x': 229.8,
            'radius_outer_x': 360.1,
            'capacity': 200
        }

        zones['ESTE_L0'] = {
            'type': 'elliptical_sector',
            'level': 0,
            'sector': 'ESTE',
            'angle_start': 137.1,
            'angle_end': 220.3,
            'radius_inner_x': 230.6,
            'radius_outer_x': 346.6,
            'capacity': 200
        }

        zones['OESTE_L0'] = {
            'type': 'elliptical_sector',
            'level': 0,
            'sector': 'OESTE',
            'angle_start': 316.6,
            'angle_end': 402.6,
            'radius_inner_x': 226.6,
            'radius_outer_x': 339.2,
            'capacity': 200
        }

        zones['ESTE_L1'] = {
            'type': 'elliptical_sector',
            'level': 1,
            'sector': 'ESTE',
            'angle_start': 141.5,
            'angle_end': 223.0,
            'radius_inner_x': 240.2,
            'radius_outer_x': 348.0,
            'capacity': 200
        }

        zones['OESTE_L1'] = {
            'type': 'elliptical_sector',
            'level': 1,
            'sector': 'OESTE',
            'angle_start': 318.0,
            'angle_end': 398.0,
            'radius_inner_x': 236.3,
            'radius_outer_x': 342.6,
            'capacity': 200
        }
        return zones

    # ==================== OUTRAS ESTRUTURAS ====================

    def _create_gates(self):
        # Gates manuais calibrados
        raw_gates = {
            'GATE_21': {'pos': [746, 869], 'sec': 'Norte'},
            'GATE_22': {'pos': [984, 815], 'sec': 'Norte'},
            'GATE_23': {'pos': [1125, 712], 'sec': 'Norte'},
            
            'GATE_7': {'pos': [1190, 626], 'sec': 'Sul'}, # Nota: User chamou Sul mas coords parecem Oeste na imagem? Vou confiar na label do user.
            'GATE_8': {'pos': [1220, 528], 'sec': 'Sul'},
            'GATE_9': {'pos': [1220, 431], 'sec': 'Sul'},
            
            'GATE_10': {'pos': [1188, 330], 'sec': 'Este'},
            'GATE_11': {'pos': [1126, 247], 'sec': 'Este'},
            'GATE_12': {'pos': [986, 142], 'sec': 'Este'}, 
            'GATE_13': {'pos': [744, 92], 'sec': 'Este'},
            'GATE_17': {'pos': [506, 146], 'sec': 'Este'},
            'GATE_18': {'pos': [375, 232], 'sec': 'Este'},
            
            'GATE_3': {'pos': [325, 300], 'sec': 'Oeste'},
            'GATE_4': {'pos': [285, 369], 'sec': 'Oeste'},
            'GATE_5': {'pos': [266, 446], 'sec': 'Oeste'},
            'GATE_6': {'pos': [266, 521], 'sec': 'Oeste'},
            'GATE_24': {'pos': [285, 601], 'sec': 'Oeste'},
            'GATE_25': {'pos': [325, 665], 'sec': 'Oeste'},
            'GATE_26': {'pos': [375, 725], 'sec': 'Oeste'},
            'GATE_27': {'pos': [504, 819], 'sec': 'Oeste'}
        }
        
        gates = {}
        cx, cy = self.get_center_for_level(0)
        
        for name, info in raw_gates.items():
            x, y = info['pos']
            angle = math.degrees(math.atan2(y - cy, x - cx))
            if angle < 0: angle += 360
            
            # Este=Esquerda(180), Oeste=Direita(0), Norte=Cima(90), Sul=Baixo(270)
            if 45 <= angle < 135: real_sector = 'Norte'
            elif 135 <= angle < 225: real_sector = 'Este'
            elif 225 <= angle < 315: real_sector = 'Sul'
            else: real_sector = 'Oeste'
            
            num = int(name.split('_')[1])
            gates[name] = {
                'location': info['pos'],
                'level': 0,
                'gate_number': num,
                'sector': real_sector,
                'capacity': 40
            }
        return gates

    def _create_bars(self):
        bars = {}
        bars['REST_L0_1'] = { 'center': [744.2, 818.6], 'level': 0, 'capacity': 20 }
        bars['REST_L0_2'] = { 'center': [957.8, 768.0], 'level': 0, 'capacity': 20 }
        bars['REST_L0_3'] = { 'center': [1109.5, 648.1], 'level': 0, 'capacity': 20 }
        bars['REST_L0_4'] = { 'center': [1169.5, 481.4], 'level': 0, 'capacity': 20 }
        bars['REST_L0_5'] = { 'center': [1109.5, 316.5], 'level': 0, 'capacity': 20 }
        bars['REST_L0_6'] = { 'center': [955.9, 194.7], 'level': 0, 'capacity': 20 }
        bars['REST_L0_7'] = { 'center': [746.1, 144.1], 'level': 0, 'capacity': 20 }
        bars['REST_L0_8'] = { 'center': [534.4, 194.7], 'level': 0, 'capacity': 20 }
        bars['REST_L0_9'] = { 'center': [378.9, 314.6], 'level': 0, 'capacity': 20 }
        bars['REST_L0_10'] = { 'center': [322.7, 479.5], 'level': 0, 'capacity': 20 }
        bars['REST_L0_11'] = { 'center': [380.8, 644.4], 'level': 0, 'capacity': 20 }
        bars['REST_L0_12'] = { 'center': [536.3, 768.0], 'level': 0, 'capacity': 20 }
        return bars

    def _create_toilets(self):
        toilets = {}
        toilets['WC_L0_1'] = { 'center': [639.3, 786.7], 'level': 0, 'capacity': 10 }
        toilets['WC_L0_2'] = { 'center': [851.0, 788.6], 'level': 0, 'capacity': 10 }
        toilets['WC_L0_3'] = { 'center': [1141.4, 565.7], 'level': 0, 'capacity': 10 }
        toilets['WC_L0_4'] = { 'center': [1139.5, 397.1], 'level': 0, 'capacity': 10 }
        toilets['WC_L0_5'] = { 'center': [852.9, 172.2], 'level': 0, 'capacity': 10 }
        toilets['WC_L0_6'] = { 'center': [639.3, 174.1], 'level': 0, 'capacity': 10 }
        toilets['WC_L0_7'] = { 'center': [348.9, 400.8], 'level': 0, 'capacity': 10 }
        toilets['WC_L0_8'] = { 'center': [348.9, 561.9], 'level': 0, 'capacity': 10 }
        toilets['WC_L1_1'] = { 'center': [586.2, 813.7], 'level': 1, 'capacity': 10 }
        toilets['WC_L1_2'] = { 'center': [832.2, 813.7], 'level': 1, 'capacity': 10 }
        toilets['WC_L1_3'] = { 'center': [1159.0, 553.7], 'level': 1, 'capacity': 10 }
        toilets['WC_L1_4'] = { 'center': [1159.0, 362.1], 'level': 1, 'capacity': 10 }
        toilets['WC_L1_5'] = { 'center': [828.7, 107.4], 'level': 1, 'capacity': 10 }
        toilets['WC_L1_6'] = { 'center': [584.4, 107.4], 'level': 1, 'capacity': 10 }
        toilets['WC_L1_7'] = { 'center': [255.9, 367.4], 'level': 1, 'capacity': 10 }
        toilets['WC_L1_8'] = { 'center': [254.1, 557.2], 'level': 1, 'capacity': 10 }
        return toilets

    def _create_stairs(self):
        # Escadas manuais (calibração user)
        # Replicam para Nível 1 automaticamente (levels=[0,1])
        raw_stairs = {
            'STAIRS_1': [274, 476],
            'STAIRS_2': [332, 676],
            'STAIRS_3': [413, 751],
            'STAIRS_4': [744, 864],
            'STAIRS_5': [1078, 753],
            'STAIRS_6': [1218, 483],
            'STAIRS_7': [1162, 287],
            'STAIRS_8': [1080, 212],
            'STAIRS_9': [748, 101],
            'STAIRS_10': [414, 213]
        }
        
        stairs = {}
        for name, loc in raw_stairs.items():
            stairs[name] = {
                'location': loc,
                'levels': [0, 1],
                'type': 'stairs'
            }
        return stairs

    def _create_bins(self):
        bins = {}
        for i in range(12):
            angle = i * 360 / 12
            level = i % 2
            loc = self.ellipse_pos(angle, self.CORRIDOR_MID_X - 20, level=level)
            bins[f'BIN_{i+1}'] = {'location': loc, 'level': level}
        return bins

    # ==================== API PÚBLICA ====================

    def get_random_seat_in_zone(self, zone_name):
        zone = self.seating_zones.get(zone_name)
        if not zone: return None
        
        # Ângulo
        angle = np.random.uniform(zone['angle_start'], zone['angle_end'])
        
        # Raio (Interpolado)
        r_ratio = np.random.uniform(0, 1)
        rx_inner = zone['radius_inner_x']
        rx_outer = zone['radius_outer_x']
        
        rx_final = rx_inner + r_ratio * (rx_outer - rx_inner)
        
        return self.ellipse_pos(angle, rx_final, level=zone['level'])

    def get_zone_for_gate(self, gate_name, level=0):
        gate = self.gates.get(gate_name)
        if not gate: return 'NORTE_L0'
        sector = gate['sector']
        suffix = 'L1' if level == 1 and sector in ['Este', 'Oeste'] else 'L0'
        return f"{sector.upper()}_{suffix}"
    
    def get_nearest_gate(self, position, level=0, target_sector=None):
        min_dist = float('inf')
        nearest = None
        
        # Se target_sector for definido, filtramos apenas gates desse setor
        # Se não encontrar nenhuma (erro), faz fallback para todas
        candidates = self.gates.items()
        if target_sector:
            sector_candidates = {k:v for k,v in self.gates.items() if v['sector'].upper() == target_sector.upper()}
            if sector_candidates:
                candidates = sector_candidates.items()
        
        for name, info in candidates:
            if info['level'] == level:
                dist = np.linalg.norm(np.array(position) - np.array(info['location']))
                if dist < min_dist:
                    min_dist = dist
                    nearest = (name, info)
        return nearest

    def get_nearest_bar(self, position, level):
        return self._get_nearest_generic(self.bars, position, level)
        
    def get_nearest_toilet(self, position, level):
        return self._get_nearest_generic(self.toilets, position, level)

    def get_nearest_stairs(self, position, current_level, target_level=None):
        valid = []
        for name, info in self.stairs.items():
            if current_level in info['levels']:
                if target_level is None or target_level in info['levels']:
                    valid.append((name, info))
        
        if not valid: return None, None
        
        min_dist = float('inf')
        nearest = None
        for name, info in valid:
            dist = np.linalg.norm(np.array(position) - np.array(info['location']))
            if dist < min_dist:
                min_dist = dist
                nearest = (name, info)
        return nearest

    def _get_nearest_generic(self, collection, position, level):
        subset = {k:v for k,v in collection.items() if v['level'] == level}
        if not subset: return None, None
        min_dist = float('inf')
        nearest = None
        for name, info in subset.items():
            dist = np.linalg.norm(np.array(position) - np.array(info['center'] if 'center' in info else info['location']))
            if dist < min_dist:
                min_dist = dist
                nearest = (name, info)
        return nearest

    def is_position_valid(self, x, y, level=0):
        if not (0 <= x <= self.IMG_WIDTH and 0 <= y <= self.IMG_HEIGHT):
            return False
            
        if self.is_position_in_field(x, y, level): # Pass level here
            return False
            
        # Limites exteriores DESATIVADOS a pedido
        return True