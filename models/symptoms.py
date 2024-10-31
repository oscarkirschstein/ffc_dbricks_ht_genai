from groq import Groq
import json
import os
import pandas as pd
import plotly.graph_objects as go
import re


def clean_filename(filename):
    # Use regex to match the expected format: 'doctor_note_yyyymmdd_hhmmss_doctorid_patientid.json' and return the matched string
    match = re.search(r'doctor_note_\d{8}_\d{6}_\d+_\d+\.json', filename)
    return match.group(0) if match else None


def map_symptom_names(doctor_note_files):
    all_symptoms = {}
    for doctor_note_file_path in doctor_note_files:
        # Read the JSON file instead of parsing the file path
        with open(doctor_note_file_path, 'r') as file:
            doctor_note = json.load(file)
        features = doctor_note["features"]
        for symptom in features["symptoms"].items():
            key = os.path.basename(doctor_note_file_path)
            if key not in all_symptoms:
                all_symptoms[key] = []
            all_symptoms[key]+= [symptom]
    
    input_json_string = json.dumps(all_symptoms, indent=2)
    
    client = Groq(api_key="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")

    prompt = """You are an assistant that ONLY TALKS JSON. You are tasked with matching symptoms from multiple doctor notes into structured JSON format that maps symptoms to similar symptoms across multiple doctor notes.
    The JSON output should follow the following structure:
    {
        "symptoms":{
            "symptom":{
                "doctor_note_file_1":"symptom_name_as_in_doctor_note_1",
                "doctor_note_file_2":"symptom_name_as_in_doctor_note_2",
                ...
            }
        }
    }
    DON'T RETURN ANYTHING ELSE BUT THE MAPPING OF SYMPTOMS IN VALID JSON FORMAT.
 
    EXAMPLE INPUT:
    {
        "doctor_note_file_1":[
            "symptom_1_as_in_doctor_note_1",
            "symptom_2_as_in_doctor_note_1",
            "symptom_3_as_in_doctor_note_1",
            ...
        ],
        "doctor_note_file_2":[
            "symptom_1_as_in_doctor_note_2",
            "symptom_2_as_in_doctor_note_2",
            "symptom_4_as_in_doctor_note_2",
            ...
        ],
        ...
    }
    EXAMPLE OUTPUT:
    {
        "symptoms":{
            "symptom_1":{
                "doctor_note_file_1":"symptom_1_as_in_doctor_note_1",
                "doctor_note_file_2":"symptom_1_as_in_doctor_note_2",
                ...
            },
            "symptom_2":{
                "doctor_note_file_1":"symptom_2_as_in_doctor_note_1",
                "doctor_note_file_2":"symptom_2_as_in_doctor_note_2",
                ...
            },
            "symptom_3":{
                "doctor_note_file_1":"symptom_3_as_in_doctor_note_1",
                ...
            },
            "symptom_4":{
                "doctor_note_file_1":"symptom_4_as_in_doctor_note_1",
                ...
            },
            ...
        }
    }
    
    INPUT:
    """

    prompt += input_json_string
    prompt += """
    
                OUTPUT:
                """
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-70b-versatile",
    )

    result = response.choices[0].message.content.strip()
    try:
        res = json.loads(result)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Raw result: {result}")
        res = {"info": "error", "error": "failed to parse features", "error_message": str(e), "result": result}
    except KeyError as e:
        print(f"KeyError: {e}")
        print(f"Raw result: {result}")
        res = {"info": "error", "error": "missing key in parsed data", "error_message": str(e), "result": result}
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"Raw result: {result}")
        res = {"info": "error", "error": "unexpected error", "error_message": str(e), "result": result}
    return res


def create_symptom_dataframe(symptom_mapping, doctor_note_files):
    doctor_note_files_dict = {}
    for doctor_note_file_path in doctor_note_files:
        # Read the JSON file instead of parsing the file path
        with open(doctor_note_file_path, 'r') as file:
            doctor_note = json.load(file)
        doctor_note_files_dict[os.path.basename(doctor_note_file_path)] = doctor_note
    
    rows = []
    # Loop through each symptom in the symptom_mapping
    for symptom in symptom_mapping["symptoms"]:
        # Loop through each doctor note file name in the symptom mapping
        for doctor_note_file_name in symptom_mapping["symptoms"][symptom]:
            symptom_name = symptom_mapping["symptoms"][symptom][doctor_note_file_name]
            doctor_note_file_name = clean_filename(doctor_note_file_name)
            doctor_note = doctor_note_files_dict[doctor_note_file_name]
            # Update this line to correctly access the diagnosis
            diagnosis = doctor_note["diagnosis"]["diagnosis"]
            symptom_data = doctor_note["features"]["symptoms"][symptom_name]
            row = {
                "symptom": symptom,
                "symptom_name": symptom_name,
                "doctor_note_file": doctor_note_file_name,
                "diagnosis": diagnosis,
                "date": doctor_note["date"],
                "location": symptom_data["location"],
                "intensity": symptom_data["intensity"],
                "is_active": symptom_data["is_active"],
                "raw_data": symptom_data["raw_data"]
            }
            # Replace -1 values with None
            row = {k: None if (v == -1 or v == "-1") else v for k, v in row.items()}
            rows.append(row)
    return pd.DataFrame(rows)


def create_symptom_list(symptom_dataframe):
    symptom_list = []
    for _, row in symptom_dataframe.iterrows():
        symptom_entry = {
            "symptom": row["symptom"],
            "date": row["date"],
            "is_active": row["is_active"],
            "intensity": row["intensity"],
            "reason": f"Patient reports {row['symptom_name']}, details: {row['raw_data']}",
        }
        symptom_list.append(symptom_entry)
    return symptom_list


def get_all_symptom_data(doctor_note_files):
    symptom_names_mapping = map_symptom_names(doctor_note_files)
    symptom_dataframe = create_symptom_dataframe(symptom_names_mapping, doctor_note_files)
    symptom_list = create_symptom_list(symptom_dataframe)
    
    return symptom_names_mapping, symptom_dataframe, symptom_list
