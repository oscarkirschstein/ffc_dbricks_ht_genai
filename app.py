import gradio as gr
from gradio_calendar import Calendar
import json
import tempfile
import os
import pandas as pd
from datetime import datetime, date
from models.pathology import extract_pathology as extract_pathology_model
from models.features import extract_features as extract_features_model
from models.visualizations import consolidate_symptoms as consolidate_symptoms_model, visualize_symptoms as visualize_symptoms_model
import io
from PIL import Image

# List to store the paths of created JSON files
json_files = []
# Dataframe to store the consolidated symptoms
consolidated_symptoms = pd.DataFrame()

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def create_json_file(input_text, selected_date):
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

    # TODO: Using temporary storage for the moment, to be replaced with a database
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, "w") as json_file:
        json.dump(data, json_file, indent=2, cls=CustomJSONEncoder)

    json_files.append(file_path)

    # Return the file paths and the JSON content as a string
    return json.dumps(data, indent=2, cls=CustomJSONEncoder) if data else "{}"


def clear_files():
    global json_files
    global consolidated_symptoms
    for file_path in json_files:
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
    return "{}"  # Return empty JSON if no file is selected


def update_dropdown():
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


if __name__ == "__main__":
    with gr.Blocks() as demo:
        gr.Markdown("# EHR - Doctor's Note")
        gr.Markdown(
            "Enter a doctor's note to create a JSON file. Each submission adds a new file."
        )

        # 1. Date picker first
        date_picker_calendar = Calendar(type="datetime", label="Select date of doctor's note", info="Click the calendar icon to bring up the calendar.")

        # 2. Doctor's note textbox
        input_text = gr.Textbox(
            label="Enter doctor's note",
        )
        
        # 3. Submit button
        submit_btn = gr.Button("Submit")

        # 4. Dropdown to select file for preview
        file_selector = gr.Dropdown(
            label="Select file to preview", choices=[], interactive=True
        )

        # 5. JSON preview
        json_preview = gr.JSON(label="JSON Preview")

        # 6. Consolidate button
        consolidate_btn = gr.Button("Consolidate")

        # 7. Consolidation Preview JSON
        consolidation_preview_json = gr.JSON(label="Consolidation Preview JSON")

        # 8. Consolidation Preview Table
        consolidation_preview_table = gr.Dataframe(label="Consolidation Preview Table")

        # 9. Visualize button
        visualize_btn = gr.Button("Visualize")

        # 10. Visualization Gallery
        visualization_gallery = gr.Gallery(label="Visualization Gallery")

        # 11. Clear All button
        clear_btn = gr.Button("Clear All")

        # Wire up button actions
        submit_btn.click(
            fn=create_json_file, inputs=[input_text, date_picker_calendar], outputs=json_preview
        ).then(fn=update_dropdown, outputs=file_selector)

        input_text.submit(
            fn=create_json_file, inputs=[input_text, date_picker_calendar], outputs=json_preview
        ).then(fn=update_dropdown, outputs=file_selector)

        file_selector.change(
            fn=preview_json, inputs=file_selector, outputs=json_preview
        )

        clear_btn.click(
            fn=clear_files, inputs=None, outputs=json_preview
        ).then(fn=update_dropdown, outputs=file_selector)

        demo.load(fn=clear_files, outputs=json_preview).then(
            fn=update_dropdown, outputs=file_selector
        )
        
        consolidate_btn.click(fn=consolidate_symptoms, inputs=None, outputs=[consolidation_preview_json, consolidation_preview_table])
    
        visualize_btn.click(fn=visualize_symptoms, inputs=None, outputs=visualization_gallery)

    demo.launch()
