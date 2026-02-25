# crm-credito-360

Aplicação Streamlit para gestão de crédito, aging e controle de limites.

Como executar:

1. Instale dependências:

	pip install -r requirements.txt

2. Execute o app:

	streamlit run app.py

Observações:


Docker (build e run):

```bash
# build
docker build -t crm-credito-360 .

# run (mapear porta local 8501)
docker run -p 8501:8501 crm-credito-360
```



```bash
pip install -r requirements.txt
streamlit run app.py --server.port $PORT
```
