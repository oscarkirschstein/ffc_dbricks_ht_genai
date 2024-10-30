import gradio as gr
import json
import tempfile
import os
from datetime import datetime
from models.features import extract_features
from models.report_generator import generate_report, generate_pdf_report

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


def display_report(patient_id):
    report = generate_report(patient_id)

    markdown = f"""# 🏥 Patient Health Analysis Report

## Patient ID: {patient_id}
*Analysis Period: {report['time_period']}*

---

## 📊 Key Statistics
| Metric | Value |
|--------|--------|
| Total Measurements | {report['data_quality']['total_measurements']} |
| Symptoms Tracked | {report['data_quality']['symptoms_tracked']} |
| Significant Changes | {report['data_quality']['significant_changes']} |

---

## 📈 Detailed Analysis
{report['analysis']}

---

## 💡 Clinical Summary & Recommendations
### Key Findings
{report['summary']}

---

## ⚠️ Important Notes
- This report was generated using AI assistance
- All findings should be validated by a healthcare professional
- Data quality metrics are provided for transparency
- Symptom intensity ranges from 0 (none) to 1 (severe)

---

<div style='text-align: center; font-size: 0.8em; color: gray; padding: 20px;'>
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Report Version: 1.0
</div>
"""

    # Generate PDF file with plot
    pdf_path = generate_pdf_report(markdown, patient_id, report["plot"])

    # Return values and update download button state
    return (
        report["plot"],  # Plot
        markdown,  # Markdown report
        gr.update(
            value=pdf_path, interactive=True
        ),  # Update download button with path and enable it
    )


def download_report(pdf_path: str) -> str:
    """Return the PDF file path when download button is clicked"""
    return pdf_path


if __name__ == "__main__":
    with gr.Blocks(theme=gr.themes.Soft()) as demo:
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
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown(
                        """
                        # 🏥 Patient Health Report
                        Generate a comprehensive health analysis report based on patient data.
                        """
                    )
                    patient_id = gr.Number(
                        label="Patient ID",
                        value=42,
                        precision=0,
                    )
                    generate_btn = gr.Button(
                        "Generate Report",
                        variant="primary",
                        scale=1,
                        min_width=100,
                        size="lg",
                    )

            with gr.Row():
                with gr.Column(scale=2):
                    report_plot = gr.Plot(label="Symptom Timeline")

            with gr.Row():
                with gr.Column():
                    report_markdown = gr.Markdown()

            with gr.Row():
                with gr.Column(scale=1, min_width=200):
                    # Use DownloadButton with initial state
                    download_btn = gr.DownloadButton(
                        "📥 Download PDF Report",
                        visible=True,
                        interactive=False,  # Initially disabled
                        variant="secondary",
                        scale=1,
                        min_width=200,
                        value=None,  # Initial value is None
                    )

            # Generate report and update download button
            generate_btn.click(
                fn=display_report,
                inputs=[patient_id],
                outputs=[
                    report_plot,
                    report_markdown,
                    download_btn,  # Connect directly to download button
                ],
            )

        demo.load(fn=clear_files, outputs=[output_files, json_preview]).then(
            fn=update_dropdown, outputs=file_selector
        )

    # Launch with a custom title and description
    demo.launch(
        share=False,
        server_name="0.0.0.0",
        server_port=7860,
        show_api=False,
        favicon_path=None,
    )
