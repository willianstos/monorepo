---
description: Auditoria Diamante completa do repositório antes de deploy. Varredura profunda de segurança, qualidade, performance e arquitetura.
trigger: /super-review
args: "[--fix] [--report-only]"
runner: cli
version: 1.0.0
---

# /super-review — Auditoria Diamante Pré-Deploy

## O que é

O workflow de **Super Review** é a última barreira de qualidade antes de qualquer deploy. Ele executa uma auditoria profunda e multidimensional em todo o repositório, cobrindo segurança, qualidade de código, performance, arquitetura e documentação. Segue o **Padrão Diamante** da Andru.ia: rigor máximo, zero tolerância a falhas críticas.

## Quando usar

- **OBRIGATÓRIO** antes de deploy para H1 (produção).
- Antes de abrir um PR importante.
- Após grandes refatorações ou merges.
- Quando solicitado: "auditar", "revisar tudo", "super review", "preparar para deploy".

## Quando NÃO usar

- Mudanças triviais (typos, docs-only) — use `/validate` em vez disso.
- Para substituir o CI remoto — este é um gate local.

## Guardrails

- Este workflow é **local-only** e não substitui o gate humano de PR nem o CI remoto.
- Requer ambiente Python 3.11+ e dependências de dev instaladas (`pip install -e .[dev]`).
- Se `--fix` for passado, a IA corrige automaticamente problemas seguros. Sem `--fix`, opera em modo report-only.
- Se `--report-only` for passado, nenhuma alteração é feita — apenas o relatório é gerado.

---

## Fluxo de Execução (6 Fases)

### FASE 1: Diagnóstico Diamante 🔍

**Objetivo:** Entender o estado atual do repositório antes de agir.

1. Listar todos os arquivos do projeto recursivamente.
2. Identificar a stack tecnológica (linguagens, frameworks, bancos de dados).
3. Mapear a arquitetura: pontos de entrada, módulos, dependências.
4. Identificar arquivos modificados recentemente (`git diff --stat HEAD~10`).
5. Classificar o repositório: "monorepo", "microserviço", "biblioteca", "aplicação".

**Saída:** Resumo do diagnóstico em 5-10 linhas.

---

### FASE 2: Limpeza de Ativos 🧹

**Objetivo:** Remover lixo, segredos expostos e arquivos que não devem existir.

// turbo
1. Verificar arquivos que NÃO devem estar no repositório:
   - OS: `.DS_Store`, `Thumbs.db`, `desktop.ini`
   - Logs: `*.log`, `npm-debug.log*`, `yarn-error.log*`
   - Temp: `*.tmp`, `*.temp`, `*.cache`, `*.swp`, `*.bak`
   - Build: `dist/`, `build/`, `.next/`, `out/`, `__pycache__/`, `*.pyc`
   - Deps: `node_modules/`, `vendor/`
   - Pessoais: `TODO.txt`, `NOTES.txt`, `scratch.*`, `test123.*`

2. **CRÍTICO — Busca de Segredos:**
   - Varrer por padrões: `password=`, `api_key=`, `token=`, `secret=`, `private_key=`
   - Verificar arquivos `.env` commitados (BLOQUEADOR se encontrado).
   - Verificar `*.pem`, `*.key`, `credentials.json`.
   - Se encontrar segredos: **PARAR e reportar como BLOQUEADOR CRÍTICO**.

3. Verificar `.gitignore`:
   - Existe? É completo?
   - Se faltar padrões críticos, adicionar (com `--fix`).

**Saída:** Lista de arquivos removidos ou sinalizados.

---

### FASE 3: Auditoria de Segurança 🛡️

**Objetivo:** Identificar e corrigir vulnerabilidades de segurança (OWASP Top 10).

1. **Injeção (SQL, Command, Path Traversal):**
   - Buscar concatenação de strings em queries SQL.
   - Buscar `exec()`, `eval()`, `os.system()` com input do usuário.
   - Buscar `innerHTML`, `dangerouslySetInnerHTML` com dados não sanitizados.

2. **Autenticação e Autorização:**
   - Rotas protegidas possuem middleware de autenticação?
   - Senhas são hasheadas com `bcrypt`/`argon2` (nunca MD5, SHA1, texto puro)?
   - Verificações de autorização existem no servidor (não só no UI)?

3. **Exposição de Dados:**
   - APIs não vazam informações desnecessárias?
   - Mensagens de erro não expõem stack traces ou detalhes de banco?
   - Endpoints de lista possuem paginação?

4. **Dependências:**

```bash
# Node.js
npm audit --audit-level=high 2>/dev/null || true

# Python
pip-audit 2>/dev/null || python -m pip check 2>/dev/null || true
```

**Saída:** Lista de vulnerabilidades classificadas como 🔴 CRÍTICO, 🟠 ALTO, 🟡 MÉDIO, 🔵 BAIXO.

---

### FASE 4: Qualidade de Código 📐

**Objetivo:** Elevar o código ao padrão corporativo.

1. **Código Morto (remover imediatamente com `--fix`):**
   - Blocos de código comentados.
   - Imports/requires não utilizados.
   - Variáveis declaradas mas nunca usadas.
   - Funções definidas mas nunca chamadas.

2. **Qualidade:**
   - Nomes vagos (`data`, `info`, `temp`, `thing`) → renomear.
   - Números mágicos (`if status === 3`) → extrair para constantes.
   - Statements de debug (`console.log`, `print()`, `debugger`) → remover.
   - Comentários TODO/FIXME → resolver ou documentar.
   - Funções > 50 linhas → considerar divisão.
   - Aninhamento > 3 níveis → refatorar com early returns.

3. **Análise Estática:**

```bash
# Python
python -m ruff check workspace projects && \
python -m mypy workspace && \
python -m compileall bootstrap workspace
```

```bash
# Node.js (se aplicável)
npx tsc --noEmit 2>/dev/null || true
npm run lint 2>/dev/null || true
```

**Saída:** Contagem de issues por categoria e severidade.

---

### FASE 5: Performance e Escalabilidade ⚡

**Objetivo:** Identificar gargalos e padrões que não escalam.

1. **Banco de Dados:**
   - Queries N+1 (loops com chamadas individuais ao banco).
   - Índices ausentes em colunas usadas em WHERE/ORDER BY.
   - Queries sem LIMIT ou paginação.
   - `SELECT *` sem necessidade.

2. **APIs:**
   - Operações pesadas (email, relatórios) que deveriam ser assíncronas.
   - Rate limiting em endpoints públicos.
   - Caching para dados lidos frequentemente.
   - Timeouts em chamadas externas.

3. **Código:**
   - Estado global mutável.
   - Event listeners não removidos (memory leaks).
   - Arquivos grandes carregados inteiramente em memória.

**Saída:** Lista de otimizações recomendadas com impacto estimado.

---

### FASE 6: Relatório Final e Veredicto 📊

**Objetivo:** Consolidar todos os achados em um relatório acionável.

1. **Gerar Relatório Padrão Diamante:**

```markdown
# 💎 Relatório de Auditoria Diamante

**Projeto:** [Nome]
**Data:** [Data]
**Nota Geral:** [A-F]

## Resumo Executivo
[2-3 frases sobre o estado geral]

**Bloqueadores Críticos:** [contagem]
**Problemas de Alta Prioridade:** [contagem]

## Achados por Categoria

### Segurança (Nota: [A-F])
- 🔴 [descrição + correção]
- 🟠 [descrição + correção]

### Qualidade de Código (Nota: [A-F])
- [achados]

### Performance (Nota: [A-F])
- [achados]

### Arquitetura (Nota: [A-F])
- [achados]

## Métricas

| Métrica        | Antes  | Depois  | Melhoria |
|----------------|--------|---------|----------|
| Vulnerabilidades | X    | Y       | Z%       |
| Code Smells    | X      | Y       | Z%       |
| Cobertura      | X%     | Y%      | +Z%      |

## Veredicto

✅ APROVADO PARA DEPLOY — ou — 🚫 BLOQUEADO (motivos)

## Ações Requeridas (se bloqueado)
1. [Ação crítica] — Prazo: imediato
2. [Ação alta prioridade] — Prazo: antes do deploy
```

2. **Critérios de Aprovação:**
   - Zero bloqueadores críticos de segurança.
   - Zero segredos expostos.
   - Análise estática sem erros (ruff, mypy, tsc).
   - Testes unitários passando.

3. **Se aprovado:** Exibir ✅ e recomendar próximo passo (`/git` ou `/pr`).
4. **Se bloqueado:** Exibir 🚫 com lista de ações obrigatórias antes de novo review.

---

## Comando Equivalente (Modo Rápido)

```bash
# Análise estática + testes + compilação
python -m ruff check workspace projects && \
python -m mypy workspace && \
python -m pytest workspace/scheduler/test_orchestration.py workspace/tools/test_policies.py -q && \
python -m compileall bootstrap workspace
```

## Skills Ativadas

Este workflow orquestra as seguintes skills automaticamente:

| Fase | Skill | Função |
|------|-------|--------|
| 1 | `production-code-audit` | Descoberta autônoma da codebase |
| 2 | `codebase-audit-pre-push` | Limpeza de ativos e segredos |
| 3 | `vulnerability-scanner` | Varredura OWASP 2025 |
| 3 | `security-auditor` | Auditoria DevSecOps |
| 4 | `lint-and-validate` | Análise estática e linting |
| 4 | `clean-code` | Princípios de código limpo |
| 5 | `performance-profiling` | Análise de performance |
| 6 | `verification-before-completion` | Verificação antes de claims |

## Modelo Mental

```
/super-review é o portão de qualidade máxima.
Se não passar aqui, não vai para produção.
Nenhuma exceção. Nenhum atalho.
```

## Nunca Esqueça

- 🔴 **Segredos expostos = BLOQUEADOR ABSOLUTO.** Nada mais importa até resolver.
- ✅ **Evidência antes de claims.** Não diga "está pronto" sem rodar os comandos.
- 💎 **Padrão Diamante:** Excelência não é opcional — é o mínimo aceitável.
