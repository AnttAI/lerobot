import signal
import time
import json
import io
import sys
import torch
import numpy as np
import rerun as rr
from PIL import Image
import google.genai.types as types
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.artifacts import InMemoryArtifactService 
from google.adk.sessions import InMemorySessionService
from google.adk.tools.tool_context import ToolContext
import examples.teleoperate_so101 as teleoperate_so101
import examples.gemini_2 as gemini_2
from examples.gemini_2 import analyze_image_with_gemini, parse_json
import atexit
from lerobot.common.utils.utils import (
    get_safe_torch_device,)
from lerobot.common.utils.control_utils import predict_action
from examples import groot_eval_lerobot
from lerobot.common.utils.visualization_utils import _init_rerun


# Set to True to enable Rerun logging, or False to disable
display_data = True

if display_data:
    _init_rerun(session_name="robot_agent")


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
        #print("get_current_inventory Observation received:", observation)

        if "head" not in observation:
            return {"status": "error", "error_message": "No head camera image found."}

        image_bytes = teleoperate_so101.image_obs_to_png_bytes(observation["head"])       
        prompt = "Identify and list all objects in this inventory image that out side the plate. Return only the object labels."
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


async def pick_item(item: str, tool_context: ToolContext) -> dict:
   """Robot pick up the item and put in tray for pickup."""
   
   if policy:
        
        duration = 30
        start = time.perf_counter()
        while True:
            observation = robot.get_observation()
            observation_frame = teleoperate_so101.build_dataset_frame(
            teleoperate_so101.dataset_features, observation, prefix="observation"
            )
            print("Observation frame:", observation_frame.keys)
            #action_values_from_groot = groot_eval_lerobot.eval(observation_frame)
            #action_from_groot = {key: action_values_from_groot[0][i].item() for i, key in enumerate(robot.action_features)}
            #print("Action from Groot values:", action_values_from_groot[0])

            action_values = predict_action(
                observation_frame,
                policy,
                get_safe_torch_device(policy.config.device),
                policy.config.use_amp,
                task=teleoperate_so101.single_task,
                robot_type=robot.robot_type,
            )
            print("Action values:", action_values)
            action = {key: action_values[i].item() for i, key in enumerate(robot.action_features)}
            print("Action values: sent to robot", action)

            # --- Rerun logging ---
            if display_data:
                for obs, val in observation.items():
                    if isinstance(val, float):
                        rr.log(f"observation.{obs}", rr.Scalar(val))
                    elif isinstance(val, np.ndarray):
                        # Only log as image if shape and dtype are valid
                        if val.ndim in (2, 3) and val.dtype in (np.uint8, np.float32):
                            rr.log(f"observation.{obs}", rr.Image(val), static=True)
                for act, val in action.items():
                    if isinstance(val, float):
                        rr.log(f"action.{act}", rr.Scalar(val))
            # --- End Rerun logging ---
                        
            #action_array = action_values.cpu().numpy()
        
            #print(action_array)

            robot.send_action(action)

            loop_time = time.perf_counter() - start
            print(f"Policry running at action at {loop_time:.2f}s")

            if duration and time.perf_counter() - start >= duration:
                break
            time.sleep(1/30)

   
        

        
        #action = {'shoulder_pan.pos': 100, 
        #    'shoulder_lift.pos': -99, 
        #   'elbow_flex.pos': 99, 
        #    'wrist_flex.pos': 94, 
        #    'wrist_roll.pos': 0.3, 
        #    'gripper.pos': 0.1}

        
        #robot.send_action(action)
        observation = robot.get_observation()
        image_bytes = teleoperate_so101.image_obs_to_png_bytes(observation["head"])
        image_artifact = types.Part(
            inline_data=types.Blob(
                mime_type="image/png",
                data=image_bytes
            )
        )
        version = await tool_context.save_artifact(filename="inventory.png", artifact=image_artifact)
        print(f"INFO: Inventory image saved with version: {version}")
        move_robot_to_home(robot) 
        return {"status": "success", "action_values": "dummy"}
   else:
        return {"status": "error", "error_message": "No policy loaded."}


async def ask_groot_to_pick_item(item: str, tool_context: ToolContext) -> dict:
   """Groot Robot pick up the item and put in tray for pickup."""
   
   if policy:
        
        duration = 30
        start = time.perf_counter()
        while True:
            observation = robot.get_observation()
            observation_frame = teleoperate_so101.build_dataset_frame(
            teleoperate_so101.dataset_features, observation, prefix="observation"
            )
            print("Observation frame:", observation_frame.keys())
            action_values_from_groot = groot_eval_lerobot.eval(observation_frame)
            #action_from_groot = {key: action_values_from_groot[0][i].item() for i, key in enumerate(robot.action_features)}
            #print("Action from Groot values:", action_values_from_groot[0])

            for i in range(8):
                action_dict = action_values_from_groot[i]
                print("action_dict", action_dict.values())
                robot.send_action(action_dict)
                time.sleep(0.02)

            
            loop_time = time.perf_counter() - start
            print(f"Policry running at action at {loop_time:.2f}s")

            if duration and time.perf_counter() - start >= duration:
                break
            time.sleep(1/10)

   
        

        
        #action = {'shoulder_pan.pos': 100, 
        #    'shoulder_lift.pos': -99, 
        #   'elbow_flex.pos': 99, 
        #    'wrist_flex.pos': 94, 
        #    'wrist_roll.pos': 0.3, 
        #    'gripper.pos': 0.1}

        
        #robot.send_action(action)
        observation = robot.get_observation()
        image_bytes = teleoperate_so101.image_obs_to_png_bytes(observation["head"])
        image_artifact = types.Part(
            inline_data=types.Blob(
                mime_type="image/png",
                data=image_bytes
            )
        )
        version = await tool_context.save_artifact(filename="inventory.png", artifact=image_artifact)
        print(f"INFO: Inventory image saved with version: {version}")
        move_robot_to_home(robot) 
        return {"status": "success", "action_values": "dummy"}
   else:
        return {"status": "error", "error_message": "No policy loaded."}

        
   

async def handoff_to_teleoperator(item: str, tool_context: ToolContext) -> dict:
    """If Robot is unbale to pick up the item, this will handoff the customer requests to leleoperator to control robot and pick the item.

    Args:
        item (str): The ID of item to be picked up.

    Returns:
        dict: status and result or error msg.
    """
    # send commadn to robot to pick item.
    fps = 30
    duration = 15 # Frames per second for manual teleoperation
    print("Entering manual teleop loop...")
    start = time.perf_counter()
    while True:
        action = teleop_device.get_action()
        print(f"[MANUAL] Action received: {action}")
        robot.send_action(action)

        loop_time = time.perf_counter() - start
        print(f"[MANUAL] Sent zero action at {loop_time:.2f}s")

        if duration and time.perf_counter() - start >= duration:
            break
    time.sleep(1 / fps)
    observation = robot.get_observation()
    image_bytes = teleoperate_so101.image_obs_to_png_bytes(observation["head"])
    image_artifact = types.Part(
        inline_data=types.Blob(
            mime_type="image/png",
            data=image_bytes
        )
    )
    version = await tool_context.save_artifact(filename="inventory.png", artifact=image_artifact)
    print(f"INFO: Inventory image saved with version: {version}")

    return {"status": "success", "action_values": "dummy"}
    
    
# initialize the robot
robot = teleoperate_so101.robot
policy = teleoperate_so101.policy 
teleop_device = teleoperate_so101.teleop_device

artifact_service = InMemoryArtifactService()
session_service = InMemorySessionService()





root_agent = Agent(
    name="robot_store",
    model="gemini-2.0-flash",
    description=(
        "Agent to act as shop keeper, the shop has mobile robot, Agent handles the customer request and sends command to robot ."
    ),
    instruction=(
        "You are a helpful agent who acts as shop keeper for Robot managed store, you enquire customer what items he need, and ask robot to pack the items user asked. To get currently avilable item, ask robot 'get_current_inventory', 'pick_item' with the item ID to pick functions." \
        "If robot is unable to pick the item, then ask groot robot using 'ask_groot_to_pick_item' tool, if that also fails, you can handoff the request to teleoperator by calling 'handoff_to_teleoperator' with the item ID. If you are not sure about the item, ask customer for more details." \
        "If you are not sure about the item, ask customer for more details. If you are not able to understand the request, ask customer to rephrase the request."
    ),
    tools=[get_current_inventory, pick_item, ask_groot_to_pick_item, handoff_to_teleoperator],
)

runner = Runner(
    agent=root_agent,
    app_name="my_artifact_app",
    session_service=session_service,
    artifact_service=artifact_service # Provide the service instance here
)

def move_robot_to_home(robot):
    """
    Sends the robot to its home position.
    Adjust the values below to match your robot's home configuration.
    """
    for motor in robot.bus.motors:
        robot.bus.write("Acceleration", motor, 20)
    home_action = {
        'shoulder_pan.pos': 0,           
        'shoulder_lift.pos': -98,
        'elbow_flex.pos': 98,
        'wrist_flex.pos': 75,
        'wrist_roll.pos': 0.3,
        'gripper.pos': 0.1
    }
    print("Moving robot to home position...")
    robot.send_action(home_action)
    
    # Optionally, wait for the robot to reach home
    time.sleep(2)
    robot.bus.disable_torque()
    
    print("Robot is at home position.")
