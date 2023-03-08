# DataQ Culture - Ferramenta de avaliação de qualidade de dados para acervos culturais

O DataQ Culture é uma ferramenta de avaliação de qualidade de dados para acervos culturais, desenvolvido como projeto de mestrado na Universidade Federal do Espírito Santo (Ufes) no Brasil. O objetivo do DataQ Culture é ajudar profissionais e instituições a garantir a integridade e a precisão dos dados em seus acervos culturais.

A ferramenta é baseada no guia de catalogação de objetos culturais [CCO (Catalogue of Cultural Objects)](https://vraweb.org/resourcesx/cataloging-cultural-objects/), guia de referência internacional, permitindo aos usuários calcular um índice de qualidade que reflete o nível de confiança na integridade e na precisão dos dados em um acervo cultural. Esse índice é baseado em uma série de critérios de acordo com as diretrizes estabelecidas pelo CCO.

O DataQ Culture oferece uma solução fácil e eficiente para garantir a qualidade dos dados em acervos culturais, possibilitando a identificação de problemas e a correção de erros antes que eles sejam ampliados ou causem danos irreparáveis. Além disso, a ferramenta também pode ser usada para monitorar a qualidade dos dados em tempo real e para garantir que os dados em um acervo cultural sejam mantidos precisos e atualizados, de acordo com as normas internacionais estabelecidas pelo CCO.

## Como usar

Para usar o DataQ Culture, siga as seguintes instruções:

1. Faça o download do DataQ Culture no repositório https://github.com/AbeilCoelho/DataQ-Culture
2. Instale os pré-requisitos necessários (requirements.txt)<br>
2.1 no Windows use o comando "python -m pip install -r requirements.txt"<br>
2.2 No Linux use o comando "python3 -m pip install -r requirements.txt"

3. Execute o arquivo `app.py`
4. No terminal aparecerá um endereço de IP, acesse esse IP no navegador<br>
4.1 é algo como "http://127.0.0.1:5000/

5. Carregue um arquivo CSV
6. Realize o alinhamento entre as colunas do seu arquivo com as do CCO, para mais detalhes desta etapa veja [este artigo](https://doi.org/10.5007/1518-2924.2023.e90510)
7. Veja os resultados e áreas de atenção para melhorar a qualidade do seu acervo

## Contribuição

Se você quiser contribuir para o desenvolvimento do DataQ Culture, sinta-se livre para enviar pull requests ou entrar em contato com os desenvolvedores.

## Autores

O DataQ Culture foi desenvolvido como projeto de mestrado na Universidade Federal do Espírito Santo (Ufes) no Brasil, pelos seguintes autores:

- Abeil Coelho Júnior (UFES)

Orientado por:
- Daniela Lucas da Silva Lemos (UFES)
- Fabrício Martins Mendonça (UFJF)

## Licença

Este projeto é licenciado sob a licença MIT - consulte o arquivo LICENSE.md para obter detalhes.
