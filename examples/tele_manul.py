import logging
import time
import io
from PIL import Image
import numpy as np
import torch
from dataclasses import asdict
from pprint import pformat
from pathlib import Path
from lerobot.common.teleoperators.so101_leader import SO101LeaderConfig, SO101Leader
from lerobot.common.datasets.lerobot_dataset import LeRobotDatasetMetadata
from lerobot.common.datasets.utils import hw_to_dataset_features
from lerobot.common.utils.utils import get_safe_torch_device, init_logging, log_say
from lerobot.common.robots.so101_follower import SO101Follower, SO101FollowerConfig
from lerobot.common.policies.factory import make_policy
from lerobot.configs.policies import PreTrainedConfig
from lerobot.common.cameras.opencv.configuration_opencv import OpenCVCameraConfig

from gemini_2 import analyze_image_with_gemini, plot_bounding_boxes


def image_obs_to_png_bytes(image_obs):
    if isinstance(image_obs, torch.Tensor):
        image_obs = image_obs.cpu().numpy()
    if isinstance(image_obs, np.ndarray):
        if image_obs.dtype != np.uint8:
            image_obs = (255 * np.clip(image_obs, 0, 1)).astype(np.uint8)
        if image_obs.shape[0] in [1, 3] and image_obs.ndim == 3:
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



def manual_teleop_loop(robot, teleop, fps=30, duration=None):
    print("Entering manual teleop loop...")
    start = time.perf_counter()
    try:
        while True:
            action = teleop_device.get_action()
            robot.send_action(action)

            loop_time = time.perf_counter() - start
            print(f"[MANUAL] Sent zero action at {loop_time:.2f}s")

            if duration and time.perf_counter() - start >= duration:
                break
            time.sleep(1 / fps)
    except KeyboardInterrupt:
        print("Manual loop interrupted.")
    finally:
        teleop.disconnect()
        print("Manual teleoperation ended.")


# ----- Setup -----
camera_config = {
    "head": OpenCVCameraConfig(index_or_path='/dev/video2', width=640, height=480, fps=30)
}

robot_config = SO101FollowerConfig(
    port="/dev/ttyACM0",
    id="blue_follower_arm",
    cameras=camera_config
)

teleop_config = SO101LeaderConfig(
    port="/dev/ttyACM1.usbmodem58760431551",
    id="blue_leader_arm",
)

single_task = "pick the wooden block"
policy_path = "/home/jony/Downloads/last/pretrained_model/"
policy_config = PreTrainedConfig.from_pretrained(policy_path)
print("Policy config:", pformat(asdict(policy_config)))

ds_meta = LeRobotDatasetMetadata("anttai/act_so101_test52", root=Path("/home/jony/Downloads/lerobot/anttai/act_so101_test52"))
print("Dataset metadata:", ds_meta)
policy = make_policy(policy_config, ds_meta)
policy.reset()

robot = SO101Follower(robot_config)
robot.connect()

teleop_device = SO101Leader(teleop_config)
teleop_device.connect()

i = 0
while i < 1:
    observation = robot.get_observation()
    print("Observation keys:", list(observation.keys()))

    if 'head' in observation:
        try:
            png_bytes = image_obs_to_png_bytes(observation["head"])
            img = Image.open(io.BytesIO(png_bytes))
            gemini_prompt = "Identify and return bounding boxes for all objects in this image. Provide a summary."

            print("INFO: Calling Gemini API...")
            gemini_response_text = analyze_image_with_gemini(png_bytes, gemini_prompt)
            print(f"Gemini Raw Response: {gemini_response_text[:500]}...")

            try:
                plot_bounding_boxes(img, gemini_response_text)
            except Exception as plot_e:
                print(f"Error plotting boxes: {plot_e}")

        except Exception as e:
            print(f"Gemini image handling error: {e}")
    else:
        print("No image data in observation.")

    manual_teleop_loop(robot, teleop, fps=30, duration=30)
    break

log_say("Stop recording", True, blocking=True)
robot.disconnect()
log_say("Exiting", True)
