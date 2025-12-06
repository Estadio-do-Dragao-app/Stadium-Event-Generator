"""
Teste de Subscrição MQTT para verificar comunicação do simulador
"""
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import sys

# Tópicos a monitorar (os mesmos definidos no sistema)
TOPICS = [
    "stadium/services/queues",      # Filas de bares e WC
    "stadium/services/maintenance", # Manutenção (caixotes)
    "stadium/events/all",           # Todos os eventos
    "stadium/services/heatmap",     # Heatmap
    "stadium/services/security"     # Segurança
]

class MQTTMonitor:
    def __init__(self):
        self.client = None
        self.connected = False
        self.message_count = 0
        self.setup_client()
    
    def setup_client(self):
        """Configura o cliente MQTT"""
        try:
            # Tentar versão nova do paho-mqtt
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except AttributeError:
            # Usar versão antiga
            self.client = mqtt.Client()
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc, *args, **kwargs):
        """Callback quando conecta ao broker"""
        if rc == 0:
            self.connected = True
            print(f"✅ CONECTADO ao broker MQTT em {datetime.now().strftime('%H:%M:%S')}")
            print(f"📡 Subscrevendo aos tópicos...")
            
            # Subscrever a todos os tópicos
            for topic in TOPICS:
                client.subscribe(topic)
                print(f"   • {topic}")
            
            print("\n" + "="*60)
            print("AGUARDANDO MENSAGENS... (Ctrl+C para sair)")
            print("="*60 + "\n")
        else:
            print(f"❌ Falha na conexão: Código {rc}")
    
    def on_disconnect(self, client, userdata, rc, *args, **kwargs):
        """Callback quando desconecta"""
        self.connected = False
        print(f"⚠️  DESCONECTADO do broker (código: {rc})")
        if rc != 0:
            print("Tentando reconectar em 5 segundos...")
            time.sleep(5)
            try:
                client.reconnect()
            except:
                pass
    
    def on_message(self, client, userdata, msg):
        """Callback quando recebe uma mensagem"""
        self.message_count += 1
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        
        try:
            # Tentar parsear como JSON
            payload = json.loads(msg.payload.decode())
            
            # Formatar saída baseada no tipo de evento
            self.print_formatted_message(timestamp, msg.topic, payload)
            
        except json.JSONDecodeError:
            # Se não for JSON, mostrar como texto
            print(f"\n[{timestamp}] 📭 {msg.topic}")
            print(f"   📝 {msg.payload.decode()}")
        
        # Mostrar contador a cada 10 mensagens
        if self.message_count % 10 == 0:
            print(f"\n📊 Total de mensagens recebidas: {self.message_count}")
    
    def print_formatted_message(self, timestamp, topic, data):
        """Imprime mensagem formatada conforme o tipo"""
        event_type = data.get('event_type', 'unknown')
        
        print(f"\n[{timestamp}] 📭 {topic}")
        print(f"   🏷️  Tipo: {event_type}")
        
        if event_type == 'queue_update':
            self.print_queue_event(data)
        elif event_type == 'bin_status':
            self.print_bin_event(data)
        elif event_type == 'bin_overflow_alert':
            self.print_bin_alert(data)
        elif event_type == 'crowd_density':
            self.print_heatmap_event(data)
        elif event_type == 'gate_passage':
            self.print_gate_event(data)
        else:
            # Para outros eventos, mostrar dados principais
            print(f"   📊 Dados: {json.dumps(data, indent=4)[:200]}...")
    
    def print_queue_event(self, data):
        """Imprime evento de fila"""
        loc_type = data.get('location_type', 'UNKNOWN')
        loc_id = data.get('location_id', 'UNKNOWN')
        queue_len = data.get('queue_length', 0)
        capacity = data.get('capacity', 1)
        wait_time = data.get('estimated_wait_min', 0)
        
        # Cor baseada no tamanho da fila
        if queue_len == 0:
            color = "🟢"  # Verde
        elif queue_len < capacity * 0.5:
            color = "🟡"  # Amarelo
        elif queue_len < capacity * 0.8:
            color = "🟠"  # Laranja
        else:
            color = "🔴"  # Vermelho
        
        print(f"   {color} {loc_type}: {loc_id}")
        print(f"   👥 Fila: {queue_len}/{capacity} pessoas")
        print(f"   ⏱️  Espera: {wait_time:.1f} minutos")
        
        if 'location' in data:
            loc = data['location']
            print(f"   📍 Local: ({loc.get('x', 0):.1f}, {loc.get('y', 0):.1f})")
    
    def print_bin_event(self, data):
        """Imprime evento de caixote"""
        bin_id = data.get('bin_id', 'UNKNOWN')
        fill = data.get('fill_percentage', 0)
        
        # Barra de progresso ASCII
        bars = int(fill / 10)
        progress_bar = "█" * bars + "░" * (10 - bars)
        
        if fill < 50:
            color = "🟢"
        elif fill < 85:
            color = "🟡"
        elif fill < 95:
            color = "🟠"
        else:
            color = "🔴"
        
        print(f"   {color} Caixote: {bin_id}")
        print(f"   🗑️  [{progress_bar}] {fill:.1f}%")
        
        if data.get('needs_service', False):
            print(f"   ⚠️  NECESSITA SERVIÇO!")
    
    def print_bin_alert(self, data):
        """Imprime alerta de caixote cheio"""
        print(f"   🔴 ALERTA CRÍTICO: Caixote {data.get('bin_id', 'UNKNOWN')}")
        print(f"   🚨 {data.get('priority', 'high').upper()} - Ação requerida: {data.get('metadata', {}).get('action_required', 'empty_bin')}")
    
    def print_heatmap_event(self, data):
        """Imprime evento de heatmap"""
        total_people = data.get('total_people', 0)
        grid_cells = len(data.get('grid_data', []))
        
        print(f"   🌡️  Heatmap: {total_people} pessoas em {grid_cells} células")
        
        # Mostrar as 3 células mais densas
        grid_data = data.get('grid_data', [])
        if grid_data:
            sorted_cells = sorted(grid_data, key=lambda x: x.get('count', 0), reverse=True)[:3]
            for i, cell in enumerate(sorted_cells):
                print(f"   📍 Top {i+1}: ({cell.get('x', 0):.1f}, {cell.get('y', 0):.1f}) - {cell.get('count', 0)} pessoas")
    
    def print_gate_event(self, data):
        """Imprime evento de portão"""
        gate = data.get('gate_id', 'UNKNOWN')
        direction = data.get('direction', 'entry')
        count = data.get('current_count', 0)
        
        if direction == 'entry':
            arrow = "➡️"
            action = "ENTRADA"
        else:
            arrow = "⬅️"
            action = "SAÍDA"
        
        print(f"   {arrow} Portão {gate}: {action}")
        print(f"   👥 Total atual: {count} pessoas")
    
    def connect(self, host="localhost", port=1883, keepalive=60):
        """Conecta ao broker MQTT"""
        print(f"\n🔗 Conectando ao broker MQTT em {host}:{port}...")
        
        try:
            self.client.connect(host, port, keepalive)
            self.client.loop_start()
            
            # Aguardar conexão
            for _ in range(20):
                if self.connected:
                    return True
                time.sleep(0.5)
            
            print("❌ Timeout na conexão")
            return False
            
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            return False
    
    def run(self):
        """Executa o monitor"""
        print("\n" + "="*60)
        print("MONITOR MQTT - ESTÁDIO DO DRAGÃO")
        print("="*60)
        
        if not self.connect():
            print("\n⚠️  Não foi possível conectar ao broker MQTT")
            print("Certifique-se de que o Mosquitto está rodando:")
            print("  Windows: net start mosquitto")
            print("  Linux: sudo systemctl start mosquitto")
            print("\nTentando novamente em 3 segundos...")
            time.sleep(3)
            
            if not self.connect():
                print("\n❌ Falha definitiva na conexão. Saindo...")
                return
        
        # Manter o programa rodando
        try:
            while True:
                time.sleep(1)
                # Verificar se ainda está conectado
                if not self.connected:
                    print("⏳ Tentando reconectar...")
                    self.connect()
        except KeyboardInterrupt:
            print("\n\n👋 Monitor interrompido pelo utilizador")
        finally:
            self.client.loop_stop()
            if self.connected:
                self.client.disconnect()
            print(f"\n📊 Total de mensagens recebidas: {self.message_count}")
            print("✅ Monitor terminado")

if __name__ == "__main__":
    monitor = MQTTMonitor()
    monitor.run()