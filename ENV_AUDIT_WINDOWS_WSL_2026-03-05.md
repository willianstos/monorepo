# Auditoria Windows + WSL + Gitea

Referencia operacional: `2026-03-05`

Fechamento da implementacao segura: `2026-03-06`

## Diagnostico Curto

O ambiente agora esta alinhado com a arquitetura alvo: Windows continua dono de UX, browser, Terminal, PowerShell 7 e credenciais nativas; o WSL Ubuntu 24.04 continua dono de repositorios de desenvolvimento, runtimes, Docker, automacao Linux e Gitea local.

Os bloqueios mais importantes foram resolvidos:

- PATH de usuario do Windows sem o segmento literal `:PATH`
- `ssh.exe` no Windows voltou a funcionar com ACL correta e include gerenciado
- WSL passou a usar bridges explicitas em `~/bin` sem depender de `appendWindowsPath=true`
- Git e SSH do WSL foram normalizados para include files gerenciados e idempotentes
- Gitea no WSL ficou com imagens pinadas, segredos rotacionados, healthcheck mais estrito, runbook menos destrutivo, backup operacional e restore destrutivo validado com prova de dados

O ambiente nao esta totalmente "imortal" ainda por tres motivos residuais:

- ainda existem repositorios do usuario no filesystem do Windows que nao foram movidos
- o contrato de segredos ainda depende do `.env` operacional fora do monorepo, embora agora exista template canonico versionado
- a saude do Docker no WSL ainda depende de restart limpo do daemon quando as chains `DOCKER-ISOLATION-*` corrompem apos eventos anormais

## Inventario

### Windows

- Edicao: `Windows 11 Pro for Workstations`
- Build: `10.0.26200.7922`
- PowerShell: `7.5.4`
- Windows Terminal: `1.23.20211.0`
- WSL: `2.6.1.0`, kernel `6.6.87.2-1`
- Distros WSL: `Ubuntu-24.04` (padrao) e `Coolify-AI`
- `%UserProfile%\.wslconfig`:
  - `localhostForwarding=true`
  - `dnsTunneling=true`
  - `memory=15GB`
  - `processors=10`
  - `swap=3GB`
- Git for Windows: `2.53.0.windows.1`
- OpenSSH Client: presente
- OpenSSH Server: ausente
- `ssh-agent`: continua desabilitado
- VS Code: `1.108.2`, instalacao user em `D:\VSCode`
- Export de extensoes do VS Code em `2026-03-06`: CLI nao detectado no PATH do host
- Antigravity: integracoes detectadas `antigravity-remote-openssh` e `antigravity-remote-wsl`
- PATH de usuario: reparado; sem `:PATH`
- SSH Windows:
  - `%UserProfile%\.ssh\config` agora contem apenas `Include config.d/dev-hybrid.conf`
  - `%UserProfile%\.ssh\config.d\dev-hybrid.conf` gerencia o bloco `github.com`
  - ACL corrigida para `SYSTEM`, `Administrators` e usuario dono
- Git global no Windows:
  - identidade existente preservada
  - `credential.helper=manager-core`
  - `init.defaultBranch=main`

### WSL Ubuntu 24.04

- Distro: `Ubuntu 24.04.3 LTS`
- Shell real: `/bin/bash`
- `/etc/wsl.conf`:
  - `systemd=true`
  - `appendWindowsPath=false`
  - `default=will`
  - `automount options=metadata`
- PATH do WSL: continua Linux-first, sem reimportar PATH do Windows
- Bridges explicitas em `~/bin`:
  - `cmd.exe`
  - `powershell.exe`
  - `pwsh.exe`
  - `clip.exe`
  - `explorer.exe`
  - `cmd`
  - `powershell`
  - `pwsh`
  - `pbcopy`
  - `pbpaste`
  - `open`
  - `explorer`
  - `code` quando CLI do host estiver disponivel
- `DEV_HOME`: padronizado para `/home/will/projetos`
- Git WSL:
  - `~/.gitconfig` agora contem apenas include para `~/.config/dev-hybrid-wsl/gitconfig`
  - `~/.config/dev-hybrid-wsl/gitconfig` gerencia identidade, `credential.helper`, `init.defaultBranch` e `pull.rebase`
  - valores efetivos:
    - `user.name=refrimixtecnologia-coder`
    - `user.email=refrimixtecnologia@gmail.com`
    - `credential.helper=cache --timeout=36000`
    - `init.defaultBranch=main`
    - `pull.rebase=false`
- SSH WSL:
  - `~/.ssh/config` agora contem apenas `Include ~/.ssh/config.d/*.conf`
  - `~/.ssh/config.d/dev-hybrid.conf` gerencia `github.com` e `gitea-local`
- Runtimes/ferramentas principais:
  - Git `2.43.0`
  - OpenSSH `9.6p1`
  - Docker `28.2.2`
  - Python `3.12.3`
  - Node `v24.14.0`
  - npm `11.9.0`
  - pnpm `10.30.3`
  - yarn `1.22.22`
- Docker context efetivo: `default`

### Gitea Local

- Ownership operacional: WSL Ubuntu + Docker nativo
- Projeto Compose: `/home/will/projetos/gitea-wsl-ops`
- HTTP: `http://localhost:3001`
- SSH: `ssh://git@localhost:222/...`
- Containers:
  - `gitea`
  - `gitea-db`
- Imagens pinadas:
  - `gitea/gitea:1.25.4`
  - `postgres:15.17-alpine`
- Configuracao aplicada:
  - `ROOT_URL=http://localhost:3001/`
  - `SSH_DOMAIN=localhost`
  - `DISABLE_REGISTRATION=true`
  - `INSTALL_LOCK=true`
  - `GITEA_DB_PASSWORD` rotacionada
  - `GITEA_SECRET_KEY`, `GITEA_INTERNAL_TOKEN` e `GITEA_JWT_SECRET` agora explicitos no `.env`
- Estado de admin:
  - usuario `admin` criado
  - `admin@localhost`
  - `is_admin=true`
- Health atual:
  - `gitea`: `healthy`
  - `gitea-db`: `healthy`
  - HTTP `/api/v1/version`: OK
  - SSH `localhost:222`: OK
  - `pg_isready`: OK
  - sem eventos recentes de recovery no Postgres durante a ultima janela validada
- Operacionalizacao adicionada:
  - `scripts/gitea_wsl_healthcheck.sh`
  - `scripts/gitea_wsl_stabilize.sh`
  - `scripts/gitea_wsl_shutdown.sh`
  - `scripts/gitea_wsl_backup.sh`
  - `scripts/gitea_wsl_restore.sh`
  - `scripts/gitea_wsl_recover.sh`
  - `GITEA_WSL_RUNBOOK.md`
- Backup validado:
  - backup real gerado em `backups/20260305-225348`
  - `gitea_wsl_restore.sh --apply backups/20260305-225348` executado com sucesso
  - marcador `restore-anchor-20260305225346` preservado
  - marcador `restore-transient-20260305225346` removido pelo restore e depois limpo do ambiente

## Matriz de Alinhamento

| Categoria | Estado final | Evidencia | Observacao |
| --- | --- | --- | --- |
| Identidade e Git | Alinhado com ownership separado | Windows preservado; WSL gerenciado por include | Ainda sem `includeIf` por contexto |
| SSH e credenciais | Melhorado | ACL Windows corrigida; include files em Windows e WSL | `ssh-agent` Windows continua desabilitado |
| PATH e interoperabilidade | Alinhado | `appendWindowsPath=false` + bridges explicitas em `~/bin` | PATH do Windows reparado |
| Editor e terminal | Parcial | Windows Terminal + PowerShell 7 OK; Antigravity Remote WSL detectado | VS Code CLI nao detectado no PATH do host |
| Repositorios e filesystem | Parcial | WSL e dono operacional; repos do usuario no Windows nao foram movidos | decisao humana pendente |
| Line endings e `.gitattributes` | Parcial | nenhuma renormalizacao foi feita | governanca por repo continua fraca onde `.gitattributes` nao existe |
| Runtimes e package managers | Alinhado por ownership | execucao de dev continua no WSL | toolchains Windows continuam presentes para UX |
| Docker e containers | Alinhado | runtime principal no WSL | sem Docker Desktop como runtime principal |
| Proxies e certificados | Nao alterado | nenhuma mudanca aplicada | pendente auditoria dedicada |
| Aliases e comandos equivalentes | Alinhado | bridges `cmd/powershell/pwsh/open/pbcopy/...` funcionais | validado em healthcheck |
| Backups e bootstrap | Melhorado | backups `2026-03-06`, exports `2026-03-06`, scripts idempotentes | restore destrutivo exercitado com prova de dados |
| Gitea local e estrategia de clone/push | Alinhado | HTTP e SSH OK, runbook endurecido, segredos rotacionados | incidente de bridge Docker apos restore foi diagnosticado e resolvido |

## Mudancas Aplicadas

- Atualizei `bootstrap/windows.ps1` para:
  - exportar `winget`
  - exportar snapshot de integracoes de editor
  - migrar o SSH do Windows para include file gerenciado
  - reparar PATH de usuario
  - manter profile bridge opcional
- Atualizei `bootstrap/wsl.sh` para:
  - criar/manter bridges explicitas em `~/bin`
  - gerenciar shell, Git e SSH por include files
  - exportar lista de pacotes Linux manuais
- Atualizei `bootstrap/healthcheck.ps1` para validar handshake SSH do Gitea no Windows
- Atualizei `bootstrap/healthcheck-wsl.sh` para:
  - validar politica do WSL
  - delegar o healthcheck detalhado do Gitea quando o repo `gitea-wsl-ops` existe
  - ler a configuracao Git efetiva, nao apenas o arquivo global bruto
- Corrigi o host Windows:
  - removi `:PATH` do PATH de usuario
  - corrigi ACL de `%UserProfile%\.ssh\config`
  - migrei `%UserProfile%\.ssh\config` para include file gerenciado
- Corrigi o WSL:
  - migrei `~/.gitconfig` para include file gerenciado
  - migrei `~/.ssh/config` para include file gerenciado
  - mantive `appendWindowsPath=false`
  - padronizei `DEV_HOME` para `/home/will/projetos`
- Endureci o Gitea:
  - imagens pinadas
  - segredos rotacionados no `.env`
  - admin inicial criado
  - healthcheck mais completo
  - probe explicito de reachabilidade inter-container na bridge Docker
  - recovery sem apagar volumes por padrao
  - backup com metadados e helper image pinada
  - restore destrutivo exercitado com prova de dados
  - runbook revisado para operacao segura
  - recuperacao do daemon Docker do WSL apos corrupcao das chains `DOCKER-ISOLATION-*`
- Refatorei `env/.env.example` para documentar:
  - contrato hibrido Windows + WSL
  - stack local do Gitea
  - placeholders seguros para segredos

## Mudancas Propostas, Mas Nao Aplicadas

- Agendar drills periodicos de restore destrutivo do Gitea apos mudancas materiais
- Mover repositorios ativos do Windows para ext4 do WSL, com confirmacao explicita
- Definir estrategia de identidade Git com `includeIf` por contexto, se houver mais de uma identidade real em uso
- Colocar o CLI do VS Code no PATH do host Windows, se ele continuar sendo editor oficial
- Auditar proxies, certificados e trust corporativo antes de qualquer endurecimento nessa camada

## Validacoes Executadas

### Bootstrap e parse

- Parse PowerShell OK:
  - `bootstrap/windows.ps1`
  - `bootstrap/healthcheck.ps1`
- Parse shell OK:
  - `bootstrap/wsl.sh`
  - `bootstrap/healthcheck-wsl.sh`
  - `scripts/gitea_wsl_*.sh`

### PowerShell

- `pwsh -NoProfile -File .\bootstrap\windows.ps1 -ReferenceDate 2026-03-06 -FixUserPath -RefreshUserSshConfig -FixSshAcl -SkipProfileBridge`
- `pwsh -NoProfile -File .\bootstrap\healthcheck.ps1`

Resultado:

- WSL invocation: OK
- Linux command execution: OK
- Windows -> Gitea HTTP: OK
- Windows -> Gitea porta 222: OK
- Windows -> Gitea SSH handshake: OK
- Windows OpenSSH config: legivel
- Windows healthcheck: OK

### WSL

- `REFERENCE_DATE=2026-03-06 bash bootstrap/wsl.sh`
- `bash bootstrap/healthcheck-wsl.sh`

Resultado:

- `cmd.exe`, `powershell.exe`, `pwsh.exe`: OK
- clipboard: OK
- `open` e `explorer`: OK
- Docker: OK
- WSL policy (`systemd=true`, `appendWindowsPath=false`): OK
- Gitea ops healthcheck: OK
- Git efetivo do WSL: OK

### Gitea

- `bash scripts/gitea_wsl_stabilize.sh`
- `bash scripts/gitea_wsl_healthcheck.sh`
- `bash scripts/gitea_wsl_backup.sh`
- `bash scripts/gitea_wsl_restore.sh --apply backups/20260305-225348`
- criacao do admin inicial via `gitea admin user create`
- `sudo systemctl restart docker` apos diagnostico de corrupcao das chains Docker

Resultado:

- stack estabiliza sem `docker pull` forcado
- containers `healthy`
- segredos placeholder removidos do `.env` operacional do Gitea
- admin count = `1`
- sem recovery recente do Postgres na ultima verificacao
- backup real gerado
- restore destrutivo validado com prova de dados
- trafego inter-container na bridge `gitea` voltou a funcionar apos reciclar o `docker.service`

## Warnings e Riscos Residuais

- Repositorios do usuario fora do ext4 do WSL continuam sendo risco arquitetural e de performance
- O contrato de segredos do Gitea depende do `.env` operacional externo ao monorepo, apesar de o template agora estar versionado em `env/.env.example`
- O CLI do VS Code continua fora do PATH do host Windows, entao a experiencia principal tende a ficar mais coerente no Antigravity
- Eventos anormais de rede Docker no WSL ainda podem exigir `systemctl restart docker` para reconstruir chains `DOCKER-ISOLATION-*`

## Artefatos Gerados ou Atualizados

- `ENV_AUDIT_WINDOWS_WSL_2026-03-05.md`
- `bootstrap/windows.ps1`
- `bootstrap/wsl.sh`
- `bootstrap/healthcheck.ps1`
- `bootstrap/healthcheck-wsl.sh`
- `.context/backups/2026-03-06/`
- `.context/exports/2026-03-06/`
- `.context/exports/2026-03-06/README.md`
- `env/.env.example`
- `env/README.md`
- `/home/will/projetos/gitea-wsl-ops/GITEA_WSL_RUNBOOK.md`
- `/home/will/projetos/gitea-wsl-ops/scripts/gitea_wsl_healthcheck.sh`
- `/home/will/projetos/gitea-wsl-ops/scripts/gitea_wsl_stabilize.sh`
- `/home/will/projetos/gitea-wsl-ops/scripts/gitea_wsl_shutdown.sh`
- `/home/will/projetos/gitea-wsl-ops/scripts/gitea_wsl_backup.sh`
- `/home/will/projetos/gitea-wsl-ops/scripts/gitea_wsl_restore.sh`
- `/home/will/projetos/gitea-wsl-ops/scripts/gitea_wsl_recover.sh`
