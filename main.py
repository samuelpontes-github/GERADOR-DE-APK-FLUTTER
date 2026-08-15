import flet as ft
import time
import threading
import os
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner

def abrir_globo():
    ip_tv = "192.168.15.117"
    port = 5555
    
    def executar_adb():
        try:
            # Gerenciar chaves de autenticação ADB necessárias para o Android
            key_path = "adbkey"
            if not os.path.exists(key_path):
                keygen(key_path)
            
            with open(key_path, 'rb') as f:
                priv = f.read()
            with open(key_path + '.pub', 'rb') as f:
                pub = f.read()
                
            signer = PythonRSASigner(pub, priv)

            # Conecta na TV via ADB
            device = AdbDeviceTcp(ip_tv, port, default_transport_timeout_s=9)
            device.connect(rsa_keys=[signer], auth_timeout_s=5)
            
            # Executa a sequência de automação
            device.shell("am force-stop com.globo.globotv")
            time.sleep(2)
            device.shell("am start -n com.globo.globotv/.maintv.MainActivity")
            time.sleep(6)
            
            # Navegação no app
            device.shell("input keyevent 66")
            time.sleep(8)
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
            print(f"Erro no ADB: {err}")

    threading.Thread(target=executar_adb, daemon=True).start()

def main(page: ft.Page):
    page.title = "Controle de Canais"
    page.bgcolor = "#030712"
    page.window.width = 400
    page.window.height = 700
    page.window.resizable = False
    page.vertical_alignment = ft.MainAxisAlignment.SPACE_BETWEEN
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 24

    def ao_clicar(e, canal):
        if canal == "Globo":
            abrir_globo()

    def criar_card(nome, caminho_imagem, cores, border_color=None):
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(nome, size=18, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Image(src=caminho_imagem, fit="contain", height=70),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8
            ),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=cores
            ),
            border_radius=20,
            padding=10,
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

    grid = ft.GridView(
        runs_count=2,
        max_extent=160,
        spacing=14,
        run_spacing=14,
        controls=[
            criar_card("Globo", "/TV GLOBO LOGO.png", ["#1d4ed8", "#1e40af"], "#60a5fa"),
            criar_card("Record", "/RECORD LOGO.png", ["#1f2937", "#111827"], "#9ca3af"),
            criar_card("SBT", "/LOGO SBT.png", ["#d97706", "#b45309"], "#fbbf24"),
            criar_card("Band", "/BAND LOGO.png", ["#059669", "#065f46"], "#34d399"),
        ],
        expand=True
    )

    footer = ft.Text("Controle Remoto de Canais", color="#475569", size=11)
    page.add(header, grid, footer)

ft.app(target=main, assets_dir="assets")
