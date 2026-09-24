import flet as ft
import time
import threading
import os
import json
import re
import urllib.request
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, quote
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner

# --- CONFIGURAÇÕES E CHAVES ---
YOUTUBE_API_KEY = "AIzaSyDV_xrdplJuun_HcFivLnIW-KPgpldb5pQ"
IP_TV = "192.168.15.117"
PORT = 5555
CHANNEL_ID_CAZETV = "UCZiYbVptd3PVPf4f6eR6UaQ"

# Configurações do LiveSoccerTV e NVIDIA API
NVIDIA_API_KEY = "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"
MODEL_NAME = "meta/llama-3.2-11b-vision-instruct"
INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

BASE_URL = "https://www.livesoccertv.com"
SCHEDULE_URL = "https://www.livesoccertv.com/pt/schedules/"
CORINTHIANS_URL = "https://www.livesoccertv.com/pt/teams/brazil/corinthians/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

session = requests.Session()
session.headers.update(HEADERS)


# --- LÓGICA ADB E AUTOMAÇÕES TV ---
def conectar_adb():
    """Gera chave e conecta ao dispositivo ADB na TV."""
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
    return device


def abrir_canal_cazetv_na_tv():
    def worker():
        try:
            print("Abrindo canal da CazéTV na TV via YouTube Oficial...")
            device = conectar_adb()
            url_canal = f"https://www.youtube.com/channel/{CHANNEL_ID_CAZETV}"
            comando_abrir = f'am start -a android.intent.action.VIEW -d "{url_canal}" com.google.android.youtube.tv'
            device.shell(comando_abrir)
            
            time.sleep(8)
            device.shell("input keyevent 20")
            device.close()
        except Exception as err:
            print(f"Erro ao abrir canal na TV: {err}")

    threading.Thread(target=worker, daemon=True).start()


def obter_lives_cazetv_api():
    lives = []
    try:
        print("Consultando lives ativas via API HTTP do YouTube...")
        url_api = (
            f"https://www.googleapis.com/youtube/v3/search"
            f"?part=snippet&channelId={CHANNEL_ID_CAZETV}"
            f"&type=video&eventType=live&maxResults=5&key={YOUTUBE_API_KEY}"
        )
        
        req = urllib.request.Request(url_api, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            items = data.get('items', [])

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
    def worker():
        try:
            print(f"🔴 Abrindo jogo selecionado na TV: {url_video}")
            device = conectar_adb()
            device.shell(f'am start -a android.intent.action.VIEW -d "{url_video}" com.google.android.youtube.tv')
            device.close()
            print("Transmissão iniciada!")
        except Exception as err:
            print(f"Erro ao abrir vídeo via ADB: {err}")

    threading.Thread(target=worker, daemon=True).start()


def abrir_globo():
    def executar_adb():
        try:
            device = conectar_adb()
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


def abrir_maxnet_base(device):
    """Passos iniciais comuns para navegar até a lista de canais no MaxNet TV."""
    device.shell("am force-stop com.exploudapps.maxnettv")
    time.sleep(1)
    device.shell("am start -n com.exploudapps.maxnettv/.ui.activities.SplashActivity")
    time.sleep(8)

    device.shell("input keyevent 66")  # OK
    time.sleep(10)

    device.shell("input keyevent 19")  # CIMA
    time.sleep(1)
    device.shell("input keyevent 66")  # OK
    time.sleep(3)

    device.shell("input keyevent 19")  # CIMA
    time.sleep(1)
    device.shell("input keyevent 19")  # CIMA
    time.sleep(1)
    device.shell("input keyevent 19")  # CIMA
    time.sleep(1)
    device.shell("input keyevent 66")  # OK
    time.sleep(7)

    device.shell("input keyevent 21")  # ESQUERDA
    time.sleep(2)


def abrir_record():
    def executar_adb():
        try:
            print("Executando automação da Record no MaxNet TV...")
            device = conectar_adb()
            abrir_maxnet_base(device)

            # Record: 3 cliques para a direita
            device.shell("input keyevent 22")  # DIREITA 1
            time.sleep(1)
            device.shell("input keyevent 22")  # DIREITA 2
            time.sleep(1)
            device.shell("input keyevent 22")  # DIREITA 3
            time.sleep(1)

            device.shell("input keyevent 66")  # OK
            time.sleep(5)
            device.shell("input keyevent 66")  # OK
            time.sleep(5)

            device.close()
        except Exception as err:
            print(f"Erro no ADB (Record): {err}")

    threading.Thread(target=executar_adb, daemon=True).start()


def abrir_sbt():
    def executar_adb():
        try:
            print("Executando automação do SBT no MaxNet TV...")
            device = conectar_adb()
            abrir_maxnet_base(device)

            # SBT: 1 clique para a direita
            device.shell("input keyevent 22")  # DIREITA 1
            time.sleep(1)

            device.shell("input keyevent 66")  # OK
            time.sleep(5)
            device.shell("input keyevent 66")  # OK
            time.sleep(5)

            device.close()
        except Exception as err:
            print(f"Erro no ADB (SBT): {err}")

    threading.Thread(target=executar_adb, daemon=True).start()


def abrir_band():
    def executar_adb():
        try:
            print("Executando automação da Band no MaxNet TV...")
            device = conectar_adb()
            abrir_maxnet_base(device)

            # Band: 2 cliques para a direita
            device.shell("input keyevent 22")  # DIREITA 1
            time.sleep(1)
            device.shell("input keyevent 22")  # DIREITA 2
            time.sleep(1)

            device.shell("input keyevent 66")  # OK
            time.sleep(5)
            device.shell("input keyevent 66")  # OK
            time.sleep(5)

            device.close()
        except Exception as err:
            print(f"Erro no ADB (Band): {err}")

    threading.Thread(target=executar_adb, daemon=True).start()


def abrir_redetv():
    def executar_adb():
        try:
            print("Executando automação da RedeTV no MaxNet TV...")
            device = conectar_adb()
            abrir_maxnet_base(device)

            # RedeTV: 4 cliques para a direita
            device.shell("input keyevent 22")  # DIREITA 1
            time.sleep(1)
            device.shell("input keyevent 22")  # DIREITA 2
            time.sleep(1)
            device.shell("input keyevent 22")  # DIREITA 3
            time.sleep(1)
            device.shell("input keyevent 22")  # DIREITA 4
            time.sleep(1)

            device.shell("input keyevent 66")  # OK
            time.sleep(5)
            device.shell("input keyevent 66")  # OK
            time.sleep(5)

            device.close()
        except Exception as err:
            print(f"Erro no ADB (RedeTV): {err}")

    threading.Thread(target=executar_adb, daemon=True).start()


# --- SCRAPING LIVESOCCERTV & FILTRO ---
def epoch_ms_para_horario(epoch_ms):
    if not epoch_ms:
        return ""
    try:
        fuso_brt = timezone(timedelta(hours=-3))
        dt = datetime.fromtimestamp(int(epoch_ms) / 1000, tz=fuso_brt)
        return dt.strftime("%H:%M")
    except Exception:
        return ""


def extrair_dados_linha(row, campeonato="", comp_href=""):
    link = row.select_one('a[id^="g"]')
    titulo = link.get('title', '').strip() if link else ''
    if not titulo and link:
        titulo = link.get_text(strip=True)

    partes = titulo.split(' x ')
    casa = partes[0].strip() if len(partes) > 0 else ''
    fora = partes[1].strip() if len(partes) > 1 else ''

    score_el = row.select_one('.score, score')
    marcador = score_el.get_text(strip=True) if score_el else ''

    ts_el = row.select_one('.timecell .ts')
    dv = ts_el.get('dv') if ts_el else None

    hora = epoch_ms_para_horario(dv)
    if not hora:
        time_cell = row.select_one('.timecell')
        hora = time_cell.get_text(strip=True) if time_cell else ''

    canais = []
    for a in row.select('.channels-col .mchannels a'):
        nome = a.get_text(strip=True)
        if nome and nome not in canais:
            canais.append(nome)

    href = link.get('href') if link else ''
    url_partido = urljoin(BASE_URL, href) if href else ''

    return {
        'id': row.get('id', ''),
        'campeonato': campeonato,
        'inicio_utc': row.get('data-ko', ''),
        'inicio_epoch': int(dv) if dv and dv.isdigit() else 0,
        'hora': hora,
        'casa': casa,
        'fora': fora,
        'marcador': marcador,
        'estado': row.select_one('.inprogress').get_text(strip=True) if row.select_one('.inprogress') else '',
        'canais': canais,
        'canais_origem': 'lista' if canais else 'nenhuma',
        'url_partido': url_partido
    }


def buscar_canais_pagina_detalhe(match_url):
    if not match_url:
        return []
    try:
        resp = session.get(match_url, timeout=10)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        tv_sec = soup.select_one('#dynamic-tv')
        canais = []
        if tv_sec:
            for a in tv_sec.select('.m-channel-name a'):
                nome = a.get_text(strip=True)
                if nome and nome not in canais:
                    canais.append(nome)
        return canais
    except Exception:
        return []


def obter_jogos_do_dia(url_alvo=None, expandir_ligas=True, buscar_detalhes_sem_canal=True, max_workers=4):
    url_final = url_alvo if url_alvo else SCHEDULE_URL
    res = session.get(url_final, timeout=15)
    soup = BeautifulSoup(res.text, 'html.parser')

    partidos = []
    ligas_colapsadas = []
    current_comp = ""
    current_comp_href = ""

    elementos = soup.select('tr.sortable_comp, tr.r_comprow, div.competition_row, tr[data-ko]')

    for el in elementos:
        classes = el.get('class', [])
        
        if any(c in classes for c in ['sortable_comp', 'r_comprow', 'competition_row']):
            a_comp = el.select_one('a.r_complink')
            if a_comp:
                current_comp = a_comp.get_text(strip=True)
                current_comp_href = a_comp.get('href', '')

            onclick = el.get('onclick', '')
            match = re.search(r"showMatches\('(\d+)','([\d-]+)','([^']+)'\)", onclick)
            if match:
                cid, fecha, tab = match.groups()
                ligas_colapsadas.append({
                    'cid': cid,
                    'fecha': fecha,
                    'tab': tab,
                    'nombre': current_comp,
                    'href': current_comp_href
                })

        elif el.name == 'tr' and el.has_attr('data-ko'):
            partidos.append(extrair_dados_linha(el, current_comp, current_comp_href))

    if expandir_ligas and ligas_colapsadas:
        def fetch_colapsada(liga):
            url = f"{BASE_URL}/pt/xschedule.php?pagetype=scompetition&pageid={liga['cid']}&date={liga['fecha']}&tab={quote(liga['tab'])}&base=1"
            try:
                r = session.get(url, timeout=10)
                if r.status_code == 200:
                    s = BeautifulSoup(r.text, 'html.parser')
                    rows = s.select('tr[data-ko]')
                    return [extrair_dados_linha(r_el, liga['nombre'], liga['href']) for r_el in rows]
            except Exception:
                pass
            return []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(fetch_colapsada, liga) for liga in ligas_colapsadas]
            for f in as_completed(futures):
                partidos.extend(f.result())

    vistos = set()
    partidos_unicos = []
    for idx, p in enumerate(partidos):
        if not p['id']:
            p['id'] = f"game_{idx}"
        
        chave = p['id'] or f"{p['campeonato']}|{p['casa']}|{p['fora']}|{p['inicio_utc']}"
        if chave not in vistos:
            vistos.add(chave)
            partidos_unicos.append(p)

    # --- FILTRO APENAS PARA JOGOS DO DIA ATUAL (SE HOUVER URL_ALVO/TIME) ---
    if url_alvo:
        fuso_brt = timezone(timedelta(hours=-3))
        hoje_str = datetime.now(fuso_brt).strftime("%Y-%m-%d")
        
        jogos_do_dia = []
        for p in partidos_unicos:
            if p['inicio_epoch']:
                dt_jogo = datetime.fromtimestamp(p['inicio_epoch'] / 1000, tz=fuso_brt).strftime("%Y-%m-%d")
                if dt_jogo == hoje_str:
                    jogos_do_dia.append(p)
            elif p['inicio_utc']:
                if p['inicio_utc'].startswith(hoje_str):
                    jogos_do_dia.append(p)
        partidos_unicos = jogos_do_dia

    partidos_unicos.sort(key=lambda x: x['inicio_epoch'])

    sem_canais = [p for p in partidos_unicos if not p['canais'] and p['url_partido']]
    if buscar_detalhes_sem_canal and sem_canais:
        def atualizar_canais(p):
            canais_detalhes = buscar_canais_pagina_detalhe(p['url_partido'])
            if canais_detalhes:
                p['canais'] = canais_detalhes
                p['canais_origem'] = 'página do jogo'

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            list(executor.map(atualizar_canais, sem_canais))

    return partidos_unicos


def filtrar_jogos_brasileiros_com_nvidia(jogos):
    if not jogos:
        return []

    jogos_candidatos = []
    for j in jogos:
        camp = j.get('campeonato', '').lower()
        casa = j.get('casa', '').lower()
        fora = j.get('fora', '').lower()
        
        if "brasil" in camp or "brasileirão" in camp or "paulista" in camp or "carioca" in camp:
            jogos_candidatos.append(j)
        elif any(c in camp for c in ["libertadores", "sul-americana", "sudamericana", "world cup"]):
            jogos_candidatos.append(j)

    if not jogos_candidatos:
        return []

    mapa_jogos = {j['id']: j for j in jogos_candidatos}

    jogos_simplificados = [
        {
            "id": j['id'],
            "campeonato": j['campeonato'],
            "casa": j['casa'],
            "fora": j['fora']
        }
        for j in jogos_candidatos
    ]

    jogos_json_str = json.dumps(jogos_simplificados, ensure_ascii=False)

    prompt = f"""Você é um filtro rigoroso de futebol.
Análise a lista JSON abaixo e retorne APENAS um array JSON com os IDs dos jogos pertencentes EXCLUSIVAMENTE ao futebol brasileiro ou com times brasileiros envolvidos.

REGRAS RÍGIDAS:
1. DESCARTE imediatamente qualquer jogo de ligas internacionais que NÃO tenham times do Brasil (Ex: Canadá, EUA, USL, Premier League, La Liga, etc.).
2. MANTENHA apenas jogos cujo campeonato seja do BRASIL (Ex: Brasil - Brasileirão, Copa do Brasil, Estaduais) OU torneios internacionais com times brasileiros jogando.
3. Responda APENAS o array JSON no formato: ["g1234", "g5678"].

Entrada:
{jogos_json_str}"""

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        "temperature": 0.0,
        "max_tokens": 1024,
        "top_p": 1,
        "stream": False
    }

    try:
        response = requests.post(INVOKE_URL, headers=headers, json=payload, timeout=40)
        response.raise_for_status()
        dados = response.json()

        conteudo_resposta = dados["choices"][0]["message"]["content"].strip()

        match_json = re.search(r'\[.*\]', conteudo_resposta, re.DOTALL)
        if match_json:
            conteudo_resposta = match_json.group(0)

        ids_selecionados = json.loads(conteudo_resposta)
        jogos_filtrados = [mapa_jogos[gid] for gid in ids_selecionados if gid in mapa_jogos]
        return jogos_filtrados

    except Exception as e:
        print(f"⚠ Erro no processamento da NVIDIA API: {e}")
        return jogos_candidatos


# --- INTERFACE FLET ---
def main(page: ft.Page):
    page.title = "Controle de Canais"
    page.bgcolor = "#030712"
    page.window.width = 400
    page.window.height = 750
    page.window.resizable = False
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO
    page.padding = ft.Padding(20, 48, 20, 16)
    
    # --- ATIVAÇÃO DO WAKELOCK ---
    wakelock = ft.Wakelock()

    async def ativar_wakelock():
        try:
            await wakelock.enable()
            print("Wakelock ativado com sucesso!")
        except Exception as err:
            print(f"Aviso Wakelock (esperado no Windows Desktop): {err}")

    page.run_task(ativar_wakelock)

    lista_jogos_container = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)
    titulo_bottom_sheet = ft.Text("Selecione a opção:", size=16, weight=ft.FontWeight.BOLD, color="white")

    bs = ft.BottomSheet(
        content=ft.Container(
            padding=20,
            bgcolor="#0f172a",
            content=ft.Column(
                controls=[
                    titulo_bottom_sheet,
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
        titulo_bottom_sheet.value = "Selecione a transmissão na CazéTV:"
        abrir_canal_cazetv_na_tv()

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

    def buscar_e_exibir_jogos(url_alvo=None, titulo="Jogos de Futebol de Hoje:"):
        titulo_bottom_sheet.value = titulo

        lista_jogos_container.controls = [
            ft.Row(
                [
                    ft.ProgressRing(color="#10b981", width=24, height=24),
                    ft.Text("Extraindo jogos...", color="#94a3b8")
                ],
                alignment=ft.MainAxisAlignment.CENTER
            )
        ]
        bs.open = True
        page.update()

        def worker():
            jogos_brutos = obter_jogos_do_dia(url_alvo=url_alvo)
            jogos = filtrar_jogos_brasileiros_com_nvidia(jogos_brutos) if not url_alvo else jogos_brutos
            
            lista_jogos_container.controls.clear()

            if jogos:
                for j in jogos:
                    casa = j.get('casa', '')
                    fora = j.get('fora', '')
                    marcador = f" ({j.get('marcador')})" if j.get('marcador') else ""
                    hora = j.get('hora', '')
                    campeonato = j.get('campeonato', '')
                    canais = ", ".join(j.get('canais', [])) if j.get('canais') else "Sem transmissão informada"

                    card_jogo = ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text(f"{casa}{marcador} x {fora}", color="white", weight=ft.FontWeight.BOLD, size=14, expand=True),
                                        ft.Text(hora, color="#38bdf8", weight=ft.FontWeight.BOLD, size=13)
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                                ft.Text(f"🏆 {campeonato}", color="#94a3b8", size=11),
                                ft.Text(f"📺 {canais}", color="#cbd5e1", size=12, weight=ft.FontWeight.W_500)
                            ],
                            spacing=4
                        ),
                        padding=12,
                        bgcolor="#1e293b",
                        border_radius=8,
                        border=ft.Border.all(1, "#334155")
                    )
                    lista_jogos_container.controls.append(card_jogo)
            else:
                fuso_brt = timezone(timedelta(hours=-3))
                data_hoje = datetime.now(fuso_brt).strftime("%d/%m/%Y")
                
                if url_alvo == CORINTHIANS_URL:
                    mensagem_vazia = f"Nenhum jogo do Corinthians encontrado na data {data_hoje}"
                else:
                    mensagem_vazia = f"Nenhum jogo encontrado na data {data_hoje}"

                lista_jogos_container.controls.append(
                    ft.Text(mensagem_vazia, color="#ef4444", size=13)
                )

            page.update()

        threading.Thread(target=worker, daemon=True).start()

    def ao_clicar(e, canal):
        if canal == "CazéTV":
            buscar_e_exibir_lives()
        elif canal == "Globo":
            abrir_globo()
        elif canal == "Record":
            abrir_record()
        elif canal == "SBT":
            abrir_sbt()
        elif canal == "Band":
            abrir_band()
        elif canal == "RedeTV":
            abrir_redetv()
        elif canal == "Jogos do Corinthians Hoje":
            buscar_e_exibir_jogos(url_alvo=CORINTHIANS_URL, titulo="Esses são os Jogos do Corinthians de Hoje:")
        elif canal == "Jogos de Futebol Hoje":
            buscar_e_exibir_jogos()

    def criar_card(nome, caminho_imagem, cores, border_color=None, text_color="white"):
        return ft.Container(
            width=165,
            height=160,
            content=ft.Column(
                controls=[
                    ft.Text(
                        nome,
                        size=13,
                        weight=ft.FontWeight.BOLD,
                        color=text_color,
                        text_align=ft.TextAlign.CENTER
                    ),
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
            criar_card("Jogos do Corinthians Hoje", "/CORINTHIANS LOGO.png", ["#ffffff", "#cbd5e1"], "#000000", text_color="#0f172a"),
            criar_card("Jogos de Futebol Hoje", "/logo jogos de futebol hoje.png", ["#ffffff", "#cbd5e1"], "#15803d", text_color="#0f172a"),
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
