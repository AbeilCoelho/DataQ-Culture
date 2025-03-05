"""
Autor: Abeil Coelho Júnior
Data de criação: 2023-02-13
Descrição: Projeto de mestrado DataQ-cultura
Versão: 1
Data de modificação: 2025-02-11
"""

import json
import os

import pandas as pd
from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from helpers.utils import (
    analyze_results,
    apply_rules_to_metadata,
    calculate_adequacy,
    detect_delimiter,
    detect_encoding,
    load_data,
    remove_file_if_exists,
)

app = Flask(__name__)

# Test to run the service on Google Colab
if os.getenv("COLAB_RELEASE_TAG"):
    print("Sendo executado no Google Colab :D\n")


app.secret_key = "1skrLdKMnX'dZ{0#XEuS+r"
app.config["UPLOAD_EXTENSIONS"] = [".csv", ".CSV"]
app.config["UPLOAD_PATH"] = "uploads"
DATA_FOLDER = "./data"

crosswalk_file = os.path.join(DATA_FOLDER, "alinhamentos/alinhamentos.parquet")


RULES = pd.read_excel(os.path.join(DATA_FOLDER, "fontes", "Base_Regex.xlsx"))
DIMENSIONS = pd.read_excel(os.path.join(DATA_FOLDER, "fontes", "Dimencoes.xlsx"))


cco_schema = [
    "Work Type",
    "Title",
    "Creator",
    "Measurements",
    "Measurements_Altura",
    "Measurements_Largura",
    "Measurements_Profundidade",
    "Measurements_Espessura",
    "Measurements_Diametro",
    "Measurements_Peso",
    "Materials and Techniques",
    "Physical Description",
    "Date",
    "Creation Location",
    "Class",
    "Description",
    "Other Descriptive Notes",
    "Related Works",
    "Inscription",
    "Location",
]


try:
    loaded_alignment = pd.read_parquet(crosswalk_file)
except FileNotFoundError:
    print("No crosswalk file found. Loading empty scheme")
    data = [["0", "0", 0]]
    loaded_alignment = pd.DataFrame(data, columns=["nome", "colunas", "id"])
    loaded_alignment.to_parquet(crosswalk_file)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST", "GET"])
def upload():
    if request.method == "GET":
        return render_template("upload.html")

    if request.method == "POST":
        user_sent_file = request.files["file"]

        # Verificar se o conteúdo que o usuário está subindo é seguro
        user_sent_filename = secure_filename(user_sent_file.filename)
        if user_sent_filename != "":
            user_sent_file_extension = os.path.splitext(user_sent_filename)[1]
            if user_sent_file_extension not in app.config["UPLOAD_EXTENSIONS"]:
                abort(400)

        user_sent_file_path = os.path.join(
            app.config["UPLOAD_PATH"], user_sent_filename
        )
        session["user_sent_file_path"] = user_sent_file_path
        session["user_sent_filename"] = user_sent_filename

        # Salvando arquivo do usuário
        user_sent_file.save(user_sent_file_path)

        # Detectar encoding do arquivo do usuário
        encoding = detect_encoding(user_sent_file_path)
        if not encoding:
            os.remove(user_sent_file)
            return render_template(
                "processamento-falha.html", nome_arquivo=session["user_sent_filename"]
            )
        session["encoding"] = encoding

        # Check if the file is too short
        num_lines = sum(1 for _ in open(user_sent_file_path, "rb"))
        if num_lines < 2:
            print("O arquivo é muito curto.")
            os.remove(user_sent_file)
            return render_template(
                "processamento-falha.html", nome_arquivo=session["user_sent_filename"]
            )

        # Detectar delimiter do arquivo do usuário
        delimiter = detect_delimiter(user_sent_file_path, encoding)
        session["encoding"] = encoding
        if not delimiter:
            os.remove(user_sent_file_path)
            return render_template(
                "processamento-falha.html", nome_arquivo=session["user_sent_filename"]
            )
        session["delimiter"] = delimiter

        return render_template(
            "processamento-ok.html",
            nome_arquivo=session["user_sent_filename"],
            encoding=encoding,
            delimitador=delimiter,
        )


@app.route("/alinhamento", methods=["GET", "POST"])
def alinhamento():
    if request.method == "GET":
        try:
            file_path = session.get("user_sent_file_path")
            delimiter = session.get("delimitador")
            encoding = session.get("encoding")

            if not file_path or not delimiter or not encoding:
                print("Missing session data for file processing.")
                return render_template("processamento-falha.html")

            dados_alinhamento = pd.read_csv(
                file_path, sep=delimiter, encoding=encoding, nrows=2
            )

            # Remove any "Unnamed" columns
            dados_alinhamento = dados_alinhamento.loc[
                :, ~dados_alinhamento.columns.str.contains("^Unnamed")
            ]

            user_file_header_list = dados_alinhamento.columns.tolist()

            # Store the header in the session
            session["user_file_header_list"] = user_file_header_list

            user_header = {col: idx for idx, col in enumerate(user_file_header_list)}

            # Generate a unique key for the column structure
            key_user_file_header = "".join(user_file_header_list).replace(" ", "_")

            # Verificar se crosswalk já existe
            key_user_file_header = "".join(user_file_header_list)
            key_user_file_header.replace(" ", "_")

            # Check if a crosswalk already exists
            possibles_pre_existing_mappings = []

            try:
                possibles_pre_existing_mappings = pd.read_parquet(crosswalk_file)
                possibles_pre_existing_mappings = possibles_pre_existing_mappings.query(
                    f"colunas == '{key_user_file_header}'"
                )
                possibles_pre_existing_mappings = (
                    possibles_pre_existing_mappings.set_index("nome")["id"].to_dict()
                )

            except FileNotFoundError:
                print(
                    "Crosswalk file not found. Proceeding without pre-existing mappings."
                )

            except Exception as e:
                print(f"Error loading crosswalk file: {e}")

            return render_template(
                "alinhamento.html",
                cabecalho_usuario=user_header,
                file_name=session["user_sent_filename"],
                esquema_cco=cco_schema,
                lista_pretendentes_crosswalk=possibles_pre_existing_mappings,
            )

        except Exception as e:
            print(f"Error processing GET request in alinhamento: {e}")
            os.remove(session.get("user_sent_file_path", ""))
            return render_template("processamento-falha.html")

    if request.method == "POST":
        try:
            # Extract form data
            new_crosswalk = request.form.items()
            crosswalk, crosswalk_vocabulary = [], []

            for key, value in new_crosswalk:
                if "vocabulario_controlado" in key:
                    crosswalk_vocabulary.append(value)
                else:
                    crosswalk.append(value)

            if not crosswalk:
                print("Error: Crosswalk data is empty.")
                return render_template("processamento-falha.html")

            # Generate a key for the column structure
            key_user_file_header = "".join(session["cabecalho_usuario_lista"]).replace(
                " ", "_"
            )
            crosswalk_name = crosswalk.pop(0)  # Extract title from crosswalk

            # Load existing crosswalk mappings
            try:
                # Remover crosswalk com mesmo nome e colunas
                existing_crosswalk = pd.read_parquet(crosswalk_file)

                # Remove existing crosswalks with the same name and columns
                existing_crosswalk = existing_crosswalk.query(
                    "colunas != @key_user_file_header or nome != @crosswalk_name"
                )

                new_crosswalk_id = (
                    int(existing_crosswalk["id"].max()) + 1
                    if not existing_crosswalk.empty
                    else 1
                )

            except FileNotFoundError:
                print("Crosswalk file not found. Creating a new one.")
                existing_crosswalk = pd.DataFrame(columns=["nome", "colunas", "id"])
                new_crosswalk_id = 1
            except Exception as e:
                print(f"Error loading crosswalk file: {e}")
                return render_template("processamento-falha.html")

            # Create a new crosswalk entry
            novo_crosswalk_df = pd.DataFrame(
                [[crosswalk_name, key_user_file_header, new_crosswalk_id]],
                columns=["nome", "colunas", "id"],
            )

            # Save updated crosswalks
            croswalks_salvos = pd.concat(
                [existing_crosswalk, novo_crosswalk_df], ignore_index=True
            )
            croswalks_salvos.to_parquet(crosswalk_file)

            # Create dictionary mapping old column names to new ones
            crosswalk_dict = dict(zip(session["cabecalho_usuario_lista"], crosswalk))

            # Map controlled vocabulary fields
            print("Before mapping vocabulario:", crosswalk_vocabulary)
            crosswalk_vocabulary = [
                crosswalk_dict.get(col, col) for col in crosswalk_vocabulary
            ]
            print("After mapping vocabulario:", crosswalk_vocabulary)

            # Save crosswalk mapping to JSON
            caminho_crosswalk = os.path.join(
                DATA_FOLDER, "alinhamentos", str(new_crosswalk_id)
            )
            with open(caminho_crosswalk, "w") as file:
                json.dump(crosswalk_dict, file)

            # Save controlled vocabulary mapping to CSV
            caminho_crosswalk_vocabulario = os.path.join(
                DATA_FOLDER, "alinhamentos", f"{new_crosswalk_id}_vocabulario"
            )
            pd.DataFrame(crosswalk_vocabulary, columns=["Campos_Ajutados"]).to_csv(
                caminho_crosswalk_vocabulario, index=False
            )

            # Update session and redirect
            session["caminho_crosswalk"] = caminho_crosswalk
            return redirect(url_for("processamento"))

        except Exception as e:
            print(f"Error processing POST request in alinhamento: {e}")
            return render_template("processamento-falha.html")


@app.route("/recuperar_alinhamento", methods=["POST"])
def recuperar_alinhamento():
    # Extract form data
    ind_rec = request.form.get("ind_rec", "").strip()
    recuperacao = request.form.get("recuperacao", "").strip()
    nome_rec = request.form.get("nome_rec", "").strip()

    # Validate required fields
    if not ind_rec or not recuperacao or not nome_rec:
        print("Error: Missing required form fields.")
        return render_template(
            "processamento-falha.html", error="Missing required fields"
        )

    try:
        if ind_rec == "2":
            # Construct the crosswalk file path
            crosswalk_path = os.path.join(DATA_FOLDER, "alinhamentos", recuperacao)

            if not os.path.exists(crosswalk_path):
                print(f"Error: Crosswalk file not found at {crosswalk_path}")
                return render_template(
                    "processamento-falha.html", error="Crosswalk file not found"
                )

            # Read and parse the crosswalk JSON file
            with open(crosswalk_path, "r", encoding="utf-8") as crosswalk_file:
                saved_crosswalk = json.load(crosswalk_file)

            print("Crosswalk Loaded:", saved_crosswalk)

            # Construct the vocabulary file path
            vocab_file = os.path.join(
                DATA_FOLDER, "alinhamentos", f"{recuperacao}_vocabulario"
            )

            if not os.path.exists(vocab_file):
                print(f"Warning: Vocabulary file not found at {vocab_file}")
                crosswalk_path_vocabulary = []
            else:
                # Read vocabulary file
                vocab_df = pd.read_csv(vocab_file, index_col=0)
                if "Campos_Ajutados" not in vocab_df.columns:
                    print(f"Error: Missing 'Campos_Ajutados' column in {vocab_file}")
                    return render_template(
                        "processamento-falha.html",
                        error="Invalid vocabulary file format",
                    )

            crosswalk_path_vocabulary = vocab_df["Campos_Ajutados"].tolist()

            # Render template with retrieved data
            return render_template(
                "editar_alinhamento.html",
                esquema_cco=cco_schema,
                cabecalho_usuario=saved_crosswalk,
                nome_crosswalk=nome_rec,
                caminho_crosswalk_vocabulario=crosswalk_path_vocabulary,
            )

    except json.JSONDecodeError:
        print(f"Error: Failed to parse JSON from {crosswalk_path}")
        return render_template(
            "processamento-falha.html", error="Invalid crosswalk file format"
        )

    except pd.errors.EmptyDataError:
        print(f"Error: Vocabulary file {vocab_file} is empty or unreadable")
        return render_template(
            "processamento-falha.html", error="Vocabulary file is empty"
        )

    except Exception as e:
        print(f"Unexpected error: {e}")
        return render_template(
            "processamento-falha.html", error="An unexpected error occurred"
        )

    # Remove alignment
    if ind_rec == "3":
        try:
            # Define crosswalk file paths
            crosswalk_path = os.path.join(DATA_FOLDER, "alinhamentos", recuperacao)
            vocab_path = os.path.join(
                DATA_FOLDER, "alinhamentos", f"{recuperacao}_vocabulario"
            )

            remove_file_if_exists(crosswalk_path)
            remove_file_if_exists(vocab_path)

            # Load and update saved crosswalks
            if os.path.exists(crosswalk_file):
                croswalk_saved = pd.read_parquet(crosswalk_file)

                # Ensure it's not empty
                if not croswalk_saved.empty:
                    croswalk_saved = croswalk_saved.query(f"nome != '{nome_rec}'")

                    croswalk_saved.to_parquet(crosswalk_file)
                    print(f"Updated crosswalk file: {crosswalk_file}")

            return redirect(url_for("alinhamento"))

        except Exception as e:
            print(f"Error removing alignment: {e}")
            return render_template(
                "processamento-falha.html", error="Failed to remove alignment"
            )


@app.route("/processamento", methods=["GET", "POST"])
def processamento():
    try:
        app.logger.info(f"Current session path: {session['caminho_crosswalk']}")

    except KeyError:
        recuperacao = request.form.get("recuperacao", "").strip()
        caminho_crosswalk = os.path.join(DATA_FOLDER, "alinhamentos", str(recuperacao))
        session["caminho_crosswalk"] = caminho_crosswalk

    # Carregando dados para processamento
    rules_cco = RULES.copy()
    dimencoes_evaluated = DIMENSIONS.copy()

    # Load data from the JSON files
    crosswalk, user_data = load_data(session)

    # Apply the validation rules to the user data
    results_df = apply_rules_to_metadata(
        rules_cco, dimencoes_evaluated, crosswalk, user_data, session
    )

    # Calculate the adequacy scores
    preliminary_results = calculate_adequacy(results_df, dimencoes_evaluated, session)

    # Analyze the results and prepare data for the report
    analyze_results(preliminary_results, session)

    # Save the results to an Excel file
    filename = session["user_sent_filename"] + ".xlsx"
    filepath = os.path.join(DATA_FOLDER, filename)
    session["arquivo_download"] = filepath
    preliminary_results.to_excel(filepath)
    print(preliminary_results.head(5))

    return redirect(url_for("relatorio"))


@app.route("/relatorio", methods=["GET"])
def relatorio():
    return render_template(
        "report.html",
        adequacao_total=session.get("adequacao_total", 0),
        adequacao_por_dimensao_adequacao=session.get("adequacao_por_dimensao_adequacao", []),
        adequacao_por_dimensao_dimencoes=session.get("adequacao_por_dimensao_dimencoes", []),
        dimensoes=session.get("dimensoes", {}),
        campos=session.get("campos", {}),
        valores_campos=session.get("valores_campos", {}),
        regras=session.get("regras", {}),
        soma_total_0=session.get("soma_total_0", 0),
        soma_total_1=session.get("soma_total_1", 0),
        dimension_labels=session.get("dimension_labels", []),
        dimension_mismatches=session.get("dimension_mismatches", []),
        dimension_matches=session.get("dimension_matches", []),
        dimension_mismatch_counts=session.get("dimension_mismatch_counts", {}),
        heatmap_data = session.get("heatmap_data", {})

    )


@app.route("/download", methods=["GET"])
def download():
    arquivo = session["arquivo_download"]
    return send_file(arquivo, as_attachment=True)


if __name__ == "__main__":
    app.run(port=5001, debug=True)
