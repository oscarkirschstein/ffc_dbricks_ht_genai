from groq import Groq
import json
import time


def extract_diagnosis(doctor_note, max_retries=3, retry_delay=2):
    client = Groq(api_key="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")
 
    prompt = """You are a medical expert that ONLY TALKS IN JSON. Given a medical case description, extract and return only the main clinical diagnosis that can be found given the information. If the clinical diagnosis is very unclear, return 'unknown', if the text is unrelated to a medical diagnosis, then return 'unrelated'. DON'T RETURN ANYTHING ELSE BUT THE CLINICAL DIAGNOSIS.
    The clinical diagnosis should be a single, concise diagnosis given in the following JSON format:
    {
        "diagnosis": "the clinical diagnosis",
        "reasoning": "a brief and concise explanation of the pointers that led to the diagnosis"
    }
 
    EXAMPLES:
        EXAMPLE INPUT 1:
        CASE: This patient's history of recurrent kidney stones, osteopenia, and high-dose vitamin D supplementation, along with laboratory findings of hypercalcemia and hypercalciuria, suggest the possibility of vitamin D toxicity. Excessive intake of vitamin D can cause increased absorption of calcium from the gut, leading to hypercalcemia and hypercalciuria, which can result in kidney stones and bone loss. Treatment would involve stopping the vitamin D supplementation and potentially providing intravenous fluids and loop diuretics to promote the excretion of calcium.
        EXAMPLE OUTPUT 1:
        {
            "diagnosis": "vitamin d toxicity",
            "reasoning": "Recurrent kidney stones, osteopenia, and high-dose vitamin D supplementation, laboratory findings of hypercalcemia and hypercalciuria."
        }
        
        EXAMPLE INPUT 2:
        CASE: A 45-year-old patient presents with vague symptoms including fatigue, mild joint pain, and occasional headaches. Physical examination reveals no significant findings, and initial laboratory tests are within normal ranges. The patient's medical history is unremarkable, and they report no recent travel or exposure to infectious diseases. Despite thorough questioning, no clear pattern or specific triggers for the symptoms can be identified.
        EXAMPLE OUTPUT 2:
        {
            "diagnosis": "unknown",
            "reasoning": ""
        }
        
        EXAMPLE INPUT 3:
        CASE: This child's symptoms of a red, bulging tympanic membrane with systemic symptoms such as fever and headache, and the additional symptoms of dizziness and a spinning sensation, raise concern for complications of acute otitis media. The differential diagnosis could include labyrinthitis or possibly even mastoiditis. Urgent evaluation, including further imaging studies such as a CT or MRI scan, may be necessary. This child likely requires admission for intravenous antibiotics and possibly surgical intervention if mastoiditis is confirmed.
        EXAMPLE OUTPUT 3:
        {
            "diagnosis": "acute otitis media, possible complication of labyrinthitis or mastoiditis",
            "reasoning": "Red, bulging tympanic membrane with systemic symptoms such as fever, headache, dizziness and a spinning sensation."
        }

        EXAMPLE INPUT 4:
        CASE: While the symptoms might initially suggest asthma, the lack of response to bronchodilators indicates a different cause. A possible diagnosis in this case might be idiopathic pulmonary fibrosis, a type of lung disease that results in scarring (fibrosis) of the lungs for an unknown reason. High-resolution CT of the chest would be the next step in diagnosis.
        EXAMPLE OUTPUT 4:
        {
            "diagnosis": "idiopathic pulmonary fibrosis",
            "reasoning": "Lack of response to bronchodilators, high-resolution CT of the chest."
        }
            
        EXAMPLE INPUT 5:
        CASE: The annual report for XYZ Corporation shows a 15% increase in revenue compared to the previous fiscal year. The company attributes this growth to the successful launch of a new product line and expansion into international markets. The board of directors has approved a 5% dividend increase for shareholders. The report also outlines plans for sustainable practices and corporate social responsibility initiatives for the coming year.
        EXAMPLE OUTPUT 5:
        {
            "diagnosis": "unrelated",
            "reasoning": ""
        }
        
        EXAMPLE INPUT 6: (unknown example)
        CASE: The patient is a 30-year-old male who presents with a 2-day history of a headache. The patient reports no fever, sore throat, or cough. The patient's medical history is unremarkable.
        EXAMPLE OUTPUT 6:
        {
            "diagnosis": "unknown",
            "reasoning": ""
        }
    
    INPUT:
    """
 
    prompt += f"CASE: {doctor_note}"

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