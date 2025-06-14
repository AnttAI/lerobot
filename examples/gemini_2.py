import os
from google import genai
from google.genai import types
from PIL import Image, ImageDraw, ImageFont, ImageColor # Added ImageDraw, ImageFont, ImageColor
import json
import io # Needed for Image.open(io.BytesIO(...))

# --- CONFIGURATION (can be overridden or passed as arguments) ---
# IMPORTANT: In a production environment, do NOT hardcode API_KEY.
# Use environment variables or a secret management system.
API_KEY = "AIzaSyCwywe5G2q1SGPAolmxUc8CMdZNxbecLzM" # Your existing API key from gemini3.py
MODEL_NAME = "gemini-2.0-flash" # The model to use for analysis
DEFAULT_BBOX_PROMPT = """
    - Return bounding boxes as a JSON array with labels.
    - Never return masks or code fencing.
    - If an object is present multiple times, name them according to their unique numbers.
    - Ignore all background objects.
    """

# Initialize the Gemini client once
client = genai.Client(api_key=API_KEY)

# Define safety settings
safety_settings = [
    types.SafetySetting(
        category="HARM_CATEGORY_DANGEROUS_CONTENT",
        threshold="BLOCK_ONLY_HIGH",
    ),
]


# --- Core Function to Analyze Image with Gemini ---
def analyze_image_with_gemini(image_png_bytes: bytes, user_prompt: str, system_instruction: str = DEFAULT_BBOX_PROMPT) -> str:
    """
    Analyzes a PNG image using the Gemini API and returns the text response.

    Args:
        image_png_bytes (bytes): The image data in PNG format.
        user_prompt (str): identify the plate.
        system_instruction (str, optional): An optional system instruction for the model.
                                            Defaults to DEFAULT_BBOX_PROMPT for bounding box detection.

    Returns:
        str: The raw text response from the Gemini model. This might be JSON if prompted for structured output.
    """
    try:
        #image = "/home/jony/Downloads/frame_00000.png"
        #im = Image.open(image)
        #im.thumbnail([640,640], Image.Resampling.LANCZOS)
        # Open the PNG bytes as a PIL Image object
        # The Gemini API `contents` argument can directly take a PIL Image object.
        pil_image = Image.open(io.BytesIO(image_png_bytes))
        pil_image.thumbnail([640,640], Image.Resampling.LANCZOS)

        # Prepare the contents for the Gemini API call
        contents = [
            user_prompt,
            pil_image # Pass the PIL Image object
        ]

        # Call the Gemini API
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.5, # Temperature from original gemini3.py
                safety_settings=safety_settings,
            )
        )
        print(f"DEBUG: Gemini API response status: {pil_image,response.text}")
        return response.text
    except Exception as e:
        print(f"ERROR: Failed to call Gemini API: {e}")
        return f"ERROR: Gemini API call failed: {e}"

# --- Helper to parse JSON output from Gemini response ---
def parse_json(json_output: str):
    # Parsing out the markdown fencing if present (e.g., "```json\n...\n```")
    lines = json_output.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == "```json": # Use strip() for robust matching
            json_output = "\n".join(lines[i+1:])  # Remove everything before "```json"
            json_output = json_output.split("```")[0]  # Remove everything after the closing "```"
            break  # Exit the loop once "```json" is found
    return json_output.strip() # Ensure no leading/trailing whitespace


# --- Plotting Function: Draws bounding boxes on a PIL Image ---
def plot_bounding_boxes(im: Image.Image, bounding_boxes_json_str: str, output_path: str = None):
    """
    Draws bounding boxes and labels on a PIL Image based on Gemini's JSON response.

    Args:
        im (Image.Image): The PIL Image object to draw on.
        bounding_boxes_json_str (str): The raw JSON string response from Gemini,
                                       potentially including markdown fencing.
        output_path (str, optional): If provided, the image with bounding boxes will be saved
                                     to this path (e.g., "output.png"). If None, img.show() is called.
    """
    img = im.copy() # Work on a copy to avoid modifying the original image
    width, height = img.size
    draw = ImageDraw.Draw(img)

    # Colors for drawing bounding boxes
    colors = [
        'red', 'green', 'blue', 'yellow', 'orange', 'pink', 'purple', 'brown',
        'gray', 'beige', 'turquoise', 'cyan', 'magenta', 'lime', 'navy',
        'maroon', 'teal', 'olive', 'coral', 'lavender', 'violet', 'gold', 'silver'
    ] + [colorname for (colorname, colorcode) in ImageColor.colormap.items()] # Add more standard colors

    # Load font for labels
    try:
        font = ImageFont.truetype("arial.ttf", size=14)
    except IOError:
        font = ImageFont.load_default() # Fallback if 'arial.ttf' is not found on the system
        print("WARNING: 'arial.ttf' not found, using default font for bounding boxes.")

    # Parse the JSON string from Gemini's response
    try:
        # Use parse_json to remove markdown fencing if it exists
        clean_json_str = parse_json(bounding_boxes_json_str)
        bounding_boxes_list = json.loads(clean_json_str)
    except json.JSONDecodeError as e:
        print(f"ERROR: Could not parse bounding box JSON: {e}")
        print(f"Received raw JSON string: {bounding_boxes_json_str[:500]}...")
        return # Exit if parsing fails

    # List to hold the new absolute boxes (for optional printing)
    absolute_boxes = []

    # Loop through each detected bounding box
    for i, bounding_box in enumerate(bounding_boxes_list):
        color = colors[i % len(colors)] # Cycle through colors

        # Ensure 'box_2d' exists and has 4 elements
        if "box_2d" not in bounding_box or len(bounding_box["box_2d"]) != 4:
            print(f"WARNING: Skipping malformed bounding box: {bounding_box}. Expected 'box_2d' with 4 coordinates.")
            continue

        # Convert normalized coordinates (0-1000) to absolute pixels
        # Gemini's coordinates are often 0-1000, as in your original gemini3.py
        abs_y1 = int(bounding_box["box_2d"][0] / 1000 * height)
        abs_x1 = int(bounding_box["box_2d"][1] / 1000 * width)
        abs_y2 = int(bounding_box["box_2d"][2] / 1000 * height)
        abs_x2 = int(bounding_box["box_2d"][3] / 1000 * width)

        # Ensure correct box orientation (min coordinate first)
        if abs_x1 > abs_x2:
            abs_x1, abs_x2 = abs_x2, abs_x1
        if abs_y1 > abs_y2:
            abs_y1, abs_y2 = abs_y2, abs_y1

        # Draw the box
        draw.rectangle(((abs_x1, abs_y1), (abs_x2, abs_y2)), outline=color, width=4)

        # Draw the label if present, otherwise use a generic object_X label
        label = bounding_box.get("label", f"object_{i+1}")
        # Position the text slightly inside the top-left corner
        draw.text((abs_x1 + 8, abs_y1 + 6), label, fill=color, font=font)

        # Save the absolute box for optional printing/logging
        absolute_boxes.append({
            "label": label,
            "abs_box": [abs_x1, abs_y1, abs_x2, abs_y2]
        
        })

    # Display or save the image
    if output_path:
        try:
            img.save(output_path)
            print(f"DEBUG: Image with bounding boxes saved to {output_path}")
        except IOError as e:
            print(f"ERROR: Could not save image with bounding boxes to {output_path}: {e}")
    else:
        # img.show() typically opens a new window, which might not work in headless environments.
        print("INFO: Displaying image with bounding boxes. This might require a display server.")
        img.show()

    # Print the absolute bounding boxes as JSON for programmatic use/logging
    print("INFO: Absolute Bounding Boxes (JSON):")
    print(json.dumps(absolute_boxes))    


#analyze_image_with_gemini("/home/jony/Downloads/frame_00000.png", "What do you see?") # Example usage
