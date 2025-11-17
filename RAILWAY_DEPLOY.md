# 🚂 Guia Completo de Deploy no Railway

Este guia vai te ajudar a fazer o deploy completo do seu projeto Django no Railway.

## 📋 Pré-requisitos

1. Conta no Railway (https://railway.app)
2. Conta no GitHub (para conectar o repositório)
3. Projeto já commitado no Git

---

## 🔧 Passo 1: Preparar o Projeto Localmente

### 1.1 Verificar arquivos criados

Certifique-se de que os seguintes arquivos estão na raiz do projeto:
- ✅ `Procfile` (já criado)
- ✅ `runtime.txt` (já criado)
- ✅ `requirements.txt` (já existe)
- ✅ `core/settings.py` (atualizado com STATIC_ROOT)

### 1.2 Coletar arquivos estáticos (opcional, mas recomendado)

Antes de fazer o deploy, você pode testar localmente:

```bash
python manage.py collectstatic --noinput
```

---

## 🚀 Passo 2: Criar Projeto no Railway

### 2.1 Acessar o Railway

1. Acesse https://railway.app
2. Faça login com sua conta (GitHub, Google, etc.)

### 2.2 Criar Novo Projeto

1. Clique em **"New Project"**
2. Selecione **"Deploy from GitHub repo"**
3. Autorize o Railway a acessar seus repositórios (se necessário)
4. Selecione o repositório do seu projeto
5. Clique em **"Deploy Now"**

---

## 🗄️ Passo 3: Configurar Banco de Dados MySQL

### 3.1 Adicionar Serviço MySQL

1. No dashboard do projeto, clique em **"+ New"**
2. Selecione **"Database"**
3. Escolha **"MySQL"**
4. O Railway criará automaticamente um banco MySQL

### 3.2 Obter Variáveis de Conexão

1. Clique no serviço MySQL criado
2. Vá na aba **"Variables"**
3. Anote as seguintes variáveis (você vai precisar delas):
   - `MYSQLHOST`
   - `MYSQLPORT`
   - `MYSQLDATABASE`
   - `MYSQLUSER`
   - `MYSQLPASSWORD`

---

## ⚙️ Passo 4: Configurar Variáveis de Ambiente

### 4.1 Acessar Variáveis do Serviço Web

1. No dashboard, clique no serviço **"web"** (sua aplicação Django)
2. Vá na aba **"Variables"**
3. Clique em **"+ New Variable"**

### 4.2 Adicionar Todas as Variáveis Necessárias

Adicione as seguintes variáveis de ambiente:

#### Variáveis de Segurança
```
SECRET_KEY=sua-chave-secreta-aqui-gerada-aleatoriamente
DEBUG=0
```

**⚠️ IMPORTANTE:** Gere uma SECRET_KEY segura. Você pode usar:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### Variáveis de Host
```
DJANGO_ALLOWED_HOSTS=seu-projeto.up.railway.app,*.railway.app
DJANGO_CORS_ORIGINS=https://seu-projeto.up.railway.app
```

**⚠️ IMPORTANTE:** Substitua `seu-projeto` pelo nome real do seu projeto no Railway. Você verá a URL depois do deploy.

#### Variáveis de Banco de Dados
```
DB_DAFAULT_ENGINE=django.db.backends.mysql
DB_DAFAULT_NAME=[valor de MYSQLDATABASE do serviço MySQL]
DB_DAFAULT_USER=[valor de MYSQLUSER do serviço MySQL]
DB_DAFAULT_PASSWORD=[valor de MYSQLPASSWORD do serviço MySQL]
DB_DAFAULT_HOST=[valor de MYSQLHOST do serviço MySQL]
DB_DAFAULT_PORT=[valor de MYSQLPORT do serviço MySQL]
```

**💡 DICA:** O Railway permite referenciar variáveis de outros serviços. Você pode usar:
- `${{MySQL.MYSQLDATABASE}}` (substitua `MySQL` pelo nome do seu serviço)
- Ou copiar os valores manualmente

---

## 🔄 Passo 5: Configurar Build e Deploy

### 5.1 Configurar Build Command (se necessário)

1. No serviço web, vá em **"Settings"**
2. Em **"Build Command"**, adicione:
```bash
python manage.py collectstatic --noinput
```

### 5.2 Configurar Start Command

O Railway deve detectar automaticamente o `Procfile`, mas você pode verificar em **"Settings"** → **"Start Command"**:
```
web: gunicorn core.wsgi:application --bind 0.0.0.0:$PORT
```

---

## 📦 Passo 6: Executar Migrações

### 6.1 Usando Railway CLI (Recomendado)

1. Instale o Railway CLI:
```bash
npm i -g @railway/cli
```

2. Faça login:
```bash
railway login
```

3. Conecte ao projeto:
```bash
railway link
```

4. Execute as migrações:
```bash
railway run python manage.py migrate
```

### 6.2 Usando Deploy Hook (Alternativa)

Você pode criar um script de deploy que executa as migrações automaticamente. Crie um arquivo `railway.json`:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python manage.py migrate && gunicorn core.wsgi:application --bind 0.0.0.0:$PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**⚠️ NOTA:** A forma mais segura é executar migrações manualmente via CLI.

---

## 👤 Passo 7: Criar Superusuário

Execute via Railway CLI:

```bash
railway run python manage.py createsuperuser
```

Ou adicione um comando de inicialização no seu código.

---

## 🔍 Passo 8: Verificar Deploy

### 8.1 Verificar Logs

1. No dashboard do Railway, clique no serviço web
2. Vá na aba **"Deployments"**
3. Clique no deployment mais recente
4. Verifique os logs para erros

### 8.2 Acessar o Site

1. No dashboard, clique no serviço web
2. Vá em **"Settings"**
3. Em **"Domains"**, você verá a URL do seu site
4. Clique na URL para acessar

---

## 🎯 Passo 9: Configurar Domínio Customizado (Opcional)

1. No serviço web, vá em **"Settings"**
2. Em **"Domains"**, clique em **"Custom Domain"**
3. Adicione seu domínio
4. Configure os registros DNS conforme instruções do Railway

---

## 🔧 Passo 10: Configurar Serviços Adicionais (Opcional)

### 10.1 Redis (se usar Celery)

Se você usar Celery com Redis:

1. Adicione serviço **"Redis"** no Railway
2. Adicione variáveis de ambiente relacionadas ao Redis no serviço web

### 10.2 Storage para Arquivos de Mídia

O Railway não persiste arquivos de mídia por padrão. Opções:

1. **Usar Railway Volume** (pago):
   - Adicione um Volume no projeto
   - Configure `MEDIA_ROOT` para apontar para o volume

2. **Usar S3 ou Cloud Storage** (recomendado):
   - Configure `django-storages` com AWS S3, Cloudflare R2, etc.
   - Atualize `settings.py` para usar storage remoto

---

## 🐛 Troubleshooting

### Erro: "No module named 'mysqlclient'"

Adicione ao `requirements.txt`:
```
mysqlclient==2.2.7
```
(Já está no seu requirements.txt ✅)

### Erro: "Static files not found"

Certifique-se de que:
1. `STATIC_ROOT` está configurado no `settings.py` ✅
2. O comando `collectstatic` está sendo executado no build

### Erro: "Database connection failed"

Verifique:
1. Todas as variáveis de banco estão corretas
2. O serviço MySQL está rodando
3. As credenciais estão corretas

### Erro: "ALLOWED_HOSTS"

Certifique-se de adicionar:
```
DJANGO_ALLOWED_HOSTS=seu-projeto.up.railway.app,*.railway.app
```

---

## 📝 Checklist Final

Antes de considerar o deploy completo, verifique:

- [ ] Todas as variáveis de ambiente configuradas
- [ ] Banco de dados MySQL criado e conectado
- [ ] Migrações executadas
- [ ] Superusuário criado
- [ ] Arquivos estáticos coletados
- [ ] Site acessível pela URL do Railway
- [ ] Logs sem erros críticos

---

## 🎉 Pronto!

Seu site Django está no ar no Railway! 🚀

Para atualizações futuras, basta fazer `git push` e o Railway fará o deploy automaticamente.

---

## 📚 Recursos Úteis

- [Documentação do Railway](https://docs.railway.app)
- [Django Deployment Checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/)
- [Railway Discord](https://discord.gg/railway) (comunidade para ajuda)

