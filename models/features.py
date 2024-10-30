from groq import Groq
import json
import time


def extract_features(doctor_note, max_retries=3, retry_delay=2):
    client = Groq(api_key="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")

    # System prompt
    prompt = """You are an assistant that ONLY TALKS JSON. You are tasked with converting unstructured doctor appointment-notes into structured JSON format, containing information about medical symptoms. 
    The JSON should follow the following FORMAT:
        {
            "symptoms":{
                "name_of_symptom_including_location":{
                    "description":"short description of the symptom within the context of the note",
                    "location":"location of the symptom on the body. Empty string if not applicable",
                    "intensity":"integer intensity (value between 0 and 10) of the symptom, this includes the intensity of the symptom in the context of the note. -1 if not mentioned",
                    "is_active":"False ONLY if explicit reference is made to that symptom having ceased",
                    "raw_data":"the region in the text where the symptom is mentioned",
                },
            }
        }

    Don't return anything but the symptoms in the valid JSON FORMAT. Here is an example of what you should OUTPUT:
 
    EXAMPLE INPUT NOTE:
    The patient describes a dull, aching pain in the lumbar region, radiating to the right hip, with intermittent numbness in the right leg. He said the pain in the lumbar region is moderate.
    He reports taking ibuprofen 400 mg twice daily with moderate relief but notes the symptoms have worsened since last week. 
    The patient says headaches have stopped. Sleep has been disturbed due to discomfort.
    
    EXAMPLE OUTPUT JSON:
    {
        "symptoms": {
            "lumbar pain": {
                "description":"Dull, aching pain in the lumbar region, radiating to the right hip.",
                "location":"lumbar region",
                "intensity":"6",
                "is_active":"True",
                "raw_data":"The patient describes a dull, aching pain in the lumbar region, radiating to the right hip, with intermittent numbness in the right leg.",
            },
            "right hip pain":{
                "description":"Radiating to the right hip.",
                "location":"right hip",
                "intensity":"-1",
                "is_active":"True",
                "raw_data":"radiating to the right hip",
            },
            "right leg numbness":{
                "description":"Intermittent numbness in the right leg.",
                "location":"right leg",
                "intensity":"-1",
                "is_active":"True",
                "raw_data":"with intermittent numbness in the right leg.",
            },
            "headache":{
                "description":"Headaches have stopped.",
                "location":"head",
                "intensity":"-1",
                "is_active":"False",
                "raw_data":"The patient says headaches have stopped.",
            },
            "sleep quality":{
                "description":"Sleep has been disturbed due to discomfort.",
                "location":"-1",
                "intensity":"-1",
                "is_active":"True",
                "raw_data":"The patient says sleep has been disturbed due to discomfort.",
            }
        }
    }
    
    INPUT NOTE:
    """

    # TODO: Intensity has to be quantified

    # User input
    prompt += doctor_note

    # Prepare system output
    prompt += """
    
    OUTPUT JSON:
    """

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-70b-versatile",
            )

            result = response.choices[0].message.content.strip()
            features = json.loads(result)
            return features  # If successful, return the parsed JSON

        except json.JSONDecodeError as e:
            if attempt < max_retries:
                print(
                    f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds..."
                )
                time.sleep(retry_delay)
            else:
                return {
                    "error": {
                        "message": f"Failed to parse features after {max_retries} attempts. Try in a few minutes.\n{e}.",
                        "result": result,
                    }
                }

    # TODO: Error handling for this.
    # TODO; Call to fast and cheap LLM for
    # TODO: Safeguards for the model hallucinating, prompt injection, or nonsensical input.
    # This line should never be reached, but it's here for completeness
    return {
        "error": {
            "message": "Unexpected error occurred.",
            "result": result,
        }
    }
