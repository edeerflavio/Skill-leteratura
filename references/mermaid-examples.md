# Padrões Mermaid para Visualizações

## Cores Padronizadas

### Paleta de Cores (Copie e cole)
```
Azul (Início/Info): fill:#4A90E2,stroke:#2E5C8A,color:#fff
Laranja (Decisão): fill:#F5A623,stroke:#C87E0A,color:#fff
Verde (Ação Positiva): fill:#7ED321,stroke:#5FA019,color:#fff
Vermelho (Alerta/Urgente): fill:#D0021B,stroke:#9A0115,color:#fff
Roxo (Neurológico): fill:#9013FE,stroke:#6B0FB8,color:#fff
Rosa (Hemodinâmica): fill:#FF6B9D,stroke:#C44570,color:#fff
Cinza (Fim/Observação): fill:#8E8E93,stroke:#636366,color:#fff
Amarelo (Atenção): fill:#FFD60A,stroke:#C4A508,color:#000
```

## 1. Fluxograma Clínico (Flowchart)

### Exemplo: Manejo de PCR
```mermaid
flowchart TD
    A[Paciente em PCR] --> B{Ritmo Chocável?}
    B -->|Sim - FV/TV| C[Desfibrilar 200J]
    B -->|Não - Assistolia/AESP| D[RCP 2min]
    C --> E[RCP 2min]
    E --> F{ROSC?}
    D --> F
    F -->|Sim| G[Admitir UTI]
    F -->|Não| H{Reversível?}
    H -->|Sim| I[Tratar Causa]
    H -->|Não| J[Continuar RCP]
    I --> F
    J --> F
    G --> K[Cuidados Pós-PCR]
    
    style A fill:#D0021B,stroke:#9A0115,color:#fff
    style B fill:#F5A623,stroke:#C87E0A,color:#fff
    style C fill:#7ED321,stroke:#5FA019,color:#fff
    style D fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style E fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style F fill:#F5A623,stroke:#C87E0A,color:#fff
    style G fill:#7ED321,stroke:#5FA019,color:#fff
    style H fill:#F5A623,stroke:#C87E0A,color:#fff
    style I fill:#FFD60A,stroke:#C4A508,color:#000
    style J fill:#FF6B9D,stroke:#C44570,color:#fff
    style K fill:#7ED321,stroke:#5FA019,color:#fff
```

### Estrutura Base
```mermaid
flowchart TD
    Inicio[Situação Inicial] --> Decisao{Pergunta?}
    Decisao -->|Opção 1| Acao1[Fazer X]
    Decisao -->|Opção 2| Acao2[Fazer Y]
    Acao1 --> Fim1[Resultado]
    Acao2 --> Fim2[Resultado]
    
    style Inicio fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style Decisao fill:#F5A623,stroke:#C87E0A,color:#fff
    style Acao1 fill:#7ED321,stroke:#5FA019,color:#fff
    style Acao2 fill:#7ED321,stroke:#5FA019,color:#fff
    style Fim1 fill:#8E8E93,stroke:#636366,color:#fff
    style Fim2 fill:#8E8E93,stroke:#636366,color:#fff
```

## 2. Mapa Mental (OBRIGATÓRIO ao final)

### Exemplo: Resumo de Estudo sobre Sepse
```mermaid
mindmap
  root((Sepse e Lactato
    JAMA 2025))
    🎯 Mensagem Principal
      Lactato inicial >2 mmol/L
      Mortalidade aumenta 15%
      Reavaliar a cada 2h
    🔬 Metodologia
      RCT multicêntrico
      N=1200 pacientes
      18 UTIs brasileiras
    📊 Resultados
      Desfecho Primário
        Mortalidade 28 dias
        21% vs 28% (p=0.002)
      Secundários
        Tempo de UTI reduzido
        Menos disfunção orgânica
    🏥 Aplicabilidade
      Sepse e choque séptico
      Protocolo de 6h
      Medir lactato seriado
    ⚠️ Limitações
      Centros terciários
      Seguimento curto
```

### Estrutura Base para Diretrizes
```mermaid
mindmap
  root((Título da Diretriz))
    🔄 Mudanças Principais
      Mudança 1
      Mudança 2
      Mudança 3
    📋 Recomendações Fortes
      Sistema 1
        Recomendação A
        Recomendação B
      Sistema 2
        Recomendação C
    🔬 Base de Evidências
      GRADE Alto
      Estudos-chave
    🏥 Implementação
      Etapa 1
      Etapa 2
```

### Estrutura Base para Estudos
```mermaid
mindmap
  root((Título do Estudo))
    🎯 Mensagem Principal
      Achado 1
      Achado 2
    🔬 Metodologia
      Tipo de Estudo
      População N
      Intervenção
    📊 Resultados
      Desfecho Primário
        Valor p
        IC 95%
      Secundários
        Resultado 1
        Resultado 2
    💡 Pontos-Chave
      Forças
        Força 1
        Força 2
      Limitações
        Limitação 1
    🏥 Aplicabilidade
      Para quem
      Quando aplicar
      Como implementar
```

## 3. Protocolo por Sistemas

### Exemplo: Protocolo Pós-PCR
```mermaid
flowchart LR
    subgraph Neuroproteção
        A[TTM ≤37.5°C] --> B[Sedação adequada]
        B --> C[EEG contínuo]
    end
    
    subgraph Hemodinâmica
        D[MAP ≥65 mmHg] --> E[Noradrenalina]
        E --> F[Volemia otimizada]
    end
    
    subgraph Respiratório
        G[SpO₂ 94-98%] --> H[PaCO₂ 35-45]
        H --> I[PEEP 5-8]
    end
    
    C --> J[Avaliar 72h]
    F --> J
    I --> J
    
    style A fill:#9013FE,stroke:#6B0FB8,color:#fff
    style B fill:#9013FE,stroke:#6B0FB8,color:#fff
    style C fill:#9013FE,stroke:#6B0FB8,color:#fff
    style D fill:#FF6B9D,stroke:#C44570,color:#fff
    style E fill:#FF6B9D,stroke:#C44570,color:#fff
    style F fill:#FF6B9D,stroke:#C44570,color:#fff
    style G fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style H fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style I fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style J fill:#7ED321,stroke:#5FA019,color:#fff
```

## 4. Timeline de Intervenções

### Exemplo: Protocolo de Sepse
```mermaid
gantt
    title Protocolo de Sepse (Primeira Hora)
    dateFormat HH:mm
    axisFormat %H:%M
    
    section Diagnóstico
    Lactato sérico           :done, 00:00, 5m
    Hemoculturas (2 sets)    :done, 00:05, 10m
    
    section Intervenção
    Antibiótico empírico     :crit, 00:15, 15m
    Reposição volêmica       :active, 00:30, 30m
    
    section Monitorização
    Reavaliação lactato      :00:55, 5m
```

## Quando Usar Cada Tipo

**Flowchart:** Algoritmos clínicos, protocolos de decisão, processos sequenciais
**Mindmap:** SEMPRE ao final de CADA resumo (obrigatório)
**Subgraphs:** Protocolos multi-sistema (cardio, neuro, respiratório)
**Timeline (Gantt):** Protocolos com timing específico (primeira hora, primeiras 6h)

## Regras de Estilo

1. **Use losangos `{}` para decisões** - sempre laranja
2. **Use retângulos `[]` para ações** - verde se positiva, azul se neutra
3. **Use cores por sistema:**
   - 🧠 Neurológico: Roxo
   - 💓 Hemodinâmica: Rosa
   - 🫁 Respiratório: Azul
   - ⚠️ Urgente/Crítico: Vermelho
   - ✅ Sucesso/Fim positivo: Verde
   - 🔍 Observação/Fim neutro: Cinza

4. **Sempre use style no final** para aplicar cores

## Dica: Teste Rápido
Cole no visualizador: https://mermaid.live/
