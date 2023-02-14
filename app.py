# Autores: Abeil Coelho Júnior
# Data de criação: 13/02/2023
# Descrição: Projeto de mestrado
# Versão: 1
# Data de modificação: 13/02/2023

from flask import *
from werkzeug.utils import secure_filename

import pandas as pd
from fileinput import filename
import csv
import os
import magic

app = Flask(__name__)
app.secret_key = "1skrLdKMnX'dZ{0#XEuS+r"
app.config["UPLOAD_EXTENSIONS"] = ['.csv', '.CSV']
app.config["UPLOAD_PATH"] = "uploads"
pasta_alinhamentos = "data\\alinhamentos"

esquema_cco = ['Work Type', 
'Title', 
'Creator', 
'Measurements',
'Measurements_Altura',
'Measurements_Largura',
'Measurements_profundidade',
'Measurements_espessura',
'Measurements_diametro',
'Measurements_peso',
'Materials and Techniques', 
'Physical Description', 
'Date', 
'Creation Location', 
'Class', 
'Description', 
'Other Descriptive Notes', 
'Related Works', 
'Inscription', 
'Location']



@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST", "GET"])
def upload():
    if request.method == "GET":
        return render_template("upload.html")

    if request.method == "POST":  
        arquivo_enviado_pelo_usuario = request.files["file"]

        # Verificar se o conteúdo que o usuário está subindo é seguro
        nome_arquivo_do_usuario = secure_filename(arquivo_enviado_pelo_usuario.filename)
        if nome_arquivo_do_usuario != '':
            extensao_arquivo = os.path.splitext(nome_arquivo_do_usuario)[1]
            if extensao_arquivo not in app.config["UPLOAD_EXTENSIONS"]:
                abort(400)

        caminho_arquivo_usuario= os.path.join(app.config["UPLOAD_PATH"], nome_arquivo_do_usuario)
        session["caminho_arquivo"] = caminho_arquivo_usuario
        session["nome_arquivo"] = nome_arquivo_do_usuario

        # Salvando arquivo do usuário
        arquivo_enviado_pelo_usuario.save(caminho_arquivo_usuario)
        

        # Detectar encoding e delimitador do arquivo do usuário
        try:
            blob = open(caminho_arquivo_usuario, 'rb').read()
            m = magic.Magic(mime_encoding=True)
            encoding = m.from_buffer(blob)
            session["encoding"] = encoding
            print("encoding:", encoding)

            sniffer = csv.Sniffer()
            with open(caminho_arquivo_usuario, encoding=encoding) as verificar_delimitador:
                try:
                    delimitador = sniffer.sniff(verificar_delimitador.read(1240)).delimiter
                    session["delimitador"] = delimitador
                    print("delimitador:", delimitador)
                except csv.Error:
                    os.remove(caminho_arquivo_usuario)
                    abort(400)
                    #return render_template("processamento-falha.html", nome_arquivo=nome_arquivo_do_usuario)

            return render_template("processamento-ok.html", nome_arquivo=nome_arquivo_do_usuario, encoding=encoding, delimitador=delimitador)
        except:
            os.remove(caminho_arquivo_usuario)
            return render_template("processamento-falha.html", nome_arquivo=nome_arquivo_do_usuario)



@app.route("/alinhamento", methods=["GET", "POST"])
def alinhamento():
    if request.method == "GET":
        
        dados_alinhamento = pd.read_csv(session["caminho_arquivo"], sep=session["delimitador"], encoding=session["encoding"])
        cabecalho_usuario_lista = dados_alinhamento.columns.tolist()

        # Salvar o cabeçalho do arquivo na seção 
        session["cabecalho_usuario_lista"] = cabecalho_usuario_lista

        # Verificar se crosswalk já existe
        key_cabecalho_usuario = ''.join(cabecalho_usuario_lista)
        key_cabecalho_usuario.replace(" ", "_")
        
        lista_pretendentes_croswalk = []
        for file in os.listdir(os.path.join(pasta_alinhamentos)):
            if file.startswith(key_cabecalho_usuario):
                lista_pretendentes_croswalk.append(file)

        if len(lista_pretendentes_croswalk) > 0:
            print(lista_pretendentes_croswalk)

            lista_pretendentes_croswalk_clean = []
            for item in lista_pretendentes_croswalk:
                item = item.replace(key_cabecalho_usuario, "")
                item = item.replace(".txt", "")
                lista_pretendentes_croswalk_clean.append(item)

                # Lista de pretendents com caminho completo e nome limpo
                lista_pretendentes_croswalk = dict(map(lambda i,j : (i,j) , lista_pretendentes_croswalk_clean,lista_pretendentes_croswalk))
        
        cabecalho_usuario = {k: v for v, k in enumerate(cabecalho_usuario_lista)}
        return render_template("alinhamento.html", cabecalho_usuario=cabecalho_usuario, file_name=session['nome_arquivo'], esquema_cco=esquema_cco, lista_pretendentes_croswalk=lista_pretendentes_croswalk)
    
    if request.method == "POST":
        novo_crosswalk = request.form.items()
        crosswalk = []
        
        for indice, valor in novo_crosswalk:
            crosswalk.append(valor)
        
        key_cabecalho_usuario = ''.join(session["cabecalho_usuario_lista"])
        key_cabecalho_usuario.replace(" ", "_")

        nome_crosswalk = key_cabecalho_usuario + crosswalk[0] + ".txt"
        crosswalk.pop(0)

        # Criar dicionário com cabeçalho antigo e novo
        crosswalk = dict(map(lambda i,j : (i,j) , session["cabecalho_usuario_lista"],crosswalk))
        
        caminho_crosswalk = os.path.join(pasta_alinhamentos, nome_crosswalk)
        with open(caminho_crosswalk, 'w') as arquivo_crosswalk:
            arquivo_crosswalk.write(json.dumps(crosswalk))

        return render_template("index.html")


@app.route("/salvar_alinhamento", methods=["POST"])
def salvar_alinhamento():
    coluna1 = request.form.get('email')

    return render_template("report.html")


if __name__ == "__main__":
    app.run(host="192.168.100.38", port=8000, debug=True)
