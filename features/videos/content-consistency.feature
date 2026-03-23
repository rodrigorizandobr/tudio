# language: pt
Funcionalidade: Consistência de Conteúdo das Cenas
  Como Creator
  Eu quero que cada cena do vídeo tenha sua legenda, narração e imagem únicas e corretas
  Para que o vídeo final seja profissional e sem repetições indevidas

  Contexto:
    Dado que o vídeo possui múltiplos capítulos e subcapítulos
    E múltiplas cenas com o mesmo índice relativo (ex: capítulo 1 e 2 ambos têm cena 1)

  @critico @smoke
  Cenário: Cenas legendadas devem ser únicas e não sobrescrever umas às outras
    Quando os processos de legenda são disparados para todas as cenas
    Então cada cena deve gerar um arquivo de vídeo com legenda único no storage
    E o campo captioned_video_url de cada cena deve apontar para seu respectivo arquivo
    E não deve haver repetição visual de legendas entre cenas que têm narrações diferentes

  @critico
  Cenário: Respeitar o aspecto ratio (horizontal/vertical) no cache de cenas
    Dado que o vídeo suporta os formatos 16:9 e 9:16
    Quando gero as cenas para o formato 16:9
    E depois gero as cenas para o formato 9:16
    Então os clips do formato 9:16 não devem usar os arquivos gerados para o formato 16:9
    E o vídeo final horizontal deve conter apenas cenas em 1920x1080
    E o vídeo final vertical deve conter apenas cenas em 1080x1920

  @performance
  Cenário: O cache de cenas deve funcionar corretamente para o mesmo ratio
    Dado que uma cena já foi gerada com sucesso para o formato 16:9
    Quando solicito a renderização das cenas para 16:9 novamente
    Então o sistema deve reutilizar o clip existente para economizar tempo de CPU
