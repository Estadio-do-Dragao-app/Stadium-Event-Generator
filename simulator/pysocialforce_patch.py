# simulator/pysocialforce_patch.py
import numpy as np
from numba import njit

@njit(cache=True, fastmath=True)
def speeds_fixed(state: np.ndarray) -> np.ndarray:
    n = state.shape[0]
    speeds = np.empty(n, dtype=np.float64)
    for i in range(n):
        vx, vy = state[i, 2], state[i, 3]
        speeds[i] = np.sqrt(vx*vx + vy*vy)
    return speeds

@njit(cache=True, fastmath=True)
def distances_fixed(state: np.ndarray) -> np.ndarray:
    pos = state[:, :2]
    diff = pos[:, np.newaxis, :] - pos[np.newaxis, :, :]
    return np.sqrt(np.sum(diff**2, axis=-1))

# Patch automático
try:
    from pysocialforce.utils import stateutils
    stateutils.speeds = speeds_fixed
    stateutils.distances = distances_fixed
except:
    pass

try:
    from pysocialforce.simulator import SocialForce
    SocialForce.DEFAULT_SPEED_FN = speeds_fixed
except:
    pass

print("Patch Numba-free aplicado → Dragão Simulator TURBO ATIVADO")