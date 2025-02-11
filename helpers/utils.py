"""
Autor: Abeil Coelho Júnior
Data de criação: 2023-02-13
Descrição: Projeto de mestrado
Versão: 1
Data de modificação: 2025-02-11
"""

import csv
import json
import os
import re
from typing import List

import pandas as pd
from chardet.universaldetector import UniversalDetector
from flask import session


def detect_encoding(file_path):
    """Detects the encoding of a given file using chardet."""
    try:
        detector = UniversalDetector()
        with open(file_path, "rb") as file:
            for line in file:
                detector.feed(line)
                if detector.done:
                    break

        detector.close()
        encoding = detector.result.get("encoding")
        session["encoding"] = encoding
        print("Encoding detected:", encoding)
        return encoding
    except Exception as e:
        print(f"Error detecting encoding: {e}")
        return None


def detect_delimiter(file_path, encoding):
    """Detects the delimiter of a CSV-like file using csv.Sniffer."""
    delimiters = ["\x00", "\x01", "^", ":", ",", "\t", ";", "|", "~", " "]
    try:
        with open(file_path, encoding=encoding) as file:
            first_line = next(file)
            dialect = csv.Sniffer().sniff(first_line, delimiters)
            delimiter = dialect.delimiter
            session["delimitador"] = delimiter
            print("Delimiter detected:", delimiter)
            return delimiter
    except Exception as e:
        print(f"Error detecting delimiter: {e}")
        return None


def remove_file_if_exists(file_path):
    """
    Safely removes a file if it exists.

    Args:
        file_path (str): The full path of the file to remove.

    Returns:
        bool: True if the file was removed, False if it didn't exist or failed to delete.
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Deleted: {file_path}")
            return True
        else:
            print(f"Warning: File not found - {file_path}")
            return False
    except Exception as e:
        print(f"Error deleting {file_path}: {e}")
        return False


def verificador_multivalor(
    regex: str, valores: List[str], negativo: int, tipo: str, compiled_regex=None
) -> bool:
    """
    Checks if at least one value in a list matches the given regex.

    Args:
        regex: The regex pattern to match.
        valores: List of values to verify.
        negativo: If 1, reverses the result.
        tipo: "Match" for re.match, otherwise uses re.fullmatch.
        compiled_regex: Precompiled regex object (optional)

    Returns:
        True if at least one value matches the regex (or none, if negativo=1), False otherwise.
    """
    try:
        if compiled_regex is None:
            compiled_regex = re.compile(regex)

        if tipo == "Match":
            matches = [compiled_regex.match(valor) for valor in valores]
        else:
            matches = [compiled_regex.fullmatch(valor) for valor in valores]

        # Check if at least one value matches the regex and flip the result if 'negativo' is set
        result = any(matches)
        return not result if negativo == 1 else result

    except Exception as e:
        print(
            f"Error in verificador_multivalor: {e} for regex '{regex}' and values '{valores}'"
        )
        return False


def verificador(
    regex: str,
    valor: str,
    negativo: int,
    tipo: str,
    nome_regra: str,
    museu: str,
    metadado: str,
    id: str,
    controlled_vocab: pd.DataFrame = None,
    compiled_regex=None,
) -> bool:
    """
    Verifies if a given value matches a rule based on regex, controlled vocabulary, and catalog language.

    Args:
        regex: The regex pattern to match.
        valor: The value to verify.
        negativo: If 1, reverses the result.
        tipo: "Match" for re.match, otherwise uses re.fullmatch.
        nome_regra: Name of the rule to apply.
        museu: Museum reference (not used in logic but kept for future use).
        metadado: Metadata field being checked.
        id: Path or identifier for controlled vocabulary file (or None if not applicable).
        controlled_vocab: DataFrame containing the controlled vocabulary (pre-loaded).
        compiled_regex: Precompiled regex object (optional)

    Returns:
        bool: True if the value meets the rule, False otherwise.
    """
    valor = str(valor)  # Ensure value is a string

    if valor == "<-99>":
        return False

    if nome_regra == "Fazer uso de vocabulário controlado":
        if controlled_vocab is None:
            print("Controlled vocabulary is required but not provided.")
            return False

        # Check if the metadata value is present in the controlled vocabulary
        controlled_check = controlled_vocab.query(
            "Campos_Ajutados == '{}'".format(metadado)
        )
        return controlled_check.shape[0] > 0

    elif nome_regra == "Usar o mesmo idioma do catálogo":
        return True  # always returns True

    # Handle multivalued fields (split by '|')
    if "|" in valor:
        return verificador_multivalor(
            regex, valor.split("|"), negativo, tipo, compiled_regex
        )

    # Extract the value after '>' if present
    if ">" in valor:
        valor = valor.split("> ")[-1]

    try:
        if compiled_regex is None:
            compiled_regex = re.compile(regex)

        # Perform regex matching
        match = (
            compiled_regex.match(valor)
            if tipo == "Match"
            else compiled_regex.fullmatch(valor)
        )
        result = match is not None

        # Reverse result if 'negativo' flag is set
        return not result if negativo == 1 else result

    except Exception as e:
        print(f"Error in verificador: {e} for rule {nome_regra}, value '{valor}'")
        return False


def load_data(session):
    """Loads data from files based on session information."""
    try:
        with open(session["caminho_crosswalk"]) as f:
            crosswalk = json.load(f)

        user_data = pd.read_csv(
            session["user_sent_file_path"],
            sep=session["delimitador"],
            encoding=session["encoding"],
        )
        user_data = user_data.loc[:, ~user_data.columns.str.match("Unnamed")]
        user_data = user_data.rename(columns=crosswalk)
        user_data = user_data.loc[:, ~user_data.columns.str.startswith("Não utilizar")]
        user_data = user_data.fillna("<-99>")

        return crosswalk, user_data

    except FileNotFoundError as e:
        print(f"File not found: {e}")
        raise  # Re-raise to be handled in the route

    except ValueError as e:
        print(f"JSON decode error: {e}")
        raise

    except Exception as e:
        print(f"Error loading data: {e}")
        raise


def apply_rules_to_metadata(metadata_rules, dimensions, crosswalk, user_data, session):
    """Applies validation rules to metadata fields."""

    controlled_vocab_path = session["caminho_crosswalk"] + "_vocabulario"

    try:
        controlled_vocab = pd.read_csv(controlled_vocab_path, index_col=0)
    except FileNotFoundError:
        print(f"Controlled vocabulary file not found: {controlled_vocab_path}")
        controlled_vocab = None

    metadata_fields = list(set(crosswalk.values()))
    if "Não utilizar" in metadata_fields:
        metadata_fields.remove("Não utilizar")

    all_results = []  # Accumulate results for efficient concatenation

    total_records = user_data.shape[0]  # Calculate this *once*

    for metadata_field in metadata_fields:
        # Select applicable rules for the metadata field
        applicable_rules = metadata_rules[
            metadata_rules.iloc[:, 1].str.contains(metadata_field)
        ]

        # Select the corresponding column
        metadata_column = user_data[metadata_field]

        # Apply all rules to the column in a vectorized manner
        for index, rule in applicable_rules.iterrows():
            rule_name = rule.iloc[0]
            regex_string = rule.iloc[2]  # grab the regex string
            is_negative = rule.iloc[3]
            data_type = rule.iloc[4]

            try:
                compiled_regex = re.compile(regex_string)  # precompile regex
            except re.error as e:
                print(f"Invalid regex '{regex_string}' for rule {rule_name}: {e}")
                continue  # Skip to the next rule if the regex is invalid

            # Apply the rule using a function (see below for definition)
            evaluations = metadata_column.apply(
                lambda x: verificador(
                    regex_string,
                    x,
                    is_negative,
                    data_type,
                    rule_name,
                    session["user_sent_filename"],
                    metadata_field,
                    controlled_vocab_path,
                    controlled_vocab,
                    compiled_regex=compiled_regex,
                )
            )

            results = pd.DataFrame(
                {
                    "Avaliacao": evaluations,
                    "Dado": metadata_column,
                    "Colecao": session["user_sent_filename"],
                    "Campo_Metadado": metadata_field,
                    "Regra": rule_name,
                    "Regex": regex_string,
                    "Total": total_records,
                }
            )

            all_results.append(results)

    # Concatenate all results *once* after the loops
    all_results_df = pd.concat(
        all_results, ignore_index=True
    )  # ignore_index for efficiency
    return all_results_df


def calculate_adequacy(results_df, dimensions, session):
    """Calculates adequacy scores based on the processed data."""

    # Group, aggregate, and pivot the data
    grouped_data = (
        results_df.groupby(
            [
                "Colecao",
                "Regra",
                "Campo_Metadado",
                "Dado",
                "Avaliacao",
                "Regex",
                "Total",
            ]
        )
        .agg(result=("Avaliacao", "count"))
        .reset_index()
    )

    pivoted_data = grouped_data.pivot(
        index=["Colecao", "Campo_Metadado", "Regra", "Dado", "Total"],
        columns=["Avaliacao"],
        values="result",
    ).reset_index()

    pivoted_data = pivoted_data.rename(columns={False: "0", True: "1"})
    pivoted_data = pivoted_data.fillna(0)

    # Merge with dimension data
    preliminary_results = pd.merge(
        pivoted_data, dimensions, how="left", on="Campo_Metadado"
    )
    preliminary_results = preliminary_results[
        ["Colecao", "Dimensão", "Campo_Metadado", "Regra", "Dado", "0", "1", "Total"]
    ]
    preliminary_results = preliminary_results.sort_values(
        by=["Dimensão", "Campo_Metadado"]
    ).reset_index(drop=True)

    return preliminary_results


def analyze_results(preliminary_results, session):
    """Analyzes preliminary results to calculate adequacy scores and prepare data for reporting."""

    # Adequacy by rule
    adequacy_by_rule = (
        preliminary_results.groupby(["Colecao", "Dimensão", "Campo_Metadado", "Regra"])
        .agg(num_mismatches=("0", "sum"), num_matches=("1", "sum"))
        .reset_index()
    )

    adequacy_by_rule_clean = adequacy_by_rule[
        [
            "Colecao",
            "Dimensão",
            "Campo_Metadado",
            "Regra",
            "num_matches",
            "num_mismatches",
        ]
    ]

    # Total Adequacy
    total_adequacy = (
        adequacy_by_rule_clean.groupby(["Colecao"])
        .agg(
            num_mismatches=("num_mismatches", "sum"), num_matches=("num_matches", "sum")
        )
        .reset_index()
    )

    total_adequacy["Total"] = (
        total_adequacy["num_mismatches"] + total_adequacy["num_matches"]
    )
    total_adequacy["Adequacy"] = (
        total_adequacy["num_matches"] / total_adequacy["Total"]
    ) * 100
    session["adequacao_total"] = total_adequacy["Adequacy"].astype("int").to_list()[0]

    # Adequacy by Dimension
    adequacy_by_dimension = (
        adequacy_by_rule_clean.groupby(["Colecao", "Dimensão"])
        .agg(
            num_mismatches=("num_mismatches", "sum"), num_matches=("num_matches", "sum")
        )
        .reset_index()
    )

    adequacy_by_dimension["Total"] = (
        adequacy_by_dimension["num_mismatches"] + adequacy_by_dimension["num_matches"]
    )
    adequacy_by_dimension["Adequacy"] = (
        adequacy_by_dimension["num_matches"] / adequacy_by_dimension["Total"]
    ) * 100

    adequacy_by_dimension = adequacy_by_dimension[["Dimensão", "Adequacy"]]
    adequacy_by_dimension = adequacy_by_dimension.sort_values(by=["Dimensão"])

    session["adequacao_por_dimensao_dimencoes"] = adequacy_by_dimension[
        "Dimensão"
    ].to_list()
    session["adequacao_por_dimensao_adequacao"] = (
        adequacy_by_dimension["Adequacy"].astype("int").to_list()
    )

    adequacy_by_dimension = adequacy_by_dimension.query("Adequacy != 100")
    adequacy_by_dimension = adequacy_by_dimension.sort_values(by=["Dimensão"])

    analysis_dimensions = adequacy_by_dimension["Dimensão"].to_list()

    dimensions_data = {"dimensao": []}
    fields_data = {}
    field_values_data = {}
    rules_data = {}

    for dimension in analysis_dimensions:
        dimensions_data["dimensao"].append(dimension)

        dimension_adequacy = adequacy_by_rule_clean.query(f"Dimensão == '{dimension}'")
        dimension_adequacy = (
            dimension_adequacy.groupby(["Colecao", "Dimensão", "Campo_Metadado"])
            .agg(
                num_mismatches=("num_mismatches", "sum"),
                num_matches=("num_matches", "sum"),
            )
            .reset_index()
        )

        dimension_adequacy["Total"] = (
            dimension_adequacy["num_mismatches"] + dimension_adequacy["num_matches"]
        )
        dimension_adequacy["Adequacy"] = (
            dimension_adequacy["num_matches"] / dimension_adequacy["Total"]
        ) * 100
        dimension_adequacy = dimension_adequacy.sort_values(
            by=["Adequacy"], ascending=True
        )

        fields_list = dimension_adequacy["Campo_Metadado"].to_list()
        field_values_list = dimension_adequacy["Adequacy"].astype("int").to_list()

        fields_data[dimension] = fields_list
        field_values_data[dimension] = field_values_list

        for field in fields_list:
            field_rules_adequacy = adequacy_by_rule_clean.query(
                f"Dimensão == '{dimension}' and Campo_Metadado == '{field}'"
            )
            field_rules_adequacy = (
                field_rules_adequacy.groupby(["Regra"])
                .agg(
                    num_mismatches=("num_mismatches", "sum"),
                    num_matches=("num_matches", "sum"),
                )
                .reset_index()
            )

            field_rules_adequacy["Total"] = (
                field_rules_adequacy["num_mismatches"]
                + field_rules_adequacy["num_matches"]
            )
            field_rules_adequacy["Adequacy"] = (
                field_rules_adequacy["num_matches"] / field_rules_adequacy["Total"]
            ) * 100

            field_rules_adequacy = field_rules_adequacy.query("Adequacy != 100")
            field_rules_adequacy = field_rules_adequacy.sort_values(
                by=["Adequacy"], ascending=True
            )

            rules_list = field_rules_adequacy["Regra"].to_list()
            rules_data[field] = rules_list

    session["dimensoes"] = dimensions_data
    session["campos"] = fields_data
    session["valores_campos"] = field_values_data
    session["regras"] = rules_data
