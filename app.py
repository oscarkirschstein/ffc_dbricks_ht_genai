import gradio as gr
import json
from gradio_calendar import Calendar
import os
import pandas as pd
from datetime import datetime, date
from models.diagnosis import extract_diagnosis as extract_diagnosis_model
from models.features import extract_features as extract_features_model
from models.visualizations import consolidate_symptoms as consolidate_symptoms_model, visualize_symptoms as visualize_symptoms_model
import io
import re
from PIL import Image
import time

# Global variables
doctor_id = None
patient_id = None
json_files = []
current_json_file = None
consolidated_symptoms_df = pd.DataFrame()
# State for json_files
json_files_state = gr.State([])


# Function to load existing JSON files
def load_existing_json_files():
    global json_files, doctor_id, patient_id
    json_files = []
    doctor_notes_dir = 'data/doctor_notes/'
    
    # Ensure both doctor_id and patient_id are available
    if not doctor_id or not patient_id:
        print("Warning: doctor_id or patient_id is not set")
        return json_files

    for filename in os.listdir(doctor_notes_dir):
        if filename.endswith('.json'):
            # Use regex to match the expected format: 'doctor_note_yyyymmdd_hhmmss_doctorid_patientid.json'
            match = re.search(r'doctor_note_\d{8}_\d{6}_(\d+)_(\d+)\.json', filename)
            if match and match.group(1) == doctor_id and match.group(2) == patient_id:
                json_files.append(os.path.join(doctor_notes_dir, filename))
    
    # Sort files by creation time (most recent first)
    json_files.sort(key=lambda x: os.path.getctime(x), reverse=True)
    
    return json_files

# Function to reset the json_files list
def reset_json_files():
    global json_files
    json_files = []

# Login function to check username and password
def login(username, password):
    global doctor_id  # Add this line
    # Load user data from JSON file
    with open('data/users/users.json', 'r') as file:
        users = json.load(file)
    for user_id, user_info in users.items():
        if user_info['username'] == username and user_info['password'] == password:
            # Login successful, show home page
            if user_info['role'] == 'doctor':  # Add this condition
                doctor_id = user_id  # Store the doctor_id
            return gr.update(visible=False), gr.update(visible=True), gr.update(visible=False, value=""), f"Welcome {user_info['first_name']} {user_info['last_name']}! You are logged in as a {user_info['role']}."
    # Login failed
    return gr.update(visible=True), gr.update(visible=False), gr.update(visible=True, value="Incorrect username or password. Please try again."), ""

# Function to load patients from the JSON file
def load_patients():
    with open('data/users/users.json', 'r') as file:
        users = json.load(file)
    patients = {f"{info['first_name']} {info['last_name']}": user_id 
                for user_id, info in users.items() if info['role'] == 'patient'}
    return patients

# Function to update the patient_id when a patient is selected
def update_patient_id(selected_patient_name):
    global patient_id
    if selected_patient_name == "Pick a patient":
        patient_id = None
        return (
            gr.update(open=True),
            "No patient selected",
            gr.update(visible=False),
            gr.update(visible=True),
            gr.update(value=[])  # Update the State component
        )
    patients = load_patients()
    patient_id = patients.get(selected_patient_name)
    json_files = load_existing_json_files()
    return (
        gr.update(open=False),
        selected_patient_name,
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(value=json_files)  # Update the State component
    )

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

# Create JSON files based on doctor's note and date
def create_json_file(input_text, selected_date):
    global json_files, patient_id, doctor_id
    diagnosis = extract_diagnosis_model(input_text)
    features = extract_features_model(input_text)

    current_time = datetime.now().strftime("%H:%M:%S")
    formatted_date = selected_date.strftime("%Y-%m-%d") if isinstance(selected_date, datetime) else selected_date.split('T')[0]
    data = {
        "doctor_id": doctor_id,
        "patient_id": patient_id,
        "date": f"{formatted_date}T{current_time}",
        "doctor_note": input_text,
        "diagnosis": diagnosis,
        "features": features
    }
    filename = f"doctor_note_{formatted_date.replace('-', '')}_{current_time.replace(':', '')}_{doctor_id}_{patient_id}.json"

    doctor_notes_dir = 'data/doctor_notes/'
    os.makedirs(doctor_notes_dir, exist_ok=True)
    file_path = os.path.join(doctor_notes_dir, filename)

    with open(file_path, "w") as json_file:
        json.dump(data, json_file, indent=2, cls=CustomJSONEncoder)

    json_files.append(file_path)

    return json.dumps(data, indent=2, cls=CustomJSONEncoder) if data else "{}"

def preview_json(selected_file):
    if selected_file:
        full_path = next(
            (f for f in json_files if os.path.basename(f) == selected_file), None
        )
        if full_path:
            with open(full_path, "r") as file:
                content = file.read()
            return content
    return "{}"

def update_file_selector():
    return gr.Dropdown(choices=[os.path.basename(f) for f in json_files])

def consolidate_symptoms():
    global json_files
    global consolidated_symptoms_df
    result, consolidated_symptoms_df = consolidate_symptoms_model(json_files)
    return result, consolidated_symptoms_df

def visualize_symptoms():
    global consolidated_symptoms_df
    figures = visualize_symptoms_model(consolidated_symptoms_df)
    images = []
    for fig in figures:
        # Convert Plotly figure to PIL Image directly
        if hasattr(fig, 'to_image'):
            # Handle Plotly figures
            img_bytes = fig.to_image(format="png")
            img = Image.open(io.BytesIO(img_bytes))
        else:
            # Handle PIL Images (from wordcloud)
            img = fig
        images.append(img)
    return images

def get_latest_json_file():
    doctor_notes_dir = 'data/doctor_notes/'
    json_files = [f for f in os.listdir(doctor_notes_dir) if f.endswith('.json')]
    if not json_files:
        return None
    return max(json_files, key=lambda x: os.path.getctime(os.path.join(doctor_notes_dir, x)))

def extract_symptoms(text):
    symptoms = []
    for symptom_name, symptom_data in text['features']['symptoms'].items():
        symptom = {
            "name": symptom_name,
            "location": symptom_data.get('location', ''),
            "intensity": int(symptom_data['intensity']) if symptom_data['intensity'] != '-1' else 0,
            "is_active": bool(symptom_data.get('is_active', False))
        }
        symptoms.append(symptom)
    return symptoms

def submit_note(input_text, selected_date):
    json_content = create_json_file(input_text, selected_date)
    
    latest_file = get_latest_json_file()
    if latest_file:
        file_path = os.path.join('data/doctor_notes/', latest_file)
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        diagnosis = data.get('diagnosis', {}).get('diagnosis', '')
        diagnosis_reasoning = data.get('diagnosis', {}).get('reasoning', '')
        symptoms = extract_symptoms(data)
        symptom_names = [symptom['name'] for symptom in symptoms]
        
        first_symptom = symptoms[0] if symptoms else {}
        
        return (
            gr.update(open=False),
            diagnosis,
            diagnosis_reasoning,
            gr.update(visible=True),  # Show diagnosis_component
            json_content,
            latest_file,
            gr.update(interactive=False, variant="secondary"),
            gr.update(visible=True),
            gr.update(choices=symptom_names, value=symptom_names[0] if symptom_names else None, visible=True),
            gr.update(value=first_symptom.get('name', '')),
            gr.update(value=first_symptom.get('location', '')),
            gr.update(value=first_symptom.get('intensity', 0)),
            gr.update(value=first_symptom.get('is_active', False)),
            gr.update(visible=True)  # Show symptoms_component
        )
    return (
        gr.update(open=True),
        "",
        "",
        gr.update(visible=False),  # Hide diagnosis_component
        "{}",
        "",
        gr.update(interactive=True, variant="primary"),
        gr.update(visible=False),
        gr.update(choices=[], value=None, visible=False),
        gr.update(value={}, visible=False),
        gr.update(visible=False)  # Hide symptoms_component
    )

def update_symptom(original_name, name, location, intensity, is_active, current_file, selected_file):
    file_to_update = current_file if current_file else selected_file
    if file_to_update:
        file_path = os.path.join('data/doctor_notes/', file_to_update)
        try:
            with open(file_path, 'r+') as file:
                data = json.load(file)
                symptoms = data['features']['symptoms']
                
                new_symptom_data = {
                    'location': str(location),
                    'intensity': str(intensity),
                    'is_active': str(is_active).capitalize()
                }
                
                # Check if the symptom name changed
                if original_name == name:
                    symptoms[name].update(new_symptom_data)
                else:
                    # Remove the old entry and add the new one
                    symptoms[name] = symptoms.pop(original_name)
                    symptoms[name] = new_symptom_data
                
                file.seek(0)
                json.dump(data, file, indent=2)
                file.truncate()
            
            symptom_names = list(data['features']['symptoms'].keys())
            return gr.update(visible=False), json.dumps(data, indent=2), gr.update(choices=symptom_names, value=name), gr.update(visible=True, value="Symptom updated successfully"), gr.update()
        except IOError:
            return gr.update(visible=True, value=f"Update failed: Could not write to file {file_to_update}"), "{}", gr.update(), gr.update(visible=True, value="Update failed: IOError occurred."), gr.update()
        except json.JSONDecodeError:
            return gr.update(visible=True, value=f"Update failed: Invalid JSON in file {file_to_update}"), "{}", gr.update(), gr.update(visible=True, value="Update failed: JSONDecodeError occurred."), gr.update()
    return gr.update(visible=True, value="Update failed: No file selected"), "{}", gr.update(), gr.update(visible=True, value="Update failed: No file selected."), gr.update()

def load_symptom(symptom_name, current_file, selected_file):
    file_to_load = current_file if current_file else selected_file
    if file_to_load:
        file_path = os.path.join('data/doctor_notes/', file_to_load)
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
            symptom_data = data['features']['symptoms'].get(symptom_name, {})
            return (
                symptom_name,
                symptom_data.get('location', ''),
                int(symptom_data.get('intensity', '0')),
                bool(symptom_data.get('is_active', False))
            )
        except IOError:
            pass
        except json.JSONDecodeError:
            pass
    return '', '', 0, False

def reset_interface():
    return (
        None,  # Reset current_file
        "",    # Clear input_text
        gr.update(visible=False),  # Hide diagnosis_component
        gr.update(interactive=True, variant="primary"),  # Enable and make submit button green
        gr.update(visible=False),  # Hide "New doctor note" button
        gr.update(open=True),  # Expand the doctor's note accordion
        gr.update(value=[], visible=False),  # Reset and hide symptoms dropdown
        gr.update(visible=False),  # Hide symptoms group
        gr.update(open=False),  # Close diagnosis accordion
        gr.update(open=False)   # Close symptoms accordion
    )

def update_diagnosis(diagnosis, reasoning, current_file, selected_file):
    file_to_update = current_file if current_file else selected_file
    if file_to_update:
        file_path = os.path.join('data/doctor_notes/', file_to_update)
        try:
            with open(file_path, 'r+') as file:
                data = json.load(file)
                data['diagnosis']['diagnosis'] = diagnosis
                file.seek(0)
                json.dump(data, file, indent=2)
                file.truncate()
            return gr.update(visible=True, value="Diagnosis updated successfully"), json.dumps(data, indent=2), gr.update()  # Show status with success message
        except IOError:
            return gr.update(visible=True, value=f"Update failed: Could not write to file {file_to_update}"), "{}", gr.update()
        except json.JSONDecodeError:
            return gr.update(visible=True, value=f"Update failed: Invalid JSON in file {file_to_update}"), "{}", gr.update()
    return gr.update(visible=True, value="Update failed: No file selected"), "{}", gr.update()  # Show status with error message

def hide_status_after_delay():
    time.sleep(1)  # Wait for 1 second
    return gr.update(visible=False)

def is_dataframe_up_to_date(df, json_files):
    if df is None or df.empty:
        return False
    processed_files = set(df['doctor_note_file'].unique())
    current_files = set(map(os.path.basename, json_files))
    return processed_files == current_files

def on_previous_visits_tab_select():
    global json_files
    return gr.Dropdown(choices=[os.path.basename(f) for f in json_files])

def on_analytics_tab_select():
    global json_files, consolidated_symptoms_df

    # Data Consolidation
    try:
        if not is_dataframe_up_to_date(consolidated_symptoms_df, json_files):
            result, consolidated_symptoms_df = consolidate_symptoms()
        consolidation_json = result
        consolidation_table = consolidated_symptoms_df
    except Exception as e:
        print(f"Error in data consolidation: {str(e)}")
        consolidation_json = f"Error in data consolidation: {str(e)}"
        consolidation_table = None

    # Visualization
    try:
        if consolidated_symptoms_df is None or consolidated_symptoms_df.empty:
            images = []
        else:
            images = visualize_symptoms()
    except Exception as e:
        print(f"Error in visualization: {str(e)}")
        images = []

    return consolidation_json, consolidation_table, images

def update_diagnosis_with_delay(diagnosis, reasoning, current_file, selected_file):
    file_to_update = current_file if current_file else selected_file
    if file_to_update:
        file_path = os.path.join('data/doctor_notes/', file_to_update)
        try:
            with open(file_path, 'r+') as file:
                data = json.load(file)
                data['diagnosis']['diagnosis'] = diagnosis
                file.seek(0)
                json.dump(data, file, indent=2)
                file.truncate()
            status = "Diagnosis updated successfully"
            json_content = json.dumps(data, indent=2)
        except IOError:
            status = f"Update failed: Could not write to file {file_to_update}"
            json_content = "{}"
        except json.JSONDecodeError:
            status = f"Update failed: Invalid JSON in file {file_to_update}"
            json_content = "{}"
    else:
        status = "Update failed: No file selected"
        json_content = "{}"
    
    # Return the results immediately
    yield gr.update(value=status, visible=True), json_content, gr.update()

    # Sleep for 1 second
    time.sleep(1)
    
    # Clear the status message
    yield gr.update(value="", visible=False), json_content, gr.update()

def update_symptom_with_delay(original_name, name, location, intensity, is_active, current_file, selected_file):
    file_to_update = current_file if current_file else selected_file
    if file_to_update:
        file_path = os.path.join('data/doctor_notes/', file_to_update)
        try:
            with open(file_path, 'r+') as file:
                data = json.load(file)
                symptoms = data['features']['symptoms']
                
                new_symptom_data = {
                    'location': str(location),
                    'intensity': str(intensity),
                    'is_active': str(is_active).capitalize()
                }
                
                if original_name == name:
                    symptoms[name].update(new_symptom_data)
                else:
                    symptoms[name] = symptoms.pop(original_name)
                    symptoms[name] = new_symptom_data
                
                file.seek(0)
                json.dump(data, file, indent=2)
                file.truncate()
            
            symptom_names = list(data['features']['symptoms'].keys())
            status = "Symptom updated successfully"
            json_content = json.dumps(data, indent=2)
            new_symptom_value = name
        except IOError:
            status = f"Update failed: Could not write to file {file_to_update}"
            json_content = "{}"
            new_symptom_value = original_name
        except json.JSONDecodeError:
            status = f"Update failed: Invalid JSON in file {file_to_update}"
            json_content = "{}"
            new_symptom_value = original_name
    else:
        status = "Update failed: No file selected"
        json_content = "{}"
        new_symptom_value = original_name
    
    # Return the results immediately
    yield gr.update(), json_content, gr.update(choices=symptom_names, value=new_symptom_value), gr.update(value=status, visible=True), gr.update()
    
    # Sleep for 1 second
    time.sleep(1)
    
    # Clear the status message
    yield gr.update(), json_content, gr.update(), gr.update(value="", visible=False), gr.update()

# Gradio interface
with gr.Blocks() as demo:
    # Login Page
    with gr.Column() as login_page:
        gr.Markdown("# Login")
        username_input = gr.Textbox(label="Username", placeholder="Enter your username")
        password_input = gr.Textbox(label="Password", placeholder="Enter your password", type="password")
        login_button = gr.Button("Login", variant="primary")
        login_message = gr.Textbox(label="Login Status", visible=False)

    # Home Page (hidden initially)
    with gr.Column(visible=False) as home_page:
        welcome_message = gr.Textbox(label="Welcome", interactive=False)
        
        with gr.Row() as patient_selection_row:
            with gr.Column(scale=3):
                with gr.Accordion("Patient Selection", open=True) as patient_picker_accordion:
                    patients = load_patients()
                    patient_choices = ["Pick a patient"] + list(patients.keys())
                    patient_dropdown = gr.Dropdown(
                        label="Select Patient", 
                        choices=patient_choices,
                        value="Pick a patient",
                        interactive=True
                    )
            
            with gr.Column(scale=1):
                patient_display = gr.Textbox(label="Selected Patient", interactive=False)
        
        with gr.Column(visible=False) as ehr_section:
            gr.Markdown("# EHR - Doctor's Note")
            
            current_file = gr.State(None)  # Store the current JSON file name
            
            with gr.Tabs() as tabs:
                with gr.TabItem("Current visit"):
                    date_picker_calendar = Calendar(type="datetime", label="Select date of doctor's note", info="Click the calendar icon to bring up the calendar.")
                    
                    with gr.Accordion("Doctor's Note", open=True) as note_accordion:
                        with gr.Column() as note_component:
                            input_text = gr.Textbox(label="Enter doctor's note", lines=10)
                            submit_btn = gr.Button("Submit", variant="primary")
                            new_note_btn = gr.Button("New doctor note", visible=False)
                    
                    with gr.Accordion("Diagnosis", open=True) as diagnosis_accordion:
                        with gr.Column(visible=False) as diagnosis_component:
                            with gr.Group():
                                with gr.Row():
                                    diagnosis_textbox = gr.Textbox(label="Extracted Diagnosis", interactive=True)
                                with gr.Row():
                                    diagnosis_update_btn = gr.Button("Update Diagnosis")
                            
                            with gr.Accordion("Diagnosis Reasoning", open=False):
                                reasoning_textbox = gr.Textbox(label="Reasoning", interactive=False)
                            
                            diagnosis_update_status = gr.Textbox(label="Diagnosis Update Status", visible=False, interactive=False)
                    
                    with gr.Accordion("Symptoms", open=True) as symptoms_accordion:
                        with gr.Column(visible=False) as symptoms_component:
                            symptom_dropdown = gr.Dropdown(label="Select Symptom", choices=[], interactive=True)
                            with gr.Group():
                                symptom_name = gr.Textbox(label="Symptom Name")
                                symptom_location = gr.Textbox(label="Location")
                                symptom_intensity = gr.Slider(label="Intensity", minimum=0, maximum=10, step=1)
                                symptom_is_active = gr.Checkbox(label="Is Active")
                            symptom_update_btn = gr.Button("Update Symptom")
                            symptom_update_status = gr.Textbox(label="Symptom Update Status", visible=False, interactive=False)
                    
                with gr.TabItem("Previous visits") as previous_visits_tab:
                    file_selector = gr.Dropdown(label="Select file to preview", choices=[], interactive=True)
                    json_preview = gr.JSON(label="JSON Preview")
                    
                with gr.TabItem("Analytics") as analytics_tab:
                    with gr.Accordion("Data Consolidation", open=False):
                        consolidation_preview_json = gr.JSON(label="Consolidation Preview JSON")
                        consolidation_preview_table = gr.Dataframe(label="Consolidation Preview Table")
                    visualization_gallery = gr.Gallery(label="Visualization Gallery")

        patient_dropdown.change(
            fn=update_patient_id,
            inputs=patient_dropdown,
            outputs=[patient_picker_accordion, patient_display, ehr_section, welcome_message, json_files_state]
        )

        file_selector.change(
            fn=preview_json,
            inputs=file_selector,
            outputs=json_preview
        )

        submit_btn.click(
            fn=submit_note,
            inputs=[input_text, date_picker_calendar],
            outputs=[
                note_accordion, diagnosis_textbox, reasoning_textbox, diagnosis_component, 
                json_preview, current_file, submit_btn, new_note_btn, symptom_dropdown,
                symptom_name, symptom_location, symptom_intensity, symptom_is_active,
                symptoms_component
            ]
        ).then(fn=update_file_selector, outputs=file_selector)

        new_note_btn.click(
            fn=reset_interface,
            inputs=[],
            outputs=[
                current_file, input_text, diagnosis_component, submit_btn, new_note_btn, 
                note_accordion, symptom_dropdown,
                gr.Group([symptom_name, symptom_location, symptom_intensity, symptom_is_active]),
                diagnosis_accordion,
                symptoms_accordion
            ]
        )

        diagnosis_update_btn.click(
            fn=update_diagnosis_with_delay,
            inputs=[diagnosis_textbox, reasoning_textbox, current_file, file_selector],
            outputs=[diagnosis_update_status, json_preview, diagnosis_update_status]
        )

        symptom_update_btn.click(
            fn=update_symptom_with_delay,
            inputs=[
                symptom_dropdown,
                symptom_name, symptom_location, symptom_intensity, symptom_is_active,
                current_file, file_selector
            ],
            outputs=[diagnosis_update_status, json_preview, symptom_dropdown, symptom_update_status, symptom_update_status]
        )

        previous_visits_tab.select(
            fn=on_previous_visits_tab_select,
            inputs=[],
            outputs=[file_selector]
        )

        analytics_tab.select(
            fn=on_analytics_tab_select,
            inputs=[],
            outputs=[consolidation_preview_json, consolidation_preview_table, visualization_gallery]
        )

    # Login event
    login_event = login_button.click(
        login, 
        inputs=[username_input, password_input], 
        outputs=[login_page, home_page, login_message, welcome_message]
    )
    username_input.submit(
        login,
        inputs=[username_input, password_input],
        outputs=[login_page, home_page, login_message, welcome_message]
    )
    password_input.submit(
        login,
        inputs=[username_input, password_input],
        outputs=[login_page, home_page, login_message, welcome_message]
    )

    # Symptom dropdown event
    symptom_dropdown.change(
        fn=load_symptom,
        inputs=[symptom_dropdown, current_file, file_selector],
        outputs=[symptom_name, symptom_location, symptom_intensity, symptom_is_active]
    )

demo.launch()
