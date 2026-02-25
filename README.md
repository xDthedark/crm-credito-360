# crm-credito-360

Aplicação Streamlit para gestão de crédito, aging e controle de limites.

Como executar:

1. Instale dependências:

	pip install -r requirements.txt

2. Execute o app:

	streamlit run app.py

Observações:


Deploy no Render.com:

- Este repositório inclui `render.yaml` para deploy automático no Render. Ele instrui o serviço a usar o ambiente Python, instalar dependências e executar o Streamlit.
- Se o Render estiver tentando usar Ruby (erro `Could not locate Gemfile`), provavelmente o serviço foi detectado como Ruby — no painel do Render escolha "Create Web Service" e selecione "Python" ou permita que o `render.yaml` seja detectado.
- Comandos chave (usados pelo `render.yaml`):

```bash
pip install -r requirements.txt
streamlit run app.py --server.port $PORT
```
