---
type: doc
name: security
description: Security policies, authentication, secrets management, and compliance requirements
category: security
generated: 2026-03-05
status: active
scaffoldVersion: "2.0.0"
---

# Segurança e Conformidade

> Snapshot gerado. Não autoritativo.
> Veja [`../../AGENTS.md`](../../AGENTS.md) e [`../../GUARDRAILS.md`](../../GUARDRAILS.md) como fontes canônicas.

**Fonte canônica:** `GUARDRAILS.md`

O objetivo do modelo de segurança deste sistema é simples: **guardrails devem ser verdadeiros porque o código os aplica, não porque os docs os afirmam.**

## Guardrails Aplicados (Ativos em Código)

Esses controles estão implementados e ativos no caminho do scheduler (`workspace/scheduler/guardrail_enforcer.py`, `service.py`, `dispatcher.py`):

- Coordenação entre agentes deve passar pelo Redis Streams — chamadas diretas entre agentes são proibidas
- Dispatch de tarefas requer prontidão de dependências — nenhuma tarefa executa antes que suas dependências completem
- Ownership de tarefas é aplicado: planner, coder, tester e reviewer possuem apenas tipos de tarefa específicos
- Transições inválidas de status de tarefas são rejeitadas (ex.: `pending → completed`, `running → ready`)
- Coder não pode modificar testes ou configurações de CI
- Tester pode modificar apenas testes e fixtures — não pode enfraquecer testes para forçar CI verde
- Reviewer pode bloquear a progressão do grafo
- Tarefas CI-gated ficam bloqueadas até que `ci_passed` seja recebido em `ci_events`
- Dispatch de `merge_task` requer aprovação humana registrada — merge sem aprovação é rejeitado
- Orçamentos de retry aplicados — tratamento de dead-letter roteia tarefas esgotadas para atenção humana
- Fontes de conclusão confiáveis aplicadas para `human_approval_gate`, `merge_task` e `rerun_ci`
- Eventos duplicados do scheduler são ignorados antes de mutação de estado e registrados em `audit_log`
- Validação de payload de memória bruta aplicada no caminho de escrita do runtime, não apenas em verificações de dry-run
- Eventos `audit_log` estruturados emitidos para todas as decisões de orquestração aceitas/rejeitadas, tratamento de CI, bloqueios do gate de merge e rejeições de memória

## Lacunas Restantes

Esses controles ainda precisam de endurecimento além da implementação atual:

- Política de execução de ferramentas e controle de escopo do filesystem precisam de aplicação em runtime além de documentação e contratos
- Logs de auditoria de prompts, ações e artefatos ainda não são completos o suficiente para análise completa de incidentes em produção
- Regras de tratamento de segredos existem, mas controles de redação e armazenamento de ponta a ponta ainda não estão totalmente conectados

## Políticas Inegociáveis

- Nenhuma tarefa pode contornar o CI como fonte da verdade
- Nenhuma tarefa pode fazer merge para `main` sem aprovação humana
- Nenhuma transcrição de conversa bruta pertence à memória de longo prazo
- Nenhum agente deve mutar arquivos fora do escopo do repositório selecionado
- Nenhum agente deve publicar sucesso falso para substituir resultados do CI
- Nenhuma ação destrutiva ou privilegiada deve ocorrer sem um caminho explícito de aprovação

## Camadas de Aplicação Operacional

| Camada | Mecanismo |
|--------|----------|
| Fonte de política | `guardrails/*.rules` — políticas narrativas e legíveis por máquina |
| Validação do scheduler | Verificações de dispatch, resultado e transição antes do grafo avançar |
| Autoridade do CI | Argo publica resultados de CI; scheduler reage a eventos em vez de inferir da saída dos agentes |
| Dead-letter e alertas | Falha repetida ou transições inválidas → atenção humana via `system_alert` |
| Validação de memória | Rejeição de transcrição bruta no caminho de escrita do runtime |

## Padrão de Prontidão para Produção

Antes de chamar de pronto para produção, o repositório precisa de:

- Execução de ferramentas auditada com logs duráveis
- Validação mais profunda de integração Gitea e Argo além do scaffolding local atual
- Observabilidade mais rica além dos contadores e hashes Redis atuais

## Docs Relacionados

- [GUARDRAILS.md](../../GUARDRAILS.md)
- [Arquitetura](./architecture.md)
- [Fluxo de Dados e Integrações](./data-flow.md)
