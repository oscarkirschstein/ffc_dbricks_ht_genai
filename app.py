import gradio as gr
import json
import tempfile
import os
from datetime import datetime
from models.features import extract_features

# List to store the paths of created JSON files
json_files = []


def create_json_file(input_text):
    # pathology = extract_pathologies(input_text)
    features = extract_features(input_text)

    data = {
        # "doctor_note": input_text,
        # "pathology": pathology,
        "features": features,
    }
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"doctor_note_{current_time}.json"

    # TODO: Using temporary storage for the moment, to be replaced with a database
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, filename)

    with open(file_path, "w") as json_file:
        json.dump(data, json_file, indent=2)

    json_files.append(file_path)

    # Return the file paths and the JSON content as a string
    return json_files, json.dumps(data, indent=2) if data else "{}"


def clear_files():
    global json_files
    for file_path in json_files:
        try:
            os.remove(file_path)
        except OSError:
            pass
    json_files = []
    return [], "{}"


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


def consolidate_features(doctor_note_files):
    return consolidate_features(doctor_note_files)


if __name__ == "__main__":
    with gr.Blocks() as demo:
        gr.Markdown("# Doctor's Note to JSON")
        gr.Markdown(
            "Enter a doctor's note to create a JSON file. Each submission adds a new file."
        )

        input_text = gr.Textbox(
            label="Enter doctor's note",
        )

        output_files = gr.File(
            label="JSON Output", file_count="multiple"
        )  # List JSON files generated up until now
        file_selector = gr.Dropdown(
            label="Select file to preview", choices=[], interactive=True
        )
        json_preview = gr.JSON(label="JSON Preview")

        submit_btn = gr.Button("Submit")
        submit_btn.click(
            fn=create_json_file, inputs=input_text, outputs=[output_files, json_preview]
        ).then(fn=update_dropdown, outputs=file_selector)
        # Enable Enter key press to submit
        input_text.submit(
            fn=create_json_file, inputs=input_text, outputs=[output_files, json_preview]
        ).then(fn=update_dropdown, outputs=file_selector)

        file_selector.change(
            fn=preview_json, inputs=file_selector, outputs=json_preview
        )

        clear_btn = gr.Button("Clear All")
        clear_btn.click(
            fn=clear_files, inputs=None, outputs=[output_files, json_preview]
        ).then(fn=update_dropdown, outputs=file_selector)

        demo.load(fn=clear_files, outputs=[output_files, json_preview]).then(
            fn=update_dropdown, outputs=file_selector
        )
    
        visualize_btn = gr.Button("Visualize")
        visualize_btn.click(fn=consolidate_features, inputs=output_files, outputs=json_preview)

    if __name__ == "__main__":
        demo.launch()
