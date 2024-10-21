from groq import Groq
import json
import pandas as pd


def consolidate_features(doctor_note_files):
    all_symptoms = {}
    for doctor_note_file in doctor_note_files:
        doctor_note = json.load(doctor_note_file)
        pathology = doctor_note["pathology"]
        features = doctor_note["features"]
        for symptom in features["symptoms"]:
            all_symptoms[(doctor_note_file, pathology)] = [features["symptoms"][symptom]]
    input_json_string = json.dumps(all_symptoms, indent=2)
    
    client = Groq(api_key="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")

    prompt = """You are tasked with matching symptoms from multiple doctor notes into structured JSON format that maps symptoms to similar symptoms across multiple doctor notes.
    The JSON output should follow the following structure:
    {
        "symptoms":{
            "symptom":{
                "doctor_note_file_1":["symptom_name_as_in_doctor_note_1"],
                "doctor_note_file_2":["symptom_name_as_in_doctor_note_2"],
                ...
            }
        }
    }
    DON'T RETURN ANYTHING ELSE BUT THE MAPPING OF SYMPTOMS IN VALID JSON FORMAT.
 
    EXAMPLE INPUT:
    {
        "(doctor_note_file_1, pathology_1)":{
            "symptom_1":["symptom_name_as_in_doctor_note_1"],
            "symptom_2":["symptom_name_as_in_doctor_note_1"],
            ...
        },
        "(doctor_note_file_2, pathology_2)":{
            "symptom_1":["symptom_name_as_in_doctor_note_2"],
            "symptom_2":["symptom_name_as_in_doctor_note_2"],
            ...
        },
        ...
    }
    EXAMPLE OUTPUT:
    {
        "symptoms":{
            "symptom_1":{
                "doctor_note_file_1":["symptom_name_as_in_doctor_note_1"],
                "doctor_note_file_2":["symptom_name_as_in_doctor_note_2"],
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
        # res = pd.DataFrame(columns=["symptom", "doctor_note_file", "pathology", "location", "duration", "frequency", "intensity", "is_active", "raw_date"])
        # for symptom in symptom_mapping["symptoms"]:
        #     for doctor_note_file in symptom_mapping["symptoms"][symptom]:
        #         doctor_note = doctor_note_files[doctor_note_file]
        #         pathology = doctor_note["pathology"]
        #         symptom_data = symptom_mapping["symptoms"][symptom][doctor_note_file][0]
        #         res = res.append({"symptom": symptom, "doctor_note_file": doctor_note_file, "pathology": pathology,
        #                                 "location": symptom_data["location"],
        #                                 "duration": symptom_data["duration"],
        #                                 "frequency": symptom_data["frequency"],
        #                                 "intensity": symptom_data["intensity"],
        #                                 "is_active": symptom_data["is_active"],
        #                                 "raw_date": symptom_data["raw_data"]}, ignore_index=True)
    except json.JSONDecodeError as e:
        res = {"error": f"Failed to parse features.\n{e}.\nResult: {result}."}
    return res