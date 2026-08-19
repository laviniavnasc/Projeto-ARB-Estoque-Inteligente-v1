# Estoque Inteligente — sistema para confeitaria

Projeto base funcional inspirado nas telas fornecidas.

## Tecnologias
- Python + Flask
- HTML5
- CSS3
- JavaScript
- MySQL

## Telas implementadas
1. Login
2. Menu inicial
3. Cadastrar produtos
4. Exclusão de produtos
5. Editar produtos
6. Catálogo de produtos
7. Livro de receitas
8. Notificações
9. Confirmação de edição
10. Confirmação de cadastro
11. Confirmação de exclusão

## 1. Instale Python
Recomendado: Python 3.11+.

## 2. Crie o banco MySQL
Abra o MySQL Workbench e execute `schema.sql`.

## 3. Configure o banco
Copie `.env.example` para `.env` e preencha sua senha do MySQL.
Você também pode definir as variáveis de ambiente diretamente.

## 4. Instale as bibliotecas
```bash
pip install -r requirements.txt
```

## 5. Crie o usuário inicial
```bash
python seed_user.py
```

Login inicial:
- usuário: `admin`
- senha: `admin123`

## 6. Execute
```bash
python app.py
```

Abra:
http://127.0.0.1:5000

## Observação
Para uso real, troque a SECRET_KEY e a senha inicial.
O sistema já possui CRUD de produtos, sessão de login e notificações automáticas
para estoque baixo (até 5 unidades) e validade próxima (7 dias).


## Notificações adaptadas

As notificações agora são geradas automaticamente a partir do banco:
- **Estoque crítico:** quantidade <= 2.
- **Estoque baixo:** quantidade > 2 e <= 5.
- **Validade próxima:** vence em até 7 dias.
- **Validade vence hoje.**
- **Produto vencido.**

A quantidade de alertas aparece como um pequeno contador sobre o sino no topo e também no menu lateral.

# Atualização ARB v3

Esta versão usa a marca **ARB Estoque Inteligente** e inclui cadastro/edição de receitas.

## Para quem JÁ criou o banco anteriormente
No MySQL Workbench, execute apenas o arquivo `migration_receitas.sql`. Ele cria as tabelas novas sem apagar seus produtos e usuários existentes.

Depois, substitua os arquivos do projeto pelos desta versão e rode:

```bash
python app.py
```

## Receitas
- `Cadastrar receita`: salva nome, código, rendimento, tempo de preparo, ingredientes e modo de preparo.
- Os ingredientes são escolhidos entre os produtos já cadastrados no estoque.
- `Editar receita`: busca pelo código (ex.: R001) e permite alterar tudo.
- `Livro de receitas`: mostra ingredientes e indica em verde quando há estoque suficiente; em vermelho quando falta algum ingrediente ou a unidade não coincide.
