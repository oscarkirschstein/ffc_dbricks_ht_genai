import gradio as gr
import hashlib
import json
from gradio_calendar import Calendar
import tempfile
import os
import pandas as pd
from datetime import datetime, date
from models.pathology import extract_pathology as extract_pathology_model
from models.features import extract_features as extract_features_model
from models.visualizations import consolidate_symptoms as consolidate_symptoms_model, visualize_symptoms as visualize_symptoms_model
import io
import re
from PIL import Image

# Global variables
json_files = []
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
    pathology = extract_pathology_model(input_text)
    features = extract_features_model(input_text)

    data = {
        "doctor_note": input_text,
        "pathology": pathology,
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

# Gradio interface
with gr.Blocks() as demo:
    # Login Page
    with gr.Column() as login_page:
        gr.Markdown("# Login")
        username_input = gr.Textbox(label="Username", placeholder="Enter your username")
        password_input = gr.Textbox(label="Password", placeholder="Enter your password", type="password")
        login_button = gr.Button("Login")
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
            
            with gr.Tabs() as tabs:
                with gr.TabItem("Current visit"):
                    date_picker_calendar = Calendar(type="datetime", label="Select date of doctor's note", info="Click the calendar icon to bring up the calendar.")
                    input_text = gr.Textbox(label="Enter doctor's note")
                    submit_btn = gr.Button("Submit")

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
            fn=create_json_file,
            inputs=[input_text, date_picker_calendar],
            outputs=json_preview
        ).then(fn=update_file_selector, outputs=file_selector)

        input_text.submit(
            fn=create_json_file,
            inputs=[input_text, date_picker_calendar],
            outputs=json_preview
        ).then(fn=update_file_selector, outputs=file_selector)

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

demo.launch()
