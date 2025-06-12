import logging
import time
import io
from PIL import Image
import numpy as np
import torch
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
from lerobot.common.datasets.utils import build_dataset_frame, hw_to_dataset_features
from lerobot.common.teleoperators.config import TeleoperatorConfig
from lerobot.common.utils.control_utils import predict_action
from dataclasses import dataclass, asdict
from pprint import pformat
from pathlib import Path
from lerobot.common.utils.utils import get_safe_torch_device
from lerobot.common.robots.so101_follower import SO101Follower, SO101FollowerConfig
from lerobot.common.teleoperators.teleoperator import Teleoperator
from lerobot.common.teleoperators.keyboard.teleop_keyboard import KeyboardTeleop, KeyboardTeleopConfig
from lerobot.common.policies.factory import make_policy
from lerobot.common.policies.pretrained import PreTrainedPolicy
from lerobot.common.datasets.utils import build_dataset_frame, hw_to_dataset_features
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset  
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset, LeRobotDatasetMetadata
from lerobot.configs.policies import PreTrainedConfig
from lerobot.common.cameras.opencv.configuration_opencv import OpenCVCameraConfig
from lerobot.common.utils.utils import (
    get_safe_torch_device,
    init_logging,
    log_say,
)
#NEW IMPORTS FOR IMAGE CONVERSION AND GEMINI API CALL
import cv2
import numpy as np
import io # Import io for handling bytes in memory
import json # For parsing Gemini's JSON response if needed
from PIL import Image # NEW: Import PIL.Image to convert NumPy array to PIL Image for plotting
from gemini_2 import analyze_image_with_gemini, parse_json, plot_bounding_boxes 



def image_obs_to_png_bytes(image_obs):
    """
    Convert an image observation (numpy array, torch tensor, or PIL Image) to PNG bytes.
    """
    # Convert to numpy if needed
    if isinstance(image_obs, torch.Tensor):
        image_obs = image_obs.cpu().numpy()
    if isinstance(image_obs, np.ndarray):
        # Ensure uint8 and channel order
        if image_obs.dtype != np.uint8:
            image_obs = (255 * np.clip(image_obs, 0, 1)).astype(np.uint8)
        if image_obs.shape[0] in [1, 3] and image_obs.ndim == 3:
            # Convert CHW to HWC
            image_obs = np.transpose(image_obs, (1, 2, 0))
        img = Image.fromarray(image_obs)
    elif isinstance(image_obs, Image.Image):
        img = image_obs
    else:
        raise ValueError("Unsupported image type")

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.getvalue()



camera_config = {
    "head": OpenCVCameraConfig(index_or_path='/dev/video2', width=640, height=480, fps=30)
}

robot_config = SO101FollowerConfig(
    port="/dev/ttyACM0",
    id="blue_follower_arm",
    cameras=camera_config
)

teleop_keyboard_config = KeyboardTeleopConfig(
    id="my_laptop_keyboard",
)

single_task = "pick the wodden block"

policy_path = "/home/jony/Downloads/last/pretrained_model/"
policy_config = PreTrainedConfig.from_pretrained(policy_path)
print("Policy config:", pformat(asdict(policy_config)))

ds_meta = LeRobotDatasetMetadata("anttai/act_so101_test52", root=Path("/home/jony/Downloads/lerobot/anttai/act_so101_test52"))
print("Dataset metadata:", ds_meta)
policy = make_policy(policy_config, ds_meta)
policy.reset()
policy = None 
robot = SO101Follower(robot_config)
telep_keyboard = KeyboardTeleop(teleop_keyboard_config)
robot.connect()
telep_keyboard.connect()
i =0

action_features = hw_to_dataset_features(robot.action_features, "action", True)
obs_features = hw_to_dataset_features(robot.observation_features, "observation", True)
dataset_features = {**action_features, **obs_features}

while i < 1:
    observation = robot.get_observation()

    print("Observation:", observation)

    for key in observation:
        observation[key] = 0

    home = {'shoulder_pan.pos': 100, 
            'shoulder_lift.pos': -99, 
            'elbow_flex.pos': 99, 
            'wrist_flex.pos': 94, 
            'wrist_roll.pos': 0.3, 
            'gripper.pos': 0.1}

    #robot.send_action(observation)
    time.sleep(5)
    #robot.send_action(home)

    observation = robot.get_observation()
    print("Observation last:", observation)

    if 'head' in observation:
        image_np_array = np.frombuffer(observation['head'], dtype=np.uint8)  
    
        
        try:

            png_bytes = image_obs_to_png_bytes(observation["head"])  # or any image observation
            img = Image.open(io.BytesIO(png_bytes))
            #img.show()

            # --- CALL GEMINI API HERE ---
            # Define your prompt for Gemini
            gemini_prompt = "Identify and return bounding boxes for all objects in this image. Provide a summary."
            # The DEFAULT_BBOX_PROMPT in gemini3_module already provides the system instruction
            # to return JSON with bounding boxes.





            print(f"INFO: Calling Gemini API with prompt: '{gemini_prompt}'...")
            gemini_response_text = analyze_image_with_gemini(png_bytes, gemini_prompt)
            print(f"INFO: Gemini API Raw Response: {gemini_response_text[:500]}...") # Print first 500 chars

            # --- PLOT BOUNDING BOXES ON THE IMAGE ---
            try:
                # Convert the original NumPy array (RGB) to a PIL Image
                #pil_image_for_plotting = Image.fromarray(image_np_array)

                # Define an output path for the image with bounding boxes
                #output_image_with_boxes_path = f"observation_image_loop_{i}_with_boxes.png"

                # Call the plot_bounding_boxes function from gemini3_module
                # It will either show the image or save it to output_image_with_boxes_path
                plot_bounding_boxes(img, gemini_response_text)
                img
                
                
                
            except Exception as plot_e:
                print(f"ERROR: Problem plotting bounding boxes: {plot_e}")

        except ValueError as e:
            print(f"ERROR: Image conversion or Gemini API call failed at pre-action observation: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during image conversion or Gemini API call: {e}")
    else:
        print("INFO: No 'head_image' or 'rgb' found in initial observation for this loop. Skipping image conversion and Gemini analysis.")

    if policy:
        
        observation = robot.get_observation()
        observation_frame = build_dataset_frame(dataset_features, observation, prefix="observation")
        print("Observation frame:", observation_frame)

        action_values = predict_action(
            observation_frame,
            policy,
            get_safe_torch_device(policy.config.device),
            policy.config.use_amp,
            task=single_task,
            robot_type=robot.robot_type,
        )
        print("Action values:", action_values)
        #robot.send_action(action_values)


    time.sleep(15)
    i += 1

log_say("Stop recording", True, blocking=True)

robot.disconnect()

log_say("Exiting", True)

        




    

