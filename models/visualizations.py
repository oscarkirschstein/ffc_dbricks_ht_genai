from groq import Groq
import json
import os
import pandas as pd
import re
import plotly.express as px


def clean_filename(filename):
    # Use regex to match the expected format: 'doctor_note_yyyymmdd_hhmmss.json' and return the matched string
    match = re.search(r'doctor_note_\d{8}_\d{6}\.json', filename)
    return match.group(0) if match else None


def consolidate_symptoms(doctor_note_files):
    all_symptoms = {}
    doctor_note_files_dict = {}
    for doctor_note_file_path in doctor_note_files:
        # Read the JSON file instead of parsing the file path
        with open(doctor_note_file_path, 'r') as file:
            doctor_note = json.load(file)
        doctor_note_files_dict[os.path.basename(doctor_note_file_path)] = doctor_note
        pathology = doctor_note["pathology"]
        features = doctor_note["features"]
        for symptom, _ in features["symptoms"].items():
            # Convert tuple to string for JSON serialization
            key = f"({os.path.basename(doctor_note_file_path)}, {pathology})"
            if key not in all_symptoms:
                all_symptoms[key] = []
            all_symptoms[key]+= [symptom]
    
    input_json_string = json.dumps(all_symptoms, indent=2)
    
    client = Groq(api_key="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")

    prompt = """You are tasked with matching symptoms from multiple doctor notes into structured JSON format that maps symptoms to similar symptoms across multiple doctor notes.
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
        "(doctor_note_file_1, pathology_1)":[
            "symptom_1_as_in_doctor_note_1",
            "symptom_2_as_in_doctor_note_1",
            "symptom_3_as_in_doctor_note_1",
            ...
        ],
        "(doctor_note_file_2, pathology_2)":[
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
        symptom_mapping = json.loads(result)
        res = symptom_mapping
        # consolidate the symptoms into a single dataframe
        rows = []
        # Loop through each symptom in the symptom_mapping
        for symptom in symptom_mapping["symptoms"]:
            # Loop through each doctor note file name in the symptom mapping
            for doctor_note_file_name in symptom_mapping["symptoms"][symptom]:
                symptom_name = symptom_mapping["symptoms"][symptom][doctor_note_file_name]
                doctor_note_file_name = clean_filename(doctor_note_file_name)
                doctor_note = doctor_note_files_dict[doctor_note_file_name]
                pathology = doctor_note["pathology"]
                symptom_data = doctor_note["features"]["symptoms"][symptom_name]
                rows.append({"symptom": symptom, "symptom_name": symptom_name, "doctor_note_file": doctor_note_file_name, "pathology": pathology, "date": doctor_note["date"],
                             "location": symptom_data["location"],
                             "duration": symptom_data["duration"],
                             "frequency": symptom_data["frequency"],
                             "intensity": symptom_data["intensity"],
                             "is_active": symptom_data["is_active"],
                             "raw_data": symptom_data["raw_data"]})
        res = pd.DataFrame(rows)
    except json.JSONDecodeError as e:
        res = pd.DataFrame([{"info": "error", "error": "failed to parse features", "error_message": e, "result": result}])
    return result, res


def visualize_symptoms(df):
    # Create figure(s) based on the dataframe and return the figure(s)
    figures = []
    
    if not df.empty:
        # If there is any symptom that has multiple entries, we need to visualize the symptom across all doctor notes
        unique_symptoms = df["symptom"].unique()
        # for symptom in unique_symptoms:
        #     symptom_df = df[df["symptom"] == symptom]
        columns = ['symptom', 'intensity', 'is_active']
        df = df[columns]
        if len(df) > 1:
            # Visualize the symptom
            fig = px.bar(df, x="symptom", y="intensity", color="is_active", barmode="group")
            figures.append(fig)
        return figures
    else:
        return []
