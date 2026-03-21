# Modo Contos Interativos

## Visão Geral

O Modo Contos Interativos é uma experiência de narrativa branching baseada em obras literárias clássicas adaptadas. Diferente do RPG, aqui o jogador faz escolhas estruturadas (A/B/C) que influenciam variáveis dinâmicas e determinam o final da história.

A proposta é aproximar o usuário da literatura clássica através de experiência imersiva com áudio e IA.

---

## Arquitetura de um Conto

Cada conto é composto por dois arquivos:

```
contos_interativos/
├── {nome_conto}.txt              # Texto original completo
└── {nome_conto}_eventos.json     # Mapa de eventos e escolhas
```

### O arquivo `.txt`
Contém o texto original da obra literária ou adaptação. É fornecido integralmente ao Gemini como **referência de estilo** — o Mestre dos Contos deve narrar com a voz, vocabulário e atmosfera do autor original.

### O arquivo `_eventos.json`
Define o grafo de eventos com escolhas e efeitos:

```json
{
  "inicio": {
    "descricao_para_ia": "Abertura — câmara escura, meia-noite, o narrador ansioso ouve batidas na porta. Lenore foi amada e perdida.",
    "opcoes": [
      {
        "texto": "(A) Abrir a porta imediatamente",
        "efeito": {"esperanca": 1, "obsessao": -1},
        "proximo_evento": "porta_aberta"
      },
      {
        "texto": "(B) Hesitar, ouvir o silêncio primeiro",
        "efeito": {"sanidade": -1, "obsessao": 1},
        "proximo_evento": "silencio_antes"
      },
      {
        "texto": "(C) Mergulhar nos livros para ignorar",
        "efeito": {"aceitacao": 1},
        "proximo_evento": "livros_conforto"
      }
    ]
  },

  "final_aceitacao": {
    "descricao_para_ia": "Final da aceitação — o narrador encontra paz ao honrar a memória de Lenore sem ser destruído por ela.",
    "opcoes": []
  }
}
```

---

## Variáveis Dinâmicas

São valores numéricos que mudam com as escolhas e determinam o final.

### Exemplo — "O Corvo" (Edgar Allan Poe)

| Variável    | Inicial | Range | Significado                                   |
|-------------|---------|-------|-----------------------------------------------|
| `sanidade`  | 5       | 0-10  | Estabilidade mental                           |
| `esperanca` | 5       | 0-10  | Capacidade de encontrar sentido               |
| `obsessao`  | 2       | 0-5   | Fixação na perda e no passado                 |
| `aceitacao` | 3       | 0-10  | Capacidade de seguir em frente                |

Essas variáveis são fornecidas ao Gemini para que ele **colore a narrativa** de acordo com o estado psicológico do personagem.

```
sanidade=2, obsessao=5: narrativa mais sombria, paranoica, fragmentada
sanidade=8, aceitacao=7: narrativa mais serena, contemplativa, poética
```

---

## Mapeamento de Finais

Os finais são eventos sem opções (`"opcoes": []`). O roteamento para o final correto é feito pelo próprio grafo de eventos — as escolhas do jogador naturalmente levam a caminhos diferentes.

### Finais de "O Corvo"

| Final             | ID                 | Condição narrativa                                 |
|-------------------|--------------------|----------------------------------------------------|
| Desespero         | `final_desespero`  | Alta obsessão, baixa aceitação, espiral sombria    |
| Violência         | `final_violencia`  | Tentativa de resolver pela força o insolúvel       |
| Aceitação         | `final_aceitacao`  | Equilíbrio entre memória e seguir em frente        |
| Despertar         | `final_despertar`  | Confronto com os próprios demônios internos        |

---

## O Papel do Gemini como Story Master

O Gemini recebe um prompt especializado diferente do RPG:

### Instruções do Story Master:
1. Localizar o evento atual no mapa de eventos
2. Narrar usando o **estilo do texto original** (vocabulário, tom, ritmo)
3. Apresentar **exatamente** as opções (A), (B), (C) — sem adicionar, sem remover
4. Terminar sempre com as opções claramente formatadas
5. Usar as variáveis dinâmicas para matizar a narração
6. Nunca quebrar a quarta parede ou explicar mecânicas

### Exemplo de prompt:
```
Você é o Mestre dos Contos, narrando "O Corvo" de Edgar Allan Poe.

TEXTO ORIGINAL (referência de estilo):
[conteúdo completo de o_corvo_poe.txt]

ESTADO ATUAL DAS VARIÁVEIS:
sanidade: 4, esperanca: 6, obsessao: 3, aceitacao: 4

EVENTO ATUAL:
ID: corvo_aparece
Descrição: O corvo entra pela janela e pousa no busto de Palas Atena.
Opções disponíveis:
(A) Questionar o corvo sobre Lenore
(B) Tentar afugentar o corvo
(C) Contemplar o corvo em silêncio

Narre este evento no estilo de Poe. Apresente as opções ao final.
```

---

## Estatísticas Finais

Ao atingir um evento final, o sistema exibe um resumo das variáveis:

```
═══════════════════════════════════
        FIM DE "O CORVO"
    Final: A Paz da Aceitação
═══════════════════════════════════

Sanidade:   ████████░░  8/10
Esperança:  ███████░░░  7/10
Obsessão:   ██░░░░░░░░  2/5
Aceitação:  █████████░  9/10

"A alma encontrou serenidade ao
 honrar o amor sem ser destruída
 por sua ausência."
═══════════════════════════════════
```

---

## Como Adicionar um Novo Conto

1. **Obter o texto original** e salvar em `contos_interativos/{nome}.txt`

2. **Criar o mapa de eventos** em `contos_interativos/{nome}_eventos.json`:
   - Definir variáveis dinâmicas relevantes para a história
   - Criar evento `"inicio"` como ponto de entrada
   - Criar pelo menos 2-4 eventos finais (`"final_*"` sem opções)
   - Mapear o grafo de escolhas entre início e finais

3. O sistema detecta automaticamente novos contos ao listar arquivos em `contos_interativos/`.

### Boas Práticas para Eventos:
- `descricao_para_ia` deve ser rico em contexto para o Gemini gerar boa narrativa
- Efeitos de escolha devem refletir a psicologia do personagem, não mecânicas simples
- Criar pelo menos 3 caminhos distintos para diferentes finais
- Nomear finais com prefixo `final_` para detecção automática

---

## Contos Disponíveis

### O Corvo — Edgar Allan Poe
- **Arquivo texto:** `o_corvo_poe.txt`
- **Arquivo eventos:** `o_corvo_poe_eventos.json`
- **Variáveis:** sanidade, esperanca, obsessao, aceitacao
- **Finais:** 4 (desespero, violência, aceitação, despertar)
- **Tema:** Luto, obsessão, perda irrecuperável
- **Atmosfera:** Gótica, onírica, poética
