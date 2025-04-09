<h1 align="center"> Dashboard para transcrição de áudio </h1>

<!-- pasta para o git conseguir acessar a foto -->
<p align="center">
  <img alt="Imagem da tela base do dashboard de transcrição de áudios" src="assets/dashboard-transcricao.png" width="100%">
</p>

## 🎯 Projetos base
- https://github.com/jojojaeger/whisper-streamlit
- https://medium.com/@xriteshsharmax/speaker-diarization-using-whisper-asr-and-pyannote-f0141c85d59a

  
## 🚀 Tecnologias
- Streamlit: framework open source usado para transformar scripts Pyhton em aplicações web. 
- [Whisper - OpenAI](https://github.com/openai/whisper): modelo de reconhecimento automático de fala desenvolvido pela OpenAI. Processa áudio e gera saída de texto. 
- [AgglomerativeClustering](https://scikit-learn.org/dev/modules/generated/sklearn.cluster.AgglomerativeClustering.html): algoritmo de aprendizado não supervisionado, utilizado aqui para a identificação e separação de diferentes vozes em um áudio. 

## ▶️ Fluxograma de funcionamento do sistema
- [Desenho do algoritmo](https://www.mermaidchart.com/raw/e361f51c-36c1-4215-ae15-dea2c0fba48a?theme=light&version=v0.1&format=svg)
  
# Configurações do ambiente de desenvolvimento
1. Clone o projeto.
```
git clone https://github.com/cibellemc/speech-to-text.git
```

2. Entre na pasta com o comando `cd/speech-to/text`.

3. Crie a pasta oculta `.streamlit/` na raiz do projeto. 

4. Crie o arquivo `secrets.toml` dentro da pasta `.streamlit/` e cole o conteúdo abaixo. 
```
[connections.postgresql]
dialect = "postgresql"
host = "localhost"
port = "5432"
database = "POSTGRES_DB" 
username = "POSTGRES_USER" 
password = "POSTGRES_PASSWORD" 
```

Esse passo é necessário para a conexão, pois armazena as variáveis sensíveis relacionadas ao banco. 

A estrutura das pastas ficará semelhante ao descrito abaixo:
```
├── .streamlit/ 
|  ├── secrets.toml 
├── pages/
├── services/
├── docker-compose.yaml
```

5. Altere as configurações do banco no arquivo `docker-compose.yaml`.
```
environment:
  POSTGRES_DB: "transcritor" # preencher nome do banco
  POSTGRES_USER: "postgres" # preencher usuário
  POSTGRES_PASSWORD: "12345678" # preencher senha
```

6. Com base nas variáveis acima, modifique também o `.streamlit/secrets.toml`. 
```
[connections.postgresql]
dialect = "postgresql"
host = "postgres"
port = "5432"
database = "POSTGRES_DB"
username = "POSTGRES_USER"
password = "POSTGRES_PASSWORD"
```

7. Rode o comando 
```
sudo docker-compose up
```

8. Abra um novo terminal, rode o comando abaixo para ver todos os containers
```
sudo docker ps -a
```

Identifique o que se tratar do banco postgres e copie o ID

9. Rode o comando abaixo para executar um terminal dentro do container.
```
docker exec -it <ID do container do postgres> psql -U <POSTGRES_USER> -d <POSTGRES_DB>
```
Exemplo: `docker exec -it 35baccfc7ce9 psql -U postgres -d transcritor`

10. Crie a tabela no banco de dados
```
CREATE TABLE transcriptions (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255),
    transcription TEXT,
    model VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time float
);
```
## 🌐 Acesso à aplicação
No terminal em que você subiu o docker-compose aparecerão os links de acesso.
```
# exemplo 
teste-docker-app-1       |   You can now view your Streamlit app in your browser.
teste-docker-app-1       | 
teste-docker-app-1       |   Local URL: http://localhost:8501
teste-docker-app-1       |   Network URL: http://172.19.0.3:8501
teste-docker-app-1       |   External URL: http://177.107.30.98:8501
```

## Caso queira fazer alguma alteração no front
Adicione a linha 3 do código abaixo no `docker-compose.yaml` para substituir o conteúdo do app pelas suas modificações.
```
    volumes:
      - .:/app # nova config
      - .streamlit/:/app/.streamlit  # já existente

```
