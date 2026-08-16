import flet as ft
import time
import threading
import os
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner

IP_TV = "192.168.15.117"
PORT = 5555

def obter_signer():
    key_path = "adbkey"
    if not os.path.exists(key_path):
        keygen(key_path)
    
    with open(key_path, 'rb') as f:
        priv = f.read()
    with open(key_path + '.pub', 'rb') as f:
        pub = f.read()
        
    return PythonRSASigner(pub, priv)

def abrir_globo():
    def executar_adb():
        try:
            signer = obter_signer()
            device = AdbDeviceTcp(IP_TV, PORT, default_transport_timeout_s=9)
            device.connect(rsa_keys=[signer], auth_timeout_s=5)
            
            device.shell("am force-stop com.globo.globotv")
            time.sleep(2)
            device.shell("am start -n com.globo.globotv/.maintv.MainActivity")
            time.sleep(15)
            
            device.shell("input keyevent 66")
            time.sleep(6)
            device.shell("input keyevent 21")
            time.sleep(0.2)
            device.shell("input keyevent 21")
            time.sleep(0.2)
            device.shell("input keyevent 21")
            time.sleep(1)
            device.shell("input keyevent 20")
            time.sleep(1)
            device.shell("input keyevent 66")
            
            device.close()
        except Exception as err:
            print(f"Erro no ADB (Globo): {err}")

    threading.Thread(target=executar_adb, daemon=True).start()

def executar_maxnet_tv(cliques_direita):
    """Executa a automação padrão do MaxNet TV variando a quantidade de cliques para a direita"""
    def executar_adb():
        try:
            signer = obter_signer()
            device = AdbDeviceTcp(IP_TV, PORT, default_transport_timeout_s=9)
            device.connect(rsa_keys=[signer], auth_timeout_s=5)
            
            # Parar e abrir o MaxNet TV
            device.shell("am force-stop com.exploudapps.maxnettv")
            time.sleep(1)
            device.shell("am start -n com.exploudapps.maxnettv/.ui.activities.SplashActivity")
            time.sleep(8)
            
            # Clique OK
            device.shell("input keyevent 66")
            time.sleep(10)
            
            # Clique Cima -> OK
            device.shell("input keyevent 19")
            time.sleep(1)
            device.shell("input keyevent 66")
            time.sleep(3)
            
            # 3 Cliques Cima -> OK
            for _ in range(3):
                device.shell("input keyevent 19")
                time.sleep(1)
            device.shell("input keyevent 66")
            time.sleep(7)
            
            # Clique Esquerda
            device.shell("input keyevent 21")
            time.sleep(2)
            
            # NAVEGAÇÃO DE ACORDO COM O CANAL (Ajustado exatamente com seus arquivos .bat)
            for _ in range(cliques_direita):
                device.shell("input keyevent 22")
                time.sleep(1)
                
            # Seleciona o canal
            device.shell("input keyevent 66")
            time.sleep(5)
            device.shell("input keyevent 66")
            time.sleep(5)
            
            device.close()
        except Exception as err:
            print(f"Erro no ADB (MaxNet TV): {err}")

    threading.Thread(target=executar_adb, daemon=True).start()

# Chamadas ajustadas conforme os arquivos .bat
def abrir_band():
    executar_maxnet_tv(cliques_direita=2)

def abrir_record():
    executar_maxnet_tv(cliques_direita=3)

def abrir_sbt():
    executar_maxnet_tv(cliques_direita=1)

def abrir_redetv():
    executar_maxnet_tv(cliques_direita=4)


def main(page: ft.Page):
    page.title = "Controle de Canais"
    page.bgcolor = "#030712"
    page.window.width = 400
    page.window.height = 700
    page.window.resizable = False
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    page.scroll = ft.ScrollMode.AUTO
    page.padding = ft.Padding(20, 48, 20, 16)

    def ao_clicar(e, canal):
        if canal == "Globo":
            abrir_globo()
        elif canal == "Record":
            abrir_record()
        elif canal == "SBT":
            abrir_sbt()
        elif canal == "Band":
            abrir_band()
        elif canal == "RedeTV":
            abrir_redetv()

    def criar_card(nome, caminho_imagem, cores, border_color=None):
        return ft.Container(
            width=165,
            height=160,
            content=ft.Column(
                controls=[
                    ft.Text(nome, size=16, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Image(src=caminho_imagem, fit="contain", expand=True),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6
            ),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=cores
            ),
            border_radius=20,
            padding=12,
            on_click=lambda e: ao_clicar(e, nome),
            border=ft.Border.all(2, border_color) if border_color else None,
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color="#000000")
        )

    header = ft.Column(
        controls=[
            ft.Row(
                [
                    ft.Icon(ft.Icons.TV_ROUNDED, color="#38bdf8", size=32),
                    ft.Text("Escolha o Canal", size=22, weight=ft.FontWeight.BOLD, color="white")
                ],
                alignment=ft.MainAxisAlignment.CENTER
            ),
            ft.Text("Toque no canal que deseja assistir", color="#94a3b8", size=13)
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=4
    )

    grid = ft.Row(
        wrap=True,
        spacing=14,
        run_spacing=14,
        alignment=ft.MainAxisAlignment.START,
        controls=[
            criar_card("Globo", "/TV GLOBO LOGO.png", ["#1d4ed8", "#1e40af"], "#60a5fa"),
            criar_card("Record", "/RECORD LOGO.png", ["#1f2937", "#111827"], "#9ca3af"),
            criar_card("SBT", "/LOGO SBT.png", ["#d97706", "#b45309"], "#fbbf24"),
            criar_card("Band", "/BAND LOGO.png", ["#059669", "#065f46"], "#34d399"),
            criar_card("RedeTV", "/LOGO REDETV.png", ["#1f2937", "#111827"], "#9ca3af"),
        ]
    )

    footer = ft.Container(
        content=ft.Text("Controle Remoto de Canais", color="#475569", size=11),
        margin=ft.Margin(0, 10, 0, 10)
    )

    page.add(header, ft.Container(height=16), grid, footer)

ft.app(target=main, assets_dir="assets")
