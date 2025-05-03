# Kahoot Solver com Azure AI

Este script Python utiliza o Playwright para monitorar uma sessão do Kahoot e a API de Modelos do GitHub Marketplace (especificamente o modelo `openai/gpt-4.1` neste código) para sugerir respostas e clicar automaticamente na opção correspondente.

## Pré-requisitos

*   Python 3.11 ou superior
*   Navegador Firefox instalado
*   Uma chave de API válida para os modelos do GitHub Marketplace.

## Configuração

1.  **Clonar ou Baixar:** Obtenha o código do script (`kahoot_bot.py`).

2.  **Instalar Dependências:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Instalar Navegadores Playwright:**
    ```bash
    playwright install firefox
    ```
    (Pode ser necessário apenas `playwright install` se você não tiver nenhum navegador Playwright instalado).

4.  **Configurar Chave de API:**
    *   **Obtenha sua chave:** Crie uma chave de API para os modelos do GitHub Marketplace aqui: [https://github.com/marketplace/models](https://github.com/marketplace/models)
    *   **Insira no Código:** Abra o arquivo `kahoot_bot.py` e substitua o valor da variável `AZURE_API_TOKEN` pela sua chave de API:
        ```python
        AZURE_API_TOKEN = "SUA_CHAVE_API_AQUI"
        ```

## Uso

1.  Execute o script:
    ```bash
    python kahoot_bot.py
    ```
2.  O script iniciará o navegador Firefox e navegará para `https://kahoot.it/`.
3.  Insira o PIN do jogo Kahoot no navegador como faria normalmente.
4.  O script monitorará a tela do jogo. Quando uma pergunta e suas opções aparecerem (nas URLs `/getready` e `/gameblock`), ele enviará a pergunta e as opções para a API configurada.
5.  Ao receber a resposta da API (espera-se um número de 1 a 4), o script tentará clicar no botão correspondente na janela do navegador.
6.  Para parar o script, volte ao terminal onde ele está rodando e pressione `Enter`.

## Pontos Importantes e Limitações

*   **Opção Kahoot Necessária:** O jogo Kahoot **DEVE** ter a opção "Mostrar perguntas e respostas nos dispositivos dos jogadores" ("Show questions and answers on players' devices") ativada para que o script consiga ler as perguntas e opções.
*   **Modelo da API:** Este código está configurado para usar o modelo `openai/gpt-4.1` através do endpoint do GitHub. Se desejar usar um modelo diferente disponível no marketplace, você precisará:
    *   Atualizar a variável `AZURE_MODEL_NAME` no código.
    *   Verificar se a estrutura da chamada da API (`client.complete`) e os parâmetros (`temperature`, `top_p`, `max_tokens`, etc.) são adequados para o novo modelo. Pode ser necessário ajustar o código na função `obter_resposta_azure`.
*   **Tipos de Quiz:**
    *   O script foi projetado principalmente para Kahoots do tipo **"Quiz"** (múltipla escolha padrão).
    *   Pode apresentar comportamento inesperado ou erros em quizzes do tipo **"Verdadeiro ou Falso"**.
    *   **Não funcionará** corretamente com outros tipos de perguntas do Kahoot (como "Type Answer", "Puzzle", "Slider", etc.) e provavelmente causará erros.
*   **Seletores HTML:** O script depende de seletores HTML específicos (`SELETOR_PERGUNTA`, `SELETOR_OPCOES`) para encontrar a pergunta e os botões de resposta. Se o Kahoot atualizar sua interface, esses seletores podem precisar ser ajustados no código.
*   **Clique Simulado:** O script realiza um clique *simulado* dentro do navegador controlado pelo Playwright. Ele não controla o cursor físico do mouse do seu computador.
*   **Precisão da IA:** As respostas são geradas por uma inteligência artificial (`openai/gpt-4.1` neste código). Embora o objetivo seja acertar, **não há garantia de 100% de acertos**. A precisão pode variar dependendo da pergunta, das opções e do próprio modelo de IA.

## Arquivo `requirements.txt`

 Use `pip install -r requirements.txt` para instalar as dependências.
