import flet as ft
import subprocess
import time
import threading

def abrir_globo():
    # IP da TV / dispositivo ADB
    ip_tv = "192.168.15.117"
    
    def executar_adb():
        print("Iniciando automação da Globo...")
        
        # Conecta no dispositivo
        subprocess.run(f"adb connect {ip_tv}", shell=True)
        
        # 1. Encerra e abre o aplicativo do zero
        subprocess.run("adb shell am force-stop com.globo.globotv", shell=True)
        time.sleep(2)
        subprocess.run("adb shell am start -n com.globo.globotv/.maintv.MainActivity", shell=True)
        
        # 2. Espera a tela do perfil carregar
        time.sleep(6)
        
        # 3. Confirma o perfil (Sidney P.)
        subprocess.run("adb shell input keyevent 66", shell=True)
        
        # 4. Espera a Home carregar totalmente
        time.sleep(8)
        
        # 5. Três cliques para a esquerda para garantir a entrada e expansão no menu lateral
        subprocess.run("adb shell input keyevent 21", shell=True)
        time.sleep(0.2)
        subprocess.run("adb shell input keyevent 21", shell=True)
        time.sleep(0.2)
        subprocess.run("adb shell input keyevent 21", shell=True)
        time.sleep(1)
        
        # 6. Clique para baixo (desce do Início para 'Agora na TV')
        subprocess.run("adb shell input keyevent 20", shell=True)
        time.sleep(1)
        
        # 7. Clique em OK para abrir o Agora na TV
        subprocess.run("adb shell input keyevent 66", shell=True)
        print("Automação da Globo concluída!")

    # Executa em uma Thread separada para não travar a tela do app enquanto espera os time.sleep
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
        print(f"Comando enviado: {canal}")
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

    # Header
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

    # Grid de Canais
    grid = ft.GridView(
        runs_count=2,
        max_extent=160,
        spacing=14,
        run_spacing=14,
        controls=[
            criar_card("Globo", "TV GLOBO LOGO.png", ["#1d4ed8", "#1e40af"], "#60a5fa"),
            criar_card("Record", "RECORD LOGO.png", ["#1f2937", "#111827"], "#9ca3af"),
            criar_card("SBT", "LOGO SBT.png", ["#d97706", "#b45309"], "#fbbf24"),
            criar_card("Band", "BAND LOGO.png", ["#059669", "#065f46"], "#34d399"),
        ],
        expand=True
    )

    # Footer
    footer = ft.Text("Controle Remoto de Canais", color="#475569", size=11)

    page.add(header, grid, footer)

ft.app(target=main)