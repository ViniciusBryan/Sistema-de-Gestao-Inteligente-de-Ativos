# SIGA Web Admin (v1.0 — Arquitetura Modular MVT)

Painel administrativo web do **Sistema Inteligente de Gestão de Ativos (SIGA)** na sua **versão 1.0**, organizado em **apps Django por funcionalidade**, com **Function-Based Views (FBVs)** diretas, isolamento lógico multi-tenant por `Empresa` e banco SQLite local para apresentação e estudo de Desenvolvimento Web em arquitetura **MVT (Model–View–Template)**.

---

## Estrutura Modular do Projeto

```text
backend/
├── config/          # Configurações globais (settings.py, urls.py com include())
├── empresas/        # Auth, onboarding de locadora e gestão de equipe (UC01)
├── ativos/          # Catálogo de classes de ativos homologadas para IA (UC03)
├── regras/          # Políticas operacionais por perfil Funcionário vs. Terceirizado (UC02)
├── dispositivos/    # Governança e homologação de aparelhos móveis ou web (UC05 Web)
├── inventarios/     # Dashboard analítico e auditoria de contagens (UC04)
├── api_mobile/      # Ponte DRF isolada (API REST para o App Mobile — UC05 API)
└── templates/       # Templates HTML (Django Template Language + Bootstrap 5)

docs/web/            # Modelagem DER, UML, Casos de Uso e diagramas MVT v1.0
```

---

## Como Rodar Localmente (Setup Completo)

1. Entre na pasta `backend/` e crie/ative o ambiente virtual:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

*(No Linux/macOS/WSL: `source venv/bin/activate` e `python3 -m pip install -r requirements.txt`.)*

2. Aplique as migrações, popule os dados de demonstração e suba o servidor:

```powershell
python manage.py migrate
python manage.py popular_dados
python manage.py runserver
```

Acesse no navegador: **http://127.0.0.1:8000/**

### Usuários de Demonstração (`popular_dados`)

| Usuário | Senha | Perfil | Observação |
| :--- | :--- | :--- | :--- |
| `gestor` | `senha123` | Gestor | Acesso ao painel completo da *Locadora Prime Eventos Ltda* |
| `funcionario1` | `senha123` | Funcionário | Operador com limite padrão de 20% de edição manual |
| `terceirizado1` | `senha123` | Terceirizado | Operador com limite restrito de 5% e vigência de contrato |

---

## Como Executar os Testes Automatizados

```powershell
cd backend
python manage.py check
python manage.py test empresas ativos regras dispositivos inventarios api_mobile
```
