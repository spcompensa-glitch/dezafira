# Setup Google Indexing API — Grátis, 200 URLs/dia

> **Nota:** Sua organização bloqueia criação de chave de Service Account
> (`iam.disableServiceAccountKeyCreation`). Este guia usa **OAuth 2.0 (Desktop App)**,
> que não sofre essa restrição.

---

## ✅ Já feito

| Etapa | Status |
|-------|--------|
| Projeto `Dezafira Indexer` criado no GCP | ✅ |
| Indexing API ativada no projeto | ✅ |
| OAuth Client ID (Desktop App) criado | ✅ |
| `credentials/oauth_client.json` salvo | ✅ |
| `modules/google_oauth_setup.py` criado | ✅ |
| `modules/google_indexer.py` atualizado (OAuth 2.0) | ✅ |

Tudo isso já está pronto no repositório. O que falta é só a autorização da sua conta.

---

## ❌ O que falta fazer

### 1. Configurar OAuth Consent Screen (escopo do projeto, não da org)

No console do GCP, no **seletor de projeto** (canto superior esquerdo),
troque de `estruturablogs83-org` para **`Dezafira Indexer`**.
Depois acesse:

**https://console.cloud.google.com/auth/consent?project=dezafira-indexer**

Preencha:
- **App name:** `Dezafira Indexer`
- **User support email:** seu email
- **Developer contact:** seu email
- **Authorized domain:** `localhost`
- **Application home page:** `http://localhost`

Clique **SAVE AND CONTINUE** até chegar em **Scopes**:
- **Add or Remove Scopes** → adicione `https://www.googleapis.com/auth/indexing`

Continue até **Test users**:
- **Add Users** → `estruturablogs83@gmail.com`

Finalize o **Summary**.

### 2. Rodar o setup (uma vez)

```bash
cd SniperVideoEngine
python modules/google_oauth_setup.py
```

Isso vai:
1. Abrir o navegador pro login Google
2. Você autoriza o app
3. Salva `GOOGLE_OAUTH_REFRESH_TOKEN`, `GOOGLE_OAUTH_CLIENT_ID` e
   `GOOGLE_OAUTH_CLIENT_SECRET` no `.env`

### 3. Testar

Pela UI (Fábrica de Blogs → modal do artigo → **Indexar no Google**)
ou via curl:

```bash
curl -X POST http://localhost:8000/api/v1/blogs/google-index \
  -H "Content-Type: application/json" \
  -d '{"post_id": "ID_DO_POST_AQUI"}'
```

---

## Limites (grátis)

- **200 URLs/dia** por conta Google
- A indexação leva de segundos a alguns minutos
- Se bater o limite, o sistema pula a etapa graciosamente

## Fallback (sem Google Indexing)

O sistema funciona sem a indexação — o Google eventualmente indexa
naturalmente. A etapa é pulada silenciosamente.
