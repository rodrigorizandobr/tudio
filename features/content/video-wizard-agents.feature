# language: pt
Funcionalidade: Criação de Vídeo com Seleção de Agente
  Como Creator
  Eu quero poder selecionar um Agente durante a criação de um novo vídeo
  Para que o roteiro e o estilo do vídeo sigam a persona e as instruções do Agente escolhido

  Contexto:
    Dado que o usuário está autenticado
    E está na página "Criar Novo Vídeo" (/panel/videos/new)

  @critico @smoke
  Cenário: Criar vídeo com um Agente específico
    Dado que existem Agentes cadastrados no sistema
    Quando o usuário preenche o prompt "Um vídeo sobre a história do café"
    E seleciona o Agente "Eduardo Escritor"
    E clica em "Gerar Vídeo"
    Então o vídeo deve ser criado com o agent_id correspondente ao "Eduardo Escritor"
    E o processamento de background deve usar as instruções do Agente no roteiro

  @regressao
  Cenário: Seleção de Agente padrão
    Dado que o usuário não seleciona um Agente específico
    Quando ele clica em "Gerar Vídeo"
    Então o sistema deve prosseguir com o Agente padrão ("Capo Imaculado")
    E o vídeo deve ser criado com sucesso
