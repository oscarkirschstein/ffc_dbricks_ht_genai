import gradio as gr
import json
import tempfile
import os
from datetime import datetime
from models.features import extract_features
from models.report_generator import generate_report

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
    choices = [os.path.basename(f) for f in json_files]
    return [
        gr.Dropdown(choices=choices),  # For the first tab
        gr.Dropdown(choices=choices),  # For the report tab
    ]


if __name__ == "__main__":
    with gr.Blocks() as demo:
        with gr.Tab("Doctor's Note"):
            gr.Markdown("# Doctor's Note to JSON")
            gr.Markdown(
                "Enter a doctor's note to create a JSON file. Each submission adds a new file."
            )

            input_text = gr.Textbox(
                label="Enter doctor's note",
            )

            output_files = gr.File(label="JSON Output", file_count="multiple")
            file_selector = gr.Dropdown(
                label="Select file to preview", choices=[], interactive=True
            )
            json_preview = gr.JSON(label="JSON Preview")

            submit_btn = gr.Button("Submit")
            submit_btn.click(
                fn=create_json_file,
                inputs=input_text,
                outputs=[output_files, json_preview],
            ).then(fn=update_dropdown, outputs=file_selector)

            input_text.submit(
                fn=create_json_file,
                inputs=input_text,
                outputs=[output_files, json_preview],
            ).then(fn=update_dropdown, outputs=file_selector)

            file_selector.change(
                fn=preview_json, inputs=file_selector, outputs=json_preview
            )

            clear_btn = gr.Button("Clear All")
            clear_btn.click(
                fn=clear_files, inputs=None, outputs=[output_files, json_preview]
            ).then(fn=update_dropdown, outputs=file_selector)

        with gr.Tab("Patient Report"):
            gr.Markdown("# Patient Health Report")
            gr.Markdown(
                "View a visual report of the patient's symptoms based on the latest doctor's note."
            )

            patient_id = gr.Number(
                label="Patient ID",
                value=1,
                precision=0,
            )

            # Add file selector for the report tab
            report_file_selector = gr.Dropdown(
                label="Select note to generate report from",
                choices=[],
                interactive=True,
            )

            # Add plotly figure output
            report_plot = gr.Plot(label="Symptom Timeline")

            generate_btn = gr.Button("Generate Report")

            def generate_report_from_file(selected_file):
                if not selected_file:
                    return None

                full_path = next(
                    (f for f in json_files if os.path.basename(f) == selected_file),
                    None,
                )
                if full_path:
                    with open(full_path, "r") as file:
                        features_data = json.load(file)
                    return generate_report(
                        1, features_data
                    )  # Patient ID hardcoded for now
                return None

            generate_btn.click(
                fn=generate_report_from_file,
                inputs=[report_file_selector],
                outputs=[report_plot],
            )

            # Update both file selectors when new files are added
            submit_btn.click(
                fn=create_json_file,
                inputs=input_text,
                outputs=[output_files, json_preview],
            ).then(
                fn=update_dropdown,
                outputs=[file_selector, report_file_selector],  # Update both dropdowns
            )

        demo.load(fn=clear_files, outputs=[output_files, json_preview]).then(
            fn=update_dropdown,
            outputs=[file_selector, report_file_selector],  # Update both dropdowns
        )

    demo.launch()
