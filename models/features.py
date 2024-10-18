from groq import Groq
import json


def extract_features(doctor_note):
    client = Groq(api_key="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")

    prompt = """You are tasked with converting unstructured doctor appointment-notes into structured JSON format. More specifically, you are tasked with extracting information about pathological symptoms. 
    The JSON should follow the following structure:
        {
            "symptoms":{
                "name_of_symptom_including_location":{
                    "description":"short description of the symptom within the context of the note",
                    "location":"location of the symptom on the body. Empty string if not applicable",
                    "duration":"timedelta duration of the symptom in DAYS. -1 if not mentioned",
                    "frequency":"integer frequency of the symptom in TIMES PER DAY. -1 if not mentioned",
                    "intensity":"integer intensity of the symptom. -1 if not mentioned",
                    "is_active":"False ONLY if explicit reference is made to that symptom having ceased",
                    "raw_data":"the region in the text where the symptom is mentioned",
                },
            }
        }
    DON'T RETURN ANYTHING ELSE BUT THE FEATURES IN VALID JSON FORMAT.
 
    EXAMPLE INPUT:
    The patient describes a dull, aching pain in the lumbar region, radiating to the right hip, with intermittent numbness in the right leg. 
    He reports taking ibuprofen 400 mg twice daily with moderate relief but notes the symptoms have worsened since last week. 
    The patient says headaches have stopped. Sleep has been disturbed due to discomfort.
    EXAMPLE OUTPUT:
    {
        "symptoms": {
            "lower lumbarpain": {
                "description":"Dull, aching pain in the lumbar region, radiating to the right hip.",
                "location":"lumbar region",
                "duration":"-1",
                "frequency":"-1",
                "intensity":"6",
                "is_active":"True",
                "raw_data":"The patient describes a dull, aching pain in the lumbar region, radiating to the right hip, with intermittent numbness in the right leg.",
            },
            "headache":{
                "description":"Headaches have stopped.",
                "location":"head",
                "duration":"-1",
                "frequency":"-1",
                "intensity":"-1",
                "is_active":"False",
                "raw_data":"The patient says headaches have stopped.",
            },
            "sleep quality":{
                "description":"Sleep has been disturbed due to discomfort.",
                "location":"-1",
                "duration":"-1",
                "frequency":"-1",
                "intensity":"-1",
                "is_active":"True",
                "raw_data":"The patient says sleep has been disturbed due to discomfort.",
            }
        }
    }
    
    INPUT:
    """

    # TODO: I see a lot of overlap between raw_data and description. We should probably just use description.
    # TODO: Intensity has to be quantified
    prompt += doctor_note
    prompt += """
    
                OUTPUT:
                """
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-70b-versatile",
    )

    result = response.choices[0].message.content.strip()
    try:
        features = json.loads(result)
    except json.JSONDecodeError as e:
        features = {"error": f"Failed to parse features.\n{e}.\nResult: {result}."}

    return features
