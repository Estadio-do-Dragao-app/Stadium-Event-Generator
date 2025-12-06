"""
Cliente MQTT para conectar ao broker Mosquitto.
"""
import json
import time
import paho.mqtt.client as mqtt
from datetime import datetime
import threading
from collections import defaultdict

# TÓPICOS MQTT (mantemos os mesmos)
MQTT_TOPIC_ALL_EVENTS = "stadium/events/all"
MQTT_TOPIC_HEATMAP = "stadium/services/heatmap"
MQTT_TOPIC_QUEUES = "stadium/services/queues"
MQTT_TOPIC_MAINTENANCE = "stadium/services/maintenance"
MQTT_TOPIC_SECURITY = "stadium/services/security"

class StadiumMQTTClient:
    """Cliente MQTT para Mosquitto Broker - mesma interface do antigo"""
    
    def __init__(self, client_id=""):
        self.client_id = client_id or f"client_{int(time.time())}_{id(self)}"
        self.connected = False
        self.message_callback = None
        self.subscribed_topics = set()
        
        # Estatísticas (mantemos compatibilidade)
        self.stats = {
            'messages_published': 0,
            'messages_received': 0,
            'subscriptions': 0
        }
        
        # Configurar cliente Paho com compatibilidade de versão
        try:
            # Para versões mais recentes do paho-mqtt (>= 2.0.0)
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=self.client_id,
                clean_session=True
            )
            print(f"Usando paho-mqtt VERSION2")
        except AttributeError:
            # Para versões mais antigas (< 2.0.0)
            self.client = mqtt.Client(
                client_id=self.client_id,
                clean_session=True
            )
            print(f"Usando paho-mqtt API antiga")
        
        # Configurar callbacks
        self.client.on_connect = self._on_connect_wrapper
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
        self.client.on_subscribe = self._on_subscribe
        
        # Configurações de conexão
        self.broker_host = "localhost"
        self.broker_port = 1883
        self.keepalive = 60
        
        print(f"Cliente MQTT criado: {self.client_id}")
    
    def _on_connect_wrapper(self, client, userdata, flags, rc, *args, **kwargs):
        """Wrapper para compatibilidade com diferentes versões do paho-mqtt"""
        # args[0] pode ser properties para v2.0.0+
        return self._on_connect(client, userdata, flags, rc)
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback quando conecta ao broker"""
        if rc == 0:
            self.connected = True
            print(f"✓ Cliente {self.client_id} conectado ao Mosquitto")
            
            # Resubscribe aos tópicos após reconexão
            for topic in self.subscribed_topics:
                self.client.subscribe(topic)
        else:
            error_messages = {
                1: "Protocol version mismatch",
                2: "Invalid client identifier",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorized"
            }
            print(f"✗ Falha na conexão: {error_messages.get(rc, f'Código: {rc}')}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc, *args, **kwargs):
        """Callback quando desconecta"""
        self.connected = False
        if rc != 0:
            print(f"✗ Conexão perdida com o broker (código: {rc})")
            print("Tentando reconectar em 5 segundos...")
            time.sleep(5)
            try:
                self.client.reconnect()
            except:
                pass
    
    def _on_message(self, client, userdata, message):
        """Callback quando recebe uma mensagem"""
        self.stats['messages_received'] += 1
        if self.message_callback:
            try:
                self.message_callback(self, None, message)
            except Exception as e:
                print(f"Erro no callback: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """Callback quando publica com sucesso"""
        pass
    
    def _on_subscribe(self, client, userdata, mid, granted_qos, *args, **kwargs):
        """Callback quando subscreve com sucesso"""
        pass
    
    def connect(self):
        """Conecta ao broker Mosquitto"""
        try:
            print(f"Conectando ao Mosquitto em {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, self.keepalive)
            self.client.loop_start()
            
            # Aguardar conexão
            for _ in range(10):
                if self.connected:
                    return 0
                time.sleep(0.5)
            
            print("Timeout na conexão")
            return 1
            
        except Exception as e:
            print(f"Erro ao conectar: {e}")
            return 1
    
    def subscribe(self, topic):
        """Subscreve a um tópico"""
        if not self.connected:
            print(f"Cliente {self.client_id} não está conectado")
            return (1, [])
        
        self.stats['subscriptions'] += 1
        result, mid = self.client.subscribe(topic, qos=0)
        self.subscribed_topics.add(topic)
        return (result, [mid])
    
    def publish(self, topic, payload=None, qos=0, retain=False):
        """Publica uma mensagem"""
        if not self.connected:
            print(f"Cliente {self.client_id} não está conectado")
            return 1
        
        if payload is None:
            payload = ""
        
        # Converter para string se necessário
        if isinstance(payload, dict):
            payload = json.dumps(payload, ensure_ascii=False)
        elif not isinstance(payload, str):
            payload = str(payload)
        
        self.stats['messages_published'] += 1
        
        try:
            result = self.client.publish(topic, payload, qos=qos, retain=retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return 0
            else:
                return 1
        except Exception as e:
            print(f"Exceção ao publicar: {e}")
            return 1
    
    def on_message(self, callback):
        """Define callback para mensagens recebidas"""
        self.message_callback = callback
    
    def loop_start(self):
        """Inicia loop (já iniciado no connect)"""
        pass
    
    def loop_stop(self):
        """Para loop"""
        self.client.loop_stop()
    
    def disconnect(self):
        """Desconecta do broker"""
        self.connected = False
        self.client.disconnect()
        print(f"Cliente {self.client_id} desconectado")
    
    def get_stats(self):
        """Retorna estatísticas (para compatibilidade)"""
        return self.stats

# Funções de compatibilidade
broker_instance = None

def get_broker():
    """Função de compatibilidade - retorna um objeto com get_stats()"""
    class MockBroker:
        def get_stats(self):
            return {
                'messages_count': 0,
                'clients_count': 1,
                'subscriptions_count': 0,
                'topics': []
            }
    
    return MockBroker()

# Teste de conexão
def test_connection():
    """Testa conexão com o Mosquitto"""
    print("Testando conexão com Mosquitto...")
    
    def on_message(client, userdata, message):
        print(f"Mensagem recebida: {message.payload.decode()}")
    
    client = StadiumMQTTClient("test_client")
    client.on_message(on_message)
    
    if client.connect() != 0:
        print("✗ Não foi possível conectar ao Mosquitto")
        print("Certifique-se de que o Mosquitto está rodando:")
        print("  net start mosquitto")
        return False
    
    client.subscribe("test/topic")
    time.sleep(1)
    client.publish("test/topic", "Teste de conexão")
    time.sleep(2)
    
    client.disconnect()
    return True

if __name__ == "__main__":
    test_connection()