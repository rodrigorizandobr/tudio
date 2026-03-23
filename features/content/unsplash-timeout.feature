# language: pt
Funcionalidade: Otimização de Timeout do Unsplash
  Como Creator
  Eu quero que a busca de imagens tenha um tempo de resposta controlado
  Para que falhas na API do Unsplash não travem a geração do vídeo por muito tempo

  @critico @performance
  Cenário: Busca de imagens com timeout de 5 segundos
    Dado que a API do Unsplash está lenta (demorando mais de 5 segundos)
    Quando o sistema tentar buscar imagens para uma cena
    Então a requisição deve falhar por timeout em exatamente 5 segundos
    E o sistema deve logar o erro e continuar o fluxo sem travar
