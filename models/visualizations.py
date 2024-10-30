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


def consolidate_symptoms(doctor_note_files):
    all_symptoms = {}
    doctor_note_files_dict = {}
    for doctor_note_file_path in doctor_note_files:
        # Read the JSON file instead of parsing the file path
        with open(doctor_note_file_path, 'r') as file:
            doctor_note = json.load(file)
        doctor_note_files_dict[os.path.basename(doctor_note_file_path)] = doctor_note
        diagnosis = doctor_note["diagnosis"]["diagnosis"]
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
        res = pd.DataFrame(rows)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        print(f"Raw result: {result}")
        res = pd.DataFrame([{"info": "error", "error": "failed to parse features", "error_message": str(e), "result": result}])
    except KeyError as e:
        print(f"KeyError: {e}")
        print(f"Raw result: {result}")
        res = pd.DataFrame([{"info": "error", "error": "missing key in parsed data", "error_message": str(e), "result": result}])
    except Exception as e:
        print(f"Unexpected error: {e}")
        print(f"Raw result: {result}")
        res = pd.DataFrame([{"info": "error", "error": "unexpected error", "error_message": str(e), "result": result}])
    
    return result, res


def visualize_symptoms(df):
    if df.empty:
        return None

    # Ensure 'is_active' is of boolean type
    df['is_active'] = df['is_active'].astype(bool)
    # Convert 'intensity' to numeric type
    df['intensity'] = pd.to_numeric(df['intensity'], errors='coerce')
    df['date'] = pd.to_datetime(df['date'])
    date_range = df['date'].agg(['min', 'max'])
    active_symptoms = df[df['is_active']].copy()

    color_scale = [
        [0, 'rgba(0,255,0,0.7)'],      # Light green with transparency
        [0.25, 'rgba(173,255,47,0.7)'], # Light yellowgreen with transparency
        [0.5, 'rgba(255,255,0,0.7)'],   # Light yellow with transparency
        [0.75, 'rgba(255,165,0,0.7)'],  # Light orange with transparency
        [1, 'rgba(255,0,0,0.7)']        # Light red with transparency
    ]

    def get_color_from_intensity(intensity):
        # Clamp intensity to be within [0, 1]
        intensity = max(0, min(intensity, 1))
        
        if intensity <= 0:
            return 'rgba(0,255,0,0.35)'
        elif intensity <= 0.25:
            r = int(0 + (173-0) * (intensity/0.25))
            g = 255
            b = int(0 + (47-0) * (intensity/0.25))
            return f'rgba({r},{g},{b},0.35)'
        elif intensity <= 0.5:
            r = int(173 + (255-173) * ((intensity-0.25)/0.25))
            g = 255
            b = int(47 + (0-47) * ((intensity-0.25)/0.25))
            return f'rgba({r},{g},{b},0.35)'
        elif intensity <= 0.75:
            r = 255
            g = int(255 + (165-255) * ((intensity-0.5)/0.25))
            b = 0
            return f'rgba({r},{g},{b},0.35)'
        else:
            r = 255
            g = int(165 + (0-165) * ((intensity-0.75)/0.25))
            b = 0
            return f'rgba({r},{g},{b},0.35)'

    # Enhanced hover text with emoji indicators and reasons
    active_symptoms['hover_text'] = (
        '📅 Date: ' + active_symptoms['date'].dt.strftime('%Y-%m-%d') + 
        '<br>🔥 Intensity: ' + active_symptoms['intensity'].astype(str) +
        '<br>📝 Reason: ' + active_symptoms['raw_data']
    )

    fig = go.Figure()

    # Get unique symptom positions
    unique_symptoms = active_symptoms['symptom'].unique()
    symptom_positions = {symptom: i for i, symptom in enumerate(unique_symptoms)}

    # Add traces for each symptom with enhanced styling
    for symptom in unique_symptoms:
        mask = active_symptoms['symptom'] == symptom
        symptom_data = active_symptoms[mask].sort_values('date')
        y_position = symptom_positions[symptom]
        
        # Add connecting gradient shapes with glowing effect
        for i in range(len(symptom_data)-1):
            # Get the next point in the original dataset after current point
            current_date = symptom_data['date'].iloc[i]
            next_date = symptom_data['date'].iloc[i+1]
            
            # Find any inactive points between these dates
            inactive_between = df[
                (df['symptom'] == symptom) & 
                (df['date'] > current_date) & 
                (df['date'] < next_date) & 
                (~df['is_active'])
            ]
            
            # Only add the colored boxes if there are no inactive points between
            if len(inactive_between) == 0:
                # Create multiple small rectangles to create a smooth gradient effect
                num_steps = 20  # Number of gradient steps
                start_intensity = symptom_data['intensity'].iloc[i]
                end_intensity = symptom_data['intensity'].iloc[i+1]
                
                for step in range(num_steps):
                    # Calculate the position and intensity for this step
                    x0 = current_date + (next_date - current_date) * (step/num_steps)
                    x1 = current_date + (next_date - current_date) * ((step+1)/num_steps)
                    intensity = start_intensity + (end_intensity - start_intensity) * (step/num_steps)
                    
                    # Add a trail to the leftmost box of a sequence
                    if step == 0:
                        x0 = current_date
                        x1 = current_date + (next_date - current_date) * (0.1/num_steps)
                        fig.add_shape(
                            type="rect",
                            x0=x0,
                            x1=x1,
                            y0=y_position-0.35,
                            y1=y_position+0.35,
                            fillcolor=get_color_from_intensity(intensity),
                            line=dict(width=0),
                            layer='below'
                        )
                    # Add a transparent trail to the left of the next box if the sequence was interrupted by an is_active = False
                    elif len(inactive_between) > 0:
                        x0 = current_date
                        x1 = current_date + (next_date - current_date) * (0.1/num_steps)
                        fig.add_shape(
                            type="rect",
                            x0=x0,
                            x1=x1,
                            y0=y_position-0.35,
                            y1=y_position+0.35,
                            fillcolor='rgba(255,255,255,0)',
                            line=dict(width=0),
                            layer='below'
                        )
                    
                    fig.add_shape(
                        type="rect",
                        x0=x0,
                        x1=x1,
                        y0=y_position-0.35,
                        y1=y_position+0.35,
                        fillcolor=get_color_from_intensity(intensity),
                        line=dict(width=0),
                        layer='below'
                    )
        
        fig.add_trace(
            go.Scatter(
                x=symptom_data['date'],
                y=[y_position] * len(symptom_data),
                mode='markers+lines',
                marker=dict(
                    size=25,
                    symbol='circle',
                    color=symptom_data['intensity'],
                    colorscale=color_scale,
                    showscale=True,
                    cmin=0.0,  # Set minimum of color scale
                    cmax=1.0,  # Set maximum of color scale
                    colorbar=dict(
                        title="Intensity Level",
                        titleside="right",
                        thickness=15,
                        len=0.4,
                        bgcolor='rgba(255,255,255,0.9)',
                        bordercolor='rgba(255,255,255,0.9)',
                        tickfont=dict(size=12),
                        tickmode='linear',
                        tick0=0.0,
                        dtick=0.2
                    ),
                    line=dict(color='white', width=2)
                ),
                line=dict(
                    color='rgba(153, 102, 255, 0.3)',
                    width=3
                ),
                name=symptom,
                hovertext=symptom_data['hover_text'],
                hoverinfo='text',
            )
        )

    fig.update_layout(
        title=dict(
            text="Symptom Intensity Timeline",
            font=dict(size=24, color='#2d3436'),
            x=0.5,
            y=0.95
        ),
        paper_bgcolor='rgba(240,242,245,0.95)',
        plot_bgcolor='rgba(240,242,245,0.95)',
        xaxis=dict(
            title="Timeline",
            title_font=dict(size=14),
            type='date',
            range=[date_range['min'], date_range['max']],
            showgrid=True,
            gridcolor='rgba(128,128,128,0.2)',
            linecolor='rgba(128,128,128,0.4)',
            zeroline=False
        ),
        yaxis=dict(
            title="Symptoms",
            title_font=dict(size=14),
            ticktext=list(unique_symptoms),
            tickvals=list(range(len(unique_symptoms))),
            categoryorder="array",
            categoryarray=list(unique_symptoms),
            gridcolor='rgba(128,128,128,0.2)',
            linecolor='rgba(128,128,128,0.4)',
            zeroline=False
        ),
        height=700,
        showlegend=False,
        margin=dict(l=150, r=100, t=100, b=50),
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,

        )
    )

    # Add subtle grid pattern
    fig.update_xaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128,128,128,0.1)',
        minor=dict(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='rgba(128,128,128,0.05)'
        )
    )
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128,128,128,0.1)'
    )

    return fig