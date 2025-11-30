# programa só para conseguir as coordenadas na image do mapa
import matplotlib.pyplot as plt
import numpy as np

def click_to_get_coordinates():
    print("=== CLICK COORDINATE FINDER ===")
    print("1. Carrega na imagem para ver coordenadas")
    print("2. Carrega 'q' para sair")
    print("3. As coordenadas aparecem no terminal")
    
    # Cria uma imagem do estádio ou grid
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Desenha um grid para referência
    ax.set_xlim(-70, 70)
    ax.set_ylim(-55, 55)
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color='black', linewidth=0.5)
    ax.axvline(0, color='black', linewidth=0.5)
    ax.set_title("CLICA EM QUALQUER PONTO PARA VER COORDENADAS\nCoordenadas aparecem no terminal", fontsize=14)
    ax.set_xlabel("Coordenada X")
    ax.set_ylabel("Coordenada Y")
    
    # Tenta carregar a imagem do estádio se existir
    try:
        from matplotlib.image import imread
        stadium_img = imread("map_stadium.png")
        ax.imshow(stadium_img, extent=[-70, 70, -55, 55])
        print("Imagem do estádio carregada!")
    except:
        print("Sem imagem - usando grid de referência")
        # Desenha áreas de referência
        stadium = plt.Rectangle((-65, -50), 130, 100, fill=False, edgecolor='blue', linewidth=2)
        field = plt.Ellipse((0, 0), 70, 40, fill=False, edgecolor='green', linewidth=2)
        ax.add_patch(stadium)
        ax.add_patch(field)
    
    # Função para capturar cliques
    coordinates = []
    
    def onclick(event):
        if event.xdata is not None and event.ydata is not None:
            x, y = round(event.xdata, 1), round(event.ydata, 1)
            coordinates.append((x, y))
            print(f" Coordenada: [{x}, {y}]")
            
            # Marca o ponto no gráfico
            ax.plot(x, y, 'ro', markersize=8)
            ax.text(x + 2, y + 2, f'[{x}, {y}]', fontsize=9)
            plt.draw()
    
    # Liga o evento de clique
    fig.canvas.mpl_connect('button_press_event', onclick)
    plt.show()
    
    # Mostra todas as coordenadas no final
    if coordinates:
        print(f"\n TODAS AS COORDENADAS:")
        for i, (x, y) in enumerate(coordinates, 1):
            print(f"  Ponto {i}: [{x}, {y}]")

if __name__ == "__main__":
    click_to_get_coordinates()