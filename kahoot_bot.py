import asyncio
import re
import threading
import os
from playwright.async_api import async_playwright, Error as PlaywrightError
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

AZURE_API_TOKEN = "SUA_CHAVE_API_AQUI"
AZURE_API_ENDPOINT = "https://models.github.ai/inference"
AZURE_MODEL_NAME = "openai/gpt-4.1"
URL_BASE = "https://kahoot.it/"
URL_PRONTO = "https://kahoot.it/getready"
SELETOR_PERGUNTA = ".visually-hidden__SROnly-sc-18gl3eq-0.fLRPag"
INDICE_PERGUNTA = 1
TEXTO_REMOVER_PERGUNTA = " - Kahoot!"
URL_JOGO = "https://kahoot.it/gameblock"
SELETOR_OPCOES = "button"
NUM_OPCOES = 4

INTERVALO_VERIFICACAO_SEG = 0.5
parada_solicitada = False
instancia_cliente_azure = None

try:
    if not AZURE_API_TOKEN:
        raise ValueError("Variável de ambiente AZURE_API_TOKEN não definida.")
    instancia_cliente_azure = ChatCompletionsClient(
        endpoint=AZURE_API_ENDPOINT,
        credential=AzureKeyCredential(AZURE_API_TOKEN),
    )
    print("Cliente Azure AI Inference configurado com sucesso.", flush=True)
except ValueError as ve:
    print(f"ERRO Configuração Azure: {ve}", flush=True)
except Exception as e:
    print(f"ERRO Configuração Azure: {e}", flush=True)
async def obter_resposta_azure(pergunta, textos_opcoes):
    if parada_solicitada: return None
    if not instancia_cliente_azure:
        print("Instância Azure AI Inference não disponível.", flush=True)
        return None
    if not pergunta or not any(opt for opt in textos_opcoes if opt is not None):
        print("Pergunta ou opções ausentes para chamada Azure.", flush=True)
        return None
    pergunta_limpa = pergunta
    if pergunta_limpa.endswith(TEXTO_REMOVER_PERGUNTA):
        pergunta_limpa = pergunta_limpa[:-len(TEXTO_REMOVER_PERGUNTA)].strip()
    system_prompt = (
        "You are a helpful assistant specialized in answering multiple-choice questions. "
        "who only responds with the button number corresponding to the most likely answer do not respond with words only a integer. "
        "You'll do this even if the question involves content you can't analyze, such as videos or images. "
        "If you cannot answer the question, you'll respond with an educated guess. "
        "Remember only respond with an integer between 1 and 4 that corresponds to the answer."
    )
    user_prompt_content = f"Pergunta: {pergunta_limpa}\nOpções:\n"
    contagem_opcoes_validas = 0
    for i, texto_opcao in enumerate(textos_opcoes):
        if i < NUM_OPCOES and texto_opcao is not None:
            user_prompt_content += f"{i + 1}: {texto_opcao}\n"
            contagem_opcoes_validas += 1
    if contagem_opcoes_validas == 0:
        print("Nenhuma opção válida encontrada para prompt Azure.", flush=True)
        return None
    print(f"--- Enviando para Azure AI ({AZURE_MODEL_NAME}) ---", flush=True)
    try:
        loop = asyncio.get_running_loop()
        resposta = await loop.run_in_executor(
            None,
            lambda: instancia_cliente_azure.complete(
                messages=[
                    SystemMessage(system_prompt),
                    UserMessage(user_prompt_content),
                ],
                temperature=1,
                top_p=1,
                max_tokens=10,
                model=AZURE_MODEL_NAME
            )
        )
        if resposta.choices and resposta.choices[0].message and resposta.choices[0].message.content:
            resposta_texto = resposta.choices[0].message.content.strip()
            resposta_limpa = ''.join(filter(str.isdigit, resposta_texto))
            print(f"Resposta Azure (limpa): {resposta_limpa}", flush=True)
            return resposta_limpa if resposta_limpa in ["1", "2", "3", "4"] else None
        else:
            print("ERRO API Azure: Resposta inesperada ou vazia.", flush=True)
            return None
    except Exception as e:
        if not parada_solicitada:
            print(f"ERRO API Azure: {e}", flush=True)
        return None
def aguardar_enter():
    global parada_solicitada
    input("Monitoramento iniciado. Pressione Enter para sair...\n")
    if not parada_solicitada:
        print("\nEnter pressionado. Iniciando desligamento...", flush=True)
        parada_solicitada = True
async def loop_monitoramento(p):
    global parada_solicitada
    navegador = None
    pagina = None
    try:
        print("Iniciando navegador Firefox...", flush=True)
        navegador = await p.firefox.launch(headless=False)
        pagina = await navegador.new_page()
        print(f"Navegando para {URL_BASE}...", flush=True)
        await pagina.goto(URL_BASE, wait_until="domcontentloaded")
        url_anterior = pagina.url
        print(f"URL Inicial: {url_anterior}", flush=True)
        texto_pergunta_anterior = None
        tupla_opcoes_anterior = tuple([None] * NUM_OPCOES)
        ultima_pergunta_valida = None
        ultimos_textos_opcoes_validos = [None] * NUM_OPCOES
        await asyncio.sleep(2)
        while not parada_solicitada:
            resposta_api = None
            try:
                if not pagina or pagina.is_closed() or not navegador.is_connected():
                    print("Página ou navegador desconectado. Encerrando loop.", flush=True)
                    parada_solicitada = True
                    continue
                url_atual = pagina.url

                texto_pergunta_atual = None
                pergunta_encontrada = False
                if url_atual == URL_PRONTO:
                    try:
                        localizadores_pergunta = pagina.locator(SELETOR_PERGUNTA)
                        if await localizadores_pergunta.count() > INDICE_PERGUNTA:
                            texto = await localizadores_pergunta.nth(INDICE_PERGUNTA).text_content(timeout=1000)
                            texto_pergunta_atual = texto.strip() if texto and texto.strip() else None
                            pergunta_encontrada = True
                    except PlaywrightError as e:
                         if "Timeout" not in str(e) and not parada_solicitada:
                              print(f"Erro ao buscar pergunta: {e}", flush=True)
                         texto_pergunta_atual = None
                         pergunta_encontrada = False
                pergunta_mudou = texto_pergunta_atual != texto_pergunta_anterior
                if pergunta_encontrada and pergunta_mudou:
                     print(f"Pergunta encontrada: {texto_pergunta_atual}", flush=True)
                lista_opcoes_atual = [None] * NUM_OPCOES
                opcoes_encontradas = False
                if url_atual == URL_JOGO:
                    try:
                        localizadores_botao = pagina.locator(SELETOR_OPCOES)
                        contagem_botao = await localizadores_botao.count()
                        if contagem_botao > 0:
                            opcoes_encontradas = True
                            tasks = []
                            for i in range(min(contagem_botao, NUM_OPCOES)):
                                tasks.append(localizadores_botao.nth(i).text_content(timeout=1000))
                            resultados_textos = await asyncio.gather(*tasks, return_exceptions=True)
                            for i, texto_ou_erro in enumerate(resultados_textos):
                                if isinstance(texto_ou_erro, Exception):
                                    if "Timeout" not in str(texto_ou_erro) and not parada_solicitada:
                                        print(f"Erro ao buscar opção {i+1}: {texto_ou_erro}", flush=True)
                                    lista_opcoes_atual[i] = None
                                else:
                                    texto_limpo = texto_ou_erro.strip() if texto_ou_erro else None
                                    if texto_limpo and texto_limpo.lower().startswith("icon"):
                                        correspondencia = re.search(r"icon(.*)", texto_limpo, re.IGNORECASE)
                                        if correspondencia: texto_limpo = correspondencia.group(1).strip()
                                    lista_opcoes_atual[i] = texto_limpo if texto_limpo else None
                    except PlaywrightError as e:
                        if "Timeout" not in str(e) and not parada_solicitada:
                            print(f"Erro ao buscar opções: {e}", flush=True)
                        opcoes_encontradas = False
                        lista_opcoes_atual = [None] * NUM_OPCOES
                tupla_opcoes_atual = tuple(lista_opcoes_atual)
                opcoes_mudaram = tupla_opcoes_atual != tupla_opcoes_anterior
                if opcoes_encontradas and opcoes_mudaram and any(opt for opt in lista_opcoes_atual if opt is not None):
                    print(f"Opções encontradas:", flush=True)
                    for i, texto_opcao in enumerate(lista_opcoes_atual):
                        if texto_opcao is not None:
                            print(f"  {i+1}: {texto_opcao}", flush=True)
                if texto_pergunta_atual is not None:
                    ultima_pergunta_valida = texto_pergunta_atual
                if url_atual == URL_JOGO and opcoes_encontradas:
                    for i in range(NUM_OPCOES):
                         if lista_opcoes_atual[i] is not None:
                              ultimos_textos_opcoes_validos[i] = lista_opcoes_atual[i]
                if url_atual == URL_JOGO and (opcoes_mudaram and any(opt for opt in lista_opcoes_atual if opt is not None)) and ultima_pergunta_valida and any(ultimos_textos_opcoes_validos):
                    resposta_api = await obter_resposta_azure(ultima_pergunta_valida, ultimos_textos_opcoes_validos)
                    if resposta_api:
                        print(f"<<< Resposta Sugerida (Azure): {resposta_api} >>>", flush=True)
                        try:
                            indice_resposta = int(resposta_api) - 1
                            if 0 <= indice_resposta < NUM_OPCOES:
                                print(f"--- Tentando clicar no botão {resposta_api} (índice {indice_resposta}) ---", flush=True)
                                await pagina.locator(SELETOR_OPCOES).nth(indice_resposta).wait_for(state="visible", timeout=1000)
                                await pagina.locator(SELETOR_OPCOES).nth(indice_resposta).click(timeout=1500)
                                print(f"--- Botão {resposta_api} clicado com sucesso! ---", flush=True)
                                ultima_pergunta_valida = None
                                ultimos_textos_opcoes_validos = [None] * NUM_OPCOES
                                texto_pergunta_anterior = None
                                tupla_opcoes_anterior = tuple([None] * NUM_OPCOES)
                                await asyncio.sleep(0.5)
                            else:
                                print(f"ERRO Clique: Índice de resposta inválido ({indice_resposta}) da API.", flush=True)
                        except ValueError:
                            print(f"ERRO Clique: Resposta da API não é um número válido ('{resposta_api}').", flush=True)
                        except PlaywrightError as click_error:
                            if not parada_solicitada:
                                if "timeout" in str(click_error).lower() or "not found" in str(click_error).lower():
                                     print(f"AVISO Clique: Botão {resposta_api} não encontrado/clicável a tempo. Erro: {click_error}", flush=True)
                                else:
                                     print(f"ERRO Clique Playwright: Não foi possível clicar no botão {resposta_api}. Erro: {click_error}", flush=True)
                        except Exception as general_click_error:
                             if not parada_solicitada:
                                print(f"ERRO Clique Inesperado: {type(general_click_error).__name__} - {general_click_error}", flush=True)
                url_anterior = url_atual
                texto_pergunta_anterior = texto_pergunta_atual
                tupla_opcoes_anterior = tupla_opcoes_atual
            except PlaywrightError as e:
                if parada_solicitada and ("Target page, context or browser has been closed" in str(e) or "Connection closed" in str(e)):
                    print("Erro esperado durante desligamento Playwright.", flush=True)
                elif not parada_solicitada:
                    print(f"ERRO Playwright no loop principal: {e}", flush=True)
                    try:
                        if pagina and not pagina.is_closed():
                            print("Tentando recarregar a página...", flush=True)
                            await pagina.reload(wait_until="domcontentloaded")
                            await asyncio.sleep(2)
                            url_anterior = pagina.url
                            texto_pergunta_anterior = None
                            tupla_opcoes_anterior = tuple([None] * NUM_OPCOES)
                            ultima_pergunta_valida = None
                            ultimos_textos_opcoes_validos = [None] * NUM_OPCOES
                            print("Página recarregada.", flush=True)
                        else:
                            print("Página fechada, não é possível recarregar.", flush=True)
                            parada_solicitada = True
                    except PlaywrightError as erro_recarga:
                        print(f"ERRO Recarga: {erro_recarga}. Encerrando.", flush=True)
                        parada_solicitada = True
            except Exception as e:
                if not parada_solicitada:
                    print(f"ERRO Inesperado no loop principal: {type(e).__name__} - {e}", flush=True)
            await asyncio.sleep(INTERVALO_VERIFICACAO_SEG)
            if parada_solicitada: break
    except Exception as e:
        if not parada_solicitada:
            print(f"ERRO Fatal no loop de monitoramento: {e}", flush=True)
            parada_solicitada = True
    finally:
        print("Iniciando limpeza final do loop de monitoramento...", flush=True)
        if navegador and navegador.is_connected():
            print("Fechando navegador...", flush=True)
            try:
                await navegador.close()
                print("Navegador fechado com sucesso.", flush=True)
            except PlaywrightError as e:
                if "Connection closed" in str(e) or "Browser has been closed" in str(e):
                    print("Erro esperado ao fechar navegador durante desligamento.", flush=True)
                else:
                    print(f"ERRO ao fechar navegador: {e}", flush=True)
            except Exception as e:
                 print(f"ERRO inesperado ao fechar navegador: {e}", flush=True)
        elif navegador:
            print("Navegador já desconectado.", flush=True)
        else:
            print("Nenhuma instância de navegador para fechar.", flush=True)
        print("Loop de monitoramento encerrado.", flush=True)
async def principal():
    if not instancia_cliente_azure:
        print("Cliente Azure não inicializado. Encerrando script.", flush=True)
        return
    thread_entrada = threading.Thread(target=aguardar_enter, daemon=True)
    thread_entrada.start()
    async with async_playwright() as p:
        await loop_monitoramento(p)
    print("Script principal encerrado.", flush=True)
if __name__ == "__main__":
    try:
        asyncio.run(principal())
    except KeyboardInterrupt:
        print("\nCTRL+C detectado no nível superior. Encerrando.", flush=True)
        parada_solicitada = True
    finally:
        print("Programa finalizado.", flush=True)
