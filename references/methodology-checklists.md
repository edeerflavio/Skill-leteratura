# Checklists de metodologia (consulta rápida)

Use junto com `evidence-grading.md`. O objetivo aqui é **avaliar o risco de viés
por desenho de estudo** e dar rastreabilidade à revisão — não transformar toda
resposta em revisão sistemática.

## Regra de escalonamento (quando aplicar o quê)

| Situação | Profundidade |
|---|---|
| Pergunta rápida, card/quiz, conferir uma afirmação | **Checklist leve** (abaixo) |
| Material de aula de alto impacto, conduta nova, algo controverso | **Checklist completo** do desenho relevante |
| Revisão para publicar / "estado da arte" formal | **PRISMA + PRESS + checklist por estudo + GRADE** |

Não aplique a ferramenta errada ao desenho errado: RoB 2 é só para RCT,
QUADAS-2 só para acurácia diagnóstica, etc. Use a tabela de seleção no fim.

### Checklist leve (toda revisão)
- [ ] O desenho do estudo responde ao tipo de pergunta? (ver `evidence-grading.md`)
- [ ] Desfecho é clínico ou substituto/surrogate?
- [ ] Tamanho amostral e IC95% reportados?
- [ ] Conflito de interesse / financiamento declarado?
- [ ] Resultado replicado em outra fonte recuperada nesta sessão?

---

## PRISMA 2020 — relato de revisões sistemáticas
Use quando **você** estiver montando uma síntese multi-fonte para publicar.
Itens mínimos a registrar:
- Pergunta em PICO/PECO e critérios de inclusão/exclusão **definidos antes**.
- Fontes buscadas + datas + estratégia de busca completa (ver PRESS).
- **Fluxo de triagem** com números: identificados → após dedup → triados
  (título/abstract) → texto completo avaliado → incluídos. Diga quantos saíram
  **e o motivo** em cada etapa.
- Risco de viés por estudo (ferramenta adequada abaixo).
- Síntese e certeza GRADE do conjunto.
> Mesmo numa revisão rápida, registrar "X identificados, Y após dedup, Z
> incluídos" já dá auditabilidade. O `merge_results.py` ajuda na etapa de dedup.

## PRESS — qualidade da estratégia de busca
Checklist mínimo antes de confiar numa busca:
- [ ] Termos MeSH/Emtree **+** texto livre (sinônimos, siglas, grafias)?
- [ ] Booleanos corretos (AND entre conceitos, OR dentro do conceito)?
- [ ] Filtros de data/idioma/espécie justificados (não escondendo evidência)?
- [ ] Buscou em ≥2 bases (PubMed + Europe PMC + OpenAlex)?
- [ ] Fez busca **contrafactual** (termos que trariam evidência contrária)?

## QUADAS-2 — risco de viés em estudos de ACURÁCIA DIAGNÓSTICA
**O mais relevante para POCUS.** 4 domínios (julgue cada um: baixo/alto/incerto):
1. **Seleção de pacientes** — amostra consecutiva/aleatória? Evitou caso-controle
   de acurácia (sadios vs doentes graves → infla sensibilidade)? Espectro real
   de pacientes?
2. **Teste índice (o US)** — interpretado **cego** ao padrão-ouro? Ponto de corte
   definido **antes**? Quem operou (emergencista/intensivista vs radiologista)?
3. **Padrão-ouro (referência)** — classifica corretamente a doença? Interpretado
   cego ao resultado do US?
4. **Fluxo e tempo** — intervalo adequado entre índice e padrão-ouro? **Todos**
   os pacientes receberam o mesmo padrão-ouro e entraram na análise?
> Sinalize sempre concordância inter-observador (kappa) — central em POCUS.

## RoB 2 — risco de viés em RCT
5 domínios (baixo / alguma preocupação / alto):
1. Processo de **randomização** (sequência + sigilo de alocação + basais).
2. Desvios da intervenção pretendida (cegamento; análise por intenção-de-tratar).
3. **Dados de desfecho faltantes** (perdas de seguimento equilibradas/explicadas).
4. Mensuração do desfecho (avaliador cego; método adequado).
5. **Seleção do resultado relatado** (registro/protocolo prévio; sem cherry-picking).

## ROBINS-I — risco de viés em estudos NÃO randomizados de intervenção
7 domínios; trata o observacional como "RCT-alvo" emulado:
1. **Confundimento** (o maior risco aqui).
2. Seleção dos participantes.
3. Classificação da intervenção.
4. Desvios da intervenção pretendida.
5. Dados faltantes.
6. Mensuração do desfecho.
7. Seleção do resultado relatado.
> Julgamento global tende a ser ≥ "moderado" — confundimento residual quase sempre existe.

## AMSTAR-2 — qualidade de uma REVISÃO SISTEMÁTICA que você vai citar
Itens **críticos** (falha aqui rebaixa muito a confiança na revisão):
- Protocolo registrado **antes** (PROSPERO)?
- Busca abrangente e justificada?
- Lista de estudos **excluídos** com motivo?
- Risco de viés dos estudos incluídos avaliado **e** considerado nas conclusões?
- Métodos de meta-análise adequados?
- Viés de publicação investigado?
- Conflitos de interesse (revisão e estudos) declarados?
> Confiança final: alta / moderada / baixa / criticamente baixa.

## STARD / CONSORT — qualidade de RELATO (não de viés)
- **STARD**: checklist de relato de estudos de acurácia diagnóstica. Falta de
  dados (ex.: não diz quem operou o US, não dá IC) = relato incompleto → cite com ressalva.
- **CONSORT**: checklist de relato de RCT. Use para detectar lacunas no relato.

---

## Tabela de seleção rápida
| Tenho em mãos… | Ferramenta de risco de viés |
|---|---|
| RCT | **RoB 2** |
| Estudo de acurácia diagnóstica (POCUS) | **QUADAS-2** (+ STARD p/ relato) |
| Coorte / caso-controle / antes-depois | **ROBINS-I** |
| Revisão sistemática / meta-análise que vou citar | **AMSTAR-2** |
| Eu montando a síntese multi-fonte | **PRISMA** (fluxo) + **PRESS** (busca) |
| Certeza do CONJUNTO da evidência | **GRADE** (`evidence-grading.md`) |
