# language: pt
Funcionalidade: Processamento Individual de Cena
  Como Creator
  Eu quero processar ou reprocessar uma única cena do meu vídeo
  Para que eu possa ver o resultado visual de uma alteração sem ter que renderizar todo o vídeo

  Contexto:
    Dado que o vídeo está no status "processing"
    E a cena possui narração e imagem/vídeo configurados

  @smoke @critico
  Cenário: Processar cena com sucesso
    Dado que a cena ainda não possui um vídeo gerado
    Quando eu clico no botão "Processar Cena"
    Então o sistema deve gerar o clipe MP4 daquela cena
    E o status da cena deve ser atualizado para exibir o player de vídeo

  @regressao
  Cenário: Reprocessar cena existente
    Dado que a cena já possui um vídeo gerado
    Quando eu clico no botão "Processar Cena" novamente
    Então o sistema deve sobrescrever o clipe MP4 existente com uma nova versão
    E o player da cena deve ser atualizado na UI

  @regressao
  Cenário: Falha ao processar cena sem assets
    Dado que a cena não possui áudio gerado
    Quando eu tento processar a cena
    Então o sistema deve exibir uma mensagem de erro informando que faltam assets
    E a cena não deve ser processada
