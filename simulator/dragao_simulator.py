# simulator/dragao_simulator.py
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm
import cv2
from pysocialforce import Simulator

# ------------------------------------------------------------------
# PATCH Numba já aplicado no __init__.py ou no patch separado
# ------------------------------------------------------------------

def run_dragao_simulation():
    print("DRAGÃO SIMULATOR 2025")
    print("Estádio do Dragão – Evacuação Total")

    # Configuração
    FPS = 25
    DT = 1.0 / FPS
    STEPS = 6000
    RECORD = True
    VIDEO_OUT = "../outputs/dragao_evacuacao_2025.mp4"   # caminho correto

    # Paredes do estádio (aproximação realista)
    walls = [
        [[-62, -42], [62, -42]],   # fundo
        [[-62,  42], [62,  42]],   # topo
        [[-62, -42], [-62,  42]],  # esquerda
        [[ 62, -42], [ 62,  42]],  # direita
    ]

    # Saídas (áreas onde as pessoas desaparecem)
    exits = [
        [-30,  44, -20,  52], [20,  44,  30,  52],   # topo
        [-30, -52, -20, -44], [20, -52,  30, -44],   # fundo
        [-66, -20, -58,  20], [58, -20,  66,  20],   # laterais
    ]

    # 12 000 adeptos (podes subir para 50 000 sem problemas)
    np.random.seed(1889)          # ano do FC Porto
    n_pedestrians = 12000

    pos = np.zeros((n_pedestrians, 2))
    for i in range(n_pedestrians):
        zone = np.random.randint(0, 5)
        if zone == 0:    # bancada topo
            pos[i] = [np.random.uniform(-55, 55), np.random.uniform(32, 40)]
        elif zone == 1:  # bancada fundo
            pos[i] = [np.random.uniform(-55, 55), np.random.uniform(-40, -32)]
        elif zone == 2:  # bancada esquerda
            pos[i] = [np.random.uniform(-60, -52), np.random.uniform(-30, 30)]
        elif zone == 3:  # bancada direita
            pos[i] = [np.random.uniform(52, 60), np.random.uniform(-30, 30)]
        else:            # relvado / túnel
            pos[i] = np.random.uniform([-15, -15], [15, 15])

    # Estado inicial: [x, y, vx, vy, dx, dy]
    state = np.zeros((n_pedestrians, 6))
    state[:, :2] = pos
    # Velocidade inicial pequena e aleatória (shape correto!)
    state[:, 2:4] = np.random.normal(0, 0.3, size=(n_pedestrians, 2))

    # Simulador
    sim = Simulator(
        initial_state=state,
        walls=walls,
        exit_areas=exits,
        step_width=DT,
        max_speed=3.8,
        tau=0.5,
        force_factor_person=2.5,
    )

    # Vídeo
    if RECORD:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(VIDEO_OUT, fourcc, FPS, (1280, 720))

    plt.ion()
    fig, ax = plt.subplots(figsize=(12.8, 7.2))

    for step in tqdm(range(STEPS), desc="Evacuação"):
        sim.step()

        if step % 4 == 0 or step == STEPS - 1:
            ax.clear()
            ax.set_xlim(-70, 70)
            ax.set_ylim(-55, 55)
            ax.set_facecolor("#003087")          # azul do FC Porto
            ax.set_title(f"Estádio do Dragão | {step*DT:.0f}s | Adeptos restantes: {len(sim.state):,}",
                         color="white", fontsize=16)

            # Desenha paredes
            for wall in walls:
                x, y = zip(*wall)
                ax.plot(x, y, color="white", linewidth=4)

            # Desenha saídas
            for e in exits:
                rect = plt.Rectangle((e[0], e[1]), e[2]-e[0], e[3]-e[1],
                                     facecolor="lime", alpha=0.6)
                ax.add_patch(rect)

            # Desenha pessoas
            if len(sim.state) > 0:
                ax.scatter(sim.state[:, 0], sim.state[:, 1],
                           c="gold", s=12, edgecolor="black", linewidth=0.3, alpha=0.9)

            ax.axis("off")
            fig.canvas.draw()
            plt.pause(0.001)

            if RECORD:
                buf = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
                buf = buf.reshape(fig.canvas.get_width_height()[::-1] + (3,))
                out.write(cv2.cvtColor(buf, cv2.COLOR_RGB2BGR))

    if RECORD:
        out.release()
        print(f"\nVídeo guardado em: {VIDEO_OUT}")

    plt.ioff()
    plt.close()
    print("Evacuação concluída – ANDA O DRAGÃO!")


if __name__ == "__main__":
    run_dragao_simulation()