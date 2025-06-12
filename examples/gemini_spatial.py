import os
from google import genai
from IPython.display import display
from PIL import Image, ImageColor, ImageDraw, ImageFont
from google.genai.types import GenerateContentConfig, Part, SafetySetting
from pydantic import BaseModel
import requests


PROJECT_ID = "[your-project-id]"  # @param {type: "string", placeholder: "[your-project-id]", isTemplate: true}
if not PROJECT_ID or PROJECT_ID == "[your-project-id]":
    PROJECT_ID = str(os.environ.get("GOOGLE_CLOUD_PROJECT"))

LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")



client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

MODEL_ID = "gemini-2.0-flash-001"  

class BoundingBox(BaseModel):
    box_2d: list[int]
    label: str


config = GenerateContentConfig(
    system_instruction="""Return bounding boxes as an array with labels. Never return masks. Limit to 25 objects.
    If an object is present multiple times, give each object a unique label according to its distinct characteristics (colors, size, position, etc..).""",
    temperature=0.5,
    safety_settings=[
        SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold="BLOCK_ONLY_HIGH",
        ),
    ],
    response_mime_type="application/json",
    response_schema=list[BoundingBox],
)

def plot_bounding_boxes(image_uri: str, bounding_boxes: list[BoundingBox]) -> None:
    """
    Plots bounding boxes on an image with markers for each a name, using PIL, normalized coordinates, and different colors.
    Args:
        img_path: The path to the image file.
        bounding_boxes: A list of bounding boxes containing the name of the object
        and their positions in normalized [y1 x1 y2 x2] format.
    """

    # Load the image
    with Image.open(requests.get(image_uri, stream=True, timeout=10).raw) as im:
        width, height = im.size
        # Create a drawing object
        draw = ImageDraw.Draw(im)
        colors = list(ImageColor.colormap.keys())

        # Load a font
        font = ImageFont.load_default(size=int(min(width, height) / 100))

        # Iterate over the bounding boxes
        for i, bbox in enumerate(bounding_boxes):
            # Convert normalized coordinates to absolute coordinates
            y1, x1, y2, x2 = bbox.box_2d
            abs_y1 = int(y1 / 1000 * height)
            abs_x1 = int(x1 / 1000 * width)
            abs_y2 = int(y2 / 1000 * height)
            abs_x2 = int(x2 / 1000 * width)

            # Select a color from the list
            color = colors[i % len(colors)]

            # Draw the bounding box
            draw.rectangle(((abs_x1, abs_y1), (abs_x2, abs_y2)), outline=color, width=4)
            # Draw the text
            if bbox.label:
                draw.text((abs_x1 + 8, abs_y1 + 6), bbox.label, fill=color, font=font)

        display(im)

def main():
    print("In main")

if __name__ == "__main__":
    main()