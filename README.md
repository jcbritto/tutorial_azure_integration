# Tutorial Azure Integration

Aplicação FastAPI minimalista utilizada em um tutorial de deploy contínuo para Azure App Service com imagens Docker hospedadas no GitHub Container Registry (GHCR). Este README descreve todo o fluxo: criação do Web App, preparo do projeto, publicação de imagem, configuração do CI/CD e verificação.

## 1. Pré-requisitos

### 1.1 Conta e permissões

- Assinatura Azure com permissão de **Contributor** no grupo de recursos `Kyte-Rg`.
- Conta GitHub com acesso de escrita ao repositório.

### 1.2 Ferramentas necessárias

| Ferramenta | Uso | Instalação sugerida (macOS) | Outras referências |
| --- | --- | --- | --- |
| Git | controle de versão | `brew install git` | [Windows](https://git-scm.com/download/win) |
| Python 3.13 | executar FastAPI e scripts | `brew install python@3.13` | [python.org/downloads](https://www.python.org/downloads/) |
| Docker Desktop | build/push de imagens | [Download](https://www.docker.com/products/docker-desktop/) | Necessário permitir o uso de CLI |
| Azure CLI (`az`) | comandos de configuração | `brew install azure-cli` | [Instalação Windows/Linux](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| GitHub CLI (`gh`) | gerenciamento de secrets e Actions | `brew install gh` | [Instalação oficial](https://cli.github.com/manual/installation) |

> Após instalar Docker Desktop, abra o aplicativo e certifique-se de que o daemon está rodando (ícone da baleia ativo).  
> Para `az` e `gh`, faça login antes de continuar:

```bash
az login            # abre navegador para autenticação
gh auth login       # selecione GitHub.com, HTTPS e informe token quando solicitado
```

### 1.3 Clonar o repositório

```bash
git clone https://github.com/jcbritto/tutorial_azure_integration.git
cd tutorial_azure_integration
```

### 1.4 Como ler este guia

- Trechos `assim` representam comandos a serem executados no terminal; remova os comentários (`# ...`) quando copiar.
- Sempre substitua valores entre `< >` pelos seus dados (ex.: `<seu-usuario>` → `jcbritto`).
- Tenha cuidado com credenciais: mantenha tokens e senhas apenas em variáveis de ambiente ou secrets, nunca commitados.

## 2. Estrutura do projeto

```
.
├── Dockerfile
├── main.py
├── requirements.txt
├── .github/workflows/deploy.yml
├── Fotos/                              # capturas de tela do portal Azure
└── README.md
```

## 3. Configuração inicial no portal Azure

As imagens em `Fotos/` ilustram a sequência usada para criar o Web App `Tutorial`.

1. **Tela inicial do portal**  
   ![Portal Azure - Criar recurso](Fotos/0.png)  
   Clique em **Criar um recurso**.

2. **Selecionar tipo de recurso**  
   ![Selecionar Aplicativo Web](Fotos/1.png)  
   Na categoria de serviços populares, escolha **Aplicativo Web**.

3. **Aba Básico**  
   ![Configuração Básica](Fotos/2.png)  
   - Assinatura: selecione seu plano.
   - Grupo de Recursos: `Kyte-Rg`.
   - Nome: `Tutorial`.
   - Publicar: `Container`.
   - Sistema Operacional: `Linux`.
   - Região: `Central US`.
   - Plano: utilize o App Service Plan existente (ex.: `kyte-gateway-sp (Premium V3)`).

4. **Aba Contêiner (quando utilizando ACR)**  
   ![Configuração de contêiner ACR](Fotos/3.png)  
   Se estiver usando um Azure Container Registry, selecione-o aqui. No nosso fluxo final usamos GHCR, então apenas referencie esta tela para entender onde ficam os campos de imagem e marcação.

5. **Aba Contêiner (início rápido)**  
   ![Configuração inicial padrão](Fotos/4.png)  
   Caso opte pela imagem de início rápido (NGINX) apenas para criar o recurso, depois atualizamos a imagem via CLI/CI.

Finalize a criação do recurso clicando em **Revisar + criar**.

## 4. Preparar o ambiente local

```bash
# criar ambiente virtual
python3 -m venv .venv
source .venv/bin/activate

# instalar dependências
pip install -r requirements.txt

# validar localmente
uvicorn main:app --reload
# acessar http://127.0.0.1:8000/health -> {"status": "ok"}
```

## 5. Dockerizar e publicar manualmente (opcional)

```bash
# com Docker Desktop ativo
docker build -t ghcr.io/<seu-usuario>/tutorial_azure_integration:latest .

# login no GHCR (pat com write:packages)
echo "$GHCR_TOKEN" | docker login ghcr.io -u <seu-usuario> --password-stdin

# publicar imagem
docker push ghcr.io/<seu-usuario>/tutorial_azure_integration:latest
```

> Substitua `<seu-usuario>` pelo usuário/organização do GitHub. O pipeline realiza esses passos automaticamente, porém é útil testar manualmente.

## 6. Configurações via Azure CLI

```bash
# logar (caso não tenha feito)
az login

# garantir porta correta
az webapp config appsettings set \
  -g Kyte-Rg \
  -n Tutorial \
  --settings WEBSITES_PORT=8000

# apontar App Service para a imagem do GHCR
az webapp config container set \
  -g Kyte-Rg \
  -n Tutorial \
  --container-image-name ghcr.io/<seu-usuario>/tutorial_azure_integration:latest \
  --container-registry-url https://ghcr.io \
  --container-registry-user <seu-usuario> \
  --container-registry-password "$GHCR_TOKEN"

# reiniciar aplicação
az webapp restart -g Kyte-Rg -n Tutorial
```

## 7. Definir variáveis de ambiente do `.env` no App Service

Caso a aplicação dependa de variáveis definidas em um arquivo `.env`, você pode enviá-las para o App Service usando a CLI. O comando abaixo ignora linhas vazias/comentários, converte o arquivo em pares `CHAVE=valor` e aplica em lote.

```bash
# gerar lista de pares CHAVE=valor a partir do .env
ENV_SETTINGS=$(python3 - <<'PY'
from pathlib import Path
pairs = []
for line in Path(".env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    pairs.append(f"{key}={value}")
print(" ".join(pairs))
PY
)

# enviar para o App Service
az webapp config appsettings set \
  -g Kyte-Rg \
  -n Tutorial \
  --settings $ENV_SETTINGS
```

> 1. Confirme o conteúdo que será enviado usando `echo "$ENV_SETTINGS"`.  
> 2. Caso algum valor contenha espaços, considere incluir aspas no `.env` (`VAR="valor com espaço"`).  
> 3. Depois de aplicado, visualize no portal Azure em **Configurações > Configurações do aplicativo** (as credenciais ficam criptografadas).

## 8. Configurar GitHub Actions

O workflow `.github/workflows/deploy.yml` realiza:

1. Checkout e instalação de dependências Python.
2. Teste rápido do endpoint `/health`.
3. Build e push da imagem com tags `latest` e `${{ github.sha }}`.
4. Login no Azure usando um Service Principal.
5. Atualização do App Service para apontar para a nova imagem e reinício da aplicação.

## 9. Gerar credenciais e secrets

### 9.1 Token do GitHub Container Registry (`GHCR_TOKEN`)

1. Acesse [Settings > Developer settings > Personal access tokens > Fine-grained tokens](https://github.com/settings/tokens?type=beta).  
2. Clique em **Generate new token**.  
3. Selecione o repositório `tutorial_azure_integration`.  
4. Marque permissões `Read and Write` para **Packages**.  
5. Defina uma expiração curta (30 ou 90 dias) e gere o token.  
6. Salve o valor em local seguro. Opcionalmente exporte para shell:

   ```bash
   export GHCR_TOKEN="ghp_xxx..."
   ```

7. Cadastre no GitHub:

   ```bash
    gh secret set GHCR_DEPLOY_TOKEN --body "$GHCR_TOKEN"
   ```

### 9.2 Publish Profile (`AZURE_WEBAPP_PUBLISH_PROFILE`)

1. Execute:

   ```bash
   az webapp deployment list-publishing-profiles \
     -g Kyte-Rg \
     -n Tutorial \
     --xml > publish_profile.xml
   ```

2. Cadastre o segredo:

   ```bash
   gh secret set AZURE_WEBAPP_PUBLISH_PROFILE < publish_profile.xml
   rm publish_profile.xml
   ```

### 9.3 Service Principal (`AZURE_CREDENTIALS`)

1. Crie um Service Principal com permissão de **Contributor** no grupo de recursos:

   ```bash
   az ad sp create-for-rbac \
     --name tutorial-azure-integration-gh \
     --role contributor \
     --scopes /subscriptions/<subscription-id>/resourceGroups/Kyte-Rg \
     --sdk-auth > azure_creds.json
   ```

2. Cadastre o JSON como segredo:

   ```bash
   gh secret set AZURE_CREDENTIALS < azure_creds.json
   rm azure_creds.json
   ```

3. Opcional: exporte variáveis locais (úteis para testes CLI):

   ```bash
   export AZURE_CLIENT_ID="..."
   export AZURE_TENANT_ID="..."
   export AZURE_SUBSCRIPTION_ID="..."
   ```

> O comando `az account show --output table` ajuda a confirmar a assinatura corrente e o `subscriptionId`.

### 9.4 Resumo dos segredos necessários

| Segredo | Como obter | Uso |
| --- | --- | --- |
| `GHCR_DEPLOY_TOKEN` | Criar token via painel GitHub (write/read packages). | Autenticação com GHCR dentro da action. |
| `AZURE_WEBAPP_PUBLISH_PROFILE` | `az webapp deployment list-publishing-profiles ... --xml` | Mantido como credencial extra (útil para troubleshooting). |
| `AZURE_CREDENTIALS` | Service Principal via `az ad sp create-for-rbac ... --sdk-auth`. | Login automático no Azure durante o deploy. |

## 10. Fluxo de deploy automático

1. Commit + push na branch `main`.
2. GitHub Actions cria a imagem e publica no GHCR.
3. Action autentica no Azure com o Service Principal.
4. CLI atualiza a imagem configurada no App Service e reinicia a aplicação.
5. Validar com:

```bash
curl https://tutorial-a2hgancsh0bbhydu.centralus-01.azurewebsites.net/health
# retorno esperado: {"status":"ok"}
```

## 11. Monitoramento e troubleshooting

### 11.1 Acompanhar a pipeline (GitHub Actions)

```bash
# listar últimas execuções
gh run list --limit 5

# acompanhar logs em tempo real
gh run watch <run-id>

# investigar um run específico
gh run view <run-id> --log --repo jcbritto/tutorial_azure_integration

# examinar apenas o job principal
gh run view <run-id> --log --job <job-id>
```

> O `run-id` aparece no output de `gh run list`. Dentro do portal GitHub, navegue até **Actions** para visualizar graficamente cada etapa.

### 11.2 Habilitar e ler logs do App Service

```bash
# garantir que logging esteja habilitado para containers
az webapp log config \
  -g Kyte-Rg \
  -n Tutorial \
  --docker-container-logging filesystem \
  --application-logging true

# acompanhar logs em tempo real
az webapp log tail -g Kyte-Rg -n Tutorial

# baixar pacote de logs para análise offline
az webapp log download -g Kyte-Rg -n Tutorial --logs-directory logs_Tutorial
```

### 11.3 Verificar status do contêiner

```bash
# checar imagem atualmente configurada
az webapp show \
  -g Kyte-Rg \
  -n Tutorial \
  --query "siteConfig.linuxFxVersion" -o tsv

# listar últimos deploys (inclui falhas de start)
az webapp deployment list \
  -g Kyte-Rg \
  -n Tutorial \
  --query "[].{time:received_time, status:status, message:message}" -o table

# obter detalhes do deployment mais recente
az webapp deployment show \
  -g Kyte-Rg \
  -n Tutorial
```

### 11.4 Dicas rápidas de diagnóstico

- Se o contêiner não iniciar, verifique `az webapp log tail` imediatamente; mensagens de `Pull` ou `CrashLoop` aparecem ali.
- Confirme se a porta exposta no `Dockerfile` (8000) coincide com `WEBSITES_PORT`.
- Para reproduzir localmente erros de build, execute `docker build` e `docker run -p 8000:8000 ...` antes de push.

## 12. Boas práticas adicionais

- Revogue/rotacione tokens (`GHCR_TOKEN`, Service Principal) periodicamente.
- Monitore o log do App Service via `az webapp log tail -g Kyte-Rg -n Tutorial`.
- Ajuste a porta do contêiner se a aplicação evoluir para múltiplos serviços.

## 13. Referências

- [FastAPI](https://fastapi.tiangolo.com/)
- [Azure App Service - Contêineres Linux](https://learn.microsoft.com/azure/app-service/)
- [GitHub Actions para Azure](https://learn.microsoft.com/azure/app-service/deploy-github-actions)
