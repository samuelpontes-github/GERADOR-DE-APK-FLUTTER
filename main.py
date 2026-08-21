import flet as ft
import time
import threading
import os
import xml.etree.ElementTree as ET
import multiprocessing
import uiautomator2 as u2
from googleapiclient.discovery import build
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner

# --- CONFIGURAÇÕES E CHAVES ---
YOUTUBE_API_KEY = "AIzaSyDV_xrdplJuun_HcFivLnIW-KPgpldb5pQ"
IP_TV = "192.168.15.117"
PORT = 5555
CHANNEL_ID_CAZETV = "UCIg6LJXdEAX4UUWdTF8z8LQ"

youtube_client = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)


def obter_link_youtube_api(titulo_exato):
    """Busca a URL direta do vídeo na API do YouTube usando o título exato."""
    try:
        request = youtube_client.search().list(
            part="snippet",
            q=titulo_exato,
            type="video",
            eventType="live",
            maxResults=1
        )
        response = request.execute()
        items = response.get('items', [])

        if not items:
            request = youtube_client.search().list(
                part="snippet",
                q=titulo_exato,
                type="video",
                maxResults=1
            )
            response = request.execute()
            items = response.get('items', [])

        if items:
            video_id = items[0]['id']['videoId']
            return f"https://www.youtube.com/watch?v={video_id}"
        return None
    except Exception as e:
        print(f"Erro na API do YouTube: {e}")
        return None


def _tarefa_uiautomator(queue_resultado, ip_tv):
    """Executado em um processo Python totalmente separado do Flet.
    Quando este processo morre, o Windows fecha forçadamente os sockets TCP."""
    titulos = []
    try:
        print("Extraindo XML da tela em processo isolado...")
        d = u2.connect(ip_tv)
        xml_dump = d.dump_hierarchy()
        
        root = ET.fromstring(xml_dump)
        for video_container in root.iter('node'):
            badge = video_container.find(".//*[@resource-id='org.smarttube.stable:id/extra_text_badge'][@text='AO VIVO']")
            if badge is not None:
                title_node = video_container.find(".//*[@resource-id='org.smarttube.stable:id/title_text']")
                if title_node is not None and title_node.attrib.get('text'):
                    titulo = title_node.attrib.get('text').strip()
                    if titulo.upper() != "CAZÉTV LIVE" and titulo not in titulos:
                        titulos.append(titulo)
    except Exception as err:
        print(f"Erro na captura por uiautomator: {err}")
    finally:
        queue_resultado.put(titulos)


def capturar_titulos_cazetv():
    """Gerencia a navegação ADB e executa o uiautomator2 em um subprocesso isolado."""
    try:
        print("Iniciando captura de títulos da CazéTV...")
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
        comando_abrir = f'am start -a android.intent.action.VIEW -d "{url_canal}" org.smarttube.stable'
        device.shell(comando_abrir)
        device.close()
        
        print("Aguardando SmartTube carregar...")
        time.sleep(8)
        
        # Cria fila e processo isolado para o UIAutomator2
        queue = multiprocessing.Queue()
        p = multiprocessing.Process(target=_tarefa_uiautomator, args=(queue, IP_TV))
        p.start()
        
        # Aguarda até 15 segundos para obter o resultado
        titulos = queue.get(timeout=15)
        p.join()
        
        # Encerra o processo de forma forçada para garantir a destruição de sockets no Windows
        if p.is_alive():
            p.terminate()

        # Limpeza no Android via ADB
        device = AdbDeviceTcp(IP_TV, PORT, default_transport_timeout_s=9)
        device.connect(rsa_keys=[signer], auth_timeout_s=5)
        device.shell("am force-stop com.github.uiautomator")
        device.shell("am force-stop com.github.uiautomator.test")
        device.close()

        print("Processo destruído e conexão totalmente encerrada!")
        return titulos

    except Exception as err:
        print(f"Erro na captura geral: {err}")
        return []


def tocar_video_no_youtube(titulo_escolhido):
    """Obtém a URL do vídeo selecionado e executa a transição para o YouTube oficial."""
    def worker():
        try:
            print(f"Título selecionado: '{titulo_escolhido}'")
            url_video = obter_link_youtube_api(titulo_escolhido)
            print(f"🔴 URL do jogo obtida: {url_video}")
            
            if url_video:
                key_path = "adbkey"
                with open(key_path, 'rb') as f:
                    priv = f.read()
                with open(key_path + '.pub', 'rb') as f:
                    pub = f.read()
                    
                signer = PythonRSASigner(pub, priv)
                device = AdbDeviceTcp(IP_TV, PORT, default_transport_timeout_s=9)
                device.connect(rsa_keys=[signer], auth_timeout_s=5)
                
                print("Encerrando o SmartTube...")
                device.shell("am force-stop org.smarttube.stable")
                time.sleep(1)
                
                print("Abrindo no YouTube Padrão...")
                device.shell(f'am start -a android.intent.action.VIEW -d "{url_video}" com.google.android.youtube.tv')
                device.close()
                print("Automação finalizada. Controle remoto liberado!")
        except Exception as err:
            print(f"Erro ao abrir vídeo: {err}")

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

    def selecionar_jogo_clicado(titulo):
        bs.open = False
        page.update()
        tocar_video_no_youtube(titulo)

    def buscar_e_exibir_lives():
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

        def worker():
            titulos = capturar_titulos_cazetv()
            lista_jogos_container.controls.clear()

            if titulos:
                for t in titulos:
                    btn = ft.Container(
                        content=ft.Text(t, color="white", weight=ft.FontWeight.W_500, size=13),
                        padding=12,
                        bgcolor="#1e293b",
                        border_radius=8,
                        on_click=lambda e, titulo_item=t: selecionar_jogo_clicado(titulo_item)
                    )
                    lista_jogos_container.controls.append(btn)
            else:
                lista_jogos_container.controls.append(
                    ft.Text("Nenhum jogo ao vivo encontrado no momento.", color="#ef4444", size=13)
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
    multiprocessing.freeze_support()
    ft.run(main, assets_dir="assets")
