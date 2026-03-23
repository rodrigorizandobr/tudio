# language: pt
Funcionalidade: Salvamento Automático de Configurações de Legendas
  Como Creator
  Eu quero que minhas escolhas de estilo e opções de legenda sejam salvas automaticamente
  Para que eu possa gerar legendas de cenas individuais com as configurações desejadas sem cliques extras

  Contexto:
    Dado que o usuário está na página de detalhes do vídeo
    E o vídeo possui narração e mídia prontos

  @critico @smoke
  Cenário: Alterar o estilo de legenda salva automaticamente
    Dado que o estilo atual é "karaoke"
    Quando o usuário clica no estilo "word_pop"
    Então o sistema deve enviar uma requisição para salvar o novo estilo no back-end
    E o estilo "word_pop" deve ser persistido no banco de dados

  @smoke
  Cenário: Alterar opções de posição ou palavras por linha salva automaticamente
    Dado que a posição atual é "bottom"
    Quando o usuário altera a posição para "top"
    Então o sistema deve enviar uma requisição para salvar a nova configuração no back-end após um breve delay (debounce)
    E a posição "top" deve ser persistida no banco de dados

  @regressao
  Cenário: Gerar legenda de cena usa as configurações salvas recentemente
    Dado que o usuário alterou o estilo para "highlight" (salvo automaticamente)
    Quando o usuário clica para gerar legenda de uma cena específica
    Então a legenda gerada para aquela cena deve usar o estilo "highlight"
