import signal
import json
import io
import sys
import torch
import numpy as np
from PIL import Image
from google.adk.agents import Agent
import examples.teleoperate_so101 as teleoperate_so101
import examples.gemini_2 as gemini_2
from examples.gemini_2 import analyze_image_with_gemini, parse_json
import atexit
from lerobot.common.utils.utils import (
    get_safe_torch_device,)
from lerobot.common.utils.control_utils import predict_action

def cleanup_and_exit(signum=None, frame=None):
    print("\n[INFO] Disconnecting robot before exit...")
    try:
        robot.disconnect()
    except Exception as e:
        print(f"[WARNING] Robot disconnect failed: {e}")
    sys.exit(0)

# --- Register signal handlers ---
signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)

def get_current_inventory() -> dict:
    """
    Tool function for the agent.
    Uses the robot head camera and Gemini to return inventory item labels.
    """
    try:
        observation = robot.get_observation()

        if "head" not in observation:
            return {"status": "error", "error_message": "No head camera image found."}

        image_bytes = teleoperate_so101.image_obs_to_png_bytes(observation["head"])
        prompt = "Identify and list all objects in this inventory image. Return only the object labels."
        response = analyze_image_with_gemini(image_bytes, prompt)

        try:
            parsed_json = json.loads(parse_json(response))
            labels = [item["label"] for item in parsed_json if "label" in item]
            if not labels:
                return {"status": "success", "report": "No objects identified in the inventory."}
            return {"status": "success", "report": f"The inventory contains: {', '.join(labels)}."}
        except Exception as e:
            return {"status": "error", "error_message": f"Failed to parse Gemini output: {e}"}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def pick_item(item: str) -> dict:
   """Robot pick up the item and put in tray for pickup."""
   
   if policy:
        observation = robot.get_observation()
        observation_frame = teleoperate_so101.build_dataset_frame(
            teleoperate_so101.dataset_features, observation, prefix="observation"
        )
        print("Observation frame:", observation_frame)

        action_values = predict_action(
            observation_frame,
            policy,
            get_safe_torch_device(policy.config.device),
            policy.config.use_amp,
            task=teleoperate_so101.single_task,
            robot_type=robot.robot_type,
        )
        print("Action values:", action_values)
        action = {'shoulder_pan.pos': 100, 
            'shoulder_lift.pos': -99, 
            'elbow_flex.pos': 99, 
            'wrist_flex.pos': 94, 
            'wrist_roll.pos': 0.3, 
            'gripper.pos': 0.1}

        action_array = action_values.cpu().numpy()
        
        print(action_array)
        robot.send_action(action)
        return {"status": "success", "action_values": "dummy"}
   else:
        return {"status": "error", "error_message": "No policy loaded."}

def handoff_to_teleoperator(item: str) -> dict:
    """If Robot is unbale to pick up the item, this will handoff the customer requests to leleoperator to control robot and pick the item.

    Args:
        item (str): The ID of item to be picked up.

    Returns:
        dict: status and result or error msg.
    """
    # send commadn to robot to pick item.
    task_done = True
    if task_done:
        return {"status": "success"}
    else:
        return {
            "status": "error",
            "error_message": (
                f"Sorry, Couldn't complete pick."
            ),
        }

# initialize the robot
robot = teleoperate_so101.robot
policy = teleoperate_so101.policy 


root_agent = Agent(
    name="robot_store",
    model="" \
    "" \
    "",
    description=(
        "Agent to act as shop keeper, the shop has mobile robot, Agent handles the customer request and sends command to robot ."
    ),
    instruction=(
        "You are a helpful agent who acts as shop keeper for Robot managed store, you enquire customer what items he need, and ask robot to pack the items user asked. To get currently avilable item, ask robot 'get_current_inventory', 'pick_item' with the item ID to pick functions." \
        "If robot is unable to pick the item, you can handoff the request to teleoperator by calling 'handoff_to_teleoperator' with the item ID. If you are not sure about the item, ask customer for more details." \
        "If you are not sure about the item, ask customer for more details. If you are not able to understand the request, ask customer to rephrase the request."
    ),
    tools=[get_current_inventory, pick_item, handoff_to_teleoperator],
)
