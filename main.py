import flet as ft
import time
import threading
import os
from googleapiclient.discovery import build
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner

# --- CONFIGURAÇÕES E CHAVES ---
YOUTUBE_API_KEY = "AIzaSyDV_xrdplJuun_HcFivLnIW-KPgpldb5pQ"
IP_TV = "192.168.15.117"
PORT = 5555
CHANNEL_ID_CAZETV = "UClXz2Nus3ASfscB60dC5gxQ"

youtube_client = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)


def abrir_canal_cazetv_na_tv():
    """Comanda a TV via ADB para abrir a página da CazéTV diretamente no YouTube Oficial, aguarda o carregamento e navega para baixo."""
    def worker():
        try:
            print("Abrindo canal da CazéTV na TV via YouTube Oficial...")
            key_path = "adbkey"
            if not os.path.exists(key_path):
                keygen(key_path)

            with open(key_path, 'rb') as f:
                priv = f.read()
            with open(key_path + '.pub', 'rb') as f:
                pub = f.read()

            signer = PythonRSASigner(pub, priv)
            device = AdbDeviceTcp(IP_TV, PORT, default_transport_timeout_s=9)
            device.connect(rsa_keys=[signer], auth_timeout_s=5)

            url_canal = f"https://www.youtube.com/channel/{CHANNEL_ID_CAZETV}"
            comando_abrir = f'am start -a android.intent.action.VIEW -d "{url_canal}" com.google.android.youtube.tv'
            device.shell(comando_abrir)
            
            # Aguarda 8 segundos para o canal carregar
            time.sleep(8)
            
            # Envia a seta para baixo (KEYCODE_DPAD_DOWN = 20)
            device.shell("input keyevent 20")

            device.close()
        except Exception as err:
            print(f"Erro ao abrir canal na TV: {err}")

    threading.Thread(target=worker, daemon=True).start()


def obter_lives_cazetv_api():
    """Busca diretamente na API do YouTube todas as transmissões ao vivo ativas no canal da CazéTV."""
    lives = []
    try:
        print("Consultando lives ativas via API do YouTube...")
        request = youtube_client.search().list(
            part="snippet",
            channelId=CHANNEL_ID_CAZETV,
            type="video",
            eventType="live",
            maxResults=5
        )
        response = request.execute()
        items = response.get('items', [])

        for item in items:
            video_id = item['id']['videoId']
            titulo = item['snippet']['title']
            url_video = f"https://www.youtube.com/watch?v={video_id}"

            if titulo.upper() != "CAZÉTV LIVE":
                lives.append({
                    "titulo": titulo,
                    "url": url_video
                })
        return lives
    except Exception as e:
        print(f"Erro na API do YouTube: {e}")
        return []


def abrir_video_na_tv(url_video):
    """Abre a URL enviada diretamente no aplicativo do YouTube Oficial da TV via ADB."""
    def worker():
        try:
            print(f"🔴 Abrindo jogo selecionado na TV: {url_video}")
            key_path = "adbkey"
            if not os.path.exists(key_path):
                keygen(key_path)

            with open(key_path, 'rb') as f:
                priv = f.read()
            with open(key_path + '.pub', 'rb') as f:
                pub = f.read()

            signer = PythonRSASigner(pub, priv)
            device = AdbDeviceTcp(IP_TV, PORT, default_transport_timeout_s=9)
            device.connect(rsa_keys=[signer], auth_timeout_s=5)

            device.shell(f'am start -a android.intent.action.VIEW -d "{url_video}" com.google.android.youtube.tv')
            device.close()
            print("Transmissão iniciada!")
        except Exception as err:
            print(f"Erro ao abrir vídeo via ADB: {err}")

    threading.Thread(target=worker, daemon=True).start()


def abrir_globo():
    def executar_adb():
        try:
            key_path = "adbkey"
            if not os.path.exists(key_path):
                keygen(key_path)

            with open(key_path, 'rb') as f:
                priv = f.read()
            with open(key_path + '.pub', 'rb') as f:
                pub = f.read()

            signer = PythonRSASigner(pub, priv)
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
            print(f"Erro no ADB: {err}")

    threading.Thread(target=executar_adb, daemon=True).start()


def abrir_redetv():
    pass


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
    
    # Impede que a tela do celular apague/desligue enquanto o app estiver visível
    page.keep_screen_on = True

    lista_jogos_container = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    bs = ft.BottomSheet(
        content=ft.Container(
            padding=20,
            bgcolor="#0f172a",
            content=ft.Column(
                controls=[
                    ft.Text("Selecione a transmissão na CazéTV:", size=16, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Container(
                        content=lista_jogos_container,
                        height=350
                    )
                ],
                tight=True,
                spacing=15
            )
        )
    )
    page.overlay.append(bs)

    def selecionar_jogo_clicado(url_video):
        bs.open = False
        page.update()
        abrir_video_na_tv(url_video)

    def buscar_e_exibir_lives():
        # 1. Manda a TV abrir a página do canal no YouTube Padrão
        abrir_canal_cazetv_na_tv()

        # 2. Exibe o indicador de carregamento no celular
        lista_jogos_container.controls = [
            ft.Row(
                [
                    ft.ProgressRing(color="#38bdf8", width=24, height=24),
                    ft.Text("Buscando jogos ao vivo...", color="#94a3b8")
                ],
                alignment=ft.MainAxisAlignment.CENTER
            )
        ]
        bs.open = True
        page.update()

        # 3. Busca a lista de links via API em segundo plano
        def worker():
            lives = obter_lives_cazetv_api()
            lista_jogos_container.controls.clear()

            if lives:
                for item in lives:
                    titulo_live = item["titulo"]
                    url_live = item["url"]

                    btn = ft.Container(
                        content=ft.Text(titulo_live, color="white", weight=ft.FontWeight.W_500, size=13),
                        padding=12,
                        bgcolor="#1e293b",
                        border_radius=8,
                        on_click=lambda e, u=url_live: selecionar_jogo_clicado(u)
                    )
                    lista_jogos_container.controls.append(btn)
            else:
                lista_jogos_container.controls.append(
                    ft.Text("Nenhuma transmissão ao vivo encontrada no momento.", color="#ef4444", size=13)
                )

            page.update()

        threading.Thread(target=worker, daemon=True).start()

    def ao_clicar(e, canal):
        if canal == "CazéTV":
            buscar_e_exibir_lives()
        elif canal == "Globo":
            abrir_globo()
        elif canal == "RedeTV":
            abrir_redetv()

    def criar_card(nome, caminho_imagem, cores, border_color=None, text_color="white"):
        return ft.Container(
            width=165,
            height=160,
            content=ft.Column(
                controls=[
                    ft.Text(nome, size=16, weight=ft.FontWeight.BOLD, color=text_color),
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
            criar_card("CazéTV", "/LOGO CAZETV.png", ["#ffffff", "#cbd5e1"], "#facc15", text_color="#0f172a"),
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


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
