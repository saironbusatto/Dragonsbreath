# Campanha: O Lamento do Bardo

## Metadados

| Atributo    | Valor                                                    |
|-------------|----------------------------------------------------------|
| ID          | `lamento_do_bardo`                                       |
| Classe      | Bardo                                                    |
| Tom         | Gótico, melancólico, misterioso                          |
| HP Inicial  | 20                                                       |
| Atos        | 3                                                        |
| Antagonista | Kael (dragão negro disfarçado de bardo)                 |
| Tema        | Perda, memória, ilusão, o poder da música               |

---

## Sinopse

Em Umbraton, uma cidade gótica envolta em névoa eterna, uma praga musical misteriosa está silenciando músicos — não apenas suas vozes, mas sua vontade de viver. O jogador, um Bardo viúvo, chega à cidade em busca de respostas sobre melodias que ecoam como a voz de sua amada morta.

O que parece ser uma praga natural revela-se uma armadilha orquestrada por Kael, um dragão negro ancião que descobriu como extrair emoções humanas através da música, alimentando-se do desespero alheio.

---

## Personagens

### Kael
**Papel:** Antagonista principal
**Aparência fácil:** Bardo sábio e carismático, viajante há décadas, oferece conforto musical
**Verdade oculta:** Dragão negro ancião que manipula através da música para extrair emoções
**Localização Ato 1:** Taverna do Corvo Ferido (encontro inicial)
**Localização Ato 2:** Santuário da Harmonia
**Localização Ato 3:** Câmara interna do Santuário (forma verdadeira revelada)

---

### Virella
**Papel:** Cultista (vítima)
**Aparência fácil:** Sacerdotisa carismática com voz hipnótica, lidera um culto de "cura"
**Verdade oculta:** Sob influência mágica de Kael, recruta voluntários para a praga
**Localização:** Santuário da Harmonia (Ato 2)

---

### Irmão Ellun
**Papel:** Cultista menor
**Aparência fácil:** Monge devoto e gentil que oferece consolo espiritual
**Verdade oculta:** Seleciona as vítimas mais vulneráveis para Kael
**Localização:** Umbraton → Santuário (Atos 1-2)

---

### Lysenn
**Papel:** Aliado
**Aparência:** Ex-aprendiz de Kael, agora cego e fugitivo, carrega conhecimento fragmentado
**Verdade:** Sabe o que Kael é, mas teme revelar diretamente
**Localização:** Escondido nos becos de Umbraton (Ato 1)

---

### Silas
**Papel:** Neutro / Vendedor de informações
**Aparência fácil:** Mercador afável de relíquias musicais raras
**Verdade oculta:** Sabe que a praga está ligada ao comércio de emoções engarrafadas, mas vende para os dois lados
**Localização:** Mercado de Umbraton (Ato 1)

---

### Elian
**Papel:** NPC menor
**Descrição:** Historiador da cidade com suspeitas sobre padrões antigos da praga
**Localização:** Biblioteca de Umbraton (Ato 1)

---

### Lyra
**Papel:** NPC menor com missão secundária
**Descrição:** Mulher desesperada buscando seu irmão desaparecido
**Irmão:** Membro silencioso do culto no Santuário
**Localização:** Portões de Umbraton (Ato 1)

---

## Localizações

### Umbraton
**Descrição:** Cidade gótica de pedra cinzenta e lanternas de chamas azuladas. As ruas vibram com um silêncio musical perturbador — músicos que antes cantavam agora têm olhar vazio.

**Pontos de interesse:**
- Portões da cidade (início)
- Mercado central (Silas)
- Biblioteca (Elian)
- Becos escuros (Lysenn)
- Igreja silenciosa (irmão de Lyra)

**Gatilhos narrativos:**

| ID                  | Descrição                                              | SFX       | Próximo              |
|---------------------|--------------------------------------------------------|-----------|----------------------|
| `corvo_na_gargula`  | Corvo pousa em gárgula; diário vibra                   | corvo     | `diario_vibra`       |
| `diario_vibra`      | Diário vibra com intensidade; quer ser aberto           | —         | (fim da cadeia)      |
| `crianca_correndo`  | Criança passa correndo e para ao ver o personagem       | crianca   | `sino_toca`          |
| `sino_toca`         | Sino da igreja toca fora de hora                       | —         | (fim da cadeia)      |
| `grito_viela`       | Grito vindo de uma viela próxima                        | scream    | (fim da cadeia)      |

---

### Taverna do Corvo Ferido
**Descrição:** Taverna de madeira escura e velha, cheira a fumaça de lareira e cerveja azeda. É onde viajantes e músicos se encontram — ou costumavam se encontrar.

**Gatilhos narrativos:**

| ID                    | Descrição                                                    | SFX        | Próximo                |
|-----------------------|--------------------------------------------------------------|------------|------------------------|
| `taverneiro_se_cala`  | Taverneiro para de falar ao meio da frase, olha para a porta | —          | `figura_encapuzada`    |
| `figura_encapuzada`   | Figura encapuzada entra e senta no canto mais escuro         | —          | (fim da cadeia)        |
| `musica_familiar`     | Melodia familiar toca ao fundo, insuportavelmente bonita     | familiar1  | `sussurro_praga`       |
| `sussurro_praga`      | Sussurro vindo de nenhum lugar: "ela ainda ecoa..."         | familiar2  | (fim da cadeia)        |

---

## Estrutura de Atos

### Ato 1: O Eco da Perda
**Missão principal:** Investigar a praga musical de Umbraton

**Arco narrativo:**
1. Chegada a Umbraton — cidade estranhamente silenciosa
2. Primeiros sinais da praga (músicos com olhar vazio)
3. Encontro com Lyra (missão secundária: irmão desaparecido)
4. Descoberta de Silas e pistas comerciais
5. Encontro com Lysenn (fragmentos de verdade)
6. Primeiro encontro com Kael na taverna (aparece como aliado)
7. Missão: rastrear origem das melodias estranhas

**Recompensa ao completar:** Anel do Sussurro

**Escolha dramática:** O personagem pode ouvir ecos da voz de sua amada morta nas melodias. Investigar ou ignorar?

---

### Ato 2: A Harmonia da Mentira
**Missão principal:** Infiltrar o Santuário da Harmonia

**Arco narrativo:**
1. Virella oferece "cura" através do Santuário
2. Encontro com o culto — parecem genuinamente aliviados
3. Kael como mestre do Santuário — aparentemente benigno
4. Chá da Ausência oferecido — apaga memórias dolorosas
5. Crise moral: aceitar o esquecimento ou manter a dor da perda?
6. Descoberta que Irmão Ellun seleciona vítimas
7. Revelação parcial: Kael extrai emoções, não apenas cura

**Itens disponíveis:**
- Lira das Mentiras (vibra quando alguém mente)
- Cristal de Memória (registrar uma memória antes de perder)
- Chá da Ausência (consumível perigoso — apaga memória)

**Escolha dramática central:** Beber o Chá da Ausência (esquecer a amada e a dor) ou resistir (manter a dor mas a identidade)?

---

### Ato 3: A Canção da Verdade
**Missão principal:** Deter Kael e encerrar a praga

**Arco narrativo:**
1. Descoberta da forma verdadeira de Kael (dragão negro)
2. Câmara interna revela o ritual completo
3. Lysenn aparece para confirmar a verdade e fornecer a chave
4. Confronto final: Melodia Final vs Pergaminho da Canção Invertida
5. Resolução: derrota, selamento ou transformação de Kael

**Mecânica do confronto final:**
- Melodia Final (Lendário) — 90% de chance de transformar Kael, 10% de destruí-lo
- Pergaminho da Canção Invertida (Raro) — silencia magia musical permanentemente
- Diapasão de Prata Pura (Raro) — interfere nos rituais de Kael

**Recompensa:** Título de Libertador de Umbraton

---

## Itens Mágicos

| Nome                         | Raridade  | Slots | Efeito                                                          |
|------------------------------|-----------|-------|----------------------------------------------------------------|
| Anel do Sussurro              | Incomum   | 1     | Entender melodias mágicas; resistir a ilusões sônicas           |
| Lira das Mentiras             | Incomum   | 2     | Vibra quando alguém próximo está mentindo                       |
| Cristal de Memória            | Raro      | 1     | Gravar e reviver uma memória com total clareza                  |
| Pergaminho da Canção Invertida| Raro      | 1     | Silenciar permanentemente um efeito de magia sonora             |
| Símbolo do Arrependido        | Raro      | 1     | Aquece ao sentir feitiços de controle mental                   |
| Melodia Final                 | Lendário  | 2     | Canção que altera a realidade (90% transforma, 10% destrói)     |
| Diapasão de Prata Pura        | Raro      | 1     | Interfere nos rituais de Kael                                   |

---

## Itens Comuns

| Nome                    | Slots | Tipo         | Efeito                                        |
|-------------------------|-------|--------------|-----------------------------------------------|
| Chá da Ausência          | 1     | Consumível   | Cura dor emocional, apaga memória relacionada |
| Livro de Acústica Antiga  | 2     | Item chave   | Como neutralizar magia musical                |
| Instrumentos Quebrados   | 1     | Simbólico    | Pistas sobre vítimas da praga                 |
| Folhas da Árvore Rara    | 1     | Crafting     | Ingrediente para antídotos                    |
| Poção de Cura            | 1     | Consumível   | +10 HP                                        |
| Alaúde de Madeira        | 2     | Equipamento  | Instrumento do Bardo (inventário inicial)     |
| Adaga                    | 1     | Arma         | Defesa básica (inventário inicial)            |
| Mochila                  | 1     | Utilidade    | Sem efeito mecânico (inventário inicial)      |
| Kit Viagem               | 1     | Utilidade    | Suprimentos básicos (inventário inicial)      |
| Kit Iluminação           | 1     | Utilidade    | Lanterna e velas (inventário inicial)         |

---

## Temas e Atmosfera

### Tom da Narrativa
- **Cores:** Cinzas, azuis escuros, preto, dourado envelhecido
- **Sons:** Melodias distorcidas, silêncios pesados, vento uivando
- **Emoções predominantes:** Nostalgia, luto, desconfiança, esperança frágil

### Questões Filosóficas
1. A memória dolorosa é preferível ao esquecimento indolor?
2. A música pode ser arma tanto quanto cura?
3. Quanto da identidade está na perda que carregamos?

### Modelo de Dualidade (NPCs)
Todo personagem importante tem camadas:
- O que parece ser → O que realmente é
- Kael: mentor sábio → dragão predador
- Virella: sacerdotisa da cura → vítima que perpetua o ciclo
- Silas: mercador neutro → cúmplice por lucro
