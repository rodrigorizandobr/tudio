# language: pt
Funcionalidade: Lógica de Exibição do Player de Cena
  Como Creator
  Eu quero que o player de cada cena exiba o vídeo mais processado disponível
  Para que eu possa ver o progresso real da cena com legendas ou efeitos

  Contexto:
    Dado que o usuário está na página de detalhes do vídeo

  @critico @smoke
  Cenário: Exibir vídeo com legenda se disponível
    Dado que uma cena possui "captioned_video_url"
    E também possui "generated_video_url" e "video_url"
    Quando a cena é renderizada na lista
    Então o player deve exibir o vídeo de "captioned_video_url"
    E a etiqueta deve indicar "Cena com Legenda"

  @critico
  Cenário: Exibir vídeo gerado se não houver legenda
    Dado que uma cena possui "generated_video_url"
    E "captioned_video_url" está vazio
    E possui "video_url"
    Quando a cena é renderizada na lista
    Então o player deve exibir o vídeo de "generated_video_url"
    E a etiqueta deve indicar "Preview da Cena"

  @regressao
  Cenário: Exibir vídeo da biblioteca se não houver processamento
    Dado que uma cena possui apenas "video_url"
    E "captioned_video_url" e "generated_video_url" estão vazios
    Quando a cena é renderizada na lista
    Então o player deve exibir o vídeo de "video_url"
    E a etiqueta deve indicar "Cena Visual"

  Cenário: Não exibir player se nenhum vídeo existir
    Dado que uma cena não possui nenhuma URL de vídeo
    Quando a cena é renderizada na lista
    Então nenhum player de vídeo deve ser exibido para esta cena
