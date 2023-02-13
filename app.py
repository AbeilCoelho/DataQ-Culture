# Autores: Abeil Coelho Júnior
# Data de criação: 13/02/2023
# Descrição: Projeto de mestrado
# Versão: 1
# Data de modificação: 13/02/2023

from flask import *  
import pandas as pd
import os
from fileinput import filename

app = Flask(__name__)
app.secret_key = "1skrLdKMnX'dZ{0#XEuS+r"

cco_schema = ['Work Type', 
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



upload_folder = "./file_upload/"
titulo = "HeritageDataPro"

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", title=titulo)

@app.route("/receber_dados", methods=["POST"])
def receber_dados():
    if request.method == 'POST':  
        f = request.files['file']
        file_path = os.path.join(upload_folder, f.filename)

        session['file_path'] = file_path
        session['filename'] = f.filename

        f.save(file_path)
        return render_template("processando.html", name=f.filename, title=titulo)

@app.route("/alinhamento", methods=["GET"])
def alinhamento():
    file_extension = session['file_path'].split('.')[-1]

    df1 = pd.read_csv(session['file_path'], sep=";")
    columns = df1.columns.tolist()
    print(cco_schema)
    return render_template("alinhamento.html", title=titulo, columns=columns, file_name=session['filename'], cco_schema=cco_schema)


@app.route("/salvar_alinhamento", methods=["POST"])
def salvar_alinhamento():
    # Fazer a mágica acontecer
    
    return render_template("report.html", title=titulo)



if __name__ == "__main__":
    app.run(host="192.168.100.38", port=8000, debug=True)
