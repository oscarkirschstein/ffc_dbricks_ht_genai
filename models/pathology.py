from groq import Groq
 
 
def extract_pathologies(doctor_note):
    client = Groq(api_key="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")
 
    prompt = """Given the following medical case description, extract and return only the main pathology or condition mentioned. If the pathology is very unclear, return 'unknown', if the text is unrelated to a pathology description, then return 'unrelated'. DON'T RETURN ANYTHING ELSE BUT THE PATHOLOGY:
 
    CASE:
    {}
 
    EXAMPLES:
    EXAMPLE INPUT 1:
    CASE: This patient's history of recurrent kidney stones, osteopenia, and high-dose vitamin D supplementation, along with laboratory findings of hypercalcemia and hypercalciuria, suggest the possibility of vitamin D toxicity. Excessive intake of vitamin D can cause increased absorption of calcium from the gut, leading to hypercalcemia and hypercalciuria, which can result in kidney stones and bone loss. Treatment would involve stopping the vitamin D supplementation and potentially providing intravenous fluids and loop diuretics to promote the excretion of calcium.
    EXAMPLE OUTPUT 1:
    vitamin d toxicity
    
    EXAMPLE INPUT 2:
    CASE: A 45-year-old patient presents with vague symptoms including fatigue, mild joint pain, and occasional headaches. Physical examination reveals no significant findings, and initial laboratory tests are within normal ranges. The patient's medical history is unremarkable, and they report no recent travel or exposure to infectious diseases. Despite thorough questioning, no clear pattern or specific triggers for the symptoms can be identified.
    EXAMPLE OUTPUT 2:
    unknown
    
    EXAMPLE INPUT 3:
    CASE: This child's symptoms of a red, bulging tympanic membrane with systemic symptoms such as fever and headache, and the additional symptoms of dizziness and a spinning sensation, raise concern for complications of acute otitis media. The differential diagnosis could include labyrinthitis or possibly even mastoiditis. Urgent evaluation, including further imaging studies such as a CT or MRI scan, may be necessary. This child likely requires admission for intravenous antibiotics and possibly surgical intervention if mastoiditis is confirmed.
    EXAMPLE OUTPUT 3:
    acute otitis media, possible complication of labyrinthitis or mastoiditis
            
    EXAMPLE INPUT 4:
    CASE: While the symptoms might initially suggest asthma, the lack of response to bronchodilators indicates a different cause. A possible diagnosis in this case might be idiopathic pulmonary fibrosis, a type of lung disease that results in scarring (fibrosis) of the lungs for an unknown reason. High-resolution CT of the chest would be the next step in diagnosis.
    EXAMPLE OUTPUT 4:
    idiopathic pulmonary fibrosis
        
    EXAMPLE INPUT 5:
    CASE: The annual report for XYZ Corporation shows a 15% increase in revenue compared to the previous fiscal year. The company attributes this growth to the successful launch of a new product line and expansion into international markets. The board of directors has approved a 5% dividend increase for shareholders. The report also outlines plans for sustainable practices and corporate social responsibility initiatives for the coming year.
    EXAMPLE OUTPUT 5:
    unrelated
    """
 
    formatted_prompt = prompt.format(doctor_note)
 
    response = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": formatted_prompt
            }
        ],
        model="llama-3.1-70b-versatile",
    )
    
    result = response.choices[0].message.content.strip()
    return result