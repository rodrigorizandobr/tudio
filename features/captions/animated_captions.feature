# language: pt
Funcionalidade: Legendas Animadas (Animated Captions)
  Como um Creator
  Eu quero gerar legendas animadas sincronizadas com o áudio
  Para que meus vídeos tenham mais engajamento e retenção

  Contexto:
    Dado que o usuário está autenticado
    E já possui um vídeo renderizado na lista de vídeos

  # ── Cenário Feliz ──────────────────────────────────────────────
  Cenário: Geração de legenda global para o vídeo
    Dado que o usuário está na página de detalhes do vídeo "completado"
    Quando o usuário clica no botão "Gerar Legenda" no card global de legendas
    Então o sistema deve exibir o progresso de geração na timeline
    E ao finalizar, os botões de download dos formatos (16:9, 9:16) devem incluir a versão com legenda
    E as legendas devem estar sincronizadas palavra-por-palavra no vídeo final

  Cenário: Geração de legenda para uma única cena
    Dado que o usuário está na página de detalhes do vídeo
    Quando o usuário clica no ícone de "Legenda" (📝) em uma cena específica
    Então o sistema deve processar os timestamps de áudio apenas para aquela cena
    E mostrar o badge "✓ Legenda" na cena quando concluído

  # ── Cenário de Erro ────────────────────────────────────────────
  Cenário: Tentativa de gerar legenda sem áudio na cena
    Dado que o usuário está na página de detalhes do vídeo
    E uma cena específica não possui narração ou áudio enviado
    Quando o usuário tenta gerar legenda para esta cena
    Então o sistema deve exibir uma mensagem de erro "Cena sem áudio"
    E não deve iniciar o processo de geração

  # ── Cenário de Performance ──────────────────────────────────────
  Cenário: Tempo de resposta para preview de legenda
    Dado que o usuário já gerou legendas para o vídeo
    Quando o usuário abre a página de visualização do vídeo
    Então a resposta do preview de legendas (/captions/preview) deve ser recebida em menos de 500ms
