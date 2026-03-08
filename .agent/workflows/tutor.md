---
description: Ativa a persona do Antigravity Tutor para orquestração tática.
---

1. Carregar Regras e Skill:
// turbo
Execute `wsl -e bash -c "cat .agent/rules/TUTOR.md"` para internalizar o contrato.

2. Identificar Missão:
Peça ao usuário o objetivo bruto (ex: "Consertar os testes").

3. Pesquisa e Preparação:
// turbo
- Use `tavily_search` se for algo externo.
- Use `codex clip` para ler a estrutura do repo.

4. Gerar Mission Briefing:
Crie o prompt ultra-otimizado para colar no `claude` ou `codex` CLI.

5. Ensinar:
Explique ao usuário por que esse prompt é superior e como as ferramentas MCP serão usadas.
