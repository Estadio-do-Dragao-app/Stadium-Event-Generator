"""
Define a estrutura completa do estádio usando dados da API do Node (Map-Service).
Integrado com sistema de coordenadas do backend (500, 400 Center).
"""
import numpy as np
import math
import requests
import sys

class StadiumBoundaries:
    def __init__(self):
        # ==================== CONFIGURAÇÃO VIA API ====================
        print("Inicializando StadiumBoundaries via API...")
        
        self.API_URL = "http://localhost:8001"
        self.nodes = []
        
        # Estruturas de dados
        self.seating_zones = {}
        self.gates = {}
        self.bars = {}
        self.toilets = {}
        self.stairs = {}
        self.bins = {} # Não tenho bins na API, vou gerar ou ignorar
        self.seats_by_block = {}
        
        # Center defaults (API uses 500, 400 typically)
        self.CENTER_X = 500
        self.CENTER_Y = 400
        self.FIELD_RADIUS_X = 150 # Estimated field radius
        self.IMG_WIDTH = 1481 # Manter compatibilidade com imagem (mas coords serão API)
        self.IMG_HEIGHT = 945
        
        # Tentar carregar dados
        try:
            self._fetch_data_from_api()
        except Exception as e:
            print(f"ERRO CRÍTICO ao carregar API: {e}")
            print("Verifique se o backend está a correr em localhost:8000")
            print("⚠️ ATIVANDO MODO FALLBACK (DADOS SINTÉTICOS) ⚠️")
            self._create_fallback_data()
            
        if not self.seating_zones:
             print("⚠️ API retornou dados vazios. ATIVANDO MODO FALLBACK.")
             self._create_fallback_data()
        
        print(f"Estrutura carregada: {len(self.seating_zones)} zonas, {len(self.gates)} gates")

    def _fetch_data_from_api(self):
        resp = requests.get(f"{self.API_URL}/nodes")
        resp.raise_for_status()
        self.nodes = resp.json()
        
        # Processar nodes
        for node in self.nodes:
            ntype = node.get('type')
            
            if ntype == 'gate':
                self._process_gate(node)
                
            elif ntype in ['food', 'bar']:
                self._process_poi(node, self.bars)
                
            elif ntype == 'restroom':
                self._process_poi(node, self.toilets)
                
            elif ntype in ['stairs', 'ramp']:
                self._process_stairs(node)
                
            elif ntype == 'seat':
                self._process_seat(node)
                
        # Pós-processamento de zonas (calcular ângulos)
        self._finalize_zones()

    def _process_gate(self, node):
        # API ID: Gate-21 -> Name: GATE_21
        # Simulator expects keys like GATE_21
        try:
            num = int(node['id'].split('-')[1])
        except:
            num = 0
            
        gate_name = f"GATE_{num}"
        
        # Setor aproximado pelo ângulo
        angle = self.get_angle_from_position(node['x'], node['y'])
        
        if 45 <= angle < 135: sector = 'Norte'
        elif 135 <= angle < 225: sector = 'Este' # Inverted in API vs Standard? Let's trust Angle
        elif 225 <= angle < 315: sector = 'Sul'
        else: sector = 'Oeste'
        
        self.gates[gate_name] = {
            'location': [node['x'], node['y']],
            'level': node['level'],
            'gate_number': num,
            'sector': sector,
            'capacity': node.get('num_servers', 4) * 10
        }

    def _process_poi(self, node, collection):
        # API has unique IDs. Collection key can be ID.
        collection[node['id']] = {
            'center': [node['x'], node['y']],
            'level': node['level'],
            'capacity': 20,
            'name': node.get('name')
        }

    def _process_stairs(self, node):
        # Stairs/Ramps
        # Simulator expects pairs? Or just locations. 
        # API defines one node per level.
        self.stairs[node['id']] = {
            'location': [node['x'], node['y']],
            'levels': [node['level']], # Actually it connects levels, but node is at one level
            'type': node['type']
        }
        
    def _process_seat(self, node):
        # Group by block (Zone)
        # Block format in API: "Norte-T0"
        block = node.get('block')
        if not block: return
        
        # Nome da zona compatível com simulator?
        # Simulator usa 'NORTE_L0', 'ESTE_L1' etc.
        # Vamos tentar mapear Block -> Zone Name
        # Block Norte-T0 -> NORTE_L0
        parts = block.split('-')
        if len(parts) >= 2:
            sector_name = parts[0].upper()
            tier = parts[1] # T0, T1
            if tier == 'T0': level_suffix = 'L0'
            elif tier == 'T1': level_suffix = 'L1'
            else: level_suffix = 'L0'
            
            zone_name = f"{sector_name}_{level_suffix}"
            
            if zone_name not in self.seats_by_block:
                self.seats_by_block[zone_name] = []
                # Init zone metadata defaults
                level = 1 if 'L1' in zone_name else 0
                self.seating_zones[zone_name] = {
                    'type': 'elliptical_sector',
                    'level': level,
                    'sector': sector_name.capitalize(),
                    'seats': [],
                    # Placeholders for geometric triggers
                    'angle_start': 0, 'angle_end': 0,
                    'radius_inner_x': 9999, 'radius_outer_x': 0
                }
            
            self.seats_by_block[zone_name].append(node)
            self.seating_zones[zone_name]['seats'].append(node)

    def _finalize_zones(self):
        # Compute bounding boxes (angles/radii) for each zone based on seats
        for name, zone in self.seating_zones.items():
            seats = zone['seats']
            if not seats: continue
            
            angles = []
            radii = []
            
            cx, cy = self.get_center_for_level(zone['level'])
            
            for s in seats:
                dx = s['x'] - cx
                dy = s['y'] - cy
                r = math.sqrt(dx*dx + dy*dy)
                ang = math.degrees(math.atan2(dy, dx))
                if ang < 0: ang += 360
                
                radii.append(r)
                angles.append(ang)
                
            zone['radius_inner_x'] = min(radii) if radii else 0
            zone['radius_outer_x'] = max(radii) if radii else 0
            
            # Angle handling is tricky due to wraparound (0/360)
            # Simplistic approach: min/max
            # If zone crosses 0, this logic breaks.
            # Check gap.
            sorted_angles = sorted(angles)
            max_gap = 0
            gap_start = 0
            
            for i in range(len(sorted_angles)):
                curr = sorted_angles[i]
                next_a = sorted_angles[(i+1)%len(sorted_angles)]
                diff = (next_a - curr) % 360
                if diff > max_gap:
                    max_gap = diff
                    gap_start = curr
            
            # The zone is the complement of the gap
            if max_gap > 300: # Probably valid contiguous zone in the ~60deg remaining
                 # Normal case (no wrap or small zone)
                 zone['angle_start'] = sorted_angles[0]
                 zone['angle_end'] = sorted_angles[-1]
            else:
                 # Wraparound likely?
                 # Start is Next of Gap
                 start_angle = (gap_start + max_gap) % 360
                 end_angle = gap_start
                 # Normalize for dragao_simulator which might expect start < end or specific range
                 # Simulator uses: ang = (start + end)/2. If wraparound, logic needs care.
                 # Let's ensure start < end by adding 360 to end if needed
                 if end_angle < start_angle:
                     end_angle += 360
                 zone['angle_start'] = start_angle
                 zone['angle_end'] = end_angle

    def _create_fallback_data(self):
        """Creates dummy data so the simulator can run without API"""
        print("Criando dados de fallback...")
        self.seating_zones = {}
        self.seats_by_block = {}
        sectors = ['Norte', 'Sul', 'Este', 'Oeste']
        for i, sector in enumerate(sectors):
            # Level 0
            z0 = f"{sector.upper()}_L0"
            self.seating_zones[z0] = {
                'level': 0, 'sector': sector, 'seats': [],
                'angle_start': i*90, 'angle_end': (i+1)*90,
                'radius_inner_x': 100, 'radius_outer_x': 140
            }
            # Generate dummy seats
            for _ in range(20):
                ang = np.random.uniform(i*90, (i+1)*90)
                pos = self.ellipse_pos(ang, np.random.uniform(100, 140), level=0)
                self.seats_by_block.setdefault(z0, []).append({'x': pos[0], 'y': pos[1]})
                
            # Level 1
            z1 = f"{sector.upper()}_L1"
            self.seating_zones[z1] = {
                'level': 1, 'sector': sector, 'seats': [],
                'angle_start': i*90, 'angle_end': (i+1)*90,
                'radius_inner_x': 100, 'radius_outer_x': 140
            }
             # Generate dummy seats
            for _ in range(20):
                ang = np.random.uniform(i*90, (i+1)*90)
                pos = self.ellipse_pos(ang, np.random.uniform(100, 140), level=1)
                self.seats_by_block.setdefault(z1, []).append({'x': pos[0], 'y': pos[1]})

        # Create Gates
        for i in range(1, 9):
            name = f"GATE_{i}"
            angle = (i-1) * 45
            pos = self.ellipse_pos(angle, 200, level=0)
            self.gates[name] = {
                'location': pos, 'level': 0, 'gate_number': i, 'sector': 'Norte'
            }

        # Create Stairs
        self.stairs['STAIR_1'] = {'location': self.ellipse_pos(45, 180, level=0), 'levels': [0, 1]}
        
        # Create POIs
        self.bars['BAR_1'] = {'center': self.ellipse_pos(0, 180, level=0), 'level': 0}
        self.toilets['WC_1'] = {'center': self.ellipse_pos(180, 180, level=0), 'level': 0}

    # ==================== HELPERS ====================

    def get_center_for_level(self, level):
        return self.CENTER_X, self.CENTER_Y

    def ellipse_pos(self, angle_deg, radius_x, radius_y=None, level=0):
        # Generic helper still used by simulator for fire/bins
        cx, cy = self.get_center_for_level(level)
        rad = math.radians(angle_deg)
        # Assuming circular or API aspect ratio (nodes define validity)
        # Using pure radius_x if y not provided
        r_y = radius_y if radius_y else radius_x
        
        x = cx + radius_x * math.cos(rad)
        y = cy + r_y * math.sin(rad)
        return [x, y]
    
    def is_position_in_field(self, x, y, level=0):
         # Simple radius check against Field
         cx, cy = self.get_center_for_level(level)
         dist = math.sqrt((x-cx)**2 + (y-cy)**2)
         return dist < self.FIELD_RADIUS_X

    def is_position_valid(self, x, y, level=0):
        # Basic bounds and field check
        # We don't have a full navmesh loaded here (expensive), 
        # so we rely on loose bounds logic + Field exclusion
        if self.is_position_in_field(x, y, level):
            return False
            
        # Optional: Check if too far?
        cx, cy = self.get_center_for_level(level)
        dist = math.sqrt((x-cx)**2 + (y-cy)**2)
        if dist > 600: # Arbitrary max radius based on map (~500 width)
            return False
            
        return True

    def get_angle_from_position(self, x, y, level=0):
        cx, cy = self.get_center_for_level(level)
        dx = x - cx
        dy = y - cy
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0: angle += 360
        return angle

    # ==================== API PÚBLICA (Simulator Calls) ====================

    def get_random_seat_in_zone(self, zone_name):
        seats = self.seats_by_block.get(zone_name)
        if not seats: return [0,0]
        
        s = seats[np.random.randint(len(seats))]
        return [s['x'], s['y']]

    def get_nearest_gate(self, position, level=0, target_sector=None):
        min_dist = float('inf')
        nearest = None
        
        candidates = self.gates.items()
        
        for name, info in candidates:
             # Basic filtering by sector if needed?
             # Simulator logic:
             # if target_sector: ...
             # We just iterate all for now unless heavily requested
             d = math.sqrt((position[0]-info['location'][0])**2 + (position[1]-info['location'][1])**2)
             if d < min_dist:
                 min_dist = d
                 nearest = (name, info)
        return nearest

    def get_nearest_bar(self, position, level):
        return self._get_nearest_generic(self.bars, position, level)
        
    def get_nearest_toilet(self, position, level):
        return self._get_nearest_generic(self.toilets, position, level)

    def get_nearest_stairs(self, position, current_level, target_level=None):
        # Find closest stair node
        return self._get_nearest_generic(self.stairs, position, current_level)

    def _get_nearest_generic(self, collection, position, level):
        # Helper
        min_dist = float('inf')
        nearest = None, None
        
        for name, info in collection.items():
            # Check level? POIs have strict levels. Stairs connect levels.
            # Assuming 'levels' list or 'level' int
            node_levels = info.get('levels', [info.get('level')])
            
            if level in node_levels or level is None:
                # Use 'center' or 'location'
                loc = info.get('location', info.get('center'))
                if not loc: continue
                
                d = math.sqrt((position[0]-loc[0])**2 + (position[1]-loc[1])**2)
                if d < min_dist:
                    min_dist = d
                    nearest = (name, info)
        return nearest

    def get_zone_for_gate(self, gate_name, level=0):
        # Heuristic mapping
        gate = self.gates.get(gate_name)
        if not gate: return 'NORTE_L0'
        sector = gate['sector']
        suffix = 'L1' if level == 1 and sector in ['Este', 'Oeste'] else 'L0'
        return f"{sector.upper()}_{suffix}"