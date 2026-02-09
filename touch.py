import cv2
import mediapipe as mp
import numpy as np
import math
import ctypes
import sys

# ===== MOUSE =====
# Constantes para mouse_event
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_ABSOLUTE = 0x8000

# Função para mover o mouse para uma posição absoluta
def move_mouse(x, y):
    # Converte para coordenadas absolutas (0-65535)
    screen_width = ctypes.windll.user32.GetSystemMetrics(0)
    screen_height = ctypes.windll.user32.GetSystemMetrics(1)
    abs_x = int(x * 65535 / screen_width)
    abs_y = int(y * 65535 / screen_height)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE, abs_x, abs_y, 0, 0)

# Clique simples
def click_left():
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

def click_right():
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)

# Segurar botão do mouse
def hold_left():
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)

def release_left():
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

# ===== TECLADO =====
# Map virtual key codes
KEYEVENTF_KEYDOWN = 0x0000
KEYEVENTF_KEYUP = 0x0002

# Exemplo de códigos: A=0x41, B=0x42, C=0x43, ENTER=0x0D, ESC=0x1B
def press_key(hexKeyCode):
    ctypes.windll.user32.keybd_event(hexKeyCode, 0, KEYEVENTF_KEYDOWN, 0)

def release_key(hexKeyCode):
    ctypes.windll.user32.keybd_event(hexKeyCode, 0, KEYEVENTF_KEYUP, 0)

def press_and_release(hexKeyCode):
    press_key(hexKeyCode)
    release_key(hexKeyCode)

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

# ===== AUX =====
def distancia(p1, p2):
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def tamanho_mao(lm):
    return distancia(lm[0], lm[12])

# ===== DETECTAR GESTO =====
def detectar_gesto(lm):
    tamanho = tamanho_mao(lm)
    dist_pulgar_indice = distancia(lm[4], lm[8])
    
    dedos_abertos = 0
    tips = [8, 12, 16, 20]
    for tip in tips:
        if lm[tip].y < lm[tip - 2].y:
            dedos_abertos += 1

    polegar_aberto = lm[4].x < lm[3].x
    if polegar_aberto:
        dedos_abertos += 1

    if dist_pulgar_indice < 0.2 * tamanho:
        return "Pinça"
    if dedos_abertos == 1 and lm[8].y < lm[6].y:
        return "Apontando"
    if dedos_abertos == 0:
        return "Punho"
    if dedos_abertos == 5:
        return "Aberta"

    return f"{dedos_abertos} dedos"

# ===== PONTO ESPECIAL =====
def ponto_especial(gesto, lm, frame):
    h, w, _ = frame.shape
    if gesto == "Apontando":
        x = int(lm[8].x * w)
        y = int(lm[8].y * h)
        return x, y
    x = int(lm[9].x * w)
    y = int(lm[9].y * h)
    return x, y

# ===== CAPTURA DE RESOLUÇÃO MÁXIMA =====
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
# Tentar usar resolução alta
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

# Confirmar resolução final
w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Resolução usada: {w}x{h}")

print("Iniciando detecção...")

# ===== LOOP PRINCIPAL =====
stable_gesto = None
same_count = 0
threshold_frames = 3
pode_fazer = True

with mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
) as hands:

    while True:
        ok, frame = cap.read()
        if not ok:
            continue

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = hands.process(rgb)

        gesto_atual = "Nenhum"
        if res.multi_hand_landmarks:
            for handLms in res.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, handLms, mp_hands.HAND_CONNECTIONS)
                lm = handLms.landmark

                gesto_atual = detectar_gesto(lm)
                px, py = ponto_especial(gesto_atual, lm, frame)

                # Suavização
                if stable_gesto == gesto_atual:
                    same_count += 1
                else:
                    same_count = 0
                    stable_gesto = gesto_atual
                if same_count >= threshold_frames:
                    print(f"Gesto: {stable_gesto} | Posição: ({px},{py},{tamanho_mao(lm)})")
                if stable_gesto == "2 dedos":
                    sys.exit()
                if stable_gesto == "3 dedos":
                    pode_fazer = not(pode_fazer)
                if pode_fazer == True:
                    move_mouse(px, py)
                    if stable_gesto == "Pinça":
                        hold_left()
                    else:
                        release_left()
                    
                    if stable_gesto == "Apontando" and tamanho_mao(lm) > 0.08 :
                        click_left()

cap.release()