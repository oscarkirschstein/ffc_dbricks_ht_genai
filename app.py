import gradio as gr
import hashlib
import json
from gradio_calendar import Calendar
import tempfile
import os
import pandas as pd
from datetime import datetime, date
from models.diagnosis import extract_diagnosis as extract_diagnosis_model
from models.features import extract_features as extract_features_model
from models.visualizations import consolidate_symptoms as consolidate_symptoms_model, visualize_symptoms as visualize_symptoms_model
import io
import re
from PIL import Image

# Global variables
json_files = []
current_json_file = None
consolidated_symptoms = pd.DataFrame()
patient_id = None

# Function to load existing JSON files
def load_existing_json_files(patient_id):
    global json_files
    json_files = []
    doctor_notes_dir = 'data/doctor_notes/'
    for filename in os.listdir(doctor_notes_dir):
        if filename.endswith('.json'):
            # Get the patient id from the filename
            # The filename is in the format doctor_note_YYYYMMDD_HHMMSS_patientID_doctorID.json
            match = re.search(r'doctor_note_\d{8}_\d{6}_(\d+)_\d+\.json', filename)
            patient_id_from_filename = match.group(1) if match else None
            if patient_id_from_filename == patient_id:
                json_files.append(os.path.join(doctor_notes_dir, filename))
                
# Function to reset the json_files list
def reset_json_files():
    global json_files
    json_files = []

# Login function to check username and password
def login(username, password):
    # Load user data from JSON file
    with open('data/users/users.json', 'r') as file:
        users = json.load(file)
    for user_id, user_info in users.items():
        if user_info['username'] == username and user_info['password'] == password:
            # Login successful, show home page
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
        reset_json_files()
        return (
            gr.update(open=True),  # Keep patient picker accordion open
            "No patient selected",
            gr.update(visible=False),  # Keep EHR section hidden
            gr.update(visible=True)  # Keep welcome message visible
        )
    patients = load_patients()
    patient_id = patients.get(selected_patient_name)
    # Load existing JSON files for the selected patient
    load_existing_json_files(patient_id)
    return (
        gr.update(open=False),  # Close patient picker accordion
        f"Selected patient: {selected_patient_name}",
        gr.update(visible=True),  # Show EHR section
        gr.update(visible=False)  # Hide welcome message
    )

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

# Create JSON files based on doctor's note and date
def create_json_file(input_text, selected_date):
    global json_files
    diagnosis = extract_diagnosis_model(input_text)
    features = extract_features_model(input_text)

    data = {
        "doctor_note": input_text,
        "diagnosis": diagnosis,
        "features": features,
        "date": selected_date.isoformat() if isinstance(selected_date, datetime) else selected_date
    }
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"doctor_note_{current_time}.json"

    doctor_notes_dir = 'data/doctor_notes/'
    os.makedirs(doctor_notes_dir, exist_ok=True)
    file_path = os.path.join(doctor_notes_dir, filename)

    with open(file_path, "w") as json_file:
        json.dump(data, json_file, indent=2, cls=CustomJSONEncoder)

    json_files.append(file_path)

    return json.dumps(data, indent=2, cls=CustomJSONEncoder) if data else "{}"

# Define additional necessary functions as in the second snippet
def clear_files():
    global json_files
    global consolidated_symptoms
    doctor_notes_dir = 'data/doctor_notes/'
    for file_path in json_files:
        if file_path.startswith(doctor_notes_dir):
            try:
                os.remove(file_path)
            except OSError:
                pass
    json_files = []
    consolidated_symptoms = pd.DataFrame()
    return "{}"

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
    global consolidated_symptoms
    result, consolidated_symptoms = consolidate_symptoms_model(json_files)
    return result, consolidated_symptoms

def visualize_symptoms():
    global consolidated_symptoms
    figures = visualize_symptoms_model(consolidated_symptoms)
    images = []
    for fig in figures:
        img_bytes = fig.to_image(format="png")
        img = Image.open(io.BytesIO(img_bytes))
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
            "duration": symptom_data.get('duration', ''),
            "frequency": symptom_data.get('frequency', ''),
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
            gr.update(value=first_symptom.get('duration', '')),
            gr.update(value=first_symptom.get('frequency', '')),
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

def update_symptom(original_name, name, location, duration, frequency, intensity, is_active, current_file, selected_file):
    file_to_update = current_file if current_file else selected_file
    if file_to_update:
        file_path = os.path.join('data/doctor_notes/', file_to_update)
        try:
            with open(file_path, 'r+') as file:
                data = json.load(file)
                symptoms = data['features']['symptoms']
                
                new_symptom_data = {
                    'location': str(location),
                    'duration': str(duration),
                    'frequency': str(frequency),
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
            return gr.update(visible=False), json.dumps(data, indent=2), gr.update(choices=symptom_names, value=name), gr.update(visible=True, value="Symptom updated successfully.")
        except IOError:
            return gr.update(visible=True, value=f"Update failed: Could not write to file {file_to_update}"), "{}", gr.update(), gr.update(visible=True, value="Update failed: IOError occurred.")
        except json.JSONDecodeError:
            return gr.update(visible=True, value=f"Update failed: Invalid JSON in file {file_to_update}"), "{}", gr.update(), gr.update(visible=True, value="Update failed: JSONDecodeError occurred.")
    return gr.update(visible=True, value="Update failed: No file selected"), "{}", gr.update(), gr.update(visible=True, value="Update failed: No file selected.")

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
                symptom_data.get('duration', ''),
                symptom_data.get('frequency', ''),
                int(symptom_data.get('intensity', '0')),
                bool(symptom_data.get('is_active', False))
            )
        except IOError:
            pass
        except json.JSONDecodeError:
            pass
    return '', '', '', '', 0, False

def reset_interface():
    return (
        None,  # Reset current_file
        "",    # Clear input_text
        gr.update(visible=False),  # Hide diagnosis_component
        gr.update(interactive=True, variant="primary"),  # Enable and make submit button green
        gr.update(visible=False),  # Hide "New doctor note" button
        gr.update(open=True),  # Expand the doctor's note accordion
        gr.update(value=[], visible=False)  # Reset and hide symptoms
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
            return gr.update(visible=False), json.dumps(data, indent=2)  # Hide status, update JSON preview
        except IOError:
            return gr.update(visible=True, value=f"Update failed: Could not write to file {file_to_update}"), "{}"
        except json.JSONDecodeError:
            return gr.update(visible=True, value=f"Update failed: Invalid JSON in file {file_to_update}"), "{}"
    return gr.update(visible=True, value="Update failed: No file selected"), "{}"  # Show status with error message

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
        
        with gr.Accordion("Patient Selection", open=True) as patient_picker_accordion:
            # Add patient selection dropdown
            patients = load_patients()
            patient_choices = ["Pick a patient"] + list(patients.keys())
            patient_dropdown = gr.Dropdown(
                label="Select Patient", 
                choices=patient_choices,
                value="Pick a patient",
                interactive=True
            )
        
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
                            
                            update_status = gr.Textbox(label="Update Status", visible=False, interactive=False)
                    
                    with gr.Accordion("Symptoms", open=True) as symptoms_accordion:
                        with gr.Column(visible=False) as symptoms_component:
                            symptom_dropdown = gr.Dropdown(label="Select Symptom", choices=[], interactive=True)
                            with gr.Group():
                                symptom_name = gr.Textbox(label="Symptom Name")
                                symptom_location = gr.Textbox(label="Location")
                                symptom_duration = gr.Textbox(label="Duration")
                                symptom_frequency = gr.Textbox(label="Frequency")
                                symptom_intensity = gr.Slider(label="Intensity", minimum=0, maximum=10, step=1)
                                symptom_is_active = gr.Checkbox(label="Is Active")
                            symptom_update_btn = gr.Button("Update Symptom")
                    
                with gr.TabItem("Previous visits"):
                    file_selector = gr.Dropdown(label="Select file to preview", choices=[], interactive=True)
                    json_preview = gr.JSON(label="JSON Preview")
                    consolidate_btn = gr.Button("Consolidate")
                    consolidation_preview_json = gr.JSON(label="Consolidation Preview JSON")
                    consolidation_preview_table = gr.Dataframe(label="Consolidation Preview Table")
                    visualize_btn = gr.Button("Visualize")
                    visualization_gallery = gr.Gallery(label="Visualization Gallery")
                    clear_btn = gr.Button("Clear All")

        # Wire up patient selection
        patient_dropdown.change(
            fn=update_patient_id,
            inputs=patient_dropdown,
            outputs=[patient_picker_accordion, patient_display, ehr_section, welcome_message]
        )

        # Wire up file selector
        file_selector.change(
            fn=preview_json,
            inputs=file_selector,
            outputs=json_preview
        )

        # Wire up button actions
        submit_btn.click(
            fn=submit_note,
            inputs=[input_text, date_picker_calendar],
            outputs=[
                note_accordion, diagnosis_textbox, reasoning_textbox, diagnosis_component, 
                json_preview, current_file, submit_btn, new_note_btn, symptom_dropdown,
                symptom_name, symptom_location, symptom_duration, symptom_frequency, 
                symptom_intensity, symptom_is_active,
                symptoms_component
            ]
        ).then(fn=update_file_selector, outputs=file_selector)

        new_note_btn.click(
            fn=reset_interface,
            inputs=[],
            outputs=[current_file, input_text, diagnosis_component, submit_btn, new_note_btn, note_accordion, symptom_dropdown,
                    gr.Group([symptom_name, symptom_location, symptom_duration, symptom_frequency, symptom_intensity, symptom_is_active])]
        )

        diagnosis_update_btn.click(
            fn=update_diagnosis,
            inputs=[diagnosis_textbox, reasoning_textbox, current_file, file_selector],
            outputs=[update_status, json_preview]
        )

        # Wire up symptom update button
        symptom_update_btn.click(
            fn=update_symptom,
            inputs=[
                symptom_dropdown,  # Pass the original name from the dropdown
                symptom_name, symptom_location, symptom_duration, symptom_frequency, symptom_intensity, symptom_is_active,
                current_file, file_selector
            ],
            outputs=[update_status, json_preview, symptom_dropdown, update_status]
        )

        clear_btn.click(
            fn=clear_files,
            inputs=None,
            outputs=json_preview
        ).then(fn=update_file_selector, outputs=file_selector)

        demo.load(fn=clear_files, outputs=json_preview).then(
            fn=update_file_selector, outputs=file_selector
        )

        consolidate_btn.click(fn=consolidate_symptoms, inputs=None, outputs=[consolidation_preview_json, consolidation_preview_table])
        visualize_btn.click(fn=visualize_symptoms, inputs=None, outputs=visualization_gallery)

    # Wire up the login button click and Enter key press
    login_event = login_button.click(
        login, 
        inputs=[username_input, password_input], 
        outputs=[login_page, home_page, login_message, welcome_message]
    )
    
    # Add Enter key functionality to both username and password inputs
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

    # Wire up symptom dropdown
    symptom_dropdown.change(
        fn=load_symptom,
        inputs=[symptom_dropdown, current_file, file_selector],
        outputs=[symptom_name, symptom_location, symptom_duration, symptom_frequency, symptom_intensity, symptom_is_active]
    )

demo.launch()
