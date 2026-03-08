---
type: doc
name: project-overview
description: High-level overview of the project, its purpose, and key components
category: overview
generated: 2026-03-05
status: active
scaffoldVersion: "2.0.0"
---

# Visão Geral do Projeto

> Snapshot gerado. Não autoritativo.
> Veja [`../../AGENTS.md`](../../AGENTS.md), [`../../README.md`](../../README.md) e [`../../WORKSPACE.md`](../../WORKSPACE.md) como fontes canônicas.

## O que é este projeto

`01-monorepo` é um **workspace local-first e orientado a eventos para assistência de desenvolvimento com IA**, projetado para entrega de software controlada e guiada por humanos.

Fornece uma camada de orquestração governada para trabalho de software assistido por IA — não uma empresa de software autônoma. Toda ação significativa é mediada por eventos explícitos, autoridade do CI e gates de aprovação humana.

## Pilares do Design

- **Local-first** — runtime e roteamento de modelos executam inteiramente na máquina do desenvolvedor
- **Orientado a eventos** — orquestração de tarefas via Redis Streams (único barramento de orquestração)
- **Persistência de DAG no Redis** — grafos de workflow com estado e recuperação
- **Quatro agentes mínimos**: Planner, Coder, Tester, Reviewer — cada um com responsabilidades fixas
- **Workflow com autoridade do CI** — o CI é a fonte da verdade para validade do código
- **Aprovação humana obrigatória antes do merge** — nenhum merge autônomo para `main`
- **Guardrails aplicados em código**, não apenas em documentação

## O que este projeto NÃO é

- Não é uma empresa de software autônoma ou engenheiro totalmente autodirigido
- Não é um sistema onde agentes se comunicam diretamente entre si
- Não é um sistema onde o CI pode ser contornado ou simulado pela saída dos agentes
- Ainda não está endurecido para produção (veja maturidade abaixo)

## Maturidade Atual

**Pré-produção com um núcleo de orquestração real.**

### Totalmente Implementado

- Barramento de eventos Redis Streams com consumer groups
- Loop de eventos do scheduler com persistência de DAG no Redis
- Orquestração de fix-loop com autoridade do CI
- Aplicação de guardrails em código (dispatch, transições, ownership)
- Eventos `audit_log` estruturados no stream `system_events`
- Validação de escrita de memória em runtime (rejeita transcrições brutas)
- Métricas do scheduler e snapshot de saúde no Redis
- Idempotência de eventos duplicados e tratamento de dead-letter
- Aplicação de fonte confiável para tarefas de sistema protegidas

### Parcialmente Implementado

- Vários nós LangGraph ainda utilizam comportamento de execução placeholder
- Adaptadores de ferramentas são contracts-first, ainda não totalmente endurecidos
- O fluxo local Gitea/Argo está scaffolded mas não totalmente exercitado de ponta a ponta
- Memória de longo prazo é um sink no Redis em runtime, não uma camada de conhecimento durável

## Agentes Principais

| Agente | Responsabilidade |
|--------|-----------------|
| Planner | Interpreta requisições e prepara insumos de planejamento |
| Coder | Escreve apenas código de implementação |
| Tester | Possui testes e fixtures apenas |
| Reviewer | Valida qualidade, consistência e guardrails |

Agentes se comunicam exclusivamente via Redis Streams — sem chamadas diretas entre agentes.

## Próximos Marcos

1. Substituir os caminhos de execução LangGraph placeholder restantes
2. Endurecer execução de ferramentas com política e captura de artefatos
3. Exercitar o loop Gitea/Argo local de ponta a ponta
4. Expandir observabilidade e fluxos de inspeção de auditoria
5. Evoluir memória de longo prazo além do sink Redis atual

## Docs Relacionados

- [Arquitetura](./architecture.md)
- [Workflow de Desenvolvimento](./development-workflow.md)
- [Segurança e Guardrails](./security.md)
- [README raiz](../../README.md)
- [WORKSPACE.md](../../WORKSPACE.md)
