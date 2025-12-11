# Docker Setup Guide

This project includes Docker Compose configuration for easy deployment.

## Prerequisites

- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)

## Quick Start

### 1. Build and Start Services

```bash
docker-compose up --build
```

This will:
- Start a Mosquitto MQTT broker on port 1883
- Build and run the stadium simulator
- Create necessary volumes for data persistence

### 2. Run in Detached Mode

```bash
docker-compose up -d
```

### 3. View Logs

```bash
# All services
docker-compose logs -f

# Simulator only
docker-compose logs -f simulator

# Mosquitto only
docker-compose logs -f mosquitto
```

### 4. Stop Services

```bash
docker-compose down
```

### 5. Stop and Remove Volumes

```bash
docker-compose down -v
```

## Services

### Mosquitto MQTT Broker
- **Port**: 1883 (MQTT)
- **Port**: 9001 (WebSocket)
- **Config**: `./mosquitto/config/mosquitto.conf`
- **Data**: Persisted in `./mosquitto/data/`
- **Logs**: Persisted in `./mosquitto/log/`

### Stadium Simulator
- **Depends on**: Mosquitto
- **Environment Variables**:
  - `MQTT_BROKER_HOST=mosquitto`
  - `MQTT_BROKER_PORT=1883`
- **Volumes**:
  - `./outputs:/app/outputs` - Simulation output files
  - `./simulator:/app/simulator` - Live code updates

## Configuration

### Mosquitto MQTT Broker

Edit `mosquitto/config/mosquitto.conf` to customize MQTT broker settings.

Default configuration:
- Anonymous connections allowed
- Persistence enabled
- Logs to both file and stdout

### Environment Variables

Create a `.env` file in the project root to override defaults:

```env
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=1883
```

## Development

### Running Locally (outside Docker)

The code still works locally without Docker. It will default to `localhost:1883`:

```bash
python simulator/dragao_simulator.py
```

### Rebuild After Code Changes

```bash
docker-compose up --build
```

### Access Running Container

```bash
docker exec -it stadium-simulator bash
```

## Troubleshooting

### Mosquitto won't start
- Check if port 1883 is already in use
- Verify `mosquitto/config/mosquitto.conf` syntax

### Simulator can't connect
- Ensure Mosquitto is running: `docker-compose ps`
- Check logs: `docker-compose logs mosquitto`

### Permission issues
- On Linux/Mac, you may need to adjust folder permissions:
  ```bash
  chmod -R 755 mosquitto/
  ```

## Network

All services run on a dedicated Docker network (`stadium-network`) for isolated communication.
