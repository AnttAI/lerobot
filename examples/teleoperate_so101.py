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
from examples. gemini_2 import analyze_image_with_gemini, parse_json, plot_bounding_boxes 



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
robot = SO101Follower(robot_config)
telep_keyboard = KeyboardTeleop(teleop_keyboard_config)
robot.connect()
telep_keyboard.connect()
i =0

action_features = hw_to_dataset_features(robot.action_features, "action", True)
obs_features = hw_to_dataset_features(robot.observation_features, "observation", True)
dataset_features = {**action_features, **obs_features}


# Optional inventory summary output for agent use
        




    

